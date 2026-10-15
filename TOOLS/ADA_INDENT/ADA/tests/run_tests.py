#!/usr/bin/env python3
"""Self-tests for ada_indent.

  cases/NNN.in.adb -> cases/NNN.out.adb   messy input (any indentation) must
                                          come out as the canonical output
  fixtures/*.adb                          correctly indented files must come
                                          back unchanged, both as they are and
                                          with all leading whitespace stripped

The fixtures cover their constructs as a whole rather than case by case: a
change once dropped the `subtype T is` rule, which pushed a block frame that
never popped, and 511 of the golden sample's 608 lines shifted while every
table case still passed. The stripped run proves the result depends on the
code alone, not on the indentation the input arrived with.

Usage:  run_tests.py [--bin PATH]          (default: ../bin/ada_indent)
Exit status 0 when everything passes, else 1.
"""

import argparse
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Listed by hand rather than globbed, so a fixture that goes missing fails
# instead of being skipped.
FIXTURES = [
    "ada_indent_sample_test.adb",
    "valid_one_liners.adb",
    "valid_generic_select.adb",
    "valid_dense_lines.adb",
    "valid_ugly_spacing.adb",
    "valid_aspects_quantified.adb",
    "valid_named_associations.adb",
    "valid_exit_entry_conditions.adb",
    "valid_record_forms.adb",
    "valid_call_continuations.adb",
    "valid_then_lines.adb",
    "valid_joined_bodies.adb",
    "valid_comment_paragraphs.adb",
    "invalid_recovery.adb",
]


def reindent(binary, text):
    # -q: invalid_recovery.adb and some cases desynchronise on purpose; the
    # tests check the indentation they recover to, not the message.
    p = subprocess.run([binary, "-q"], input=text.encode("latin-1"),
                       capture_output=True, check=True)
    return p.stdout.decode("latin-1")


def read(path):
    with open(path, encoding="latin-1", newline="") as f:
        return f.read()


def check_cases(binary):
    passed = failed = 0
    ins = sorted(glob.glob(os.path.join(HERE, "cases", "*.in.adb")))
    if not ins:
        print("FAIL: no cases found")
        return 0, 1
    for path in ins:
        name = os.path.basename(path)[:-len(".in.adb")]
        want = read(path[:-len(".in.adb")] + ".out.adb")
        got = reindent(binary, read(path))
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: case {name}")
            print("--- expected ---")
            print(want, end="")
            print("--- got ---")
            print(got, end="")
    return passed, failed


def check_fixture(binary, name):
    path = os.path.join(HERE, "fixtures", name)
    if not os.path.isfile(path):
        print(f"FAIL: {name} not found")
        return False
    text = read(path)
    want = text.split("\n")
    ok = True
    for flatten in (False, True):
        src = "\n".join(l.lstrip() for l in want) if flatten else text
        got = reindent(binary, src).split("\n")
        bad = 0
        for i, wanted in enumerate(want):
            if i >= len(got) or got[i] != wanted:
                bad += 1
                if bad == 1:
                    how = "flattened " if flatten else ""
                    print(f"FAIL: {how}{name} is not a fixpoint, first difference at line {i + 1}")
                    print(f"  want |{wanted}|")
                    print(f"  got  |{got[i] if i < len(got) else ''}|")
        if bad:
            print(f"  {bad} lines differ in total")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bin", default=os.path.join(HERE, "..", "bin", "ada_indent"))
    args = ap.parse_args()
    if not os.access(args.bin, os.X_OK):
        sys.exit(f"run_tests: {args.bin} not built; run  g gprbuild -P ada_indent.gpr")
    passed, failed = check_cases(args.bin)
    for name in FIXTURES:
        if check_fixture(args.bin, name):
            passed += 1
        else:
            failed += 1
    print(f"{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
