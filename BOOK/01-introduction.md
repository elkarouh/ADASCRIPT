# Chapter 1 — Introduction: One Language, Two Targets

## 1.1 What Adascript is

Adascript is an unapologetically eclectic language. Its author spent years
looking for a language that offers expressive types, a large ecosystem, good
performance, *and* good developer experience — and concluded that no single
language delivers all four. Adascript's answer is to steal:

- from **Python** — the entire surface syntax. Every valid Python 3 file is
  also a valid Adascript file; all extensions are purely additive.
- from **Ada** (and Pascal before it) — enumeration types that work as array
  indexes and loop ranges, variant records, subrange types, and tick
  attributes like `Door_T'First` and `state'Next`.
- from **Nim** — the compile target, the `var`/`let`/`const` discipline, the
  type system, and native performance.
- from **Perl and AWK** — first-class regex literals `/pat/flags`, capture
  variables `$+1`, and `s/pat/repl/` substitution.
- from **Bash** — `$1`, `$#`, `$@`, `$HOME`, file tests like `-f path`, and
  first-class `shell:` blocks.

A single `.ady` source file transpiles to *both* ecosystems:

```
source.ady
    │
    ├── python3 TO_PYTHON/py2py.py source.ady  ──▶  Python 3
    └── python3 TO_NIM/py2nim.py   source.ady  ──▶  Nim  ──▶  native binary
```

You prototype with Python's ecosystem and debugging comfort, then ship the
same source as a compiled Nim binary — or keep both targets alive forever, as
the examples in this repository do.

## 1.2 Hello, world — and hello, benchmark

The smallest Adascript program is also a valid Python program, except for one
courtesy inherited from Python 2: `print` works without parentheses.

```python
#!/usr/bin/env py2nim
print "Hello, world!"
```

The shebang line matters. With `chmod +x`, running `./hello.ady` transpiles
the file to Nim, compiles it into a cache directory
(`~/.cache/hparsec/cache-<HASH>/`), symlinks the binary next to the source,
and runs it. Subsequent runs skip whatever is already up to date, so an
unchanged script starts as fast as any native executable.

Here is the first real program, `EXAMPLES/primes.ady`, which counts the
primes below one million and times itself:

```python
#!/usr/bin/env py2nim

pyimport time

N = 1000000

def is_prime(n: Positive) -> bool:
    result = True
    limit : Positive = Positive(n**0.5)
    for k in 2..limit:
        if n % k == 0:
            result = False
            break

def count_primes(n: Positive) -> Positive:
    result = 1 # we know 2 is a prime
    for k in 3..<n:
        if is_prime(k):
            result += 1

start = time.perf_counter()
print f"Number of primes: {count_primes(N)}"
finish = time.perf_counter()
print f"time elapsed: {finish - start}/s"
```

Twenty lines, and already half the language's character is on display:

- **Ada-style numeric subtypes.** `Positive` (1..) and its sibling `Natural`
  (0..) are available out of the box, mapping to Nim's types of the same
  names and to plain `int` in Python.
- **Range operators.** `2..limit` is an inclusive range; `3..<n` excludes the
  upper bound. In Python output these become `range(2, limit+1)` and
  `range(3, n)`; in Nim they are native ranges.
- **The implicit `result` variable.** Borrowed from Nim: a function with a
  return-type annotation has a pre-declared `result` variable, and falling
  off the end returns it. `is_prime` never writes `return`.
- **Python interop.** `pyimport time` plus `time.perf_counter()` works on
  both targets — the transpiler knows which Python stdlib modules have native
  Nim equivalents and maps the calls (here `times`/`epochTime` territory).
- **f-strings and parenthesis-free `print`**, which becomes `echo fmt"..."`
  in Nim.

The payoff for these twenty lines: run it with `py2py.py -c` and you get
Python's answer in Python's time; run it with `py2nim.py -d:release` and the
identical source runs at native speed.

## 1.3 A four-line filter

Adascript is also meant for the small end of the scale — the scripts you
would otherwise write in AWK. `EXAMPLES/average_line.ady` in its entirety:

```python
#!/usr/bin/env py2nim
"""
cat FILE | ./average_line
./average_line < FILE
"""

var sum : Natural = 0
var count : Natural = 0
for line in stdin.lines:
  sum += line'Length
  count += 1

print f"Average line length is {sum/count}"
```

Note `line'Length` — an Ada *tick attribute* applied to a string, and
`stdin.lines`, an iterator over standard input that works on both backends.
Chapter 3 covers tick attributes; Chapter 11 shows how far the
shell-scripting side of the language goes.

## 1.4 The toolchain at a glance

```bash
# Python backend
python3 TO_PYTHON/py2py.py source.ady        # print generated Python to stdout
python3 TO_PYTHON/py2py.py -c source.ady     # transpile and run

# Nim backend
python3 TO_NIM/py2nim.py source.ady          # transpile + compile + run (default)
python3 TO_NIM/py2nim.py -t source.ady       # transpile only, write source.nim
python3 TO_NIM/py2nim.py c -d:release source.ady   # optimised build
```

Per-file compiler options live on the second line of the source, after the
shebang. Many examples pin their C compiler this way:

```python
#!/usr/bin/env py2nim
#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc
```

Any flag `py2nim` does not recognise (e.g. `-d:release`, `--opt:speed`) is
forwarded to the Nim compiler. Builds are incremental at three levels:
transpilation is skipped if the `.nim` file is newer than both the source and
the transpiler; compilation is skipped if the binary is newer than the
`.nim`; and if everything is current the cached binary simply runs.

## 1.5 What the examples directory contains

The `EXAMPLES/` directory is the language's proving ground — every feature
was driven by a real program there. A rough map, which is also the plan of
this book:

| Kind | Programs |
|------|----------|
| Classic algorithms | `primes.ady`, `graph.ady`, `dijkstra.ady`, `floyd.ady`, `sudoku.ady`, `spell.ady`, `phonecode.ady`, `tsp.ady` |
| Simulations | `monty_hall.ady`, `prisoners.ady` |
| Frameworks | `shortest_path.ady` (+ `test_shortest_path.ady`), `state_search.ady` (+ tests) |
| Operations research / RL | `dp/jacks.ady`, `td_learning/qlearning.ady`, `td_learning/sarsa.ady`, `timetable_*.ady` |
| An interpreter | `INTERACTIVE/lispy.ady` — a full Scheme interpreter |
| Text processing | `awk_example.ady`, `test_awk.ady`, `test_regex.ady`, `average_line.ady` |
| System tools | `rsync_time_machine.ady`, `lolcate/lolcate.ady`, `geo_server.ady` |
| Interactive shell tools | `INTERACTIVE/fsel.ady`, `INTERACTIVE/sv.ady`, `INTERACTIVE/show_status.ady`, `INTERACTIVE/lv.ady`* |
| Feature exercises | `openarray_demo.ady`, `test_iters.ady`, `test_do_block.ady`, `test_ownership.ady`, `test_shell_block.ady`, `test_expect.ady`, `argparse.ady` |

\* `lv.ady` lives at the top of `EXAMPLES/`.

By the end of the book you will have read substantial parts of all of them.

---

*Next: [Chapter 2 — Types, Declarations, and Annotations](02-types-and-declarations.md)*
