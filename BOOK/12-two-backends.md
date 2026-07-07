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
  shims (`nimport stdlib`, `nimport awk`, `nimport iters`, `nimport
  expect`), and for other `.ady` files compiled as libraries.
- **`pyimport x`** — the reverse emphasis; see `primes.ady` (`pyimport
  time`) and `rsync_time_machine.ady`, which opens with both:

  ```python
  pyimport os
  pyimport sys
  pyimport time
  pyimport signal
  nimport strutils, osproc, posix, times
  ```

  One source file, each backend importing what it natively needs.

`nimport`-ing another `.ady` file triggers automatic transpilation of the
dependency into the same build cache. That is how the optimiser framework
splits library from tests:

```python
# test_shortest_path.ady
nimport stdlib
nimport shortest_path  # provides Minimizer and Maximizer — auto-transpiled
```

## 12.2 Python libraries with no Nim equivalent: the nimpy bridge

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

## 12.4 Memory ownership: `own`, `lent`, `move`, `drop`, `with own`

Python has a GC; Nim (ARC/ORC) frees values deterministically when their
owner's scope ends. Adascript exposes optional ownership annotations that
document intent and help ARC elide copies — and are stripped or trivialised
in Python output. `EXAMPLES/test_ownership.ady` demonstrates the whole set:

```python
type Msg_T is record:
    text: str
    count: int

def summarise(msg: lent Msg_T) -> str:      # lent: read-only borrow
    f"{msg.text} x{msg.count}"

def make_msg(text: str, n: int) -> Msg_T:
    var m: Msg_T = Msg_T(text=text, count=n)
    m

def main():
    own a: Msg_T = make_msg("hello", 3)     # unique owner
    print(summarise(a))

    with own tmp = make_msg("scoped", 1):   # RAII block
        print(summarise(tmp))
    # tmp freed here

    own b: Msg_T = move(a)                  # transfer; a is now invalid
    print(summarise(b))

    own c: Msg_T = make_msg("temp", 5)
    drop(c)                                 # explicit early release

    print("done")
```

The vocabulary:

| Construct | Meaning | Nim | Python |
|-----------|---------|-----|--------|
| `own x: T = e` | unique owner; freed at scope end | `var x` (ARC) | plain binding |
| `param: lent T` | borrow: callee only reads | `param: T` | `param: T` |
| `param: own T` | callee takes ownership | `param: sink T` | `param: T` |
| `move(x)` | transfer; `x` becomes invalid | `move(x)` | alias |
| `drop(x)` | destroy now | `=destroy` + `=wasMoved` | `del x` |
| `with own x = e:` | scoped RAII | `block:` + ARC | `try/finally: del x` |

Where they pay off in the examples (per `TUTORIAL.md` §20):

- **`lent`** on read-only traversals — the graph parameter in `graph.ady` /
  `dijkstra.ady`, the candidate set in `spell.ady`. The annotation promises
  "no mutation, no storage" and lets ARC pass a view.
- **`drop`** after an algorithm's working structures are done — releasing the
  `visited` set and queue before returning results.
- **`with own`** around per-branch board copies in `sudoku.ady`'s DFS, so
  each speculative copy dies with its branch instead of accumulating across
  the recursion.

Honest limitations: no borrow checker (misusing `move` is a runtime
zero-value, not a compile error), no shared ownership, no custom destructors
from Adascript, and cyclic structures need Nim's ORC directly.

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
tables in `README.md` and `TUTORIAL.md` are the authority, but the shape is:

- Python output is *plain* Python 3: `Enum`/`NamedTuple`/`@dataclass`
  classes, `match/case`, `subprocess`, `re` — reviewable and debuggable with
  standard tools.
- Nim output is *idiomatic* Nim: native enums, objects and variants,
  `Table`/`HashSet`/bitsets, `proc`/`iterator`, `case` or desugared
  `if/elif`, with a small `stdlib.nim` shim for `PriorityQueue`, `Counter_T`
  and friends.

When something behaves differently between targets, run `py2py.py` and
`py2nim.py -t` and *read both outputs side by side* — they are short, and
the diff usually explains the behaviour immediately.

---

*Next: [Chapter 13 — Case Studies: The Big Programs](13-case-studies.md)*
