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

Declarations without an initial value are legal; the Nim backend
zero-initialises them and the Python backend emits a bare annotation:

```python
var result: []int          # empty seq[int] / list[int]
var visited: {}Node_T      # empty set — see dijkstra.ady
```

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

| Adascript | Python | Nim |
|-----------|--------|-----|
| `[]T` | `list[T]` | `seq[T]` |
| `[N]T` | `tuple[T, ...]` | `array[N, T]` |
| `[*]T` | `Sequence[T]` | `openArray[T]` |
| `[E]T` | `dict[E, T]` | `array[E, T]` (enum-indexed) |
| `{K}V` | `dict[K, V]` | `Table[K, V]` |
| `{}T` | `set[T]` | `HashSet[T]` or `set[T]` |
| `?T` | `T \| None` | `Option[T]` |
| `(T, U)` | `tuple[T, U]` | `(T, U)` |
| `[(T, U)]R` | `Callable[[T, U], R]` | `proc(a0: T, a1: U): R` |

The notations compose freely. `EXAMPLES/graph.ady` models a graph as a type
alias built from two of them:

```python
type Node_T is enum A, B, C, D, E, F
type Graph_T is {Node_T}[]Node_T
graph: Graph_T = {A: [B, C], B: [C, D], C: [D], D: [C], E: [F], F: [C]}
```

`{Node_T}[]Node_T` — a dict mapping each node to a list of neighbours — would
be `dict[Node_T, list[Node_T]]` in Python and `Table[Node_T, seq[Node_T]]`
in Nim. `EXAMPLES/dijkstra.ady` goes one step further with a dict of dicts:

```python
type Distance_T is float
type Graph_T is {Node_T}{Node_T}Distance_T

graph : Graph_T = {A:{B:1.0, C:4.0}, B: {C:2.0, D:5.0}, C: {D:1.0}, D: {:}}
```

Even function types follow the pattern. In `EXAMPLES/geo_server.ady`, a
geometric region is defined by an optional predicate from `Point` to `bool`:

```python
class Region:
    var _predicate: ?[(Point,)]bool
```

Read it inside-out: `[(Point,)]bool` is "callable taking a `Point`, returning
`bool`", and the leading `?` makes it optional.

## 2.3 Empty collection literals

Python's `{}` is famously ambiguous — it is an empty *dict*, and there is no
literal for an empty set. Adascript fixes this with a dedicated empty-dict
literal:

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

---

*Next: [Chapter 3 — Enums, Sets, and Tick Attributes](03-enums-sets-and-tick-attributes.md)*
