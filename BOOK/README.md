# The Adascript Book

*One source, two targets: type-safe scripting from Python to Nim.*

Adascript is a statically-typed superset of Python 3 that borrows the best
ideas of Ada, Nim, Perl, AWK and Bash, and transpiles the result to both
Python 3 and Nim. This book teaches the language from the ground up. Every
concept is illustrated with **real, runnable code from the `EXAMPLES/`
directory** of this repository — not toy snippets invented for the book, but
the programs the language was built to write: simulations, solvers,
interpreters, system tools and interactive shell utilities.

## How to read this book

Chapters 1–5 cover the core language and should be read in order. Chapters
6–12 are feature deep-dives that can be read in any order. Chapter 13 walks
through the large example programs as case studies, and the appendix is a
condensed syntax reference.

Whenever a chapter quotes a program, the path is given relative to the
repository root (e.g. `EXAMPLES/monty_hall.ady`) so you can open the full
source, transpile it, and run it on either backend.

## Table of contents

| # | Chapter | Featured examples |
|---|---------|-------------------|
| 1 | [Introduction: One Language, Two Targets](01-introduction.md) | `primes.ady`, `average_line.ady` |
| 2 | [Types, Declarations, and Annotations](02-types-and-declarations.md) | `graph.ady`, `prisoners.ady`, `openarray_demo.ady` |
| 3 | [Enums, Sets, and Tick Attributes](03-enums-sets-and-tick-attributes.md) | `monty_hall.ady`, `floyd.ady`, `prisoners.ady` |
| 4 | [Tuples, Records, and Variant Records](04-tuples-records-and-variants.md) | `dijkstra.ady`, `argparse.ady`, `lispy.ady` |
| 5 | [Pattern Matching](05-pattern-matching.md) | `argparse.ady`, `awk_example.ady`, `lispy.ady`, `test_shortest_path.ady` |
| 6 | [Collections and Iteration](06-collections-and-iteration.md) | `sudoku.ady`, `spell.ady`, `test_iters.ady` |
| 7 | [Regular Expressions as a Language Feature](07-regex.md) | `test_regex.ady`, `awk_example.ady`, `spell.ady` |
| 8 | [Functions, Closures, and Generators](08-functions-and-generators.md) | `phonecode.ady`, `shortest_path.ady`, `spell.ady` |
| 9 | [Classes, Generics, and Inheritance](09-classes-and-generics.md) | `phonecode.ady`, `lv.ady`, `shortest_path.ady`, `test_awk.ady` |
| 10 | [Optional Types and the Maybe Monad](10-optionals.md) | `graph.ady`, `phonecode.ady`, `test_do_block.ady` |
| 11 | [Shell Integration: Adascript as a Better Bash](11-shell-and-scripting.md) | `fsel.ady`, `sv.ady`, `show_status.ady`, `test_shell_block.ady` |
| 12 | [Living on Two Backends](12-two-backends.md) | `test_ownership.ady`, `rsync_time_machine.ady`, `shortest_path.ady` |
| 13 | [Case Studies: The Big Programs](13-case-studies.md) | `tsp.ady`, `lispy.ady`, `geo_server.ady`, `sudoku.ady`, `lolcate.ady`, `jacks.ady`, `qlearning.ady` |
| A | [Appendix: Syntax Cheat Sheet and Toolchain](14-appendix.md) | — |

## Running the examples

```bash
# Transpile to Python 3 and run
python3 TO_PYTHON/py2py.py -c EXAMPLES/monty_hall.ady

# Transpile to Nim, compile, and run (results are cached)
python3 TO_NIM/py2nim.py EXAMPLES/monty_hall.ady

# Or, with the py2nim shebang and chmod +x:
EXAMPLES/monty_hall.ady
```
