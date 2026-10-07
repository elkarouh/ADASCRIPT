# Adascript Language Reference for LLMs

## What is Adascript?

Adascript (`.ady` files) is a statically-typed language built on Python 3. Most Python 3 code is valid Adascript as it stands; the exception is `import`: write `import X` for an Adascript (`.ady`) module, `nimport X` for a Nim module and `pyimport X` for a Python package — a plain `import X` of anything else is refused on both backends. It transpiles to both **Python 3** and **Nim** — you write one source file and target either ecosystem.

```
source.ady  ──▶  python3 TO_PYTHON/ady2py.py source.ady  ──▶  Python 3
            ──▶  python3 TO_NIM/ady2nim.py   source.ady  ──▶  Nim
```

Key design goals: Ada-style type safety, Python ergonomics, Nim performance.

---

## Running Adascript

```bash
# Transpile to Python 3 and run
python3 TO_PYTHON/ady2py.py -c source.ady

# Transpile to Nim and compile+run (default)
python3 TO_NIM/ady2nim.py source.ady

# Transpile only (write .nim file)
python3 TO_NIM/ady2nim.py -t source.ady

# Optimised Nim build
python3 TO_NIM/ady2nim.py c -d:release source.ady
```

Shebang + per-file Nim options (first two lines only):
```adascript
#!/usr/bin/env ady2nim
#ady2nim-args c -d:release
```

Build artifacts go into `~/.cache/adascript/cache-<HASH>/` — source directories stay clean. Builds are incremental.

---

## Type Annotations (Left-to-Right)

Adascript uses prefix notation for containers. `[]int` = "list of int".

**The scheme:** two independent questions pick the form.

- **Ordered?** = bracket shape. `[…]` ordered, `{…}` unordered.
- **Keyed?** = whether a type sits inside. Empty (`[]T`, `{}T`) = a
  **collection** of T; a type inside (`[K]T`, `{K}V`) = a **mapping** from
  the bracketed type to the one that follows.
- Inside `[…]` the key's kind picks the order. A **finite ordinal** (enum,
  `bool`, `char`, integer subrange) = an array: keys and order fixed at
  compile time. **Any other** key (`str`, `int`, class, named tuple) =
  **insertion order**: `[str]float` is `OrderedTable` on Nim, a dict on
  Python. Inside `{…}`, any hashable type, no order promised.

|                | ordered `[…]`          | unordered `{…}` |
|----------------|------------------------|-----------------|
| **collection** | `[]T` list             | `{}T` set       |
| **mapping**    | `[K]T` ordered         | `{K}V` dict     |

Underneath, a collection is a mapping that supplies its own key: a list maps
positions to elements, a set maps elements to in-or-out. Hence `xs[i]` and
`x in s` are both lookups, and a set cannot hold anything twice.

Consequences: `[10]T` ≡ `[0..9]T` (a length is shorthand for a subrange; on
Nim `array[10,int] is array[0..9,int]` is `true`), so the fixed array is not
a special form. `{:}` has the colon of `key: value`, so it is the empty
dict; bare `{}` is the empty set.

**What `for x in c` and `x in c` give: the half NOT known in advance.**
- keys known in advance (`[]T`, `[N]T`, `[E]T`, `[lo..hi]T`: positions or the domain) → the **values**; `x in c` tests values;
- keys not known in advance (`[str]V`, `{K}V`) → the **keys**; `k in m` asks whether k arrived;
- a set `{}T` → its elements (they are its keys).

`.keys()` / `.values()` / `.items()` for the other half. `enumerate(c)` = `(position, element)` for a list, `(key, value)` for every mapping. So `for k in totals` over a `[str]float` gives keys, in insertion order.

**Portability:** `{…}` types iterate in insertion order on Python and hash
order on Nim — never depend on it; sort the keys (sort the *keys*, not the
table: `sorted(d)` compiles only on Python). `[O]T` is fine: all four forms
yield values in domain order on both backends, `[E]T` included. So is a
`[K]V` over any other key: keys in insertion order on both. Need a dict
whose order matters? Declare it `[str]V`, not `{str}V`.

| Adascript | Python | Nim |
|-----------|--------|-----|
| `[]T` | `list[T]` | `seq[T]` |
| `[N]T` | `tuple[T, ...]` (fixed-size) | `array[N, T]` |
| `[*]T` | `Sequence[T]` | `openArray[T]` |
| `[E]T` | `dict[E, T]` | `array[E, T]` (enum-indexed) |
| `[K]V` | `dict[K, V]` | `OrderedTable[K, V]` (K not a finite ordinal) |
| `{K}V` | `dict[K, V]` | `Table[K, V]` |
| `{}T` | `set[T]` | `HashSet[T]` or `set[T]` (ordinal) |
| `?T` | `T \| None` | `Option[T]` |
| `(T, U)` | `tuple[T, U]` | `(T, U)` |
| `(T, U) -> R` | `Callable[[T,U], R]` | `proc(a0: T, a1: U): R` |

Types compose: `{Node_T}[]Node_T` = dict mapping node to list of nodes.

**Function types** — written like a `def` signature, `(T, U) -> R`:
```adascript
type Op_T is (int, int) -> int
def run(cb: () -> None): ...             # () and (,) are the same; (T) = (T,)
let p: (str) -> int | None = parse_digit # result is a whole type: optional int
var check: ?(Point) -> bool = None       # leading ? = the function is optional
var steps: [](int) -> int = [inc]
```
Nesting: `->` groups right; `(…)` before `->` is always a parameter list.
`(int) -> (int) -> int` returns a function; `((int) -> int) -> int` takes one;
`?(int) -> int` = optional function; `(int) -> int | None` = `(int) -> ?int`.
In a `def`, the first `->` is the def's: `def pick() -> (int) -> int:`.
NOT `[(T, U)]R` — that is now an insertion-ordered map keyed by a tuple
(`[(,)]R` is refused with a hint). NOT `{(T, U)}R` — a dict keyed by a tuple.

**Empty literals** — resolves Python's `{}` ambiguity:
```adascript
var counts:  {str}int = {:}    # empty dict  → Python: {}   Nim: initTable()
var visited: {}str    = {}     # empty set   → Python: set() Nim: initHashSet()
```

**Open arrays** (`[*]T`) are only valid in parameter/return annotations, not variable declarations. They accept both `[]T` (seq) and `[N]T` (fixed array) at call sites.

### Named types, not bare ones

**Rule:** don't use bare `int` / `float` / `str` for a value that means something specific. Declare a named type and put the unit or format in a comment on its declaration.

```adascript
# discouraged: what goes in, what comes out?
def format_dates(epochs: []int) -> {int}str:

# preferred
# seconds since 1970-01-01 UTC
type Epoch is int
# an Epoch as the date column prints it: YYYY.MM.DD
type DateStamp is str
def format_dates(epochs: []Epoch) -> {Epoch}DateStamp:

# nested containers: say what is keyed by what
var owners: {TargetKey}{LineNo}[]HitIndex = {:}   # not {str}[]int keyed by "<target>\x02<line>"
```

**Rationale:**
- The signature documents itself, and `grep Epoch` finds every use.
- Nested containers become readable, and often better shaped. Glued string keys give way to a nested mapping.
- The unit or format is written once, on the type.
- The representation can change in one place.
- There is no cost: a named scalar type is a plain alias on both backends (Nim `type Epoch = int`, Python `Epoch = int`), so `let n: int = e + 1` needs no conversion. (`distinct`, below, is the opt-in when mixing should be refused.)

**Keep bare types for** values that only count or index: lengths, widths, string offsets, loop indices, and text that is just text. Rule of thumb: if the declaration would need a comment saying what the `int` holds, name the type instead.

Both naming styles exist in the examples, `Velocity_T` and `Epoch`; be consistent within one program. A class NEVER ends in `_T`, in either style: name it for the thing it is (`Report`, `Flight`). The snippets are in `EXAMPLES/DOC/type_snippets.ady`.

### `distinct` and units

A named type is an alias: it documents, it does not enforce. `type Distance_T is distinct float` makes a real type; derived units say what `*` and `/` between units make:
```adascript
type Distance_T is distinct float            # nautical miles
type Duration_T is distinct float            # hours
type Velocity_T is Distance_T / Duration_T   # derived: knots
def travelled(v: Velocity_T, t: Duration_T) -> Distance_T:
    return v * t                             # V * Dur is a Distance: no float() needed
let v: Velocity_T = d / t                    # Dist / Dur is a Velocity
var w: Velocity_T = 100.0                    # literal: takes the context's type
w += 5.0                                     # literal beside + - < is a Velocity_T
w *= 2.0                                     # * and / by a plain number SCALE
```
- keeps the base's operations closed over itself (`+`, `-`, comparisons, `min`, `max`, `abs`, `+=`, `f"{v:.1f}"`); distinct str: `+`, `len`; distinct int: `//`, `%`;
- **`*` and `/` scale**: `V * n`, `n * V`, `V / n` are V and the number stays a number; `V / V` is a plain float; **`V * V` is refused** (knots times knots is not knots). Two different units multiplied or divided are refused unless a derived unit defines it;
- `type C is A / B` defines A/B -> C, C*B -> A, B*C -> A, A/C -> B; `type C is A * B` defines A*B -> C (either order), C/A -> B, C/B -> A. Operands must be distinct types of one kind: float (quotient or product) or int (product only). `1.0 / t` (plain number over a unit) has no unit: refused;
- does NOT mix with its base or another distinct type: `let d: Distance_T = v` and `v + d` are errors; `let f: float = d` too -- write `float(d)` / `Distance_T(f)`;
- a literal converts implicitly where the type is visible (declaration, assignment, return, argument, record field -- named or positional, `Point(1.0, 2.0)` -- beside `+ - <`); a base-typed *variable* never does;
- money: `distinct int` in cents. `price * 3` scales; `price * qty` needs `type Total_T is Cents_T * Qty_T`;
- Nim: `distinct float` + borrowed procs + one small proc per relation; Python: `class Velocity_T(float)`. Nim checks everything; Python works out the unit of arithmetic over typed names and refuses declarations, assignments and operators it can see.

**A narrowed unit**: `type Latitude_T is Degrees_T range -90 .. 90` (P a distinct float or int; bounds may be negative; `..<` excludes the top). A type of its own with a parent: it goes UP to `Degrees_T` with no cast (assignment, argument, `Radians_T(lat)`), comes DOWN only by `Latitude_T(d)`, which checks the range (raises `AssertionError`; Nim `AssertionDefect`), and is refused beside a SIBLING (`let l: Latitude_T = lon`, `Latitude_T(lon)`, `at(lon)`). Arithmetic is the parent's (`lat + lat` is a `Degrees_T`: convert back to store it); a literal is checked where the type is declared. Prefer it to `distinct float range` whenever a parent unit exists, and never write `Degrees_T(float(lat))`. Both backends; `EXAMPLES/test_narrowed_type.ady`.

**A mod type**: `type Slot_T is mod 8` (whole number, 0 .. 7) and `type Bearing_T is Degrees_T mod 360` (a distinct float or int parent). Where `range` raises, `mod` wraps, with the sign of the modulus as Python's `%` has it: `Bearing_T(-10.0)` is `350.0`, `Slot_T(-1)` is `7`. `+`, `-`, `*` on it wrap, and `bearing + Degrees_T(30.0)` is a `Bearing_T`; it goes UP to its parent with no cast and comes DOWN by `Bearing_T(d)`; `Bearing_T / Bearing_T` is a plain float; a literal is wrapped where the type is declared. M may be a number or a `const` declared `int` or `float` (`const CAPACITY: int = 100`, `type Index_T is mod CAPACITY`: a ring-buffer index). A mod type of whole numbers is an array index type: `var items: [Index_T]int` has M slots, indexed by an `Index_T` with no `int(...)`. A standalone `mod M` has no parent, so a plain `int` enters it by `Slot_T(n)`. It is refused beside a sibling and beside a plain number (`bearing + 1.0`). Use it for angles, bearings and ring indexes instead of a `modulo(...)` helper. Both backends; `EXAMPLES/test_mod_type.ady`.

**A derived unit combines exactly TWO units**; a chain is built by naming the middle:
```adascript
type Momentum_T is Mass_T * Speed_T          # kg m/s
type Energy_T   is Momentum_T * Speed_T      # NOT: Mass_T * Speed_T * Speed_T (refused)
def kinetic(m: Mass_T, v: Speed_T) -> Energy_T:
    return 0.5 * m * v * v                   # (0.5*m)*v is a Momentum, *v an Energy
```
`m * (v * v)` is refused (Speed*Speed has no unit) unless `type SpeedSq_T is Speed_T * Speed_T` exists. Relations run both ways: `e / v` is a Momentum, `p / m` a Speed.

**A fixed multiple of a unit** is declared with a number (or a `const` float) times the unit -- Nim only, `ady2py` refuses it:
```adascript
const METRES_PER_MILE: float = 1609.344
type Distance_in_km_T    is 1000.0 * Distance_T            # one km is 1000 m
type Distance_in_miles_T is METRES_PER_MILE * Distance_T   # one mile is 1609.344 m
let mi: Distance_in_miles_T = Distance_in_miles_T(d)       # d: Distance_T -> d / 1609.344
let m: Distance_T = Distance_T(mi)                         # mi * 1609.344
```
`C(x)` scales when x is the other unit, keeps the number when x is a plain number, is refused for any other unit; km to miles goes through the base. Over a `distinct int` it counts money: `type Dollar_T is 100 * Dollar_in_cent_T` makes `Dollar_T(cents)` a float and `Dollar_in_cent_T(d)` the nearest cent, halves away from zero; cents times a float is refused. The factor must be fixed at compile time (a `let`/`var` or a unit-typed const is refused): a varying rate such as euros per dollar is a derived unit, below.

**Money** (the commonest case): `Dollar_T` scales by a count, a tax rate or a discount; a currency conversion needs the rate as a derived unit:
```adascript
type Dollar_T is distinct float
type Euro_T   is distinct float
type Rate_T   is Euro_T / Dollar_T           # euros per dollar
const Max_Allowed_Quantity: int = 100
type Quantity_T is 0 .. Max_Allowed_Quantity # a count: Natural or a range, never bare int
let total: Dollar_T = unit_price * quantity  # quantity: Quantity_T -- scales
let tax: Dollar_T = total * 0.08             # plain float factor -- scales
def to_euro(amount: Dollar_T, rate: Rate_T) -> Euro_T:
    return amount * rate                     # Dollar * Rate is Euro
def to_dollar(amount: Euro_T, rate: Rate_T) -> Dollar_T:
    return amount / rate                     # Euro / Rate is Dollar
```
Refused: `usd + eur`, `usd * usd`, `eur * rate` and `usd / rate` (rate the wrong way round), `let d: Dollar_T = plain_float`. Print with `f"{x:.2f}"`. Exact sums: `distinct int` cents; converting int cents <-> float rate is written out (`Cents_T(...)`, `float(c)`), not derived. `x * n` with `n` an int, `Natural` or range variable scales a float-based unit. Counts and quantities are `Natural` or a range type (`type Quantity_T is 0 .. Max_Allowed_Quantity`), not a bare `int`: on Nim a literal outside the range does not compile and a computed one stops at its line; Python keeps a plain int and does not check.

Use it for units and for IDs of different entities that share a representation. Keep aliases for values meant to mix with their base.

**`distinct` separates a type; it does not say which values are valid.** `Callsign_T("")` and `let c: Callsign_T = "not a callsign !!"` both compile and run. A subrange bounds a number and an enum is exactly its members, but nothing does that for a string. State the rule in a function that returns the type or a failure, and make every value through it; only it (and the literals of a test) calls the conversion:
```adascript
type Callsign_T is distinct str
type CallsignFailure_T is record:
    reason: str
def callsign(text: str) -> Callsign_T | !CallsignFailure_T:
    if text == /^[A-Z][A-Z0-9-]{1,11}\z/:       # \z, not $: `$` also matches before a final newline
        return Callsign_T(text)
    return CallsignFailure_T(f"'{text}' is not a callsign")
```
It is a convention the compiler does not check. For a rule that has to hold wherever a value is made, make it a class that asserts in `__init__` (`GeoPoint` in `EXAMPLES/MAP_UTILS/map_geo.ady` does); a class cannot inherit from `str` on Nim, so a validated string cannot also be accepted where a `str` is -- pass it on with `str(c)`. See `callsign` and `test_geo_server.ady` in `EXAMPLES/GEO_SERVER/`.

**No bare `float` for a quantity that has a meaning.** A distance, a time, an angle each get a type (`EXAMPLES/GEO_SERVER/geo_server.ady`). What a quantity cannot be goes in a subrange, which an alias does not mix up but does bound; what it cannot be mixed with goes in `distinct`:
```adascript
type Distance_T is distinct float            # not addable to an angle: refused at compile time
type Area_T     is Distance_T * Distance_T   # a squared distance, so `dx * dx + dy * dy <= r_sq` types
type Bearing_T   is float range 0.0 .. 360.0     # clockwise from North; 360 allowed, for rounding at the seam
type HalfAngle_T is float range 0.0 .. 180.0     # a wedge's reach to one side: at most half a circle
def angular_gap(a: Bearing_T, b: Bearing_T) -> HalfAngle_T:   # the smaller angle between two bearings
    let around: float = abs(a - b) % 360
    around if around <= 180 else 360 - around
```
A float subrange is checked at RUN time, on Nim (an assert after an assignment, naming the type and the value); a range type is an alias, so a `Bearing_T` and a `HalfAngle_T` still mix. A `distinct` type is the one the compiler keeps apart. Take the quantity out for `math` with `float(d)`, put the result back with the named type.

Other enforcement: enums are their own types; subranges are bounds-checked, on Nim only; records are nominal; `?T` is not `T`; `Path` is a distinct string, so `let p: Path = s` is an error; write `Path(s)`.

Style: every place on disk is a `Path`, joined with `/` (`Path(root) / sub / ".git"`), never a `str` joined with `"/"`; parameters that are directories or files are typed `Path`. Keep `str` for what is not a place on this disk (a URL, a path as another tool reports it, a git config value); convert with `str(p)` where an API takes strings, e.g. `run(["rmdir", str(work)])`. Go up with `.parent`, not `/ ".."`.

Failures: **an operation that can fail returns `T | !Failure_T`; it does not raise.** Do not write `try/except` around what you expect to go wrong -- a missing file, a failed command, a path not below its base, a bad number. Take the result where you call it, so the intent is explicit, and either handle it right there or pass it up to the caller:

```adascript
let res: int | !Failure_T = read_number(text)
if res is Failure_T:
    fatal(res.detail)          # handled here, next to the call
print res + 1                  # res is the int from here on

def total(a: str, b: str) -> int | !Failure_T:
    do:
        x <- read_number(a)    # a failure ends the function and is
        y <- read_number(b)    # passed up, as it is, to the caller
    return x + y
```

Passing up is as easy as with an exception, and explicit: the function says `| !Failure_T` in its signature and each `do:` step (or `return`) is where it happens, so the caller sees that it can fail and decides where it is handled. The built-in operations are written this way: `shell:` (`str | !ShellFailure_T`), and `Path.mkdir`, `.relative_to`, `.read_text`, `.read_lines`, `.write_text` (`... | !PathFailure_T`), `parse_float`, `parse_int` and `parse_enum` (`... | !ParseFailure_T`), and `input(prompt)` and `stdin.readLine()` (`str | !InputFailure_T`, `.reason`: the input ended). A failure that is dropped is refused. Exceptions stay for what is not expected -- a bug, and the older forms that still raise (`readFile`, `writeFile`, `for line in p.lines:`): prefer the failure-typed spelling where there is one. An exception travels up through functions whose signatures say nothing about it and is caught (or not) somewhere else; a failure value is in the type of every function it passes through.

---

## Variable Declarations

```adascript
var   counter: int   = 0        # mutable
let   name:    str   = "Alice"  # immutable
const MAX:     int   = 1_000    # compile-time constant

var result: []int               # no init: empty value of the type, both backends
# `result: []int` without `var` is Python's annotation -- binds nothing, on
# both backends. The first assignment picks the type up. In a record/class
# body the bare form is the field spelling and does declare.
```

**Tuple unpacking:**
```adascript
let (x, y) = point              # explicit let destructuring
var (a, b) = (1, 2)             # explicit var destructuring
a, b = some_func()              # implicit let tuple unpack (bare comma = implicit let)
```

---

## Enums

```adascript
type Door_T  is enum Door1, Door2, Door3
type Priority is enum LOW, MED, HIGH
type Digit_T  is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are valid assignment keywords.

**Python output:** `class Door_T(Enum): Door1 = 0; ...` (members compare, by value)
**Nim output:** `type Door_T = enum Door1, Door2, Door3`

**Members with values** -- `type Key_T is enum DOWN = 258, UP = 259, END = 360`, or one `NAME = value` per line in the block form (`enum:`). Every member has a value or none does (a mix is refused); the values must strictly ascend and give the order: `ord`, `<`, `case` and sets follow them. Consecutive values (`1, 2, 3`) leave the enum as good as any other; values that skip a number can still order, compare and `case`, but cannot index an array (`[E]T`), be iterated (`for x in E`) or be stepped (`'Next`, `'Prev`), on both backends. `parse_enum(E, n)` turns an integer into the member with that value (`E | !ParseFailure_T`), and `E(n)` raises where no member has it.

A member stringifies as its bare name on both backends — `str(d)`,
`print d`, `f"{d}"` and `d'Image` all give `Door1`, matching Nim's `$`.
(The generated Python class carries a `__str__` for this.) A *container* of
enum values still differs: Python formats elements with `repr`, so
`print xs` over a `[]Door_T` gives `[<Door_T.Door1: 0>, ...]` against Nim's
`@[Door1, ...]`. Known, and in `TODO.md`.

Reading an enum member from text is `parse_enum(E, s)` -> `E | !ParseFailure_T` (exact name; an integer `s` is read as the member's value, `.text` its digits); `State(s)` is the older form and raises:
```adascript
def parse_state(s: str) -> State:
    let state: State | !ParseFailure_T = parse_enum(State, s.replace("-", "_").upper())
    if state is ParseFailure_T:
        return ACTIVE
    return state
```

---

## Named Tuples

```adascript
type Point is tuple:
    x: float
    y: float

p = Point(x: 1.0, y: 2.5)       # construct with (field: value) syntax
```

**Python output:** `Point(x=1.0, y=2.5)` via `NamedTuple`
**Nim output:** `(x: 1.0, y: 2.5)` structural tuple literal

Named tuple literals work inside collections and as function arguments:
```adascript
fringe.push((stage: STAGE1, budget: float(CAPITAL)))
```

---

## Records and Variant Records

**Record** (dataclass):
```adascript
type Person is record:
    name: str
    age:  int
```

**Python output:** `@dataclass class Person: ...`
**Nim output:** `type Person = object`

**Discriminated (variant) record** — fields depend on a tag:
```adascript
type Shape_Kind is enum Circle, Rectangle

type Shape (Kind : Shape_Kind) is record:
    case Kind is
        when Circle:
            Radius : float
        when Rectangle:
            Width  : float
            Height : float
```

**Nim output:** native variant object with `case Kind: Shape_Kind`
**Python output:** flattened `@dataclass` with `None` defaults for unused fields

**Bare literals** — the kind alone builds a value, and matches in a pattern:

```adascript
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

## Subranges

```adascript
type SmallInt is 0 .. 255     # inclusive, both ends
type Index    is 0 ..< 10     # exclusive upper bound (0–9)
type Age      is int range 0..100    # synonym form

type Probability is float range 0.0 .. 1.0   # float subrange
```

**Python output:** `int` or `float` (type alias)
**Nim output:** native range type with compile-time bounds checking. Float subranges emit `assert` after every assignment.

Tick attributes `T'First` and `T'Last` give the bounds of a subrange.

---

## Tick Attributes

Ada-style `'` attributes. Where a name is followed immediately by `'` and an identifier, the tokeniser emits the apostrophe as its own `TICK_TOKEN` instead of letting Python's lexer read it as a string quote; the grammar matches the pair as `tick_trailer = TICK + IDENTIFIER`.

| Expression | Meaning |
|------------|---------|
| `E'First` | First member of enum `E` |
| `E'Last` | Last member of enum `E` |
| `E'Range` | Full ordinal set of enum `E` |
| `expr'Next` | Successor |
| `expr'Prev` | Predecessor |
| `expr'choose` | Random element from enum, set, or range |
| `expr'Image` | String representation |

> **Note:** a tick attaches to a field access or a subscript as readily as to a bare name — `r.c'Image`, `xs[0]'Image` and `self.x'Image` all work on both backends, with no local binding or `str()` needed. Ticks do not *chain*: bind the intermediate value rather than writing `Stage_T'First'Image`, which is a parse error.

> **Note:** `E'Range` is a set of the members, so set arithmetic works (`Door_T'Range - {chosen}`). On a value, `x'Range` is the index range: `for i in word'Range`.

```adascript
# Iterating over an enum — two spellings, both fine
for s in Stage_T:
    print(f"processing stage {s}")

for s in Stage_T'First .. Stage_T'Last:
    print(f"processing stage {s}")

# Set arithmetic with 'Range
let available: {}Door_T = Door_T'Range - {candidateFirstChoice, carLocation}
let hostChoice: Door_T  = available'choose   # random door from the set

# Random selection from a range
t = (1..i)'choose    # random int in 1..i
```

---

## Ordinal Types as Domains

Every ordinal type is iterable by naming it — an enum, a named subrange,
and the two builtin ordinals that are never declared anywhere.

```adascript
type Off is 2 .. 6

for c in Color:      # RED GREEN BLUE
    pass
for o in Off:        # 2 3 4 5 6 — its own domain, not 0-based
    pass
for b in bool:       # False True
    pass
for ch in char:      # 256 of them
    pass
```

`ord(x)` is the ordinal position of any ordinal value, not just the
one-character string Python's builtin accepts:

| Expression | Value |
|------------|-------|
| `ord("a")` | 97 |
| `ord(GREEN)` | 1 (position in the enum, or the value it was declared with) |
| `ord(True)` | 1 |
| `ord(4)` | 4 |

**Python output:** `for c in Color` needs no help (an enum is a class, a
subrange is a `range`); `bool` becomes `(False, True)` and `char` a
256-element generator. `ord(...)` becomes an injected `_ada_ord` helper.
**Nim output:** `bool.low..bool.high`, `Off.low..Off.high`; `ord` is
native.

---

## Range Expressions

`..` is inclusive. `..<` excludes the upper bound.

```adascript
for i in 0 .. 10:       # 0, 1, …, 10
    pass

for i in 0 ..< 10:      # 0, 1, …, 9
    pass

if x in 1 .. 100:
    print("in range")
```

**Python output:** `range(lo, hi+1)` for `..`; `range(lo, hi)` for `..<`
**Nim output:** native `lo .. hi` / `lo ..< hi`

---

## Control Flow

### if / elif / else
Standard Python. Also supports single-statement inline form:
```adascript
if x < 5: print("x<5")
elif x < 10: print("5<=x<10")
else: print("x>=10")
```

### Statement modifier
`return`, `break`, `continue`, and a call to `die` or `quit`, may carry
their own `if` (Perl/Ruby style) and run only when the condition holds. Emits
the one-line `if cond: stmt` on both backends.
```adascript
return False if code_s == ""
return True if code_s.startswith("(")
return if quiet
continue if line.startswith("#")
break if depth < 0
die(f"no such file: {p}") if not -f p
quit(0) if len(todo) == 0
```
NO other statement may take one: an assignment, any other call, a `print`, a
`raise` under an `if` modifier is a parse error -- `x = 1 if c` opens like the
conditional expression `x = 1 if c else 2`. A modifier's `if` has no `else`,
so `x = 1 if flag else 2` is still a ternary.

A modifier testing an optional establishes the auto-unwrap for the rest of
the scope, as the indented guard does. Use the plain name after it; an
explicit `.get()` there unwraps twice and does not compile.
```adascript
let bt: ?BuildType = build_type_from(name)
continue if bt is None
builds.append((name: name, btype: bt))   # bt is a plain BuildType here
```

### while
```adascript
while queue:
    item = queue.pop()

while n > 0: n -= 1    # inline form
```

### case / when
Pattern matching. Ada-style alternative to Python 3.10+ `match/case` (both syntaxes work).

**Literal and range patterns:**
```adascript
case code:
    when 200:              print("OK")
    when 400 | 401 | 403:  print("client error")
    when 500 .. 599:       print("server error")
    when others:           print("unknown")
```

**Enum patterns:**
```adascript
case choice:
    when DontSwitch:
        if candidateFirstChoice == carLocation:
            stayWins += 1
    when Switch:
        if candidateSecondChoice == carLocation:
            switchWins += 1
```

**Tuple patterns (multi-dimensional dispatch):**
```adascript
let (year, age) = current_state
case (year, age):            # subject must be a tuple EXPRESSION, not a plain variable
    when (6, _):
        []
    when (0, _):
        [(BUY, maintenance_cost[0] + market_value[0])]
    when (_, 3):
        [(TRADE, -market_value[age] + market_value[0])]
    when others:
        [(KEEP, maintenance_cost[age])]
```

**Python output:** `match/case` with tuple pattern
**Nim output:** `if/elif/else` chain (Nim doesn't support tuple case selectors)

> **Critical:** The tuple desugar path fires only when `case` subject is a compound expression `(x, y)` or field access `x.kind`. A plain variable holding a tuple emits Nim's `case`, which rejects it. Always destructure with `let` first.

**Structural patterns (record matching):**
```adascript
case x:
    when Val_T(kind=VSym, sym="if"):    # uppercase → equality check
        return "keyword: if"
    when Val_T(kind=VSym, sym=name):    # lowercase → let binding
        return "symbol: " + name
    when Val_T(kind=VNum, num=n):
        return "number"
    when others:
        return "other"
```

**Sequence patterns:**
```adascript
case x.items:
    when [Val_T(kind=VSym, sym="if"), test, consequence, alternative]:
        return "if-expr"
    when [Val_T(kind=VSym, sym=op), *args]:    # *name captures tail
        return "call: " + op
    when []:                                    # empty list
        return "empty"
    when others:
        return "other"
```

Rules: `TypeName(field=Value)` with uppercase → equality check; lowercase → `let` binding. `*rest` captures tail. `[]` matches empty. `_` or `others` → catch-all.

### Style: `case` over `if` chains, enums over strings, expressions over loops
Write the shorter form the language has. The examples are written this way, and
the transpiler is tested on it.

**A chain of `if`/`elif` on one value is a `case`.** A `case` branch with a value
is the function's result when it is the last statement (no `return`), a `when`
takes a regex, a guard (`when X if cond:`) or an enum, and an enum `case` with no
`when others` is checked for completeness.
```adascript
# discouraged
if name.endswith(".ady") or name.endswith(".py"):
    return PYTHON
elif name.endswith(".nim"):
    return NIM
else:
    return PLAIN

# preferred
case name:
    when /\.(ady|py)$/: PYTHON
    when /\.nim$/:      NIM
    when others:        PLAIN
```
The same goes for a long run of `==` tests on one name, for a `word == "a" or
word == "b" or ...` (use `word in KEYWORDS` against a named constant set) and for
key codes (an `enum` with values, then `case` over it).

**A range test is one chained comparison**, not two joined by `and`, and its
negation is `not` over the chain:
```adascript
# discouraged
if ch >= 32 and ch <= 126: ...
if day < 1 or day > days_in_month: ...

# preferred
if 32 <= ch <= 126: ...
if not 1 <= day <= days_in_month: ...
```

**A string that is always one of a few values is an `enum`.** A mode, a state, which
of two prompts, which quotes a string was opened with: a `str` for these lets any
text in, and `""` or `"/"` has to be remembered to mean something. An `enum` lists
the values, `case` over it is checked for completeness, and a typo is a compile
error. Where a value also has a text to show or to look for, put it in a constant
array indexed by the enum, rather than turning the enum back into a string.
```adascript
# discouraged
var prompt: str = ":"                 # ":" or "/"
var open: str = ""                    # the quotes of an unfinished string, "" when none
...
if self.prompt == "/": ...
if open != "": close = line.find(open)

# preferred
type Prompt_T is enum COLON, SLASH
const PROMPT: [Prompt_T]str = [COLON: ":", SLASH: "/"]

type Quote_T is enum NO_QUOTE, TRIPLE_DOUBLE, TRIPLE_SINGLE
const DELIMITER: [Quote_T]str = [NO_QUOTE: "", TRIPLE_DOUBLE: "\"\"\"", TRIPLE_SINGLE: "'''"]

var prompt: Prompt_T = COLON
var open: Quote_T = NO_QUOTE
...
if self.prompt == SLASH: ...
if open != NO_QUOTE: close = line.find(DELIMITER[open])
```
Member names are global, so give them names that do not collide with another enum's
(`NO_QUOTE`, not `NONE`). Not every string is a state: text the user typed, a
file's lines, a message to show stay `str`. A `""` that means "nothing" is a smell
of another kind: use `?str`, or a `| !Failure_T` result.

**A loop that only accumulates or searches is a comprehension**: `sum(...)`,
`any(...)`, `all(...)` over a generator, or a list comprehension for a new list.
A variable that is only there to be added to is a sign.
```adascript
# discouraged
var total: float = 0.0
for i in 0 ..< len(a):
    total = total + a[i] * b[i]
return total

var found: bool = False
for c in word:
    if 97 <= ord(c) <= 122:
        found = True

# preferred
return sum(a[i] * b[i] for i in 0 ..< len(a))
return any(97 <= ord(c) <= 122 for c in word)
```
Index with the wrap-around in the expression (`tour[(i + 1) % n]`) instead of
special-casing the last element after the loop.

Keep the loop where the body does more than produce one value (it changes
something, prints, or stops early for a reason that is not a plain `any`/`all`),
and where the loop is what an example is showing.

---

## Functions

```adascript
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
```

**Implicit return:** if a function has a return-type annotation and its last statement is a bare expression (not `return`), it's promoted to a return. Excludes `-> None`.
```adascript
def clamp(x: int, lo: int, hi: int) -> int:
    max(lo, min(x, hi))    # implicitly returned
```

**Generator functions:** `yield` transpiles to Python generators and Nim iterators.
```adascript
def shortest_path(self, start_state: S, end_state: S):
    while fringe:
        ...
        if current_state == end_state:
            yield self.real_cost(cost), path
```

---

## Classes and Inheritance

Use `var`, `let`, `const` inside class body to declare fields.

```adascript
class TrieNode:
    var children: [Digit_T]TrieNode
    var words:    []str

    def __init__(self):
        self.children = {d: None for d in Digit_T}
        self.words = []
```

**Inline field defaults** are injected into the constructor automatically:
```adascript
class AwkProcessor(AwkBase):
    var NR     : int = 0
    var counts : [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]

    def __init__(self, fs: str = " "):
        self.FS = fs    # only caller-supplied fields need explicit init
```

**Mutable self** — the transpiler auto-detects if a method mutates `self` (field assignment, `+=`, `.add()`, or a call to a method that does — transitively) and emits `self: var ClassName` in Nim. A method that only reads, even one calling other readers, keeps plain `self`. A method called *on a field*, or `self` passed to another routine, is assumed to write. No annotation needed.

**Parameter mutation** — parameters follow Python's rules. Rebinding the name (`s = s + "!"`) is local: Nim shadows it with `var s = s`. Mutating in place (`xs.append(...)`, `xs[i] = ...`, `+=`) is visible to the caller: Nim emits `xs: var seq[int]`. No annotation needed either way.

**Forwarding constructors** — when a subclass has no `__init__`, the transpiler generates one mirroring the parent's parameters.

**`@virtual`** — only needed when subclasses live in a different file (module). Makes Nim emit `ref object of RootObj` for cross-module dynamic dispatch.

**Inheritance:**
```adascript
class Circle(Shape):
    var radius: float

    def __init__(self, r: float):
        self.radius = r

    def area(self) -> float:
        return 3.14159 * self.radius ** 2
```

**Declaration order** — does not matter, as in Python: a function, method or `__init__` MAY call a function or method defined below it, and a class MAY use a class defined below it (in a field, a signature or a constructor call). The Nim backend forward-declares every routine called before its definition and puts all types in one `type` section.

**`var` instances** — mutable `self` is inferred transitively, so if any method reaches a field-mutating sibling, the instance must be `var`, not `let`:
```adascript
var report: Report = Report(opt)   # let → Error: expression 'report' is immutable, not 'var'
report.run()
```
Only the Nim backend reports this. Rule of thumb: if you call a method on it, declare it `var`.

**ALL_CAPS for shared state** — when a class is defined inside a function, local variables of the outer function aren't visible in Nim's hoisted methods. Declare shared variables with ALL_CAPS names; the transpiler hoists them to global scope.

---

## Generic Functions

Type parameters are declared in brackets after the name and used in the
annotations. One definition serves every instantiation.

```adascript
def first_of[T](xs: []T) -> T:
    xs[0]
def head_of[Elem](xs: []Elem) -> Elem:   # any name, not just one letter
    xs[0]

print(first_of[int]([7, 8]))     # ALWAYS name the type at the call
print(first_of[str](["x"]))
```

**Adascript never infers type parameters.** Both are errors, on both backends:
- `first_of([7, 8])` -- a bare call of a generic function: write `first_of[int](...)`;
- `def first_of(xs: []T) -> T` -- a type parameter nobody declared: write `def first_of[T](...)`.

A type argument is a name or a tuple (`first_of[Row_T]`, `first_of[(int, str)]`); an inline `[]int` is not parsed there, so name the composite first (`type Row_T is []int`). A definition nested in a generic function uses the function's `T` without declaring it; methods use their generic class's parameters. Prefer names worth reading (`Node_T`, `Elem_T`) over `[T]`. A declared parameter is scoped to the function, so it may share a name with a real type the caller has.

**Nim output:** `proc first_of[T](xs: seq[T]): T`; `first_of[int](...)` is passed through.
**Python output:** `def first_of[T](xs: list[T]) -> T` (PEP 695, 3.12+); the type application is dropped at the call, since a function object is not subscriptable.

---

## Overloads

One name, several defs, differing in parameter TYPES: the call picks by the types of its arguments (Ada, Nim). Works for functions and methods, operators included -- `__mul__(self, scale: float)` and `__mul__(self, t: Duration_T)` side by side, so `v * 2.0` scales and `v * t` is a displacement. Prefer this to `over(t)` / `per(t)` helper methods. Constructors too (`Vector(length, angle)` / `Vector(x, y)`). A LITERAL argument to an overloaded name is refused on Nim: write `Meters_T(3.0)`. Same parameter types twice is an error (a name defined twice). Python: defs are renamed, a dispatcher picks by exact type, then isinstance (a distinct type is its own); call by position. Unions and generics match anything. `EXAMPLES/test_overload_types.ady`.

## Generic Classes

```adascript
class Optimizer[S, D, C]:
    var offset: float

    def get_next_decisions(self, current_state: S) -> [](D, C):
        raise NotImplementedError()

    def shortest_path(self, start: S, end: S):
        ...
        yield cost, path
```

Subclass by instantiating parameters:
```adascript
class BookMap(Optimizer[State_T, State_T, Cost_T]):
    def get_next_decisions(self, curr: State_T) -> [](State_T, Cost_T):
        return self.G.get(curr, [])
```

Methods defined outside a generic class avoid Nim 2.x generic-method restrictions and can be called via UFCS:
```adascript
def longest_path(self: Optimizer[S, D, C], start: S, end: S) -> (float, []D):
    ...
```

---

## Shell Integration

Shell commands are first-class expressions.

A capturing form keeps the two streams apart: `.output` is stdout alone,
`.stderr` holds the rest, and neither reaches the terminal. So `2>/dev/null`
is redundant in `shell:`/`shellLines:` that capture -- a failing command
gives clean output and an empty `[]str`, not error text. It is NOT redundant
in the forms that keep the terminal (`shell: cmd` alone, `let rc: int =
shell: cmd`), which pass both streams through.

```adascript
let result = shell: git status
print(result.output)    # stdout as string
print(result.stderr)    # stderr as string
print(result.code)      # exit code as int

# Lines capture — type annotations and bare names both work
let lines: []str = shellLines: ls -la
entries = shellLines: find . -name "*.ady"
for line in lines:
    print(line)

# Variable interpolation — simple names and function calls
let branch: str = "main"
let r = shell: git log --oneline {branch}
shell: mkdir -p -- {!os.path.join(d, "subdir")}

# git's revision braces are never interpolated: a { right after ^ or @
let c = shell: git -C {!repo} rev-parse {!tag}^{commit}   # also X^{}, @{u}, HEAD@{1}
# any other literal brace in an interpolating line: double it, {{ and }}
# backslashes reach the shell as written, on both backends: grep '\bcat\b'

# Options
let r = shell(cwd = "/tmp"): pwd
let r = shell(timeout = 5000): slow-command

# Discard output
shell: rm -rf /tmp/build

# Block form — multiple commands joined with &&
shell:
    echo hello
    echo world

# join picks the separator: ";" runs all regardless, "|" makes one pipeline.
# With ";" the .code is the LAST command's, so a mid-block failure is
# invisible in it and check = true has nothing to catch. Test r.stderr for a
# scan; use join = "&&" with pipefail = true for a must-all-succeed sequence
# (pipefail is required for any line ending in a pipe, or the last command's
# 0 hides the failure). grep/rg exit 1 for "found nothing" and 2 for a real
# error, so a scan's status cannot tell those apart -- stderr can.
let r = shell(join = ";"):
    rg FATAL {log} | head -20
    rg SEVERE {log} | head -20
if r.stderr.strip() != "":
    stderr.writeLine("scan: " + r.stderr.strip())

# Interactive block (PTY expect/send)
shell:
    bc -q
    send("2 + 2\n")
    expect("4")
    send("quit\n")
```

| Adascript | Python 3 | Nim |
|-----------|----------|-----|
| `let r = shell: cmd` | `subprocess.run(…, capture_output=True)` | `execCmdEx("cmd")` |
| `let ls = shellLines: cmd` | `…stdout.splitlines()` | `execCmdEx(…)[0].splitLines()` |
| `let ls: []str = shellLines: cmd` | same (annotation stripped) | same (Nim infers type) |
| `ls = shellLines: cmd` | same (bare assignment) | same |
| `shell: cmd` | `subprocess.run("cmd", shell=True)` | `discard execCmd("cmd")` |
| `{var}` in body | f-string | `fmt"""…"""` |
| `{f(x)}` in body | f-string | hoisted to `let tmp = f(x)` |

Required imports (`subprocess`, `osproc`, `strformat`) are inserted automatically.

---

## Bash Variables and File Tests

```adascript
if $# < 2:
    print(f"Usage: {$0} <input> <output>")
    quit(1)

let dict_file:  str = $1
let phone_file: str = $2
for arg in $@:
    print(arg)

home   = $HOME
editor = $EDITOR
```

| Adascript | Python | Nim |
|-----------|--------|-----|
| `$0` | `sys.argv[0]` | `getAppFilename()` |
| `$1`…`$9` | `sys.argv[1]`… | `paramStr(1)`… |
| `$@` | `sys.argv[1:]` | `commandLineParams()` |
| `$#` | `len(sys.argv) - 1` | `paramCount()` |
| `$NAME` | `os.environ.get('NAME','')` | `getEnv("NAME")` |

**File-test operators:**
```adascript
if -e path:      # exists
if -f path:      # regular file
if -d path:      # directory
if -L path:      # symlink
if -r path:      # readable
if -w path:      # writable
if -x path:      # executable
if -s path:      # non-empty
if a -nt b:      # a newer than b
if a -ot b:      # a older than b

if not -f dict_file:
    die(f"{dict_file}: not found")
```

**Messages and exit — `die`, `warn`, `PROG` (built in, no import):**
```adascript
warn("no config, using defaults")         # stderr: "<prog>: no config, using defaults"
die("cannot read " + str(p))              # stderr: "<prog>: cannot read ...", exit 1
die(f"bad option {arg}", code = 2)        # same, exit 2
print(f"usage: {PROG} [-v] FILE")         # PROG: the program's name
```
- `PROG` is the name the program was invoked as, with no directory. It drops a leading `.` (ady2nim runs a cached `.name` binary) and a trailing `_gen.py` / `.py` (ady2py), so both backends print the same name. Nim reads it from `paramStr(0)`, so symlinks aren't resolved.
- `die` never returns (Nim `{.noreturn.}`), so a function may end in `die(...)` with no `return` after it.
- **Don't** write `let PROG = Path($0).name...` or your own `def die` / `def warn` for this. A module's own top-level `def die` / `def warn` or `let/var/const PROG` still takes precedence over the built-in (e.g. `c500.ady`'s `die` prints to stdout). The helpers are emitted only when used.

---

## Nim-Only Features

**`pyimport`** — an import that appears only in Python output; the Nim
backend routes it through nimpy. Use it **only for libraries with no shell
equivalent** (`numpy`, `requests`, a vendor SDK). Never for the time, the
process id, the platform, the environment, temp directories or file tests —
those have one-line answers and a `pyimport` costs the Nim build a nimpy
dependency and a libpython link:

Try `nimport` first: `os` and `time` are mapped natively, so the fix for
`pyimport os` is usually `nimport os` and not a subprocess at all.

```adascript
nimport os
nimport time
let pid: int    = os.getpid()                     # native, starts nothing
let now: float = time.time()                      # native, sub-second
```

Only what has no mapping goes to the shell:

```adascript
let (stamp, rc1) = shell: date +%Y-%m-%d-%H%M%S   # not datetime
let (kern,  rc4) = shell: uname -s                # not sys.platform
quit(1)                                           # not sys.exit(1)
let home: Path = Path($HOME)                      # not os.environ
```

`$PPID` is the one to watch: `$NAME` reads the *environment*, and no shell
exports `PPID`, so a bare `$PPID` is always `""`. Inside a `shell:` it is
your pid (the shell it starts is your child) — but `os.getpid()` is the
answer.

Never for regexes either: matching is an operator, so `pyimport re` has no
use at all. A pattern you can write is a literal; a pattern that arrives as
data — a rule from a config file or a database column — is `grep`'s job,
since a literal has nowhere to put it:

```adascript
if name == /^[A-Z]{3}_[0-9]+\.xml$/:              # a pattern you can write
    print $+0

def matches(text: str, pattern: str) -> bool:     # a pattern you cannot
  let (_, rc) = shell(stdin = text + "\n"): grep -qE -- {!pattern}
  return rc == 0
```

**`nimport`** — imports that appear only in Nim output, stripped from Python:
```adascript
nimport strutils, sequtils, algorithm
nimport stdlib          # PriorityQueue, FifoQueue, LifoQueue, ANY
from awk import AwkBase                          # record-processor base class
from shortest_path import Minimizer, Maximizer   # another .ady file as a library (auto-transpiled)
```

`nimport` has Python's meaning too: `nimport math` binds `math` (write `math.sqrt(x)`; a bare
`sqrt` is undeclared), `from math nimport sqrt, floor` gives just those two, and
`from json nimport *` gives the whole module. For the common modules (`math`, `os`, `time`, `strutils`, `sequtils`, `random`, `algorithm`, `json`) a bare name is refused with a message giving the line and the fix; for other modules Nim's compiler refuses it.
The transpiler imports for itself what it writes (`^` for `**`, a float `%`, `async`, `await`).

**Modules** — a module is a `.ady` file; `import` links a whole project:

```adascript
# EXAMPLES/PROJECT/dispatch.ady — the program
from lib/geometry import Point_T       # lib/geometry.ady, path written with '/'
from lib/fleet import Depot, Energy_T, Vehicle_T
# EXAMPLES/PROJECT/lib/fleet.ady — a module
from geometry import Point_T, distance   # a sibling is imported by its bare name
```

Resolution order for each imported name: the importing file's directory, its
parent, then the build cache (where the bundled `TO_NIM/STDLIB/*.ady`
libraries live). No match -> the name goes to Nim untouched, which is why
`nimport strutils` works. No `..` syntax; the parent rule covers `bin/` +
`lib/` layouts.

- Python's rule: `import geometry` binds `geometry` (write `geometry.distance(a, b)`, a bare `distance` is refused); `from geometry import distance` gives `distance(a, b)`; `from geometry import *` gives everything. For `import lib/fleet` the qualifier is `fleet`.
- Every top-level declaration of a dependency is exported automatically.
- Types, constructor signatures and record field order cross the boundary, so `Vehicle_T("van-9", p, 6.0)` and `Depot("Central", base)` work in an importer.
- A dependency's top-level statements run at import time — modules declare, programs act.
- Basenames must be unique project-wide and must not be Nim keywords (`mod.ady` fails).
- Keep the import graph acyclic: put shared types in a leaf module.
- Build the whole graph with `ady2nim c -r <entry>.ady`; `ady2nim -t` transpiles it and stops.
- **ady2py merges modules, it does not link them**: an `import` of a `.ady` found beside the file (or one directory up) is replaced by that module's text, once, so types and classes cross the boundary and a program split across modules runs on both backends. One namespace on Python (a name defined in two modules clashes), `geometry.f()` is rewritten to `f()` (refused where the file has its own `f`), the libraries in `TO_NIM/STDLIB` stay Nim-only.

**`# nimraw: <code>`** — raw Nim line verbatim, stripped from Python, for Nim with no Adascript spelling (a pragma: `# nimraw: {.push overflowChecks: off.}`). NOT needed for forward declarations: mutually recursive functions are written as in Python.

---

## Python Interoperability

Adascript knows which Python imports have direct Nim equivalents and which need the `nimpy` bridge.

**Natively mapped modules** (no runtime overhead):

| Python import | Nim module |
|---------------|------------|
| `import os` | `import os` |
| `import math` | `import math` |
| `import time` | `import times` |
| `import re` | `import re` |
| `import random` | `import random` |
| `import json` | `import std/json` |
| `import itertools` | `import sequtils` |
| `import asyncio` | `import asyncdispatch` |

Call translation examples:
```adascript
import math, time, re, random
x      = math.sqrt(4.0)      # → sqrt(4.0)
t      = time.time()          # → epochTime()
result = re.sub(r'\s+', ' ', text)   # → replace(text, re("\\s+"), " ")
n      = random.randint(1, 100)      # → rand(1..100)
```

**Non-native libraries** go through `nimpy` automatically:
```adascript
import requests
r = requests.get('https://example.com')
```
Nim output:
```nim
import nimpy
let requests = pyImport("requests")
var r = requests.get("https://example.com")
```

**Automatic `.to(T)` coercion** — when a variable has a primitive type annotation and its right-hand side is from a `PyObject` call chain:
```adascript
count: int   = r.json()['total']    # → r.json()["total"].to(int)
score: float = r.json()['score']    # → r.json()["score"].to(float)
```

---

## String Literals

`"..."` and `'...'` both make a `str` — pick whichever avoids escaping the
other quote. A single-character literal is a `char` only where a `char` is
declared; the declared type decides.

```adascript
let double: str = "she said hello"
let single: str = 'she said "hello"'
let initial: char = 'x'
let one_char: str = 'x'
```

| Form | Meaning | Python | Nim |
|------|---------|--------|-----|
| `"a"` / `'a'` | string | `"a"` / `'a'` | `"a"` |
| `'x'` declared `char` | single character | `'x'` (a `str`) | `'x'` (a `char`) |
| `"""…"""` | spans lines | `"""…"""` | `"…\n…"` |
| `r"\d+"` | raw — backslashes survive | `r"\d+"` | `r"\d+"` |
| `f"{x}"` | interpolation | `f"{x}"` | `fmt"{x}"` |

**Adjacent literals concatenate**, as in Python and C — no operator, and
nothing happens at run time. A piece may be a plain string or an f-string,
and the kinds mix freely in one run:

```adascript
assert "ab" == "a" "b"
assert f"x={n} " "then plain " f"and {n * 2}" == "x=42 then plain and 84"
```

Parentheses let a run break across lines, which is the usual reason to want
it — a long message stays readable in the source as well as in the output:

```adascript
let report: str = (f"{n} item(s) processed, "
                   "none rejected, "
                   f"{n * 2} checks run")
```

Nim has no juxtaposition rule, so a run is emitted as a `&` chain
(`fmt"…" & "…" & fmt"…"`); Python takes it verbatim.

---

## Print Statement

Python-2-style `print` without parentheses is supported (call form also works):
```adascript
print "hello"
print f"result: {value}"
print "x =", x
print("also valid")
print                      # an empty line
```

Nim output: `echo(...)`. Python output: `print(...)`. A bare `print` is `echo ""` / `print()`.

---

## Enum-Indexed Arrays

```adascript
type Priority is enum LOW, MED, HIGH
var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
print(costs[HIGH])    # 10

# Nested 2-D lookup table
var transition: [Hidden_State_T][Hidden_State_T]float = [
    HEALTHY: [HEALTHY: 0.7, FEVER: 0.3],
    FEVER:   [HEALTHY: 0.4, FEVER: 0.6],
]
```

**Python output:** nested dict
**Nim output:** `array[Hidden_State_T, array[Hidden_State_T, float]]` — stack-allocated, O(1) lookup.

An enum is one ordinal key among several; `[10]T`, `[0..9]T`, `[Off]T`,
`[bool]T` and `[char]T` are the same construct (an enum whose values skip a number is the exception: it cannot index an array). All of them iterate their
values in domain order on both backends, and `x in arr` tests values: the
keys are the domain, known in advance.

A comprehension fills one as readily as it fills a list — the annotation
picks which. Iterate the key type, not an integer range of the same length:

```adascript
type Off is 2 .. 6
var byE:   [Priority]int = [ord(p) * 10 for p in Priority]
var byOff: [Off]int      = [o * 10      for o in Off]      # byOff[2] is 20
var byB:   [bool]int     = [ord(b)      for b in bool]
var asList: []int = [i*i for i in 0..4]    # same RHS, a seq/list here
var asArr:  [5]int = [i*i for i in 0..4]   # a length has no type to name
```

`for p in Priority` makes the loop variable the key each value belongs to,
so adding a member cannot leave the two out of step; `for i in 0..2` only
happens to be the right length. There is no keyed comprehension
(`[LOW: 1 for ...]`) — values are positional.

**Insertion-ordered `[K]V`** — K not a finite ordinal:

```adascript
var totals: [str]float = {:}          # or {"a": 1.0}, ["a": 1.0], {k: v for ...}
totals["zeta"] = 3.0
totals["alpha"] = 1.0
for k in totals: print k              # KEYS, insertion order: zeta alpha
for v in totals.values(): print v     # 3.0 1.0
for k, v in totals.items(): ...       # (key, value), insertion order
for k, v in enumerate(totals): ...    # (key, value), as over any mapping
assert "zeta" in totals               # tests keys
```

Iterates and tests **keys** (they are not known in advance), like `{K}V`
and unlike `[E]T` (whose keys are its domain, so it gives values). Use
`.values()` for the values. Tuple keys work directly: `[(int, int)]float`.

---

## Callable Objects and Pipe Operator

Classes with `__call__` become callable; Nim uses `{.experimental: "callOperator".}` (inserted automatically). `__ror__` flips argument order for pipe syntax:

```adascript
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
print("hello" | bold)     # via __ror__
print(bold("hello"))      # via __call__
```

The `|` operator is context-sensitive: when operands involve custom types, emits Nim `|`; otherwise emits `or`.

---

## Collections — Key Patterns

**Sequences:**
```adascript
var words: []str = ["hello", "world"]
words.append("!")
print(len(words))
```

**Hash tables:**
```adascript
var counts: {str}int = {:}
counts["apple"] += 1
for key, val in counts.items():
    print(f"{key}: {val}")
```

**Sets:**
```adascript
var visited: {}str    = {}    # HashSet[string]
var seen:    {}Door_T = {}    # set[Door_T] (bitset — ordinal type)
visited.add("node_A")
if "node_A" in visited:
    print("seen")
```

The Nim backend uses bitset (`set[T]`) for ordinal types (bool, char, byte, small int, enum) and `HashSet` otherwise.

Python's operators work on both kinds: `a & b` (intersection), `a | b`
(union), `a ^ b` (symmetric difference), `a - b` (difference), and the
augmented forms `seen |= more`. Nim spells them `*`, `+`, `-+-` and `-`; the
emitter picks from the operand types, so the same source builds on both
backends. On integers the same signs stay bitwise. The snippets are in
`EXAMPLES/test_set_operators.ady`.

---

## Comprehensions

One syntax builds every container; the brackets and the annotation pick
which — the same scheme the type notation uses to declare them.

```adascript
var asList:  []int    = [i*i for i in 0..4]     # seq / list
var asArray: [5]int   = [i*i for i in 0..4]     # stack array
var asSet:   {}int    = {i*i for i in 0..4}     # set
var asDict:  {int}int = {i: i*i for i in 0..4}  # dict
```

Multiple generators and `if` guards work as in Python. Two lists join with
`+`, so a list drawn from several sources is one expression:

```adascript
var unitlist: [][]str = (
    [cross(ROWS, c) for c in COLS]
    + [cross(r, COLS) for r in ROWS]
    + [cross(rb, cb) for rb in ["ABC", "DEF", "GHI"] for cb in ["123", "456", "789"]])
```

The loop variable is typed from what it iterates, and the binding is scoped
to the comprehension as it is in Python:

```adascript
[r + c for r in ["A", "B"] for c in ["1", "2"]]   # ["A1","A2","B1","B2"]
[p + q for p in "AB" for q in "12"]               # the same, over strings

let same: int = 5
[same + "?" for same in ["p"]]      # a string in here
assert same + 1 == 6                # still the outer int out here
```

**Concatenation:** use `+`. Nim spells it `&` and the backend rewrites `+`
to that once it knows an operand is a string or seq; writing `&` yourself
is Nim-only — it is bitwise-and on Python and raises there.

**Nim output:** `collect(...)` from `std/sugar`, nested for multiple
generators; `toHashSet(collect(...))` for a set; `collect(initTable, ...)`
for a dict; and a copy loop into `array[N, T]` for a fixed-size array,
since Nim will not assign a `collect()` to one. Iterating a string yields
`char` there, so `p + q` above relies on `&(char, char)` giving a string.
Iterating a string gives a char, so `[]char` is the annotation for keeping
them and works throughout (append, index, add to a string, compare, pass to
a `str` parameter): `let chars: []char = [c for c in grid if c in
DIGITS+"0."]`. `in` over two strings is a membership/substring test on both
backends (`"x" in "daxfdjd"`).

A char is also stringified automatically wherever a string is wanted — a
call argument whose parameter is `str` (`cross(ROWS, c)` needs no
`str(c)`), a declaration annotated `str`, `.append` onto a `[]str`, and a
string method given part chars and part strings (`s.replace(c, "\\" + c)`;
Nim overloads `replace`/`split`/… all-char or all-string, never mixed, and
an all-char call is left alone). A slice is not a char and is left alone
(`s[i]` indexes, `s[2:10]` cuts). On Python a char *is* a one-character
string, so none of this arises.

**Not supported:** the keyed form `[LOW: 1 for ...]` — values are
positional. Iterate the key type when filling an `[O]T`.

---

## Guards, and the catch-all they require

`case`/`when` is the only pattern-matching construct; Python's `match`/`case`
is not accepted. A branch may carry an `if` guard, but a guard anywhere in the block
stops Nim checking the branches for completeness, so such a block must carry
an unguarded `when others:`. The same applies to a block whose subject is a
`str`. `when others` may not itself be guarded.

```adascript
def get_kind(arg: str) -> Kind_T:
    case arg:
        when "--":
            return cmdEnd
        when _ if arg.startswith("--"):
            return cmdOption
        when others:
            return cmdArgument
```

All Python 3.10 pattern forms work: literals, guards (`if`), wildcards (`_`), capture variables, class patterns, sequence patterns, OR patterns (`|`).

---

## Walrus Operator `:=`

The walrus operator assigns and tests in one expression. The primary use-case is optional-type bind chains — it provides Haskell-do-notation ergonomics without dedicated syntax.

```adascript
# Optional bind: if the result is present, unwrap and use it
def load_config(path: str) -> ?Config:
    if text := read_file_safe(path):
        if raw := parse_json(text):
            if port := parse_int(raw.get("port") or ""):
                return Config(host=raw.get("host") or "localhost", port=port)
    return None

# While loop consuming an iterator
while token := lexer.try_next(TK_STRCONST):
    emit(token)
```

**Nim output** — the transpiler hoists the binding out of the condition:

```nim
let text = read_file_safe(path)
if text.isSome:
    let raw = parse_json(text.get())
    if raw.isSome:
        ...
```

Inside a `while` condition, `:=` becomes a `let` before the loop with the test inlined.

---

## `do:` Block — Monadic Bind

The `do:` block is first-class do-notation for `?T` chains. Each `x <- expr` step evaluates `expr` (which must return `?T`), short-circuits to `return none(R)` if absent, and binds the unwrapped value to `x` as a plain variable.

```adascript
def compute(raw_a: str, raw_b: str) -> ?int:
    do:
        a <- parse_int(raw_a)
        b <- parse_int(raw_b)
        q <- safe_div(a, b)
        r <- clamp_positive(q)
    return r
```

After the block, `a`, `b`, `q`, `r` are plain `int` (not `?int`) and in scope for the rest of the function body.

**Nim output:**

```nim
proc compute(raw_a: string, raw_b: string): Option[int] =
    let adadoA = parse_int(raw_a)
    if adadoA.isNone: return none(int)
    let a = adadoA.get()
    ...
    return some(r)
```

Rules:
- Every `expr` after `<-` must return `?T`.
- The enclosing function must also return `?R`.
- All bindings are plain (non-optional) `let` variables in scope after the block.
- Use `do:` for chains of 3+ steps; walrus `:=` for 1–2 steps.

---

## Perl-Style Regex Literals

Adascript supports inline regex literals. No `import re` needed.

```adascript
# Match / non-match test — returns bool
if s == /^\d+$/:
    print("integer")

if s != /^\s*$/:
    print("non-blank")

# Flags: i (case-insensitive), g (findall)
if s == /^yes$/i:
    print("affirmative")

# Positional captures — $+1, $+2, ... after a successful match
if s == /(\w+)\s*=\s*(\w+)/:
    print(f"{$+1} → {$+2}")

# Named captures — $+{name}
if s == /(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/:
    print(f"{$+{day}}/{$+{month}}/{$+{year}}")

# Whole-match capture
if s == /\d+/:
    print($+0)

# Findall — /pat/g returns []str
let words: []str = s == /\w+/g

# Substitution — s/pat/repl/flags
s = s/\d+/[N]/g    # replace all digits with [N]
```

**Python output:** uses `re` module.
**Nim output:** uses `std/re`.

---

## Block-Form Enum Declarations

In addition to the inline `type E is enum A, B, C` form, enums can be declared with one member per line — useful for long enums or when per-member comments are needed:

```adascript
type Expr_Kind is enum:
    EK_IntLit      # integer literal  42
    EK_RealLit     # float literal    3.14
    EK_Sym         # symbol           foo
    EK_List        # list             (...)
    EK_Builtin     # built-in op      +, -, car, cdr
```

Both forms are identical at the type level and produce the same Python/Nim output.

---

## `@contextmanager` → Nim Template

Python's `@contextmanager` decorator transpiles to a Nim `template` with a trailing block argument. The `yield` in the body becomes the injection point for the caller's block.

```adascript
@contextmanager
def emit_block(self, start: str, close: str):
    self(start)
    self.indent_level += 2
    yield
    self.indent_level -= 2
    self(close)

# Call site — caller's block is injected at yield
with emit.emit_block("{", "}"):
    emit("int x = 42;")
```

**Nim output:**

```nim
template emit_block(self: var Emitter, start: string, close: string, body: untyped) =
    self(start)
    self.indent_level += 2
    body
    self.indent_level -= 2
    self(close)

emit.emit_block("{", "}"):
    emit("int x = 42;")
```

---

## Ownership (`own` / `lent` / `move` / `drop`)

Adascript exposes Nim's ARC (automatic reference counting) memory model through optional ownership annotations. These are purely additive — unowned code is valid and identical in behaviour.

```adascript
# own: declare a uniquely-owned value (freed at end of scope by ARC)
own a: Msg_T = make_msg("hello", 3)

# lent: borrow without taking ownership (read-only in Nim)
def summarise(msg: lent Msg_T) -> str:
    f"{msg.text} x{msg.count}"

print(summarise(a))    # borrows a

# with own: RAII scoped block — a is freed when the block exits
with own tmp = make_msg("scoped", 1):
    print(summarise(tmp))
# tmp freed here

# move: explicit ownership transfer (a is invalid after this)
own b: Msg_T = move(a)

# drop: explicit early release
own c: Msg_T = make_msg("temp", 5)
drop(c)
```

**Python output:** ownership annotations are stripped; code runs identically under GC.
**Nim output:** `own` → `var`, `lent` → `lent`, `move` → `move()`, `drop` → `=destroy()`.

---

## `html:` Blocks — a Class Renders Itself (Nim only)

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

An attribute value is a string or an expression without spaces
(`id=self.id`); `class` and `for` are fine as attribute names, and
`data-id` is written `data_id`. The block needs exactly one root tag.

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
dispatches on the object. `EXAMPLES/HTML/html_app.ady` is the whole
program, with an `App` that renders `html`, `head` and `body` around a
panel.

The same classes compile for the browser with `ady2nim js`, where the
karax tree is a live DOM. Needs `nimble install karax`. **Nim only**: the
Python backend does not know `html:`. Not built yet: event handlers
(`onclick`).

**Rules for writing one:** the method returns `Html`; the block has one root
tag; a child's HTML is `+ child.to_html()`; do not use it in a program that
must also build with `ady2py`.

---

## Complete Quick Example

```adascript
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

**Python output:** uses `Enum`, `NamedTuple`, `dict`, `range()`.
**Nim output:** uses native `enum`, `tuple`, `array[Stage_T, Choice_T]`, `lo .. hi`.

---

## Full Syntax Reference

| Feature | Adascript syntax |
|---------|-----------------|
| Mutable variable | `var x: int = 0` |
| Immutable binding | `let name: str = "hello"` |
| Compile-time constant | `const MAX: int = 1000` |
| Enum declaration | `type E is enum A, B, C` |
| Named tuple | `type P is tuple: x: float; y: float` |
| Record | `type P is record: name: str; age: int` |
| Variant record | `type S (Kind: K) is record: case ...` |
| Subrange | `type T is lo .. hi` |
| List annotation | `[]T` |
| Fixed array annotation | `[N]T` |
| Open array (param only) | `[*]T` |
| Dict annotation | `{K}V` |
| Set annotation | `{}T` |
| Enum-indexed array | `[E]T` |
| Optional | `?T` |
| Inclusive range | `lo .. hi` |
| Exclusive range | `lo ..< hi` |
| Enum first/last | `E'First`, `E'Last` |
| Full enum set | `E'Range` |
| Successor/predecessor | `expr'Next`, `expr'Prev` |
| Random selection | `expr'choose` |
| Empty dict literal | `{:}` |
| Named tuple literal | `(field: value, ...)` |
| Enum-indexed array literal | `[KEY: value, ...]` |
| Pattern matching | `case x: when P: ... when others: ...` |
| Inline suite | `if x>0: f()`, `while c: g()`, `when P: h()` |
| Generator function | `def f(): ... yield value` |
| Field with default | `var x: int = 0` inside class body |
| Mutable self (auto) | `self.field =`, or a call reaching one |
| Cross-module base class | `@virtual class C: ...` |
| Generic class | `class C[S, D, C]: ...` |
| An `.ady` module | `import module` binds the module (`module.name`); a bare use of a name of the module's that is not listed is refused on both backends |
| Import only some names of a module | `from module import A, B` |
| Nim-only / Python-only import | `nimport module` / `pyimport module` |
| Raw Nim injection | `# nimraw: <code>` |
| Shell capture | `let r = shell: cmd` |
| Shell exit code, terminal kept | `let code: int = shell: cmd` |
| Shell interpolation, quoted | `shell: cmd {!path}` |
| Shell interpolation, list | `shell: cmd {*args}` |
| Shell, fail on non-zero | `shell(check = true): cmd` |
| Shell, feed stdin | `shell(stdin = text): cmd` |
| Shell, child environment | `shell(env = e): cmd` |
| Shell, streamed lines | `for line in shellIter: cmd` |
| Streamed, fail on non-zero | `shellIter(check = true)` (at the end) |
| Shell, replace this process | `shellExec: cmd` (never returns) |
| Shell, run alongside | `let j: Job = shellSpawn: cmd` |
| Pipeline reports first failure | `shell(pipefail = true): a \| b` |
| Block join | `shell(join = ";"):` (`&&` default, `;`, `\|`, `\|\|`) |
| Where is a program? | `which("git")` -> `?Path` (`have()` is deprecated) |
| Fail with a message | `die("msg")` / `die("msg", code = 2)`: `<prog>: msg` on stderr, exit |
| Warn and carry on | `warn("msg")`: `<prog>: msg` on stderr |
| Program name | `PROG` (predeclared; no `let PROG = ...` needed) |
| Path join | `let p: Path = root / "sub"` (Path is a str subclass/distinct) |
| Path <-> str | `Path(s)` / `str(p)`; a bare `p = s` is refused on both backends |
| Read a file or stdin | `let f: File = (open(p) if p != "" else stdin)`; `File` is `typing.TextIO` on Python |
| Lines without the newline | `for line in f.lines:` -- the trailer strips it on both backends |
| A file's lines, by its `Path` | `for line in p.lines:` -- opens, reads and closes the file; prefer it to `readFile(p).split("\n")` |
| Character literal | `let c: char = '\t'`; narrowed in every position a char is declared (let/var, assignment, return, implicit return, `[]char` element, `{char}V` key, `{K}char` value, record field, argument) |
| Path split | `p.parent` -> Path, `p.name` -> str (pathlib rules, not os.path) |
| Path mkdir | `p.mkdir()` = mkdir -p (parents, exist_ok) -> `None \| !PathFailure_T` (`.op`, `.path`, `.reason`): take it -- `assert p.mkdir() is None`, `if r is PathFailure_T:`, or a `do:` step; a bare `p.mkdir()` is refused like any dropped failure |
| Path resolve | `p.resolve()` = realpath (absolute, symlinks expanded) |
| Text to a number or an enum | `parse_float(s)` -> `float \| !ParseFailure_T`, `parse_int(s)` -> `int \| !ParseFailure_T`, `parse_enum(E, s)` -> `E \| !ParseFailure_T` (`.what`, `.text`). A float is a decimal number and nothing else (sign, digits, one `.`, exponent: no spaces, `_`, `inf`, `nan`, hex); an int is a sign and digits that fit 64 bits; an enum member is named exactly (`beta` is not `BETA`). Nothing raises; `float(s)`, `int(s)` and `E("NAME")` still do |
| Read / write a file, by its `Path` | `p.read_text()` -> `str \| !PathFailure_T`, `p.read_lines()` -> `[]str \| !PathFailure_T` (no newlines), `p.write_text(s)` -> `None \| !PathFailure_T`: the failure names the `op`, the `path` and the `reason`; take it as `mkdir`'s. Nothing raises; `readFile`, `writeFile` and `for line in p.lines:` still do, and stay the way to stream or to not care |
| Path below a directory | `let r: Path \| !PathFailure_T = p.relative_to(base)` -- the Path (`"."` for the same path), or the built-in `PathFailure_T` (`.path`, `.base`) when p is not below base; pathlib's rules, `..` not resolved. `r is PathFailure_T`, `case r:`, or a `do:` step, as with `ShellFailure_T` |
| Wait for one / many jobs | `j.wait()` / `waitAll(jobs)` |
| Run a program, no shell | `run(["git", "log"])` -> RunResult |
| Run a program, output lines | `runLines(["ls", d])` -> `[]str` |
| Shell lines capture | `let ls = shellLines: cmd` |
| Shell lines (typed) | `let ls: []str = shellLines: cmd` |
| Shell (bare assign) | `ls = shellLines: cmd` |
| Shell expr interpolation | `shell: cmd {f(x)}` (auto-hoisted) |
| Discard shell output | `shell: cmd` |
| Shell block | `shell:` then indented commands |
| Interactive PTY block | `shell:` then `cmd` / `send(...)` / `expect(...)` |
| CLI argument | `$1`, `$@`, `$#` |
| Environment variable | `$HOME`, `$PATH` |
| File-test | `-e path`, `-f path`, `-d path` |
| File comparison | `a -nt b`, `a -ot b` |
| Python 2-style print | `print "text"` or `print expr, expr` |
| Pattern match | `case x:` / `when P:` / `when others:` (full pattern syntax) |
| Walrus bind | `if r := f():` / `while r := f():` |
| Monadic do block | `do:` / `x <- expr` |
| Regex literal | `s == /pat/`, `s != /pat/`, `s == /pat/g` |
| Regex capture | `$+1`, `$+{name}`, `$+0` |
| Substitution | `s = s/pat/repl/g` |
| Block-form enum | `type E is enum:` / one member per indented line |
| Context manager | `@contextmanager def f(): ... yield ...` |
| Owned value | `own x: T = expr` |
| Borrow parameter | `param: lent T` |
| Ownership transfer | `move(x)` |
| Explicit release | `drop(x)` |
| RAII scope | `with own x = expr:` |
| HTML page (Nim only) | `html:` in a `-> Html` method; tags indented below |

---

## Known Limitations

- **Comments on a `case` header** — blank lines and inline comments survive into the output, inside `def`, `class`, `for`, `while`, `if`, fields and method bodies alike. Two placements do not, on both backends: a comment on the `case` line itself is dropped, and one on a `type ... is enum` line is relocated to the last generated member.
- **A plain named type is an alias**: `type Velocity_T is float` and `type Distance_T is float` mix freely. Write `type Velocity_T is distinct float` where mixing would be a bug. Subranges are bounds-checked on Nim only; on Python a range is a plain `int`.
- **`%` on a negative operand differs between the backends**: Python's result has the divisor's sign (`-7 % 3` is 2, `-30.0 % 360` is 330.0); on Nim `%` is `mod`, which keeps the dividend's (-1, -30.0), and a float `%` is `mod`, which needs `nimport math` (the transpiler then imports just that operator). For a bearing or any wrap-around write it out: `x - period * floor(x / period)` (floats), and see `modulo` in `EXAMPLES/MAP_UTILS/map_utils.ady`.
- **Ticks do not chain** — `Stage_T'First'Image` is a parse error; bind the intermediate value first. Ticks on field accesses and subscripts are fine.
- **Case subject must be structural** — `case state:` where `state` is a tuple variable emits Nim's native `case`, which rejects non-ordinal selectors. Destructure with `let (a, b) = state` first, then `case (a, b):`.
- **Global parser state** — `ParserState` is a class-level singleton; call `ParserState.reset()` between independent parse runs. Thread-unsafe for concurrent parses.
- **`nimport` stdlib coverage** — some Python builtins (`PriorityQueue`, `FifoQueue`, `ANY`) live in a local `stdlib.nim` shim (`nimport stdlib`).
- **`$name` is always a shell variable** — `$HOME`, `$1`, etc. are tokenised as environment/CLI lookups even outside `shell:` blocks. Use explicit `getEnv("NAME")` in Nim-only contexts if needed.
