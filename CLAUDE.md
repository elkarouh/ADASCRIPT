# CLAUDE.md — Adascript Project

## Skills

When the user mentions "adascript" (case-insensitive), read `memory/project_adascript_language.md` before responding. This file contains the full Adascript language reference (syntax, type system, transpilation targets, shell integration, known limitations). Use it to write, review, and debug `.ady` code accurately.

## Pushing to master

Push finished work straight to `master` (fast-forward from the working
branch; rebase onto `origin/master` first if it has moved) -- unless the
change touches the transpiler itself: `TO_NIM/`, `TO_PYTHON/`, `GRAMMAR/` or
`HPARSEC/`. Transpiler changes wait on the working branch until the user says
to push them to master.

What to run before pushing:

- A transpiler change: the full `make test`, and the ada_indent translation
  check -- transpile `TOOLS/ADA_INDENT/ada_indent.ady` with the transpiler
  before the change and after it; `ada_indent.nim` and its `strscan.nim` must
  come out byte for byte the same.
- Anything else: only the checks for what changed (that app's own
  `make test`, the examples touched, the browser check of a page), not the
  full `make test`.
