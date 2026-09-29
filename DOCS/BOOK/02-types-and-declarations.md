# Chapter 2 — Types, Declarations, and Annotations

## 2.1 var, let, const

Python has one way to bind a name. Adascript, following Nim, has three, and
they document intent while giving the Nim backend real guarantees:

```python
var   counter: int   = 0        # mutable variable
let   name:    str   = "Alice"  # immutable binding
const MAX:     int   = 1_000    # compile-time constant
```

`EXAMPLES/prisoners.ady` — a simulation of the 100-prisoners problem — opens
with a block of constants that read like a problem statement:

```python
const NUM_PRISONERS : Natural = 100
const NUM_BOXES     : Natural = 100
const MAX_OPEN      : Natural = 50
const TRIALS        : Natural = 1000
```

A declaration without an initial value is legal, and both backends give it
the empty value of its type — `seq[int]` and `list[int] = []`, and so on:

```python
var result: []int          # empty seq[int] / list[int]
var visited: {}Node_T      # empty set — see dijkstra.ady
```

The keyword is what makes it a declaration. Dropping it leaves `result:
[]int`, which is Python's *annotation*: it records a type and binds nothing,
so reading the name before assigning to it is an error on both backends.
That is deliberate — a valid Python file has to keep its meaning — and the
type is not wasted, since the first assignment picks it up: `count: int`
then `count = 5` declares `count` as an `int`. Inside a record or class body
the bare form is the field spelling and does declare.

Tuple unpacking works in three spellings:

```python
let (x, y) = point          # explicit immutable destructuring
var (a, b) = (1, 2)         # explicit mutable destructuring
a, b = some_func()          # implicit: treated as let (a, b) = ...
```

## 2.2 Left-to-right type annotations

Adascript replaces Python's `typing` module with a compact, left-to-right
notation where the container kind is a *prefix*. `[]int` reads "list of
int"; `{str}int` reads "dict from str to int".

That reading is right as far as it goes, but it makes the notation look like
a list of separate spellings to memorise. It is one idea, and two
independent questions settle which form you want.

The first is *is it ordered?*, which is the shape of the brackets. `[…]` is
ordered: there is a first, a next and a last, and the container is held in
that order. `{…}` is unordered: there is no order at all.

The second is *is it keyed?*, which is whether anything sits inside them.
Nothing inside — `[]T`, `{}T` — is a **collection** of `T`. A type inside —
`[K]T`, `{K}V` — is a **mapping**, from the type in the brackets to the one
that follows.

Four combinations, four forms, and each corner is the everyday name of the
thing:

|                | ordered `[…]`                    | unordered `{…}` |
|----------------|----------------------------------|-----------------|
| **collection** | `[]T` — a list                   | `{}T` — a set   |
| **mapping**    | `[K]T` — keys in order           | `{K}V` — a dict |

The two questions meet in one place: which order a `[…]` mapping has
depends on its key. With a **finite ordinal type** — an enum, `bool`,
`char`, an integer subrange — every key and its place are known at compile
time, and `[O]T` is an array indexed by `O`. With any other key — `str`,
`int`, a class — the keys cannot be known in advance, so they are held in
the order they are **inserted**: `[str]float` is an `OrderedTable` on Nim
and a dict on Python. Either way `[…]` means an ordered collection. Between
`{…}` any hashable type will do, and no order is promised.

The row above the line is not really a separate kind, which is why the four
line up so neatly: a collection is a mapping whose key it supplies itself. A
list maps its positions to its elements; a set maps its elements to
in-or-out, its characteristic function. That is why `xs[i]` and `x in s` are
both lookups, and why a set cannot hold the same element twice — a key is
present or absent, with no third state for "present twice". The four names
in the table are the level to think at day to day; this is why they hold
together.

It also settles what a loop gives you. A mapping has two halves, and
`for x in c` — and `x in c`, which asks the same question — gives the half
that is **not known in advance**, because that half is the information.

- When the keys are known in advance, the values are the news. `[Color]int`
  has exactly the keys `RED, GREEN, BLUE`, fixed by its type; listing them
  would tell you nothing. So `for x in score` gives the scores, and
  `x in score` asks whether some colour has that score. A list and a fixed
  array are the same case: their keys are positions, known from the length.
- When the keys are not known in advance, the keys are the news. A
  `{str}int` holds whichever words happened to arrive: `for w in counts`
  gives the words, `w in counts` asks whether a word occurred, and its
  count is reached through it, `counts[w]`. A `[str]float` is the same, and
  gives its keys in the order they arrived.
- A set is the limiting case. Its value half — present or absent — says
  nothing, so its elements, which are its keys, are all there is to give.

| | keys known in advance? | `for x in c`, `x in c` |
|---|---|---|
| `[]T`, `[N]T`, `[E]T`, `[lo..hi]T` | yes: positions, or the domain | the values |
| `[str]V`, `[(int, int)]V`, `{K}V` | no | the keys |
| `{}T` | no: the elements are the keys | the elements |

The brackets say whether there is an order; the key type says what a loop
gives. `.keys()`, `.values()` and `.items()` ask for the other half, or
both, and `enumerate(c)` gives `(position, element)` for a list and
`(key, value)` for every mapping.

One consequence is worth drawing out, because it removes a form from the
list rather than adding one: the fixed-size array is not special. `[10]int`
is `[O]T` whose ordinal type happens to be a subrange — a length `N` is
shorthand for `0 .. N-1`. So `[10]int` and `[0..9]int` are the same type,
not two similar ones. Nim agrees literally: there,
`array[10, int] is array[0..9, int]` evaluates to `true`, and a value of one
spelling assigns to the other. The key can equally be written out, named
(`type Idx is 0 .. 4`, then `[Idx]int`), or be any other ordinal —
`[bool]str`, `[Priority]int`, `[char]int`.

| Adascript | Python | Nim |
|-----------|--------|-----|
| `[]T` | `list[T]` | `seq[T]` |
| `[N]T` | `tuple[T, ...]` | `array[N, T]` |
| `[*]T` | `Sequence[T]` | `openArray[T]` |
| `[E]T` | `dict[E, T]` | `array[E, T]` (enum-indexed) |
| `[K]V` | `dict[K, V]` | `OrderedTable[K, V]` (K not a finite ordinal) |
| `{K}V` | `dict[K, V]` | `Table[K, V]` |
| `{}T` | `set[T]` | `HashSet[T]` or `set[T]` |
| `?T` | `T \| None` | `Option[T]` |
| `(T, U)` | `tuple[T, U]` | `(T, U)` |
| `(T, U) -> R` | `Callable[[T, U], R]` | `proc(a0: T, a1: U): R` |

`?T` and `(T, U)` are not containers and sit outside the scheme. Nor does
the function type, which is written the way a `def` writes its signature:
the parameter types in parentheses, an arrow, the result. A pure function is
a mapping too, but not one a `{…}` could spell: `{(int, int)}float` is a
dict keyed by a tuple — iterable, countable, writable — where a function can
only be called. The declaration has to say which it is, and the arrow does.

"Unordered" is a portability rule rather than a mnemonic, because the two
backends really do disagree. Iterating the same `{str}int` gives insertion
order on the Python backend and hash order on Nim: for keys inserted
`zebra, apple, mango, kiwi, banana`, Python returns them in that order and
Nim returns `zebra, kiwi, apple, mango, banana`. Sets diverge the same way.
A program that iterates a `{…}` type and depends on what comes out first is
therefore not portable between the backends — sort the keys, or use an
ordered form.

The notations compose freely. `EXAMPLES/graph.ady` models a graph as a type
alias built from two of them:

```python
type Node_T is enum A, B, C, D, E, F
type Graph_T is {Node_T}[]Node_T
graph: Graph_T = {A: [B, C], B: [C, D], C: [D], D: [C], E: [F], F: [C]}
```

`{Node_T}[]Node_T` — a dict mapping each node to a list of neighbours — would
be `dict[Node_T, list[Node_T]]` in Python and `Table[Node_T, seq[Node_T]]`
in Nim. `EXAMPLES/dijkstra.ady` maps each node to a list of tuples — an
adjacency list, weights included:

```python
type Distance_T is float
type Neighbour_T is tuple:
    distance: Distance_T
    neighbor: Node_T
type Graph_T is {Node_T}[]Neighbour_T

graph : Graph_T = {A: [(1.0, B), (4.0, C)], B: [(2.0, C), (5.0, D)], C: [(1.0, D)], D: []}
```

Three levels of the notation compose in that one declaration: a `{…}`
mapping, whose values are a `[…]` collection, of a named tuple.

Even function types follow the pattern. In `EXAMPLES/geo_server.ady`, a
geometric region is defined by an optional predicate from `Point` to `bool`:

```python
class Region:
    var _predicate: ?(Point) -> bool
```

`(Point) -> bool` is "a function taking a `Point`, returning `bool`", and
the leading `?` makes the function optional. The result after the arrow is
a whole type, as in a `def`, so `(Point) -> ?bool` would instead be a
function whose *result* is optional.

### Reading nested arrows

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

## 2.3 Empty collection literals

Python's `{}` is famously ambiguous — it is an empty *dict*, and there is no
literal for an empty set. Adascript fixes this with a dedicated empty-dict
literal, and the two follow the split above: the colon of a `key: value`
pair marks the **mapping**, and its absence the **collection**.

| Literal | Meaning | Python output | Nim output |
|---------|---------|---------------|------------|
| `{:}` | empty dict | `{}` | `initTable[K, V]()` |
| `{}` | empty set | `set()` | `initHashSet[T]()` or `{}` |

You can see both in the `dijkstra.ady` graph literal above (`D: {:}` — node D
has no outgoing edges) and in `sudoku.ady`, which threads `{:}` through its
whole constraint-propagation core as the "contradiction" sentinel:

```python
def assign(values: {str}str, s: str, d: str) -> {str}str:
    """Assign d to s by eliminating all other digits. Return False on contradiction."""
    var other_digits: str = values[s].replace(d, "")
    for d2 in other_digits:
        values = eliminate(values, s, str(d2))
        if not values:
            return {:}
    return values
```

For sets, the declared element type decides the Nim representation: ordinal
types (`bool`, `char`, small ints, enums) become Nim's zero-allocation
bitset `set[T]`; everything else becomes a `HashSet`.

## 2.4 Subrange types

A subrange type constrains a base type to an interval, exactly as in Ada and
Pascal:

```python
type SmallInt  is 0 .. 255     # values 0–255, inclusive
type Index     is 0 ..< 10     # values 0–9
```

`prisoners.ady` derives its domain types from its constants:

```python
type Prisoner_T is int range 1..NUM_PRISONERS
type Box_T      is int range 1..NUM_BOXES
```

A subrange is an ordinal type, so it is also a key type: `[Box_T]Prisoner_T`
is an array with one slot per box, indexed by box number rather than by a
position that happens to line up with one. This is the other end of the
observation in §2.2 — `[10]int` is shorthand for `[0..9]int` — and it is
what makes the fixed-size array and the enum-indexed array the same
construct with different ordinals in the brackets.

and then uses `Prisoner_T` both as an array index type and as a loop range —
the Pascal/Ada "base minimum" the README insists on:

```python
def make_boxes() -> [Prisoner_T]Box_T:
    var boxes: [Prisoner_T]Box_T
    for i in Prisoner_T'Range:
        boxes[i] = i
    boxes'Shuffle
```

Float subranges get Ada-style semantics: the constraint is checked after
**every assignment** to a variable of the type. From
`EXAMPLES/dp/jacks.ady` (Jack's Car Rental, policy iteration):

```python
type Cars_T     is 0..20
type Reward_T   is float
type Prob_T     is float range 0.0..1.0
type Discount_T is float range 0.0..1.0
```

In Nim output an assignment to a `Prob_T` variable is followed by an
`assert p >= 0.0 and p <= 1.0` — probability bugs fail at the assignment
site, not three functions later. In Python output subranges are plain
aliases; the checking costs you nothing on the prototyping target.

`spell.ady` (Norvig's spelling corrector) uses the same trick for word
probabilities:

```python
type Prob_T is float range 0..1

def P(word: str) -> Prob_T:
    0 if word not in WORDS else WORDS[word]/N
```

## 2.5 Open arrays: `[*]T`

`[*]T` maps to Nim's `openArray[T]` — a read-only *view* that a caller can
satisfy with either a dynamic `[]T` or a fixed-size `[N]T`, without copies
or conversions. It is only valid in parameter and return annotations.
`EXAMPLES/openarray_demo.ady` is the dedicated exercise:

```python
def sum_f(xs: [*]float) -> float:
    var s: float = 0.0
    for x in xs:
        s = s + x
    return s

def dot(a: [*]float, b: [*]float) -> float:
    """Dot product — both arguments may be seq or fixed array, independently."""
    var s: float = 0.0
    for i in 0..<len(a):
        s = s + a[i] * b[i]
    return s

var readings: []float = [3.1, 1.4, 2.7, 0.9, 4.2, 1.6]   # a seq

const N: int = 6
var baseline: [N]float = [3.0, 1.0, 2.0, 1.0, 4.0, 1.0]  # a fixed array

print(f"dot(readings, baseline) = {dot(readings, baseline):.2f}")
print(f"dot(baseline, readings) = {dot(baseline, readings):.2f}")
```

Write library functions against `[*]T` whenever they only read their
argument, and both kinds of caller are served by one instantiation.

## 2.6 Predefined subtypes: Natural and Positive

Two Ada-inherited integer subtypes appear all over the examples and deserve
an early mention: `Natural` (0 and up) and `Positive` (1 and up). They map
to Nim's identically-named types and to `int` in Python. Use them the way
the examples do — as documentation-with-teeth for counters and sizes:

```python
# awk_example.ady
var NR        : Natural = 0     # record number
var NF        : Natural = 0     # field count

# lv.ady
def align(length: Positive, s: str) -> str:
    return s.alignLeft(length)
```

## 2.7 Distinct types and units

A named scalar type is an alias. `type Velocity_T is float` puts the unit in
the signature, but a `Distance_T` given a `Velocity_T` still compiles. Ada's
answer is a *derived* type, and Adascript spells it `distinct`:

```python
type Distance_T is distinct float     # nautical miles
type Duration_T is distinct float     # hours

var d: Distance_T = 600.0
d += 10.0
let t: Duration_T = Duration_T(2.0)   # Duration_T(x) in, float(t) out
let wrong: Duration_T = d             # refused, on both backends
```

A distinct type keeps its base type's operations, closed over itself —
`Distance_T + Distance_T` is a `Distance_T` — and mixes with nothing else.

A literal is the exception, as it is in Ada, where a literal belongs to a
*universal* type until its context gives it one. `600.0` given to a
`Distance_T` declaration, assignment, return, argument or record field, or
written beside one with `+`, `-` or a comparison, is a `Distance_T`. A
`float` *variable* is not a literal, and needs the conversion.

### Scaling, and units made from units

Multiplying is where quantities part company with types. A product is not in
the unit of its factors — knots times knots is not knots — so `*` and `/`
mean something different from `+`:

- a unit times or over a **plain number** is that unit: `d * 2.0`,
  `2.0 * d`, `d / 4.0`. The number stays a number;
- two of one unit **divided** are a plain `float`, a ratio;
- two of one unit **multiplied**, or two different units multiplied or
  divided, are refused — unless you have said what they make.

Saying so is a declaration. `type C is A / B` defines the operators between
A, B and C:

```python
type Velocity_T is Distance_T / Duration_T    # knots

def travelled(v: Velocity_T, t: Duration_T) -> Distance_T:
    return v * t                      # Velocity x Duration is a Distance

def eta(d: Distance_T, v: Velocity_T) -> Duration_T:
    return d / v                      # Distance / Velocity is a Duration

let v: Velocity_T = d / t             # Distance / Duration is a Velocity
```

A Distance over a Duration is a Velocity, and from that follow the other
three: Velocity times Duration, in either order, is a Distance, and Distance
over Velocity is a Duration. `type C is A * B` runs the other way —
`type Area_T is Length_T * Length_T`, `type Total_T is Cents_T * Qty_T` — and
a derived unit can be an operand of the next, `type Accel_T is Velocity_T /
Duration_T`. Everything else between the units does not exist, so `d * t`,
`v + d` and `1.0 / t` do not compile: there is no "mile-hour" until you
declare one.

The operands must be distinct, and of one kind: `float` for a quotient,
`float` or `int` for a product, since a quotient of ints is not an int. Money
is naturally `distinct int` in cents, so `price * 3` scales it, and
`price * qty` needs a total unit to say what it is.

On Nim each unit is `distinct float` with the operations borrowed and one
small proc per relation, so the compiler checks every use at no run-time
cost. The Python backend makes it a subclass of `float` and works out the
unit of arithmetic over typed names, refusing what it can see — `v * 2.0 +
d` is a Velocity plus a Distance — while a wrong argument is caught by
building for Nim. Chapter 12 has the general rule.

This is deliberately less than a units library, which tracks the exponent of
every base unit for you. Here every combination you use has a name — a
reader can search for it, and it appears in the signature — and the
compiler's messages talk about `Velocity_T`, not about exponents.

Use `distinct` for units and for identifiers of different things that share
a representation. Keep an alias where the value should mix with its base.

## 2.8 String literals

The literal forms are Python's, and they mean what they do in Python. The
quote character is not part of the type: `"..."` and `'...'` both make a
`str`, so the one to reach for is whichever lets the other sit inside
without an escape.

```python
# EXAMPLES/DOC/string_snippets.ady
let double: str = "she said hello"
let single: str = 'she said "hello"'
```

A `char` is its own type rather than a one-character `str`, and it is the
**declared type** that decides which a single-character literal is — the
same `'x'` is a `str` where a `str` is declared:

```python
# EXAMPLES/DOC/string_snippets.ady
let initial: char = 'x'
let one_char: str = 'x'
```

| Form | Meaning | Python output | Nim output |
|------|---------|---------------|------------|
| `"a"` / `'a'` | string | `"a"` / `'a'` | `"a"` |
| `'x'` declared `char` | single character | `'x'` (a `str`) | `'x'` (a `char`) |
| `"""…"""` | spans lines | `"""…"""` | `"…\n…"` |
| `r"\d+"` | raw — backslashes survive | `r"\d+"` | `r"\d+"` |
| `f"{x}"` | interpolation | `f"{x}"` | `fmt"{x}"` |

Triple quotes span lines, and a raw string keeps its backslashes — which is
what a regex wants, since otherwise `\d` would be an escape for the compiler
to interpret rather than two characters to match with:

```python
# EXAMPLES/DOC/string_snippets.ady
let banner: str = """first
second"""
```

f-strings interpolate an expression, and a format spec after `:` aligns and
pads exactly as in Python:

```python
# EXAMPLES/DOC/string_snippets.ady
let n: Natural = 42
assert f"n is {n}" == "n is 42"
assert f"{n * 2}" == "84"
# A format spec after ':' aligns and pads, as in Python.
assert f"[{n:>5}]" == "[   42]"
```

### Adjacent literals join

Writing two literals next to each other concatenates them, as in Python and
C. There is no operator, and nothing happens at run time: the pieces are one
literal by the time either backend sees them.

```python
# EXAMPLES/DOC/string_snippets.ady
assert "ab" == "a" "b"
```

A piece may be an f-string, and the kinds mix freely within one run. What
holds a run together is the juxtaposition, not what each piece happens to be:

```python
# EXAMPLES/DOC/string_snippets.ady
assert f"x={n} " "then plain " f"and {n * 2}" == "x=42 then plain and 84"
```

The reason to want it is a long message that has to be readable in the source
as well as in the output. Parentheses let the run break across lines, and each
line stays inside the margin:

```python
# EXAMPLES/DOC/string_snippets.ady
let report: str = (f"{n} item(s) processed, "
                   "none rejected, "
                   f"{n * 2} checks run")
```

Nim has no juxtaposition rule of its own, so the run is emitted as a `&`
chain — `fmt"…" & "…" & fmt"…"`. Python takes it verbatim, since the rule is
Python's to begin with. Either way the result is the same string, and the
concatenation of the constant pieces costs nothing at run time.

---

*Next: [Chapter 3 — Enums, Sets, and Tick Attributes](03-enums-sets-and-tick-attributes.md)*
