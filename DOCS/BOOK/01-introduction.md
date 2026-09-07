# Chapter 1 — Introduction: One Language, Two Targets

## 1.1 What Adascript is

Adascript is an unapologetically eclectic language. Its author spent years
looking for a language that offers expressive types, a large ecosystem, good
performance, *and* good developer experience — and concluded that no single
language delivers all four. Adascript's answer is to steal:

- from **Python** — the entire surface syntax. Every valid Python 3 file is
  also a valid Adascript file; all extensions are purely additive.
- from **Ada** (and Pascal before it) — enumeration types that work as array
  indexes and loop ranges, variant records, subrange types, and tick
  attributes like `Door_T'First` and `state'Next`.
- from **Nim** — the compile target, the `var`/`let`/`const` discipline, the
  type system, and native performance.
- from **Perl and AWK** — first-class regex literals `/pat/flags`, capture
  variables `$+1`, and `s/pat/repl/` substitution.
- from **Bash** — `$1`, `$#`, `$@`, `$HOME`, file tests like `-f path`, and
  first-class `shell:` blocks.

A single `.ady` source file transpiles to *both* ecosystems:

```
source.ady
    │
    ├── python3 TO_PYTHON/py2py.py source.ady  ──▶  Python 3
    └── python3 TO_NIM/py2nim.py   source.ady  ──▶  Nim  ──▶  native binary
```

You prototype with Python's ecosystem and debugging comfort, then ship the
same source as a compiled Nim binary — or keep both targets alive forever, as
the examples in this repository do.

## 1.2 Hello, world — and hello, benchmark

The smallest Adascript program is also a valid Python program, except for one
courtesy inherited from Python 2: `print` works without parentheses.

```python
#!/usr/bin/env py2nim
print "Hello, world!"
```

The shebang line matters. With `chmod +x`, running `./hello.ady` transpiles
the file to Nim, compiles it into a cache directory
(`~/.cache/hparsec/cache-<HASH>/`), symlinks the binary next to the source,
and runs it. Subsequent runs skip whatever is already up to date, so an
unchanged script starts as fast as any native executable.

Here is the first real program, `EXAMPLES/primes.ady`, which counts the
primes below one million and times itself:

```python
#!/usr/bin/env py2nim

pyimport time

N = 1000000

def is_prime(n: Positive) -> bool:
    result = True
    limit : Positive = Positive(n**0.5)
    for k in 2..limit:
        if n % k == 0:
            result = False
            break

def count_primes(n: Positive) -> Positive:
    result = 1 # we know 2 is a prime
    for k in 3..<n:
        if is_prime(k):
            result += 1

start = time.perf_counter()
print f"Number of primes: {count_primes(N)}"
finish = time.perf_counter()
print f"time elapsed: {finish - start}/s"
```

Twenty lines, and already half the language's character is on display:

- **Ada-style numeric subtypes.** `Positive` (1..) and its sibling `Natural`
  (0..) are available out of the box, mapping to Nim's types of the same
  names and to plain `int` in Python.
- **Range operators.** `2..limit` is an inclusive range; `3..<n` excludes the
  upper bound. In Python output these become `range(2, limit+1)` and
  `range(3, n)`; in Nim they are native ranges.
- **The implicit `result` variable.** Borrowed from Nim: a function with a
  return-type annotation has a pre-declared `result` variable, and falling
  off the end returns it. `is_prime` never writes `return`.
- **Python interop.** `pyimport time` plus `time.perf_counter()` works on
  both targets — the transpiler knows which Python stdlib modules have native
  Nim equivalents and maps the calls (here `times`/`epochTime` territory).
- **f-strings and parenthesis-free `print`**, which becomes `echo fmt"..."`
  in Nim.

The payoff for these twenty lines: run it with `py2py.py -c` and you get
Python's answer in Python's time; run it with `py2nim.py -d:release` and the
identical source runs at native speed.

## 1.3 A four-line filter

Adascript is also meant for the small end of the scale — the scripts you
would otherwise write in AWK. `EXAMPLES/average_line.ady` in its entirety:

```python
#!/usr/bin/env py2nim
"""
cat FILE | ./average_line
./average_line < FILE
"""

var sum : Natural = 0
var count : Natural = 0
for line in stdin.lines:
  sum += line'Length
  count += 1

print f"Average line length is {sum/count}"
```

Note `line'Length` — an Ada *tick attribute* applied to a string, and
`stdin.lines`, an iterator over standard input that works on both backends.
Chapter 3 covers tick attributes; Chapter 11 shows how far the
shell-scripting side of the language goes.

## 1.4 Dijkstra, entire

The claim this book keeps returning to is that Adascript reads as executable
pseudocode. `EXAMPLES/dijkstra.ady` is the shortest way to see what that
means — this is the whole file, nothing elided:

```python
#!/usr/bin/env py2nim
from stdlib nimport PriorityQueue
type Node_T is enum A, B, C, D
type Distance_T is float
type Graph_T is {Node_T}{Node_T}Distance_T
const MAX_DIST : float = 1e6
type Neighbour_T is tuple:
    distance: Distance_T
    neighbor: Node_T

def dijkstra(graph : Graph_T, start: Node_T) -> {Node_T}Distance_T:
    distances: {Node_T}Distance_T = {node: (0.0 if node==start else MAX_DIST) for node in graph}
    var visited : {}Node_T
    queue : PriorityQueue[Neighbour_T] = [(0.0, start)]
    while queue:
        current_dist, node = queue.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph[node]:
            let new_dist: Distance_T = current_dist + graph[node][neighbor]
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                queue.push((new_dist, neighbor))
    return distances

graph : Graph_T = {A:{B:1.0, C:4.0}, B: {C:2.0, D:5.0}, C: {D:1.0}, D: {:}}
print dijkstra(graph, A)
```

It prints `{D: 4.0, C: 3.0, A: 0.0, B: 1.0}`.

Four things are worth stopping on, and none of them is a trick.

**The types are the specification.** `type Graph_T is {Node_T}{Node_T}Distance_T`
is the textbook definition of a weighted digraph — a mapping from a node to
a mapping from a node to a distance — and it is also, with no further
ceremony, the data structure. Chapter 2 gives the notation; here it is
enough that the declaration says what a graph *is* rather than how to build
one.

**The initialisation is one line, and it is the sentence you would write.**

```python
distances: {Node_T}Distance_T = {node: (0.0 if node==start else MAX_DIST) for node in graph}
```

"Every node starts at infinity, except the start, which starts at zero."
That is Dijkstra's initialisation phase in full. In most languages it is a
loop with a special case afterwards, and the special case is where the bug
lives. Here the special case is a conditional inside the comprehension, so
there is no afterwards.

**`for node in graph` means what it says.** A `{K}V` is an unordered mapping
and iterating one yields its keys, so that phrase reads "for each node in
the graph" — and the same line is a valid dict comprehension in Python,
which is what a superset buys.

**The loop body is the algorithm, line for line.** Pop the nearest unvisited
node; skip it if already visited; mark it; relax each edge out of it. There
is no scaffolding around that — no class to hold the state, no visitor, no
manual bookkeeping of the queue's invariants. Twenty-eight lines, and the
only line that is not the algorithm is the `#!` on the first.

### The same program in Python

Adascript is a superset, so it can never say *less* than Python — every
Python program is already an Adascript one. The interesting question is
whether the additions let you say the same thing more directly. Here is the
same algorithm written in idiomatic Python 3, checked to produce the same
distances:

```python
#!/usr/bin/env python3
import heapq
from enum import IntEnum
from typing import NamedTuple, TypeAlias

class Node_T(IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3

Distance_T: TypeAlias = float
Graph_T: TypeAlias = dict[Node_T, dict[Node_T, Distance_T]]
MAX_DIST: float = 1e6

class Neighbour_T(NamedTuple):
    distance: Distance_T
    neighbor: Node_T

def dijkstra(graph: Graph_T, start: Node_T) -> dict[Node_T, Distance_T]:
    distances: dict[Node_T, Distance_T] = {node: (0.0 if node == start else MAX_DIST) for node in graph}
    visited: set[Node_T] = set()
    queue: list[Neighbour_T] = [Neighbour_T(0.0, start)]
    while queue:
        current_dist, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph[node]:
            new_dist: Distance_T = current_dist + graph[node][neighbor]
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                heapq.heappush(queue, Neighbour_T(new_dist, neighbor))
    return distances

A, B, C, D = Node_T.A, Node_T.B, Node_T.C, Node_T.D
graph: Graph_T = {A: {B: 1.0, C: 4.0}, B: {C: 2.0, D: 5.0}, C: {D: 1.0}, D: {}}
print(dijkstra(graph, A))
```

Twenty-six non-blank lines against thirty-three, and 1018 characters against
1222 — worth having, but the line count is the weaker half of the argument.
Three of those extra lines are not algorithm at all:

- **`import heapq`, and `heappush`/`heappop` written out.** Python's heap is
  a module of functions operating on a list, so the queue is not an object
  and the calls do not read as pushing and popping a queue. Adascript's
  `PriorityQueue[Neighbour_T]` is a value with `.push()` and `.pop()`, and
  `while queue:` tests it for emptiness the way any container is tested.
- **`IntEnum` rather than `Enum`.** This one is a trap rather than a
  nuisance. `heapq` compares tuples, so when two distances tie it goes on to
  compare the nodes — and a plain `Enum` is not ordered. Write the obvious
  `class Node_T(Enum)` and this program dies on *this* graph, where `(4.0,
  C)` and `(4.0, D)` both reach the queue:
  `TypeError: '<' not supported between instances of 'Node_T' and 'Node_T'`.
  Nothing in the source hints that the enum's base class and the heap are
  connected. Adascript's queue orders on the tuple's first element and never
  reaches the second.
- **`A, B, C, D = Node_T.A, Node_T.B, Node_T.C, Node_T.D`.** Without it the
  graph literal has to qualify every member — `{Node_T.A: {Node_T.B: 1.0,
  …}}` — and stops looking like a graph. Adascript uses enum members bare,
  so the literal is the adjacency list as you would draw it.

The type declarations are the other half:

```python
type Graph_T is {Node_T}{Node_T}Distance_T                  # Adascript
Graph_T: TypeAlias = dict[Node_T, dict[Node_T, Distance_T]]  # Python
```

and the difference is not only the width. Python's annotation is
documentation that nothing enforces; Adascript's is what the Nim backend
compiles the program *from*, and what its compiler checks. The same line is
carrying more.

One caveat, since this chapter is called *One Language, Two Targets*: this
particular file builds and runs on the Nim backend only. `PriorityQueue`
comes from the bundled `stdlib` library through `from stdlib nimport`, and
the Python backend cannot yet supply a `nimport`ed module, so `queue` stays
a plain list there. That is a gap in the toolchain rather than the language,
and it is written up in `TODO.md`; every other program quoted in this book
runs on both.

## 1.5 The toolchain at a glance

```bash
# Python backend
python3 TO_PYTHON/py2py.py source.ady        # print generated Python to stdout
python3 TO_PYTHON/py2py.py -c source.ady     # transpile and run

# Nim backend
python3 TO_NIM/py2nim.py source.ady          # transpile + compile + run (default)
python3 TO_NIM/py2nim.py -t source.ady       # transpile only, write source.nim
python3 TO_NIM/py2nim.py c -d:release source.ady   # optimised build
```

Per-file compiler options live on the second line of the source, after the
shebang. Many examples pin their C compiler this way:

```python
#!/usr/bin/env py2nim
#ady2nim-args c --cc:clang --clang.exe:zigcc --clang.linkerexe:zigcc
```

Any flag `py2nim` does not recognise (e.g. `-d:release`, `--opt:speed`) is
forwarded to the Nim compiler. Builds are incremental at three levels:
transpilation is skipped if the `.nim` file is newer than both the source and
the transpiler; compilation is skipped if the binary is newer than the
`.nim`; and if everything is current the cached binary simply runs.

## 1.6 What the examples directory contains

The `EXAMPLES/` directory is the language's proving ground — every feature
was driven by a real program there. A rough map, which is also the plan of
this book:

| Kind | Programs |
|------|----------|
| Classic algorithms | `primes.ady`, `graph.ady`, `dijkstra.ady`, `floyd.ady`, `sudoku.ady`, `spell.ady`, `phonecode.ady`, `tsp.ady` |
| Simulations | `monty_hall.ady`, `prisoners.ady` |
| Frameworks | `shortest_path.ady` (+ `test_shortest_path.ady`), `state_search.ady` (+ tests) |
| Operations research / RL | `dp/jacks.ady`, `td_learning/qlearning.ady`, `td_learning/sarsa.ady`, `timetable_*.ady` |
| An interpreter | `INTERACTIVE/lispy.ady` — a full Scheme interpreter |
| Text processing | `awk_example.ady`, `test_awk.ady`, `test_regex.ady`, `average_line.ady` |
| System tools | `rsync_time_machine.ady`, `lolcate/lolcate.ady`, `git1.ady`, `geo_server.ady` |
| Interactive shell tools | `INTERACTIVE/fsel.ady`, `INTERACTIVE/sv.ady`, `INTERACTIVE/show_status.ady`, `INTERACTIVE/lv.ady`* |
| Feature exercises | `openarray_demo.ady`, `test_iters.ady`, `test_do_block.ady`, `test_ownership.ady`, `test_shell_block.ady`, `test_expect.ady`, `argparse.ady` |

\* `lv.ady` lives at the top of `EXAMPLES/`.

By the end of the book you will have read substantial parts of all of them.

---

*Next: [Chapter 2 — Types, Declarations, and Annotations](02-types-and-declarations.md)*
