# Chapter 8 — Functions, Closures, and Generators

Function definition is Python's `def`, with Adascript annotations and a few
Nim-inspired conveniences that the examples lean on constantly.

## 8.1 Basics, defaults, implicit return

```python
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
```

Two features remove ceremony:

**Implicit return.** If a function has a return-type annotation and its last
statement is a bare expression, that expression is the return value:

```python
def clamp(x: int, lo: int, hi: int) -> int:
    max(lo, min(x, hi))
```

The examples use this pervasively — recall `spell.ady`'s one-liners:

```python
def P(word: str) -> Prob_T:
    0 if word not in WORDS else WORDS[word]/N

def correction(word: str) -> str:
    max(candidates(word), key=P)
```

(`max` with a `key` function works on both backends; here the key *is* the
probability function `P`.) It also fires per-branch: each arm of an
`if`/`else` or `case` can end in a bare expression, as in `lispy.ady`'s
`is_true` (§4.3). `-> None` functions are exempt — their last expression
stays a statement.

**The `result` variable.** Nim's implicit accumulator is available:
`primes.ady` sets `result = True` and lets `break` fall out of the function
(§1.2), and `prisoners.ady`'s `make_boxes` ends with `boxes'Shuffle`, whose
in-place result is the return value. Use whichever of the two idioms reads
better; both avoid `return` noise in small functions.

**Default parameter values** behave as in Python. A recursive default from
`graph.ady`:

```python
def find_path(graph: Graph_T, start_node: Node_T, end_node: Node_T,
              path: []Node_T = []) -> ?[]Node_T:
    path = path + [start_node]
    if start_node == end_node:
        return path
    if start_node not in graph:
        return None
    for node in graph[start_node]:
        if node not in path:
            newpath : ?[]Node_T = find_path(graph, node, end_node, path)
            if newpath is not None:
              return newpath
    return None
```

Note that unlike Python, the `[]` default is safe — the Nim backend has
value semantics for seqs, and the function never mutates `path` in place
anyway (it rebinds `path + [start_node]`).

## 8.2 Nested functions and closures

Functions nest, and inner functions close over enclosing locals.
`phonecode.ady` uses a nested helper to keep a conversion private to the one
method that needs it:

```python
def load_dictionary(self, filename: str, verbose: bool) -> None:
    var word_count: int = 0

    def word_to_digits(word: str) -> []Digit_T:
        var digits: []Digit_T
        for c in word.lower():
            if c not in CHAR_TO_DIGIT:
                return []
            digits.append(CHAR_TO_DIGIT[c])
        return digits

    with open(filename, "r") as f:
        for line in f:
            let word: str = line.strip()
            if not word:
                continue
            let digits: []Digit_T = word_to_digits(word)
            if len(digits) > 0 and len(digits) == len(word):
                self.add_word(word, digits)
                word_count += 1
```

The same file builds its character-to-digit table with a closure that
mutates a local dict — a tidy "constructor function" pattern:

```python
def _build_char_to_digit() -> {char}Digit_T:
    var mapping: {char}Digit_T = {:}

    def m(chars: str, digit: Digit_T):
        for c in chars:
            mapping[c.lower()] = digit
            mapping[c.upper()] = digit

    m("e", Digit_T(0))
    m("jnq", Digit_T(1))
    ...
    return mapping
```

Closures are also how `geo_server.ady` implements its region algebra —
`__and__` returns a `Region` wrapping a closure over both operands:

```python
def __and__(self, other: Region) -> Region:
    def both(p: Point) -> bool:
        p in self and p in other
    Region(both)
```

## 8.3 Mutual recursion and forward declarations

Nim requires declaration before use; Adascript has no forward-declaration
syntax. The escape hatch is a `# nimraw:` comment, which passes its payload
verbatim to the Nim output (and is invisible to Python):

```python
# nimraw: proc scheme_eval(x: Val, eid: int): Val   # forward decl
def scheme_apply(proc_val: Val, args: []Val) -> Val:
    ...
    return scheme_eval(...)

def scheme_eval(x: Val, eid: int) -> Val:
    ...
    return scheme_apply(...)
```

This is exactly the shape of a Scheme interpreter's eval/apply loop, and
`lispy.ady` is where the feature earns its keep.

## 8.4 Generators

`yield` is fully supported: Python output is a generator, Nim output an
iterator. The signature feature of `EXAMPLES/shortest_path.ady` is a
generator *method* that lazily yields ever-costlier solutions — callers take
one and break, or keep iterating for alternatives:

```python
def shortest_path(self, start_state: S, allsolutions: bool = True, end_state: auto = ANY):
    self.start_state = start_state
    var parents:   []int = [-1]
    var decisions: []D   = []
    fringe: PriorityQueue[Fringe_Element_T[S, C]] = PriorityQueue((C(0), C(0), 0, start_state))
    visited: {}S = {}

    while fringe:
        let (_, cost, node_idx, current_state) = fringe.pop()
        if not allsolutions and current_state in visited:
            continue
        visited.add(current_state)

        reached: bool = current_state == end_state if not isANY(end_state) else self.is_end_state(current_state)
        if reached:
            self.decision_path = self._reconstruct(parents, decisions, node_idx)
            yield self.real_cost(cost), self.decision_path
            if not allsolutions:
                break

        for new_decision, step_cost in self.get_next_decisions(current_state):
            next_state: S = self.get_next_state(current_state, new_decision)
            if next_state not in visited:
                ...
                fringe.push((hcost, new_cost, len(parents) - 1, next_state))
```

Consumption reads like Python because it is Python:

```python
# test_shortest_path.ady
op2s: ShortestGraph = ShortestGraph()
for solution in op2s.shortest_path(start_state=a, end_state=j):
    print(solution)
```

Design notes worth stealing from this file:

- The fringe stores **back-links** (`node_idx` into parallel `parents` /
  `decisions` arrays) instead of whole paths, so a push is O(1) instead of
  O(depth); `_reconstruct` walks the links only when a goal is reached.
- `end_state: auto = ANY` uses the `ANY` sentinel so one generator serves
  both "search to a known goal" and "search until `is_end_state()` says
  stop".

## 8.5 Callable values

Functions are values. You have seen `max(..., key=P)`; predicates passed to
the iterator library (`takewhile(less_than_4, ...)` in `test_iters.ady`)
work the same way, and the `[(T,)]R` annotation from §2.2 lets you *store*
callables in fields — `geo_server.ady`'s `Region` holds its predicate that
way. For user-defined callable *objects* (`__call__`, `__ror__`), see
Chapter 9.

---

*Next: [Chapter 9 — Classes, Generics, and Inheritance](09-classes-and-generics.md)*
