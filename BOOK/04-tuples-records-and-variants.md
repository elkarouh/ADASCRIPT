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
`EXAMPLES/INTERACTIVE/lispy.ady` represents environments as a record
containing a dict and a reference to the enclosing scope:

```python
type Env_T is record:
    bindings: {str}Val_T
    outer:    Env_T
```

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
representation is one tagged record. Here the author chose the *flat* record
style — every field present, the `kind` enum saying which ones are
meaningful — because the interpreter targets both backends and manipulates
values generically:

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

type Val_T is record:
    kind:      Val_Kind_T
    num:       float
    sym:       str
    flag:      bool
    items:     []Val_T
    parms:     []str
    rest_parm: str       # non-empty -> variadic: extra args bound here
    body:      Val_T
    env:       Env_T
```

Everything downstream dispatches on `kind` — with `case`/`when` (next
chapter) or with structural patterns like `Val_T(kind=VSym, sym=name)`.

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

## 4.4 Type aliases

The humblest `type` declaration is an alias, and the examples use them
liberally to give domain names to structural types:

```python
type Node_T     is str                       # graph.ady (tutorial variant)
type Distance_T is float                     # dijkstra.ady
type Graph_T    is {Node_T}{Node_T}Distance_T
type Result_T   is [][]str                   # phonecode.ady
type Coord_T    is (row: Row_T, col: Col_T)  # qlearning.ady — inline named tuple
```

Aliases cost nothing on either backend and pay for themselves the first time
a signature like `def dijkstra(graph: Graph_T, start: Node_T)` replaces a
nest of raw braces.

## 4.5 Choosing between them

| You need | Use |
|----------|-----|
| A small immutable value: a point, a queue entry, a (state, cost) pair | named tuple |
| Mutable fields, defaults, piecemeal construction | record |
| "One of N shapes" with per-shape fields, checked in Nim | variant record |
| A domain name for an existing structure | alias |

A practical note from the examples: search/DP state must be **hashable and
comparable** (it goes into `visited` sets and priority queues), which is why
`test_shortest_path.ady` and `state_search.ady` use tuples for state
throughout, and records only for bulkier data that stays put.

---

*Next: [Chapter 5 — Pattern Matching](05-pattern-matching.md)*
