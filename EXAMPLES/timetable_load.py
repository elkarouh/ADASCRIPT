#!/usr/bin/env python3
"""
timetable_load.py — regenerate the INPUT DATA block in .ady files from the DB.

Usage:
  python3 timetable_load.py [--problem NAME] [--db PATH] <file.ady> [file2.ady ...]

The script replaces the block between
  # ---- INPUT DATA BEGIN ----
and
  # ---- INPUT DATA END ----
in each target .ady file with fresh data loaded from the SQLite DB.

If --problem is omitted, uses DEFAULT.
If no .ady files are given, prints the generated block to stdout.
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timetable_db import DB, DEFAULT_NAME

BEGIN_MARKER = "# ---- INPUT DATA BEGIN ----"
END_MARKER   = "# ---- INPUT DATA END ----"


def generate_block(data):
    classes  = [c["name"] for c in data["classes"]]
    subjects = data["subjects"]
    teachers = data["teachers"]
    rooms    = [r["name"] for r in data["rooms"]]

    def fmt_list(items):
        return "[" + ", ".join(f'"{x}"' for x in items) + "]"

    req_lines = []
    for cls in classes:
        reqs = data["requirements"].get(cls, {})
        inner = ", ".join(f'"{s}": {reqs.get(s, 0)}' for s in subjects)
        req_lines.append(f'    "{cls}": {{{inner}}}')
    req_block = "{\n" + ",\n".join(req_lines) + "\n}"

    ct_lines = []
    for t in teachers:
        subjs = data["can_teach"].get(t, [])
        ct_lines.append(f'    "{t}": {fmt_list(subjs)}')
    ct_block = "{\n" + ",\n".join(ct_lines) + "\n}"

    rc_items = ", ".join(f'"{r["name"]}": {r["capacity"]}' for r in data["rooms"])
    cs_items = ", ".join(f'"{c["name"]}": {c["size"]}' for c in data["classes"])

    lines = [
        BEGIN_MARKER,
        "",
        f"var CLASSES:  []str = {fmt_list(classes)}",
        f"var SUBJECTS: []str = {fmt_list(subjects)}",
        f"var TEACHERS: []str = {fmt_list(teachers)}",
        f"var ROOMS:    []str = {fmt_list(rooms)}",
        "",
        "# requirements[class][subject] = number of periods per week",
        f"var requirements: {{str}}{{str}}int = {req_block}",
        "",
        "# can_teach[teacher] = list of subjects they can teach",
        f"var can_teach: {{str}}[]str = {ct_block}",
        "",
        f"var room_capacity: {{str}}int = {{{rc_items}}}",
        f"var class_size:    {{str}}int = {{{cs_items}}}",
        "",
        END_MARKER,
    ]
    return "\n".join(lines)


def make_copy(template_path, problem, block):
    with open(template_path) as f:
        src = f.read()
    b = src.find(BEGIN_MARKER)
    e = src.find(END_MARKER)
    if b == -1 or e == -1:
        print(f"  WARNING: markers not found in {template_path}, skipping", file=sys.stderr)
        return
    new_src = src[:b] + block + src[e + len(END_MARKER):]
    base, ext = os.path.splitext(template_path)
    out_path = f"{base}_{problem}{ext}"
    with open(out_path, "w") as f:
        f.write(new_src)
    print(f"  Written {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", default=DEFAULT_NAME)
    ap.add_argument("--db",      default=None)
    ap.add_argument("files",     nargs="*")
    args = ap.parse_args()

    if args.problem == DEFAULT_NAME:
        print("Problem is DEFAULT — reference files are immutable, nothing to do.")
        return

    kwargs = {"path": args.db} if args.db else {}
    db    = DB(**kwargs)
    data  = db.load(args.problem)
    block = generate_block(data)

    if not args.files:
        print(block)
        return

    for f in args.files:
        make_copy(f, args.problem, block)


if __name__ == "__main__":
    main()
