# CLAUDE.md — Adascript Project

## Skills

When the user mentions "adascript" (case-insensitive), read `memory/project_adascript_language.md` before responding. This file contains the full Adascript language reference (syntax, type system, transpilation targets, shell integration, known limitations). Use it to write, review, and debug `.ady` code accurately.

## Pushing to master

After `make test` passes, push finished work straight to `master` (fast-forward
from the working branch; rebase onto `origin/master` first if it has moved,
and re-run `make test`) -- unless the change touches the transpiler itself
(`TO_NIM/`, `TO_PYTHON/`, `ADASCRIPT_GRAMMAR/` or `HPARSEC/`) or Tcheck_tact
(`TOOLS/TCHECK/`), which the user tries out in their own environment first.
Those changes wait on the working branch until the user says to push them to
master.
