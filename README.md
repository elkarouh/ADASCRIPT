# Adascript (WORK IN PROGRESS, use at your own risk)

Adascript is a statically-typed language built on Python 3 that steals the best
features from many languages: **Ada** (enums, variant records, tick attributes,
subranges), **Nim** (compile target, type system, performance), **Perl** and
**AWK** (first-class regex literals `/pat/flags`, `$+N` captures, `s/pat/repl/`
substitution), and **Bash** (`$1`, `$#`, `$@`, `-e path`, `shell:` blocks).
It transpiles to both **Python 3** and **Nim**, letting you write concise,
type-safe code in a familiar syntax and target either ecosystem without
changing the source.

I’ve been searching for the perfect programming language for years and my
conclusion thus far is that it’s missing. Every language I’ve tried makes me
choose between expressive types, a large ecosystem, good performance, and good
devx. Adascript is my attempt to have it all by being unapologetically eclectic:
if a language got something right, we take it.

This is a programming language that I’ve been developing for about 10 years.
More recently, I’ve used Codex as an assistant for parts of the documentation
work, refactoring, and some of the more difficult feature implementations, so
the project does include some AI-assisted code and writing. That said, the
overall design, review, and ongoing maintenance of the project are handled by me.

**Why two backends.** Adascript began more than ten years ago as an
augmented-Python-to-Python translator, which is why the Python backend came
first. About five years ago I added the Nim backend, because Nim generates C
and JavaScript: one language can then write a whole application, the server
side as a native program and the browser side as a script.

> **The two backends are not equal.** The Nim backend (`ady2nim`) is the
> reference: it supports every feature of the language and its compiler does
> the checking. The Python backend (`ady2py`) supports less -- it refuses some
> declarations (scaled units, for one), does not check an argument's type, and
> stops at six union members -- so a program that runs on Python can still be
> refused by Nim. Write for Nim when you want every guarantee; use Python as a
> second target for what it can take. See "What is not yet true" in
> `DOCS/WHY_ADASCRIPT.md`.

Most Python 3 code is valid Adascript as it stands. The exception is `import`:
Adascript asks where a module comes from -- `pyimport os` for a Python package,
`nimport os` for a Nim module -- and the Nim backend rejects a plain `import os`.
The rest is additive: left-to-right type annotations, Ada-style enums and variant records,
tick attributes, range expressions, `case/when` pattern matching, Perl/AWK-style
regex literals, and first-class shell command integration.

# Elucubrations
Pascal has set base minimum for systems programming languages. In Pascal it is possible to declare enumerated type and use it wherever ordinal type is accepted. Index an array and for loop. Ada has inherited this base minimum and enhanced by records with discriminants. In Rust I can see nothing but mess. Rust enumeration type can be used as neither array index nor for loop. Also, Rust for some unknown reason tangled records with discriminats and custom enumeration types in a way that cannot be untangled. Yeah, record with discriminant is a popular use of enumeration type, but everything becomes stupid if they come in inseparatable pack. Rust does not deliver base minimum. Wirth's minimum.

```
source.ady
    │
    ├── python3 TO_PYTHON/ady2py.py source.ady  ──▶  Python 3
    └── python3 TO_NIM/ady2nim.py   source.ady  ──▶  Nim
```

---

## Table of Contents

- [Quick Example](#quick-example)
- [Installation](#installation)
- [Usage](#usage)
- [Type Annotations](#type-annotations)
- [Type Declarations](#type-declarations)
- [Collections](#collections)
- [Variable Declarations](#variable-declarations)
- [Range Expressions](#range-expressions)
- [Case / When Statements](#case--when-statements)
- [Statement Modifier](#statement-modifier)
- [Regex Literals](#regex-literals)
- [Tick Attributes](#tick-attributes)
- [Functions](#functions)
- [Classes and Inheritance](#classes-and-inheritance)
- [Memory Ownership](#memory-ownership)
- [HTML Pages: `html:` blocks](#html-pages-html-blocks)
- [Modules and Project Layout](#modules-and-project-layout)
- [Nim-Only Imports](#nim-only-imports)
- [Raw Nim Injection](#raw-nim-injection)
- [Python Interoperability](#python-interoperability)
- [Print Statement](#print-statement)
- [Unions: `A | B`](#unions-a--b)
- [Failures as Values: `T | !F`](#failures-as-values-t--f)
- [Shell Statements](#shell-statements)
- [Bash Variables](#bash-variables)
- [Callable objects and pipe operator](#callable-objects-and-pipe-operator)
- [Enum constructors](#enum-constructors)
- [Side by Side with awk and Bash](#side-by-side-with-awk-and-bash)
- [Summary of Adascript-Only Syntax](#summary-of-adascript-only-syntax)
- [Benchmark Programs](#benchmark-programs)
- [Tools](#tools)
- [Editor Support](#editor-support)
- [Architecture](#architecture)
- [Known Limitations](#known-limitations)

---

## Quick Example

```python
type Stage_T is enum STAGE1, STAGE2, STAGE3

type Choice_T is tuple:
    weight: int
    benefit: int

var items: [Stage_T]Choice_T = [
    STAGE1: (weight: 2, benefit: 65),
    STAGE2: (weight: 3, benefit: 80),
    STAGE3: (weight: 1, benefit: 30),
]

for s in Stage_T'First .. Stage_T'Last:
    let choice: Choice_T = items[s]
    print(f"Stage {s}: weight={choice.weight}, benefit={choice.benefit}")
```

**Python 3 output**

```python
from enum import Enum, auto
from typing import NamedTuple

class Stage_T(Enum):
    STAGE1 = auto()
    STAGE2 = auto()
    STAGE3 = auto()

class Choice_T(NamedTuple):
    weight: int
    benefit: int

items: dict[Stage_T, Choice_T] = {
    Stage_T.STAGE1: Choice_T(weight=2, benefit=65),
    Stage_T.STAGE2: Choice_T(weight=3, benefit=80),
    Stage_T.STAGE3: Choice_T(weight=1, benefit=30),
}

for s in range(Stage_T.STAGE1.value, Stage_T.STAGE3.value + 1):
    choice: Choice_T = items[s]
    print(f"Stage {s}: weight={choice.weight}, benefit={choice.benefit}")
```

**Nim output**

```nim
import sequtils

type Stage_T = enum STAGE1, STAGE2, STAGE3

type Choice_T = tuple
  weight: int
  benefit: int

var items: array[Stage_T, Choice_T] = [
  STAGE1: (weight: 2, benefit: 65),
  STAGE2: (weight: 3, benefit: 80),
  STAGE3: (weight: 1, benefit: 30),
]

for s in Stage_T.STAGE1 .. Stage_T.STAGE3:
  let choice: Choice_T = items[s]
  echo fmt"Stage {s}: weight={choice.weight}, benefit={choice.benefit}"
```

---

## Installation

```bash
git clone https://github.com/elkarouh/ADASCRIPT
cd ADASCRIPT
make install                      # or: make install PREFIX=$HOME/.local
```

`make install` puts `ady2nim` and `ady2py` on your PATH, so any `.ady` file
starting with `#!/usr/bin/env ady2nim` runs directly:

```bash
chmod +x script.ady && ./script.ady
```

It installs into `/usr/local/bin`, falling back to `~/.local/bin` when that
is not writable, and finishes by transpiling and running a small program to
prove the install works. `make uninstall` removes the launchers again.

The two tools were called `py2nim` and `py2py` while Adascript was still a
Python dialect rather than its own language. `make install` also writes those
names as aliases, so a `.ady` file carrying the old shebang keeps working.

The launchers are wrappers rather than symlinks so they can pin the
interpreter: the scripts' own shebang says `python3`, which on many systems
is older than the version the transpiler needs.

You can also skip the install and invoke the scripts directly —
`python3.12 TO_PYTHON/ady2py.py source.ady` — but then the shebang line in the
examples will not resolve.

### Python dependencies

Python **3.12 or newer** (the tokenizer relies on `FSTRING_START` tokens,
which earlier versions do not emit). Nothing beyond the standard library.

### Nim dependencies

| Package | Install | Required for |
|---------|---------|--------------|
| `nimpy` | `nimble install nimpy` | Any `.ady` file that uses `pyimport` to call Python libraries from Nim |
| `karax` >= 1.5.0 | `nimble install karax@1.5.0` (1.2.1 does not compile on Nim 2.2) | Any `.ady` file with an `html:` block (`BROWSER_EXAMPLES/HTML/`) |
| `db_connector` | `nimble install db_connector` | Any `.ady` file that uses `import db` (SQLite support; removed from Nim 2.x stdlib) |
| `zig` / `zigcc` | *optional* — download from [ziglang.org](https://ziglang.org/download/), then `printf '#!/bin/sh\nexec zig cc "$@"\n' > /usr/local/bin/zigcc && chmod +x /usr/local/bin/zigcc` | Preferred by files pinning `#ady2nim-args c --cc:clang --clang.exe:zigcc` — `state_search.ady`, `shortest_path.ady`, their tests, and the timetable examples |

Standard library Nim modules (`std/deques`, `tables`, `hashes`, `math`, `re`, `posix`, …) are bundled with Nim and need no separate install.

A compiler pin is a preference, not a requirement. When the pinned binary is
not installed, `ady2nim` drops the pin — with a note on stderr — and lets Nim
use its default C compiler, so those files build with whatever compiler is
present. Install zig only if you want the exact toolchain the examples were
measured with.

`make test` needs `nimpy` and `db_connector`, plus `bc` and `libpcre3` at
runtime. [`requirements.txt`](requirements.txt) lists every dependency, which
example needs it, and the install command.

---

## Usage

### Transpile to Python 3

```bash
python3 TO_PYTHON/ady2py.py source.ady         # print to stdout
python3 TO_PYTHON/ady2py.py -c source.ady      # transpile and run
echo "var x: int = 42" | python3 TO_PYTHON/ady2py.py  # from stdin
```

### Transpile to Nim

```bash
python3 TO_NIM/ady2nim.py source.ady           # transpile and compile+run (default)
python3 TO_NIM/ady2nim.py -t source.ady        # transpile only; writes the .nim
                                               # into the cache and prints its
                                               # path to stderr
python3 TO_NIM/ady2nim.py c source.ady         # compile (nim c)
python3 TO_NIM/ady2nim.py c -r source.ady      # compile and run (nim c -r)
python3 TO_NIM/ady2nim.py --test               # run built-in self-tests
```

**Incremental builds** — `ady2nim` performs a three-tier up-to-date check:
skip transpilation if `.nim` is newer than both `.ady` and the transpiler
source files; skip compilation if the binary is newer than `.nim`; execute
the existing binary directly if everything is current. Changing any
transpiler `.py` file automatically triggers retranspilation of all cached
`.ady` files on their next run.

**Clean source directories** — all generated artifacts (`.nim` file,
compiled binary, nimcache) are stored in `~/.cache/adascript/cache-<HASH>/`,
keyed by the absolute path of the `.ady` file. Source directories stay
uncluttered and the cache survives reboots (inspired by
[nimbang](https://github.com/jabbalaci/nimbang)). Set `XDG_CACHE_HOME` to put
the cache somewhere else — `XDG_CACHE_HOME=$(mktemp -d) ady2nim prog.ady`
builds from cold without touching the real one.

**Shebang support** — add `#!/usr/bin/env ady2nim` as the first line of an
`.ady` file and make it executable. The file compiles and runs directly
without arguments to the transpiler.

**Per-file compiler options** — add an `#ady2nim-args` directive as the
second line to set per-file nim options (inspired by nimbang's
`#nimbang-args`). The first token may be a nim subcommand; remaining tokens
are forwarded to the nim compiler. Command-line flags always override the
directive.

A compiler pin in the directive (`--cc:NAME`, `--NAME.exe:BIN`,
`--NAME.linkerexe:BIN`) is treated as a preference. If the named binary is
not installed, `ady2nim` drops just that flag, notes it on stderr, and lets
nim use its default C compiler — so a file pinning `zigcc` still builds on a
machine without zig. Every other flag in the directive is passed through
untouched.

```python
#!/usr/bin/env ady2nim
#ady2nim-args c -d:release
```

**Symlink next to source** — after a successful compile, `ady2nim` creates a
symlink in the same directory as the `.ady` file pointing to the cached
binary. Running `./script` from the source directory works without any path
gymnastics.

**Forwarding flags to Nim** — any flag not recognised by `ady2nim` (e.g.
`-d:release`, `--opt:speed`) is passed straight to `nim`.

```bash
python3 TO_NIM/ady2nim.py c -d:release source.ady   # optimised build
```

### Nim-specific directives

Three comment-based directives control Nim-specific behaviour and are ignored
by the Python transpiler:

| Directive | Purpose |
|-----------|---------|
| `#ady2nim-args c -d:release` | Per-file Nim compiler flags (second line only) |
| `nimport strutils, sequtils` | Import a Nim module without a Python equivalent |
| `# nimraw: <code>` | Emit a raw Nim line verbatim (e.g. a pragma) |

`# nimraw:` is for Nim with no Adascript spelling, such as a pragma. It is
not needed for forward declarations: definition order does not matter, so
mutually recursive functions are written as they are in Python:

```python
def a(x: int) -> int:
    return b(x - 1)             # b is defined below -- fine
def b(x: int) -> int:
    if x <= 0: return 0
    return a(x - 1)
```

---

## Type Annotations

Adascript uses a concise **left-to-right** annotation syntax rather than
Python's `typing` module. There is one idea behind all of the container
forms, and it is worth learning once, because two independent questions
settle which form you want.

**Is it ordered?** — that is the *shape* of the brackets.

- `[…]` — **ordered**. There is a first, a next and a last, and the
  container is held in that order.
- `{…}` — **unordered**. There is no order at all, and you must not rely on
  one (see the warning below — the two backends genuinely differ).

**Is it keyed?** — that is whether anything sits *inside* the brackets.

- Nothing inside — `[]T`, `{}T` — a **collection** of `T`.
- A type inside — `[K]T`, `{K}V` — a **mapping**, from the type in the
  brackets to the one that follows them.

Four combinations, four forms, and each corner is just the everyday name of
the thing:

|                | ordered `[…]`                    | unordered `{…}`   |
|----------------|----------------------------------|-------------------|
| **collection** | `[]T` — a list                   | `{}T` — a set     |
| **mapping**    | `[K]T` — keys in order           | `{K}V` — a dict   |

Read them aloud and they say what they are:

- `[]int` — an ordered collection of `int`. A list.
- `{}str` — an unordered collection of `str`. A set.
- `{str}int` — an unordered mapping from `str` to `int`. A dict.
- `[Color]int` — an ordered mapping from `Color` to `int`. One slot per enum
  member, held in enum order.
- `[0..9]int` — an ordered mapping from `0 .. 9` to `int`. A fixed array.
- `[str]float` — an ordered mapping from `str` to `float`, its keys held in
  the order they were inserted.
- `[10]int` — **the same type**, spelled by size instead of by bound. A
  length `N` is shorthand for the subrange `0 .. N-1`, so `[10]int` and
  `[0..9]int` are one type, not two — on the Nim backend
  `array[10, int] is array[0..9, int]` is literally `true`, and a value of
  one is assignable to the other.

Between either pair of brackets the key may be any type; what the ordering
depends on is the key. With a **finite ordinal type** — an enum, `bool`,
`char`, an integer subrange — every key and its place are known at compile
time, and `[O]T` is an array: one slot per value of `O`, in the order of
`O`. With any other key — `str`, `int`, a class, a tuple named by a type —
the keys are not known until they arrive, so they are held **in insertion
order**: `[str]float` is an `OrderedTable` on Nim and a dict on Python.
Either way `[…]` keeps its meaning, an ordered collection. `{K}V` makes no
such promise.

**What a loop gives you** — `for x in c`, and `x in c` with it — is the
half of the mapping that is *not known in advance*. That is the
information; the other half you already had.

- **Keys known in advance → the values.** `[Color]int` has exactly the keys
  `RED, GREEN, BLUE`, in that order, fixed by its type; listing them would
  say nothing the declaration did not. So `for x in score` gives the
  values, and `x in score` asks whether some colour has that score. A list
  and a fixed array are the same case: their keys are positions `0 .. n-1`,
  known from the length.
- **Keys not known in advance → the keys.** A `{str}int` holds whichever
  words happened to arrive, and *which* ones is exactly what you do not
  know. So `for w in counts` gives the words and `w in counts` asks "did
  this word occur?"; the value is reached through the key, `counts[w]`. A
  `[str]float` is the same, and gives its keys in the order they arrived.
- **A set is the limiting case.** `{}str` maps each element to present or
  absent; that half says nothing, so the keys — the elements — are all
  there is. Iterating a set gives them, and `x in s` tests them.

| | keys known in advance? | order | `for x in c`, `x in c` |
|---|---|---|---|
| `[]T`, `[N]T`, `[E]T`, `[lo..hi]T` | yes — positions, or the domain | positions / domain | the values |
| `[str]V`, `[(int, int)]V` | no | insertion | the keys |
| `{K}V` | no | none | the keys |
| `{}T` | no — the elements *are* the keys | none | the elements |

`.keys()`, `.values()` and `.items()` ask for the other half, or both.
`enumerate(c)` pairs each item with where it sits: `(position, element)`
for a list, `(key, value)` for every mapping — `(RED, 10)` for an `[E]T`,
`("zeta", 3.0)` for a `[str]float` or a `{str}float`. So the brackets say
whether there is an order; the key type says what a loop gives you.

```python
var totals: [str]float = {:}      # OrderedTable[string, float] / dict
totals["zeta"] = 3.0
totals["alpha"] = 1.0
for k in totals:
    print k                       # zeta, then alpha -- on both backends
for k, v in totals.items():
    print f"{k}={v}"              # zeta=3.0, alpha=1.0
assert "zeta" in totals           # a key: did "zeta" arrive?
```

Its literal is a dict's, `{"zeta": 3.0}` or `{:}`, or the keyed form
`["zeta": 3.0]`; the declaration makes it ordered. A tuple works as a key
like any other type: `[(int, int)]float` is a grid of floats, keyed by
coordinates in the order they were first set.

So the fixed array is not a special form: it is `[O]T` where the ordinal
type happens to be a subrange. The key may equally be written out
(`[0..9]int`), named (`type Idx is 0 .. 4`, then `[Idx]int`), or be any
other ordinal — `[bool]str`, `[Color]int`, `[char]int`. All of these work on
both backends.

`char` is an ordinal like the rest, spanning `chr(0) .. chr(255)`, so
`[char]int` is a 256-slot array. Adascript inherits Python's lack of a
character type, so `'a'` is a one-character *string* rather than a char —
the Nim backend narrows it to a char literal wherever a char is what the
declaration asks for, escapes included. That covers every position, not just
subscripts: a `let`/`var` with a `char` annotation, an assignment to one, a
`return`, the trailing expression of a `-> char` function, an element of a
`[]char` literal, a record field, and an argument to a parameter typed
`char`. So `freq['a']`, `freq["\\"]`, `let c: char = '\\t'` and
`is_digit_ch('7')` all work on both backends. `str(chr(n))` is the character
n as text, as in Python, for any n: `str(chr(233))` is `"é"` (UTF-8 on Nim,
where a bare `chr` past 127 would be one byte).

`char` is also a container element type in its own right. Iterating a string
yields characters, so a `[]char` annotation says what the loop already
produces, and `in` on two strings is a substring test:

```python
let cs: []char = [c for c in "abc"]      # ['a', 'b', 'c']
let digits: []char = [c for c in grid if c in "0123456789"]
print "b" in "abc"                       # True — substring, not membership
```

The empty literals fall out of the same split, which is what makes them easy
to keep straight: `{:}` carries the colon of a `key: value` pair, so it is
the empty **mapping** — a dict. Bare `{}` has no colon, so it is the empty
**collection** — a set.

Underneath, the two collections are mappings as well: a list maps its
positions to its elements, and a set maps its elements to in-or-out, which
is its characteristic function. That is why `xs[i]` and `x in s` are both
lookups, and why a set cannot hold the same element twice — a key is present
or absent, and there is no third state for "present twice". The four names
in the table are the useful level to think at; this is the reason they line
up as neatly as they do.

A pure function is the same idea taken one step further: `f(x)` is a lookup
too, mapping the argument to a result, and nothing about that mapping is
ordered — call it twice with the same argument and it owes you the same
answer both times, in whatever order you like. It is an **unordered
mapping**, kin to `{K}V` in spirit. It is still written with its own arrow,
`(T, U) -> R`, rather than inside the grid, because a declaration has to say
whether the mapping is *stored* — a table you can iterate, count and write
to — or *computed*, which you can only call; see below.

| Adascript        | Python                    | Nim                            |
|----------------|---------------------------|--------------------------------|
| `[]T`          | `list[T]`                 | `seq[T]`                       |
| `[N]T`         | `tuple[T, ...]`           | `array[N, T]`                  |
| `[*]T`         | `Sequence[T]`             | `openArray[T]`                 |
| `[E]T`         | `dict[E, T]`              | `array[E, T]` (enum-indexed)   |
| `[K]V`         | `dict[K, V]` (insertion order) | `OrderedTable[K, V]` (K not a finite ordinal) |
| `{K}V`         | `dict[K, V]`              | `Table[K, V]`                  |
| `{}T`          | `set[T]`                  | `HashSet[T]` or `set[T]`       |
| `?T`           | `T \| None`               | `Option[T]`                    |
| `T \| None`     | `T \| None`               | `Option[T]` -- the same as `?T` |
| `A \| B`        | `A \| B`                  | `OneOf2[A, B]` (a union)       |
| `T \| !F`       | `T \| F`                  | `Result[T, F]` (F a failure)   |
| `(T, U)`       | `tuple[T, U]`             | `(T, U)`                       |
| `(T, U) -> R`  | `Callable[[T, U], R]`     | `proc(a0: T, a1: U): R`        |

`?T` is shorthand for `T | None`: one type, spelled either way (or `None | T`).
`T | !F`, with F a record marked `!` in place of `None`, is a value or a failure
-- see [Failures as Values](#failures-as-values-t--f).

`?T` and `(T, U)` are not containers and stand outside the scheme. `[*]T`
is `[]T` with the length left to the caller — see below.

> **`{…}` means unordered on purpose, and the backends prove it.** Iterating
> the same `{str}int` gives insertion order on the Python backend and hash
> order on Nim:
>
> ```
> keys inserted:  zebra, apple, mango, kiwi, banana
> Python backend: zebra, apple, mango, kiwi, banana
> Nim backend:    zebra, kiwi, apple, mango, banana
> ```
>
> Sets diverge the same way. So a program that iterates a `{…}` type and
> depends on what comes out first is not portable between the two backends —
> sort the keys, or use an ordered form.
>
> `[]T`, `[N]T` and `[*]T` carry no such caveat: iterating them yields the
> values in position order on both backends. Nor does `[K]V` with any other
> key, `[str]float` say: it yields its keys in insertion order on both.
>
> `[E]T` included: it yields its values in enum order, whatever order the
> literal was written in, and `score[RED]` indexes it — its keys are the
> domain, known in advance, so the values are what a loop is for. On the
> Python backend it is a dict keyed by the members, which would otherwise
> have yielded, and tested with `in`, its keys; it gives its values
> instead, as the `array[E, T]` Nim compiles it to does.
>
> ```python
> type Color is enum RED, GREEN, BLUE, AMBER
> var score: [Color]int = [BLUE: 3, RED: 1, AMBER: 4, GREEN: 2]
> for v in score:  print v         # 1 2 3 4
> for c in Color:  print score[c]  # the same, by domain
> ```

Types compose freely:

```python
var words:    []str        = ["hello", "world"]
var counts:   {str}int     = {"hello": 1}
var maybe:    ?int         = None
var grid:     [][]float    = [[1.0, 2.0], [3.0, 4.0]]
var callback: (int) -> bool = my_predicate
```

A graph as an adjacency list is a `{…}` mapping whose values are a `[…]` collection:

```python
type Node_T is str
type Graph_T is {Node_T}[]Node_T

graph: Graph_T = {'A': ['B', 'C'], 'B': ['C', 'D']}
```

Add weights by making the element a named tuple, which is what `dijkstra.ady` does -- `{Node_T}[]Neighbour_T`, three levels in one line.

### Function types `(T, U) -> R`

A function type is written like a `def`'s signature: the parameter types in
parentheses, an arrow, the result.

```python
type Op_T is (int, int) -> int

def fold(op: Op_T, xs: []int, init: int) -> int:
    var acc: int = init
    for x in xs:
        acc = op(acc, x)
    return acc

def run(cb: () -> None):                  # no parameters, no result
    cb()

let p: (str) -> int | None = parse_digit  # returns an optional int
var steps: [](int) -> int = [inc, inc]    # a list of functions
var check: ?(Point) -> bool = None        # an optional function
```

`(int) -> int` and `(int,) -> int` are one type; so are `() -> R` and
`(,) -> R`. The result is a whole type, as after a `def`'s `->`: `?` in
front of the parameters makes the function optional, `?` after the arrow
makes its result optional. Python gets `Callable[[int, int], int]`, Nim
`proc(a0: int, a1: int): int`. A union of functions needs a name.

> **Why not `{(int, str)}bool`?** A pure function *is* an unordered mapping,
> so `{…}` would be the consistent spelling — but it is taken, and not by
> accident: `{(int, str)}bool` is also a dict keyed by a tuple, a real type
> with real uses (`var poisson_cache: {(int, int)}float = {:}` in
> `EXAMPLES/jacks_car_rental/jacks.ady` is a memo table). The transpiler cannot pick one
> from context: a parameter, a field or a return type carries no value to
> look at, and the two admit different operations — a table can be
> iterated, counted, tested with `in` and written to; a function can only be
> called, but over a domain no table could hold. A declaration has to say
> which it is. The arrow says it the way every signature already does.
>
> `[(int, str)]bool` meant the function type until this change. It is now
> what the ordered scheme says it is: a mapping keyed by `(int, str)`, in
> insertion order.

#### Reading nested arrows

A function type can take or return another function, and three rules keep
that unambiguous:

- **The arrow groups to the right.** `(int) -> (int) -> int` takes an int
  and returns a function from int to int.
- **Parentheses before an arrow are always a parameter list.** There is no
  parenthesized type on its own, so a function that *takes* a function puts
  it inside the parameter list: `((int) -> int) -> int`. Without an arrow,
  `(int, int)` is a tuple, so `(int, int) -> (int, int)` returns a pair.
- **In a `def`, the first `->` is the `def`'s.** Its parameters have names,
  so `def pick(name: str) -> (int, int) -> int:` returns a function.

| Written | Means | Nim |
|---|---|---|
| `(int) -> (int) -> int` | returns a function | `proc(a0: int): proc(a0: int): int` |
| `((int) -> int) -> int` | takes a function | `proc(a0: proc(a0: int): int): int` |
| `(int) -> int \| None` | returns an optional int | `proc(a0: int): Option[int]` |
| `?(int) -> int` | an optional function | `Option[proc(a0: int): int]` |
| `(int) -> ?int` | returns an optional int | `proc(a0: int): Option[int]` |

The last three are where a reader slows down: the arrow reaches as far
right as it can, so a `|` after it belongs to the result, and a `?` in front
covers the whole function. Past one level of nesting, name the inner type:

```python
type Op_T is (int, int) -> int
def pick(name: str) -> Op_T:
```

### Open arrays `[*]T`

`[*]T` maps to Nim's `openArray[T]`: a read-only view that the caller can
satisfy with either a `[]T` (seq) or a `[N]T` (fixed array). Use it for
function parameters that only read their argument — Nim handles the
unification automatically:

```python
def total(xs: [*]float) -> float:
    var s: float = 0.0
    for x in xs:
        s = s + x
    return s

var a: []float  = [1.0, 2.0, 3.0]
var b: [3]float = [1.0, 2.0, 3.0]
print(total(a))   # seq — ok
print(total(b))   # fixed array — ok
```

`[*]T` is only valid in **parameter and return annotations** — not in
variable declarations.

The same with ints, and the Nim it compiles to:

```python
def sum_values(xs: [*]int) -> int:
    var total: int = 0
    for x in xs:
        total = total + x
    return total

var a: []int  = [1, 2, 3]
var b: [3]int = [1, 2, 3]
print(sum_values(a))   # seq argument -- ok
print(sum_values(b))   # fixed array argument -- ok
```

**Nim output:**

```nim
proc sum_values(xs: openArray[int]): int =
    var total: int = 0
    for x in xs:
        total = total + x
    return total
```

Callers never need to do anything special: Nim passes both a seq and an array to an `openArray` parameter automatically.

### Empty collection literals

Adascript uses distinct syntax for empty dicts and empty sets, resolving
Python's ambiguity where `{}` means an empty dict:

| Literal | Meaning      | Python output | Nim output                  |
|---------|--------------|---------------|-----------------------------|
| `{:}`   | empty dict   | `{}`          | `initTable[K, V]()`         |
| `{}`    | empty set    | `set()`       | `initHashSet[T]()` or `{}`  |

```python
var counts:  {str}int = {:}    # empty dict
var visited: {}str    = {}     # empty HashSet
var flags:   {}bool   = {}     # empty ordinal set
```

**Nim output:**

```nim
import tables, sets
var counts:  Table[string, int] = initTable[string, int]()
var visited: HashSet[string]    = initHashSet[string]()
var flags:   set[bool]          = {}
```

For sets, the Nim backend uses the type annotation to pick between
`initHashSet` (heap-allocated, any T) and `{}` (Nim ordinal set for
`bool`, `char`, `byte`, small integers, and user-defined enums).

### Float infinities

`Inf`, `NegInf` and `NaN` are float literals on both backends, so an
"unreachable" or "not yet measured" distance needs no sentinel constant and
no `?float` wrapper — it compares and arithmetises like any other float:

```python
var dist: {str}float = {n: (0.0 if n == start else Inf) for n in graph}
if candidate < dist[node]:            # Inf loses every comparison
    dist[node] = candidate
```

They pass through to Nim as `Inf`, `NegInf` and `NaN`, and become
`float("inf")`, `float("-inf")` and `float("nan")` in Python — no import is
needed on either side. `NaN` keeps IEEE semantics on both, so `NaN != NaN`
is true.

Note that the two backends part company on division by zero: Nim's
`1.0 / 0.0` evaluates to `Inf`, while Python raises `ZeroDivisionError`.
Write `Inf` when you mean it rather than computing it.

### Name the type, not its representation

Bare `int`, `float` and `str` are discouraged wherever the value means
something more specific than "a number" or "some text". They say how a value
is stored, not what it is. Give it a named type instead:

```python
# bare: what goes in, what comes out?
def format_dates_bare(epochs: []int) -> {int}str:

# named: the signature is the documentation
# seconds since 1970-01-01 UTC
type Epoch is int
# an Epoch as the date column prints it: YYYY.MM.DD
type DateStamp is str

def format_dates(epochs: []Epoch) -> {Epoch}DateStamp:
```

Why:

- **The signature explains itself.** `[]int -> {int}str` could be anything;
  `[]Epoch -> {Epoch}DateStamp` can only be one thing. A reader, a reviewer
  and a grep for `Epoch` all find the meaning without opening the body.
- **Nested containers become readable.** `{str}[]int` says nothing about
  what is keyed by what. `{TargetKey}{LineNo}[]HitIndex` reads as "for each
  target, for each line, the hits that asked for it". Naming the parts often
  shows a better shape, too. Here, one table keyed by glued strings like
  `"<target>\x02<line>"` became a table per target, keyed by line:

  ```python
  var owners_bare: {str}[]int = {:}                  # keyed by "<target>\x02<line>"
  var owners: {TargetKey}{LineNo}[]HitIndex = {:}   # the hits that asked for each line
  ```

- **The unit or format is written down once.** The comment on
  `type Epoch is int` says "seconds since 1970, UTC" for every use, instead
  of a comment at each field and parameter, or none.
- **The representation can change in one place.** If `Epoch` has to become
  a `float`, only its declaration changes.
- **It costs nothing.** A named scalar type is a plain alias on both
  backends (`type Epoch = int` on Nim, `Epoch = int` on Python), so no
  conversion is needed in or out:

  ```python
  let e: Epoch = 1700000000
  let n: int = e + 1
  ```

A bare type is still right when the value only counts or indexes and means
nothing more: a length, a column width, a string offset, a loop index, text
that is just text.

```python
var widths: []int = []
for s in ["ab", "abc"]:
    widths.append(len(s))
```

A rule of thumb: if you would write a comment next to a declaration to say
what its `int` or `str` holds, name the type and put the comment there.

Both naming styles appear in the examples: a `_T` suffix (`Velocity_T`,
`Node_T`) and a plain name (`Epoch`, `LineNo`). Pick one per program. A class
never takes the suffix, whichever style: it is named for the thing it is --
`Report`, `Baseline`, `Flight`.

### A place on disk is a `Path`

The same rule, for its commonest case: a directory or a file is a `Path`,
not a `str` joined with `"/"`. Make it one where it enters the program —
from an argument, an environment variable, a line of `ls` output — and
join with `/`:

```python
# rather than
let work: str = root + "/" + sub
if -e (work + "/.git"): ...

# write
let work: Path = Path(root) / sub
if -e (work / ".git"): ...
```

Why:

- **The signature says it is a place.** `def checked_out(dir: Path)` cannot
  be read as taking a name, a pattern or a line of text.
- **A string cannot slip in by mistake.** `Path` is a distinct type, so
  `let p: Path = s` does not compile; `Path(s)` is how you mean it.
- **There is no slash to get wrong.** No doubled or missing `/`, and
  `.parent`, `.name`, `.resolve()`, `.relative_to(base)` (a `Path | !PathFailure_T`), `.mkdir()` (a `None | !PathFailure_T`), `.read_text()`, `.read_lines()` and `.write_text(s)` (the file, each with a `PathFailure_T` for what goes wrong) and the file tests are there
  when you need them.
- **It reads itself.** `for line in p.lines:` opens the file, yields its
  lines without their newlines and closes it -- no `open()`, no
  `readFile(p).split("\n")`.

What stays a `str` is what is not a place on this disk: a relative path as
another tool reports it (a file in a changes report, a sparse-checkout
pattern), a URL, a value handed to a program that resolves it itself. Where
an API takes strings, convert at the call: `run(["rmdir", str(work)])`.
Go up with `.parent` rather than `/ ".."`, which the two backends print
differently (see `TODO.md`). The section on [Paths: `Path` and `/`](#paths-path-and-) has the
operations.

### Text beyond ASCII: bytes on Nim, characters on Python

A `str` is UTF-8 bytes on Nim and a string of characters on Python. For
ASCII text the two are the same; past it, `len(s)`, `s[i]`, a slice and
`for c in s` count and give bytes on Nim and characters on Python: `len("été")`
is 5 on Nim and 3 on Python. A program that must agree on both backends over
such text compares and searches whole strings (`==`, `in`, `.find`,
`.split`, `.startswith`), which agree, and leaves counting and indexing to
ASCII text. `str(chr(n))` is the one character n on both.

---

## Type Declarations

### Enums

```python
type Color   is enum RED, GREEN, BLUE
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are accepted as the assignment keyword.

**Python output:** `class Color(Enum): RED = 0; GREEN = 1; BLUE = 2` (members compare, by value)
**Nim output:** `type Color = enum RED, GREEN, BLUE`

A member can be given its value -- key codes, exit codes, protocol numbers:

```python
type Key_T   is enum DOWN = 258, UP = 259, LEFT = 260, RIGHT = 261
type Level_T is enum:           # or one NAME = value to a line
    LOW  = 1
    MID  = 2
    HIGH = 3
```

Either every member has a value or none does -- a mix is refused -- and the values must
ascend: they give the order, so `ord(UP)` is `259`, `DOWN < UP`, and `case` and sets follow
them. Values that follow one another (`1, 2, 3`) leave the enum as good as any other; values
that skip a number still order, compare and `case`, but cannot index an array (`[E]T`), be
iterated or be stepped with `'Next` and `'Prev`, which Nim refuses for them too, and
Adascript says so on both backends. `parse_enum(Key_T, 259)` is `UP`, and 260 a failure.

A member stringifies as its bare name on both backends — `str(d)`, `print
d`, `f"{d}"` and `d'Image` all give `Door1`, which is what Nim's `$` gives.
So does a list of them: `print xs` over a `[]Door_T` gives `[Door1, Door2]` on
both (a list prints Python's way on Nim, `[1, 2]` and `['a']`, not `@[1, 2]`).

Enums integrate tightly with arrays, `case` and tick attributes -- see [Collections](#collections), [Case / When Statements](#case--when-statements) and [Tick Attributes](#tick-attributes).

### Subranges

Subrange types constrain a base type to a value range. The `..` operator is
inclusive; `..<` excludes the upper bound:

```python
type SmallInt  is 0 .. 255     # values 0–255
type Index     is 0 ..< 10     # values 0–9
type Positive  is 1 .. 1000
```

The explicit `int range` form is a synonym for the bare subrange and generates identical output:

```python
type Age is int range 0..100   # same as: type Age is 0..100
```

**Python output:** `int` (a type alias)  
**Nim output:** a native Nim range type with compile-time bounds checking

#### Float subranges

For floating-point ranges use `float range lo .. hi` (the bounds may be negative). It is a float with a stated range, and still mixes with floats. Write `distinct float range lo .. hi` when it should also be a unit of its own: it does not mix with a float, or with another range. When the range narrows a unit that already exists -- a latitude is a `Degree_T` in `-90 .. 90` -- say so with `type Latitude_T is Degree_T range -90 .. 90` (see [A unit narrowed to a range](#a-unit-narrowed-to-a-range)): it goes up to its parent without a cast.

```python
type Temperature is float range 0.0 .. 100.0
type Probability  is float range 0.0 .. 1.0

def measure() -> Temperature:
    var t: Temperature = 36.6
    t += 1.0
    t = 98.5
    return t
```

**Nim output:**

```nim
type Temperature = float
type Probability  = float

proc measure(): Temperature =
    var t: Temperature = 36.6
    assert t >= 0.0 and t <= 100.0, "Temperature value " & $t & " out of range [0.0, 100.0]"
    t += 1.0
    assert t >= 0.0 and t <= 100.0, "Temperature value " & $t & " out of range [0.0, 100.0]"
    t = 98.5
    assert t >= 0.0 and t <= 100.0, "Temperature value " & $t & " out of range [0.0, 100.0]"
    return t
```

The range constraint is stored in the symbol table and checked after **every assignment** to a variable of that type — matching Ada's constraint model. The type is a plain `float` alias (not `distinct`), so all arithmetic operators work without casts.

`Temperature'First` and `Temperature'Last` give the bounds.

### Distinct types and units

A named type is an alias. It documents the meaning but does not enforce it,
so mixing up two of them still compiles:

```python
type Velocity_T is float     # knots
type Distance_T is float     # nautical miles

let v: Velocity_T = 250.0
let d: Distance_T = v        # compiles on both backends: an alias, not a type
```

`distinct` closes that gap. A distinct type has its base type's values and
operations, and mixes with nothing else:

```python
type Distance_T is distinct float     # nautical miles
type Duration_T is distinct float     # hours

var d: Distance_T = 600.0        # a literal takes the declared type
d += 10.0                        # and the type of what it is added to
let t: Duration_T = Duration_T(2.0)   # in with Duration_T(x), out with float(t)
print f"{d:.1f} nm"              # 610.0 nm
let wrong: Duration_T = d        # refused, on both backends
```

- **Operations** are the base type's, closed over the new one:
  `Distance_T + Distance_T` is a `Distance_T`, comparisons, `max`, `abs`
  and `+=` work. A distinct `str` has `+` and `len`; a distinct `int` has
  `//` and `%`.
- **Conversions** are explicit: `Distance_T(x)` in, `float(d)` out.
- **Literals** take the type of their context: a declaration, assignment,
  return, argument or record field of the type, or the other operand of `+`,
  `-` or a comparison. A *variable* of the base type does not -- write
  `Distance_T(f)`.

**`*` and `/` scale.** Knots times knots is not knots, so they do not mean
what `+` means:

- a distinct value times, or over, a plain number is that unit --
  `d * 2.0`, `2.0 * d`, `d / 4.0`, `d * n` for an `int` count `n` -- and the
  number stays a number;
- two of the same unit divided are a plain `float`: a ratio has no unit;
- two of them multiplied are refused: there is no "miles squared" unless you
  declare one; and a unit times another unit has no meaning until you say.

That makes money a natural `distinct int` in cents: `price * 3` scales it,
and `price * quantity` needs a unit to be a total, below.

**Units made from units** are declared, and the declaration defines the
operators between them:

```python
type Distance_T is distinct float     # nautical miles
type Duration_T is distinct float     # hours
type Velocity_T is Distance_T / Duration_T    # knots

def travelled(v: Velocity_T, t: Duration_T) -> Distance_T:
    return v * t                      # Velocity x Duration is a Distance

def eta(d: Distance_T, v: Velocity_T) -> Duration_T:
    return d / v                      # Distance / Velocity is a Duration

let v: Velocity_T = d / t             # Distance / Duration is a Velocity
```

`type C is A / B` says A / B is a C, so C * B and B * C are an A, and A / C
is a B. `type C is A * B` says A * B and B * A are a C, so C / A is a B and
C / B an A -- `type Area_T is Length_T * Length_T`, `type Total_T is
Cents_T * Qty_T`. Beyond what a declaration says, units relate by
dimension: two units multiplied or divided are the one declared unit with
that dimension, so with `Force_T is Mass_T * Accel_T` and `MassFlow_T is
Mass_T / Duration_T` declared, `force / speed` is a `MassFlow_T` with no
declaration naming that pair. A result of no dimension is a plain number, and
one two declared units share is refused with both named. Everything else
between the units is refused: `d * t`, `v + d`, `1.0 / t` (unless `1.0 / t` is a
declared reciprocal, below). A unit of no
dimension is the ratio it is, `type Radians_T is Length_T / Length_T`, and
scales a length into a length. A unit raised to a whole number written out
is the unit of that dimension: `side ** 2` for a `Length_T` side is an
`Area_T`, and a power no declared unit has is refused, saying what to
declare. A derived unit can be made from another (`type Accel_T
is Velocity_T / Duration_T`) and has the kind of its operands: `float`, or
`int` for a product. Nim gets a small proc per relation, so it costs nothing
at run time.

A multiple of a unit is declared once, as what one of it is: `type
Kilometers_T is 1000.0 * metre_T`. The conversion then does the scaling
itself, both ways: `Kilometers_T(d)` of a `metre_T` d divides by 1000, and
`metre_T(k)` of a `Kilometers_T` k multiplies, so `float(metre_T(k))` is the
number of metres, never `float(k) * 1000.0`. Of a plain number the
conversion keeps the number; of an unrelated unit it is refused (book 2.7,
"A multiple of a unit").

**A point on a scale is not an amount.** Celsius and Fahrenheit are not
multiples of the kelvin: their zero is somewhere else, so they are declared
as the offset they are, and a scale can be declared from another:

```
type Kelvin_T     is distinct float
type Celsius_T    is Kelvin_T - 273.15
type Fahrenheit_T is 1.8 * Celsius_T + 32.0

let boil: Celsius_T = Celsius_T(100.0)
let f: Fahrenheit_T = Fahrenheit_T(boil)         # 212.0
let k: Kelvin_T = Kelvin_T(boil)                 # 373.15
let rise: Kelvin_T = boil - Celsius_T(20.0)      # a difference is a change
let warmer: Celsius_T = boil + Kelvin_T(2.0)     # a change moves a point
```

The conversions work between any two of the scales, and of a plain number
they keep the number. What the language refuses is arithmetic that looks
harmless and is wrong, and the reason is worth knowing:

- **`c + c`** (20 C + 10 C). The zero of Celsius is arbitrary, so the sum
  depends on where you put it: 20 C and 10 C are 293.15 K and 283.15 K, which
  add to 576.3 K -- not the 30 C you meant. Two *points* have no sum. Their
  *difference* is meaningful, a change of 10 kelvin, so `c1 - c2` is allowed
  and is a `Kelvin_T`.
- **`c * 2.0`** (twice as hot). 20 C is not "twice" 10 C: double the kelvin
  and 20 C becomes 313 C, double the Fahrenheit and it becomes something
  else. The answer depends on the scale the number was written in, so a
  point has no multiple. An *amount* does: `Kelvin_T(10.0) * 2.0` is fine.
- **`c + 1.0`**. One degree is one kelvin on the Celsius scale and 1.8 on the
  Fahrenheit one. A bare number does not say which change it is, so write
  the change: `c + Kelvin_T(1.0)`.
- **`c + f`** mixes two scales: convert one, `c + Celsius_T(f)`. And **`k - c`**
  takes a point from a change, which has no meaning (`c - k` is fine).

Points on a scale compare, `c1 < c2`, since that is just order.

**The reciprocal of a unit** is declared as one over it:

```
type Second_T is distinct float
type Hertz_T  is 1.0 / Second_T

let period: Second_T = 0.02
let freq: Hertz_T = 1.0 / period                 # 50 Hz
let cycles: float = freq * Second_T(0.1)         # 5.0: a plain number
let back: Second_T = 1.0 / freq                  # 0.02
```

A number over a `Second_T` is a `Hertz_T`, a number over a `Hertz_T` is a
`Second_T`, and the two multiplied are the plain number of cycles. A
`Hertz_T` is a unit like any other, and joins the dimension rules above:
`Metre_T * Hertz_T` is the speed if one is declared. The standard `units`
module has `celsius_T`, `fahrenheit_T` and `hertz_T` ready made. Book 2.7
has the details.

### A unit narrowed to a range

A distinct type can be narrowed to part of its values, in the manner of an Ada subtype, with `type N is P range lo .. hi` -- `P` any distinct float or int, the bounds negative if need be. The result is a type of its own, with a relation to its parent: it goes up, comes down only by an explicit conversion that checks the range, and does not stand for a sibling:

```python
type Degree_T is distinct float
type Latitude_T is Degree_T range -90 .. 90
type Longitude_T is Degree_T range -180 .. 180

let lat: Latitude_T = Latitude_T(45.5)
let wide: Degree_T = lat                  # up to the parent: no cast
let sum: Degree_T = lat + Degree_T(1.0)  # arithmetic is the parent's
let back: Latitude_T = Latitude_T(sum)     # down: checked
let lat2: Latitude_T = 12.5                # a literal takes the declared type, checked
```

- A narrowed type goes up to its parent, and to the parent's parents, wherever the parent is wanted -- a `Degree_T` parameter takes a `Latitude_T`, and `Radians_T(lat)` of a scaled unit converts it. `Degree_T(lat)` is allowed too, if you like to say so.
- It comes down by `Latitude_T(d)`, from a `Degree_T` or a plain number: out of range, that raises `AssertionError` (Nim: `AssertionDefect`, which `except AssertionError` catches). It is never silent, and never skipped in a release build.
- It does not stand for a sibling: `let l: Latitude_T = lon` and `Latitude_T(lon)` are refused, and so is a `Longitude_T` passed where a `Latitude_T` is declared -- the point of two types, that `GeoPoint(lon, lat)` is an error.
- Arithmetic leaves the range, so it is the parent's: `lat + lat` is a `Degree_T`, to be converted back to be stored in a `Latitude_T`. Comparisons, `min`, `max`, `print` and f-string formats work on the narrowed type as they do on its parent.
- Python: `class Latitude_T(Degree_T)`, whose constructor checks the range. Nim: a `distinct float` with a converter up and a checking `to_Latitude_T` that `Latitude_T(x)` is emitted as.

It is a unit with a range, where `distinct float range lo .. hi` (see [Float subranges](#float-subranges)) is a unit of its own that has no parent. Use the narrowing when there is a parent to go up to.

<!-- tested by TESTS/test_narrowed_type.ady -->

### A type that wraps: `mod`

Where a range type refuses a value outside it, a mod type wraps it back in. `type Slot_T is mod 8` is a whole number that is always 0 .. 7, and `type Bearing_T is Degree_T mod 360` is a `Degree_T` that is always 0 .. 360 -- a compass bearing, an angle, a clock hand, a ring-buffer index. Making one, and `+`, `-` and `*` on it, wrap:

```python
type Slot_T is mod 8
type Degree_T is distinct float
type Bearing_T is Degree_T mod 360

var s: Slot_T = Slot_T(6)
s = s + Slot_T(1)                          # 7
s = s + Slot_T(1)                          # 8 wraps to 0
print(int(Slot_T(-1)))                     # 7

let b: Bearing_T = Bearing_T(-10.0)        # 350.0
let turned: Bearing_T = b + Degree_T(30.0)   # 380 wraps to 20.0
let wide: Degree_T = b                    # up to the parent: no cast
```

- The modulus may be a `const`, declared with its type: `const CAPACITY: int = 100` and `type Index_T is mod CAPACITY` make a ring-buffer index, `buffer[int(i)]` with `i = i + Index_T(1)` coming round to 0 after 99. An `int` const makes a whole-number type and a `float` one a float type; the name of anything else is refused.
- A ring buffer is the usual use. The index is a mod type, so it comes round by itself, and it is the array's index type too: `[Index_T]int` has `CAPACITY` slots, indexed 0 to `CAPACITY - 1`, and needs no `int(...)` to index it:

```python
const CAPACITY: int = 4
type Index_T is mod CAPACITY
type Count_T is int range 0 .. CAPACITY      # how many are held: 0 to CAPACITY, one more than an index

class Ring:
    var items: [Index_T]int
    var head: Index_T                  # a mod type starts at 0
    var tail: Index_T
    var count: Count_T

    def push(self, x: int):
        self.head += 1                 # a literal is an Index_T; it comes round at CAPACITY
        self.items[self.head] = x      # head is the newest slot
        if self.count == CAPACITY:
            self.tail += 1             # full: the oldest is overwritten
        else:
            self.count += 1

    def pop(self) -> ?int:
        if self.count == 0:
            return None
        self.tail += 1                 # tail is the slot last read
        self.count -= 1
        return self.items[self.tail]

    def latest(self, back: Index_T) -> int:
        return self.items[self.head - back]         # back = 0 is the newest
```

  After six pushes of 10, 20, ... 60 into this four-slot ring, `latest(0)` is 60 and `latest(3)` is 30. The count is not an `Index_T`: it runs from 0 to `CAPACITY`, one more value than an index has, so it is an `int range 0 .. CAPACITY`. `CAPACITY` appears twice, in the two types, there is no `% CAPACITY` anywhere, and `head - Index_T(1)` is the newest slot even when `head` is 0. This is `TESTS/test_ring_buffer.ady`.
- The value wraps with the sign of the modulus, as Python's `%` does, on both backends: `Slot_T(-1)` is 7, not -1.
- `Slot_T` has no parent: it is a type of its own, and a plain `int` is given to it by `Slot_T(n)`. `Bearing_T` has `Degree_T`: a `Bearing_T` goes up to it without a cast, `bearing + degrees` is a `Bearing_T`, and a `Degree_T` comes down only by `Bearing_T(d)`, which wraps it. A literal takes the declared type, wrapped: `let c: Bearing_T = 400.0` is 40.0.
- `*` by a plain number gives the same type, wrapped; `/` by a plain number does too, and `Bearing_T / Bearing_T` is a plain ratio. Comparisons compare the wrapped values.
- It is refused beside a sibling, as a narrowed type is, and `bearing + 1.0` mixes a unit with a plain number as it does for any unit.
- A mod type wraps and never raises. Use `range` when a value outside should be an error, and `mod` when it should come round.
- Python: `class Bearing_T(Degree_T)`, whose `__new__` and operators wrap. Nim: a `distinct float` with a `to_Bearing_T` that wraps with `floorMod`, wrapping operators, and a converter up.

<!-- tested by TESTS/test_mod_type.ady -->

### A unit made from a unit: momentum and energy

Energy is mass times velocity times velocity, but a derived unit combines
two units, and the product evaluated first, mass times velocity, would have no
name. So name it; momentum is a real quantity and the two-step form reads
better:

```python
type Mass_T     is distinct float          # kg
type Speed_T    is distinct float          # m/s
type Momentum_T is Mass_T * Speed_T        # kg m/s
type Energy_T   is Momentum_T * Speed_T    # joules

def kinetic(m: Mass_T, v: Speed_T) -> Energy_T:
    return 0.5 * m * v * v        # a scale, then two units

let p: Momentum_T = m * v
print p / m                       # a Momentum over a Mass is a Speed
print kinetic(m, v) / v           # an Energy over a Speed is a Momentum
```

`type Energy_T is Mass_T * Speed_T * Speed_T` is refused, and the message
says how to split it. The ½ scales for free. `m * (v * v)` is refused too,
because `Speed_T * Speed_T` has no unit unless one is declared; declare
`type SpeedSq_T is Speed_T * Speed_T` and `m * (v * v)` is an `Energy_T` too,
by dimension. It is all in `TESTS/test_units.ady` and
`TESTS/test_units_dims.ady`.

### Money: `Dollar_T`, and converting to `Euro_T`

Money is the commonest use of `distinct`, and needs nothing beyond what is
above. A dollar amount is not a number: it cannot be added to euros or
squared, but it scales by a quantity, a tax rate or a discount, all plain
numbers. An exchange rate is a unit of its own, euros per dollar, and
declaring it is what lets the conversion routines type-check:

```python
type Dollar_T is distinct float
type Euro_T   is distinct float
type Rate_T   is Euro_T / Dollar_T        # euros per dollar

const Max_Allowed_Quantity: int = 100
type Quantity_T is 0 .. Max_Allowed_Quantity   # never negative, never absurd

let unit_price: Dollar_T = 19.99
let quantity: Quantity_T = 3
let subtotal: Dollar_T = unit_price * quantity   # a count scales a price
let tax: Dollar_T = subtotal * 0.08              # so does a tax rate
let total: Dollar_T = subtotal + tax
print f"{total:.2f}"                             # 64.77

def to_euro(amount: Dollar_T, rate: Rate_T) -> Euro_T:
    return amount * rate          # Dollar x (Euro / Dollar) is Euro

def to_dollar(amount: Euro_T, rate: Rate_T) -> Dollar_T:
    return amount / rate          # Euro / (Euro / Dollar) is Dollar

let rate: Rate_T = 0.92
print f"{to_euro(total, rate):.2f} EUR"           # 59.59
print f"{to_dollar(to_euro(total, rate), rate):.2f}"   # 64.77, and back
```

A count is not a bare `int` either. `quantity` above is a `Quantity_T`, a
range of its own -- or a `Natural` where there is no top -- so a negative or
absurd quantity is a bug the program stops at, not a total that quietly
comes out wrong. On Nim `let q: Quantity_T = 101` does not compile and a
computed one, `q -= 5` below zero, stops at that line; the Python backend
keeps a plain `int` for a range and does not check it.

What it refuses is what goes wrong in real code:

```python
total + to_euro(total, rate)      # dollars plus euros
total * total                     # dollars squared
let e: Euro_T = total / rate      # the rate applied the wrong way round
let fee: Dollar_T = tax_rate      # a plain number is not money
```

Format money with `:.2f`. Amounts you must add up exactly are better held
as a `distinct int` in cents (`Cents_T`); a rate is a float, so a conversion
between the two is written out, where you decide how to round.
`TESTS/test_money.ady` is a whole order: lines, tax, a discount, a
budget, and each line converted.

Where it is checked: the Nim compiler checks every use. The Python backend
works out the unit of arithmetic over typed names -- `v * 2.0 + d` is a
`Velocity_T` plus a `Distance_T` -- and refuses it, or a declaration or
assignment of another type; a wrong argument is caught by building for Nim.

Use `distinct` where a mix-up would be a bug the compiler should catch:
units (metres vs feet, knots vs km/h), and IDs of different things that
share a representation (a user ID vs an order ID, both `int`). Keep a
plain alias where the point is readability, and the value is meant to mix
freely with its base type (an `Epoch` added to a number of seconds).

Other types that enforce a distinction:

- An **enum** is its own type.
- A **subrange** (`type Age is 0 .. 150`) is checked against its bounds, on
  Nim only. On Python it is a plain `int`.
- A **record** is nominal.
- `?T` is not `T`.
- `Path` is a distinct string: `let p: Path = s` is an error, and `Path(s)`
  is how you convert.

`DOCS/WHY_ADASCRIPT.md` makes the longer argument for naming types.

### What a unit becomes

**Nim output:** `type Velocity_T = distinct float`, the operations of `float`
borrowed for `+`, `-` and comparisons, and a small proc for each thing the
declarations define (`proc `/`(a: Distance_T, b: Duration_T): Velocity_T`),
so a unit costs nothing at run time. **Python output:** `class Velocity_T(float):
__slots__ = ()`.

A unit library
tracks every base unit's exponent for you; this asks you to name the
combinations you use, which is what a program has to do anyway, and every
one of them has a name a reader can search for.

### Named Tuples

Declare named tuples with `type … is tuple:` and a body of annotated fields:

```python
type Point is tuple:
    x: float
    y: float

type Neighbour_T is tuple:
    distance: float
    neighbor: Node_T
```

Construct them with `(field: value)` syntax:

```python
p = Point(x: 1.0, y: 2.5)
n = Neighbour_T(distance: 3.7, neighbor: 'B')
```

**Python output:** `Point(x=1.0, y=2.5)` (using `NamedTuple`)  
**Nim output:** `(x: 1.0, y: 2.5)` (structural tuple literal)

Destructure with `let`:

```python
let (dist, node) = queue.pop()
```

Named tuple literals work anywhere — inside collections, as function arguments,
and as fringe elements in priority queues:

```python
fringe.push((stage: STAGE1, budget: float(CAPITAL)))
```

### Records (Dataclasses)

```python
type Person is record:
    name: str
    age:  int
```

**Python output:** `@dataclass class Person: …`  
**Nim output:** `type Person = object`

A record (or tuple) of a single field fits on the line of its `type`, the way
`if c: stmt` does; `pass` stands for no fields at all:

```python
type Num_T is record: num: float
type Nil_T is record: pass
```

It means exactly the two-line form. A record with two or more fields takes
the indented block.

### Copied on Nim, shared on Python

A record is a **value** on the Nim backend and a **reference** on the Python
one. Assigning it to another name, appending it to a collection, passing it
to a function or storing it in another object's field copies it on Nim; on
Python all of those share the one object. The difference shows as soon as
the value is changed through one name and read through another:

```python
type Pos_T is record:
    x: int = 0

var a: Pos_T = Pos_T()
var b: Pos_T = a        # Nim: a copy of a.  Python: a itself.
b.x = 5
print a.x               # Nim: 0   Python: 5
```

A plain `class` and a `[]T` follow the same rule. To get one answer on both
backends:

- **Do not change a value that another name also holds.** Build what you
  need and hand it over, or change it before anyone else has it. Most
  programs already work this way.
- **Make the copy yourself** when you need an independent value:
  `var b: Pos_T = Pos_T(x=a.x)` is a new record on both backends.
- **Make it shared on both** when several names must see the same changes:
  a `@virtual class` is a reference on Nim too (see [`@virtual`](#virtual--enabling-cross-module-subclassing)).

Chapter 13 §13.2 of the book has the full account.

### Discriminated Records (Variant Types)

When the set of fields depends on a tag, use Ada-style discriminated records.
The discriminant goes in parentheses after the type name:

```python
type Shape_Kind is enum Circle, Rectangle

type Shape (Kind : Shape_Kind) is record:
    case Kind is
        when Circle:
            Radius : float
        when Rectangle:
            Width  : float
            Height : float
```

**Nim output** — a native variant object:

```nim
type Shape = object
  case Kind: Shape_Kind
  of Circle:
    Radius: float
  of Rectangle:
    Width, Height: float
```

**Python output** — flattened dataclass with `None` defaults:

```python
@dataclass
class Shape:
    Kind:   Shape_Kind
    Radius: float = None
    Width:  float = None
    Height: float = None
```

**Bare literals** — the kind alone builds a value, and matches in a pattern:

```python
type Val_T (kind: Val_Kind_T) is record:
    case kind is
        when VNum:
            num: float
        when VNil:
            pass                       # a kind that carries nothing
        ...

let a: Val_T = VNum(3.0)               # Val_T(kind=VNum, num=3.0)
let b: Val_T = VNil()                  # Val_T(kind=VNil)
case items:
    when [VSym("if"), test, *rest]:    # Val_T(kind=VSym, sym="if")
        ...
```

Arguments fill the fields of that kind in the order declared, or name them
(`VLambda(lam=f)`); too many, or a positional one after a named one, is
refused. A bare `VNil` (no parentheses) is still the enum member, so
`x.kind == VNil` reads as before. A kind that two variant records share, or
that the file also defines as a function, class or type, is not rewritten.
The rewrite is textual and runs before the parse, in both backends; it does
not see a variant declared in another module.

---

## Collections

The container types are introduced under [Type Annotations](#type-annotations); this section shows what to do with them. A union (`A | B`) and a value-or-failure (`T | !F`) have their own sections, [Unions](#unions-a--b) and [Failures as Values](#failures-as-values-t--f).

### Sequences `[]T`

```python
var words:  []str  = ["hello", "world"]
var matrix: [][]float = [[1.0, 2.0], [3.0, 4.0]]

words.append("!")
print(len(words))
```

### Hash tables `{K}V`

```python
var counts: {str}int = {:}
counts["apple"] += 1

for key, val in counts.items():
    print(f"{key}: {val}")
```

### Sets `{}T`

The type annotation drives the Nim backend: ordinal types (bool, char,
byte, small int, enum) use Nim's efficient bitset; other types use `HashSet`.

```python
var visited: {}str    = {}          # HashSet[string]
var flags:   {}bool   = {}          # set[bool] (bitset)
var seen:    {}Door_T = {}          # set[Door_T] (bitset)

visited.add("node_A")
if "node_A" in visited:
    print("already seen")
```

Python's operators work on both kinds: `a & b` (intersection), `a | b`
(union), `a ^ b` (symmetric difference), `a - b` (difference), and the
augmented forms `seen |= more`. Nim spells them `*`, `+`, `-+-` and `-`; the
emitter picks from the operand types, so the same source builds on both
backends. On integers the same signs stay bitwise. The snippets are in
`TESTS/test_set_operators.ady`.

### Enum-indexed arrays `[E]T`

When all keys are enum members, use `[E]T` — this maps to a fixed-size array
in Nim (no heap allocation, O(1) lookup). An enum whose values skip a number
(`enum A = 0, B = 5`, see [Enums](#enums)) cannot be a key, and is refused:

```python
type Priority is enum LOW, MED, HIGH

var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
print(costs[HIGH])   # 10
```

**Python output:** `{Priority.LOW: 1, Priority.MED: 5, Priority.HIGH: 10}`
**Nim output:** `[LOW: 1, MED: 5, HIGH: 10]`

An enum is just one ordinal key; `[10]T`, `[0..9]T` and `[bool]T` are the
same construct with a different one in the brackets.

It iterates its values in enum order, whatever order the literal used, like
every other `[O]T` — its keys are the domain, known in advance, so the
values are what a loop is for — and `x in score` asks whether some member
has the value x. Walk the domain when you want the member too:

```python
type Color is enum RED, GREEN, BLUE, AMBER
var score: [Color]int = [BLUE: 3, RED: 1, AMBER: 4, GREEN: 2]

for v in score:
    print v                      # 1 2 3 4
for c in Color:
    print c'Image, score[c]      # RED 1, GREEN 2, BLUE 3, AMBER 4
```

A comprehension fills one as readily as it fills a list — the annotation
decides which, and the values land in domain order. Iterate the key type,
not an integer range that happens to be the same length:

```python
type Off is 2 .. 6
var byE:   [Color]int = [ord(c) * 10 for c in Color]   # byE[RED] .. byE[AMBER]
var byOff: [Off]int   = [o * 10      for o in Off]     # byOff[2] is 20
var byB:   [bool]int  = [ord(b)      for b in bool]
```

`for c in Color` makes the loop variable the key each value belongs to, so
adding a member to `Color` cannot leave the two out of step. `for i in
0..2` only happens to be the right length. A plain length is the one key
with no type to name, so `[5]int` still takes a `0..4`.

There is no keyed comprehension (`[RED: 1 for ...]`); the values are
positional, which is why iterating the domain is the spelling that keeps
them honest.

Nested enum arrays work too (2-D lookup table):

```python
var transition: [Hidden_State_T][Hidden_State_T]float = [
    HEALTHY: [HEALTHY: 0.7, FEVER: 0.3],
    FEVER:   [HEALTHY: 0.4, FEVER: 0.6],
]
```

**Python output:** nested dict  
**Nim output:** `array[Hidden_State_T, array[Hidden_State_T, float]]`

### Insertion-ordered maps `[K]V`

An ordered mapping whose key is not a finite ordinal (see [Type Annotations](#type-annotations)) keeps its keys in the order they arrived, on both backends:

```python
var totals: [str]float = {:}
totals["zeta"] = 3.0
totals["alpha"] = 1.0
totals["mid"] = 2.0

for k in totals:
    print k                          # zeta alpha mid -- the keys, in order
for v in totals.values():
    print v                          # 3.0 1.0 2.0
for k, v in enumerate(totals):
    print k, v                       # (key, value), as over any mapping
assert "zeta" in totals              # a key: did "zeta" arrive?

var lens: [str]int = {s: len(s) for s in ["ccc", "a", "bb"]}   # in that order
var ages: [str]int = ["bob": 41, "amy": 37]                    # likewise
```

A dict literal, `{:}` and a dict comprehension all build one: the
declaration decides. Its keys are not known in advance — they are whatever
arrived — so, like a `{K}V`, a loop and `in` give the **keys**, here in the
order they arrived; `.values()` and `.items()` give the rest. An
`[Color]int` is the opposite case: its keys are fixed by its type, so it
gives its values. Keys can be any hashable type, a tuple included:
`[(int, int)]float` holds a value per coordinate, in the order the
coordinates were first set.

Pick `[K]V` when the order matters — output that follows the input, a
report in the order things were first seen — and `{K}V` when it does not.

### Comprehensions

One syntax builds every container; the brackets and the annotation choose
which, the same scheme the type notation uses to declare them:

```python
var asList:  []int    = [i*i for i in 0..4]     # seq / list
var asArray: [5]int   = [i*i for i in 0..4]     # stack array (see `[E]T` above)
var asSet:   {}int    = {i*i for i in 0..4}     # set
var asDict:  {int}int = {i: i*i for i in 0..4}  # dict
```

Multiple generators and `if` guards work as in Python, and two lists join
with `+`, so a list drawn from several sources is still one expression.
`sudoku.ady` builds its 27 units that way:

```python
var unitlist: [][]str = (
    [cross(ROWS, c) for c in COLS]
    + [cross(r, COLS) for r in ROWS]
    + [cross(rb, cb) for rb in ["ABC", "DEF", "GHI"] for cb in ["123", "456", "789"]])
```

The loop variable is typed from whatever it iterates, so the element
expression can operate on it — which the Nim backend needs, having separate
operators for arithmetic and concatenation:

```python
[r + c for r in ["A", "B"] for c in ["1", "2"]]   # ["A1","A2","B1","B2"]
[p + q for p in "AB" for q in "12"]               # the same, over strings
```

Iterating a string yields characters on the Nim backend, and the second
line relies on `char + char` being a string. That is `sudoku.ady`'s
`cross()`, whole.

Since iterating a string gives characters, `char` is the honest annotation
for keeping them, and `[]char` works throughout — appending, indexing back
out, adding to a string, comparing, passing to a `str` parameter.
`sudoku.ady`'s grid parser says what it means in one line:

```python
let chars: []char = [c for c in grid if c in DIGITS+"0."]
```

`in` over strings is a membership test on both backends, so `"x" in
"daxfdjd"` answers the substring question too.

Where a character does have to become a string it happens on its own, so no
`str(c)` is needed in four common places: a call argument whose parameter is
`str` (`cross(ROWS, c)` above), a declaration annotated `str`, `.append`
onto a `[]str`, and a string method given part characters and part strings —
`s.replace(c, "\\" + c)` works, because Nim overloads `replace` all-char or
all-string with nothing mixed. Each is an error on Nim and a no-op on
Python, where a character *is* a one-character string.

A slice is not a character and is left alone: `s[i]` indexes, `s[2:10]`
cuts.

The binding is scoped to the comprehension, as in Python — the same name
can hold different types in two of them, and an outer name of that spelling
is untouched:

```python
let same: int = 5
[same + "?" for same in ["p"]]      # a string in here
assert same + 1 == 6                # still the outer int out here
```

Concatenate with `+`. Nim spells it `&` and the backend rewrites `+` to
that, but writing `&` yourself is a Nim-only spelling: it is bitwise-and on
Python and raises there.

### Optional values `?T`

`?T` is shorthand for `T | None`: `?str` and `str | None` are one type.

```python
def find_exact_word(self, digits: []Digit_T) -> ?str:
    ...
    if len(node.words) > 0:
        return node.words[0]
    return None
```

---

## Variable Declarations

```python
var   x: int    = 10       # mutable
let   name: str = "hello"  # immutable (Nim: let; Python: annotated assignment)
const MAX: int  = 1_000    # compile-time constant
```

Declarations without an initial value are valid:

```python
var result: []int          # Nim: seq[int]; Python: list[int]
var table:  {str}int       # empty Table[string, int]
```

Tuple unpacking:

```python
let (x, y) = point          # explicit let destructuring
var (a, b) = (1, 2)         # explicit var destructuring
a, b = some_func()          # implicit: let (a, b) = some_func()
```

When the left-hand side is a bare comma-separated list and the variables are
not yet declared, the assignment is treated as an implicit `let` tuple
destructuring.

---

## Range Expressions

```python
for i in 0 .. 10:     # inclusive: 0, 1, …, 10
    pass

for i in 0 ..< 10:    # exclusive upper bound: 0, 1, …, 9
    pass

if x in 1 .. 100:     # range membership test
    pass
```

**Python output:** `range(lo, hi + 1)` for `..`, `range(lo, hi)` for `..<`.
**Nim output:** native `lo .. hi` and `lo ..< hi`.

Ranges work with enum tick attributes too:

```python
for s in Stage_T'First .. Stage_T'Last:
    ...
```

Ranges are first-class values, usable in `for` loops, membership tests and with `'choose`. `primes.ady` uses one as a loop bound:

```python
# From primes.ady:
for k in 2 .. int(n ** 0.5):
    if n % k == 0:
        return False
```

### for and while

Loops are Python's: `for` runs over any collection or range (a `{K}V` gives its keys; [Type Annotations](#type-annotations) says what each container gives), and `while` takes the inline form shown under [Case / When Statements](#case--when-statements).

```python
for item in collection:
    pass

for i in 0 ..< 10:
    pass

for key, val in mapping.items():
    pass
```

```python
while queue:
    item = queue.pop()
```

`while` also supports the inline form:

```python
var n: int = 3
while n > 0: n -= 1
```

---

## Case / When Statements

Pattern matching with Ada/Nim-inspired syntax, and the preferred way to
choose among the values of one subject: prefer `case` to an `if` / `elif` /
`else` chain that tests the same variable in every condition. The subject
is named once, the branches read as a table, and over an enum with constant
branches the Nim build rejects a `case` that misses a member -- so adding
one finds every dispatch that has to learn about it. Keep `if` for
conditions that test different things.

All standard pattern kinds are supported: literals, captures, wildcards, OR-patterns, ranges,
sequences, class patterns, `as` bindings and guards. (Mapping patterns are
not — see [Known Limitations](#known-limitations).)

A block Nim cannot check for completeness has to carry `when others:` — that
means a block with a guarded branch, or with a string subject. `when others`
may not itself be guarded. As in Ada, no value may be covered by two
unguarded branches (`when 34:` then `when 32 .. 126:` is refused), so the
order of the branches never changes what a block does. See
[The Adascript Book, Chapter 5](DOCS/BOOK/05-pattern-matching.md) for the
complete pattern reference and for what exhaustiveness does and does not
cover.

```python
case value:
    when 1:
        print("one")
    when 2 | 3:
        print("two or three")
    when 4 .. 10:
        print("four to ten")
    when others:
        print("something else")
```

`when`, like `if` / `elif` / `else` and `while`, also accepts an inline
single-statement body on the same line as the colon:

```python
case arg:
    when "--help" | "-h": usage(0)
    when "--verbose":     res.verbose = True
    when others:          print "unknown:", arg
```

Inline and indented branches can be mixed in the same `case`. The same
inline form works for `if` / `elif` / `else` / `while`:

```python
if x < 5: print("x<5")
elif x < 10: print("5<=x<10")
else: print("x>=10")

while n > 0: n -= 1
```

One subject tested against several values is what `case` is for; it replaces an `if` chain:

```python
# rather than
if mode == LIST:
    list_files()
elif mode == UNCHECKOUT:
    take_out()
else:
    check_out()

# write
case mode:
    when LIST:       list_files()
    when UNCHECKOUT: take_out()
    when CHECKOUT:   check_out()
```

The Python output is a `match/case` statement. The Nim output differs only when patterns require desugaring (structural, guards, tuple subjects).

**Enum patterns:**

```python
# from monty_hall.ady
for choice in Choice_T:
    case choice:
        when DontSwitch:
            if candidateFirstChoice == carLocation:
                stayWins += 1
        when Switch:
            let candidateSecondChoice: Door_T = switchOptions'choose
            if candidateSecondChoice == carLocation:
                switchWins += 1
```

**Tuple patterns (multi-dimensional dispatch):**

When the subject is a tuple, each `when` clause lists one value per element.
Use `_` as a wildcard that matches anything. The `others` catch-all works as
usual.

```python
# from shortest_path_demo.ady, example 6 (Equipment Replacement)
type Decision_T is enum BUY, SELL, KEEP, TRADE
type Cost_T is float
var maintenance_cost: {int}Cost_T = {0: 60.0, 1: 80.0, 2: 120.0}
var market_value: {int}Cost_T = {0: 1000.0, 1: 800.0, 2: 600.0, 3: 500.0}

def get_next_decisions(current_state: State_T) -> [](Decision_T, Cost_T):
    let (year, age) = current_state
    case (year, age):
        when (6, _):
            []
        when (0, _):
            [(BUY, maintenance_cost[0] + market_value[0])]
        when (5, _):
            [(SELL, -market_value[age])]
        when (_, 3):
            [(TRADE, -market_value[age] + market_value[0] + maintenance_cost[0])]
        when others:
            [
                (KEEP, maintenance_cost[age]),
                (TRADE, -market_value[age] + market_value[0] + maintenance_cost[0]),
            ]
```

Because Nim's `case` only accepts ordinal/string selectors (not tuples), the
transpiler desugars this to an `if/elif/else` chain:

```nim
# Generated Nim
proc get_next_decisions(current_state: State_T): seq[(Decision_T, Cost_T)] =
    let (year, age) = current_state
    if year == 6:
        @[]
    elif year == 0:
        @[(BUY, maintenance_cost[0] + market_value[0])]
    elif year == 5:
        @[(SELL, -market_value[age])]
    elif age == 3:
        @[(TRADE, -market_value[age] + market_value[0] + maintenance_cost[0])]
    else:
        @[(KEEP, maintenance_cost[age]), (TRADE, -market_value[age] + market_value[0] + maintenance_cost[0])]
```

Wildcard `_` elements are omitted from the generated condition (they add no
constraint). A `when (4, 8):` clause generates `elif year == 4 and age == 8:`.

**Python output:** `match/case` with tuple pattern  
**Nim output:** `if/elif/else` chain (desugared)

**Structural patterns (discriminated union matching):**

When matching against record types with a `kind` discriminant, use
`TypeName(field=value, ...)` patterns. Uppercase field values are treated as
enum/constant comparisons; lowercase names become `let` bindings.

```python
type Val_Kind_T is enum VNum, VSym, VList
type Val_T is record:
    kind: Val_Kind_T
    num:  float
    sym:  str
    items: []Val_T

def describe(x: Val_T) -> str:
    case x:
        when Val_T(kind=VSym, sym="if"):   # field equality check
            return "keyword: if"
        when Val_T(kind=VSym, sym=name):   # field capture binding
            return "symbol: " + name
        when Val_T(kind=VNum, num=n):
            return "number"
        when others:
            return "other"
```

Generated Nim:

```nim
if x.kind == VSym and x.sym == "if":
    return "keyword: if"
elif x.kind == VSym:
    let name = x.sym
    return "symbol: " & name
elif x.kind == VNum:
    let n = x.num
    return "number"
else:
    return "other"
```

**Sequence patterns** match lists by length and element structure. Use `*name`
to capture the tail:

```python
def eval_expr(x: Val_T) -> str:
    case x.items:
        when [Val_T(kind=VSym, sym="if"), test, consequence, alternative]:
            return "if-expr"
        when [Val_T(kind=VSym, sym="define"), Val_T(kind=VSym, sym=name), expr]:
            return "define: " + name
        when [Val_T(kind=VSym, sym=op), *args]:
            return "call: " + op
        when others:
            return "other"
```

Generated Nim:

```nim
if len(x.items) == 4 and x.items[0].kind == VSym and x.items[0].sym == "if":
    let test = x.items[1]
    let consequence = x.items[2]
    let alternative = x.items[3]
    return "if-expr"
elif len(x.items) == 3 and x.items[0].kind == VSym and x.items[0].sym == "define" and x.items[1].kind == VSym:
    let name = x.items[1].sym
    let expr = x.items[2]
    return "define: " & name
elif len(x.items) >= 1 and x.items[0].kind == VSym:
    let op = x.items[0].sym
    let args = x.items[1..x.items.high]
    return "call: " & op
else:
    return "other"
```

Rules:
- `TypeName(field=Value)` — uppercase `Value` → equality check (`x.field == Value`)
- `TypeName(field=name)` — lowercase `name` → let binding (`let name = x.field`)
- `[p0, p1, ..., pN]` — fixed-length sequence match (`len(x) == N+1`)
- `[p0, *rest]` — variable-length match (`len(x) >= 1`, `rest = x[1..]`)
- `[]` — empty sequence match (`len(x) == 0`)
- `_` or `others` → catch-all (no condition, no binding)

See `lispy.ady` for a complete example using all these forms.

**Python output:** `match/case` with class and sequence patterns  
**Nim output:** `if/elif/else` chain with field checks and `let` bindings

**Limitation — subject must be a structural expression:**

The tuple and structural desugar paths activate only when the `case` subject
is written as a compound expression. A plain variable falls through to Nim's
native `case`, which only accepts ordinal/string selectors and will fail to
compile for tuple or record subjects.

```python
# ✓ Correct: unpack first, then use the tuple expression as subject
let (f, w, g, c) = state
case (f, w, g, c):
    when (right, right, right, right):
        return True
    when others:
        return False

# ✓ Correct: field access as subject
case x.kind:
    when VSym: ...
    when VNum: ...

# ✗ Wrong: plain variable holding a tuple — emits Nim `case state:`,
#   which Nim rejects because tuples are not ordinal selectors
case state:
    when (right, right, right, right): ...
```

This is a transpiler limitation, not a language design choice. The workaround
is always to destructure the compound value with `let` first.

**Guards:**

A branch may carry an `if` guard on an arbitrary expression. A guard anywhere
in the block means Nim cannot check the branches for completeness, so
the block must then carry an unguarded `when others:`.

```python
def classify(arg: str) -> str:
    case arg:
        when "--":
            return "end-of-options"
        when _ if arg.startswith("--"):
            return "long option"
        when _ if arg.startswith("-") and len(arg) > 1:
            return "short option"
        when others:
            return "argument"
```

Nim output (guards force if/elif desugaring):

```nim
if arg == "--":
    return "end-of-options"
elif arg.startsWith("--"):
    return "long option"
elif arg.startsWith("-") and len(arg) > 1:
    return "short option"
else:
    return "argument"
```

**Enum auto-qualification:**

Write enum members bare in patterns — the transpiler qualifies them
automatically in Python output so they act as value patterns, not captures:

```python
type Color = enum Red, Green, Blue

case pixel:
    when Red:   r += 1    # → Python: case Color.Red:
    when Green: g += 1
    when Blue:  b += 1
```

---

## Statement Modifier

`return`, `break` and `continue` -- and a call to `die` or `quit` -- can
carry their own `if`, Perl- and Ruby-style: the statement runs only when the
condition holds. It is the
guard clause written the way it reads -- the exit first, the reason for it
after.

```python
def is_term_continuation(code_s: str) -> bool:
    return False if code_s == ""
    return True if code_s.startswith("(")
    return False if not starts_with_operator(code_s) or code_s.startswith((":=", "=>", "|"))
    let w: str = lead_ident(code_s).lower()
    return w != "xor"
```

Both backends emit the one-line `if`, so the shape of the generated code is
the shape of the source:

**Python output:**

```python
if code_s == "": return False
```

**Nim output:**

```nim
if code_s == "": return false
```

A bare `return` takes one too, and so do `break` and `continue`. The
condition is an ordinary expression -- calls, `and` / `or` / `not`,
comparisons, `in`:

```python
return if quiet
continue if line.startswith("#") or line.strip() == ""
break if depth < 0
```

`die(msg) if not found` and `quit(0) if done` are guards in the same sense:
they leave the program rather than the function.

`die` and `quit` leave too -- the program rather than the function -- so
they are guards in the same sense:

```python
die(f"no such file: {p}") if not -f p
die("bad option " + a, code = 2) if a.startswith("-")
quit(0) if len(todo) == 0
```

A modifier testing an optional establishes the auto-unwrap for everything
after it, exactly as the indented guard does — the optional is a plain value
from that line on, and writing `.get()` yourself would unwrap it twice:

```python
let bt: ?BuildType = build_type_from(name)
continue if bt is None
builds.append((name: name, btype: bt))   # bt is a plain BuildType here
```

**Those statements and no others.** An assignment, any other call, a
`print`, a `raise` -- none of them may carry a modifier, and the parser rejects the
line rather than emit it. The modifier is for the guard clause, where the
statement leaves the block it is in and the condition is the reason it left.
`x = 1 if c` would open exactly like the conditional expression
`x = 1 if c else 2` and stop looking like one only at the end of the line,
which is the opposite of what a guard is for.

**A conditional expression is still a conditional expression.** The modifier
takes only an `if` with no `else`, so the ternary keeps its Python reading:

```python
v: int = 1 if flag else 2      # conditional expression, unchanged
return 1 if flag else 2        # likewise -- not a modifier
```

So the `else` decides what a `return` means. `return a if cond` is a
conditional return: it leaves only when `cond` holds, and otherwise the next
line runs. `return a if cond else b` always returns, one of the two values:

```python
def evaluate(x: Val_T, env: Env) -> Val_T:
    return lookup(env, x.sym) if x is Sym_T    # leaves, or falls through
    return x if x is not List_T                # leaves, or falls through
    ...

def atom(token: str) -> Val_T:
    let num: float | !ParseFailure_T = parse_float(token)
    return Sym_T(token) if num is ParseFailure_T else Num_T(num)   # always
```

The two branches of a conditional expression may be different members of a
union; each is wrapped in the union that the `return` (or the declared type)
asks for.

One statement per line: `a; return if c` is not accepted, because neither
backend can spell it on one line.

---

## Regex Literals

Adascript has first-class regex literal syntax: `/pattern/flags`. No `import re`
needed — regex support is injected automatically into the generated code for both
backends (Nim uses `nre`/`std/re`; Python uses the standard `re` module). Regexes work with `==` / `!=`, `case/when`, and the substitution form `s/pat/repl/`.

### Match test (`==` / `!=`)

Use `==` with a regex on the right-hand side to test whether a string matches:

```python
if line == /error/i:
    print "found error"

if text != /^\s*$/:
    process(text)
```

The left operand is a `str`; the transpiler detects the regex RHS and emits a
match call instead of an equality test.

**Nim output:**
```nim
if nimatch(line, re"(?i)error"):
    echo "found error"

if not nimatch(text, re"^\s*$"):
    process(text)
```

**Python output:**
```python
if _pymatch(line, r'error', re.IGNORECASE):
    print("found error")

if not _pymatch(text, r'^\s*$'):
    process(text)
```

### Positional capture groups

After a successful `== /pat/` match, `$+0` holds the whole match and `$+1`,
`$+2`, … hold the numbered capture groups:

```python
if src == /^([a-zA-Z_]\w*)\s*=\s*(.+)$/:
    name:  str = $+1
    value: str = $+2
    print f"{name} → {value}"
```

**Nim output:**
```nim
if nimatch(src, re"^([a-zA-Z_]\w*)\s*=\s*(.+)$"):
    var name:  string = matches[1]
    var value: string = matches[2]
    echo fmt"{name} → {value}"
```

**Python output:**
```python
if _pymatch(src, r'^([a-zA-Z_]\w*)\s*=\s*(.+)$'):
    name:  str = matches[1]
    value: str = matches[2]
    print(f"{name} → {value}")
```

### Named capture groups

Use PCRE named groups `(?P<name>...)`. After a match, the `namedCaptures`
dict (type `{str}str`) holds the results:

```python
if line == /(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/:
    year:  str = namedCaptures["year"]
    month: str = namedCaptures["month"]
    day:   str = namedCaptures["day"]
    print f"{year}/{month}/{day}"
```

Both `matches` and `namedCaptures` are globals populated by the last
successful match call. Copy them immediately if you need to call another
regex before consuming the results.

### Find all (`/g` flag)

Adding `g` returns all non-overlapping matches as `[]str` instead of a bool:

```python
let words:  []str = text  == /\w+/g
let digits: []str = line  == /\d+/g
let count:  int   = len(text == /\w+/g)
```

`!= /pat/g` is not meaningful; use `len(s == /pat/g) == 0` to test for no
matches when using `g`.

**Nim output** uses `std/re.findAll` (O(n), much faster than `nre.findAll`):
```nim
let words:  seq[string] = text.findAll(srx.re(r"\w+"))
```

**Python output:**
```python
words:  list[str] = re.findall(r'\w+', text)
```

### Substitution (`s/pat/repl/flags`)

```python
text = s/\s+/ /g         # collapse whitespace runs to single space
name = s/[^a-z]//gi      # strip everything that is not a–z
line = s/\bfoo\b/bar/    # replace first occurrence of whole word "foo"
```

Backreferences in the replacement use `$+1`, `$+2` (positional) or
`$+{name}` (named group). The substitution assigns the result back to the
left-hand side.

**Nim output:**
```nim
text = text.replace(srx.re(r"\s+"), " ")
```

**Python output:**
```python
text = re.sub(r'\s+', r' ', text)
```

### Regex in `case/when`

Regex patterns work directly as `when` branches. The entire `case` block
desugars to an `if/elif/else` chain:

```python
def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER
```

**Nim output:**
```nim
proc classify(line: string): Severity_T =
    if nimatch(line, re"(?i)error"):
        return ERROR
    elif nimatch(line, re"(?i)warn"):
        return WARN
    elif nimatch(line, re"(?i)info|debug"):
        return INFO
    else:
        return OTHER
```

**Python output:**
```python
def classify(line: str) -> Severity_T:
    if _pymatch(line, r'error', re.IGNORECASE):
        return ERROR
    elif _pymatch(line, r'warn', re.IGNORECASE):
        return WARN
    elif _pymatch(line, r'info|debug', re.IGNORECASE):
        return INFO
    else:
        return OTHER
```

Mixed patterns (some literal, some regex) in the same `case` are allowed —
the whole block still desugars to `if/elif/else`.

### Supported flags

| Flag | Meaning |
|------|---------|
| `i`  | Case-insensitive |
| `g`  | Return all matches as `[]str` (only on `==` RHS) |
| `m`  | Multiline — `^` / `$` match per-line boundaries |
| `s`  | Dotall — `.` also matches `\n` |

### Translation reference

| Adascript | Nim (generated) | Python (generated) |
|-----------|-----------------|-------------------|
| `s == /pat/` | `nimatch(s, re"pat")` | `_pymatch(s, r'pat')` |
| `s == /pat/i` | `nimatch(s, re"(?i)pat")` | `_pymatch(s, r'pat', re.IGNORECASE)` |
| `s != /pat/` | `not nimatch(s, re"pat")` | `not _pymatch(s, r'pat')` |
| `s == /pat/g` | `s.findAll(srx.re(r"pat"))` | `re.findall(r'pat', s)` |
| `$+0` | `matches[0]` (whole match) | `matches[0]` |
| `$+N` | `matches[N]` (N-th group) | `matches[N]` |
| `$+{name}` | `namedCaptures["name"]` | `namedCaptures["name"]` |
| `$+{k}` | `namedCaptures["k"]` | `namedCaptures["k"]` |
| `s = s/pat/repl/` | `s = s.replace(srx.re(r"pat"), "repl")` | `s = re.sub(r'pat', r'repl', s)` |
| `s = s/pat/$+1/` | `s = s.replace(srx.re(r"pat"), "$1")` | `s = re.sub(r'pat', r'\1', s)` |
| `s = s/pat/repl/g` | same (std/re replace is always global) | same (`re.sub` is always global) |
| `when /pat/:` in `case` | `elif nimatch(subject, re"pat"):` | `elif _pymatch(subject, r'pat'):` |

`nimatch`/`_pymatch`, `matches`, and `namedCaptures` are injected automatically
into the generated file whenever a regex literal is used.

---

## Tick Attributes

Ada-style `'` attributes provide first-class access to enum and subrange
metadata. A name followed immediately by `'` and an identifier is read as an
attribute, not as the start of a string literal. Where a name is followed immediately by `'` and an identifier, the tokeniser emits the apostrophe as a token of its own (`TICK_TOKEN`), so Python's lexer never takes it for the start of a string; the grammar matches the pair as `tick_trailer = TICK + IDENTIFIER`.

```python
type Stage_T is enum A, B, C

Stage_T'First    # first member  → A
Stage_T'Last     # last member   → C
Stage_T'Range    # full set      → {Stage_T.low..Stage_T.high} (Nim ordinal set)
current'Next     # successor     → type(current)(current.value + 1)
current'Prev     # predecessor   → type(current)(current.value - 1)
```

Particularly useful for iterating over an enum's full range:

```python
for s in Stage_T'First .. Stage_T'Last:
    ...
```

`T'Range` produces a Nim ordinal set containing all members of the enum —
useful for set arithmetic:

```python
let available: {}Door = Door'Range - {picked, car}
```

### Full attribute reference

Several attributes read differently on a *type* than on a *value*: on the
type they ask about the domain, on a value about the container. `Stage_T'First`
is the first member, where `xs'First` is the index `0`.

| Attribute | Applies to | Meaning |
|-----------|------------|---------|
| `T'First`, `T'Low`   | enum or subrange type | first member |
| `T'Last`, `T'High`   | enum or subrange type | last member |
| `xs'First`, `xs'Low` | sequence or string    | first index (`0`) |
| `xs'Last`, `xs'High` | sequence or string    | last index (`len - 1`) |
| `T'Range`            | enum type             | set of every member, for set arithmetic |
| `xs'Range`           | sequence or string    | its index range, for `for i in xs'Range:` |
| `x'Next`, `x'Prev`   | enum value            | successor / predecessor |
| `x'Image`            | enum value            | the member's name as a `str` |
| `xs'Length`, `xs'len`| sequence, string, set | element count — the same as `len(xs)` |
| `xs'Shuffle`         | sequence              | a shuffled copy |
| `x'choose`           | enum type, set, or range expression | a uniformly random element |
| `x'Size`             | any value             | **Nim only** — machine size in bytes |

`'choose` and `'Shuffle` draw on the random number generator, which is seeded
once per program:

```python
let d: Door_T = Door_T'choose         # random member
let t: int    = (1..6)'choose         # random int in 1..6
let r: []int  = deck'Shuffle          # shuffled copy
```

On the Nim backend `'Shuffle` needs a mutable sequence, so declare the source
with `var` rather than `let`.

`'Size` is Ada's representation attribute, not a count: it reports how many
bytes the value occupies, so a set of a three-member enum is `1` while
`len()` of that same set is however many members it holds. Reach for
`len(s)` or `s'Length` when you want the number of elements. It is also the
one attribute the Python backend does not implement — it raises `unknown
tick attribute 'Size'` there.

Attributes do not chain: write `let f: Stage_T = Stage_T'First` and then
`f'Image`, not `Stage_T'First'Image`.

> **Note:** a tick attaches to a field access or a subscript as readily as
> to a bare name — `r.c'Image`, `xs[0]'Image` and `self.num'Image` all work,
> on both backends. There is no need to bind a local or reach for `str()`
> first. What a tick does *not* do is chain: bind the intermediate value
> (`let f: Stage_T = Stage_T'First`, then `f'Image`) rather than writing
> `Stage_T'First'Image`, which is a parse error.

> **Note:** `E'Range` is a *set* of the members (`set(E)` on the Python
> backend, `{E.low..E.high}` on Nim), so set arithmetic works on it —
> `Door_T'Range - {chosen}`. On a value rather than a type, `x'Range` is the
> index range instead: `for i in word'Range` walks the positions of a
> string.

### Iterating an ordinal type

Every ordinal type is a domain, so naming one is enough to walk it — an
enum, a named subrange, and the two builtin ordinals that are never
declared anywhere:

```python
type Stage_T is enum STAGE1, STAGE2, STAGE3
type Off     is 2 .. 6

for s in Stage_T:                # STAGE1 STAGE2 STAGE3
    print(f"processing stage {s}")

for o in Off:                    # 2 3 4 5 6 — its own domain, not 0-based
    pass
for b in bool:                   # False True
    pass
for c in char:                   # 256 of them
    pass
```

The bounds spelling is also available where the bounds themselves matter:

```python
for s in Stage_T'First .. Stage_T'Last:
    print(f"processing stage {s}")
```

`ord(x)` gives the ordinal position of any of these — Python's builtin
takes a one-character string and nothing else, so the emitter supplies the
rest: `ord(STAGE2)` is 1, `ord(True)` is 1, `ord(4)` is 4, `ord("a")` is
97. Both backends agree.

### Set arithmetic with `'Range`

`E'Range` yields the full set of an enum's members — useful for computing
complements:

```python
# from monty_hall.ady — Monty Hall simulation
type Door_T is enum Door1, Door2, Door3

let available: {}Door_T = Door_T'Range - {candidateFirstChoice, carLocation}
let hostChoice: Door_T  = available'choose   # random door from the set
```

### Enum successor and predecessor

`'Next` and `'Prev` step through enum members (not for an enum whose values skip a number, see [Enums](#enums)):

```python
type Stage_T is enum STAGE1, STAGE2, STAGE3, END

current_stage: Stage_T = STAGE1
next_stage: Stage_T = current_stage'Next    # STAGE2
```

---

## Functions

Standard Python `def` syntax with Adascript type annotations:

```python
def add(a: int, b: int) -> int:
    return a + b
```

### Implicit return

When a function has a return-type annotation and its last statement is a
bare expression (not an explicit `return`), Adascript automatically promotes
it to a return value:

```python
def clamp(x: int, lo: int, hi: int) -> int:
    max(lo, min(x, hi))

def is_even(n: int) -> bool:
    n % 2 == 0
```

**Python output:** wraps with `return`.
**Nim output:** left as-is (Nim treats the last expression as the implicit
return value).

Two rules govern when implicit return fires:

- The function must have a return-type annotation (`-> T`).
- `-> None` is excluded — a void function's last expression stays as a
  statement.

### Default parameter values

```python
def find_path(graph: Graph_T, start: Node_T, end: Node_T,
              path: []Node_T = []) -> []Node_T:
    ...
```

### Parameter mutation

Parameters behave as they do in Python, on both backends. Rebinding the
parameter name is local to the function; mutating the object it refers to is
visible to the caller:

```python
def rebind(s: str) -> str:
    s = s + "!"        # local — the caller's string is unchanged
    return s

def append_to(xs: []int):
    xs.append(99)      # in-place — the caller sees the new element

var msg:  str   = "hi"
var nums: []int = [1, 2]

let out: str = rebind(msg)
print f"{out} / {msg}"          # hi! / hi   — the caller's msg is unchanged
append_to(nums)
print f"{len(nums)}"            # 3          — the caller's list grew
```

The Nim backend infers which case applies and needs no annotation. A rebound
parameter is shadowed by a mutable local, and one mutated in place becomes a
`var` parameter:

```nim
proc rebind(s: string): string =
    var s = s                   # shadow: the caller's value is untouched
    s = s & "!"
    return s

proc append_to(xs: var seq[int]) =
    xs.add(99)                  # var: the mutation reaches the caller
```

In place includes what a field or an element holds, as in `r.names.append(x)` or `r.groups[k][i].members.append(x)`.

### Overloads

A function, or a method, may be defined more than once under one name if the parameters differ in their types. The call picks the def from the types of its arguments, as in Ada and in Nim:

```python
def describe(n: int) -> str:
    return f"int {n}"

def describe(s: str) -> str:
    return f"str {s}"

def describe(d: Duration_T) -> str:
    return f"duration {float(d):.1f}"

def describe(n: int, s: str) -> str:
    return f"{n} of {s}"
```

This is what makes an operator work on more than one type: `Velocity` has `__mul__(self, scale: float) -> Velocity`, which scales, and `__mul__(self, t: Duration_T) -> Vector`, which turns a speed into a distance, so `v * 2.0` and `v * t` are both written as they read. A distinct type is its own type here: a `Duration_T` finds the overload that names it, not the one that names `float`.

- A constructor overloads the same way: `Vector(length, angle)` and `Vector(x, y)` are two `__init__`s, told apart by the types of the arguments (`Degree_T` against `Meters_T`).
- A literal is no argument of any type, so one given to an overloaded name is refused on Nim -- `Vector(3.0, 4.0)` could be either -- and written with its type: `Vector(Meters_T(3.0), Meters_T(4.0))`.
- Two defs with the same parameter types are one name defined twice, and refused.
- Nim overloads natively. On Python the defs are renamed and a def of the name dispatches on the types of the arguments, the exact type first, then what each is an instance of; a type it cannot test (a union, a generic) matches anything. Arithmetic on a distinct value is a plain number in Python, so as a last resort a plain number matches a distinct type of numbers; write `Meters_T(a + b)` where overloads differ only in such types. Call overloads by position.
- Decorated defs, and defs with `*args` or `**kwargs`, are left as they are.

<!-- tested by TESTS/test_overload_types.ady -->

### Decorators

A wrapper marked `@decorator` takes the decorator's own arguments, then the
function it wraps as `f`, then that function's arguments:

```python
# from test_decorators.ady
@decorator
def aligned(width: int, f: (str) -> str, s: str) -> str:
    return f"{f(s):<{width}}"

@aligned(8)
def tag(name: str) -> str:
    return "<" + name + ">"
```

`tag("a")` is `"<a>     "`. A wrapper can be generic, `def timed[T, R](label: str,
f: (T) -> R, x: T) -> R`, and then serves any function, its arguments packed
into one tuple when there are several: that is how a timing or logging
decorator is written (both are in the test). A parameter with a default
before `f`, `cache: {T}R = {:}`, is state: a bare `@cached` gets a table of
its own. Stacked decorators apply bottom-up; a recursive
call goes through the decorated name. The transpiler rewrites this before
the parse (the body becomes `tagBody`, and `tag` returns
`aligned(8, tagBody, name)`), so it works the same on Nim, Python and JS.
`f`'s type, the parameters after it and the return type must match the
decorated def, or it is refused. On a method, the wrapper is handed the
method bound to self, so `@shout` on `def greet(self, other: str) -> str`
wraps a `(str) -> str`, and the method may write to self.

<!-- tested by TESTS/test_decorators.ady -->

### Nested functions and closures

```python
# from phonecode.ady
def load_dictionary(self, filename: str, verbose: bool) -> None:
    def word_to_digits(word: str) -> []Digit_T:
        var digits: []Digit_T = []
        for c in word.lower():
            if c not in CHAR_TO_DIGIT:
                return []
            digits.append(CHAR_TO_DIGIT[c])
        return digits

    with open(filename, "r") as f:
        for line in f:
            let digits: []Digit_T = word_to_digits(line.strip())
            ...
```

### Generic functions

Type parameters are declared in brackets after the function name, the same
way [generic classes](#generic-classes) declare theirs:

```python
def first_of[Elem_T](xs: []Elem_T) -> Elem_T:
    xs[0]

def pair_up[A_T, B_T](a: A_T, b: B_T) -> (A_T, B_T):
    (a, b)
```

Nim gets `proc first_of[Elem_T](xs: seq[Elem_T]): Elem_T` and instantiates
one version per call site; Python gets the same brackets as PEP 695 type
parameters, `def first_of[Elem_T](xs: list[Elem_T]) -> Elem_T`.

A call names the types it instantiates. Adascript never infers them, so the
reader never has to work out from the arguments what a generic call was made
with:

```python
print first_of[int]([4, 5, 6])
print first_of[str](["a", "b"])
```

A bare call, `first_of([7, 8])`, is an error on both backends, and the message
says what to write: `'first_of' is generic in Elem_T: name the types at the
call, first_of[<Elem_T>](...)`. The declaration is held to the same rule: a
type parameter is what the brackets after a function's name, or a generic
class's, declare, and nothing else. A lone capital in a signature that nobody
declared -- `def first_of(xs: []T) -> T` -- is refused with the declaration
to write, and is not guessed to be a type parameter as it once was. A nested
definition uses its enclosing function's parameter without declaring it
again.

A type argument is a name, or a tuple: `first_of[Row_T]`, `first_of[(int,
str)]`. A composite type such as `[]int` is named first -- `type Row_T is
[]int` -- as it is anywhere else it is worth writing down twice.

Any identifier may be a type parameter once it is declared in the brackets,
so prefer a name that says what it stands for — `Node_T`, `Elem_T` — over a
bare letter. The bundled `iters` and `graphs` libraries are written this
way.

### Generator functions

`yield` is fully supported, enabling generator functions that transpile
correctly to both Python and Nim:

```python
def shortest_path(self, start_state: S, end_state: S):
    ...
    while fringe:
        ...
        if current_state == end_state:
            yield self.real_cost(cost), path
```

---

## Classes and Inheritance

Standard Python class syntax is fully supported, including inheritance,
`__init__`, properties, and generic type parameters. In Nim output, classes
with inheritance become `ref object of Base` with separate `proc` definitions.

```python
class Shape:
    def area(self) -> float:
        return 0.0

class Circle(Shape):
    var radius: float

    def __init__(self, r: float):
        self.radius = r

    def area(self) -> float:
        return 3.14159 * self.radius ** 2
```

### Class-level variable declarations

Adascript uses `var`, `let`, or `const` inside a class body to declare fields,
keeping declarations visually distinct from assignments:

```python
class TrieNode:
    var children: [Digit_T]TrieNode
    var words: []str
```

Field declarations can carry inline defaults. The transpiler injects them into
the generated constructor automatically, so `__init__` only needs to set
fields that differ per instance. Every instance gets fields of its own, on
both backends: a field without a default starts at its zero, and a list,
table or object default is made afresh for each instance, never shared:

```python
class SeverityProcessor(AwkProcessor):
    var NR        : int = 0
    var NF        : int = 0
    var total_len : int = 0
    var counts    : [Severity_T]int = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]

    def __init__(self, fs: str = " ", ofs: str = " "):
        self.FS  = fs   # only non-defaulted fields need setting
        self.OFS = ofs
```

A field can be an enum-indexed array of the class itself, as in a trie:

```python
class TrieNode:
    var children: [Digit_T]TrieNode   # fixed-size array indexed by enum
    var words:    []str

    def __init__(self, filename: str = "", verbose: bool = False):
        self.children = {d: None for d in Digit_T}
        self.words = []
        if filename:
            self.load_dictionary(filename, True)

    def add_word(self, word: str, digits: []Digit_T) -> None:
        var node: TrieNode = self
        for digit in digits:
            if node.children[digit] is None:
                node.children[digit] = TrieNode()
            node = node.children[digit]
        node.words.append(word)
```

### A type written in a class

A type that only one class uses can be written in its body, next to the fields that name it:

```python
class Cover:
    type Kind_T is enum CLEAR, NO_FLY, APPROACH
    var kind: Kind_T

    def colour(self) -> str:
        case self.kind:
            when CLEAR:    "blue"
            when NO_FLY:   "red"
            when APPROACH: "green"
```

The type is declared beside the class, before it, in both backends: it is not scoped to the class, so
`Kind_T` and its members are named bare everywhere in the file, and a second class cannot declare a `Kind_T`
of its own. An enum cannot be written on the field itself (`var kind: enum CLEAR, NO_FLY` does not parse); it
needs its name. See `TESTS/test_class_type.ady`.

### Mutable self in non-virtual classes

For plain (non-`@virtual`) classes, the transpiler automatically detects
whether a method mutates `self` (field assignment, `+=`, `.add()`, or a
call to a method that does) and emits `self: var ClassName` in the
generated Nim. No annotation is needed:

```python
class Counter:
    var count: int = 0

    def increment(self):
        self.count += 1   # transpiler emits: proc increment(self: var Counter)
```

A method that only reads -- calling other reading methods, or handing
fields to a function or method of the program that takes nothing as
`var` -- keeps a plain `self`, so it can be called on a `let`.

`@virtual` is only needed when subclasses live in a **different file** (module)
from their base class — it makes Nim use `ref object` for dynamic dispatch
across module boundaries.

### Declaration order, and `var` instances

Nim resolves a name where the call is written, not when it runs; the
transpiler makes up for that, so declaration order does not matter. Only the
last rule below, about `var`, survives into Adascript.

**A method may call a sibling method defined below it** — the transpiler
declares the sibling ahead of its first caller (and declares nothing that
is not called early):

```python
class Report:
    var name: str

    def __init__(self, name: str):
        self.name = name

    def run(self):
        self.header()      # defined below — fine
        self.body()

    def header(self): print f"{self.name} header"
    def body(self):   print f"{self.name} body"
```

**A method may call a free function, or use a class, defined below it** --
and a function may call one defined below it. Every routine called before
its definition is declared ahead of its first caller, and every type goes
into one `type` section, so the file can be laid out for the reader: the
driver class first, say, and the helpers after.

**`__init__` may call a sibling method too** — the generated `initT` / `newT`
come out ahead of the other method bodies, so this once reached an undeclared
routine (or, with a same-named proc in scope such as `nimport os`'s
`resolve(Path)`, silently bound to *that* one and failed as a type mismatch).
The forward declarations cover it now.

**An instance whose methods reach a write must be `var`.** Mutable `self` is
inferred transitively: `run` calls `body`, `body` assigns a field, so both
take `self: var Report`, and a `let` binding cannot receive it:

```python
let report: Report = Report(opt)
report.run()  # Error: expression 'report' is immutable, not 'var'

var report: Report = Report(opt)
report.run()  # correct
```

A method that only reads keeps a plain `self` even when it calls other
readers, so it works on a `let`, a loop variable or a parameter. Where the
transpiler cannot tell — a method called on a field, `self` passed to a
routine from outside the program — it assumes a write. The Python backend accepts either, so only Nim
reports it. Rule of thumb: if you call a method on it, declare it `var`.

### Forwarding constructors

When a subclass has no `__init__`, the transpiler generates a forwarding
constructor that mirrors the parent's parameters and calls the parent's
initialiser automatically:

```python
@virtual
class AwkProcessor:
    var FS: str
    var OFS: str

    def __init__(self, fs: str = " ", ofs: str = " "):
        self.FS  = fs
        self.OFS = ofs

class SeverityProcessor(AwkProcessor):
    var counts: [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]
    # no __init__ needed — SeverityProcessor(fs, ofs) is generated automatically
```

### Inheritance and `super()`

```python
class EquipmentReplacement(Optimizer[State_T, Decision_T, Cost_T]):
    var maintenance_cost: {Age_T}Cost_T = {0: 60.0, 1: 80.0, 2: 120.0}

    def __init__(self, offset: float = 0.0):
        super().__init__(offset)

    def get_next_decisions(self, current_state: State_T) -> [](Decision_T, Cost_T):
        let (year, age) = current_state
        ...
```

### Variables shared between methods and outer scope

When a class is defined inside a function, Nim requires that type declarations
and method bodies be hoisted to global scope. Local variables of the enclosing
function are **not** visible inside hoisted methods.

To share a variable between the enclosing function and the class methods,
declare it with an **ALL_CAPS** name. The transpiler recognises ALL_CAPS
`var`/`let`/`const` declarations as globals and hoists them alongside the
methods:

```python
def example():
    type Stage_T is enum STAGE1, STAGE2, STAGE3, END
    type Choice_T is tuple:
        weight: int
        benefit: int

    var ITEMS: [Stage_T]Choice_T = [   # ALL_CAPS → hoisted to global scope
        STAGE1: (weight:2, benefit:65),
        STAGE2: (weight:3, benefit:80),
        STAGE3: (weight:1, benefit:30),
    ]

    class Knapsack(Optimizer[State_T, Decision_T, Cost_T]):
        def get_next_decisions(self, state: State_T) -> [](Decision_T, Cost_T):
            let (weight, benefit) = ITEMS[state.stage]  # accessible here
            ...
```

Lowercase `var` declarations stay inside the enclosing proc and are **not**
visible to hoisted methods. Use ALL_CAPS for any variable that methods need
to read.

### `@virtual` — enabling cross-module subclassing

The `@virtual` decorator makes Nim generate `ref object of RootObj` instead of
a plain `object`. It is **only required** when subclasses live in a different
file (module) from their base class — for dynamic dispatch across module
boundaries. Within a single file, plain classes handle mutable `self`
automatically (see above).

```python
@virtual
class Optimizer[S, D, C]:
    var offset: float
    var decision_path: []D
    var start_state: S

    def __init__(self, offset: float = 0.0):
        self.offset = offset
        self.decision_path = []
```

When used with `import` (see [Modules and Project Layout](#modules-and-project-layout)), the base class's `.nim` is compiled as a
library and subclasses in the importing file dispatch dynamically at runtime.

`@virtual` also changes what assignment does on Nim: a `ref object` is shared
by every name that holds it, as every object is on Python. A plain class is
copied on assignment on Nim and shared on Python (see [Copied on Nim, shared on Python](#copied-on-nim-shared-on-python)); a `@virtual` one is shared on both.

A class that holds itself needs no `@virtual`: on Nim a value cannot contain
itself, so a class with a field of its own type (`next: ?Node`), or one that
holds itself by way of a record (a `Closure` whose `body: Expr_T` is a variant
record with a `fun: Closure` case), is made a `ref object` by the transpiler,
and is shared on assignment on both backends. TESTS/test_value_cycle.ady
is the second kind.

### Generic Classes

Generic type parameters go in square brackets after the class name. The
transpiler carries the declared list through all generated Nim procs; nothing
about it is inferred:

```python
class Optimizer[S, D, C]:
    """Generic shortest-path / DP optimiser.
    S = state type, D = decision type, C = cost type."""

    var offset: float

    def get_next_decisions(self, current_state: S) -> [](D, C):
        raise NotImplementedError("Override get_next_decisions()")

    def shortest_path(self, start_state: S, end_state: S):
        ...
        yield self.real_cost(cost), path
```

Subclass by instantiating the parameters:

```python
type State_T is str
type Cost_T  is float

class BookMap(Optimizer[State_T, State_T, Cost_T]):
    var G: {State_T}[](State_T, Cost_T) = { ... }

    def get_state(self, past_decisions: []State_T) -> State_T:
        return past_decisions[-1]

    def get_next_decisions(self, curr: State_T) -> [](State_T, Cost_T):
        return self.G.get(curr, [])
```

Methods that need to sit outside the class (to avoid Nim 2.x's
generic-method restriction) can be written as top-level functions and called
via UFCS (`op.longest_path(...)` still works):

```python
def longest_path(self: Optimizer[S, D, C], start_state: S, end_state: S,
                 max_path_length: int = 1000) -> (float, []D):
    """Find the highest-revenue simple path (defined outside the class so
    Nim emits 'proc' instead of 'method', avoiding Nim 2.x restrictions)."""
    ...
```

Nim output uses `[S, D, C]` generic parameters on the object type and all
generated procs.

---

## Memory Ownership

### Why ownership matters

Every value your program creates has to live somewhere.  Stack memory is freed
automatically when a function returns — fast, deterministic, zero overhead.
But if you want a value to outlive the function that created it, it needs
somewhere else to live: the heap.  Heap memory is flexible but requires
*someone* to free it eventually.  The three common strategies are:

| Strategy | Who frees | Risk |
|---|---|---|
| Manual (`malloc`/`free`, C) | You | Use-after-free, double-free, leaks |
| Garbage collection (Python) | Runtime (GC) | Pauses, non-deterministic |
| Ownership (Adascript/Nim ARC) | Compiler at end of owning scope | Deterministic, no GC pauses |

Adascript uses Nim's **Automatic Reference Counting / Ownership (ARC/ORC)**
as its memory model.  The ownership annotations are optional hints that make
intent clear and help the compiler elide copies.  The Python backend ignores
them (the GC handles everything); the Nim backend uses them to guide ARC.

### `own` declaration

Use `own` to declare a variable that is the *unique owner* of a heap value.
It is freed automatically when the variable goes out of scope.

```python
own buf: Buffer = Buffer(size=4096)
own name: str = "hello"
own xs: []int = [1, 2, 3]
```

Nim output:

```nim
var buf: Buffer = Buffer(size: 4096)  # ARC tracks the one owner
var name: string = "hello"
var xs: seq[int] = @[1, 2, 3]
```

Python output:

```python
buf: Buffer = Buffer(size=4096)  # GC tracks references as usual
name: str = "hello"
xs: list[int] = [1, 2, 3]
```

`own x: T` is syntactically identical to `var x: T` from the compiler's
perspective.  The word `own` is documentation — it signals to readers that
*this variable is responsible for the value's lifetime*.

### `lent` and `own` parameter modes

Two type modifiers express how a function relates to ownership of its
arguments:

```python
def read(data: lent Buffer) -> int:   # borrow: caller keeps ownership
    data.size

def consume(data: own Buffer):        # take ownership: callee is responsible
    pass
```

| Adascript | Nim | Python | Meaning |
|---|---|---|---|
| `param: lent T` | `param: T` | `param: T` | Read-only borrow; caller still owns the value |
| `param: own T` | `param: sink T` | `param: T` | Ownership transferred to the callee |
| `param: var T` | `param: var T` | `param: T` | The callee changes the caller's value |

**`lent T`** — the callee promises not to store or transfer the value; it
simply reads it.  Nim passes by value (ARC may optimise to a pointer); Python
passes by reference as usual.

**`own T` / `sink T`** — the callee takes responsibility for the value.  In
Nim this enables the "sink" optimisation: the caller's copy is moved rather
than copied.  In Python the annotation is stripped; the GC handles cleanup.

**`var T`** — the callee changes the value its caller passed: a field written,
or a method called that changes its object. A plain function works this out
from its body, and `var` there only says it. A method does not: an override
must take its parameters as the method it overrides does, so ady2nim refuses
a method that changes a by-value parameter, naming the `var` to declare, and
an override whose `var` parameters differ from its base's. A reference class
(`@virtual`) needs no `var`: the callee changes the object the caller holds.

```python
def process(buf: lent Buffer) -> int:
    buf.size                        # read only; caller's buf is still valid

def store(buf: own Buffer):
    self.cache = buf                # we keep it; caller's copy is moved
```

### `move()` — explicit ownership transfer

`move(x)` transfers ownership of `x` to the target.  After the call, `x`
should be considered invalid (it may be in a zeroed/moved-from state).

```python
own a: Buffer = make_buffer(1024)
own b: Buffer = move(a)            # a is now invalid; b owns the data
print(b.size)                      # 1024
```

Nim output:

```nim
var a: Buffer = make_buffer(1024)
var b: Buffer = move(a)            # Nim's built-in move()
echo(b.size)
```

Python output (annotation stripped, GC manages references):

```python
a: Buffer = make_buffer(1024)
b: Buffer = move(a)               # Python has no built-in move(); same as assign
```

### `drop()` — explicit early release

`drop(x)` destroys `x` immediately, before its natural scope end.  Use this
to release expensive resources (file handles, network sockets, large buffers)
as soon as you are done with them.

```python
own conn: Connection = Database.connect("...")
result = conn.query("SELECT 1")
drop(conn)                         # release connection now; don't wait for scope end
# conn is invalid here
do_other_stuff()                   # runs without holding the connection
```

Nim output:

```nim
var conn: Connection = Database.connect("...")
let result = conn.query("SELECT 1")
(block: `=destroy`(conn); `=wasMoved`(conn))  # Nim ARC hook
do_other_stuff()
```

Python output (GC handles cleanup — `drop` becomes a no-op comment):

```python
conn: Connection = Database.connect("...")
result = conn.query("SELECT 1")
(block: `=destroy`(conn); `=wasMoved`(conn))   # ignored by Python GC
do_other_stuff()
```

### `with own` — scoped RAII block

`with own x = expr:` creates a new scope.  `x` is initialised from `expr`
at entry and destroyed at exit — regardless of whether the body raised an
exception.  This is the Adascript equivalent of C++'s RAII or Rust's drop
at end of scope.

```python
with own conn = Database.connect("localhost"):
    rows = conn.query("SELECT 1")
    print(rows)
# conn is freed here
```

Nim output:

```nim
block:
    var conn = Database.connect("localhost")
    let rows = conn.query("SELECT 1")
    echo(rows)
# conn freed by ARC at end of block
```

Python output:

```python
conn = Database.connect("localhost")
try:
    rows = conn.query("SELECT 1")
    print(rows)
finally:
    del conn
```

The `with own` form is preferred over `try/finally` for resources because it
reads like a declaration ("I own this for the duration of the block") rather
than a cleanup obligation.

### Full example

```python
type Buffer_T is record:
    data: []int
    size: int

def make_buffer(n: int) -> Buffer_T:
    Buffer_T(data=[], size=n)

def summarise(buf: lent Buffer_T) -> str:
    f"Buffer({buf.size} slots)"

def main():
    own buf: Buffer_T = make_buffer(4)
    print(summarise(buf))           # Buffer(4 slots)

    with own tmp = make_buffer(2):
        print(summarise(tmp))       # Buffer(2 slots)
    # tmp freed here

    own buf2: Buffer_T = move(buf)  # buf is now invalid
    print(summarise(buf2))          # Buffer(4 slots)

    drop(buf2)                      # explicit early release
    print("done")

main()
```

Expected output:

```
Buffer(4 slots)
Buffer(2 slots)
Buffer(4 slots)
done
```

### Translation reference

| Adascript | Nim (ARC) | Python (GC) |
|---|---|---|
| `own x: T = expr` | `var x: T = expr` | `x: T = expr` |
| `param: lent T` | `param: T` | `param: T` |
| `param: own T` | `param: sink T` | `param: T` |
| `param: var T` | `param: var T` | `param: T` |
| `-> own T` (return) | `-> T` | `-> T` |
| `move(x)` | `move(x)` | `x` (alias; GC ref) |
| `drop(x)` | `(block: =destroy(x); =wasMoved(x))` | `del x` |
| `with own x = e:` | `block: var x = e; body` | `x=e; try: body; finally: del x` |

### Patterns in the example programs

The constructs above appear in the bundled examples — see `EXAMPLES/` for
complete, runnable code.

**`lent T` — read-only graph traversal (`graph.ady`, `dijkstra.ady`, `spell.ady`)**

All three traversal functions in `graph.ady` accept the graph by borrow because
they never modify it:

```python
def find_path(graph: lent Graph_T, start_node: Node_T, end_node: Node_T,
              path: []Node_T = []) -> ?[]Node_T:
    ...
```

`dijkstra.ady` does the same for its adjacency map, and `spell.ady` borrows the
candidate set in `known_variations`.

**`drop()` — eager cleanup after an algorithm finishes (`dijkstra.ady`)**

The working structures (`visited` set, priority `queue`) are only needed during
the search.  `drop()` releases them before the result is returned, rather than
leaving them alive until the caller's scope ends:

```python
def dijkstra(graph: lent Graph_T, start: Node_T) -> {Node_T}Distance_T:
    ...
    while queue:
        ...
    drop(visited)
    drop(queue)
    return distances
```

**`with own` — scoped board copy in backtracking search (`sudoku.ady`)**

The sudoku solver makes a temporary copy of the board for each speculative
branch.  `with own` ties the copy's lifetime to the recursion so it is freed
the moment the branch either succeeds or fails:

```python
for d in values[chosen]:
    with own attempt = {s: values[s] for s in squares}:
        attempt = assign(attempt, chosen, str(d))
        var result: {str}str = search(attempt)
        if result:
            return result
# attempt freed here — on every branch
```

Without `with own`, each copy would survive until the end of the enclosing
function, keeping up to 9×81 strings alive simultaneously during deep recursion.

### What the 20% leaves out

The ownership annotations in Adascript cover the common cases.  A few
advanced scenarios are not yet supported:

- **Cyclic data structures** — ARC cannot collect cycles; use `nimport
  system` and Nim's `ref` types with the ORC cycle collector directly.
- **Shared ownership** (`Arc<T>` in Rust, `shared_ptr` in C++) — not in
  Adascript; if you need this, write Nim directly.
- **Custom destructors** — Nim's `=destroy` hooks require writing Nim.  The
  `drop()` built-in calls `=destroy` but you cannot customise what it does
  from Adascript.
- **Borrow checker** — Adascript does not enforce borrow rules statically
  (Nim does not have a borrow checker either).  Misusing `move()` does not
  produce a compile-time error; the moved-from variable simply becomes a
  zero/nil value at runtime.

---

## HTML Pages: `html:` blocks

An `html:` block writes a page as indented tags, inside a method whose
result type is `Html`. The Nim backend turns it into a
[karax](https://github.com/karaxnim/karax) `buildHtml`, so `Html` is karax's
`VNode` and `$page` is the HTML text. Every expression in the block is
ordinary Adascript, checked like the rest.

```python
class Card:
    var title: str
    var items: []str
    var done:  bool

    def __init__(self, title: str, items: []str, done: bool):
        self.title = title
        self.items = items
        self.done = done

    def to_html(self) -> Html:
        html:
            div class="card":
                h2: self.title
                ul:
                    for item in self.items:
                        li: item
                if self.done:
                    span: "done"
                br
                button id="inc": "+1"
```

Line forms inside the block:

| Line                          | Meaning                                             |
|-------------------------------|-----------------------------------------------------|
| `tag a="x" b=expr:`           | a tag; its children are indented below              |
| `tag a="x": expr`             | a tag around one expression or string              |
| `tag a="x"`                   | a void tag (`br`, `hr`, `img`, `input`)             |
| `"text"` / `f"text"`          | text                                                |
| `+ expr`                      | another widget's `Html` goes here                   |
| `for` / `if` / `elif` / `else` / `while` | ordinary control flow around tags        |

An attribute value is a string or an expression (`id=self.id`); a space
ends it unless it is inside brackets or a string, so `x=str(a + b)`,
`class=("on" if lit else "off")` and `marker="url(#"+name+")"` each read
whole. `class` and `for` are fine as attribute
names, and `data-id` is written `data_id`. `style=` takes CSS text,
`style=f"fill: {c}"`. The text of a `style:` or
`script:` tag is written as it is, not escaped, so CSS keeps its `>` and
quotes. The block needs exactly one root tag.

**What the block accepts.** Expressions and control flow are Adascript; the
tag lines are the block's own. Four things follow:

- A tag's text is a string: `td: t.what` works, an `int` is written
  `td: str(n)` or `td: f"{n}"`.
- Only the line forms above: a `let`, an assignment or a bare call is not
  one of them, so it goes before `html:` (a function may hold any statements
  before its block).
- `case`/`when` does not work inside the block (its `when` lines are read as
  tags); use `if`/`elif`, or a helper function that returns the string.
- `+ expr` takes a name or a call on one: `+ part`, `+ child.to_html()`,
  `+ arrow_html(f, a, b)`. A call on a call's result (`+ f(x).to_html()`)
  is refused by karax, so bind it first; and a function named like a tag
  (`g`, `p`, `a`, `b`, `i`, `table` ...) is read as that tag.

**A page as a tree of objects.** Each object knows how to render itself, and a
parent asks its children for theirs with `+`:

```python
@virtual
class Widget:
    def to_html(self) -> Html:
        html:
            div class="widget"

class Panel(Widget):
    var title:    str
    var children: []Widget

    def to_html(self) -> Html:
        html:
            section class="panel":
                h2: self.title
                for child in self.children:
                    + child.to_html()
```

A `Panel` can hold a `Label`, a `Button` or another `Panel`: the call
dispatches on the object. `BROWSER_EXAMPLES/HTML/html_app.ady` is the whole
program, with an `App` that renders `html`, `head` and `body` around a
panel.

The same classes compile for the browser with `ady2nim js`, where the
karax tree is a live DOM. Needs `nimble install karax`. **Nim only**: the
Python backend does not know `html:`.

An `int` in the browser is a JavaScript number, exact to 2^53. Nim would check
it for overflow against 32 bits, so a sum past 2,147,483,647 (21 million in
cents) would stop the page; `ady2nim js` turns those checks off
(`#ady2nim-args js --overflowChecks:on` turns them back on).

**Events.** An attribute whose name starts with `on` is an event handler. Its
value is a call on the widget, with no arguments to write:

```python
from karax/karax nimport setRenderer

@virtual
class Counter:
    var count: int = 0

    def inc(self):
        self.count += 1

    def to_html(self) -> Html:
        html:
            div class="counter":
                h2: f"count: {self.count}"
                button id="inc" onclick=self.inc: "+1"

var counter: Counter = Counter()

def render() -> Html:
    return counter.to_html()

setRenderer(render)
```

The page is redrawn after every handler. A class whose handlers change its
own fields is `@virtual`, so the handler and the page share one object.
A page with a handler builds only under `ady2nim js` (`#ady2nim-args js` on
the second line); it needs a `<div id="ROOT">` and the compiled script in an
HTML file. `BROWSER_EXAMPLES/HTML/html_app.ady` and its `index.html` are the whole
program, and `make app` there serves it. Handlers that take the event object
are not built.

**The page, from a script.** A script built with `ady2nim js` reaches the
page through the standard library's `browser` module, in the page's own words
rather than JavaScript's: `page.find("#move")`, `page.all("g.node")`,
`node.data("name")` (what the server wrote in `data_name`), `node.has_class("from")`,
`form.fill("x", "120")`, `page.press("#redraw")`, and `send_request("PUT", "/nodes",
{"name": "A"}, "#all", "#state")`, which sends a request with no form or button for
it and puts the answer in the page, as htmx does. Its doc comment lists the rest.

**A function called with a dot.** Any function can be called on its first
argument with a dot (Nim's uniform call syntax): with

```python
def data_name(n: Element_T) -> str:
    return n.data("name")
```

`node.data_name` (or `node.data_name()`) is `data_name(node)`. That gives a
type the program did not declare, such as a page's `Element_T`, what reads like fields,
with no wrapper class around it. Both backends do this; ady2py does it where the
value before the dot is a name whose declared type is the function's first
parameter's, and the type has no field or method of that name.

**Pages the server draws.** When the server draws the page and htmx keeps it
current, the browser script holds only what must follow the mouse. `import
svg_drag` (`TO_NIM/STDLIB/svg_drag.ady`, built on `browser`) drags the shapes of such an SVG:
`draggable(shapes, svg, width, moved, dropped, clicked)`, where the three
functions say what a drag means to the app. Pixels and drawing units are
distinct types in it, with a scale between them. `BROWSER_EXAMPLES/DIJKSTRA_HTMX` and
`BROWSER_EXAMPLES/ACCOUNTING` are whole programs built this way.

**Data the server hands the script.** `import json_value`
(`TO_NIM/STDLIB/json_value.ady`) is the same code on the server and in the
browser: the server writes its records as JSON with `json_string` and plain
numbers, into a `<script type="application/json">` element, and the script
reads them back with `read_json(text)` (a `?Json_T`, None when it is not JSON)
and, by name, `json_list`, `json_text`, `json_number` and `json_flag`.
`BROWSER_EXAMPLES/ACCOUNTING` hands its accounts and arrows over this way.

### The look, in the class: `style` blocks

A class that draws something writes its look in its body, as a `style` block:

```python
from style import Look, Rule, Style

type Role_T is enum NO_ROLE, START, GOAL

class Node_View:
    style "g.node":
        &:                  cursor="grab"
        circle:             fill=PAPER stroke=RIM stroke_width=2
        &:hover circle:     stroke=INK
        [START] circle:     fill=PALE_GREEN stroke=GREEN stroke_width=4
```

The string is the scope, the selector of the class's element, and every rule
is under it: `circle` is a circle in the element, `&` the element itself
(`&:hover circle`, `&.selected circle`), `[START]` the element in a state, an
enum value whose class (`start`, `style.class_of(START)`) the element carries.
After the `:`, the properties are `name=value`, each value an expression and
each name a field of the stdlib's `Look` (`stroke_width` for
`stroke-width`), so a misspelt one does not compile. A value is a string as
CSS writes it, a length with its unit (`font_size="0.9em"`,
`margin="0 auto"`); `stroke_width` (pixels), `opacity` and `font_weight` are
numbers.

The page's own rules, for what is not drawn (the body, the buttons, the
tables), are a block with no scope, `style "":`, its selectors whole; a comma
joins two there (`header, #all:`), as in CSS:

```python
class Page_View:
    style "":
        body:               margin="0" font_family="Arial, sans-serif"
        header, #all:       max_width="1100px" margin="0 auto"
        button:             font="inherit" font_size="0.9em" border="1px solid #555"
        p.problem:empty:    display="none"
```

The block is the field `style`, a `Style` (`TO_NIM/STDLIB/style.ady`), made
for each instance; the page puts `view.style.css()` in its `<style>` once,
and an element carries only its class and its state. Both backends;
`TESTS/test_style_block.ady`; the four apps of BROWSER_EXAMPLES (DIJKSTRA_HTMX,
SVG_NODE_EDITOR, ROI_HTMX, ACCOUNTING) write all their CSS this way, each page's
own in a `Page_View`.

A view meant for many apps cannot take its colours from one app's constants,
so it builds its `Style` in its constructor, from the colours it is given:
the stdlib's `graph_views.ady` (`Node_View[State_T]`, `Edge_View[State_T]`)
does, with `mark(state, ...)` for the look of each of the app's states.

---

## Modules and Project Layout

Everything above describes one file. A program that outgrows one file splits
into modules, and `import` is how they find each other. ady2nim resolves,
transpiles and compiles a whole dependency graph; ady2py brings each module
into the one file it writes (see [Known Limitations](#known-limitations) for
what that costs).

A module is just a `.ady` file; there is no manifest and nothing to register.
`EXAMPLES/PROJECT/` is a complete four-file program:

```
EXAMPLES/PROJECT/
    dispatch.ady          # the program — import lib/geometry, lib/fleet, lib/report
    lib/geometry.ady      # leaf module: Point_T, distance(), bearing()
    lib/fleet.ady         # domain model — import geometry  (sibling, bare name)
    lib/report.ady        # formatting   — import geometry
    test_geometry.ady     # a second entry point: the unit test for lib/geometry
```

```bash
ady2nim c -r EXAMPLES/PROJECT/dispatch.ady
```

### Importing your own modules

```python
import geometry           # geometry.ady beside this file, or one directory up; use geometry.distance
import lib/fleet          # lib/fleet.ady — path form, written with '/'; use fleet.Depot
from geometry import distance, Point_T   # only these, unqualified, and what they carry
```

The rule is Python's. `import geometry` binds `geometry`, as `import geometry`
does, so the file writes `geometry.distance(a, b)`; for a path it is the last part,
`lib/fleet` is `fleet`. `from geometry import distance, Point_T` is `from geometry
import distance, Point_T`: the file may use `distance`, `Point_T` and what `Point_T`
carries (an enum's members; a record's fields and a class's methods are reached
through a value) without the prefix. `from geometry import *` is `from geometry
import *`. As in Python, only `import geometry` binds `geometry`: after `from geometry import
distance` alone, `geometry.distance` is refused, not accepted. A bare use of any other name of `geometry`'s is refused, on both
backends, with the line and what to do:

```
line 12: 'bearing' is not imported from geometry: add bearing to `from geometry import Point_T, bearing, distance`, or `import geometry` and write geometry.bearing
```

A name the file declares itself is not checked, so it cannot clash by accident;
but the file cannot then write `geometry.name` for a `name` of its own, since the
two are one namespace after the merge, and is told so.

Three words name three worlds, on both backends: `import` an `.ady` module,
`nimport` a Nim module, `pyimport` a Python package (via nimpy on the Nim
backend). A plain `import` of anything but an `.ady` module is refused, naming
the other two, and so is a `nimport` of an `.ady` module, naming `import`:

```
line 3: 'import os' is not allowed: os is not an .ady module. Use 'nimport os' for Nim/stdlib modules or 'pyimport os' for Python packages.
line 2: 'geometry' is an .ady module: write `import geometry`, `nimport` is for Nim modules
```

All three follow Python's rules. `nimport math` binds `math`, so the file writes
`math.sqrt(x)`, and a bare `sqrt` is undeclared; `from math nimport sqrt, floor` gives the
file `sqrt` and `floor` and nothing else of `math`'s; `from json nimport *` gives it the
whole module, as Python's star does. For the common modules (`math`, `os`, `time`,
`strutils`, `sequtils`, `random`, `algorithm`, `json`) a bare name is refused by Adascript, on
both backends, with the line and what to write; for any other Nim module Nim's own compiler does the
refusing, naming the bare name (Nim says this with `from math import nil` and `from math import sqrt, floor`).
A name the transpiler itself writes into the Nim (the `^` of `**`, a float `%`, `async`
and `await`) is imported for it, so the file does not have to list those. A rename in a
`from M nimport A as B` is not a thing Nim has, so it takes the whole module.

`import M as N` and `from M import A as B` rename, as in Python: `N.name`, and `B`
for `A`, and the old names `M` and `A` are then refused. `from stdlib import PriorityQueue` is the one exception to all this:
`stdlib` is a bundled shim with a Nim and a Python implementation.

### How a name is resolved

For every `import`, ady2nim looks for a matching `.ady` file in three places,
in order:

1. the directory of the file doing the importing,
2. that directory's parent,
3. the build cache, where the bundled `TO_NIM/STDLIB/*.ady` libraries live.

The first hit wins; if nothing matches, the name is handed to Nim untouched —
which is how `nimport strutils` reaches Nim's own module. There is no `..`
syntax; the parent rule covers the one level of escape a layout needs, and
it is what lets an entry point in `bin/` say `import lib/util`.

ady2py looks in the same two directories, then in `TO_PYTHON/STDLIB` (the Python versions of bundled libraries made of what only Nim has, such as `db`), then in `TO_NIM/STDLIB`. Both backends take the rule from one place, `GRAMMAR/ady_modules.py`'s `module_dirs`.

### Layouts that work

| Layout | When | Example |
|--------|------|---------|
| Flat — every module in one directory | up to a dozen modules | `EXAMPLES/CFMU/` (17 scripts over `ftps_common.ady`) |
| Entry point at the root, modules in `lib/` | modules with their own relationships | `EXAMPLES/PROJECT/` |
| `bin/` programs, `lib/` modules | several programs, one library | resolved by the parent rule |

Modules address each other by bare name (siblings); the program addresses
them by path from the project root (`lib/geometry`).

### The build

```
ady2nim c -r EXAMPLES/PROJECT/dispatch.ady

# transpiled → ~/.cache/adascript/cache-<HASH>/dispatch.nim
# transpiled dependency → ~/.cache/adascript/cache-<HASH>/lib/geometry.nim
# transpiled dependency → ~/.cache/adascript/cache-<HASH>/lib/fleet.nim
# transpiled dependency → ~/.cache/adascript/cache-<HASH>/lib/report.nim
# nim c --nimcache:… --out:…/.dispatch --path:…/cache-<HASH> …/dispatch.nim
```

1. ady2nim walks the `import` graph breadth-first and pre-parses every
   dependency, collecting what importers need: class names, constructor
   signatures, `ref`/virtual classes, return types, and the field order of
   records and named tuples.
2. Each dependency is transpiled into the entry point's cache directory with
   Nim export markers (`proc distance*`), mirroring any subdirectory in its
   name.
3. One `nim c` compiles the graph, with `--path:<cache dir>` so
   `import lib/geometry` resolves inside the cache.

The cache directory is keyed by a hash of the entry point's absolute path and
the backend, so each program gets its own; nothing but the binary symlink is
written next to your sources. Rebuilds follow the same three mtime tiers as a
single file: a dependency edited at any depth re-triggers the compile.
`ady2nim -t` runs the transpile step for the whole graph and stops.

### What crosses a module boundary

Types (records, named tuples, enums, subranges, classes), procs, iterators,
constants and `let` bindings — plus the two pieces of knowledge the
transpiler needs to keep its rewrites working across files:

```python
# lib/fleet.ady declares the record and the class
type Vehicle_T is record:
    name: str
    position: Point_T
    fuel: float

# dispatch.ady builds both — field order and constructor signature travel
# with the type, so the positional forms work in the importer too
let spare: Vehicle_T = Vehicle_T("van-9", (x: 2.0, y: 2.0), 6.0)
var d:     Depot     = Depot("Central", base)       # -> newDepot("Central", base)
```

What else the module's own translation learned travels with it too: which
names are enums (so `Energy_T("ELECTRIC")` in the importer is a parse of
the name), the types of its globals and type aliases, the routines that
never return (a `die`-like helper), its iterators, and which of its procs take
nothing as `var`. So do the standard modules behind its containers and
strings (`tables`, `sets`, `deques`, `heapqueue`, `options`, `strutils`,
`sequtils`, `std/paths`): Nim's imports are not transitive, so an importer
asking `"van-7" in d.fuel_of` of a module's table needs `tables` as much as
the module did, and gets it without a `nimport tables` of its own. Its other
imports stay its own -- `times` would bring a `Days` that is `DAYS` to Nim.

Inheritance works across files as well: a `@virtual` base class in one module
and a subclass in another (that is `TESTS/test_awk.ady` over the bundled
`awk.ady`), including the inherited constructor.

### Rules to respect

- **Module top-level code runs at import time**, before the program's first
  line — modules declare, programs act.
- **Keep the graph acyclic.** Give the project a leaf module for shared
  types. Nim tolerates some mutual imports, but a cycle involving type
  declarations does not resolve.
- **Basenames must be unique across the project** — dependencies land in one
  cache directory, keyed by the name they were imported by.
- **A basename cannot be a Nim keyword.** `mod.ady` fails with
  ``Error: invalid module name: `mod` ``.
- **Exported names share one namespace.** Nim overloading absorbs most of it;
  rename the rest.
- **A module test is just another entry point** that imports the module and
  asserts — see `EXAMPLES/PROJECT/test_geometry.ady`.
- **ady2py merges rather than links.** It replaces an `import` of an `.ady` module by the module's text (once), so a program split across modules runs on both backends, the bundled libraries too. A name two imported modules both define is refused where it is used bare, on both backends, naming both; `geometry.distance` beside a `distance` of the file's own is kept apart on Python by merging the module's as `geometry__distance`, in every file that takes it.

Full treatment, with the layouts and failure modes worked through:
[The Adascript Book, Chapter 14 — Programming in the Large](DOCS/BOOK/14-programming-in-the-large.md).

---

## Nim-Only Imports

`nimport` marks imports of *Nim* modules: they appear only in Nim output and are
stripped from Python output. Use it for Nim standard-library modules that have no
Python equivalent (an `.ady` module is `import`ed, a Python package `pyimport`ed):

```python
nimport strutils, sequtils, algorithm, stdlib
```

One Nim module is shared: Nim's `math` is Python's under other spellings, so `nimport math` (`math.arctan(x)`) and `from math nimport sqrt, arctan2, PI` build with ady2py too, Nim's names taken as Python's (`arctan2` is `atan2`, `PI` is `pi`).

On one line each, the three kinds of import look like this:

```python
nimport strutils, sequtils, algorithm
nimport stdlib                      # PriorityQueue, FifoQueue, ANY shims
from awk import AwkProcessor            # the bundled record-processor stdlib
from shortest_path import Minimizer, Maximizer   # another .ady file compiled as a library
```

When `import`-ing another `.ady` file, `ady2nim` automatically transpiles that dependency (if not already cached and up to date) and places both `.nim` files in the same cache directory, wiring up `--path` for the Nim compiler.

### Bundled libraries

The files in `TO_NIM/STDLIB/` are installed into the build cache, so they are
reached from any directory without a local copy. The `.ady` ones are imported with
`import`, the `.nim` ones with `nimport`:

| Name              | Provides                                                  |
|-------------------|-----------------------------------------------------------|
| `import awk`      | `AwkProcessor` — the record loop (`run`: `get_record`, `process_record`), with `StdinProcessor`, `FileProcessor` and `TextProcessor` for where the records come from |
| `import iters`    | itertools equivalents (`take`, `chunks`, `pairwise`, …), generic over the element type |
| `import strscan`  | character classification and the small scanners a hand-written lexer needs (`is_digit_ch`, `skip_quoted`, `lead_ident`, `strip_line_comment`, …) |
| `import ansi`     | terminal colours and effects as values a pipe applies: `"x" \| bold \| fg_white \| bg_red` (`fg_*`, `fg_bright_*`, `bg_*`, `bold`, `dim`, `blink`, `inverted`, `reset`); `bold + fg_red` is one style with both codes |
| `import graphs`   | `dijkstra`, `shortest_path` and `shortest_route` (with its cost) over a weighted digraph, generic in the node type |
| `import db`       | thin SQLite wrapper                                        |
| `import jointjs`  | `JsElem` base class and helpers for JointJS applications   |
| `import browser`  | (js) the page in plain words, for a script in the browser: `page.find(css)`, `page.all(css)`, `node.data("name")`, `node.has_class(c)`, `form.fill(name, value)`, `page.press(css)`, `send_request(method, url, fields, target, include)`, a `Click` |
| `import svg_drag` | (js) drag the shapes of a server-drawn SVG with the mouse: `draggable(shapes, svg, width, moved, dropped, clicked)`, pixels and drawing units as distinct types; `BROWSER_EXAMPLES/DIJKSTRA_HTMX` and `BROWSER_EXAMPLES/ACCOUNTING` use it |
| `import svg_path` | paths for an SVG drawing, as the `d` of a `<path>`; plain arithmetic, so it compiles both to C and to JavaScript: `connector_d(x1, y1, x2, y2, leave, stop_short)`, an S-shaped curve between two boxes; `BROWSER_EXAMPLES/ROI_HTMX` uses it |
| `import commands` | the vocabulary a page and its server share, compiled both ways: the verbs `CREATE`, `READ`, `UPDATE`, `DELETE`, a `Command_Of[Thing_T]` the app's things (its fields: `c.value(name)`, `c.method()`, `c.is_draft()`, `c.spot()`), and the `Change` a server publishes; the four htmx apps of `BROWSER_EXAMPLES` use it |
| `import page_server` | (c) what every server of an htmx page does the same: `News` (the pages following `GET /events`: `follow`, `tell`), `send_script`, `port_of` |
| `import page_request` | (c, js) a request as the page sent it: `Page_Request` (its method, path and fields, read once from the query and the body: `field`, `number_field`) |
| `import page_alone` | (js) an htmx page with no server: `serve_in_page(answer, shell)` answers every request the page makes with the app's own session, in the page, and writes the page; `tell_page` tells it a change, as `GET /events` would; `ady2nim js` keeps such a script's names to itself, beside the page's own (DIJKSTRA_HTMX's `make alone`) |
| `from style import Look, Rule, Style` | (c, js) the look of what a class draws, written in the class as a `style` block (see [The look, in the class](#the-look-in-the-class-style-blocks)): a `Style(scope, rules)`, each `Look` property named as in CSS (`stroke_width`), `css()` for the page's `<style>`, once per class; `part` and `when` add a rule in code |
| `from graph_views import Graph_Palette, Node_View, Edge_View` | (c, js) a graph's node and edge drawn as SVG, reusable by any app: `to_html` takes only what drawing needs (a label, a `Spot_T`, a state of the app's own enum); the colours are a `Graph_Palette` given to the constructor, and `mark(state, ...)` says what a state looks like; `css()` for the page's `<style>`. BROWSER_EXAMPLES/DIJKSTRA_HTMX draws with it |
| `from store import Store` | (c, js) texts kept by name from one run to the next: `Store(place)` with `names`, `read`, `write`, `drop`; natively the files of a directory, under `ady2nim js` the browser's storage under the place's name, and `Store("")` in memory (for tests) |
| `import server_page` | (c) the page a server draws, in the page's own words: `Page_Of[Thing_T]` writes the htmx attributes from a command, so an app's gui says only which command each part sends: `button`, `sending` (any element), `on_change` (a field or a form), `every` (a tick), `shell_text` (the first page, which loads the rest) |
| `import page_board` | (js) the blackboard of an htmx page's script: `Page_Channel_T` (`COMMANDS`, `CHANGES`), `changes_channel` (what the server says changed, from `GET /events`), and `Liaison_Officer[Thing_T]`, the observer that sends each command to the server but a draft |
| `nimport illwill` | [illwill](https://github.com/johnnovak/illwill), a curses-like terminal library in pure Nim (one file, WTFPL): non-blocking keys, a screen buffer that writes what changed; `EDITORS/VI/vi_curses.ady` uses it |
| `nimport expect`  | `Spawn`, `send`, `expect` PTY automation                   |

`stdlib.nim` in the same directory is a Nim shim for a few Python builtins
(`PriorityQueue`, `FifoQueue`, `ANY`) that generated code relies on.

Example — a custom awk processor in any directory:

```python
#!/usr/bin/env ady2nim
from awk import StdinProcessor, AwkRecord_T, AwkFailure_T

class WordCounter(StdinProcessor):
    var word_count: int = 0

    def process_record(self, rec: AwkRecord_T):
        self.word_count += rec.NF

    def finish(self):
        print f"total words: {self.word_count}"

var wc: WordCounter = WordCounter()
let done: None | !AwkFailure_T = wc.run()
if done is AwkFailure_T:
    die(done.reason)
```

### Splitting a library from its tests

**shortest_path.ady** (the library, decorated with `@virtual`):

```python
#!/usr/bin/env ady2nim
#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc

nimport stdlib

@virtual
class Optimizer[S, D, C]:
    var offset: float
    ...
```

**shortest_path_demo.ady** (the test file):

```python
#!/usr/bin/env ady2nim
#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc

nimport stdlib
from shortest_path import Optimizer   # triggers auto-transpilation of shortest_path.ady

class MyOptimizer(Optimizer[str, str, float]):
    ...
```

---

## Raw Nim Injection

A comment of the form `# nimraw: <code>` is passed through verbatim to the
Nim output and stripped from Python output, for Nim that has no Adascript
spelling -- a pragma, say:

```python
# nimraw: {.push overflowChecks: off.}
def hash_step(h: int, c: int) -> int:
    return h * 31 + c
# nimraw: {.pop.}
```

Forward declarations are not needed. Definition order does not matter, as in
Python: a function may call one defined further down -- two mutually
recursive functions included -- and a class may use a class defined below
it. The Nim backend declares each routine ahead of its first caller and puts
every type in one `type` section.

The transpiler replaces each `# nimraw:` line with the raw code that follows
the prefix, leaving Python output unaffected (Python ignores the comment).

Use `# nimraw:` sparingly — it bypasses the type system and produces Nim-only
output. For most Nim-specific needs, prefer `nimport` or `#ady2nim-args`.

---

## Python Interoperability

A Python package is `pyimport`ed, through the
[nimpy](https://github.com/yglukhov/nimpy) bridge on the Nim backend; a Python
module the Nim backend maps natively is `nimport`ed (`nimport os`), and the table
below shows what each of those becomes. (`import` is for `.ady` modules.)

> **Before reaching for `pyimport`:** it is for libraries with no
> equivalent here — `numpy`, `requests`, a vendor SDK. Try things in this
> order.
>
> **`nimport` first.** `os` and `time` are mapped natively, so `os.getpid()`
> and `time.time()` are ordinary calls that cost the build nothing —
> `getCurrentProcessId()` and `epochTime()` on Nim, Python's own on the
> other side. Changing `pyimport` to `nimport` is often the whole fix.
>
> **Then the shell,** for what has no mapping: `date +%Y-%m-%d-%H%M%S` for a
> formatted stamp, `uname -s`, `id -un`, `mktemp -d`, `$HOME`, `-f`/`-d`.
> Regexes need neither — matching is an operator here, so `pyimport re` has
> no use at all. (Watch `$PPID`: `$NAME` reads the *environment*, and no
> shell exports `PPID`, so a bare `$PPID` is always `""`.)
>
> **Then `pyimport`,** knowing it costs the Nim build a nimpy dependency and
> a libpython link. `DOCS/ADASCRIPT_FOR_SHELL.md` §11 has the table, and
> `EXAMPLES/pyimport_similar.ady` is the worked example of an import that
> *is* worth it.

### Natively mapped stdlib modules

A Nim module is `nimport`ed. These are written with the name Python gives them
and translate directly to their Nim counterparts with no runtime overhead:

| You write            | Nim imports           | Notes                            |
|----------------------|-----------------------|----------------------------------|
| `nimport os`         | `import os`           | `os.path.*` → Nim path procs     |
| `nimport math`       | `import math`         | All standard functions mapped    |
| `nimport time`       | `import times`        | `time.time()` → `epochTime()`    |
| `nimport random`     | `import random`       | `random.rand(n)`                 |
| `nimport json`       | `import std/json`     |                                  |
| `nimport itertools`  | `import sequtils`     |                                  |
| `nimport asyncio`    | `import asyncdispatch`|                                  |

`nimport re` is not on the list: there is no Nim `re` here, so it reaches Python's
through nimpy, and the native `/pat/` literals replace it. `sys.exit` needs no import
at all.

### Function call translation

```python
nimport math, time, random

x = math.sqrt(4.0)
t = time.time()
n = random.rand(100)
```

**Nim output:**

```nim
import math, random, times

var x = sqrt(4.0)
var t = epochTime()
var n = rand(100)
```

### `os` and `sys` utilities

```python
nimport os

if os.path.exists('/tmp/data'):
    p = os.path.join('/tmp', 'data', 'out.txt')
    os.makedirs('/tmp/data')

sys.exit(1)
```

**Nim output:**

```nim
import os, strutils

if adascriptExists("/tmp/data"):   # fileExists or dirExists, a helper the output defines
    var p = joinPath("/tmp", "data", "out.txt")
    createDir("/tmp/data")

quit(1)
```

### Non-native Python libraries (nimpy bridge)

A library with no Nim equivalent is a `pyimport`, and comes in through nimpy:

```python
pyimport requests
pyimport pandas as pd

r  = requests.get("https://example.com")
df = pd.read_csv("data.csv")
```

**Nim output:**

```nim
import nimpy

let requests = pyImport("requests")
let pd       = pyImport("pandas")

var r  = requests.get("https://example.com")
var df = pd.read_csv("data.csv")
```

### Automatic `.to(T)` coercion

When a variable has a primitive type annotation and its right-hand side
comes from a `PyObject` call chain, `.to(T)` is injected automatically:

```python
pyimport requests

r     = requests.get("https://api.example.com/data")
count: int   = r.json()["total"]
score: float = r.json()["score"]
name:  str   = r.json()["name"]
```

**Nim output:**

```nim
var count: int   = r.json()["total"].to(int)
var score: float = r.json()["score"].to(float)
var name:  string = r.json()["name"].to(string)
```

You can write `.to(T)` explicitly if you prefer — the transpiler will not
double-wrap it.

### Calling Python callables from Nim

When a variable holds a callable `PyObject` (e.g. a fitted model, compiled
regex, scipy interpolator), calling it emits `callObject()` automatically:

```python
pyimport scipy.interpolate as interp

f   = interp.interp1d(x_points, y_points, 'linear')
val: float = f(1.5)
```

**Nim output:**

```nim
var f   = interp.interp1d(x_points, y_points, "linear")
var val: float = callObject(f, 1.5).to(float)
```

### `len()` helper

When nimpy is active and `len()` is called on a `PyObject`, a thin helper
proc is emitted automatically — only when needed:

```nim
proc len(o: PyObject): int = pyBuiltinsModule().len(o).to(int)
```

---

## Print Statement

Adascript supports Python-2-style `print` without parentheses. The
transpiler rewrites it to `print(...)` in Python 3 and `echo(...)` in Nim:

```python
print "hello"
print f"result: {value}"
print "x =", x
```

The call form `print(...)` still works unchanged — the parser only
intercepts `print` when it is *not* immediately followed by `(`.

---

## Unions: `A | B`

A union holds one of its members, and the value says which. What is
assigned or returned becomes the member its type names; `x is int` asks
which member x holds and narrows x to it; `case x:` gives a branch per
member, and must name them all or say `when others:`.

```python
def compute(n: int) -> int | float:
    if n % 2 == 0:
        return n // 2              # an int
    return n / 2                   # a float

let x: int | float = compute(5)
case x:
    when int:
        print f"int {x + 1}"       # x is the int here
    when float:
        print f"float {x * 2.0}"   # and the float here
```

Any number of members, and a union can be named: `type Number_T is int |
float`. The members must be told apart at run time -- `[]int | []str` and
`int | bool` are refused. `T | None` is `?T`, and a union with a failure
member is a value-or-failure (next section). Python holds the member
itself; Nim holds stdlib.nim's `OneOf2[A, B]`. The book's section 4.4 has
the whole of it; `TESTS/test_union.ady` is the spec.

**Which test says what.** `x is A` asks about the *type*: `A` is a type, and
inside the branch `x` is an `A`, with no cast and no second variable.
`x == A` asks about the *value*: `A` is a value, an enum member or a
constant. `case x:` does the one the subject calls for. Over a union every
`when` names a member type (or `None`), so it is a type test and narrows
`x`; over an enum, an int or a string it compares values, `when RED`,
`when 3`. A union is never matched by value, so there is nothing to confuse:
test the type, then use the value.

Members that are handled alike share a branch: `when Circle_T | Square_T:`
runs one body for either. It is checked once for each member, so it may use
only what both have (`x.delete()` if both define `delete`), and it is a
compile error where one of them does not.

For why a union of records is preferred to a variant record or a class hierarchy,
see [UNION_TYPES.md](DOCS/UNION_TYPES.md).

---

## Failures as Values: `T | !F`

**Adascript prefers a failure value to an exception.** A function that can
fail says so in its return type: `-> int | !Failure_T` returns an int, or a
failure saying why there is none. The caller takes the result and either
handles it right there, so the intent is explicit and the handling is local,
or passes it up:

```python
let res: int | !Failure_T = read_number(text)
if res is Failure_T:
    die(res.detail)       # handled where the call is
print res + 1             # res is the int from here on

def total(a: str, b: str) -> int | !Failure_T:
    do:
        x <- read_number(a)   # a failure ends total and goes to
        y <- read_number(b)   # its caller, as it is
    return x + y
```

Passing up costs a `do:` step, and it is visible: `total`'s signature says it
can fail, so every caller knows to decide where it is handled. An exception
also travels up, but through functions that say nothing about it, and is
caught, if it is, somewhere else. The built-ins are written this way --
`shell:` and the `Path` operations that can fail (`mkdir`, `relative_to`,
`read_text`, `read_lines`, `write_text`) return a `T | !ShellFailure_T` or
`T | !PathFailure_T` -- as are `parse_float(s)`, `parse_int(s)` and
`parse_enum(E, s)` (`... | !ParseFailure_T`), for a number or an enum member read from text
(`s` a name, or an integer read as the member's value),
and `input(prompt)` and `stdin.readLine()`, a `str | !InputFailure_T` (the input ended) --
and a failure that is dropped is refused. Exceptions
are for what nobody expected; `readFile`, `writeFile` and `for line in
p.lines:` are the older forms that still raise.

A failure is an ordinary record; the `!` in front of it, not the order of the sides, says
which side is the failure -- the one a `do:` block passes on.

```python
type ErrKind_T is enum BAD_NUMBER, DIVIDE_BY_ZERO, NOT_POSITIVE

type Failure_T is record:
    kind:   ErrKind_T    # which failure
    detail: str          # what it needs to say so

def fail(kind: ErrKind_T, detail: str) -> Failure_T:
    """A Failure_T -- a helper, so that each failure is one short line."""
    return Failure_T(kind=kind, detail=detail)

def read_number(s: str) -> int | !Failure_T:
    if len(s) == 0:
        return fail(BAD_NUMBER, "empty")      # a Failure_T: the failure
    for c in s:
        if not (c >= '0' and c <= '9'):
            return fail(BAD_NUMBER, f"'{s}' is not a number")
    return int(s)                             # anything else: the value

def divide(a: int, b: int) -> int | !Failure_T:
    if b == 0:
        return fail(DIVIDE_BY_ZERO, f"{a} / 0")
    return a // b

def check_positive(n: int) -> None | !Failure_T:
    """A step with nothing to return: it can only fail."""
    if n <= 0:
        return fail(NOT_POSITIVE, f"got {n}")
```

`fail` is an ordinary function, not part of the language: a failure is a
record, and returning one is returning the record. `None | !Failure_T` is a
step that can only fail; falling off its end is success.

| You write | It means |
|---|---|
| `r is Failure_T` / `r is int` | which side r holds -- and r is narrowed to it, as `x is None` narrows a `?T` |
| `case r:` / `when Failure_T:` / `when int:` | a branch per member; all of them, or `when others:` |
| `None \| !Failure_T` | a step that can only fail; falling off the end is success |
| `do:` / `x <- step` | bind the value, or return the failure from the whole function |
| `do:` / `x <- step else e` | a step that fails some other way -- a `?T`, another failure type, a shell command -- returns `e` instead; inside `e`, `x` is the step's own failure |
| `let o: str \| !ShellFailure_T = shell: cmd` | a command's output, or the built-in `ShellFailure_T` (`command`, `code`, `stderr`) |

The functions above chain in a `do:` block, which stops at the first
failure and returns it; the caller then asks which it got:

```python
def ratio(raw_a: str, raw_b: str) -> int | !Failure_T:
    do:
        a <- read_number(raw_a)
        b <- read_number(raw_b)
        q <- divide(a, b)
        check_positive(q)          # a `None | !Failure_T` step: checked, binds nothing
    return q

for pair in [("20", "4"), ("20", "0"), ("x", "4")]:
    let r: int | !Failure_T = ratio(pair[0], pair[1])
    case r:
        when int:
            print f"ratio {r}"                   # r is the int here
        when Failure_T:
            print f"failed: {r.detail}"          # and the failure here
```

The transpiler refuses a union with two failure members, a failure dropped
(a bare call whose `T | !F` result nobody takes), a `do:` step that fails
some other way without an `else`, and a `case` that leaves a member out.
A failure union may have several value members: `int | str | !Failure_T`. With `None` in place of a failure, the `|` is `?T`: `?T` is
shorthand for `T | None`.

**Forgetting the `!`.** Once a type is marked `!` anywhere, a union that
mentions it unmarked is refused, so the usual slip does not build. A type
marked nowhere is no failure: `int | Failure_T` is then a plain union of
two values, a dropped call to it goes unnoticed, and a `do:` step on it is
refused. And `None | Failure_T` without the mark is `?Failure_T` -- an
optional, which anyone may ignore: nothing refuses dropping it. Book
chapter 10.12, *Forgetting the `!`*, has the details.

On Python the value is the T or the F itself; on Nim it is stdlib.nim's
`Result[T, F]`, and `r` reads as its `.value` or `.error` where a test has
narrowed it. The whole of it is in the book, chapter 10.12;
`TESTS/test_result.ady` is the spec, and `TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady`
a full-size program written this way.

---

## Shell Statements

Adascript has first-class syntax for running shell commands. The `shell` and
`shellLines` keywords integrate subprocess execution directly, with variable
interpolation, output capture, and options for working directory and timeout.

### Basic usage

```python
let result = shell: echo hello
print(result.output)   # stdout as a string
print(result.stderr)   # stderr as a string
print(result.code)     # exit code as int
```

The streams are captured **separately**: `.output` is stdout alone, what the
command complained about is in `.stderr`, and neither reaches the terminal.
A capturing form therefore needs no `2>/dev/null` — the error a failing
command prints is already out of the way:

```python
let r = shell: rg FATAL {logfile}      # no redirect needed;
                                       # rg's "No such file" is in r.stderr
```

`shellLines:` behaves the same — a failing command gives an empty `[]str`,
not a list containing the error text.

The forms that keep the terminal (`shell: cmd` on its own, and
`let code: int = shell: cmd`) pass both streams straight through, so there
a `2>/dev/null` still does what it says.

### Variable and expression interpolation

Use `{name}` anywhere in the command body to interpolate an Adascript variable.
Function calls and other complex expressions also work inside `{}` — the
transpiler hoists them to temp variables automatically:

```python
let name: str = "world"
let result = shell: echo hello {name}

shell: mkdir -p -- {!os.path.join(d, "subdir")}
```

Braces that belong to the command stay braces. A `{` right after `^` or `@`
is git's revision syntax and is never an interpolation, whatever else the
line interpolates. Any other literal brace in a line that also interpolates
is written twice, `{{` and `}}`:

```python
let c = shell: git -C {!repo} rev-parse {!tag}^{commit}   # also X^{}, @{u}, HEAD@{1}
```

Backslashes are the shell's too: a shell line is not an Adascript string,
so `\b`, `\t` and `\s` reach the command exactly as written, on both
backends.

```python
let n = shell(stdin = words): grep -c '\bcat\b'
```

### Output as lines

`shellLines` captures stdout and splits it into `[]str`, one element per line.
The assignment target supports type annotations, bare names, or `let`/`var`/`const`:

```python
let lines = shellLines: ls -la
for line in lines:
    print(line)

let entries: []str = shellLines: ls -1a /tmp
output = shellLines: find . -name "*.ady"
```

### Exit code with the terminal left alone

An `int`-typed target runs the command with stdin, stdout and stderr
inherited — its output, colours and pager reach the user directly — and
returns the exit status:

```python
let code: int = shell: git log --oneline
```

`let r = shell:` captures instead, and gives `.output`, `.stderr`, `.code`.

### Quoting an interpolated value

`{expr}` interpolates the value as written, which is what a command fragment
needs. `{!expr}` quotes it, so a path holding spaces or shell metacharacters
arrives as a single argument:

```python
let f: str = "my notes.txt"
shell: ls -l {!f}              # ls -l 'my notes.txt'
shell: ls -l {f}               # ls -l my notes.txt   — two arguments
```

For a whole argument list, `{*xs}` quotes each element and joins them:

```python
let args: []str = ["commit", "-m", "two words"]
shell: git {*args}             # git commit -m 'two words'
```

Nim emits `quoteShell(expr)` and `mapIt(xs, quoteShell(it)).join(" ")`;
Python `shlex.quote(expr)` and `' '.join(...)`.

### Failing on a non-zero status

`check = true` raises when the command fails, instead of leaving the status
to be inspected — `OSError` on the Nim backend, `CalledProcessError` on
Python, both catchable:

```python
shell(check = true): git commit -m {!msg}

try:
    shell(check = true): exit 9
except:
    print "handled"
```

It works with every form: bare, capture, tuple, `shellLines:` and an
`int`-typed target.

### A command's output, or its failure: `ShellFailure_T`

`check = true` ends the program; a `T | !ShellFailure_T` target hands the
failure back instead. The command holds its output when it succeeds, and
the built-in failure record `ShellFailure_T` -- `command`, `code`,
`stderr` -- when it does not. `str` is the output, `[]str` its lines
(`shellLines:`), `None` nothing:

```python
let hi: str | !ShellFailure_T = shell: echo hi
let oops: str | !ShellFailure_T = shell: echo oops >&2; exit 3
if oops is ShellFailure_T:
    print f"exit {oops.code}, stderr {oops.stderr.strip()}"
let quiet: None | !ShellFailure_T = shell: true
```

In a `do:` block a command is a step -- `out <- shell: cmd`, or a bare
`shell: cmd` -- and a failing one stops the chain. A program with a failure
type of its own says once how a command's failure becomes one, and names
that after `else`; inside the `else`, the step's name is the failed
command:

```python
type Failure_T is record:
    detail: str

def cmd_failed(f: ShellFailure_T) -> Failure_T:
    return Failure_T(detail=f"`{f.command}` exited {f.code}: {f.stderr.strip()}")

def make_dir(path: Path) -> None | !Failure_T:
    do:
        r <- shell: mkdir -p -- {!path} else cmd_failed(r)

let made: None | !Failure_T = make_dir(Path("/proc/no-such-dir"))
if made is Failure_T:
    print made.detail
```

In a `do:` step, a command ends at a bare `else`. See [Failures as
Values](#failures-as-values-t--f).

### Feeding a command's input

`stdin = expr` sends a string to the child:

```python
let text: str = "gamma\nalpha\nbeta\n"
let r = shell(stdin = text): sort        # r.output is alpha, beta, gamma
```

It applies to the capturing forms — record, tuple, `shellLines:` — since
those are the ones that give the child a pipe; on a bare `shell:` it is a
transpile-time error rather than a silently ignored option. When no `stdin`
is given, a captured command sees EOF straight away rather than waiting on a
terminal.

An `int`-typed target takes it too:

```python
let rc: int = shell(stdin = pod_text()): pod2text | more -f
```

That form keeps the terminal, so there is no pipe to write into: the text
goes to a temporary file and the command is redirected from it, braced first
so a pipeline reads the text at its *first* stage. The file is removed when
the command ends.

### Setting the child's environment

`env = expr` takes a `{str}str` and **adds** to the environment the child
inherits, rather than replacing it:

```python
let extra: {str}str = {"GIT_DIR": repo, "LC_ALL": "C"}
let r = shell(env = extra): git status
```

Names already in the environment are overridden; everything else — `PATH`
included — is still there. Unlike `stdin`, it applies to every form.

### Reading output as it arrives

The capturing forms wait for the command to finish. `shellIter` yields each
line as the command prints it:

```python
for line in shellIter: tail -f build.log
    print line
```

Only stdout is streamed, so a command whose output you also want captured
wants a capturing form. Interpolation works as usual, `{!x}` and `{*xs}`
included, and `cwd`, `env` and `pipefail` apply:

```python
for line in shellIter(cwd = src, env = e): make -j4
    print line
```

`check = true` raises when the command ends badly — once the stream is over,
since that is when the status exists:

```python
for line in shellIter(check = true): make -j4
    print line
# raises here if make failed
```

It applies to a loop that ran to completion. Breaking out early leaves the
command unfinished, and an unfinished command has no status to object to, so
a `break` never raises.

### Leaving the shell out: `run` and `runLines`

Every `shell:` form builds a command line and hands it to `/bin/sh`, so the
shell parses it and quoting is the caller's problem. `{!x}` and `{*xs}` solve
that — but only when remembered. `run` takes an argument list instead, and
there is nothing to quote because nothing parses the arguments a second time:

```python
let r: RunResult = run(["git", "commit", "-m", msg])
print r.output, r.code
let names: []str = runLines(["ls", dir])
```

The difference shows up on a value that is also shell syntax:

```python
let nasty: str = "; rm -rf ~"
run(["ls", nasty])        # ls complains about a file named "; rm -rf ~"
shell: ls {nasty}         # the shell runs it
shell: ls {!nasty}        # quoted — safe, if you remember the !
```

`run` returns the same record as `shell`: `.output`, `.stderr`, `.code`. Its
type is spelled `RunResult` where a binding needs an annotation. `runLines`
returns `[]str`. Both take the same options, as keyword arguments rather than
in parentheses before the colon:

```python
let r: RunResult = run(["make", "-j4"], cwd = src, env = e,
                       stdin = text, timeout = 30000, check = true)
```

A program that isn't there reports 127 and a timeout 124, the way a shell and
`timeout(1)` do, so the two families agree on what a failure looks like.

Reach for `shell:` when you want a shell — pipes, redirection, globbing,
`&&`. Reach for `run` when you just want to run a program, which is most of
the time.

### Pipelines: `pipefail`

A pipeline's exit status is its *last* command's, which is what POSIX says
and almost never what a script means:

```python
let r = shell: false | cat
print r.code                      # 0 — the failure vanished
```

`pipefail = true` reports the first command that failed instead:

```python
let r = shell(pipefail = true): grep -q pat file | sort | uniq
print r.code                      # non-zero if grep failed
```

`/bin/sh` is dash on most Linuxes and has no `set -o pipefail`, so both
backends run these through bash — which therefore has to be installed for
this option, and a missing one reports 127 like any other missing program.
It combines with `check = true`, which is usually what you want.

### Block form: choosing the joint

An indented block joins its lines with `&&`, so it stops at the first
failure. `join` picks something else:

```python
shell(join = ";"):                # run them all regardless
    make clean
    rm -rf tmp
    echo done

let top = shell(join = "|"):      # one pipeline
    sort access.log
    uniq -c
    head -1
```

`"&&"`, `";"`, `"|"` and `"||"` are accepted, as literals — the lines are
joined at transpile time, so it cannot be a variable.

Mind what the choice of joint does to error reporting: with
`join = ";"` the `.code` you get back is the **last** command's, so a line
that failed in the middle leaves no trace in it, and `check = true` has no
non-zero status to catch either. Two ways to ask instead:

```python
# A scan, where coming up empty is normal and only a broken command speaks:
let r = shell(join = ";"):
    rg FATAL {log} | head -20
    rg SEVERE {log} | head -20
if r.stderr.strip() != "":
    stderr.writeLine("scan: " + r.stderr.strip())

# A sequence, where every step must succeed. pipefail is needed for any
# line ending in a pipe, or the last command's 0 hides the failure:
let s = shell(join = "&&", pipefail = true):
    rg FATAL {log} | head -20
    process-results
print(s.code)
```

`grep` and `rg` exit 1 when they find *nothing* and 2 on a real error, so
for a scan the status cannot tell "matched nothing" from "could not read
the file" — `.stderr` can, and an `&&` chain would stop at the first
pattern that matched nothing.

### Paths: `Path` and `/`

A path is a string, and joining two of them is `os.path.join` in most
languages. `Path` makes it an operator:

```python
let root: Path = Path("/tmp")
let cdir: Path = root / ".git1"
let repo: Path = cdir / name / "HEAD"
```

Use it for every place on disk: a directory or file is a `Path` from where
it enters the program -- an argument, an environment variable, a line of
`ls` output -- rather than a `str` joined with `"/"`, and a function that
takes one says `dir: Path`. What stays a `str` is what is not a place on
this disk: a URL, a path as another tool reports it, a value a program
resolves itself. [A place on disk is a `Path`](#a-place-on-disk-is-a-path) gives
the reasons.

`Path` is *a string that also joins*, not a separate world: it goes wherever
a `str` goes — file tests, `readFile`, shell interpolation, a `str`
parameter, a dict key, `.upper()`. The other direction is not automatic and
both backends refuse it: `Path(s)` makes one from a `str`, `str(p)` goes
back. A bare `p = s` is an error on both backends: `Path` is a
`distinct string` on Nim.

A declared-but-unset `Path` is empty, not None, so `var p: Path` compares
equal to `""` on both backends.

That is deliberate. Nim's `std/paths.Path` is a `distinct string`, so the
backend injects a converter back to `string`; Python gets the same shape from
a `str` subclass with `__truediv__`. Real `pathlib.Path` was the obvious
choice and is the wrong one here — `p + "!"` and `p.upper()` work on Nim and
raise on pathlib, so the two backends would disagree.

Taking one apart is the other half:

```python
let p: Path = Path("/etc/nginx/nginx.conf")
p.parent        # Path("/etc/nginx") — the directory holding it
p.name          # "nginx.conf" — the last component, a plain str
assert (p.parent / "sites").mkdir() is None   # mkdir -p; a None | !PathFailure_T
```

`parent` and `name` follow `pathlib`'s splitting rules, which is what Nim's
`parentDir`/`lastPathPart` already do. `os.path` is the odd one out and is
deliberately not the model: it calls the basename of `"a/b/"` empty and its
dirname `"a/b"`, where both `pathlib` and Nim say `"b"` and `"a"`. A path
with no directory part has `"."` as its parent, and the root is its own
parent.

`resolve()` is the other direction: the absolute path with every symlink
along it expanded. It follows `os.path.realpath`, including on a path that
does not exist yet — Nim's `expandFilename` raises there, so the helper
resolves as much of the path as does exist and keeps the rest, which is what
Python does.

`mkdir()` is `mkdir -p` on both backends — it creates missing parents and
succeeds on a directory that already exists. That is Nim's `createDir` and
Python's `os.makedirs(..., exist_ok = true)`, not `pathlib.mkdir()`'s
stricter default. It can still fail — a permission, a file where the
directory should be — and says so as a `None | !PathFailure_T` rather than
raising: take it with `assert p.mkdir() is None`, `if r is PathFailure_T:`
(`r.op`, `r.path`, `r.reason`), or a `do:` step.

One wrinkle: a file test takes a primary, so a join inside one needs
parentheses — `-f (gitdir / "HEAD")`.

Reading one is `.lines`: `for line in p.lines:` opens the file, yields its
lines without their newlines, and closes it when the loop ends, however it
ends. It is the way to read a file line by line; the next section says why.

### Reading a file or standard input: `File`

`File` is the type a file handle has, and `stdin` is one, so a program that
reads either can hold both in one variable and write the loop once:

```python
let f: File = (open(file_arg) if file_arg != "" else stdin)
for line in f.lines:
    print process(line)
```

`.lines` yields each line **without** its terminator, on both backends —
Python's own iteration keeps the newline and Nim's drops it, so the trailer
is what makes the two agree. `open()` returns a `File`; on the Python target
the annotation becomes `typing.TextIO`.

A `Path` has `.lines` too, and it is the way to read a file line by line:
the file is opened, read a line at a time, and closed when the loop ends —
or is left early, by `return` or `break`:

```python
for line in log.lines:
    return $+{ref} if line == /reference baseline\s*:\s*(?P<ref>\S+)/
```

Not `readFile(log).split("\n")`, which reads the whole file first and
yields one more line, an empty one, after a final newline; and not an
`open()` whose `File` nothing closes.

### Messages and exit: `die`, `warn`, `PROG`

Built in, with no import, and emitted only into programs that use them:

```python
warn("no config, using defaults")      # "<prog>: no config, using defaults" on stderr
die("cannot read " + str(p))           # the same, then exit 1
die(f"bad option {arg}", code = 2)     # ...exit 2
print(f"usage: {PROG} [-v] FILE")
```

`PROG` is the name the program was invoked as, like `${0##*/}`; `$0` is
its path as invoked, on both backends -- a link is not followed, and a
program started through `PATH` gets the path `PATH` found it at. A leading
`.` from ady2nim's cached binary is dropped, and so is a `_gen.py` / `.py`
from ady2py, so both backends print the same name. `die` never returns, so a
function can end in it. A program's own top-level `def die`, `def warn` or
`let PROG` takes precedence over the built-in.

Because `die` never returns, a function may end in it:

```python
def positive(n: int) -> int:
    if n > 0:
        return n
    die(f"n must be positive, got {n}", code = 3)
```

Before these were built in, every tool started with the same lines:

```python
let PROG: str = Path($0).name.lstrip(".")

def die(msg: str):
    stderr.writeLine(PROG + ": " + msg)
    quit(1)
```

Such copies drift. One tool forgot the `.lstrip(".")` and signed its
messages `.Tblame:` whenever it ran through its `#!` line. Don't write them
any more. `TOOLS/C500/c500.ady`, for example, defines a `die` of its own
that reports a line number on stdout, which takes precedence over the built-in.

### Where is this program?

```python
let git: ?Path = which("git")
if git is None:
    die("git is required")
print "using " + str(git)
```

`which` answers from `PATH` — `shutil.which` on Python, `findExe` on Nim —
so unlike `command -v` it costs neither a process nor a shell. It hands back
a `?Path`: `None` when the program is not there.

**`have(x)` is deprecated.** It asked the same question and threw the path
away; it still works and now warns, and `which(x) is not None` is what it
meant.

```python
if which("git") is None:        # was: if not have("git")
    die("git is required")
```

A program that has to find its own installation is the reason it exists —
`which($0's name).parent` is where this binary lives, without spawning the
`which` command, which is a process and a program not every system carries.
A `?Path` rather than an empty string because an empty path does not stay
empty: `Path("").parent` is `"."`, so a missed check builds a plausible path
out of nothing.

A guard that leaves proves the value is there, and both backends know it:

```python
let found: ?Path = which(prog)
if found is None:
    die("not on PATH")
let base: Path = found.parent.parent    # a plain Path from here on
```

### Running commands alongside each other

Every form so far waits: the statement does not finish until the command
does, so N commands take the sum of their times. `shellSpawn` starts one and
carries on, handing back a `Job` to collect later:

```python
var jobs: []Job = []
for host in hosts:
    let j: Job = shellSpawn: ping -c1 {!host}
    jobs.append(j)

let results: []RunResult = waitAll(jobs)
for r in results:
    print r.code
```

Those pings happen at the same time, so the loop takes about as long as the
slowest one rather than the sum.

A single job is waited on directly, and the handle answers a few other
questions:

```python
let j: Job = shellSpawn: make -j8
while j.running():          # never blocks
    print "still building"
let r: RunResult = j.wait() # blocks; .output, .stderr, .code
let r2: RunResult = j.wait(check = true)   # raises if it failed
j.kill()                    # SIGTERM, reported as 143; safe to call twice
print j.pid
```

`wait` is safe to call twice — the result is kept once the child has been
reaped, so the second call returns rather than hanging.

`cwd`, `env` and `stdin` apply at the spawn. `timeout` and `check` do not:
there is nothing to time or check yet, and both belong on the wait —
`j.wait(check = true)`.

**Use `waitAll` for more than one job.** The output goes into a pipe, and a
pipe holds only so much — 64K on Linux. A job that produces more stops when
it fills and resumes when something drains it, so waiting for jobs one at a
time in a loop quietly serialises them again. `waitAll` drains every job as
it goes; on Nim that is one non-blocking loop over all of them, on Python a
thread per job.

A spawned command needs a target, since without one nothing is left to
collect it:

```python
shellSpawn: sleep 5        # transpile-time error — assign it to a Job
```

### Handing the process over

`shellExec:` replaces the running process with the command. It does not
return: nothing written after it can run, and the command's own exit status
becomes the script's.

```python
shellExec: git {*args}          # this script *becomes* git
print "never reached"
```

That is what a wrapper script wants — one less process in the tree, no
status to forward by hand, and signals going straight to the real command.
`cwd` and `env` apply; `timeout`, `stdin` and `check` do not, since there is
no child to wait for or feed. Both backends exec `/bin/sh -c`: Nim through
`execv` / `execve`, Python through `os.execv` / `os.execve`.

Compare with the capturing form, which does return:

```python
let code: int = shell: git {*args}    # runs git, then carries on
quit(code)                            # forwarding the status by hand
```

### Options

```python
let result = shell(cwd = "/tmp"):           pwd
let result = shell(timeout = 5000):         slow-command
let result = shell(cwd = "/tmp", timeout = 3000): ls -la
```

Which options a form takes:

| | `cwd` | `env` | `timeout` | `stdin` | `check` | `pipefail` | `join` |
|---|---|---|---|---|---|---|---|
| `shell:` / `shellLines:` | ✓ | ✓ | ✓ | capturing forms | ✓ | ✓ | block form |
| `shellIter` | ✓ | ✓ | | | ✓ (at the end) | ✓ | |
| `shellExec` | ✓ | ✓ | | | | ✓ | block form |
| `shellSpawn` | ✓ | ✓ | | ✓ | | ✓ | block form |
| `run` / `runLines` | ✓ | ✓ | ✓ | ✓ | ✓ | n/a — no shell | n/a |

An option a form cannot honour is a transpile-time error, not a silent
no-op, and a misspelled one says what you probably meant:

```
shell: unknown option `timout` -- did you mean `timeout`?
       (supported: check, cwd, env, stdin, timeout)
shellExec(timeout = ...) is not supported: shellExec replaces this
       process, so there is no child to time out. timeout works on
       shell, shellLines.
```

### Discarding output

```python
shell: rm -rf /tmp/build
```

### Block form — multi-line and interactive (expect/send)

`shell:` followed by an indented block accepts multiple lines:

```python
# Pure block: commands joined into a single pipeline with " && "
shell:
    echo hello
    echo world
```

When a block contains `send(...)` / `expect(...)` calls, the first line is
the command spawned under a PTY and the remaining calls drive it. The
transpiler emits calls to the bundled `expect` standard library
(`forkpty + select + re`, links against `-lutil`):

```python
# from TESTS/test_shell_block.ady
shell:
    bc -q
    send("2 + 2\n")
    expect("4")
    send("10 * 5\n")
    expect("50")
    send("quit\n")
```

For finer control (capturing matches, multiple spawns, explicit lifetimes),
use the `expect` library directly:

```python
nimport expect

var s: Spawn = spawn("bc")
s.expect("\\$|>|bc")
s.send("2 + 2\n")
s.expect("4")
print("result = " & s.match)
s.send("quit\n")
s.close()
```

### Translation reference

| Adascript              | Python 3                                            | Nim                                        |
|----------------------|-----------------------------------------------------|--------------------------------------------|
| `let r = shell: cmd`        | `subprocess.run(…, capture_output=True, text=True)` | `adascriptRun("cmd")` — streams kept apart |
| `let (out, code) = shell: cmd` | `…stdout, …returncode`                       | `(r.output, r.code)`                      |
| `let (out, code, err) = shell: cmd` | `…stdout, …returncode, …stderr`         | `(r.output, r.code, r.stderr)`            |
| `shell(timeout = ms): cmd`  | killed at the deadline, code `124`              | same — the child is killed, code `124`    |
| `let ls = shellLines: cmd`  | `…stdout.splitlines()`                          | `execCmdEx("cmd")[0].splitLines()`        |
| `shell: cmd`                | `subprocess.run("cmd", shell=True)`             | `discard execCmd("cmd")`                  |
| `shellLines: cmd`           | (implicit return of split lines)                | `return execCmdEx("cmd")[0].splitLines()` |
| `{var}` in body      | `f"""…{var}…"""`                                    | `fmt"""…{var}…"""` (imports `strformat`)   |
| `{f(x)}` in body    | `f"""…{f(x)}…"""`                                   | `let tmp = f(x); fmt"""…{tmp}…"""`         |

Required imports (`subprocess`, `types`, `osproc`, `strformat`) are inserted
automatically.

---

## Bash Variables

Adascript supports bash-style special variables for scripts that handle
command-line arguments and environment variables:

### Argument variables

```python
print $0        # script name
print $1        # first argument
print $@        # all arguments (as a list)
print $#        # number of arguments
```

A program usually starts by checking them:

```python
if $# < 2:
    print(f"Usage: {$0} <dict_file> <phone_file>")
    quit(1)

let dict_file:  str = $1
let phone_file: str = $2

for arg in $@:
    print(arg)
```

### Environment variables

All-caps identifiers with `$` read an environment variable:

```python
home   = $HOME
path   = $PATH
editor = $EDITOR
```

An unset variable reads as the empty string. To supply something else, the
shell's `${var:-val}` form works, falling back when the variable is unset
**or** set to the empty string:

```python
cache  = ${XDG_CACHE_HOME:-"/tmp/cache"}
editor = ${EDITOR:-$VISUAL}
outdir = ${OUTDIR:-$HOME + "/output"}
```

Unlike the shell, where the fallback is a bare word, here it is an ordinary
expression — so literal text needs quoting. A bare `/tmp` would lex as
division and then as a regex literal.

`${NAME}` without a fallback is accepted too, and means exactly `$NAME`.

Because `$NAME` is a `str`, it cannot tell a variable that is absent from one
that is set to nothing — both read as `""`. When that difference matters,
`$?NAME` is the same lookup as a `?str`:

```python
if $?EDITOR:                  # set at all? "" counts as set
    print "EDITOR is set"

let editor: ?str = $?EDITOR   # …and it carries the value
print $?EDITOR or "vi"        # …with a default, applied only when absent
```

`${?NAME}` is the braced spelling of the same thing. `$NAME` is unchanged and
still a `str`, so nothing that reads the environment today has to be revisited
— reach for `$?NAME` only where "unset" and "set to nothing" are different
answers.

Note the difference between the two fallbacks: `${NAME:-default}` follows the
shell and substitutes for an empty value as well, while `$?NAME or default`
substitutes only when the variable is absent.

### The environment is read-only

`$NAME` reads; there is no `export`. An assignment to one is refused, with
the alternative in the message:

```python
$PATH = "/opt/bin:" + $PATH      # error: assigns to the environment, which is read-only
```

The reason is that writing it would buy almost nothing: a process's own
environment reaches no further than the commands it starts, and those take
one directly — `env` adds to what the child inherits, so the rest of the
environment, `PATH` included, is still there:

```python
let extra: {str}str = {"PATH": "/opt/bin:" + $PATH}

shell(env = extra): make -j4          # this command sees it
run(["make", "-j4"], env = extra)     # so does this one
shellExec(env = extra): make -j4      # ...and this becomes it
```

That last line is the shell wrapper's whole shape — `export` then `exec`,
without the `export`. Argument variables (`$0`, `$1`, `$@`, `$#`) are
read-only for the same reason and refuse assignment the same way; copy one
into a `var` if you want to change it.

### In expressions

```python
if $# < 2:
    print f"Usage: {$0} <input> <output>"
    quit(1)

for arg in $@:
    print arg

outdir = $HOME + "/output"
```

### Translation reference

| Adascript   | Python 3                    | Nim                    |
|-----------|-----------------------------|------------------------|
| `$0`      | `sys.argv[0]`               | `getAppFilename()`     |
| `$1` … `$9` | `sys.argv[1]` … `sys.argv[9]` | `paramStr(1)` … `paramStr(9)` |
| `$@`      | `sys.argv[1:]`              | `commandLineParams()`  |
| `$#`      | `len(sys.argv) - 1`         | `paramCount()`         |
| `$NAME`   | `os.environ.get('NAME', '')` | `getEnv("NAME")`      |

Required imports are inserted automatically.

### File-test operators

Bash-style file-test operators work as boolean expressions:

```python
if -e path:          # path exists
if -f path:          # path is a regular file
if -d path:          # path is a directory
if -L path:          # path is a symlink
if -r path:          # path is readable
if -w path:          # path is writable
if -x path:          # path is executable
if -s path:          # path exists and is non-empty

if file1 -nt file2:  # file1 is newer than file2
if file1 -ot file2:  # file1 is older than file2
```

They can be negated and combined with `and`/`or`:

```python
if not -e comment_path:
    comment_path = comment_path.replace("_t/", "_e/")
if -f comment_path:
    text = readFile(comment_path)
```

### Translation reference

| Adascript      | Python 3                        | Nim                          |
|--------------|---------------------------------|------------------------------|
| `-e path`    | `os.path.exists(path)`          | `fileExists(path) or dirExists(path)` |
| `-f path`    | `os.path.isfile(path)`          | `fileExists(path)`           |
| `-d path`    | `os.path.isdir(path)`           | `dirExists(path)`            |
| `-L path`    | `os.path.islink(path)`          | `symlinkExists(path)`        |
| `-r path`    | `os.access(path, os.R_OK)`      | `fileExists(path)`           |
| `-w path`    | `os.access(path, os.W_OK)`      | `fileExists(path)`           |
| `-x path`    | `os.access(path, os.X_OK)`      | `fileExists(path)`           |
| `-s path`    | `os.path.isfile(path) and os.path.getsize(path) > 0` | `fileExists(path) and getFileSize(path) > 0` |
| `a -nt b`    | `os.path.getmtime(a) > os.path.getmtime(b)` | `getLastModificationTime(a) > getLastModificationTime(b)` |
| `a -ot b`    | `os.path.getmtime(a) < os.path.getmtime(b)` | `getLastModificationTime(a) < getLastModificationTime(b)` |

---

## Callable objects and pipe operator

### `__call__` and `__ror__`

Classes that define `__call__` become callable objects. In Nim this uses
the `{.experimental: "callOperator".}` pragma (inserted automatically).

`__ror__` (and other reflected operators like `__radd__`, `__rsub__`) flip
the argument order in Nim so `"text" | style` works naturally:

```python
class Style:
    var on: str
    var off: str
    def __init__(self, code: int):
        self.on = f"\x1b[{code}m"
        self.off = "\x1b[0m"
    def __call__(self, *args: str) -> str:
        return "".join([f"{self.on}{arg}" for arg in args]) + self.off
    def __ror__(self, other: str) -> str:
        return self(other)

let bold: Style = Style(1)
let red:  Style = Style(31)

print("hello" | bold | red)   # chains via __ror__
print(bold("hello", "world")) # direct __call__
```

The `|` operator is context-sensitive: when both operands involve custom
types (not plain integers), it emits Nim `|`; otherwise it emits `or`.

---

## Enum constructors

Reading an enum member from text is `parse_enum(E, s)`, an `E |
!ParseFailure_T`: the member named exactly `s` -- or, given an integer, the member with
that value -- or the failure, handled where
it is called and no `try` involved:

```python
type State = enum ACTIVE, ON_HOLD, DONE

def parse_state(s: str) -> State:
    let state: State | !ParseFailure_T = parse_enum(State, s.replace("-", "_").upper())
    if state is ParseFailure_T:
        return ACTIVE
    return state
```

Transpiles to:

```nim
proc parse_state(s: string): State =
    let state: Result[State, ParseFailure_T] = adascriptParseEnum(State, s.replace("-", "_").toUpperAscii())
    if state.is_err:
        return ACTIVE
    return state.value
```

Calling the enum type itself with a string, `State(s)`, is the older form: it
emits `parseEnum` and raises when `s` names no member (Nim's `parseEnum` also
ignores case and underscores, which `parse_enum` does not).

---

## Side by Side with awk and Bash

Four examples ship with the program they are arguing against, so the claims
about what Adascript buys can be run rather than read. Each pair does the
same job on the same input, and `make test` compares them on every run — the
first three must agree byte for byte, and the fourth must not.

| Adascript | Written against | Same output? |
|---|---|---|
| `EXAMPLES/AWK/awk_logscan.ady` | `EXAMPLES/AWK/awk_logscan.awk` | yes, on two inputs |
| `EXAMPLES/AWK/config_check.ady` | `EXAMPLES/AWK/config_check.awk` | yes, on two inputs |
| `EXAMPLES/AWK/html_body.ady` | `EXAMPLES/AWK/process_html.awk` | yes, except one case below |
| `EXAMPLES/sh_janitor.ady` | `EXAMPLES/sh_janitor.sh` | **no**, and that is the point |

Run any of them yourself:

Every command below is bash (the `<(...)` needs it), and each prints nothing
when the two agree:

```bash
# a log scanner: two kinds of record, a state machine, two lists at the end
awk -f EXAMPLES/AWK/awk_logscan.awk EXAMPLES/AWK/awk_logscan_sample.txt \
    | diff - <(EXAMPLES/AWK/awk_logscan < EXAMPLES/AWK/awk_logscan_sample.txt)

# a config checker against a four-shape schema
EXAMPLES/AWK/config_check                     # writes its fixture under /tmp
awk -f EXAMPLES/AWK/config_check.awk /tmp/ady_config_check/app.conf \
    | diff - <(EXAMPLES/AWK/config_check /tmp/ady_config_check/app.conf)

# lifting the <body> out of an HTML page (needs gawk: gensub is a GNU thing)
cd EXAMPLES && gawk -f process_html.awk html_body_sample.html \
    | diff - <(./html_body html_body_sample.html)

# the log-rotation janitor -- these two do NOT agree
EXAMPLES/sh_janitor.sh; EXAMPLES/sh_janitor
```

**The three that agree** are there so the comparison is about the code and
not about the answer. What the awk has to spell out — parallel arrays
because there is no record, enum members as a string and their order written
out twice, an `if`/`else` chain where a `case` over ranges would do, an
insertion sort by hand to answer one median, a schema whose four shapes
share one flat set of fields — is walked through in
`DOCS/ADASCRIPT_FOR_AWK.md` §10.

**The two exceptions are the interesting part.**

`process_html.awk` and `html_body.ady` agree on ordinary pages and diverge
on one: a page whose footer contains a `<div>` on a line of its own. The awk
spends the page's id on that line and then drops the line, so the output has
no id at all. Its tagging rule tests `in_body`, and the footer is inside the
body; the translation cannot do this because the states that drop a record
never rewrite it. `EXAMPLES/AWK/html_body_wasted_id.html` is that page.

`sh_janitor.sh` disagrees on every run, silently:

```
$ EXAMPLES/sh_janitor.sh        $ EXAMPLES/sh_janitor
  COMPRESS  2 file(s),  328       COMPRESS  3 file(s),  628
  DELETE    1 file(s),   10       DELETE    2 file(s),   20
  0 failure(s)   → exit 0         0 failure(s)   → exit 0
```

`for f in $(ls -A "$DIR")` splits `quiet service.log` into two names that do
not exist. Nine files go in, seven come out of the report, no error is
printed and the exit status is 0. `make test` asserts that this is still
what happens, so the claim fails rather than rots. The quoting is fixable;
what is not is the rest of `DOCS/ADASCRIPT_FOR_SHELL.md` §12.

---

## Summary of Adascript-Only Syntax

| Feature                           | Adascript syntax                         |
|-----------------------------------|------------------------------------------|
| Mutable variable declaration      | `var x: int = 0`                         |
| Immutable binding                 | `let name: str = "hello"`                |
| Compile-time constant             | `const MAX: int = 1000`                  |
| Enum declaration                  | `type E is enum A, B, C`                 |
| Named tuple declaration           | `type P is tuple: x: float; y: float`   |
| Record declaration                | `type P is record: name: str; age: int` |
| Variant record                    | `type S (Kind: K) is record: case ...`  |
| Subrange type                     | `type T is lo .. hi`                     |
| List type annotation              | `[]T`                                    |
| Fixed-size array annotation       | `[N]T`                                   |
| Open array annotation (param only)| `[*]T`                                   |
| Dict type annotation              | `{K}V`                                   |
| Set type annotation               | `{}T`                                    |
| Enum-indexed array annotation     | `[E]T`                                   |
| Optional type annotation          | `?T`                                     |
| Inclusive range                   | `lo .. hi`                               |
| Exclusive range                   | `lo ..< hi`                              |
| Enum first/last                   | `E'First`, `E'Last`                      |
| Full enum set                     | `E'Range`                                |
| Successor / predecessor           | `expr'Next`, `expr'Prev`                 |
| Random selection                  | `expr'choose`                            |
| Empty dict literal                | `{:}`                                    |
| Named tuple literal               | `(field: value, ...)`                    |
| Enum-indexed array literal        | `[KEY: value, ...]`                      |
| Pattern matching                  | `case x: when P: ... when others: ...`  |
| Inline suite (single-stmt body)   | `if x>0: f()`, `while c: g()`, `when P: h()` |
| Statement modifier                | `return False if s == ""` (return/break/continue/die/quit) |
| Generator functions               | `def f(): ... yield value`               |
| Field with inline default         | `var x: int = 0` inside class body       |
| Mutable self (auto-detected)      | `self.field =`, or a call reaching one   |
| Cross-module inheritable class    | `@virtual class C: ...`                  |
| HTML page (Nim only)              | `html:` in a `-> Html` method; tags indented below |
| Generic class                     | `class C[S, D, C]: ...`                  |
| An `.ady` module                  | `import module` (names are `module.name`) |
| Import only some names of a module | `from module import A, B` (the file may use A, B and what they carry) |
| Nim-only / Python-only import     | `nimport module` / `pyimport module`     |
| Shell command capture             | `let r = shell: cmd`                     |
| Shell lines capture               | `let ls = shellLines: cmd`               |
| Shell lines (typed)               | `let ls: []str = shellLines: cmd`        |
| Shell (bare assign)               | `ls = shellLines: cmd`                   |
| Shell expr interpolation          | `shell: cmd {f(x)}` (auto-hoisted)      |
| Shell interpolation, quoted       | `shell: cmd {!path}` (one argument)     |
| Shell interpolation, list         | `shell: cmd {*args}` (each quoted)      |
| Shell, fail on non-zero           | `shell(check = true): cmd`              |
| Shell, feed stdin                 | `shell(stdin = text): cmd`              |
| Shell, child environment          | `shell(env = e): cmd` (added to)        |
| Shell, streamed lines             | `for line in shellIter: cmd`            |
| Streamed, fail on non-zero        | `shellIter(check = true)` — at the end  |
| Shell, replace this process       | `shellExec: cmd` (never returns)        |
| Shell, run alongside              | `let j: Job = shellSpawn: cmd`          |
| Pipeline reports first failure    | `shell(pipefail = true): a | b`         |
| Block joined with something else  | `shell(join = ";"):` / `"|"` / `"||"`   |
| Where is a program?               | `which("git")` -> `?Path`                |
| Fail with a message               | `die("msg")`, `die("msg", code = 2)`     |
| Warn and carry on                 | `warn("msg")`                            |
| The program's name                | `PROG`, predeclared                      |
| Path join                         | `let p: Path = root / "sub" / name`     |
| Path <-> str                      | `Path(s)` / `str(p)`; a bare `p = s` is refused |
| Read a file or stdin              | `let f: File = (open(p) if p != "" else stdin)` |
| Lines without the newline         | `for line in f.lines:` -- same on both backends |
| A file's lines, by its `Path`     | `for line in p.lines:` -- opened, read and closed for you |
| Character literal                 | `let c: char = '\t'`; narrowed wherever a char is declared |
| Path split                        | `p.parent` -> Path, `p.name` -> str     |
| Path mkdir                        | `p.mkdir()` -- mkdir -p; a `None \| !PathFailure_T` |
| Path resolve                      | `p.resolve()` -- abs, symlinks expanded |
| Wait for one / many jobs          | `j.wait()` / `waitAll(jobs)`            |
| Run a program, no shell           | `run(["git", "log"])` -> RunResult      |
| Run a program, output lines       | `runLines(["ls", d])` -> `[]str`        |
| Shell exit code, terminal kept    | `let code: int = shell: cmd`            |
| Discard shell output              | `shell: cmd`                             |
| Shell block (commands joined)     | `shell:` then indented `cmd1` / `cmd2`   |
| Shell block (PTY expect/send)     | `shell:` then `cmd` / `send(...)` / `expect(...)` |
| Command-line argument             | `$1`, `$@`, `$#`                         |
| Environment variable              | `$HOME`, `$PATH`                         |
| File-test operator                | `-e path`, `-f path`, `-d path`          |
| Regex match test                  | `s == /pat/`, `s != /pat/i`              |
| Regex positional capture          | `$+0`, `$+1`, `$+2` …                   |
| Regex named capture               | `namedCaptures["name"]`                  |
| Regex find-all                    | `s == /pat/g` → `[]str`                  |
| Regex substitution                | `s = s/pat/repl/g`                      |
| Regex in case/when                | `when /pat/:`                            |
| File comparison                   | `a -nt b`, `a -ot b`                     |
| Python 2-style print              | `print "text"` or `print expr, expr`    |
| An empty line                     | `print` on its own                      |
| Owned variable declaration        | `own x: T = expr`                        |
| Borrow type annotation            | `lent T` (param type)                    |
| Ownership-transfer type annotation| `own T` (param type)                     |
| Explicit ownership transfer       | `move(x)`                                |
| Explicit early release            | `drop(x)`                                |
| Scoped RAII block                 | `with own x = expr:`                     |

---

## Benchmark Programs

The `EXAMPLES/` directory contains real programs that exercise the full
language and serve as end-to-end tests. Each has a `.ady` source, a
transpiled `.nim` output, and in most cases a reference Python `.py` file.

### `primes.ady` — Prime sieve

Counts primes up to 1,000,000 and measures wall time. Demonstrates the
`..` and `..<` range operators, and the cheapest of the three ways to ask
the machine something: `nimport time` maps `time.time()` to Nim's
`epochTime()` and to Python's own, so the clock costs the build nothing.
It used to be a `pyimport`, which is what the rule above is about.

```python
#!/usr/bin/env ady2nim
import time

N = 1_000_000

def is_prime(n: int) -> bool:
    for k in 2 .. int(n ** 0.5):    # inclusive range
        if n % k == 0:
            return False
    return True

def count_primes(n: int) -> int:
    count = 0
    for k in 2 ..< n:               # exclusive upper bound
        if is_prime(k):
            count += 1
    return count

start = time.perf_counter()
print f"Number of primes: {count_primes(N)}"
print f"Time elapsed: {time.perf_counter() - start}s"
```

Features: `..` / `..<` range operators, `import time` (→ Nim `times`),
Python-2-style `print`, f-strings.

### `graph.ady` — Graph path search

Three path-finding functions (find_path, find_all_paths, find_shortest_path)
on a dict-of-lists graph. Exercises recursive functions, `[]str` default
parameters, `not in`, and `append`.

```python
#!/usr/bin/env ady2nim

type Node_T  is str
type Graph_T is {Node_T}[]Node_T    # dict mapping node to list of neighbours

graph: Graph_T = {
    'A': ['B', 'C'],
    'B': ['C', 'D'],
    'C': ['D'],
    'D': ['C'],
}

def find_path(graph: Graph_T, start: Node_T, end: Node_T,
              path: []Node_T = []) -> []Node_T:
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    for node in graph[start]:
        if node not in path:
            newpath: []Node_T = find_path(graph, node, end, path)
            if newpath:
                return newpath
    return None

assert find_path(graph, 'A', 'D') == ['A', 'B', 'C', 'D']
print(find_path(graph, 'A', 'D'))
```

Features: type aliases for readability, `{}` and `[]` collections,
`not in`, default parameters.

### `monty_hall.ady` — Enums, sets, tick attributes, case/when

```python
#!/usr/bin/env ady2nim

type Door_T   is enum Door1, Door2, Door3
type Choice_T is enum Switch, DontSwitch

def monty_hall_simulation(trials = 100_000):
    var stayWins:   int = 0
    var switchWins: int = 0

    for _ in 1 .. trials:
        let carLocation:          Door_T  = Door_T'choose
        let candidateFirstChoice: Door_T  = Door_T'choose
        let availableDoors:       {}Door_T = Door_T'Range - {candidateFirstChoice, carLocation}
        let hostChoice:           Door_T  = availableDoors'choose
        let switchOptions:        {}Door_T = Door_T'Range - {candidateFirstChoice, hostChoice}

        for choice in Choice_T:
            case choice:
                when DontSwitch:
                    if candidateFirstChoice == carLocation:
                        stayWins += 1
                when Switch:
                    let candidateSecondChoice: Door_T = switchOptions'choose
                    if candidateSecondChoice == carLocation:
                        switchWins += 1

    print "Trials: ", trials
    print f"Stay:   {stayWins} wins ({stayWins * 100 / trials} %)"
    print f"Switch: {switchWins} wins ({switchWins * 100 / trials} %)"

monty_hall_simulation()
```

Features: enums, ordinal sets (`{}Door_T`), `'choose` for random selection,
`'Range` for the full set of enum members, set difference (`-`), `case/when`
on enum values, inclusive range `1 .. trials`.

### `dijkstra.ady` — Priority queue, enum-keyed dicts, from-import

The algorithm entire — 27 lines (`dijkstra.ady` closes with a comment
about the generic version in the bundled `graphs` library, not shown here):

```python
#!/usr/bin/env ady2nim
from stdlib nimport PriorityQueue
type Node_T is enum A, B, C, D
type Distance_T is float
type Neighbour_T is tuple:
    distance: Distance_T
    neighbor: Node_T
type Graph_T is {Node_T}[]Neighbour_T

def dijkstra(graph : Graph_T, start: Node_T) -> {Node_T}Distance_T:
    distances: {Node_T}Distance_T = {node: (0.0 if node==start else Inf) for node in graph}
    var visited : {}Node_T
    queue : PriorityQueue[Neighbour_T] = [(0.0, start)]
    while queue:
        current_dist, node = queue.pop()
        if node in visited:
            continue
        visited.add(node)
        for dist, neighbor in graph[node]:
            let new_dist: Distance_T = current_dist + dist
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                queue.push((new_dist, neighbor))
    return distances

graph : Graph_T = {A: [(1.0, B), (4.0, C)], B: [(2.0, C), (5.0, D)], C: [(1.0, D)], D: []}
print dijkstra(graph, A)
```

Prints `{D: 4.0, C: 3.0, A: 0.0, B: 1.0}`.

Features: `from stdlib nimport` for `PriorityQueue`, nested dict type
`{K}{K}V`, enum members as dict keys, `const`, and a dict comprehension that
does the whole initialisation — the conditional sits *inside* it, so there
is no second pass to set the start node to zero. `for node in graph`
iterates a `{K}V`, which yields its keys.

Runs on both backends. Nim compiles against the shim in
`TO_NIM/STDLIB/stdlib.nim`; Python has no module of that name to import, so
`ady2py` writes `PriorityQueue` into its output instead — a `heapq` heap,
which is what Nim's hand-written binary heap amounts to. `FifoQueue`,
`LifoQueue` and the `ANY` sentinel come the same way.

One difference is worth knowing before you rely on it: when two entries
carry the same priority, the order they come back in is not promised and
the two backends do differ. Only the lowest priority is guaranteed to
come out first.

### `phonecode.ady` — Phone code benchmark

Implements Prechelt's classic benchmark: find all word encodings of phone
numbers using a trie. Exercises enums, dict types, optional types, nested
classes, closures, and `$#`/`$1`/`$2` argument variables.

It demonstrates:

- Enum `Digit_T` as trie index
- `[Digit_T]TrieNode` — fixed-size array indexed by enum
- `?str` optional return type
- Nested function `word_to_digits` inside a method
- `$1`, `$2`, `$#` command-line argument variables
- `-f path` file-test operator
- `with open(…) as f:` file I/O

```python
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9

class TrieNode:
    var children: [Digit_T]TrieNode    # array[Digit_T, TrieNode] in Nim
    var words:    []str

    def find_exact_word(self, digits: []Digit_T) -> ?str:
        var node: TrieNode = self
        for digit in digits:
            if node.children[digit] is None:
                return None
            node = node.children[digit]
        if len(node.words) > 0:
            return node.words[0]
        return None

def main():
    if $# < 2:
        print("Usage: phonecode <dict_file> <phone_file>")
        quit(1)
    let dict_file:  str = $1
    let phone_file: str = $2
    if not -f dict_file:
        print(f"Error: {dict_file} not found")
        quit(1)
    ...
```

### `shortest_path.ady` — Generic optimiser framework

A 200-line framework demonstrating: generic classes `[S, D, C]`, nested
type declarations, `yield` (generator methods), discriminated tuples,
tick-attribute iteration, and ten complete algorithm examples in
`shortest_path_demo.ady`, including Dijkstra, A*, dynamic programming, knapsack, rod cutting, HMM Viterbi,
equipment replacement, and capital budgeting.

The key architectural pattern is **generic
class + `import` + subclassing**:

```python
# shortest_path.ady — library
@virtual
class Optimizer[S, D, C]:
    var offset:        float
    var decision_path: []D
    var start_state:   S

    def shortest_path(self, start_state: S, end_state: S, allsolutions: bool = True):
        fringe: PriorityQueue[Fringe_Element_T[S, D, C]] = PriorityQueue(...)
        while fringe:
            let (_, cost, path, current_state) = fringe.pop()
            ...
            if current_state == end_state or self.is_end_state(current_state):
                yield self.real_cost(cost), path

# Methods defined outside the class avoid Nim 2.x generic-method restrictions
def longest_path(self: Optimizer[S, D, C], start_state: S, end_state: S,
                 max_path_length: int = 1000) -> (float, []D):
    ...
```

```python
# shortest_path_demo.ady — consumer
from shortest_path import Optimizer

def example7():   # Romania map, A* with heuristic
    type State_T    is str
    type Distance_T is float

    class BookMap(Optimizer[State_T, State_T, Distance_T]):
        var G: {State_T}[](State_T, Distance_T) = { 'arad': [('sibiu', 140.0), ...], ... }
        var _heuristic: {State_T}Distance_T = { 'arad': 366.0, 'bucharest': 0.0, ... }

        def get_state(self, past_decisions: []State_T) -> State_T:
            return past_decisions[-1]

        def get_next_decisions(self, curr: State_T) -> [](State_T, Distance_T):
            return self.G.get(curr, [])

        def get_heuristic_cost(self, city: State_T) -> float:
            return self._heuristic.get(city, 0.0)

    op: BookMap = BookMap()
    for solution in op.shortest_path('oradea', 'bucharest'):
        print(solution)
```

### `awk_example.ady` / `awk_OO.ady` — awk-style line processor

A stdin line processor that classifies lines as ERROR/WARN/INFO/OTHER via
regex, prints severity-prefixed output, and prints a summary (record count,
average line length, average field count, per-severity counts).

`awk_example.ady` is the procedural version. `awk_OO.ady` is the class-based
version, demonstrating field defaults, auto-`var self`, and inheritance:

```python
@virtual
class AwkProcessor:
    var FS: str
    var NR: int = 0

    def get_record(self) -> AwkRecord_T: ...   # a generator, overridden per use case
    def process_record(self, rec: AwkRecord_T): raise NotImplementedError(...)
    def start(self): pass
    def finish(self): pass
    def run(self) -> None | !AwkFailure_T:
        self.start()
        for rec in self.get_record():
            self.process_record(rec)
        self.finish()

class SeverityProcessor(StdinProcessor):   # StdinProcessor: get_record reads stdin
    var counts: [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]

    def process_record(self, rec: AwkRecord_T): ...
    def start(self): print "--- awk report ---"
    def finish(self): ...  # print summary
```

### `show_status.ady` — Shell integration demo

A test-monitoring daemon that polls a shell command every minute, parses
its output, and prints timing summaries. Exercises `shellLines:`, `{}str`
sets, `time.sleep()`, and Python-2-style `print`.

```python
def getTestStatusLines() -> []str:
    shellLines: show_tests_status -raw

completedTests: {}str = {}
while True:
    time.sleep(60)
    for test in parseCompletedTests(getTestStatusLines()):
        completedTests.add(test)
```

### `pyimport_similar.ady` — when the bridge is worth it

The counterweight to the rule above: the one example whose subject *is*
`pyimport`, and the one `make test` runs across the nimpy bridge rather
than merely compiling. It asks `difflib` which of a tool's subcommands a
typo most resembles — a similarity ranking, which nothing in `/usr/bin`
computes (`grep` answers whether a pattern matched, not how close it came)
and which Nim's `std/editdistance` measures differently enough to rank
differently. `difflib` ships with Python, so no install stands between a
reader and running it; the mechanism is the same one `numpy` and
`requests` use. The file says what it costs, down to the
`Testing libpython: ...` line nimpy prints ahead of the program's output.

```python
pyimport difflib

def suggest(word: str) -> []str:
    var out : []str = []
    for hit in difflib.get_close_matches(word, KNOWN, 3, 0.6):
        out.append(str(hit))
    out
```

```
  comit      did you mean commit? (91% alike)
  stauts     did you mean status? (83% alike)
              ... or stash (73%)
  xyzzy      no idea
```

---

## Editors

[`EDITORS/`](EDITORS) holds the text editors: [`KILO/`](EDITORS/KILO), a
translation of antirez's kilo, and [`VI/`](EDITORS/VI), a small vi with three
terminals, each with its README and its tests. `make test-kilo` and
`make test-vi` run them alone.

## Tools

[`TOOLS/`](TOOLS) holds the programs written in Adascript that are tools in
their own right rather than examples of a language feature: each has a
command set and a README, and the first two have a test suite and editor
integrations as well. They are also the language's own proof that it is
worth using — all three are the kind of program the README argues Adascript
is for.

| | |
|---|---|
| [`TOOLS/ADA_INDENT/`](TOOLS/ADA_INDENT) | re-indents **Ada** source. Not a parser: indentation needs only the keywords that open, close or split a block, and [its README](TOOLS/ADA_INDENT/README.md) specifies that simplified grammar |
| [`TOOLS/GIT1/`](TOOLS/GIT1) | version control for **one file at a time**: every tracked file gets its own private git repository, so many of them share a directory without seeing each other |
| [`TOOLS/PGREP/`](TOOLS/PGREP) | greps the sources of a **CM build closure**, or of every subsystem's LATEST build, one process per subsystem. A translation of a ~480-line ksh script, and [its README](TOOLS/PGREP/README.md) says where it deliberately differs from it |
| [`TOOLS/LISPY/`](TOOLS/LISPY) | a **Scheme interpreter** after Norvig's `lis.py` (kept beside it): a variant record for values, classes for environments and the reader, `Val_T \| !Failure_T` from the reader, special forms as `case` patterns |

They build the same way any `.ady` file does, and `make test` builds and
exercises all three:

```bash
ady2nim c TOOLS/ADA_INDENT/ada_indent.ady   # then: cat file.adb | ada_indent
ady2nim c TOOLS/GIT1/git1.ady               # then: git1 init notes.txt
ady2nim c TOOLS/PGREP/Pgrep.ady             # then: Pgrep -closure IFPS remote
```

`ady2nim c` drops a symlink to the built binary beside the source, so
`~/.local/bin/ada_indent` pointing at `TOOLS/ADA_INDENT/ada_indent` survives
a rebuild — a link into `~/.cache/adascript/` does not, since the hash
changes with the source.

Each tool's own README is the reference: what it does, how it is invoked,
and what it deliberately does not do — `git1` has no merge, `ada_indent`
has no semantic analysis, and `Pgrep` finds nothing without the CM
environment it searches.

---

## Editor Support

Three separate things live under this heading, and it is worth keeping them
apart: support for **writing Adascript**, and the editor integrations that
belong to two of the tools in [`TOOLS/`](TOOLS) — the **Ada indenter** and
**git1** — which are editor support for something other than the language.

### Writing Adascript — [`LSP/`](LSP)

A language server plus one client per editor.
[`LSP/adascript_ls.py`](LSP/adascript_ls.py) provides three features over
stdio — **diagnostics** (parse errors on open, change and save), **hover**
(type and enum information for an identifier) and **completion** (enum type
names, their members, and tick attributes). It needs Python 3.13 and `pygls`.

| | |
|---|---|
| [`LSP/vscode-adascript/`](LSP/vscode-adascript) | VS Code: the `.ady` language, a TextMate grammar, and a client for the server |
| [`LSP/emacs/adascript-mode.el`](LSP/emacs) | a major mode deriving from `nim-mode`, with the server reached through eglot or lsp-mode |
| [`LSP/sublime-adascript/`](LSP/sublime-adascript) | Sublime Text: syntax highlighting and language defaults (no server) |

Each directory has its own README with the install steps.

### Indenting Ada — [`TOOLS/ADA_INDENT/EDITOR_SUPPORT/`](TOOLS/ADA_INDENT/EDITOR_SUPPORT)

[`TOOLS/ADA_INDENT/ada_indent.ady`](TOOLS/ADA_INDENT) re-indents **Ada** source. It is an
Adascript program, but what it edits is `.adb` / `.ads`, so its editor
integrations are a separate set — one directory per editor, all three driving
the same binary:

| | |
|---|---|
| [`emacs/`](TOOLS/ADA_INDENT/EDITOR_SUPPORT/emacs) | a minor mode on `RET` and `TAB`, plus `indent-region-function` |
| [`vim/`](TOOLS/ADA_INDENT/EDITOR_SUPPORT/vim) | sets `'indentexpr'`, so `==`, `gg=G`, `=ip` and `o`/`O` all route through it |
| [`vs_code/`](TOOLS/ADA_INDENT/EDITOR_SUPPORT/vs_code) | Format Document, Format Selection, and format-on-type |

None of them is a language-server client: each calls the binary directly, so
no editor needs Python or a server process for indentation. There is a
[`TOOLS/ADA_INDENT/LSP/`](TOOLS/ADA_INDENT/LSP) as well, for editors where LSP is the
shorter path (Helix, Neovim's built-in client, eglot).

Build the binary once and put it on `PATH` (see [Tools](#tools) above), and
any of the three will find it:

```bash
ady2nim c TOOLS/ADA_INDENT/ada_indent.ady
ln -sf "$PWD/TOOLS/ADA_INDENT/ada_indent" ~/.local/bin/ada_indent
```

The one idea all three share is that `ada_indent` is **stateful** — it carries
a stack of open blocks, so it cannot indent a line in isolation, and replaying
the file from the top on every keypress is O(file size). The binary therefore
offers `--emit-state` (interleave a `##STATE:…` line after each output line)
and `--state S` (resume from one), and each integration caches the last state
per buffer, sends only the lines since, and drops the cache when the buffer is
edited *strictly* above the cache point.

All three have test suites, and `make test` runs them — each SKIPping rather
than failing when its editor is absent, since none of node, emacs or vim is
otherwise a dependency here. Every suite drives the shipped integration against
the real binary and checks the same short list of properties, the state cache
included. [`TOOLS/ADA_INDENT/EDITOR_SUPPORT/README.md`](TOOLS/ADA_INDENT/EDITOR_SUPPORT)
has the details.

### Versioning one file — [`TOOLS/GIT1/`](TOOLS/GIT1)

[`TOOLS/GIT1/git1.ady`](TOOLS/GIT1/git1.ady) gives every tracked file its own private git
repository, named after the file and kept in a `.git1` container beside it, so
many tracked files share a directory without seeing each other. Its editor
support has the same problem to solve in both editors: a tracked file lives in
no repository that the editor can find by walking up the tree, so each
integration has to make the file's own directory count as a root and point the
git calls that follow at that file's repo.

| | |
|---|---|
| [`TOOLS/GIT1/git1.el`](TOOLS/GIT1/git1.el) | Emacs: `C-x v ...` on a tracked file, plus `C-c g` and branch commands VC has no equivalent for |
| [`TOOLS/GIT1/vscode-git1/`](TOOLS/GIT1/vscode-git1) | VS Code: the same idea, as a front end |

[`TOOLS/GIT1/README.md`](TOOLS/GIT1) covers the tool, the layout on disk, and why it
adopts a branch rather than merging one.

---

## Architecture

```
ADASCRIPT/
├── HPARSEC/                   Parser combinator engine and tokenizer
│                              (see HPARSEC/README.md)
│
├── GRAMMAR/                   Language-neutral grammar definitions
│   ├── ady_expr.py            Expression grammar (precedence, all operators)
│   ├── ady_stmt.py            Simple statements (assignment, import, raise, …)
│   ├── ady_compound_stmt.py   Compound statements (if/while/for/def/class/shell/…)
│   └── ady_declarations.py    Adascript type annotations and type declarations
│
├── TO_PYTHON/                 Python 3 backend
│   ├── hek_py_expr.py         to_py() for all expression nodes
│   ├── hek_py_stmt.py         to_py() for simple statements
│   ├── hek_py_parser.py       to_py() for compound statements + type decls
│   ├── hek_py_declarations.py to_py() for type annotations
│   └── ady2py.py              Entry point: parse + emit Python 3
│
├── TO_NIM/                    Nim backend
│   ├── hek_nim_expr.py        to_nim() for all expression nodes
│   ├── hek_nim_stmt.py        to_nim() for simple statements
│   ├── hek_nim_parser.py      to_nim() for compound statements + type decls
│   ├── hek_nim_declarations.py to_nim() for type annotations
│   ├── ady2nim.py             Entry point: parse + emit Nim
│   └── STDLIB/                Bundled runtime, reachable with `nimport`
│       ├── stdlib.nim         Nim shim for Python builtins (PriorityQueue, etc.)
│       ├── awk.ady            AwkProcessor record processor
│       ├── graphs.ady         Shortest paths, generic in the node type
│       ├── iters.ady          Iterator toolkit (take, chunks, pairwise, …)
│       ├── illwill.nim        Curses-like terminal library, pure Nim (one file)
│       └── db.ady, jointjs.ady, browser.ady, svg_drag.ady, svg_path.ady, commands.ady, page_server.ady, page_request.ady, server_page.ady, page_board.ady, page_alone.ady, store.ady, style.ady, karax_text.nim, expect.nim
│
├── EXAMPLES/                  End-to-end example programs (`*.ady`)
│                              Transpiled output is not kept here — it goes to
│                              ~/.cache/adascript/cache-<HASH>/
│
├── TOOLS/                     Programs written in Adascript that are tools in
│   │                          their own right, each with its own README
│   ├── ADA_INDENT/            Ada source indenter
│   │   ├── EDITOR_SUPPORT/    emacs/, vim/, vs_code/ — each calls the binary
│   │   └── LSP/               the same, for editors that prefer a server
│   └── GIT1/                  Per-file version control: one git repo per file
│       ├── git1.el            Emacs VC integration
│       └── vscode-git1/       the same idea for VS Code
│
├── LSP/                       Editing Adascript: language server, emacs,
│                              vscode, sublime
└── DOCS/                      Tutorials, topic references, and BOOK/
```

### How transpilation works

1. The tokenizer scans the source, adding the token types Python has no
   syntax for — the `'` of a tick attribute, `$` variables, ranges, regex
   literals, bash tests — and keeps inline comments attached so they survive
   into the output.
2. The grammar in `GRAMMAR/` defines the language, one rule per
   construct, independently of either target.
3. Each grammar rule gets a `to_py()` and a `to_nim()` method, in
   `TO_PYTHON/` and `TO_NIM/` respectively. Every method carries a docstring
   quoting the grammar rule it implements.
4. `ady2py.py` / `ady2nim.py` parse the module and walk the tree, calling
   `to_py()` or `to_nim()` on each node.

The engine underneath — combinator operators, the tokenizer's extra token
types, the parse-time state — is documented in
[HPARSEC/README.md](HPARSEC/README.md).

---

## Known Limitations

**Comments on a `case` header** — blank lines and inline comments survive
into the output, inside `def`, `class`, `for`, `while`, `if` and method
bodies alike. Two placements are still not reproduced faithfully, on both
backends:

```python
case c:                      # this comment is dropped
    when 1:                  # this one survives
        print "one"

type Color_T is enum RED, GREEN   # kept, but moved to the last member line
```

A comment on the `case` line itself is lost, and one on a `type ... is enum`
line is preserved but relocated, since the declaration expands to several
generated lines and the comment lands on the last of them.

**No bytes type** — `b"..."` is a plain string: the prefix is dropped on both
backends, so `b"x" == "x"` where Python would say otherwise. Nim's `string`
is a byte string, which makes that the faithful reading rather than a lossy
one, but nothing can be declared, passed or returned as bytes. `u"..."` is
dropped too, being a no-op since Python 3; an `r` in the prefix survives, so
`br"\d"` is `r"\d"`.

**Assignment copies on Nim, shares on Python** — a `record`, a plain `class`
and a `[]T` are values on the Nim backend and references on the Python one.
Assigning one to another name, appending it to a collection or passing it to
a function copies it on Nim and shares it on Python, so a change made through
one name is seen through the other on Python only. A `@virtual class` is
shared on both. [Copied on Nim, shared on Python](#copied-on-nim-shared-on-python) and the book's chapter 13 §13.2 show
the difference and how to write code that behaves the same on both.

**Decorators are Python-only** — Nim has no decorators. The Nim backend
reads five annotations written as decorators — `@contextmanager` (the
routine becomes a template, used with `with`), `@virtual` (a class shared by
reference), `@proc` (a method emitted as a plain proc), `@export` and
`@used` — and refuses any other, saying so. On the Python backend every
decorator passes through: `@property`, `@functools.cache`, one of your own.
A program meant for both backends keeps to the five.

A function of your own can be a decorator on both backends if it is a
*wrapper* marked `@decorator`: an ordinary top-level function handed the
function it wraps. `@aligned(64)` on `def f` means `f = aligned(64, f)`; the
transpiler keeps the original as `fBody` and writes a `def f` that calls
`aligned(64, fBody, ...)`, so no closures are involved. The wrapper's `f`
parameter must have the decorated function's type, the parameters after it
must be the decorated function's, and the leading ones are the decorator's
arguments; each mismatch is a one-line error. Stacked decorators apply
bottom-up. A wrapper keeps no state of its own, and lives in the same file as
what it decorates (`TESTS/test_decorators.ady`).

**Exhaustiveness is a Nim-build property** — a `case` block is checked for
completeness only when the Nim backend can make it a native `case`: an
ordinal subject whose branches are all constants. A string subject is not
checked, and a guard anywhere in the block switches the check off. Adascript
asks for `when others:` in exactly those two cases, but `ady2py` enforces
none of it, so a block that backend accepts can still be refused by
`ady2nim`. Chapter 5 has the table.

**Python backend maturity** — the Nim backend is the better-tested of the
two, since `make test` builds and runs every example through it. Every
example also transpiles to Python that parses, but the round-trip suite in
`TO_PYTHON/test_ady2py.py` still records failures, so treat the Python output
as the less exercised of the two and check it on anything unusual. Sweeping
every example through `ady2py` and parsing the result is a cheap way to catch
a regression the Nim-only test suite cannot see.

**Pattern forms with no Nim path** — four Python pattern spellings are
deliberately absent, each with a one-line rewrite (worked through in
[Chapter 5](DOCS/BOOK/05-pattern-matching.md#512-what-is-not-supported)):
mapping patterns (`case {"host": h}:` — test membership and read instead),
positional class patterns (`case Point_T(0, y):` — name the fields),
structural patterns inside an alternation (`case Point_T(x=0) | Circle_T(radius=0):`
— split the branches), and `as` over an alternation (`case 400 | 401 as code:`
— bind in the body).

**Modules on the Python backend are merged, not linked.** ady2nim compiles each
`import`ed `.ady` as a module of its own; ady2py replaces the `import` by the
module's text, where it is first imported and once, so what the module declares
-- an enum, a record, a failure type, a class -- is known to the program and
`case`, `is` and positional construction work across the boundary. The merge has
costs: the program is one namespace (two modules that each define `helper` clash
on Python and not on Nim), `geometry.distance` is rewritten to `distance` there, and refused where the file has a `distance` of its own, a parse error is reported at its line in the
merged text, and the libraries bundled with ady2nim (`TO_NIM/STDLIB/*.ady`) stay
Nim-only. A `nimport` with no `.ady` behind it (`nimport strutils`) is a Nim-only
import and is dropped from the Python output as before. `from geometry import *`
brings in everything, unqualified, as in Python; see
[Modules and Project Layout](#modules-and-project-layout).

**Nim stdlib coverage** — a few Python builtins reach Nim through the
`stdlib.nim` shim rather than natively; see [Bundled
libraries](#bundled-libraries).
