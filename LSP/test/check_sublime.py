#!/usr/bin/env python3
"""The Sublime syntax against the VS Code grammar: no Sublime Text here to
run it in, so the check is that its regex rules are the VS Code grammar's,
verbatim, and come before the strings in `main` -- the VS Code grammar is
the one the engine check runs.

Exit 0 and "ok" when they agree; 1 and what differs otherwise; 2 when
PyYAML is not installed.
"""
import json
import os
import sys

try:
    import yaml
except ImportError:
    print("no yaml")
    sys.exit(2)

LSP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
tm = json.load(open(os.path.join(LSP, "vscode-adascript", "syntaxes", "adascript.tmLanguage.json")))
sub = yaml.safe_load(open(os.path.join(LSP, "sublime-adascript", "Adascript.sublime-syntax")))

bad = []
for rule in ("regex-literal", "substitution"):
    want = tm["repository"][rule]["match"]
    got = sub["contexts"].get(rule, [{}])[0].get("match")
    if got != want:
        bad.append(f"{rule}: the pattern differs from the VS Code grammar's")
includes = [r.get("include") for r in sub["contexts"]["main"]]
first_string = min(i for i, x in enumerate(includes) if x and "string" in x)
for rule in ("regex-literal", "substitution"):
    if rule not in includes or includes.index(rule) > first_string:
        bad.append(f"main: {rule} is not included before the strings")
print("\n".join(bad) if bad else "ok")
sys.exit(1 if bad else 0)
