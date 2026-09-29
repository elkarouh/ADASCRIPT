# Chapter 4 — Tuples, Records, and Variant Records

Adascript offers three aggregate kinds, in increasing weight: **named
tuples** (structural, value-semantics), **records** (nominal, dataclass-like)
and **variant records** (Ada-style discriminated unions). This chapter shows
where each earns its keep in the examples.

## 4.1 Named tuples

Declared with `type ... is tuple:` and a body of annotated fields:

```python
type Point is tuple:
    x: float
    y: float
```

Python output is a `NamedTuple` subclass; Nim output is a structural tuple.
Construction uses `(field: value)` syntax — note the colon, not `=`:

```python
p = Point(x: 1.0, y: 2.5)
```

`EXAMPLES/dijkstra.ady` uses a named tuple as its priority-queue element, so
ordering comes for free from the first field:

```python
type Neighbour_T is tuple:
    distance: Distance_T
    neighbor: Node_T

queue : PriorityQueue[Neighbour_T] = [(0.0, start)]
while queue:
    current_dist, node = queue.pop()
    ...
    queue.push((new_dist, neighbor))
```

Named-tuple literals work anywhere an expression does — inside collections,
as arguments, in queue pushes. `EXAMPLES/test_shortest_path.ady` initialises
a capital-budgeting search with one:

```python
for solution in op4.longest_path((stage:STAGE1, budget:Cost_T(CAPITAL))):
    print(solution)
```

Tuples are the natural *state* type for search and DP problems — small,
copyable, comparable, hashable. The same file's knapsack example:

```python
type State_T is tuple:
  stage: Stage_T
  remaining: Natural
type Decision_T is tuple:
  stage: Stage_T
  quantity: Natural
type Choice_T is tuple:
  weight : int
  benefit: int

var ITEMS: [Stage_T]Choice_T = [
  STAGE1: (weight:2, benefit:65),
  STAGE2: (weight:3, benefit:80),
  STAGE3: (weight:1, benefit:30)
]
```

Access fields by name (`state.stage`) or destructure:

```python
let (stage, remaining) = current_state
```

## 4.2 Records

Records are nominal types with mutable fields — `@dataclass` in Python
output, `object` in Nim output:

```python
type Person is record:
    name: str
    age:  int
```

Fields can carry defaults. `EXAMPLES/argparse.ady` collects parsed
command-line options into a record whose defaults *are* the program's
defaults:

```python
type Command_Line_Arguments_T is record:
    inputFile : str = ""
    outputFile : str = "output.txt"
    verbose   : bool = False
    count     : Natural = 1
    free_args : []str
```

The parser then simply declares `var res : Command_Line_Arguments_T` and
mutates fields as flags arrive — no constructor boilerplate. Compare a tuple:
you *could* not do this, because tuples are immutable values; records are the
right tool the moment fields are assigned piecemeal.

Records nest happily with the collection notations. The Scheme interpreter
`TOOLS/LISPY/lispy.ady` represents an environment as a *class*
(chapter 9) holding a dict and a reference to the enclosing scope, with
`define`, `assign` and `lookup` as its methods:

```python
class Env:
    var bindings: {str}Val_T
    var outer:    ?Env
```

An ordinary record can also be the failure side of a function's return
type, marked `!` there: `-> int | !Failure_T` returns either an int or a
Failure_T saying why there is none. Section 10.12 is how to write code in
that style.

## 4.3 Variant records — the discriminated union

When a type is "one of several shapes", Ada and Nim use a record whose field
set depends on an enum *discriminant*. Adascript adopts the Ada syntax:

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

Nim output is a native variant object (accessing `Width` on a `Circle` is a
runtime error); Python output is a flattened dataclass with `None` defaults
for the fields of inactive branches.

The heavyweight real-world use is `lispy.ady`, whose entire value
representation is one variant record. Each kind carries only the fields it
has, so reading the number of a symbol is not something a program can say:

```python
type Val_Kind_T is enum:
    VNum        # number literal
    VSym        # symbol / identifier
    VStr        # string literal
    VBool       # boolean
    VNil        # the empty value
    VList       # cons list
    VLambda     # user-defined closure
    VBuiltin    # built-in primitive proc

type Val_T (kind: Val_Kind_T) is record:
    case kind is
        when VNum:
            num:   float
        when VSym:
            sym:   str
        when VStr:
            text:  str
        when VBool:
            flag:  bool
        when VNil:
            unit:  bool       # carries nothing; a variant needs a field
        when VList:
            items: []Val_T
        when VLambda:
            lam:   Lambda     # a class: a record cannot hold itself
        when VBuiltin:
            name:  str
```

On Nim a variant is a value type, so a closure, which holds a `Val_T` (its
body) that would in turn hold the closure, is a class marked `@virtual`;
that makes it a reference, and the cycle is broken.

Everything downstream dispatches on `kind` — with `case`/`when` (next
chapter) or with structural patterns.

Naming the kind twice, in `Val_T(kind=VSym, sym=name)`, says nothing the
second time, so the kind alone is a *bare literal*: `VSym(name)` builds a
symbol and matches one, `VNum(3.0)` a number, and `VNil()` a kind that
carries nothing (declared `when VNil: pass`). The arguments fill the fields
of that kind in the order they were declared, or name them. Without
parentheses `VNil` is still the enum member, so `x.kind == VNil` reads as
it always did. `lispy.ady` is written this way, and its special-form
patterns read `when [VSym("if"), test, consequence, alternative]:`.

Truthiness, Scheme-style, becomes a three-line method:

```python
def is_true(self: Val_T) -> bool:
    case self.kind:
        when VBool:
            self.flag
        when VNil:
            False
        when others:
            True
```

## 4.4 Unions — one of several types

A variant record names its shapes and gives each its fields. When the shapes
are types that already exist, a *union* says the same thing in one line:
`int | float` holds an int or a float, and the value itself says which.
`EXAMPLES/test_union.ady` is the spec:

```python
def compute(n: int) -> int | float:
    if n % 2 == 0:
        return n // 2              # an int
    return n / 2                   # a float

for n in [4, 5]:
    let x: int | float = compute(n)
    case x:
        when int:
            print f"int {x + 1}"
        when float:
            print f"float {x * 2.0}"
```

What is assigned or returned becomes the member its type names — there is
nothing to wrap. `case x:` gives a branch per member, and inside each branch
`x` *is* that member: `x + 1` is int arithmetic, `x * 2.0` float. The case
must name every member or say `when others:`, as one over an enum must.
`x is int` asks the same question in an `if`, and narrows `x` the same way —
in the `else` of a two-member union, to the other one:

```python
let h: int | float = compute(7)
if h is int:
    print "an int"
else:
    print f"a float, {h}"          # the other member: h is the float here
```

A union can have any number of members — `int | str | float` — and a name of
its own, which then means exactly what it names:

```python
type Number_T is int | float
```

Two members of one union must be things a running program can tell apart:
on the Python backend the value *is* the member, and its class is all that
says which, so `[]int | []str` is refused, and so is `int | bool` (a bool is
an int to Python). Make one of them a record of its own. Nim holds a union
as stdlib.nim's `OneOf2[int, float]`, a variant object much like 4.3's.

Two members are special. `T | None` is `?T` — Chapter 10 — and a member that
is a *failure* record makes the union a value-or-failure, which a `do:` block
can chain (10.12). A union has at most one failure member.

## 4.5 Type aliases

The humblest `type` declaration is an alias, and the examples use them
liberally to give domain names to structural types:

```python
type Node_T     is str                       # graph.ady (tutorial variant)
type Distance_T is float                     # dijkstra.ady
type Graph_T    is {Node_T}[]Neighbour_T     # dijkstra.ady, adjacency list
type Result_T   is [][]str                   # phonecode.ady
type Coord_T    is (row: Row_T, col: Col_T)  # qlearning.ady — inline named tuple
```

Aliases cost nothing on either backend and pay for themselves the first time
a signature like `def dijkstra(graph: Graph_T, start: Node_T)` replaces a
nest of raw braces.

## 4.6 Choosing between them

| You need | Use |
|----------|-----|
| A small immutable value: a point, a queue entry, a (state, cost) pair | named tuple |
| Mutable fields, defaults, piecemeal construction | record |
| "One of N shapes" with per-shape fields, checked in Nim | variant record |
| A value that is one of a few existing types | union, `int \| float` |
| A domain name for an existing structure | alias |

A practical note from the examples: search/DP state must be **hashable and
comparable** (it goes into `visited` sets and priority queues), which is why
`test_shortest_path.ady` and `state_search.ady` use tuples for state
throughout, and records only for bulkier data that stays put.

---

*Next: [Chapter 5 — Pattern Matching](05-pattern-matching.md)*
