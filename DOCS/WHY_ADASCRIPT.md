# Why Adascript

*Hassan El-Karouni*

I have spent a long career in aerospace building complex systems, and I have
written them in C, C++, AWK, Bash, Ada, Python and Nim. Every one of those
languages is useful. Not one of them is right. The last three shaped how I
think, each by being excellent at the thing the other two were missing.

**Ada** taught me that a type is a statement about the world, not a size in
bytes. Its enumerations can index an array and drive a `for` loop; its records
can carry a discriminant; its subranges make a whole class of bug
unrepresentable. Pascal set that minimum and Ada raised it. What Ada asks in
return is ceremony, and a build.

**Python** taught me that a language can get out of the way. No build, no
declarations demanded, a line of it does a day of work in C. What it takes in
return is every guarantee. `$3` in AWK and `d["k"]` in Python mean nothing to
the next reader and nothing at all to the compiler, because there is no
compiler.

**Nim** taught me that the two are not opposites. It compiles to C, it is
fast, it is statically typed, and it is as short to write as Python. What it
lacks is Python's reach — the library, the people, the scripts already on the
disk.

Adascript is what I wanted from all three: Ada's types, Python's syntax, and
both of Nim's and Python's backends from one source. This document is the
argument, not the manual. The manual is `README.md` and `DOCS/BOOK/`.

---

## The lessons

### Software is written for humans to be read

Everything else here follows from this one. A program is executed perhaps
millions of times and read perhaps a hundred, but those hundred readings are
where the cost is — every change, every review, every incident at three in the
morning is somebody reading. A language that is short to *write* and hard to
*read* has optimised the wrong number.

This is why I care about notation. Not because terse is good — because a form
that a reader can take in without decoding it is good.

### Executable pseudocode, for real this time

Python was sold as executable pseudocode, and on a slide it is. Then the
program meets a real problem. The priority queue turns out to be `heapq`, a
module of functions over a list, so the code says `heapq.heappush(queue, …)`
where the pseudocode said "push". The enumeration has to be an `IntEnum`, or
the heap dies comparing two nodes that tie on distance. Its members have to
be written `Node_T.A` or copied into globals first. And the graph's type is
`dict[Node_T, list[Neighbour_T]]`, an annotation nothing checks, so most
people leave it out and the reader is left to guess what `graph[node]`
holds. Each of those is small. Together they are why the Python version of
an algorithm is rarely the one in the textbook.

Here is Dijkstra's shortest paths in Adascript, types and all:

<!-- from: EXAMPLES/dijkstra.ady -->
```python
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
```

The graph is declared in one line. `type Graph_T is {Node_T}[]Neighbour_T`
reads "for each node, a list of its neighbours, each with the distance to
it" — the textbook definition of a weighted digraph as an adjacency list,
and the data structure itself, with nothing to build. The queue holds the
same `Neighbour_T` the edges are made of, so an edge and a queue entry are
one type, not two descriptions of the same pair.

The initialisation is one line, and it is the sentence you would say —
"every node starts at infinity, except the start, which starts at zero":

`distances: {Node_T}Distance_T = {node: (0.0 if node==start else Inf) for node in graph}`

That is Dijkstra's whole initialisation phase, written as a mapping
comprehension, and its result is typed: the keys are `Node_T`, the values
`Distance_T`, and the Nim compiler checks both. Comprehensions are Python's
gift; a typed one that a compiler checks is rare. In most statically typed
languages the same line is a pipeline of calls — in Rust,
`graph.keys().map(|&n| (n, if n == start { 0.0 } else { f64::INFINITY })).collect()`;
in Java, a stream ending in `Collectors.toMap` — or it is a loop over the
nodes with the special case fixed up after it, and the fix-up is where the
bug lives. Here the special case is the conditional inside the
comprehension, so there is no afterwards.

The function is the algorithm and nothing else. Every node starts at
infinity except the start; take the nearest node; skip it if it has been
seen; mark it; relax every edge out of it. A signature and fourteen lines,
and not one of them is there for the language rather than for the
algorithm. That is what executable pseudocode was supposed to mean. The
book's chapter 1 §1.4 sets it beside the same program in idiomatic Python,
line by line.

### Implicit typing is a bad idea

Not "static typing is good" — that argument is over. Implicit typing is
something narrower: a language that *has* types but declines to make you write
them, so the type exists in the compiler and not on the page.

The compiler is not the audience. When I read

<!-- illustrative: the counter-example -- a bare assignment is not a declaration, and does not compile -->
```python
speed = compute(track, wind)
```

I know nothing. When I read

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
let speed: Velocity_T = compute("BAW117", 12.0)
```

I know what came back, I know what `compute` is for, and if the next line
treats `speed` as a distance the discrepancy is on the page where a reader can
see it, not three files away where only the compiler can. Inference saves the
writer a few characters and costs every later reader the trip.

Adascript makes the annotation the ordinary way to write a declaration, and
`let` and `var` say whether the thing can change. Those two words are worth
their keystrokes.

### A complex system is built out of layers of abstraction

There is no other way. The only method anyone has ever found for a system too
big to hold in one head is to make a level at which the thing below is a
detail, then stand on it. The interesting question is not whether to do it but
how to tell when you have done it badly.

### Within a layer, all concepts belong at the same level of abstraction

That is the test. A layer is sound when everything it names is the same
*kind* of thing. A flight-plan layer that talks about flights, routes and
waypoints is a layer. One that talks about flights, routes and
`buf[i + 2] & 0x3F` is not — it has a hole in it, and every reader falls
through the hole every time they pass.

This is a design rule, not a language feature, and no language will enforce
it. But a language can make it cheap or expensive to obey, and that decides
whether you actually do.

### User-defined types are how a layer gets built

A layer is exactly its vocabulary. If the language makes it cheap to name a
concept, the vocabulary grows and the layers appear. If naming a concept costs
a class, a header and a constructor, you use `float` and write a comment, and
the layer never forms.

### A `Velocity_T` is better than a `float`

`float` says how the value is stored. `Velocity_T` says what it *is*. Consider:

<!-- illustrative: two signatures contrasted, neither of them with a body -->
```python
def separation(a: float, b: float, c: float, d: float) -> float
def separation(own: Position_T, other: Position_T,
               closing: Velocity_T, horizon: Duration_T) -> Distance_T
```

The second signature is the documentation, the review checklist and the
argument order all at once. You cannot get the arguments the wrong way round
without it being visible on the page. And the day somebody asks "is this in
knots or metres per second?", there is one place to look and one place to
change.

That is the argument, and it holds even when the type is only a name — which
brings me to the one thing in this document that is not yet finished, and
which I will come back to at the end.

---

## The method

Three steps, in order, before writing any code that *does* anything.

### 1. Name the concepts of the problem domain

One type per concept, with a name ending `_T` so a reader can see at a
glance what is a type. The types come in a progression, from a single value
to a thing with behaviour, and a concept moves up it only as far as it
needs to.

**A single value: a named type, not a bare one.** `float` says how a value
is stored; `Velocity_T` says what it is, as argued above. So a quantity of
the domain is never a bare `int`, `float` or `str`: it gets a name of its
own, and its unit is written once, next to that name. A closed set of
values — a phase of flight, a message kind, a state — is an enumeration.

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Callsign_T     is str
type Altitude_T     is Natural        # feet
type Velocity_T     is float          # knots
type Flight_Phase_T is enum CLIMB, CRUISE, DESCENT, HOLD
type Latitude_T     is float          # degrees, north positive
type Longitude_T    is float          # degrees, east positive
```

A bare type is still right for a value that only counts or indexes and
means nothing more: a length, a loop index, text that is just text.

**A few values that go together: a tuple.** A position is a latitude and a
longitude — always both, passed around whole, and equal to another when both
parts are. A named tuple says exactly that, and names the parts:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Fix_T is tuple:
    lat: Latitude_T
    lon: Longitude_T
```

**A thing whose parts change: a record.** An aircraft has more parts, each
with a sensible starting value, and they change over its life: it climbs, it
changes phase. A record holds them, each field one of the named types
above:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Aircraft_T is record:
    callsign: Callsign_T     = ""
    phase:    Flight_Phase_T = CLIMB
    altitude: Altitude_T     = 0
    speed:    Velocity_T     = 0.0
```

**A thing with behaviour: a class.** Once there are operations that belong
to the data — the ways a flight's state may change, the questions asked of
it — a class groups the data with every method that acts on it. There is
then one place to read what can be done with a flight, and one place to
change it; the rest of the program goes through those methods instead of
reaching into the fields.

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
class Flight_T:
    var aircraft: Aircraft_T
    var route:    []Fix_T

    def __init__(self, aircraft: Aircraft_T):
        self.aircraft = aircraft
        self.route = []

    def report(self, position: Fix_T):     # a position report
        self.route.append(position)

    def climb(self, to: Altitude_T):
        self.aircraft.altitude = to
        self.aircraft.phase = CLIMB

    def above(self, ceiling: Altitude_T) -> bool:
        return self.aircraft.altitude > ceiling
```

Six lines of vocabulary, a tuple, a record and a class, and the layer has a
boundary: every value in it says what it is, and every operation on a
flight is in one place.

### 2. Name the collections and the mappings

This is the step people skip, and it is the one that decides whether the
program is readable. A model is not just its concepts — it is *how many* of
each there are and *which* is reachable from *which*. One aircraft or a fleet?
Found by callsign, or walked in order? Grouped by phase?

Write those down as declarations, before any logic:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
var fleet   : {Callsign_T}Aircraft_T     = {:}   # every aircraft, by callsign
var by_phase: [Flight_Phase_T][]Callsign_T       # who is in each phase
var watched : {}Callsign_T               = {}    # the ones above their ceiling
var ceiling : [Flight_Phase_T]Altitude_T = [CLIMB: 41000, CRUISE: 41000,
                                            DESCENT: 41000, HOLD: 24000]
```

Each of those lines is a relation between concepts of step 1, and each one
answers the same three questions: which way does it go, how many are at the
far end, and does order matter?

- `fleet` goes from a callsign to *the* aircraft that has it. One way only:
  a callsign finds an aircraft, and nothing finds an aircraft by its speed.
  The fleet has no order worth keeping, so it is a plain mapping.
- `by_phase` goes from a phase to the callsigns in it. Many at the far end,
  so a list of them; and one entry for every phase, all of them, in phase
  order.
- `watched` is a set, which is a mapping too: from a callsign to in or
  out, and that is all anyone asks of it.
- `ceiling` goes from a phase to exactly one altitude, and every phase has
  one.

Four lines, and the shape of the whole program is decided. A reader who has
seen those four lines knows what can be asked of this code and what cannot.

### 3. Only then, write what it does

By the time you get here the code is short, because the hard decisions are
already made and visible.

---

## The notation

Step 2 is why Adascript has a notation of its own for collections. It is
built from the answers to two questions, the same two that step 2 asks of
every group of things in the model.

**Does the order mean something?** Square brackets `[…]` if it does — the
waypoints of a route, the phases of a flight. Braces `{…}` if it does not —
the aircraft being watched, the fleet by callsign.

**Is it keyed?** Nothing between the brackets: a **collection**, some T's.
A type between them: a **mapping**, from that type to the one after the
brackets.

Two questions, four answers, and each is a structure you already know:

|                | ordered `[…]`                        | unordered `{…}`            |
|----------------|--------------------------------------|----------------------------|
| **collection** | `[]T` — a list of T                  | `{}T` — a set of T         |
| **mapping**    | `[E]T` — one T for each member of E  | `{K}V` — a mapping from K to V |

An ordered mapping needs a key with an order to index by — an enumeration,
`bool`, a character, an integer range — so `[E]T` has a slot for every
member of `E`, in declaration order, and cannot lack one. An unordered
mapping takes any hashable key and holds only the keys put in it. That is the whole
difference between `ceiling` and `fleet` above, and the notation makes you
choose.

Mappings are the heart of it, because a model is its concepts *and the
relations between them*, and nearly every relation is a mapping: callsign to
aircraft, phase to callsigns, phase to ceiling. Writing a relation as a
mapping type puts the answers of step 2 in the declaration — the direction
is the order of the two types, how many are at the far end is the element
type (one `Aircraft_T`, or a `[]Callsign_T`), and whether every key is there
is the choice of brackets. Solving the problem is then walking those
relations one lookup at a time, and each lookup's type says what comes out.

The collections are mappings too, seen from the side: a list maps its
positions to its elements, and a set maps its elements to in-or-out. That is
why `xs[i]` and `x in s` are both lookups, and why a set cannot hold the
same element twice — a key is present or absent, there is no third state.

Two more forms sit outside the grid, as neither holds many of anything:

| Written | Read as |
|---------|---------|
| `?T` | a T, possibly absent |
| `Fix_T is tuple:` | a named tuple, fields by name |

The four containers and `?T` are written as a **prefix on the element
type**, so a declaration reads left to right as a sentence:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
let xs   : []int              = [1, 2, 3]                 # a list of
let m    : {str}int           = {"a": 1}                  # a mapping from .. to
let s    : {}str              = {"x", "y"}                # a set of
let arr  : [Sector_T]int       = [NORTH: 1, CENTRE: 2, SOUTH: 3]  # one per member
let opt  : ?int               = 7                         # possibly absent
let pair : Fix_T              = (lat: 51.5, lon: -0.1)    # named tuple
```

They compose by stacking, with no brackets to hold open:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
var routes : {str}[]str       = {"BA117": ["EGLL", "KJFK"]}
var bysector: [Sector_T][]str   = [NORTH: [], CENTRE: ["BA117"], SOUTH: []]
var nested : {str}{str}int    = {"a": {"b": 1}}

routes["AF22"] = ["LFPG", "LEMD"]

assert xs'Length == 3 and m["a"] == 1 and "x" in s
assert arr[CENTRE] == 2 and (opt or 0) == 7 and pair.lat == 51.5
assert routes["BA117"]'Length == 2 and routes'Length == 2
assert bysector[CENTRE][0] == "BA117" and bysector[NORTH]'Length == 0
assert nested["a"]["b"] == 1
```

`{Callsign_T}[]Waypoint_T` is "for each callsign, a list of waypoints", and
you read it in that order, once, left to right. Compare what the same type
costs elsewhere:

| Adascript | Python | Nim |
|-----------|--------|-----|
| `{Callsign_T}[]Waypoint_T` | `Dict[Callsign_T, List[Waypoint_T]]` | `Table[Callsign_T, seq[Waypoint_T]]` |
| `[Phase_T]Altitude_T` | `Dict[Phase_T, Altitude_T]` | `array[Phase_T, Altitude_T]` |
| `{}Callsign_T` | `Set[Callsign_T]` | `HashSet[Callsign_T]` |
| `?Altitude_T` | `Optional[Altitude_T]` | `Option[Altitude_T]` |

The others all put the container's *name* first and its contents inside
brackets, so the reader opens a bracket, holds it, and closes it. At one level
that is a small tax. At two it is why people stop writing the annotation at
all — and a type annotation nobody writes is worth nothing.

I make no claim that every sigil here is unprecedented; Go writes a slice
`[]T` and a map `map[K]V`, and anyone designing in this space will land near
`[]T` eventually. What is Adascript's own is the *family*: that the list, the set, the
enum-indexed array and the mapping are the four answers to two questions,
that the optional joins them under the same rule — "container first,
element after, no brackets to balance" — and that they stack. I did not take it from another language,
because I could not find one that had it.

`[E]T` in particular is the one I would not give up. An array indexed by an
enumeration is Pascal's and Ada's idea and it has been quietly dropped by
almost everything since. It is how you say "one of these per case, and the
compiler will tell you if you miss one" — and in Adascript it costs four
characters.

---

## A worked model

The whole of step 1 and step 2, and then the code:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
for cs in ["AFR22", "BAW117"]:
    let a: Aircraft_T = fleet[cs]
    by_phase[a.phase].append(a.callsign)
    if a.altitude > ceiling[a.phase]:
        watched.add(a.callsign)

for phase in Flight_Phase_T:
    print f"{phase:<8} {by_phase[phase]'Length}"
```

There is no plumbing in it. Each line walks a relation declared in step 2:
from a callsign to its aircraft (`fleet[cs]`), from its phase to the
callsigns in that phase (`by_phase[a.phase]`) and to that phase's ceiling
(`ceiling[a.phase]`). `by_phase[a.phase]` works because the phase *is* an
index; `for phase in Flight_Phase_T` walks the domain in declaration order
and cannot miss a member; `ceiling[a.phase]` is a table lookup that cannot
be misspelled. None of that is clever. It is what happens when step 1 and
step 2 were done first.

---

## What is not yet true

An advocacy document that overclaims is worth less than no document, so:
**a scalar type alias is documentation, not enforcement.**

<!-- from: EXAMPLES/DOC/why_alias_snippets.ady -->
```python
type Velocity_T is float
type Distance_T is float

let v: Velocity_T = 250.0
let d: Distance_T = v        # compiles today, on both backends
```

`Velocity_T` gives you the name in the signature, in the review and in the
grep, and by the argument above that is most of the benefit. What it does not
yet give you is the compiler refusing to put knots where metres belong.

Where Adascript *does* enforce a distinction today: an enumeration is a real
type (index an `[E]T` with a string and it will not compile), `Natural` and
`Positive` are range-checked at run time, a record is nominal, `?T` is not
`T`, and `Path` is a distinct string — `p = s` is an error on both backends
and `Path(s)` is how you mean it.

That last one is the proof that the machinery exists. `Path` is a distinct
type because it was built as one. Letting a user-defined scalar say the same
thing — `type Velocity_T is distinct float` — is the next thing on the list,
and it is in `TODO.md`.

---

## Further reading

- `README.md` — the language reference
- `DOCS/BOOK/` — the book, chapter by chapter
- `DOCS/ADASCRIPT_FOR_AWK.md` — for text and record processing
- `DOCS/ADASCRIPT_FOR_SHELL.md` — for scripts and system tools
- `EXAMPLES/` — every one of them compiled and run on both backends by
  `make test`
