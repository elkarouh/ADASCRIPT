# ada_indent

A simplified Ada source re-indenter, written in Ada 2012.

It is **not** a full Ada parser: indentation needs only the keywords that
open, close or split a block, so that is all it implements. The input is read
from a file or stdin; the output goes to stdout, each line replaced by its
re-indented form (2 spaces per level, spaces only). Trailing comments never
move relative to their code.

```bash
bin/ada_indent file.adb               # re-indent a file
cat file.adb | bin/ada_indent         # ...or stdin
```

Options:

| Option | Meaning |
|---|---|
| `-h`, `--help` | usage |
| `-q`, `--quiet` | silence the stderr diagnostics (the indenting is unchanged) |
| `--emit-state` | after each output line print `##STATE:<data>`, the indenter's full parse state |
| `--state <data>` | restore a state snapshot before the first input line (incremental re-indentation) |

Diagnostics (an `end` that contradicts the open blocks, and so on) go to
stderr, never stdout, so a formatter pipe stays clean.

## Build

Needs GNAT and `gprbuild`, run through the `g` wrapper:

```bash
make                                      # or: g gprbuild -P ada_indent.gpr
g gprbuild -P ada_indent.gpr -XMODE=debug # assertions, overflow and stack checks
make clean                                # g gprclean + remove obj/ bin/
```

Without the wrapper: `make GPRBUILD=gprbuild GPRCLEAN=gprclean`.

## Tests

```bash
make test
```

* `tests/run_tests.py` -- the 91 messy-input -> canonical-output cases in
  `tests/cases/` (`NNN.in.adb` must come out as `NNN.out.adb`; what each one
  is about is in `tests/CASES.md`), and the files in `tests/fixtures/`, which
  must come back unchanged both as they are and with all leading whitespace
  stripped: the golden sample (one block per numbered requirement) and
  `valid_*.adb`, code that is valid but awkward and once threw the indenter
  off. `invalid_recovery.adb` is the fixture for the resynchronisation rules.
* `tools/metamorphic_check.py` -- re-lays-out the valid fixtures in ways Ada
  allows (case, spacing, tabs, comments, `then` on its own line, a statement
  pulled up beside its `loop`, ...), re-indents them, and requires every line
  it did not touch to keep its column. The file's own indentation is the
  oracle.
* `tools/check_ada_tree.py DIR...` -- runs the indenter over a tree of Ada
  sources that compile and reports resynchronisation warnings, output that
  changes when re-indented, and damaged lines. Any hit is an indenter bug.

To add a case, put `NNN.in.adb` and `NNN.out.adb` in `tests/cases/` and
describe it in `tests/CASES.md`. To add a fixture, indent it by hand, put it
in `tests/fixtures/` and list it in `FIXTURES` in `tests/run_tests.py`.

## Documentation

* [`docs/INDENTATION.md`](docs/INDENTATION.md) -- the block-stack model, the
  grammar, how comments are placed, how a mis-parse is contained.
* [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) -- the numbered requirements
  the golden sample covers.
* [`docs/STATE_PROTOCOL.md`](docs/STATE_PROTOCOL.md) -- `--emit-state` and
  `--state`, for editors that re-indent incrementally.

## Layout

| Path | Contents |
|---|---|
| `src/strscan.ads/.adb` | character classification, scanners, and the string idioms the indenter uses (`Strip`, `Split_Ws`, `Slice`, ...) |
| `src/ada_scan.ads/.adb` | single-line lexical helpers: `Last_Word`, `Code_Words`, `Stmt_Incomplete`, `Scan_Parens`, `Declared_Name`, ... |
| `src/indenter.ads/.adb` | the block-stack machine: `Indent_Line`, `Indent_Lines`, `Dump_State`/`Load_State` |
| `src/ada_indent.adb` | command line |
| `tests/`, `tools/`, `docs/`, `examples/` | as above |

Two conventions carry the code: indices are **0-based** in `Strscan` and
everything built on it (`Ch (S, I)`, `Slice (S, Lo, Hi)` = `S[Lo:Hi]`), and
enum literals carry a prefix (`B_PKG`, `P_PLAIN`) because `RECORD`, `CASE`,
`LOOP`, ... are reserved words in Ada. The saved state spells them `PKG`,
`PLAIN`, ...
