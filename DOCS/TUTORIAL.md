# Adascript Tutorial

Adascript is a statically-typed language built on Python 3 that steals the best
features from many languages: **Ada** (enums, variant records, tick attributes,
subranges), **Nim** (compile target and type system), **Perl** and **AWK**
(first-class regex literals `/pat/flags`, `$+N` captures, substitution), and
**Bash** (`$1`/`$#`/`$@`, file-test operators, `shell:` blocks). Most Python 3
code is valid Adascript as it stands; the exception is `import`, which has to
say where a module comes from — `import` for an Adascript (`.ady`) module,
`nimport os` for a Nim module, `pyimport numpy` for a Python package — and a plain
`import os` is refused on both backends.
You write one source file; both ecosystems get idiomatic, efficient output.

```
source.ady  ──▶  python3 TO_PYTHON/ady2py.py source.ady  ──▶  Python 3
            ──▶  python3 TO_NIM/ady2nim.py   source.ady  ──▶  Nim
```

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Type Annotations](#2-type-annotations)
3. [Variable Declarations](#3-variable-declarations)
4. [Enums](#4-enums)
5. [Named Tuples](#5-named-tuples)
6. [Records and Variant Records](#6-records-and-variant-records)
7. [Collections](#7-collections)
8. [Subranges](#8-subranges)
9. [Tick Attributes](#9-tick-attributes)
10. [Range Expressions](#10-range-expressions)
11. [Control Flow](#11-control-flow)
12. [Functions](#12-functions)
13. [Classes and Inheritance](#13-classes-and-inheritance)
14. [Generic Classes](#14-generic-classes)
15. [Shell Integration](#15-shell-integration)
16. [Bash Variables and File Tests](#16-bash-variables-and-file-tests)
17. [Nim-Only Imports](#17-nim-only-imports)
18. [Real Examples](#18-real-examples)
19. [Regex Literals](#19-regex-literals)
20. [Memory Ownership](#20-memory-ownership)
21. [Programming in the Large](#21-programming-in-the-large)
22. [Summary of Adascript-Only Syntax](#summary-of-adascript-only-syntax)

---

## 1. Getting Started

### File structure

Adascript files use the `.ady` extension. The first two lines can carry a
shebang and per-file compiler options:

```python
#!/usr/bin/env ady2nim
#ady2nim-args c --cc:clang -d:release
```

With the shebang line and `chmod +x`, you can execute the file directly:

```bash
./hello.ady        # compiles (cached) and runs
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

### The simplest program

```python
#!/usr/bin/env ady2nim
print "Hello, world!"
```

Python 2-style `print` without parentheses is fully supported — the transpiler
rewrites it to `print(...)` in Python 3 and `echo(...)` in Nim. The call form
`print(...)` also works unchanged.

### Running programs

```bash
# Transpile to Python 3 and print to stdout
python3 TO_PYTHON/ady2py.py source.ady

# Transpile to Python 3 and run
python3 TO_PYTHON/ady2py.py -c source.ady

# Transpile to Nim and compile+run (default)
python3 TO_NIM/ady2nim.py source.ady

# Transpile only — writes the .nim into the cache and prints its path
python3 TO_NIM/ady2nim.py -t source.ady

# Optimised build
python3 TO_NIM/ady2nim.py c -d:release source.ady
```

All build artifacts go into `~/.cache/adascript/cache-<HASH>/`, keeping your
source directory clean. Builds are incremental: re-runs skip transpilation or
compilation whenever the cached output is newer than both the source and the
transpiler itself.

---

## 2. Type Annotations

Adascript uses **left-to-right** annotation syntax. Container kinds are
prefixes, so `[]int` reads "list of int" and `{str}int` reads "dict mapping
str to int".

There is one idea behind the whole table, and it is worth having up front:
two independent questions settle which form you want.

- **Is it ordered?** — the *shape* of the brackets. `[…]` is ordered, `{…}`
  is not.
- **Is it keyed?** — whether anything sits *inside* them. Nothing inside
  (`[]T`, `{}T`) is a **collection** of `T`; a type inside (`[K]T`, `{K}V`)
  is a **mapping**, from the bracketed type to the one that follows.

|                | ordered `[…]`                    | unordered `{…}` |
|----------------|----------------------------------|-----------------|
| **collection** | `[]T` — a list                   | `{}T` — a set   |
| **mapping**    | `[K]T` — keys in order           | `{K}V` — a dict |

The two questions meet in one place: what order a `[…]` mapping has depends
on its key. With a **finite ordinal** key — an enum, `bool`, `char`, or an
integer subrange — all the keys and their order are known at compile time,
and `[O]T` is an array indexed by `O`. With any other key — `str`, `int`, a
class — the keys are ordered by **insertion**: `[str]float` is an
`OrderedTable` on Nim and a dict on Python. Between `{…}` any hashable type
works, in no promised order.

That makes the fixed-size array unremarkable rather than a special case: a
length is shorthand for a subrange, so `[10]int` and `[0..9]int` are one
type. On the Nim backend `array[10, int] is array[0..9, int]` is literally
`true`. And `{:}` versus `{}` stops being arbitrary — the colon of a
`key: value` pair marks the mapping, so `{:}` is the empty dict and bare
`{}` the empty set.

Underneath, a collection is a mapping that supplies its own key: a list maps
positions to elements, a set maps elements to in-or-out. That is why `xs[i]`
and `x in s` are both lookups, and why a set cannot hold anything twice.

**What a loop gives you.** `for x in c`, and `x in c` with it, give the half
of the mapping that is *not known in advance* — that is the information.

- Keys known in advance → **the values**. `[Color]int`'s keys are `RED,
  GREEN, BLUE`, fixed by its type, so `for x in score` gives the scores and
  `x in score` asks whether some colour has that score. A list and a fixed
  array are the same: their keys are positions, known from the length.
- Keys not known in advance → **the keys**. A `{str}int` holds whichever
  words arrived, and which ones is what you want to know: `for w in counts`
  gives the words, `w in counts` asks whether one occurred. A `[str]float`
  is the same, in the order the keys arrived.
- A set is the limiting case: `{}str` maps each element to present or
  absent, so its elements — its keys — are all there is to give.

| | keys known in advance? | `for x in c`, `x in c` |
|---|---|---|
| `[]T`, `[N]T`, `[E]T`, `[lo..hi]T` | yes | the values |
| `[str]V`, `{K}V` | no | the keys |
| `{}T` | no — the elements are the keys | the elements |

`.keys()`, `.values()` and `.items()` give the other half, or both;
`enumerate(c)` gives `(position, element)` for a list and `(key, value)`
for every mapping.

"Unordered" is a portability rule, not a mnemonic: the same `{str}int`
iterates in insertion order on Python and hash order on Nim. Sort the keys
if the output has to match.

| Adascript      | Python                | Nim                            |
|----------------|----------------------|--------------------------------|
| `[]T`          | `list[T]`            | `seq[T]`                       |
| `[N]T`         | `tuple[T, ...]`      | `array[N, T]`                  |
| `[*]T`         | `Sequence[T]`        | `openArray[T]`                 |
| `[E]T`         | `dict[E, T]`         | `array[E, T]` (enum-indexed)  |
| `[K]V`         | `dict[K, V]`         | `OrderedTable[K, V]` (K not a finite ordinal) |
| `{K}V`         | `dict[K, V]`         | `Table[K, V]`                  |
| `{}T`          | `set[T]`             | `HashSet[T]` or `set[T]`      |
| `?T`           | `T \| None`          | `Option[T]`                    |
| `(T, U)`       | `tuple[T, U]`        | `(T, U)`                       |
| `(T, U) -> R`  | `Callable[[T,U], R]` | `proc(a0: T, a1: U): R`       |

Types compose freely — a graph as an adjacency list is a `{…}` mapping
whose values are a `[…]` collection:

```python
type Node_T is str
type Graph_T is {Node_T}[]Node_T

graph: Graph_T = {'A': ['B', 'C'], 'B': ['C', 'D']}
```

Add weights by making the element a named tuple, which is what
`dijkstra.ady` does — `{Node_T}[]Neighbour_T`, three levels in one line.

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
`proc(a0: int, a1: int): int`.

A pure function is a mapping, but it is not written `{(int, int)}int`: that
is a dict keyed by a tuple, which can be iterated, counted and written to.
A function can only be called. The declaration says which one you have.

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

### Empty collection literals

Python's `{}` is ambiguous (empty dict or empty set). Adascript resolves this:

```python
var counts:  {str}int = {:}    # empty dict  → Python: {}   Nim: initTable[...]()
var visited: {}str    = {}     # empty set   → Python: set() Nim: initHashSet[...]()
```

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
differently (see `TODO.md`). The README's "Paths: `Path` and `/`" has the
operations.

### `distinct` types

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
Cents_T * Qty_T`. Everything else between the units is refused: `d * t`,
`v + d`, `1.0 / t`. A derived unit can be made from another (`type Accel_T
is Velocity_T / Duration_T`) and has the kind of its operands: `float`, or
`int` for a product. Nim gets a small proc per relation, so it costs nothing
at run time.

### A unit narrowed to a range

A distinct type can be narrowed to part of its values, in the manner of an Ada subtype, with `type N is P range lo .. hi` -- `P` any distinct float or int, the bounds negative if need be. The result is a type of its own, with a relation to its parent: it goes up, comes down only by an explicit conversion that checks the range, and does not stand for a sibling:

```python
type Degrees_T is distinct float
type Latitude_T is Degrees_T range -90 .. 90
type Longitude_T is Degrees_T range -180 .. 180

let lat: Latitude_T = Latitude_T(45.5)
let wide: Degrees_T = lat                  # up to the parent: no cast
let sum: Degrees_T = lat + Degrees_T(1.0)  # arithmetic is the parent's
let back: Latitude_T = Latitude_T(sum)     # down: checked
let lat2: Latitude_T = 12.5                # a literal takes the declared type, checked
```

- A narrowed type goes up to its parent, and to the parent's parents, wherever the parent is wanted -- a `Degrees_T` parameter takes a `Latitude_T`, and `Radians_T(lat)` of a scaled unit converts it. `Degrees_T(lat)` is allowed too, if you like to say so.
- It comes down by `Latitude_T(d)`, from a `Degrees_T` or a plain number: out of range, that raises `AssertionError` (Nim: `AssertionDefect`, which `except AssertionError` catches). It is never silent, and never skipped in a release build.
- It does not stand for a sibling: `let l: Latitude_T = lon` and `Latitude_T(lon)` are refused, and so is a `Longitude_T` passed where a `Latitude_T` is declared -- the point of two types, that `GeoPoint(lon, lat)` is an error.
- Arithmetic leaves the range, so it is the parent's: `lat + lat` is a `Degrees_T`, to be converted back to be stored in a `Latitude_T`. Comparisons, `min`, `max`, `print` and f-string formats work on the narrowed type as they do on its parent.
- Python: `class Latitude_T(Degrees_T)`, whose constructor checks the range. Nim: a `distinct float` with a converter up and a checking `to_Latitude_T` that `Latitude_T(x)` is emitted as.

It is a unit with a range, where `distinct float range lo .. hi` (below) is a unit of its own that has no parent. Use the narrowing when there is a parent to go up to.

<!-- tested by EXAMPLES/test_narrowed_type.ady -->

### A type that wraps: `mod`

Where a range type refuses a value outside it, a mod type wraps it back in. `type Slot_T is mod 8` is a whole number that is always 0 .. 7, and `type Bearing_T is Degrees_T mod 360` is a `Degrees_T` that is always 0 .. 360 -- a compass bearing, an angle, a clock hand, a ring-buffer index. Making one, and `+`, `-` and `*` on it, wrap:

```python
type Slot_T is mod 8
type Degrees_T is distinct float
type Bearing_T is Degrees_T mod 360

var s: Slot_T = Slot_T(6)
s = s + Slot_T(1)                          # 7
s = s + Slot_T(1)                          # 8 wraps to 0
print(int(Slot_T(-1)))                     # 7

let b: Bearing_T = Bearing_T(-10.0)        # 350.0
let turned: Bearing_T = b + Degrees_T(30.0)   # 380 wraps to 20.0
let wide: Degrees_T = b                    # up to the parent: no cast
```

- The value wraps with the sign of the modulus, as Python's `%` does, on both backends: `Slot_T(-1)` is 7, not -1.
- `Slot_T` has no parent: it is a type of its own, and a plain `int` is given to it by `Slot_T(n)`. `Bearing_T` has `Degrees_T`: a `Bearing_T` goes up to it without a cast, `bearing + degrees` is a `Bearing_T`, and a `Degrees_T` comes down only by `Bearing_T(d)`, which wraps it. A literal takes the declared type, wrapped: `let c: Bearing_T = 400.0` is 40.0.
- `*` by a plain number gives the same type, wrapped; `/` by a plain number does too, and `Bearing_T / Bearing_T` is a plain ratio. Comparisons compare the wrapped values.
- It is refused beside a sibling, as a narrowed type is, and `bearing + 1.0` mixes a unit with a plain number as it does for any unit.
- A mod type wraps and never raises. Use `range` when a value outside should be an error, and `mod` when it should come round.
- Python: `class Bearing_T(Degrees_T)`, whose `__new__` and operators wrap. Nim: a `distinct float` with a `to_Bearing_T` that wraps with `floorMod`, wrapping operators, and a converter up.

<!-- tested by EXAMPLES/test_mod_type.ady -->

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
because `Speed_T * Speed_T` has no unit unless one is declared. It is all in
`EXAMPLES/test_units.ady`.

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
`EXAMPLES/test_money.ady` is a whole order: lines, tax, a discount, a
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

---

## 3. Variable Declarations

The keywords `var`, `let`, and `const` make intent explicit and map cleanly to
Nim:

```python
var   counter: int   = 0        # mutable variable
let   name:    str   = "Alice"  # immutable binding
const MAX:     int   = 1_000    # compile-time constant
```

Declarations without an initial value are valid (Nim zero-initialises):

```python
var result: []int               # empty seq[int]
var table:  {str}int            # empty Table[string, int]
```

### Tuple unpacking

```python
let (x, y) = point              # explicit let destructuring
var (a, b) = (1, 2)             # explicit var destructuring
a, b = some_func()              # implicit let tuple unpack
```

---

## 4. Enums

Enums use Ada/Nim-style declaration with `type … is enum`:

```python
type Door_T   is enum Door1, Door2, Door3
type Priority is enum LOW, MED, HIGH
type Digit_T  is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are accepted as the assignment keyword.

**Python output:** `class Door_T(Enum): Door1 = auto()` …  
**Nim output:** `type Door_T = enum Door1, Door2, Door3`

A member stringifies as its bare name on both backends — `str(d)`, `print
d`, `f"{d}"` and `d'Image` all give `Door1`, which is what Nim's `$` gives.
A *container* of enum values is the exception: Python formats elements with
`repr`, so printing a `[]Door_T` still shows `[<Door_T.Door1: 0>, …]`
against Nim's `@[Door1, …]`. That one is in `TODO.md`.

### Members with values

A member can be given its value, for the numbers a program has to match -- key codes,
exit codes, protocol numbers:

```python
type Key_T   is enum DOWN = 258, UP = 259, LEFT = 260, RIGHT = 261
type Level_T is enum:
    LOW  = 1
    MID  = 2
    HIGH = 3
```

Either every member has a value or none does; a mix is refused, so a reader never has to
work out what an unwritten one is. The values give the order and must ascend: `ord(UP)` is
`259`, `DOWN < UP`, and a `case` or a set follows them. `Key_T(259)` is `UP`, the integer read
as the value. Values that follow one another (`1, 2, 3`) leave the enum as good as any
other. Values that skip a number (`0, 5, 6`) still order, compare and `case`, but cannot
index an array (`[E]T`), be iterated (`for x in E`) or be stepped with `'Next` and `'Prev`,
which Nim refuses for them too; Adascript says so on both backends.

Enums integrate tightly with arrays, case statements, and tick attributes —
see those sections below.

---

## 5. Named Tuples

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

---

## 6. Records and Variant Records

### Records (dataclasses)

```python
type Person is record:
    name: str
    age:  int
```

**Python output:** `@dataclass class Person: …`  
**Nim output:** `type Person = object`

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
  a `@virtual class` is a reference on Nim too (see §13).

Chapter 13 §13.2 of the book has the full account.

### Discriminated (variant) records

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

**Python output** — flattened dataclass with `None` defaults for the unused fields.

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

## 7. Collections

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
`EXAMPLES/test_set_operators.ady`.

### Enum-indexed arrays `[E]T`

When all keys are enum members, use `[E]T` — this maps to a fixed-size array
in Nim (no heap allocation, O(1) lookup). An enum whose values skip a number
(`enum A = 0, B = 5`, §4) cannot be a key, and is refused:

```python
type Priority is enum LOW, MED, HIGH

var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
print(costs[HIGH])   # 10
```

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

### Insertion-ordered maps `[K]V`

When the key is not a finite ordinal — a string, an int, a class — `[K]V`
is still an ordered mapping, and the order is the order the keys arrived
in. It is an `OrderedTable` on Nim and a dict on Python, so the two backends
agree on the order, which a `{K}V` does not promise:

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

Nested enum arrays work too (2-D lookup table):

```python
var transition: [Hidden_State_T][Hidden_State_T]float = [
    HEALTHY: [HEALTHY: 0.7, FEVER: 0.3],
    FEVER:   [HEALTHY: 0.4, FEVER: 0.6],
]
```

**Python output:** nested dict  
**Nim output:** `array[Hidden_State_T, array[Hidden_State_T, float]]`

### Open arrays `[*]T`

`[*]T` is Nim's `openArray[T]`: a read-only view that accepts both `[]T`
(seq) and `[N]T` (fixed-size array) at the call site without copying. Use it
for function parameters that only iterate or index into the argument:

```python
def sum_values(xs: [*]int) -> int:
    var total: int = 0
    for x in xs:
        total = total + x
    return total

var a: []int  = [1, 2, 3]
var b: [3]int = [1, 2, 3]
print(sum_values(a))   # seq argument — ok
print(sum_values(b))   # fixed array argument — ok
```

**Nim output:**

```nim
proc sum_values(xs: openArray[int]): int =
    var total: int = 0
    for x in xs:
        total = total + x
    return total
```

`[*]T` is valid **only in parameter and return annotations** — not in
variable declarations. Callers never need to do anything special: Nim passes
both seq and array to an `openArray` parameter automatically.

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

### Unions `A | B`

A union holds one of its members; `case` gives a branch per member, and the
name is that member inside it:

```python
def compute(n: int) -> int | float:
    if n % 2 == 0:
        return n // 2
    return n / 2

let x: int | float = compute(5)
case x:
    when int:
        print f"int {x + 1}"
    when float:
        print f"float {x * 2.0}"
```

`x is int` asks the same in an `if`. `?T` is the union `T | None`, and a
union with a member marked `!` -- a failure -- is a value-or-failure:

### Value or failure `T | !F`

When the caller needs to know *why* there is no value, return a failure
instead of `None`. A failure is an ordinary record, marked `!` in the
return type; the function returns either its value or one of those, and
`is` tells them apart:

```python
type ErrKind_T is enum BAD_NUMBER, TOO_BIG

type Failure_T is record:
    kind:   ErrKind_T    # which failure
    detail: str          # what it needs to say so

def read_number(s: str) -> int | !Failure_T:
    if len(s) == 0:
        return Failure_T(kind=BAD_NUMBER, detail="empty")
    return int(s)

let n: int | !Failure_T = read_number("42")
if n is Failure_T:
    print n.detail           # n is the failure here
else:
    print n + 1              # and the int here
```

`do:` chains such steps and passes the first failure on; `case n:` with
`when Failure_T:` / `when int:` gives a branch per side. Book chapter 10.12
has the whole of it.

**Prefer a failure to an exception.** Where an operation can go wrong in a
way you expect -- a missing file, a command that fails, a path not below its
base, a number that is not one -- it returns `T | !Failure_T`; it does not
raise, and you do not wrap the call in `try/except`. The intent is then
explicit, in the signature and again at the call. You either handle the
failure right there, next to the call, or pass it up to the caller:

```python
let res: int | !Failure_T = read_number(text)
if res is Failure_T:
    die(res.detail)              # handled here, where the call is
print res + 1                    # res is the int from here on

def total(a: str, b: str) -> int | !Failure_T:
    do:
        x <- read_number(a)      # a failure ends total and goes to its
        y <- read_number(b)      # caller as it is
    return x + y
```

Passing a failure up is as easy as letting an exception through, and it is
written down: `total` says `| !Failure_T` in its signature, and each `do:`
step is where it happens, so the caller can see the call can fail and
decides where it is dealt with. An exception goes up through functions whose
signatures say nothing about it, and is caught (or not) at some distance; a
failure value cannot be dropped unseen -- a bare call that ignores one is
refused. The built-in operations follow this: `shell:` gives a `str |
!ShellFailure_T`, and `Path.mkdir`, `.relative_to`, `.read_text`,
`.read_lines` and `.write_text` give a `... | !PathFailure_T`, and reading a
number or an enum member from text is `parse_float(s)`, `parse_int(s)` and
`parse_enum(E, s)`, a `float | !ParseFailure_T`, an `int | !ParseFailure_T`
and an `E | !ParseFailure_T` (`s` a name, or an integer read as the member's value); `input(prompt)` and `stdin.readLine()` give a line or, when the input
has ended, an `InputFailure_T` (`str | !InputFailure_T`). What still
raises -- `readFile`, `writeFile`, `for line in p.lines:`,
`float(s)`, `int(s)` -- is the
older spelling: use the failure-typed one where there is one, and keep
exceptions for what nobody expected.

Do not forget the `!`: without it, nothing says Failure_T is a failure.
Marked in another union, the type is refused unmarked, so that slip does
not build; marked nowhere, `int | Failure_T` is an ordinary union of two
values, whose failure can be dropped unnoticed -- and `None | Failure_T`
is `?Failure_T`, an optional. Book 10.12, *Forgetting the `!`*.

---

## 8. Subranges

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

### Float subranges

For floating-point ranges use `float range lo .. hi` (the bounds may be negative). It is a float with a stated range, and still mixes with floats. Write `distinct float range lo .. hi` when it should also be a unit of its own: it does not mix with a float, or with another range. When the range narrows a unit that already exists -- a latitude is a `Degrees_T` in `-90 .. 90` -- say so with `type Latitude_T is Degrees_T range -90 .. 90` (see *A unit narrowed to a range*): it goes up to its parent without a cast.

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

---

## 9. Tick Attributes

Ada-style `'` attributes provide metadata about enums and ranges without
any runtime overhead. Where a name is followed immediately by `'` and an
identifier, the tokeniser emits the apostrophe as a token of its own
(`TICK_TOKEN`), so Python's lexer never takes it for the start of a string;
the grammar matches the pair as `tick_trailer = TICK + IDENTIFIER`.

| Expression         | Meaning                            |
|--------------------|------------------------------------|
| `E'First`          | First member of enum `E`           |
| `E'Last`           | Last member of enum `E`            |
| `E'Range`          | Ordinal set of all members of `E`  |
| `expr'Next`        | Successor of `expr`                |
| `expr'Prev`        | Predecessor of `expr`              |
| `expr'choose`      | Random element from expr or range  |
| `expr'Image`       | String representation of `expr`    |

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

### Random selection with `'choose`

`'choose` picks a uniformly random element from an enum, set, or range:

```python
let carLocation:         Door_T = Door_T'choose       # random enum member
let candidateFirstChoice: Door_T = Door_T'choose

# 'choose also works on a range expression:
# from floyd.ady — Floyd's algorithm for distinct random sampling
t = (1..i)'choose    # random int in 1..i
```

### Enum successor/predecessor

`'Next` and `'Prev` step through enum members (not for an enum whose values skip a number, §4):

```python
type Stage_T is enum STAGE1, STAGE2, STAGE3, END

current_stage: Stage_T = STAGE1
next_stage: Stage_T = current_stage'Next    # STAGE2
```

---

## 10. Range Expressions

The `..` (inclusive) and `..<` (exclusive) operators produce integer or enum
ranges. They are first-class values, usable in `for` loops, membership tests,
and with `'choose`.

```python
for i in 0 .. 10:      # 0, 1, …, 10  (inclusive)
    pass

for i in 0 ..< 10:     # 0, 1, …, 9   (exclusive upper bound)
    pass

if x in 1 .. 100:      # range membership test
    print("in range")

# From primes.ady:
for k in 2 .. int(n ** 0.5):
    if n % k == 0:
        return False
```

**Python output:** `range(lo, hi+1)` for `..`; `range(lo, hi)` for `..<`  
**Nim output:** native `lo .. hi` / `lo ..< hi`

---

## 11. Control Flow

### if / elif / else

Standard Python — no changes.

```python
if x > 0:
    print("positive")
elif x == 0:
    print("zero")
else:
    print("negative")
```

Each branch also accepts a single statement on the same line as the colon
(Python-style inline suite). Useful for short, terminal branches:

```python
if x < 5: print("x<5")
elif x < 10: print("5<=x<10")
else: print("x>=10")
```

### Statement modifier: `return` / `break` / `continue` / `die` / `quit` if cond

Those three statements, and a call to `die` or `quit`, can carry their own
`if`, and run only when the condition holds. The guard clause reads
exit-first:

```python
def is_term_continuation(code_s: str) -> bool:
    return False if code_s == ""
    return True if code_s.startswith("(")
    return False if not starts_with_operator(code_s)
    return lead_ident(code_s).lower() != "xor"
```

Each of those lines emits the one-line `if` on both backends
(`if code_s == "": return False`). A bare `return` takes one too:

```python
return if quiet
continue if line.startswith("#")
break if depth < 0
```

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

Nothing else may: an assignment, any other call, a `print` or a `raise`
under an `if` modifier is a parse error. `x = 1 if c` opens exactly like the
conditional expression `x = 1 if c else 2` and would only stop looking like
one at the end of the line.

The conditional expression itself is untouched: a modifier's `if` has no
`else`, so `v: int = 1 if flag else 2` is still a ternary.

### for loops

```python
for item in collection:
    pass

for i in 0 ..< 10:
    pass

for key, val in mapping.items():
    pass
```

### while loops

```python
while queue:
    item = queue.pop()
```

`while` also supports the inline form:

```python
var n: int = 3
while n > 0: n -= 1
```

### case / when

Pattern matching is written `case x:` with `when pat:` branches, and
`when others:` for everything not named. It is the only spelling.

**Prefer `case` to an `if` / `elif` / `else` chain** whenever the branches
test one subject against different values. The subject is named once, at
the top, instead of in every condition; the branches line up as a table of
the alternatives; and when the subject is an enum and the branches are
constants, the Nim build proves the dispatch is total — add a member to the
enum and every `case` over it that misses the new one stops compiling,
where an `if` chain would quietly fall into its `else`:

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

Keep `if` for conditions that test different things — `if cache != "" and
-d dir:` is not a choice among the values of anything.

The Python output is a `match/case` statement. The Nim output differs only
when patterns require desugaring (structural, guards, tuple subjects). For a
full reference see
[The Adascript Book, Chapter 5](BOOK/05-pattern-matching.md).

**Literal and range patterns:**

```python
case code:
    when 200:
        print("OK")
    when 400 | 401 | 403:
        print("client error")
    when 500 .. 599:
        print("server error")
    when others:
        print("unknown")
```

`when` clauses also support the inline form when the body is a single
statement — handy for compact dispatch tables:

```python
# from EXAMPLES/argparse.ady
case arg:
    when "--help" | "-h": usage(0)
    when "--verbose" | "-v":
        res.verbose = True
        state = expecting_option_or_argument
    when "-n" | "-o" | "--count" | "--output":
        current_option = arg
        state = processing_option
    when others:
        print "Unknown option:", arg
        quit(1)
```

Inline and indented branches can be mixed freely — only the simple
single-statement branches need to be inlined.

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
# from test_shortest_path.ady, example 6 (Equipment Replacement)
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

---

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

---

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

## 12. Functions

Standard Python `def` with Adascript type annotations:

```python
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
```

### Implicit return

When a function has a return-type annotation and its last statement is a bare
expression (not an explicit `return`), Adascript promotes it to a return:

```python
def clamp(x: int, lo: int, hi: int) -> int:
    max(lo, min(x, hi))

def is_even(n: int) -> bool:
    n % 2 == 0
```

`-> None` is excluded: void functions' last expression stays as a statement.

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

- A constructor overloads the same way: `Vector(length, angle)` and `Vector(x, y)` are two `__init__`s, told apart by the types of the arguments (`Degrees_T` against `Meters_T`).
- A literal is no argument of any type, so one given to an overloaded name is refused on Nim -- `Vector(3.0, 4.0)` could be either -- and written with its type: `Vector(Meters_T(3.0), Meters_T(4.0))`.
- Two defs with the same parameter types are one name defined twice, and refused.
- Nim overloads natively. On Python the defs are renamed and a def of the name dispatches on the types of the arguments, the exact type first, then what each is an instance of; a type it cannot test (a union, a generic) matches anything. Arithmetic on a distinct value is a plain number in Python, so as a last resort a plain number matches a distinct type of numbers; write `Meters_T(a + b)` where overloads differ only in such types. Call overloads by position.
- Decorated defs, and defs with `*args` or `**kwargs`, are left as they are.

<!-- tested by EXAMPLES/test_overload_types.ady -->

### Nested functions / closures

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

### Generator functions

`yield` is fully supported and transpiles to Python generators and Nim
iterators:

```python
def shortest_path(self, start_state: S, end_state: S, allsolutions: bool = True):
    fringe: PriorityQueue[...] = PriorityQueue(...)
    while fringe:
        let (_, cost, path, current_state) = fringe.pop()
        if current_state == end_state:
            yield self.real_cost(cost), path
            if not allsolutions:
                break
        for new_decision, step_cost in self.get_next_decisions(current_state):
            fringe.push(...)
```

---

## 13. Classes and Inheritance

Standard Python class syntax with Adascript annotations. Use `var`, `let`,
or `const` inside the class body to declare fields (visually distinct from
method-local assignments).

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

### Inline field defaults

Field declarations can carry default values. The transpiler injects them into
the generated constructor, so `__init__` only needs to set fields whose values
differ per instance:

```python
class AwkProcessor(AwkBase):
    var NR        : int = 0
    var NF        : int = 0
    var total_len : int = 0
    var counts    : [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]

    def __init__(self, fs: str = " ", ofs: str = " "):
        self.FS  = fs   # only the caller-supplied fields need explicit init
        self.OFS = ofs
```

### Mutable self in non-virtual classes

For plain (non-`@virtual`) classes, the transpiler automatically detects
whether a method mutates `self` — via field assignment (`+=`, `=`), `.add()`,
indexed assignment, or a call to a method that does, directly or through
another — and emits
`self: var ClassName` in the generated Nim. No decorator or annotation needed:

```python
class Counter:
    var count: int = 0

    def increment(self):
        self.count += 1   # → proc increment(self: var Counter) in Nim
```

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

When a subclass has no `__init__`, the transpiler automatically generates a
forwarding constructor that mirrors the parent's parameters and delegates to
the parent's initialiser:

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
    # No __init__ needed — AwkProcessor(fs, ofs) is generated automatically,
    # calling initAwkBase(result, fs, ofs) and initialising counts.
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

When used with `import` (see §17), the base class's `.nim` is compiled as a
library and subclasses in the importing file dispatch dynamically at runtime.

`@virtual` also changes what assignment does on Nim: a `ref object` is shared
by every name that holds it, as every object is on Python. A plain class is
copied on assignment on Nim and shared on Python (see §6, "Copied on Nim,
shared on Python"); a `@virtual` one is shared on both.

---

## 14. Generic Classes

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

---

## 15. Shell Integration

Shell commands are first-class expressions in Adascript. The `shell` and
`shellLines` keywords integrate subprocess calls directly.

### Basic capture

```python
let result = shell: git status
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

### Lines capture

`shellLines` splits stdout into `[]str`, one element per line.  The
assignment target supports type annotations, bare names, or `let`/`var`/`const`:

```python
def getTestStatusLines() -> []str:
    shellLines: show_tests_status -raw

for line in getTestStatusLines():
    print(line)

let entries: []str = shellLines: ls -1a /tmp
output = shellLines: find . -name "*.ady"
```

### Variable and expression interpolation

Use `{name}` to embed an Adascript variable in the command body.  Function
calls and other complex expressions also work inside `{}` — the transpiler
hoists them to temp variables automatically:

```python
let branch: str = "main"
let result = shell: git log --oneline {branch}

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

### Options

```python
let result = shell(cwd = "/tmp"):          pwd
let result = shell(timeout = 5000):        slow-command
let result = shell(cwd = src, timeout = 3000): make all
```

### A command's output, or its failure

Typed `T | !ShellFailure_T`, a command holds its output, or the built-in
failure record `ShellFailure_T` (`command`, `code`, `stderr`):

```python
let oops: str | !ShellFailure_T = shell: echo oops >&2; exit 3
if oops is ShellFailure_T:
    print f"exit {oops.code}, stderr {oops.stderr.strip()}"
```

In a `do:` block, `out <- shell: cmd` is a step that stops the chain when
the command fails — see *Value or failure `T | !F`* above.

### Discarding output

```python
shell: rm -rf /tmp/build
shell: git add {filename}
```

### Block form — multi-line and interactive (expect/send)

`shell:` followed by an indented block accepts multiple lines. There are two
flavors of block:

**Pure block** — a sequence of commands joined into a single shell pipeline
with `&&`:

```python
shell:
    echo hello
    echo world
```

This runs `echo hello && echo world`.

`join` picks a different separator — `";"` runs every line regardless,
`"|"` makes one pipeline. Mind what that does to error reporting: with
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

**Interactive block** — when the block contains `send(...)` or `expect(...)`
calls, the first line is treated as the command to spawn under a PTY, and
subsequent `send`/`expect` calls drive it. The transpiler emits calls to the
bundled `expect` standard library (PTY backed by `forkpty + select + re`,
linked against `-lutil`):

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
use the `expect` library directly via `nimport expect`:

```python
# from EXAMPLES/test_expect.ady
nimport expect

var s: Spawn = spawn("bc")
s.expect("\\$|>|bc")     # wait for prompt
s.send("2 + 2\n")
s.expect("4")
print("result = " & s.match)
s.send("quit\n")
s.close()
```

### Translation summary

| Adascript                    | Python 3                                   | Nim                              |
|------------------------------|--------------------------------------------|----------------------------------|
| `let r = shell: cmd`         | `subprocess.run(…, capture_output=True)`   | `execCmdEx("cmd")`               |
| `let ls = shellLines: cmd`   | `…stdout.splitlines()`                     | `execCmdEx(…)[0].splitLines()`   |
| `let ls: []str = shellLines: cmd` | same (type annotation stripped)        | same (Nim infers type)           |
| `ls = shellLines: cmd`       | same (bare assignment)                     | same                             |
| `shell: cmd`                 | `subprocess.run("cmd", shell=True)`        | `discard execCmd("cmd")`         |
| `{var}` in body              | f-string interpolation                     | `fmt"""…"""` with `strformat`    |
| `{f(x)}` in body             | f-string interpolation                     | hoisted to `let tmp = f(x)`      |

Required imports (`subprocess`, `osproc`, `strformat`) are inserted
automatically.

---

## 16. Bash Variables and File Tests

### Command-line arguments

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

All-caps identifiers preceded by `$` read environment variables:

```python
home   = $HOME
editor = $EDITOR
outdir = $HOME + "/output"
```

### File-test operators

```python
if not -f dict_file:
    print(f"Error: {dict_file} not found")
    quit(1)

if -d output_dir:
    shell: ls {output_dir}
elif not -e output_dir:
    shell: mkdir -p {output_dir}

if src -nt dest:     # src is newer than dest
    shell: cp {src} {dest}
```

| Operator    | Meaning                        |
|-------------|-------------------------------|
| `-e path`   | path exists                   |
| `-f path`   | path is a regular file        |
| `-d path`   | path is a directory           |
| `-L path`   | path is a symlink             |
| `-r path`   | path is readable              |
| `-w path`   | path is writable              |
| `-x path`   | path is executable            |
| `-s path`   | path exists and is non-empty  |
| `a -nt b`   | a is newer than b             |
| `a -ot b`   | a is older than b             |

### Messages and exit: `die`, `warn` and `PROG`

Almost every script needs the same three things: its own name, a way to
report a problem and carry on, and a way to report one and stop. They are
built in, and need no import:

```python
if not -f dict_file:
    die(f"{dict_file} not found")           # "<prog>: ... not found" on stderr, exit 1

if $# > 2:
    warn("extra arguments ignored")        # "<prog>: extra arguments ignored" on stderr

if mode not in ["fast", "full"]:
    die(f"unknown mode {mode}", code = 2)  # the same, with exit status 2

print(f"usage: {PROG} <dict_file> <phone_file>")
```

- **`PROG`** is the name the program was invoked as, without its directory,
  like `${0##*/}` in the shell. Both backends give the same answer: a
  leading `.` is dropped (ady2nim runs a cached `.name` binary), and so is a
  trailing `_gen.py` or `.py` (ady2py). A program installed as a symlink is
  known by the link's name.
- **`warn(msg)`** writes `PROG + ": " + msg` to stderr.
- **`die(msg, code = 1)`** does the same, then exits with `code`. It never
  returns, so a function may end in `die(...)`:

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
any more. A program that means something else by these names can still
define them: its own top-level `def die`, `def warn` or `let PROG` takes
precedence over the built-in. `TOOLS/C500/c500.ady`, for example, has a `die`
that reports a line number on stdout. The helpers are only emitted into
programs that use them.

---

## 17. Nim-Only Imports and Adascript Modules

`nimport` marks imports of Nim modules, which appear **only** in Nim output and are
stripped from Python output. Use it for Nim standard-library modules. Dependencies
between Adascript files are `import`s:

```python
nimport strutils, sequtils, algorithm
nimport stdlib                      # PriorityQueue, FifoQueue, ANY shims
from awk import AwkBase            # the bundled record-processor stdlib
from shortest_path import Minimizer, Maximizer   # another .ady file compiled as a library
```

When `import`-ing another `.ady` file, `ady2nim` automatically transpiles
that dependency (if not already cached and up to date) and places both `.nim`
files in the same cache directory, wiring up `--path` for the Nim compiler.

### Bundled Adascript standard libraries

`.ady` files shipped in `TO_NIM/` are automatically installed into the build
cache at compile time, so they can be used via `import` from **any directory**
without a local copy next to your source file:

| Import         | Provides                                              |
|----------------|-------------------------------------------------------|
| `nimport stdlib` | `PriorityQueue`, `FifoQueue`, `LifoQueue`, `ANY`    |
| `import awk`  | `AwkBase` — subclass and override `process_record()`, `begin()`, `finish()` |
| `import strscan` | character classification (`is_digit_ch`, `is_space_ch`, …) and the small scanners a hand-written lexer needs (`skip_space`, `skip_quoted`, `lead_ident`, `strip_line_comment`) |
| `import ansi` | terminal colours and effects as values a pipe applies: `"x" \| bold \| fg_white \| bg_red`; styles add, `bold + fg_red`, into one escape |
| `nimport illwill` | a curses-like terminal library in pure Nim, one file (`EXAMPLES/VI/vi_curses.ady`) |

Example — a custom awk processor in any directory:

```python
#!/usr/bin/env ady2nim
from awk import AwkBase

class WordCounter(AwkBase):
    var word_count: int = 0

    def process_record(self):
        self.word_count += self.NF

    def finish(self):
        print f"total words: {self.word_count}"

var wc: WordCounter = WordCounter()
wc.run()
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

**test_shortest_path.ady** (the test file):

```python
#!/usr/bin/env ady2nim
#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc

nimport stdlib
from shortest_path import Optimizer   # triggers auto-transpilation of shortest_path.ady

class MyOptimizer(Optimizer[str, str, float]):
    ...
```

---

## 18. Real Examples

The `EXAMPLES/` directory contains complete programs. Here are annotated
highlights from each.

---

### primes.ady — Range operators and timing

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

---

### graph.ady — Type aliases and recursive functions

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

---

### monty_hall.ady — Enums, sets, tick attributes, case/when

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

---

### dijkstra.ady — Priority queue, enum-keyed dicts, from-import

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

---

### phonecode.ady — Full application structure

A complete solution to Prechelt's phone-code benchmark, demonstrating:

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

---

### shortest_path.ady — Generic framework

A 160-line generic optimiser that becomes 10+ complete algorithm examples
in `test_shortest_path.ady`. The key architectural pattern is **generic
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
# test_shortest_path.ady — consumer
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

---

## 19. Regex Literals

Adascript has first-class regex literal syntax: `/pattern/flags`. No `import re`
needed — regex support is injected automatically into the generated code for both
backends (Nim uses `nre`/`std/re`; Python uses the standard `re` module).

### 19.1 Match test (`==` / `!=`)

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

### 19.2 Positional capture groups

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

### 19.3 Named capture groups

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

### 19.4 Find all (`/g` flag)

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

### 19.5 Substitution (`s/pat/repl/flags`)

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

### 19.6 Regex in `case/when`

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

### 19.7 Supported flags

| Flag | Meaning |
|------|---------|
| `i`  | Case-insensitive |
| `g`  | Return all matches as `[]str` (only on `==` RHS) |
| `m`  | Multiline — `^` / `$` match per-line boundaries |
| `s`  | Dotall — `.` also matches `\n` |

### 19.8 Translation reference

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

---

## 20. Memory Ownership

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

### 20.1 `own` declaration

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

### 20.2 `lent` and `own` parameter modes

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

**`lent T`** — the callee promises not to store or transfer the value; it
simply reads it.  Nim passes by value (ARC may optimise to a pointer); Python
passes by reference as usual.

**`own T` / `sink T`** — the callee takes responsibility for the value.  In
Nim this enables the "sink" optimisation: the caller's copy is moved rather
than copied.  In Python the annotation is stripped; the GC handles cleanup.

```python
def process(buf: lent Buffer) -> int:
    buf.size                        # read only; caller's buf is still valid

def store(buf: own Buffer):
    self.cache = buf                # we keep it; caller's copy is moved
```

### 20.3 `move()` — explicit ownership transfer

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

### 20.4 `drop()` — explicit early release

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

### 20.5 `with own` — scoped RAII block

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

### 20.6 Full example

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

### 20.7 Translation reference

| Adascript | Nim (ARC) | Python (GC) |
|---|---|---|
| `own x: T = expr` | `var x: T = expr` | `x: T = expr` |
| `param: lent T` | `param: T` | `param: T` |
| `param: own T` | `param: sink T` | `param: T` |
| `-> own T` (return) | `-> T` | `-> T` |
| `move(x)` | `move(x)` | `x` (alias; GC ref) |
| `drop(x)` | `(block: =destroy(x); =wasMoved(x))` | `del x` |
| `with own x = e:` | `block: var x = e; body` | `x=e; try: body; finally: del x` |

### 20.8 Patterns in the example programs

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

### 20.9 What the 20% leaves out

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

## 21. Programming in the Large

Up to here every program has been one file. Past a few hundred lines a
program wants modules, and `import` is how they find each other. ady2nim builds
a whole dependency graph and links it; ady2py merges each module into the one
file it writes, where the module is first imported.

### 21.1 A module is a file

No manifest, no package file, nothing to register. `EXAMPLES/PROJECT/` is a
complete example:

```
EXAMPLES/PROJECT/
    dispatch.ady          # the program
    lib/geometry.ady      # leaf module: Point_T, distance(), bearing()
    lib/fleet.ady         # domain model — import geometry
    lib/report.ady        # formatting   — import geometry
    test_geometry.ady     # a second entry point: the unit test
```

```bash
ady2nim c -r EXAMPLES/PROJECT/dispatch.ady
```

```python
# dispatch.ady
from lib/geometry import Point_T
from lib/fleet import Depot, Energy_T, Vehicle_T
from lib/report import format_leg

let base: Point_T = (x: 0.0, y: 0.0)

var d: Depot = Depot("Central", base)        # constructor crosses the file boundary
d.add("truck-1", (x: 12.0, y: 5.0), 4.0)

print format_leg("truck-1", base, d.vehicles[0].position)
```

Every top-level declaration of an imported file is exported automatically —
`def distance(...)` becomes `proc distance*(...)` in the generated Nim. Names
are reached as in Python: `import geometry` gives `geometry.distance(a, b)`,
and `from geometry import distance` gives `distance(a, b)`.

### 21.2 How a name is found

For each `import`, ady2nim looks for the `.ady` file in three places, in
order: the importing file's own directory, that directory's parent, then the
build cache (where the bundled `TO_NIM/STDLIB/*.ady` libraries are
installed). The first hit wins; if nothing matches, the name is passed to Nim
untouched, which is what makes `nimport strutils` work.

So a sibling is imported by its bare name (`import geometry` inside
`lib/fleet.ady`), and the program addresses modules by their path from the
project root (`import lib/geometry`). There is no `..` — the parent rule is
what lets an entry point in `bin/` write `import lib/util`.

### 21.3 Layouts

| Layout | When |
|--------|------|
| Flat — every module in one directory | up to a dozen modules (`EXAMPLES/CFMU/`) |
| Program at the root, modules in `lib/` | modules with their own relationships (`EXAMPLES/PROJECT/`) |
| `bin/` programs over a shared `lib/` | several programs, one library |

### 21.4 The build

`ady2nim c -r dispatch.ady` walks the `import` graph breadth-first,
pre-parses each dependency (collecting class names, constructor signatures,
return types, and the field order of records and named tuples), transpiles
each into a per-program cache directory under `~/.cache/adascript/`, and then
runs one `nim c` over the graph with `--path` pointing at that cache. Only
the binary symlink is written next to your sources. Editing any module at any
depth triggers a rebuild; `ady2nim -t` transpiles the graph and stops.

### 21.5 Rules

- A module's top-level statements run at import time, before the program's
  first line. Modules declare; programs act.
- Keep the graph acyclic — give the project a leaf module for shared types.
  Nim tolerates some mutual imports, but a cycle involving type declarations
  does not resolve.
- Basenames must be unique project-wide, and must not be Nim keywords
  (`mod.ady` fails with `invalid module name`).
- Exported names share one namespace; Nim overloading absorbs most clashes.
- A module's test is another entry point that imports it and asserts
  (`EXAMPLES/PROJECT/test_geometry.ady`).
- ady2py replaces an `import` of an `.ady` module by the module's text (once),
  so a program split across modules runs on both backends. On Python it is one
  namespace -- two modules defining the same name clash, and `geometry.distance`
  is refused where the file has a `distance` of its own; the libraries bundled
  with ady2nim stay Nim-only.

Chapter 14 of the book (`DOCS/BOOK/14-programming-in-the-large.md`) works
through the same ground in more detail.

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
