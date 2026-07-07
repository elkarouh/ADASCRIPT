# Chapter 9 — Classes, Generics, and Inheritance

Adascript classes are Python classes with `var`-declared fields. The
transpiler does substantial work behind the scenes so that one class
definition produces idiomatic code on both targets: Python gets a normal
class; Nim gets an `object` (or `ref object`) plus free `proc`s, with
mutability, constructors and generic parameters inferred.

## 9.1 Fields with `var`, and inline defaults

Fields are declared in the class body with `var`/`let`/`const`, visually
distinct from method-local assignment. From `phonecode.ady`:

```python
class TrieNode:
    var children: [Digit_T]TrieNode   # array indexed by digit enum
    var words: []str

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

Field declarations can carry defaults, which the transpiler injects into the
generated constructor. `__init__` then only sets what varies per instance —
or disappears entirely. `EXAMPLES/test_awk.ady`:

```python
nimport awk

class AwkProcessor(AwkBase):
    var counts : [Severity_T]int = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]
    # no __init__ at all — a forwarding constructor calling AwkBase's
    # initialiser is generated automatically
```

## 9.2 Mutable `self`, detected for you

Nim distinguishes procs that mutate their receiver (`self: var T`). You
never annotate this: the transpiler detects field assignment, `+=`,
`.add()`, indexed assignment, or calls to other mutating methods, and emits
`var` where needed.

```python
class Counter:
    var count: int = 0

    def increment(self):
        self.count += 1   # → proc increment(self: var Counter) in Nim
```

## 9.3 Dunder operators: callable objects and pipes

Python operator methods translate to Nim operators. The showpiece is
`EXAMPLES/lv.ady`, which builds ANSI terminal styling from a class with
`__call__` and `__ror__`:

```python
class Style:
    var on: str
    var off: str
    def __init__(self, code: Natural):
        self.on = f"{prefix}{code}{suffix}"
        self.off = f"{prefix}0{suffix}"
    def __call__(self, *args: str) -> str:
        return "".join([f"{self.on}{arg}" for arg in args]) + self.off
    def __ror__(self, other: str) -> str:
        return self(other)

let bold: Style = Style(1)
let blue: Style = Style(34)
let bg_white: Style = Style(47)
```

`__call__` makes a `Style` callable (Nim: the experimental call operator,
enabled automatically); `__ror__` flips the pipe so plain strings flow
through styles left-to-right:

```python
return align(64, f"{login_name}.{view | inverted | bold | blue | bg_white}")
```

The `|` operator is context-sensitive in Nim output: between custom-typed
operands it stays `|`; between integers it becomes `or`.

`geo_server.ady` uses `__and__`, `__or__`, `__invert__` and `__contains__`
to build a region algebra where composition looks like the geometry text:

```python
# An engageability annulus: outside the inner circle, inside the outer
Annulus = ~Circle(center, inner) & Circle(center, outer)
...
if track_position in Annulus:
    ...
```

## 9.4 Inheritance and `@virtual`

Standard Python inheritance works, including `super().__init__(...)`.
Within one file, plain classes suffice. The `@virtual` decorator exists for
one purpose: **cross-module dispatch**. It makes the Nim backend emit
`ref object of RootObj` so subclasses in *other* files dispatch dynamically.

The `awk` stdlib base class is the working illustration. `TO_NIM/awk.ady`
ships a `@virtual class AwkBase` implementing the AWK machinery (`FS`,
`OFS`, `NR`, `NF`, `read_record`, `run`); user programs `nimport awk` and
override the hooks. `EXAMPLES/test_awk.ady`:

```python
class AwkProcessor(AwkBase):
    var counts : [Severity_T]int = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]

    def classify_record(self) -> Severity_T:
        case self.line:
            when /error/i:      return ERROR
            when /warn/i:       return WARN
            when /info|debug/i: return INFO
            when others:        return OTHER

    def process_record(self):
        let F: []str = self.Fields
        let sev: Severity_T = self.classify_record()
        ...

    def begin(self):  print "--- awk report ---"
    def finish(self): ...   # summary
```

Compare with the procedural `awk_example.ady` doing the same job with
globals: the OO version is what you graduate to when several record
processors share the skeleton.

## 9.5 Generic classes

Type parameters go in brackets after the class name and thread through all
generated procs. The framework in `EXAMPLES/shortest_path.ady` is built on
two of them:

```python
@virtual
class Minimizer[S, D, C]:
    """
    Generic shortest-path / dynamic-programming minimiser.
    Define the state S, the decision D, and the cost type C.
    Override:
      - get_next_state(state, decision)   -> next state
      - get_next_decisions(state)         -> list of (decision, cost) pairs
      - get_heuristic_cost(state)         -> admissible heuristic (default 0)
      - cost_operator(accumulated, new)   -> how costs combine (default: addition)
      - is_end_state(state)               -> True when goal is reached
    """
    var offset: float
    var decision_path: []D
    var start_state: S

    def get_next_state(self, current_state: S, decision: D) -> S:
        raise NotImplementedError("Override get_next_state()")

    def get_next_decisions(self, current_state: S) -> [](D, C):
        raise NotImplementedError("Override get_next_decisions()")

    def get_heuristic_cost(self, current_state: S) -> float:
        0.0
    ...
```

A subclass instantiates the parameters and overrides the hooks — Dijkstra on
a ten-node graph is a dozen lines in `test_shortest_path.ady`:

```python
type State_T is enum a,b,c,d,e,f,g,h,i,j
type Cost_T is 0..100
type Decision_T is State_T

class ShortestGraph(Minimizer[State_T, Decision_T, Cost_T]):
    var G: {State_T}[]CostChoice_T = {
        a: [(b, 2), (c, 4), (d, 3)],
        b: [(e, 7), (f, 4), (g, 6)],
        ...
    }

    def get_next_state(self, current_state: State_T, decision: Decision_T) -> State_T:
        decision

    def get_next_decisions(self, curr_state: State_T) -> []CostChoice_T:
        self.G.get(curr_state, [])
```

Generic helper types ride along — the fringe element is itself generic:

```python
type Fringe_Element_T[S, C] is tuple:
    hcost:      C
    new_cost:   C
    node_idx:   int
    next_state: S
```

**Nim 2.x restriction:** generic *methods* on `ref object` hierarchies are
limited, so functions that would be generic methods can be written as
top-level functions taking `self` explicitly — UFCS keeps the call syntax:

```python
def longest_path(self: Optimizer[S, D, C], start_state: S, end_state: S,
                 max_path_length: int = 1000) -> (float, []D):
    ...
# call as op.longest_path(...) — Nim UFCS / Python method lookup both work
```

## 9.6 Classes inside functions, and ALL_CAPS globals

`test_shortest_path.ady` defines each example's types and classes *inside* a
function (`def example5(): ...`) to keep the file modular. The Nim backend
must hoist those class bodies to module scope — which means enclosing-function
locals are invisible to methods. The convention that bridges the gap:
**ALL_CAPS declarations are hoisted as globals** alongside the methods.

```python
def example5():
    const MAX_WEIGHT: Natural = 5
    var ITEMS: [Stage_T]Choice_T = [        # ALL_CAPS → hoisted, visible to methods
      STAGE1: (weight:2, benefit:65),
      STAGE2: (weight:3, benefit:80),
      STAGE3: (weight:1, benefit:30)
    ]

    class Knapsack(Maximizer[State_T, Decision_T, Revenue_T]):
        def get_next_decisions(self, current_state: State_T) -> [](Decision_T, Revenue_T):
            let (weight, benefit) = ITEMS[stage]     # accessible here
            ...
```

Lowercase locals stay inside the enclosing proc. If a method needs to read
it, shout it.

---

*Next: [Chapter 10 — Optional Types and the Maybe Monad](10-optionals.md)*
