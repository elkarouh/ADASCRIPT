# Adascript

Adascript is a statically-typed superset of Python 3 that steals the best
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

Every valid Python 3 file is also valid Adascript. The extra features are purely
additive: left-to-right type annotations, Ada-style enums and variant records,
tick attributes, range expressions, `case/when` pattern matching, Perl/AWK-style
regex literals, and first-class shell command integration.

# Elucubrations
Pascal has set base minimum for systems programming languages. In Pascal it is possible to declare enumerated type and use it wherever ordinal type is accepted. Index an array and for loop. Ada has inherited this base minimum and enhanced by records with discriminants. In Rust I can see nothing but mess. Rust enumeration type can be used as neither array index nor for loop. Also, Rust for some unknown reason tangled records with discriminats and custom enumeration types in a way that cannot be untangled. Yeah, record with discriminant is a popular use of enumeration type, but everything becomes stupid if they come in inseparatable pack. Rust does not deliver base minimum. Wirth's minimum.

```
source.ady
    │
    ├── python3 TO_PYTHON/py2py.py source.ady  ──▶  Python 3
    └── python3 TO_NIM/py2nim.py   source.ady  ──▶  Nim
```

---

## Table of Contents

- [Quick Example](#quick-example)
- [Installation](#installation)
- [Usage](#usage)
- [Type Annotations](#type-annotations)
- [Type Declarations](#type-declarations)
- [Variable Declarations](#variable-declarations)
- [Range Expressions](#range-expressions)
- [Case / When Statements](#casewhen-statements)
- [Regex Literals](#regex-literals)
- [Tick Attributes](#tick-attributes)
- [Enum Array Literals](#enum-array-literals)
- [Named Tuple Literals](#named-tuple-literals)
- [Functions](#functions)
- [Classes and Inheritance](#classes-and-inheritance)
- [Nim-Only Imports](#nim-only-imports)
- [Python Interoperability](#python-interoperability)
- [Print Statement](#print-statement)
- [Shell Statements](#shell-statements)
- [Bash Variables](#bash-variables)
- [Benchmark Programs](#benchmark-programs)
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
git clone --recurse-submodules https://github.com/elkarouh/ADASCRIPT
cd ADASCRIPT
make install                      # or: make install PREFIX=$HOME/.local
```

`make install` puts `py2nim` and `py2py` on your PATH, so any `.ady` file
starting with `#!/usr/bin/env py2nim` runs directly:

```bash
chmod +x script.ady && ./script.ady
```

It installs into `/usr/local/bin`, falling back to `~/.local/bin` when that
is not writable, fetches the `HPARSEC` submodule if the clone omitted it, and
finishes by transpiling and running a small program to prove the install
works. `make uninstall` removes the launchers again.

The launchers are wrappers rather than symlinks so they can pin the
interpreter: the scripts' own shebang says `python3`, which on many systems
is older than the version the transpiler needs.

You can also skip the install and invoke the scripts directly —
`python3.12 TO_PYTHON/py2py.py source.ady` — but then the shebang line in the
examples will not resolve.

### Python dependencies

Python **3.12 or newer** (the tokenizer relies on `FSTRING_START` tokens,
which earlier versions do not emit). Nothing beyond the standard library.

### Nim dependencies

| Package | Install | Required for |
|---------|---------|--------------|
| `nimpy` | `nimble install nimpy` | Any `.ady` file that uses `pyimport` to call Python libraries from Nim |
| `db_connector` | `nimble install db_connector` | Any `.ady` file that uses `nimport db` (SQLite support; removed from Nim 2.x stdlib) |
| `zig` / `zigcc` | *optional* — download from [ziglang.org](https://ziglang.org/download/), then `printf '#!/bin/sh\nexec zig cc "$@"\n' > /usr/local/bin/zigcc && chmod +x /usr/local/bin/zigcc` | Preferred by files pinning `#ady2nim-args c --cc:clang --clang.exe:zigcc` — `state_search.ady`, `shortest_path.ady`, their tests, and the timetable examples |

Standard library Nim modules (`std/deques`, `tables`, `hashes`, `math`, `re`, `posix`, …) are bundled with Nim and need no separate install.

A compiler pin is a preference, not a requirement. When the pinned binary is
not installed, `py2nim` drops the pin — with a note on stderr — and lets Nim
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
python3 TO_PYTHON/py2py.py source.ady         # print to stdout
python3 TO_PYTHON/py2py.py -c source.ady      # transpile and run
echo "var x: int = 42" | python3 TO_PYTHON/py2py.py  # from stdin
```

### Transpile to Nim

```bash
python3 TO_NIM/py2nim.py source.ady           # transpile and compile+run (default)
python3 TO_NIM/py2nim.py -t source.ady        # transpile only, write source.nim
python3 TO_NIM/py2nim.py c source.ady         # compile (nim c)
python3 TO_NIM/py2nim.py c -r source.ady      # compile and run (nim c -r)
python3 TO_NIM/py2nim.py --test               # run built-in self-tests
```

**Incremental builds** — `py2nim` performs a three-tier up-to-date check:
skip transpilation if `.nim` is newer than both `.ady` and the transpiler
source files; skip compilation if the binary is newer than `.nim`; execute
the existing binary directly if everything is current. Changing any
transpiler `.py` file automatically triggers retranspilation of all cached
`.ady` files on their next run.

**Clean source directories** — all generated artifacts (`.nim` file,
compiled binary, nimcache) are stored in `~/.cache/hparsec/cache-<HASH>/`,
keyed by the absolute path of the `.ady` file. Source directories stay
uncluttered and the cache survives reboots (inspired by
[nimbang](https://github.com/jabbalaci/nimbang)).

**Shebang support** — add `#!/usr/bin/env py2nim` as the first line of an
`.ady` file and make it executable. The file compiles and runs directly
without arguments to the transpiler.

**Per-file compiler options** — add an `#ady2nim-args` directive as the
second line to set per-file nim options (inspired by nimbang's
`#nimbang-args`). The first token may be a nim subcommand; remaining tokens
are forwarded to the nim compiler. Command-line flags always override the
directive.

A compiler pin in the directive (`--cc:NAME`, `--NAME.exe:BIN`,
`--NAME.linkerexe:BIN`) is treated as a preference. If the named binary is
not installed, `py2nim` drops just that flag, notes it on stderr, and lets
nim use its default C compiler — so a file pinning `zigcc` still builds on a
machine without zig. Every other flag in the directive is passed through
untouched.

```python
#!/usr/bin/env py2nim
#ady2nim-args c -d:release
```

**Symlink next to source** — after a successful compile, `py2nim` creates a
symlink in the same directory as the `.ady` file pointing to the cached
binary. Running `./script` from the source directory works without any path
gymnastics.

**Forwarding flags to Nim** — any flag not recognised by `py2nim` (e.g.
`-d:release`, `--opt:speed`) is passed straight to `nim`.

```bash
python3 TO_NIM/py2nim.py c -d:release source.ady   # optimised build
```

---

## Type Annotations

Adascript uses a concise **left-to-right** annotation syntax rather than
Python's `typing` module. Container kinds are expressed as prefixes:
`[]int` reads naturally as "list of int".

| Adascript        | Python                    | Nim                            |
|----------------|---------------------------|--------------------------------|
| `[]T`          | `list[T]`                 | `seq[T]`                       |
| `[N]T`         | `tuple[T, ...]`           | `array[N, T]`                  |
| `[*]T`         | `Sequence[T]`             | `openArray[T]`                 |
| `[E]T`         | `dict[E, T]`              | `array[E, T]` (enum-indexed)   |
| `{K}V`         | `dict[K, V]`              | `Table[K, V]`                  |
| `{}T`          | `set[T]`                  | `HashSet[T]` or `set[T]`       |
| `?T`           | `T \| None`               | `Option[T]`                    |
| `(T, U)`       | `tuple[T, U]`             | `(T, U)`                       |
| `[(T, U)]R`    | `Callable[[T, U], R]`     | `proc(a0: T, a1: U): R`        |

Types compose freely:

```python
var words:    []str        = ["hello", "world"]
var counts:   {str}int     = {"hello": 1}
var maybe:    ?int         = None
var grid:     [][]float    = [[1.0, 2.0], [3.0, 4.0]]
var callback: [(int,)]bool = my_predicate
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

---

## Type Declarations

### Enums

```python
type Color   is enum RED, GREEN, BLUE
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are accepted as the assignment keyword.

**Python output:** `class Color(Enum): RED = auto(); GREEN = auto(); BLUE = auto()`
**Nim output:** `type Color = enum RED, GREEN, BLUE`

### Subranges

```python
type SmallInt is 0 .. 255    # inclusive on both ends
type Index    is 0 ..< 10    # exclusive upper bound (0–9)
```

### Named Tuples

```python
type Point is tuple:
    x: float
    y: float
```

**Python output:** `class Point(NamedTuple): ...`
**Nim output:** `type Point = tuple`

### Records (Dataclasses)

```python
type Person is record:
    name: str
    age:  int
```

**Python output:** `@dataclass class Person: ...`
**Nim output:** `type Person = object`

### Discriminated Records (Variant Types)

Ada/Nim-style variant records where the set of fields depends on an enum
discriminant. The discriminant is declared in parentheses after the type
name:

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

**Nim output** — native variant object:

```nim
type Shape = object
  case Kind: Shape_Kind
  of Circle:
    Radius: float
  of Rectangle:
    Width:  float
    Height: float
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

---

## Variable Declarations

```python
var   x: int    = 10       # mutable
let   name: str = "hello"  # immutable (Nim: let; Python: annotated assignment)
const MAX: int  = 1000     # compile-time constant
```

Declarations without an initial value are valid:

```python
var result: []int          # Nim: seq[int]; Python: list[int]
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

---

## Case / When Statements

Pattern matching with Ada/Nim-inspired syntax. All standard pattern kinds
are supported: literals, captures, wildcards, OR-patterns, ranges,
sequences, mappings, class patterns, and `as` bindings.

Python 3.10+ `match` / `case` is accepted as well, so Adascript stays a
superset; use it when a branch needs an `if` guard, which `case` / `when`
does not provide. See [TUTORIAL.md](TUTORIAL.md#11-control-flow) and
[PATTERN_MATCHING.md](PATTERN_MATCHING.md) for the two side by side.

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

Tuple patterns with wildcards (desugars to `if/elif` in Nim):

```python
let (year, age) = current_state
case (year, age):
    when (6, _):
        []
    when (0, _):
        [(BUY, maintenance_cost[0] + market_value[0])]
    when (_, 3):
        [(TRADE, -market_value[age] + market_value[0] + maintenance_cost[0])]
    when others:
        [(KEEP, maintenance_cost[age])]
```

**Python output:** standard `match/case` statement.
**Nim output:** `if/elif/else` chain (Nim does not support tuple case selectors).

**Subject must be a structural expression, not a plain variable.**
The tuple/structural desugar path triggers only when the `case` subject is
written as a compound expression (`(x, y)`, `x.field`). A plain variable
holding a tuple falls through to Nim's native `case`, which rejects runtime
values and causes a compile error. Write:

```python
let (f, w, g, c) = state
case (f, w, g, c):       # ✓ tuple expression as subject
    when (right, right, right, right): ...
```

not:

```python
case state:              # ✗ plain variable — emits Nim `case`, fails at compile
    when (right, right, right, right): ...
```

---

## Regex Literals

Adascript has first-class regex literal syntax: `/pattern/flags`. Regexes
work with `==` / `!=`, `case/when`, and the substitution form `s/pat/repl/`.
There is no need to `import re`.

### Match test

```python
if line == /error/i:
    print "found error"

if text != /^\s*$/:
    process(text)
```

### Positional captures

After a successful `== /pat/` match, `$+0` holds the whole match, `$+1` the
first capture group, `$+2` the second, and so on:

```python
if src == /^([a-zA-Z_]\w*)\s*=\s*(.+)$/:
    name:  str = $+1
    value: str = $+2
```

### Named captures

Use `(?P<name>...)` groups; after a match the `namedCaptures` dict holds the
results:

```python
if line == /(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/:
    year:  str = namedCaptures["year"]
    month: str = namedCaptures["month"]
```

### Find all (`/g`)

Adding the `g` flag returns all non-overlapping matches as `[]str`:

```python
let words:  []str = text == /\w+/g
let digits: []str = line == /\d+/g
```

### Substitution

```python
text == s/\s+/ /g         # collapse whitespace runs
name == s/[^a-z]//gi      # strip non-alpha characters
```

### Regex patterns in `case/when`

Regex literals work directly as `when` patterns; the compiler desugars the
whole `case` block to an `if/elif/else` chain:

```python
def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER
```

### Flags

| Flag | Meaning |
|------|---------|
| `i`  | Case-insensitive |
| `g`  | Return all matches as `[]str` |
| `m`  | Multiline — `^`/`$` match line boundaries |
| `s`  | Dotall — `.` matches newlines |

### Translation reference

| Adascript | Nim (generated) | Python (generated) |
|-----------|-----------------|-------------------|
| `s == /pat/` | `nimatch(s, re"pat")` | `_pymatch(s, r'pat')` |
| `s == /pat/i` | `nimatch(s, re"(?i)pat")` | `_pymatch(s, r'pat', re.IGNORECASE)` |
| `s != /pat/` | `not nimatch(s, re"pat")` | `not _pymatch(s, r'pat')` |
| `s == /pat/g` | `s.findAll(srx.re(r"pat"))` | `re.findall(r'pat', s)` |
| `$+0` … `$+N` | `matches[0]` … `matches[N]` | `matches[0]` … `matches[N]` |
| `$+{k}` | `namedCaptures["k"]` | `namedCaptures["k"]` |
| `s == s/pat/repl/g` | `s = s.replace(srx.re(r"pat"), "repl")` | `s = re.sub(r'pat', r'repl', s)` |
| `when /pat/:` in `case` | `elif nimatch(subject, re"pat"):` | `elif _pymatch(subject, r'pat'):` |

`nimatch`/`_pymatch`, `matches`, and `namedCaptures` are injected automatically
into the generated file whenever a regex literal is used.

---

## Tick Attributes

Ada-style `'` attributes provide first-class access to enum and subrange
metadata. The tokenizer preprocesses `Type'Attr` to `Type__tick__Attr`
before parsing, so Python's lexer is not confused by the apostrophe.

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

---

## Enum Array Literals

Arrays indexed by enum members use `[KEY: value, ...]` syntax, mapping
cleanly to Python dicts and Nim enum-indexed arrays:

```python
type Priority is enum LOW, MED, HIGH

var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
```

**Python output:** `{Priority.LOW: 1, Priority.MED: 5, Priority.HIGH: 10}`
**Nim output:** `[LOW: 1, MED: 5, HIGH: 10]`

Nested enum arrays (for 2-D lookup tables):

```python
var trans_p: [Hidden_State_T][Symptom_T]float = [
    HEALTHY: [NORMAL: 0.5, COLD: 0.4, DIZZY: 0.1],
    FEVER:   [NORMAL: 0.1, COLD: 0.3, DIZZY: 0.6],
]
```

---

## Named Tuple Literals

Construct named tuples with `(field: value)` syntax. The transpiler matches
field names against registered `type … is tuple` declarations:

```python
type Point is tuple:
    x: float
    y: float

p = Point(x: 1.0, y: 2.5)
```

**Python output:** `p = Point(x=1.0, y=2.5)`
**Nim output:** `p = (x: 1.0, y: 2.5)`

Named tuple literals also work inside collections and as function arguments:

```python
fringe.push((stage: STAGE1, budget: float(CAPITAL)))
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

Parameters follow Python's rules on both backends. Rebinding the name is
local to the function; mutating the object in place is visible to the caller:

```python
def rebind(s: str) -> str:
    s = s + "!"        # local — the caller's string is unchanged
    return s

def append_to(xs: []int):
    xs.append(99)      # in-place — the caller sees the new element
```

The Nim backend infers this: a rebound parameter is shadowed by a mutable
local (`var s = s`), while one that is mutated in place becomes a `var`
parameter (`xs: var seq[int]`). No annotation is needed either way.

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

### Generic Classes

```python
class Optimizer[S, D, C]:
    var offset: float

    def __init__(self, offset: float = 0.0):
        self.offset = offset

    def evaluate(self, state: S) -> float:
        return 0.0
```

Nim output uses `[S, D, C]` generic parameters on the object type and all
generated procs.

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
fields that differ per instance:

```python
class AwkProcessor(AwkBase):
    var NR        : int = 0
    var NF        : int = 0
    var total_len : int = 0
    var counts    : [Severity_T]int = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]

    def __init__(self, fs: str = " ", ofs: str = " "):
        self.FS  = fs   # only non-defaulted fields need setting
        self.OFS = ofs
```

### Mutable self in non-virtual classes

For plain (non-`@virtual`) classes, the transpiler automatically detects
whether a method mutates `self` (field assignment, `+=`, `.add()`, or any
`self.method()` call) and emits `self: var ClassName` in the generated Nim.
No annotation is needed:

```python
class Counter:
    var count: int = 0

    def increment(self):
        self.count += 1   # transpiler emits: proc increment(self: var Counter)
```

`@virtual` is only needed when subclasses live in a **different file** (module)
from their base class — it makes Nim use `ref object` for dynamic dispatch
across module boundaries.

### Forwarding constructors

When a subclass has no `__init__`, the transpiler generates a forwarding
constructor that mirrors the parent's parameters and calls the parent's
initialiser automatically:

```python
@virtual
class AwkBase:
    var FS: str
    var OFS: str

    def __init__(self, fs: str = " ", ofs: str = " "):
        self.FS  = fs
        self.OFS = ofs

class AwkProcessor(AwkBase):
    var counts: [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]
    # no __init__ needed — AwkProcessor(fs, ofs) is generated automatically
```

---

## Nim-Only Imports

`nimport` marks imports that appear only in Nim output and are stripped
from Python output. Use it for Nim standard-library modules that have no
Python equivalent:

```python
nimport strutils, sequtils, algorithm, stdlib
```

---

## Raw Nim Injection

A comment of the form `# nimraw: <code>` is passed through verbatim to the
Nim output and stripped from Python output. This is mainly useful for Nim
**forward declarations** when two functions are mutually recursive and
AdaScript has no forward-declaration syntax:

```python
# nimraw: proc scheme_eval(x: Val, eid: int): Val   # forward decl
def scheme_apply(proc_val: Val, args: []Val) -> Val:
    ...
    return scheme_eval(...)   # calls the forward-declared proc

def scheme_eval(x: Val, eid: int) -> Val:
    ...
    return scheme_apply(...)
```

The transpiler replaces each `# nimraw:` line with the raw code that follows
the prefix, leaving Python output unaffected (Python ignores the comment).

Use `# nimraw:` sparingly — it bypasses the type system and produces Nim-only
output. For most Nim-specific needs, prefer `nimport` or `#ady2nim-args`.

---

## Python Interoperability

Adascript knows whether each Python `import` has a direct Nim equivalent or
needs the [nimpy](https://github.com/yglukhov/nimpy) bridge. You write
ordinary Python imports; the transpiler decides how to map them.

### Natively mapped stdlib modules

These modules translate directly to their Nim counterparts with no runtime
overhead:

| Python import    | Nim module         | Notes                            |
|------------------|--------------------|----------------------------------|
| `import os`      | `import os`        | `os.path.*` → Nim path procs     |
| `import math`    | `import math`      | All standard functions mapped    |
| `import time`    | `import times`     |                                  |
| `import re`      | `import re`        | Superseded by native `/pat/` literals |
| `import random`  | `import random`    |                                  |
| `import json`    | `import std/json`  |                                  |
| `import itertools`| `import sequtils` |                                  |
| `import asyncio` | `import asyncdispatch` |                              |

### Function call translation

```python
import math, time, re, random

x      = math.sqrt(4.0)
t      = time.time()
result = re.sub(r'\s+', ' ', text)
n      = random.randint(1, 100)
```

**Nim output:**

```nim
import math, re, random, times

var x      = sqrt(4.0)
var t      = epochTime()
var result = replace(text, re("\\s+"), " ")
var n      = rand(1..100)
```

### `os` and `sys` utilities

```python
import os, sys

if os.path.exists('/tmp/data'):
    p = os.path.join('/tmp', 'data', 'out.txt')
    os.makedirs('/tmp/data')

sys.exit(1)
```

**Nim output:**

```nim
import os

if fileExists("/tmp/data"):
    var p = joinPath("/tmp", "data", "out.txt")
    createDir("/tmp/data")

quit(1)
```

### Non-native Python libraries (nimpy bridge)

Libraries with no direct Nim equivalent are imported via nimpy automatically:

```python
import requests
import pandas as pd

r  = requests.get('https://example.com')
df = pd.read_csv('data.csv')
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
import requests

r     = requests.get('https://api.example.com/data')
count: int   = r.json()['total']
score: float = r.json()['score']
name:  str   = r.json()['name']
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
import scipy.interpolate as interp

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

### Variable and expression interpolation

Use `{name}` anywhere in the command body to interpolate an Adascript variable.
Function calls and other complex expressions also work inside `{}` — the
transpiler hoists them to temp variables automatically:

```python
let name = "world"
let result = shell: echo hello {name}

def Q(s: str) -> str:
    "'" + s.replace("'", "'\\''") + "'"

shell: mkdir -p -- {Q(os.path.join(d, "subdir"))}
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

### Setting the child's environment

`env = expr` takes a `{str}str` and **adds** to the environment the child
inherits, rather than replacing it:

```python
let extra: {str}str = {"GIT_DIR": repo, "LC_ALL": "C"}
let r = shell(env = extra): git status
```

Names already in the environment are overridden; everything else — `PATH`
included — is still there. Like `stdin`, it applies to the capturing forms.

### Options

```python
let result = shell(cwd = "/tmp"):           pwd
let result = shell(timeout = 5000):         slow-command
let result = shell(cwd = "/tmp", timeout = 3000): ls -la
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
# from EXAMPLES/test_shell_block.ady
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

### Environment variables

All-caps identifiers with `$` read an environment variable:

```python
home   = $HOME
path   = $PATH
editor = $EDITOR
```

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
| `-s path`    | `os.path.getsize(path) > 0`     | `fileExists(path) and getFileSize(path) > 0` |
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

Calling an enum type with a string argument emits `parseEnum`:

```python
type State = enum ACTIVE, ON_HOLD, DONE

def parse_state(s: str) -> State:
    try:
        State(s.replace("-", "_"))
    except:
        ACTIVE
```

Transpiles to:

```nim
proc parse_state(s: string): State =
    try:
        parseEnum[State](s.replace("-", "_"))
    except:
        ACTIVE
```

---

## Benchmark Programs

The `EXAMPLES/` directory contains real programs that exercise the full
language and serve as end-to-end tests. Each has a `.ady` source, a
transpiled `.nim` output, and in most cases a reference Python `.py` file.

### `primes.ady` — Prime sieve

Counts primes up to 1,000,000 and measures wall time. Demonstrates the
`..` and `..<` range operators and `time.perf_counter()`.

```python
def is_prime(n: int) -> bool:
    for k in 2 .. int(n ** 0.5):
        if n % k == 0:
            return False
    return True

for k in 2 ..< N:
    if is_prime(k): count += 1
```

### `graph.ady` — Graph path search

Three path-finding functions (find_path, find_all_paths, find_shortest_path)
on a dict-of-lists graph. Exercises recursive functions, `[]str` default
parameters, `not in`, and `append`.

```python
type Node_T  is str
type Graph_T is {Node_T}[]Node_T

def find_path(graph: Graph_T, start: Node_T, end: Node_T,
              path: []Node_T = []) -> []Node_T:
    ...
```

### `phonecode.ady` — Phone code benchmark

Implements Prechelt's classic benchmark: find all word encodings of phone
numbers using a trie. Exercises enums, dict types, optional types, nested
classes, closures, and `$#`/`$1`/`$2` argument variables.

```python
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9

class TrieNode:
    var children: [Digit_T]TrieNode
    var words:    []str
    ...
```

### `shortest_path.ady` — Generic optimiser framework

A 450-line framework demonstrating: generic classes `[S, D, C]`, nested
type declarations, `yield` (generator methods), discriminated tuples,
tick-attribute iteration, and 8 complete algorithm examples including
Dijkstra, A*, dynamic programming, knapsack, rod cutting, HMM Viterbi,
equipment replacement, and capital budgeting.

```python
class Optimizer[S, D, C]:
    def shortest_path(self, start_state: S, end_state: S, allsolutions: bool = True):
        fringe: PriorityQueue[Fringe_Element_T[S, D, C]] = PriorityQueue(...)
        while fringe:
            ...
            yield self.real_cost(cost), path
```

### `awk_example.ady` / `awk_OO.ady` — awk-style line processor

A stdin line processor that classifies lines as ERROR/WARN/INFO/OTHER via
regex, prints severity-prefixed output, and prints a summary (record count,
average line length, average field count, per-severity counts).

`awk_example.ady` is the procedural version. `awk_OO.ady` is the class-based
version, demonstrating field defaults, auto-`var self`, and inheritance:

```python
@virtual
class AwkBase:
    var FS: str
    var NR: int = 0
    var NF: int = 0

    def read_record(self, raw: str): ...   # parse line into self.line / self.Fields
    def process_record(self): raise NotImplementedError(...)
    def begin(self): pass
    def finish(self): pass
    def run(self):
        self.begin()
        for raw in stdin.lines:
            self.read_record(raw)
            self.process_record()
        self.finish()

class AwkProcessor(AwkBase):   # no __init__ needed
    var counts: [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]

    def process_record(self): ...
    def begin(self): print "--- awk report ---"
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

---

## Architecture

```
hparsec/
├── hek_parsec.py               Parser combinator engine
│                               ParserMeta (+, |, [], *, ~), packrat memoization,
│                               SymbolTable, forward references, token helpers
│
├── hek_tokenize.py             Enhanced tokenizer
│                               RichNL (comments attached to newlines),
│                               tick-attribute preprocessing (Type'Attr),
│                               bracket-context NL stripping
│
├── hek_helpers.py              Shared indentation and RichNL utilities
│
├── ADASCRIPT_GRAMMAR/            Language-neutral grammar definitions
│   ├── py3expr.py              Expression grammar (precedence, all operators)
│   ├── py3stmt.py              Simple statements (assignment, import, raise, …)
│   ├── py3compound_stmt.py     Compound statements (if/while/for/def/class/shell/…)
│   └── py_declarations.py      Adascript type annotations and type declarations
│
├── TO_PYTHON/                  Python 3 backend
│   ├── hek_py3_expr.py         to_py() for all expression nodes
│   ├── hek_py3_stmt.py         to_py() for simple statements
│   ├── hek_py3_parser.py       to_py() for compound statements + type decls
│   ├── hek_py_declarations.py  to_py() for type annotations
│   └── py2py.py                Entry point: parse + emit Python 3
│
├── TO_NIM/                     Nim backend
│   ├── hek_nim_expr.py         to_nim() for all expression nodes
│   ├── hek_nim_stmt.py         to_nim() for simple statements
│   ├── hek_nim_parser.py       to_nim() for compound statements + type decls
│   ├── hek_nim_declarations.py to_nim() for type annotations
│   ├── py2nim.py               Entry point: parse + emit Nim
│   ├── stdlib.nim              Nim shim for Python builtins (PriorityQueue, etc.)
│   └── awk.ady                 Bundled Adascript stdlib: AwkBase record processor
│
└── EXAMPLES/                  End-to-end example programs
    ├── *.ady                   Adascript source
    ├── *.nim                   Transpiled Nim output
    └── stdlib.nim              Nim shim for Python builtins (PriorityQueue, etc.)
```

### How transpilation works

1. `hek_tokenize.Tokenizer` scans the source, preprocesses tick attributes
   (`Type'Attr` → `Type__tick__Attr`), and bundles inline comments into
   `RichNL` objects so they travel with the parse tree.
2. The grammar combinators in `ADASCRIPT_GRAMMAR/` define the language using
   `hek_parsec` operators. Parsers are plain classes composed with `+`, `|`,
   and `[:]`; forward references use `fw("name")`.
3. Each grammar rule class gets `to_py()` and `to_nim()` methods attached
   via the `@method` decorator (defined in the respective backend modules).
   Every method carries a docstring quoting the grammar rule it implements.
4. `py2py.py` / `py2nim.py` parse the full module and walk the AST, calling
   `to_py()` or `to_nim()` on each node.

### Parser combinator operators

| Expression  | Meaning                                      |
|-------------|----------------------------------------------|
| `A + B`     | Sequence: match A then B                    |
| `A \| B`    | Ordered choice: try A, fall back to B       |
| `A[1:]`     | One or more repetitions                     |
| `A[:]`      | Zero or more repetitions                    |
| `A[n:m]`    | Between n and m repetitions                 |
| `A * n`     | Exactly n repetitions                       |
| `~A`        | Negative lookahead: succeed only if A fails |
| `fw("X")`   | Lazy forward reference (recursive grammars) |

---

## Known Limitations

**Blank lines and inline comments** — `py2py.py` currently collapses blank
lines between statements and drops inline comments (`x = 1  # note`). The
infrastructure for fixing this (`RichNL` carrying comments through the parse
tree) is already in place; the remaining work is threading those tokens
through all compound-statement `to_py()` methods.

**Python backend maturity** — the Nim backend is the better-tested of the two.
Several constructs still transpile to Python that does not run: implicit
return does not reach into `if`/`else` branches, `Natural` and `Positive` are
emitted into annotations without being defined, and a declaration written
without an initialiser binds no value. Each is written up with a reproduction
in the [TODO list](TODO.md#python-backend-py2py--known-bugs). Programs that
avoid those constructs transpile and run on both backends.

**Nim stdlib coverage** — generated Nim code relies on a local `stdlib.nim`
shim for some Python builtins (`PriorityQueue`, `FifoQueue`, `ANY`). See
`TO_NIM/stdlib.nim`.

**Bundled Adascript libraries** — `.ady` files in `TO_NIM/` are automatically
installed into the build cache so they can be used via `nimport` from any
directory without a local copy:

| `nimport` name | Provides              |
|----------------|-----------------------|
| `nimport awk`  | `AwkBase` — generic stdin record-processor base class |

**Global parser state** — `ParserState` is a class-level singleton, so
independent parse runs in the same process share it. For a *sequence* of
runs, `ParserState.reset()` between them is still the simplest thing. For a
*nested* run — translating one unit while another is in progress — use the
context manager, which saves the state on entry and restores it on exit, so
the inner unit may `reset()` and mutate freely:

```python
with ParserState.scoped():
    translate(inner_source)      # free to reset() and mutate
# the outer unit's state is back
```

`snapshot()` and `restore()` are the same mechanism without the `with`.
Containers are copied one level deep, so in-place mutation inside the nested
run does not leak into the captured state. None of this makes the singleton
thread-safe: concurrent parses in separate threads remain unsupported.
