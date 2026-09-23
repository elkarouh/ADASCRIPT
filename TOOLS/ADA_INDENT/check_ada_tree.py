#!/usr/bin/env python3
"""Run ada_indent over a tree of Ada sources and report what looks like a bug.

The sources are assumed to compile, which gives three checks that need no
knowledge of what the right indentation is:

  warnings   ada_indent reports on stderr each time it has to resynchronise
             on code it could not make sense of. On code that compiles there
             is nothing to resynchronise on, so every warning is a mis-parse.
  unstable   re-indenting the indenter's own output must change nothing. A
             file where it does has a line whose treatment depends on the
             indentation it arrived with - which should never matter.
  damaged    the output must have the same lines as the input, with only the
             leading (and trailing) whitespace changed.

It also counts, per file, the lines whose indentation the indenter would
change ('moved'). That is not a bug by itself - the file may simply not be
in the indenter's style - but a file that is otherwise well kept and has a
run of moved lines is the place to look first. --moved lists them.

Usage:
  check_ada_tree.py [options] DIR...

Options:
  --bin PATH     the ada_indent binary (default: 'ada-indent' or 'ada_indent'
                 on PATH, else the ada_indent symlink next to this script)
  --moved        also list every moved line (file:line: old -> new column)
  --max N        list at most N items per file (default 5)
  --jobs N       files processed in parallel (default: number of CPUs)

Exit status: 0 if there are no warnings, unstable or damaged files, else 1.
Moved lines alone never fail the run.
"""

import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ADA_EXTENSIONS = (".adb", ".ads", ".ada")


def find_binary(explicit):
    if explicit:
        return explicit
    for name in ("ada-indent", "ada_indent"):
        found = shutil.which(name)
        if found:
            return found
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ada_indent")
    if os.access(here, os.X_OK):
        return here
    sys.exit("check_ada_tree: no ada_indent binary found; build it with\n"
             "  ady2nim c TOOLS/ADA_INDENT/ada_indent.ady\n"
             "or pass --bin PATH")


def ada_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                if name.lower().endswith(ADA_EXTENSIONS):
                    yield os.path.join(dirpath, name)


def indent(binary, text):
    """(stdout lines, stderr lines) of one run over `text`."""
    r = subprocess.run([binary], input=text, capture_output=True,
                       text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"exit status {r.returncode}: {r.stderr.strip()[:200]}")
    out = r.stdout.split("\n")
    if out and out[-1] == "":
        out.pop()
    return out, [l for l in r.stderr.split("\n") if l.strip()]


def lead(line):
    return len(line) - len(line.lstrip(" \t")) if line.strip() else None


def check_file(binary, path):
    report = {"path": path, "warnings": [], "unstable": [], "damaged": [],
              "moved": [], "error": None}
    try:
        with open(path, encoding="latin-1") as f:
            src = f.read().split("\n")
        if src and src[-1] == "":
            src.pop()
        text = "\n".join(src) + "\n"
        out, warnings = indent(binary, text)
        report["warnings"] = warnings
        if len(out) != len(src):
            report["damaged"].append(f"{len(src)} lines in, {len(out)} out")
        else:
            for i, (a, b) in enumerate(zip(src, out), 1):
                if a.strip() != b.strip():
                    report["damaged"].append(f"line {i}: text changed")
                elif a.strip() and lead(a.expandtabs()) != lead(b):
                    report["moved"].append((i, lead(a.expandtabs()), lead(b)))
        again, _ = indent(binary, "\n".join(out) + "\n")
        for i, (a, b) in enumerate(zip(out, again), 1):
            if a != b:
                report["unstable"].append((i, lead(a), lead(b)))
    except (OSError, RuntimeError) as e:
        report["error"] = str(e)
    return report


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    ap.add_argument("roots", nargs="+", metavar="DIR")
    ap.add_argument("--bin")
    ap.add_argument("--moved", action="store_true")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    binary = find_binary(args.bin)
    files = list(ada_files(args.roots))
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        reports = list(pool.map(lambda p: check_file(binary, p), files))

    bad = 0
    n_warn = n_unstable = n_damaged = n_moved = files_moved = 0
    for r in reports:
        problems = r["error"] or r["warnings"] or r["unstable"] or r["damaged"]
        if problems:
            bad += 1
        if r["error"]:
            print(f"{r['path']}: ERROR {r['error']}")
        for w in r["warnings"][:args.max]:
            # 'ada_indent: line N: msg' -> 'path:N: msg', clickable in editors
            msg = w.split(": ", 1)[1] if w.startswith("ada_indent: ") else w
            if msg.startswith("line "):
                num, _, rest = msg[5:].partition(": ")
                print(f"{r['path']}:{num}: warning: {rest}")
            else:
                print(f"{r['path']}: warning: {msg}")
        if len(r["warnings"]) > args.max:
            print(f"{r['path']}: ... {len(r['warnings']) - args.max} more warnings")
        for d in r["damaged"][:args.max]:
            print(f"{r['path']}: DAMAGED {d}")
        for (i, a, b) in r["unstable"][:args.max]:
            print(f"{r['path']}:{i}: unstable: column {a} on the first run, {b} on the second")
        if r["moved"]:
            files_moved += 1
            if args.moved:
                for (i, a, b) in r["moved"][:args.max]:
                    print(f"{r['path']}:{i}: moved: column {a} -> {b}")
                if len(r["moved"]) > args.max:
                    print(f"{r['path']}: ... {len(r['moved']) - args.max} more moved lines")
        n_warn += len(r["warnings"])
        n_unstable += 1 if r["unstable"] else 0
        n_damaged += 1 if r["damaged"] else 0
        n_moved += len(r["moved"])

    print(f"\n{len(files)} files: {n_warn} warnings, {n_unstable} unstable, "
          f"{n_damaged} damaged; {n_moved} lines in {files_moved} files would move")
    if files_moved and not args.moved:
        print("(--moved lists the lines that would move)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
