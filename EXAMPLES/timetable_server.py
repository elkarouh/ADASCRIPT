#!/usr/bin/env python3
"""Timetable solver backend.
Usage:  python3 timetable_server.py
API:
  GET  /list              -> {"names": [...]}
  GET  /load?name=X       -> {"ok": true, "data": {...}}
  POST /save              <- {"name": "X", "data": {...}}  -> {"ok": true}
  POST /delete            <- {"name": "X"}                 -> {"ok": true}
  POST /solve             <- problem dict                  -> {"ok": true, "schedule": [...], ...}
"""

import json, time, os, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from timetable_db import DB

PORT = 8765
db   = DB()

# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

DAYS     = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_SLOTS = 8


def solve(data):
    days    = DAYS
    slots   = list(range(1, MAX_SLOTS + 1))
    periods = [(d, s) for d in days for s in slots]

    classes  = [c["name"] for c in data["classes"]]
    rooms    = [r["name"] for r in data["rooms"]]
    teachers = data["teachers"]

    class_size    = {c["name"]: c["size"]     for c in data["classes"]}
    room_capacity = {r["name"]: r["capacity"] for r in data["rooms"]}
    can_teach     = {t: set(ss) for t, ss in data["can_teach"].items()}
    requirements  = {c: {s: int(v) for s, v in sv.items() if int(v) > 0}
                     for c, sv in data["requirements"].items()}

    lessons = []
    for c in classes:
        for s, cnt in sorted(requirements.get(c, {}).items()):
            for occ in range(cnt):
                lessons.append((c, s, occ))

    if not lessons:
        return {"ok": False, "error": "No lessons to schedule."}

    def candidates(c, s):
        return [(t, r, p)
                for t in teachers for r in rooms for p in periods
                if s in can_teach.get(t, set())
                and room_capacity.get(r, 0) >= class_size.get(c, 0)]

    all_candidates = {}
    for c in classes:
        for s in requirements.get(c, {}):
            cands = candidates(c, s)
            if not cands:
                return {"ok": False,
                        "error": f"No valid candidate for {c}/{s} — check teacher assignments and room capacities."}
            all_candidates[(c, s)] = cands

    def is_consistent(assignment, lesson, value):
        c, _, _ = lesson
        t, r, p = value
        for (c2, _, _), (t2, r2, p2) in assignment.items():
            if p == p2 and (t == t2 or c == c2 or r == r2):
                return False
        return True

    def count_options(assignment, lesson):
        c, s, _ = lesson
        return sum(1 for v in all_candidates[(c, s)]
                   if is_consistent(assignment, lesson, v))

    stats = {"calls": 0, "backtracks": 0}

    def backtrack(assignment, remaining):
        stats["calls"] += 1
        if not remaining:
            return True
        lesson = min(remaining, key=lambda l: count_options(assignment, l))
        remaining.remove(lesson)
        c, s, _ = lesson
        for value in all_candidates[(c, s)]:
            if is_consistent(assignment, lesson, value):
                assignment[lesson] = value
                if backtrack(assignment, remaining):
                    return True
                del assignment[lesson]
                stats["backtracks"] += 1
        remaining.append(lesson)
        return False

    assignment = {}
    t0 = time.perf_counter()
    solved = backtrack(assignment, list(lessons))
    elapsed = time.perf_counter() - t0

    if not solved:
        return {"ok": False,
                "error": "No solution found. Try relaxing constraints (more rooms, teachers, or periods)."}

    schedule = [{"class": c, "subject": s, "occ": occ,
                 "teacher": t, "room": r, "day": d, "slot": sl}
                for (c, s, occ), (t, r, (d, sl)) in assignment.items()]

    return {"ok": True, "schedule": schedule,
            "stats": {"calls": stats["calls"],
                      "backtracks": stats["backtracks"],
                      "elapsed_ms": round(elapsed * 1000, 1)},
            "days": days, "slots": slots, "classes": classes}

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj):
        payload = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/list":
            self._send_json({"names": db.list()})
        elif path == "/load":
            qs   = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0].strip()
            try:
                self._send_json({"ok": True, "data": db.load(name)})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)})
        else:
            viewer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timetable_viewer.jsx")
            try:
                with open(viewer, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(body))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        path = urlparse(self.path).path
        try:
            data = json.loads(body)
            if path == "/save":
                name = data.get("name", "").strip()
                if not name:
                    raise ValueError("name is required")
                db.save(name, data["data"])
                result = {"ok": True}
            elif path == "/delete":
                name = data.get("name", "").strip()
                db.delete(name)
                result = {"ok": True}
            else:
                result = solve(data)
        except Exception as e:
            result = {"ok": False, "error": str(e)}
        self._send_json(result)


def kill_existing():
    import signal, subprocess
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{PORT}"], text=True).strip()
        for pid in out.splitlines():
            os.kill(int(pid), signal.SIGTERM)
    except (subprocess.CalledProcessError, ValueError):
        pass

if __name__ == "__main__":
    kill_existing()
    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Timetable solver running at {url}")
    print(f"Database: {db.path}  (problems: {db.list()})")
    print("Press Ctrl-C to stop.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
