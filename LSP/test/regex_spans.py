#!/usr/bin/env python3
"""The regex literals and substitutions the transpiler's tokenizer finds in
each file given: FILE:LINE: TEXT, one per line.

The reference the editor checks compare against -- the editors must see a
regex exactly where the transpiler does, and nowhere else.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "HPARSEC"))
import hek_tokenize as ht  # noqa: E402

for f in sys.argv[1:]:
    with open(f) as fh:
        for t in ht.tokenize_string(fh.read()):
            if t.type in (ht.REGEX_TOKEN, ht.SUBST_TOKEN):
                print(f"{f}:{t.start[0]}: {t.string}")
