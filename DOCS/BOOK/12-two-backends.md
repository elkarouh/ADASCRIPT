# Chapter 12 — Living on Two Backends

The promise of one source and two targets holds only if the language gives
you controlled ways to speak to each backend individually. This chapter
covers that machinery: import mapping, Nim-only constructs, Python-only
libraries via nimpy, and the ownership annotations that guide Nim's memory
management while remaining no-ops in Python.

## 12.1 Import mapping: `import`, `pyimport`, `nimport`

Ordinary Python imports are *mapped*: the transpiler knows which stdlib
modules have native Nim equivalents and rewrites both module and call sites.

```python
import math, time, re, random

x = math.sqrt(4.0)        # Nim: sqrt(4.0)         (import math)
t = time.time()           # Nim: epochTime()        (import times)
n = random.randint(1, 100)# Nim: rand(1..100)       (import random)
```

`os`/`sys` calls map too: `os.path.exists(p)` → `fileExists(p)`,
`os.makedirs(p)` → `createDir(p)`, `sys.exit(1)` → `quit(1)`.

Two prefixed forms give per-backend control:

- **`nimport x`** — import that appears *only* in Nim output. Use it for Nim
  stdlib modules (`nimport strutils, sequtils, algorithm`), for the bundled
  shims (`nimport stdlib`, `nimport awk`, `nimport iters`, `nimport graphs`,
  `nimport expect`), and for other `.ady` files compiled as libraries.
- **`pyimport x`** — the reverse emphasis: an import that appears only in
  Python output, and that the Nim backend routes through nimpy. Read §12.2
  before reaching for it, because it costs more than it looks like it does.

`nimport`-ing another `.ady` file triggers automatic transpilation of the
dependency into the same build cache. That is how the optimiser framework
splits library from tests:

```python
# test_shortest_path.ady
nimport stdlib
nimport shortest_path  # provides Minimizer and Maximizer — auto-transpiled
```

## 12.2 Python libraries with no Nim equivalent: the nimpy bridge

### First: is it a library, or a fact about the machine?

`pyimport` is for **libraries with no shell equivalent** — `numpy`,
`requests`, `pandas`, a vendor's SDK. It is not for the time, the process
id, the platform, the environment, a temporary directory or a file test,
and reaching for it there costs more than it appears to.

What it costs on the Nim side is a real dependency: the build needs nimpy on
the Nim path, the binary links against libpython, and it has to find a
matching interpreter at run time. `EXAMPLES/rsync_time_machine.ady` used to
open with five `pyimport`s — `os`, `sys`, `time`, `signal`, `datetime` —
and for that it could not be compiled by `make test` at all, because the
test run cannot assume nimpy is installed. Every one of the five had a
one-line answer:

| was | now |
|---|---|
| `datetime.now().strftime(...)` | `shell: date +%Y-%m-%d-%H%M%S` |
| `time.time()` | `shell: date +%s` |
| `os.getpid()` | `shell: echo $PPID` — the shell's parent is this program |
| `sys.platform` | `shell: uname -s` |
| `sys.exit(n)` | `quit(n)` |
| `os.path.expanduser` | `$HOME` and `Path` |

`DOCS/ADASCRIPT_FOR_SHELL.md` §11 has the longer table, including the
cases where the shell answer is *not* portable — `date -d` is GNU, so
turning a stamp into an epoch is arithmetic rather than a command.

`pyimport re` is the same mistake in a different register, and the answer is
not the shell but Chapter 7: matching is an operator and captures are
variables, so a pattern you can write needs no import. The one case that is
neither is a pattern that arrives as *data* — a rule read out of a database
column, say, which a literal has nowhere to put.
`EXAMPLES/CFMU/cfmu_get_file_type.ady` had exactly that, and the whole of
its `re` is now three lines around `grep -qE`, fed through `stdin =` so the
subject never touches the quoting.

With the imports gone the file compiles with no nimpy, no libpython, and
joins the compile list. That is the rule in one sentence: **if a shell
script would know how to ask, ask that way.**

### When it really is a library

Import a third-party Python library and the Nim backend routes it through
[nimpy](https://github.com/yglukhov/nimpy) automatically:

```python
import requests
import pandas as pd

r  = requests.get('https://example.com')
df = pd.read_csv('data.csv')
```

becomes, in Nim:

```nim
import nimpy
let requests = pyImport("requests")
let pd       = pyImport("pandas")
```

Values crossing the bridge are `PyObject`s; when you annotate a primitive
target, the transpiler injects the conversion:

```python
count: int   = r.json()['total']     # Nim: r.json()["total"].to(int)
```

and calling a callable `PyObject` (a fitted model, a scipy interpolator)
emits `callObject(...)` for you. The Python-heavy examples
(`EXAMPLES/TIMETABLE/`, `geo_server.ady`'s plotting variants) rely on this
to keep numpy/matplotlib access while the core logic compiles natively.

## 12.3 Raw Nim and per-file flags

- `# nimraw: <code>` — emit a line verbatim into Nim output, invisible to
  Python. Main use: forward declarations for mutual recursion (§8.3).
- `#ady2nim-args c -d:release` on line 2 — per-file Nim compiler options.
  Several examples pin zig as the C compiler this way
  (`#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc`).

Use both sparingly; they are the escape hatches, not the road.

## 12.4 Memory ownership

Python has a GC; Nim (ARC/ORC) frees values deterministically when their
owner's scope ends. Adascript has a small vocabulary for writing down what
you know about a value's lifetime — `own`, `lent`, `move`, `drop` and
`with own` — which guides ARC on one backend and is mostly erased on the
other.

It is the one part of the two-backend contract where a program can observe
the difference, so it has a chapter of its own:
[Chapter 13 — Memory Ownership](13-memory-ownership.md), with what each form
emits, what to use when, and the two cases where the backends give different
answers.

## 12.5 Nim idioms that leak in (pleasantly)

Because the Nim backend is a first-class citizen, a handful of Nim spellings
are valid Adascript, and the examples mix them freely with the Python ones:

- `&` concatenates strings (`sa & str(b)` in `sudoku.ady`) alongside `+`;
- Nim stdlib procs arrive via `nimport`: `alignLeft` (`lv.ady`), `readFile`
  / `writeFile` (`spell.ady`, `fsel.ady`), `getCurrentDir` / `setCurrentDir`
  (`fsel.ady`), `getHomeDir` (`lv.ady`), `sortedByIt` (`lv.ady`):

  ```python
  view_lines = view_lines.sortedByIt((ord(it.state), it.view))
  ```

- `quit(1)` is the portable exit (mapped to `sys.exit(1)` in Python);
- `echo`-style formatting concerns disappear behind f-strings, which compile
  to `fmt"..."`.

Style advice drawn from the examples: prefer the Python spelling where both
exist (it keeps the file runnable-in-your-head for Python readers), and
reach for the Nim names when they are simply better tools — `sortedByIt` and
`alignLeft` have no one-line Python equivalent.

## 12.6 The generated-code contract

It helps to know what the backends emit for each construct — the translation
tables in `README.md` and `DOCS/TUTORIAL.md` are the authority, but the
shape is:

- Python output is *plain* Python 3: `Enum`/`NamedTuple`/`@dataclass`
  classes, `match/case`, `subprocess`, `re` — reviewable and debuggable with
  standard tools.
- Nim output is *idiomatic* Nim: native enums, objects and variants,
  `Table`/`HashSet`/bitsets, `proc`/`iterator`, `case` or desugared
  `if/elif`, with a small `stdlib.nim` shim for `PriorityQueue`, `Counter_T`
  and friends.

When something behaves differently between targets, run `ady2py.py` and
`ady2nim.py -t` and *read both outputs side by side* — they are short, and
the diff usually explains the behaviour immediately.

One caveat worth carrying into the case studies: the two backends are not
equally mature. Nim is the one every example is exercised against, and the
one the `Makefile` builds. The Python backend transpiles the whole corpus,
but several constructs still produce Python that does not run — implicit
return inside `if`/`else`, `Natural` and `Positive` in annotations, and
declarations written without an initialiser. `README.md`'s "Known
Limitations" and `TODO.md` track these with reproductions. Nothing in this
chapter's *design* advice changes; it is the "prototype in Python, ship as
Nim" workflow of §1.1 that currently works better in the shipping direction
than the prototyping one.

---

*Next: [Chapter 13 — Memory Ownership](13-memory-ownership.md)*
