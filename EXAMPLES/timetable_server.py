#!/usr/bin/env python3
"""Timetable solver backend.
Usage:  python3 timetable_server.py [--db PATH] [--port N]
API:
  GET  /list              -> {"names": [...]}
  GET  /load?name=X       -> {"ok": true, "data": {...}}
  POST /save              <- {"name": "X", "data": {...}}  -> {"ok": true}
  POST /delete            <- {"name": "X"}                 -> {"ok": true}
  POST /solve             <- problem dict                  -> {"ok": true, "schedule": [...], ...}
  POST /validate          <- {"schedule": [...], "data": problem dict} -> {"ok": true} or {"ok": false, "violations": [...]}
"""

import json, time, os, threading, webbrowser, argparse, subprocess, tempfile
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
# Solver — delegates to the compiled timetable_sa binary
# ---------------------------------------------------------------------------

DAYS      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAX_SLOTS = 8

_HERE = os.path.dirname(os.path.abspath(__file__))
SA_BINARY = os.path.join(_HERE, "timetable_sa.ady")


def _all_hard_violations(schedule, data):
    """Return sorted list of all hard violation strings."""
    hard       = data.get("hard_constraints", {})
    max_consec = int(hard.get("max_consecutive_same_subj", 2))
    max_day    = int(hard.get("max_teacher_periods_day", 4))

    # Build avoid set from unified teacher_slot_pref table
    avoid_set = set()
    for u in data.get("teacher_slot_pref", []):
        if u.get("pref") == "avoid":
            avoid_set.add((u["teacher"], u["day"], u["slot"]))

    by_period   = {}
    teacher_day = {}
    for e in schedule:
        by_period.setdefault((e["day"], e["slot"]), []).append(e)
        teacher_day.setdefault((e["teacher"], e["day"]), []).append(e["slot"])

    viols = set()

    for (day, slot), entries in by_period.items():
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                a, b = entries[i], entries[j]
                if a["teacher"] == b["teacher"]:
                    viols.add(f"Teacher {a['teacher']} double-booked {day} slot {slot}")
                if a["class"] == b["class"]:
                    viols.add(f"Class {a['class']} double-booked {day} slot {slot}")
                if a["room"] == b["room"]:
                    viols.add(f"Room {a['room']} double-booked {day} slot {slot}")

    for (teacher, day), slots in teacher_day.items():
        if len(slots) > max_day:
            viols.add(f"Teacher {teacher} has {len(slots)} periods on {day} (max {max_day})")

    for e in schedule:
        if (e["teacher"], e["day"], e["slot"]) in avoid_set:
            viols.add(f"Teacher {e['teacher']} unavailable {e['day']} slot {e['slot']}")

    class_day_subj = {}
    for e in schedule:
        class_day_subj[(e["class"], e["day"], e["slot"])] = e["subject"]
    for c in {e["class"] for e in schedule}:
        for d in {e["day"] for e in schedule}:
            run, prev = 0, None
            for sl in range(1, MAX_SLOTS + 1):
                subj = class_day_subj.get((c, d, sl))
                if subj and subj == prev:
                    run += 1
                    if run > max_consec:
                        viols.add(f"Class {c} has >{max_consec} consecutive {subj} on {d}")
                        break
                else:
                    run = 1 if subj else 0
                prev = subj

    return sorted(viols)


def validate(payload):
    """Check a modified schedule against hard constraints.
    payload: {"schedule": [...], "original": [...], "data": {problem dict}}
    - If original is empty: returns all hard violations (used after solve).
    - Otherwise: returns only violations newly introduced vs original (used for drag-drop).
    Returns {"ok": true} or {"ok": false, "violations": [...]}
    """
    schedule = payload["schedule"]
    original = payload.get("original", [])
    data     = payload.get("data", {})

    new_viols = set(_all_hard_violations(schedule, data))

    if not original:
        introduced = sorted(new_viols)
    else:
        orig_viols = set(_all_hard_violations(original, data))
        introduced = sorted(new_viols - orig_viols)

    if introduced:
        return {"ok": False, "violations": introduced}
    return {"ok": True}


def solve(data):
    slots   = list(range(1, MAX_SLOTS + 1))
    classes = [c["name"] for c in data["classes"]]

    # Write the problem to a temp DB, run the SA binary, return its JSON.
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name
    try:
        tmp_store = DB(tmp_db)
        tmp_store.save("_solve", data)

        result = subprocess.run(
            [SA_BINARY, "--db", tmp_db, "--problem", "_solve", "--json"],
            stdout=subprocess.PIPE, stderr=None,
            text=True, timeout=120
        )
        if not result.stdout.strip():
            return {"ok": False, "error": "SA binary produced no output"}

        resp = json.loads(result.stdout.strip())
        if resp.get("ok"):
            resp["days"]    = DAYS
            resp["slots"]   = slots
            resp["classes"] = classes
        return resp
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Solver timed out after 120 seconds"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        os.unlink(tmp_db)

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path} — {args[1]}")

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
            elif path == "/validate":
                result = validate(data)
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
