#!/usr/bin/env python3
"""Metamorphic tests for ada_indent: change the layout, not the meaning.

Each input is a correctly indented file (the golden sample and the
regress/valid_*.adb fixtures). A transform rewrites it in a way Ada allows
and real code does - a keyword moved to the next line, a statement pulled up
beside its 'then' - and the file is indented again. Every line the transform
did not touch must come back at the column it had; some transforms also say
where the lines they touched belong. No expected output is written by hand:
the file's own indentation is the oracle, so one run tries every place each
transform fits, including layouts no test was ever written for.

Two families:

  in-line   the line structure is kept; only case, spacing, tabs, comments,
            blank lines or leading whitespace change (every line compared,
            except that glue/spread skip lines inside parentheses, whose
            alignment follows the '(' column and moves with the spacing).
  layout    lines are split or joined, one place at a time:
              join_body     'then' / 'else' / 'loop' ending a line + the
                            one-line statement below it -> one line
              split_then    'if C then' / 'elsif C then' -> 'then' alone
                            on the next line, at the 'if' column
              split_when    'exit [Name] when C;' -> 'when C;' on the next
                            line
              split_is      'procedure/function/... P is' -> 'is' alone on
                            the next line, at the header column

Usage:
  metamorphic_check.py [--bin PATH] [--max N] [FILE...]

With no FILE, runs on the golden sample and regress/valid_*.adb next to this
script. Exit status 0 when every transform holds, else 1.
"""

import argparse
import glob
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_ada_tree import find_binary, indent   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- lexing
_TOK = re.compile(r'"(?:[^"]|"")*"|(?<![A-Za-z0-9_)])\'.\'|--.*$')


def segments(line):
    """[(kind, text)]: 'c' code, 'l' a string/char literal or the comment."""
    out, pos = [], 0
    for m in _TOK.finditer(line):
        if m.start() > pos:
            out.append(("c", line[pos:m.start()]))
        out.append(("l", m.group()))
        pos = m.end()
    if pos < len(line):
        out.append(("c", line[pos:]))
    return out


def code_of(line):
    """The line without its comment, literals kept."""
    return "".join(t for k, t in segments(line) if not (k == "l" and t.startswith("--")))


def map_code(line, f):
    return "".join(f(t) if k == "c" else t for k, t in segments(line))


def has_code(line):
    return code_of(line).strip() != ""


def paren_delta(line):
    return sum(t.count("(") - t.count(")") for k, t in segments(line) if k == "c")


def words(line):
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", "".join(t for k, t in segments(line) if k == "c"))


def lead(line):
    return len(line) - len(line.lstrip(" ")) if line.strip() else None


def depths(lines):
    """Paren depth at the START of each line."""
    d, out = 0, []
    for l in lines:
        out.append(d)
        d = max(0, d + paren_delta(l))
    return out


# ------------------------------------------------------ in-line transforms
def glue(l):
    lead_ws = l[:len(l) - len(l.lstrip())]
    return lead_ws + map_code(l.lstrip(), lambda t: re.sub(r"\s*(:=|=>|\.\.|[(),;&|])\s*", r"\1", t))


def per_line(f):
    return lambda lines: ([f(l) for l in lines], list(range(len(lines))))


def insert_comments(lines):
    out, m = [], []
    for l in lines:
        if has_code(l):
            out.append("-- noise: end if; begin ( is")
        m.append(len(out))
        out.append(l)
    return out, m


def insert_blanks(lines):
    out, m = [], []
    for l in lines:
        out.append("")
        m.append(len(out))
        out.append(l)
    return out, m


INLINE = [
    ("upper", per_line(lambda l: map_code(l, str.upper)), False),
    ("lower", per_line(lambda l: map_code(l, str.lower)), False),
    ("glue", per_line(glue), True),
    ("spread", per_line(lambda l: map_code(l, lambda t: re.sub(r"(:=|=>|[(),;&])", r"  \1  ", t))), True),
    ("tabs", per_line(lambda l: map_code(l, lambda t: re.sub(r"(?<=\S) +(?=\S)", "\t", t))), False),
    ("trail_comment", per_line(lambda l: l + "  -- is begin then loop record end if ; ( ("
                               if has_code(l) and "--" not in l else l), False),
    ("flatten", per_line(lambda l: l.lstrip()), False),
    ("jitter", per_line(lambda l: " " * random.Random(l).randint(0, 9) + l.lstrip()), False),
    ("insert_comments", insert_comments, False),
    ("insert_blanks", insert_blanks, False),
]


# ------------------------------------------------------- layout transforms
# Each finds its sites in `lines` (with paren depths `dp`) and, per site,
# returns (new_lines, index_map, expect) where index_map[i] is the new index
# of old line i (None when the line was merged away) and expect maps a new
# index to the column it must have (for the lines the transform touched).

STMT_START_BAN = {"end", "elsif", "else", "when", "exception", "begin", "or",
                  "then", "is", "declare", "private", "record", "select"}


def join_body(lines, dp):
    for i in range(len(lines) - 1):
        a, b = lines[i], lines[i + 1]
        ws = words(a)
        if dp[i] or dp[i + 1] or paren_delta(a) or not ws or "--" in a:
            continue
        last = ws[-1].lower()
        prev = ws[-2].lower() if len(ws) > 1 else ""
        if last not in ("then", "else", "loop") or code_of(a).rstrip().endswith(";"):
            continue
        if (last, prev) in (("then", "and"), ("else", "or"), ("then", "abort")):
            continue
        if not code_of(b).rstrip().endswith(";") or paren_delta(b) or "--" in b:
            continue
        bw = words(b)
        if not bw or bw[0].lower() in STMT_START_BAN or bw[0].lower() in ("if", "case", "for", "while", "loop"):
            continue
        new = lines[:i] + [a.rstrip() + " " + b.strip()] + lines[i + 2:]
        m = list(range(i + 1)) + [None] + [k - 1 for k in range(i + 2, len(lines))]
        yield i, new, m, {i: lead(a)}


def split_then(lines, dp):
    for i, a in enumerate(lines):
        ws = words(a)
        if dp[i] or paren_delta(a) or len(ws) < 3 or "--" in a:
            continue
        if ws[0].lower() not in ("if", "elsif") or ws[-1].lower() != "then" or ws[-2].lower() == "and":
            continue
        head = re.sub(r"\s*\bthen\s*$", "", a.rstrip(), flags=re.I)
        new = lines[:i] + [head, " " * lead(a) + "then"] + lines[i + 1:]
        m = list(range(i + 1)) + [k + 1 for k in range(i + 1, len(lines))]
        yield i, new, m, {i: lead(a), i + 1: lead(a)}


def split_when(lines, dp):
    for i, a in enumerate(lines):
        c = code_of(a)
        mt = re.match(r"^(\s*exit(?:\s+[A-Za-z_][\w.]*)?)\s+(when\b.*;)\s*$", c, flags=re.I)
        if dp[i] or not mt or "--" in a:
            continue
        new = lines[:i] + [mt.group(1), " " * (lead(a) + 2) + mt.group(2)] + lines[i + 1:]
        m = list(range(i + 1)) + [k + 1 for k in range(i + 1, len(lines))]
        yield i, new, m, {i: lead(a)}


def split_is(lines, dp):
    for i, a in enumerate(lines):
        ws = words(a)
        if dp[i] or paren_delta(a) or len(ws) < 3 or "--" in a:
            continue
        if ws[0].lower() not in ("procedure", "function", "package", "task", "protected", "entry") \
                or ws[-1].lower() != "is":
            continue
        head = re.sub(r"\s*\bis\s*$", "", a.rstrip(), flags=re.I)
        new = lines[:i] + [head, " " * lead(a) + "is"] + lines[i + 1:]
        m = list(range(i + 1)) + [k + 1 for k in range(i + 1, len(lines))]
        yield i, new, m, {i: lead(a), i + 1: lead(a)}


LAYOUT = [("join_body", join_body), ("split_then", split_then),
          ("split_when", split_when), ("split_is", split_is)]


# ------------------------------------------------------------------ driver
def run(binary, lines):
    out, _ = indent(binary, "\n".join(lines) + "\n")
    return out


def compare(src, base, out, m, expect, skip_paren_lines):
    """First (old line no, want col, got col, text) that broke, or None."""
    dp = depths(src)
    for i, j in enumerate(m):
        if j is None or not has_code(src[i]) or j in expect:
            continue
        if skip_paren_lines and dp[i]:
            continue
        if lead(base[i]) != lead(out[j]):
            return (i + 1, lead(base[i]), lead(out[j]), src[i].strip())
    for j, col in expect.items():
        if lead(out[j]) != col:
            return (f"{j + 1} (new)", col, lead(out[j]), out[j].strip())
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--bin")
    ap.add_argument("--max", type=int, default=5, help="failures listed per transform and file")
    args = ap.parse_args()
    binary = find_binary(args.bin)
    files = args.files or ([os.path.join(HERE, "ada_indent_sample_test.adb")]
                           + sorted(glob.glob(os.path.join(HERE, "regress", "valid_*.adb"))))
    failures = runs = 0
    for f in files:
        src = open(f, encoding="latin-1").read().split("\n")
        if src and src[-1] == "":
            src.pop()
        base = run(binary, src)
        if base != src:
            print(f"{f}: not a fixpoint to begin with - fix that first")
            failures += 1
            continue
        name = os.path.relpath(f, HERE)
        for tname, t, skip in INLINE:
            new, m = t(src)
            runs += 1
            bad = compare(src, base, run(binary, new), m, {}, skip)
            if bad:
                failures += 1
                print(f"{name}: {tname}: line {bad[0]} moved from column {bad[1]} to {bad[2]}: {bad[3]}")
        dp = depths(src)
        for tname, t in LAYOUT:
            listed = 0
            for site, new, m, expect in t(src, dp):
                runs += 1
                bad = compare(src, base, run(binary, new), m, expect, False)
                if bad:
                    failures += 1
                    if listed < args.max:
                        print(f"{name}:{site + 1}: {tname}: line {bad[0]} should be at column "
                              f"{bad[1]}, got {bad[2]}: {bad[3]}")
                    listed += 1
            if listed > args.max:
                print(f"{name}: {tname}: ... {listed - args.max} more")
    print(f"\n{runs} transformed runs over {len(files)} files: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
