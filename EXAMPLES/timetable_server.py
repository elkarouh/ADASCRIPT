#!/usr/bin/env python3
"""Timetable solver backend.
Usage:  python3 timetable_server.py [--db PATH] [--port N]
API:
  GET  /list              -> {"names": [...]}
  GET  /load?name=X       -> {"ok": true, "data": {...}}
  POST /save              <- {"name": "X", "data": {...}}  -> {"ok": true}
  POST /delete            <- {"name": "X"}                 -> {"ok": true}
  POST /solve             <- problem dict                  -> {"ok": true, "schedule": [...], ...}
"""

import json, time, os, threading, webbrowser, argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from timetable_db import DB, DB_PATH

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--db",   default=DB_PATH)
ap.add_argument("--port", type=int, default=8765)
_args, _ = ap.parse_known_args()

PORT = _args.port
db   = DB(_args.db)

# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

DAYS      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_SLOTS = 8


def soft_penalty(assignment, max_consec, max_day):
    """Score soft constraint violations. 0 = perfect."""
    consec_violations = 0
    daily_violations  = 0

    # Consecutive same-subject per class per day
    class_day_slots = {}
    for (c, _s, _occ), (_t, _r, (d, sl)) in assignment.items():
        class_day_slots.setdefault(c, {}).setdefault(d, {})[sl] = _s

    for _c, day_map in class_day_slots.items():
        for _d, slot_map in day_map.items():
            run = 1
            for sl in sorted(slot_map)[1:]:
                prev = sl - 1
                if prev in slot_map and slot_map[sl] == slot_map[prev]:
                    run += 1
                    if run > max_consec:
                        consec_violations += 1
                else:
                    run = 1

    # Teacher daily load
    teacher_day_count = {}
    for (_c, _s, _occ), (t, _r, (d, _sl)) in assignment.items():
        teacher_day_count[(t, d)] = teacher_day_count.get((t, d), 0) + 1
    for count in teacher_day_count.values():
        if count > max_day:
            daily_violations += count - max_day

    return consec_violations + daily_violations, consec_violations, daily_violations


def solve(data):
    days    = DAYS
    slots   = list(range(1, MAX_SLOTS + 1))
    periods = [(d, s) for d in days for s in slots]

    classes  = [c["name"] for c in data["classes"]]
    rooms    = [r["name"] for r in data["rooms"]]
    teachers = data["teachers"]

    class_size    = {c["name"]: c["size"]     for c in data["classes"]}
    room_capacity = {r["name"]: r["capacity"] for r in data["rooms"]}
    room_type     = {r["name"]: r.get("room_type", "standard") for r in data["rooms"]}
    can_teach     = {t: set(ss) for t, ss in data["can_teach"].items()}
    requirements  = {c: {s: int(v) for s, v in sv.items() if int(v) > 0}
                     for c, sv in data["requirements"].items()}

    subj_room_type = data.get("subject_room_type", {})
    unavailable    = {(u["teacher"], u["day"], u["slot"])
                      for u in data.get("teacher_unavailability", [])}

    soft = data.get("soft_constraints", {})
    max_consec = int(soft.get("max_consecutive_same_subj", 2))
    max_day    = int(soft.get("max_teacher_periods_day", 4))

    lessons = []
    for c in classes:
        for s, cnt in sorted(requirements.get(c, {}).items()):
            for occ in range(cnt):
                lessons.append((c, s, occ))

    if not lessons:
        return {"ok": False, "error": "No lessons to schedule."}

    def candidates(c, s):
        req_type = subj_room_type.get(s)
        return [
            (t, r, p)
            for t in teachers for r in rooms for p in periods
            if s in can_teach.get(t, set())
            and room_capacity.get(r, 0) >= class_size.get(c, 0)
            and (req_type is None or room_type.get(r, "standard") == req_type)
            and (t, p[0], p[1]) not in unavailable
        ]

    all_candidates = {}
    for c in classes:
        for s in requirements.get(c, {}):
            cands = candidates(c, s)
            if not cands:
                hint = ""
                req_type = subj_room_type.get(s)
                if req_type:
                    hint = f" (no {req_type} room available with sufficient capacity)"
                return {"ok": False,
                        "error": f"No valid candidate for {c}/{s}{hint} — "
                                 "check teacher assignments and room capacities."}
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
                "error": "No solution found. Try relaxing constraints "
                         "(more rooms, teachers, or periods)."}

    total_pen, consec_viol, daily_viol = soft_penalty(assignment, max_consec, max_day)

    schedule = [{"class": c, "subject": s, "occ": occ,
                 "teacher": t, "room": r, "day": d, "slot": sl}
                for (c, s, occ), (t, r, (d, sl)) in assignment.items()]

    return {"ok": True, "schedule": schedule,
            "stats": {"calls": stats["calls"],
                      "backtracks": stats["backtracks"],
                      "elapsed_ms": round(elapsed * 1000, 1),
                      "soft_penalty": total_pen,
                      "soft_details": {
                          "consecutive_violations": consec_viol,
                          "daily_load_violations":  daily_viol,
                      }},
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
    print(f"Database: {db.path}")
    print(f"Problems: {db.list()}")
    print("Press Ctrl-C to stop.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
