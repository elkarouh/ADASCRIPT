#!/usr/bin/env python3
"""Check that every code block in the prose documents is real.

A document that quotes an example is making a claim about a file, and the
file moves. These three documents each open by promising the reader that
what they are looking at compiles and runs, so the promise is worth
checking rather than asserting.

Every ```python block in a checked document is one of three kinds, and an
HTML comment immediately above it says which. The comment does not render,
so the documents read the same as before.

    <!-- from: EXAMPLES/awk_logscan.ady -->
        a quote. Every non-blank line must appear in that file, verbatim.

    <!-- illustrative: why it cannot be a quote -->
        not a quote: a sketch, a signature, a fragment with an undefined
        name or an elided body. Not checked against anything -- which is
        why the reason is required, and why the count is capped below. The
        reason is the part that does the work: a block that cannot say what
        stops it being real code usually can be made into real code. Most
        of what the documents show outside their worked examples lives in
        EXAMPLES/DOC/*_snippets.ady, which `make test` runs.

    (no comment)
        a quote from somewhere in the repository. Every non-blank line
        must appear in some .ady file. Weaker than `from:` -- prefer
        `from:` when the block really is one file's code.

Exit status is 0 when every block checks out, 1 otherwise.
"""
import pathlib
import re
import sys

# Document -> how many blocks may go unchecked. A cap rather than a count,
# so that the easy way out of a failing check -- marking the block
# illustrative and moving on -- costs a deliberate edit here. Lower these
# when a sketch becomes a quote; raising one should need a reason.
DOCS = {
    "DOCS/ADASCRIPT_FOR_AWK.md":    3,
    "DOCS/ADASCRIPT_FOR_SHELL.md":  4,
    "DOCS/WHY_ADASCRIPT.md":        2,
}

ROOT = pathlib.Path(__file__).resolve().parent.parent

# A fenced block, with whatever HTML comment sits immediately above it.
BLOCK = re.compile(
    r"(?:<!--\s*(?P<marker>[^>]*?)\s*-->\s*\n)?```python\n(?P<body>.*?)```",
    re.S)


def significant(body):
    """The lines of a block that a file would have to contain.

    Blank lines and an ellipsis standing for elided code are not evidence
    of anything. A comment is: a comment that has drifted is exactly the
    kind of rot this is looking for.
    """
    for line in body.splitlines():
        text = line.strip()
        if text and text != "...":
            yield text


def main():
    sources = {p: p.read_text() for p in ROOT.rglob("*.ady")}
    every_source = "\n".join(sources.values())

    failures = 0
    for doc, budget in DOCS.items():
        path = ROOT / doc
        if not path.is_file():
            print(f"  {doc}: MISSING")
            failures += 1
            continue
        text = path.read_text()
        checked = quoted = illustrative = 0

        for match in BLOCK.finditer(text):
            marker = (match.group("marker") or "").strip()
            body = match.group("body")
            first = next(significant(body), "")

            if marker.startswith("illustrative"):
                reason = marker[len("illustrative"):].lstrip(":").strip()
                if not reason:
                    print(f"  {doc}: illustrative without a reason:")
                    print(f"      block starting {first[:60]!r}")
                    print(f"      write `<!-- illustrative: why it cannot "
                          f"be a quote -->`")
                    failures += 1
                illustrative += 1
                continue

            if marker.startswith("from:"):
                named = marker[len("from:"):].strip()
                target = ROOT / named
                if not target.is_file():
                    print(f"  {doc}: no such file: {named}")
                    failures += 1
                    continue
                haystack, where = target.read_text(), named
                quoted += 1
            else:
                haystack, where = every_source, "any .ady file"
                checked += 1

            for line in significant(body):
                if line not in haystack:
                    print(f"  {doc}: not in {where}:")
                    print(f"      block starting {first[:60]!r}")
                    print(f"      line           {line[:60]!r}")
                    failures += 1

        print(f"  {doc}: {quoted} quoted, {checked} unattributed, "
              f"{illustrative} illustrative (cap {budget})")
        if illustrative > budget:
            print(f"      {illustrative - budget} more unchecked block(s) than "
                  f"this document is allowed. Quote them from a file, or raise "
                  f"the cap in {pathlib.Path(__file__).name} and say why.")
            failures += 1

    if failures:
        print(f"  {failures} block line(s) do not match their source")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
