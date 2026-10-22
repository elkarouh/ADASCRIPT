# Why Adascript

*Hassan El-Karouni*

## The bug that lost a spacecraft

On 23 September 1999 the Mars Climate Orbiter reached Mars about 57 km above
the surface, not the planned 226 km, and was lost. Two programs were each
correct. One wrote thruster impulses in pound-force seconds, the other read
them as newton-seconds, and a factor of 4.45 sat between them, because both
held the number in a `float` and nothing could notice. In Adascript the two
units are two types, and one line says how they relate:

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
from units import kilogram_T, metre_T, second_T

type Mass_T     is kilogram_T
type Distance_T is metre_T
type Duration_T is second_T
type Speed_T    is Distance_T / Duration_T                 # m/s
type Impulse_T  is Mass_T * Speed_T                        # N s, which is kg m/s: what the navigation expects
type Impulse_in_lbf_s_T is 4.4482216152605 * Impulse_T    # one pound-force second is 4.448 N s
```

A mass, a distance and a duration are units of their own. A speed is declared as a
distance over a time, an impulse as a mass times that speed, and a pound-force
second as 4.448 of an impulse. The call that was the mission's loss does not
compile:

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
#     let wrong: Speed_T = speed_change(SMALL_FORCES, SPACECRAFT)
```

That is the whole case for this language in one example: a type that says what
a number *is*, and a compiler that holds you to it. The rest of this document is
how far the idea goes, and how little it costs to write down.

Adascript rests on three ideas:

1. **Take inspiration from Ada's typing, because it is fantastic.**
2. **Exceptions are not a very good idea. Errors should be processed where they
   occur.**
3. **Software is written for humans, not for machines, so type inference is a
   bad idea.** When you write life-threatening software, you do not want to
   take the risk of someone guessing incorrectly.

I stole many features from many languages, and I say from whom where I know.
What is unique to Adascript is its powerful typing syntax, and this document
goes deeper on it. It transpiles to both Python and Nim from one source. This
document is the argument, not the manual; the manual is `README.md` and
`DOCS/BOOK/`. Every block of Adascript quoted here is checked against its file
by `DOCS/check_quotes.py`, and the examples are compiled and run by `make test`.

How it is laid out:

- **What I believe** states the three ideas above.
- **What it looks like** shows a whole algorithm, types and all.
- **Layers and vocabulary**, **The method** and **The notation** are the
  typing: why a type should name a concept, how to find the concepts, and the
  notation that writes them down.
- **What the compiler holds you to** is what that buys, as one ladder of rungs
  from a name to a check: units, money, ranges, and a spacecraft that would not
  have been lost.
- **A failure belongs in the signature** is the second idea in full, down to
  the constructor.
- **Objections** answers the questions a sceptical reader asks first.
- **What is not yet true** lists what each backend does not do.
- **Why I wrote it** is the story, kept to the end.

---

## What I believe

### Ada's typing is the right idea

A type is a statement about the world, not a size in bytes. Ada's
enumerations can index an array and drive a `for` loop; its records can carry a
discriminant; its subranges make a whole class of bug unrepresentable. Pascal
set that minimum and Ada raised it. What Ada asks in return is ceremony and a
build, and the ceremony is what Adascript removes: the typing is Ada's, the
syntax is Python's.

### Software is written for humans to be read

Everything else here follows from this one. A program is executed perhaps
millions of times and read perhaps a hundred, but those hundred readings are
where the cost is — every change, every review, every incident at three in the
morning is somebody reading. A language that is short to *write* and hard to
*read* has optimised the wrong number.

This is why I care about notation. Not because terse is good — because a form
that a reader can take in without decoding it is good.

### Implicit typing is a bad idea

Not "static typing is good" — that argument is over. Implicit typing is
something narrower: a language that *has* types but declines to make you write
them, so the type exists in the compiler and not on the page.

The compiler is not the audience. Take the same call, written twice. When I
read

<!-- illustrative: the counter-example -- a bare assignment is not a declaration, and does not compile -->
```python
limit = restriction(phase)
```

I know nothing about `limit`. Feet? A flight level? Metres? Nothing on the
page says, so I have to find `restriction` and read it. When I read

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
let limit: Altitude_T = restriction(phase)
```

the call is the same, and only the declaration has changed. It now says what
came back, so I do not need `restriction` to know it, and if the next line
compares `limit` with a speed the discrepancy is on the page where a reader
can see it, not three files away where only the compiler can. Inference saves
the writer a few characters and costs every later reader the trip. In software
that can hurt someone, the reader who guesses the type wrong is the risk,
and the page should leave nothing to guess.

Adascript makes the annotation the ordinary way to write a declaration, and
`let` and `var` say whether the thing can change. Those two words are worth
their keystrokes.

### Errors belong where they occur

An exception is handled wherever a `try` happens to be, some distance up the
call stack, or nowhere; the function that failed and the function that
decides what to do about it do not meet on the page. Adascript returns the
failure as a value instead, in the signature, and a failure that is dropped is
refused. The full argument, with a real tool that lost three bugs to it, is
the section "A failure belongs in the signature" below.

---

## What it looks like

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
    var distances: {Node_T}Distance_T = {node: (0.0 if node==start else Inf) for node in graph}
    var visited : {}Node_T
    var queue : PriorityQueue[Neighbour_T] = [(0.0, start)]
    while queue:
        current_dist, node = queue.pop()
        continue if node in visited
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

`var distances: {Node_T}Distance_T = {node: (0.0 if node==start else Inf) for node in graph}`

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
seen; mark it; relax every edge out of it. A signature and thirteen lines,
and not one of them is there for the language rather than for the
algorithm. That is what executable pseudocode was supposed to mean. The
book's chapter 1 §1.4 sets it beside the same program in idiomatic Python,
line by line.

---

## Layers and vocabulary

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

### A `Speed_T` is better than a `float`

`float` says how the value is stored. `Speed_T` says what it *is*. Consider:

<!-- illustrative: two signatures contrasted, neither of them with a body -->
```python
def separation(a: float, b: float, c: float, d: float) -> float
def separation(own: Fix_T, other: Fix_T,
               closing: Speed_T, horizon: Duration_T) -> Distance_T
```

The second signature is the documentation, the review checklist and the
argument order all at once. You cannot get the arguments the wrong way round
without it being visible on the page. And the day somebody asks "is this in
knots or metres per second?", there is one place to look: `Speed_T` is metres
per second, and the knots the radar speaks are a unit of their own, a line
away.

That is the argument, and it holds even when the type is only a name. When
putting one of them where the other belongs would be a bug, a type can be
more than a name: `distinct` makes the compiler hold you to it, and the section
"What the compiler holds you to" says exactly how far that reaches.

---

## The method

Three steps, in order, before writing any code that *does* anything.

### 1. Name the concepts of the problem domain

One type per concept. A named type -- an alias, an enumeration, a tuple, a
record -- has a name ending `_T`, so a reader can see at a glance what is a
type; a class does not: it is named for the thing it is, `Flight`. The types
come in a progression, from a single value to a thing with behaviour, and a
concept moves up it only as far as it needs to.

**A single value: a named type, not a bare one.** `float` says how a value
is stored; `Speed_T` says what it is, as argued above. So a quantity of
the domain is never a bare `int`, `float` or `str`: it gets a name of its
own, and its unit is written once, next to that name. Only the basic units
of the domain, a distance, a duration, an angle, are declared from nothing;
every other quantity is made from them, so that a speed cannot be declared
without saying what it is a speed of. A closed set of
values — a phase of flight, a message kind, a state — is an enumeration.

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
const METRES_PER_KNOT: float = 1852.0 / 3600.0      # exact: a nautical mile is 1852 m

from units import metre_T, second_T

type Callsign_T       is str where c: c == /^[A-Z][A-Z0-9-]{1,11}\z/
type Distance_T       is metre_T                     # the quantity, as a signature says it
type Duration_T       is second_T
type Speed_T          is Distance_T / Duration_T     # metres per second
type Altitude_T       is 30.48 * Distance_T          # a flight level: hundreds of feet
type Speed_in_knots_T is METRES_PER_KNOT * Speed_T   # what the radio and the radar say
type Flight_Phase_T   is enum CLIMB, CRUISE, DESCENT, HOLD
type Degree_T         is distinct float
type Latitude_T       is Degree_T range -90 .. 90        # north positive
type Longitude_T      is Degree_T range -180 .. 180      # east positive
```

A metre, a second and a degree are the basic units: the first two come from
the standard library's `units` module, and the degree is the only one the
program declares bare. `Distance_T` and `Duration_T` are those same types under the
names a signature wants to read, and `Duration_T` says what it holds. A speed is a distance over a duration; an altitude is the
flight level the controller says, hundreds of feet, which is 30.48 metres of
distance; the knots the radar reports are a multiple of the speed; and a
latitude is an angle that is only ever between -90 and 90. None of them is a
`float` that someone has to remember the meaning of, and a callsign is not a
plain `str` either: it is a string that has passed its check, so the first line
of the block says which strings are callsigns.

A bare type is still right for a value that only counts or indexes and
means nothing more: a count, a loop index, text that is just text.

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
with a sensible starting value except the callsign, which is given when the
aircraft is made, and they change over its life: it climbs, it
changes phase. A record holds them, each field one of the named types
above:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Aircraft_T is record:
    callsign: Callsign_T
    phase:    Flight_Phase_T   = CLIMB
    altitude: Altitude_T       = 0.0
    speed:    Speed_in_knots_T = 0.0
```

**A thing with behaviour: a class.** Once there are operations that belong
to the data — the ways a flight's state may change, the questions asked of
it — a class groups the data with every method that acts on it. There is
then one place to read what can be done with a flight, and one place to
change it; the rest of the program goes through those methods instead of
reaching into the fields.

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
class Flight:
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
var ceiling : [Flight_Phase_T]Altitude_T = [CLIMB: 410.0, CRUISE: 410.0,
                                            DESCENT: 410.0, HOLD: 240.0]
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
| **mapping**    | `[K]T` — a T per key, keys in order  | `{K}V` — a mapping from K to V |

What order an ordered mapping has depends on its key. When the key is an
enumeration, `bool`, a character or an integer range, every key and its
place are known before the program runs: `[E]T` has a slot for every member
of `E`, in declaration order, and cannot lack one. When the key is anything
else — a callsign, a tuple of coordinates — the keys cannot be known in
advance, so the order is the order they **arrived** in, and that is kept.
An unordered mapping takes any hashable key, holds only the keys put in it,
and promises no order at all. That is the whole difference between
`ceiling` and `fleet` above, and the notation makes you choose.

The arrival order is worth keeping because it is so often the fact you
wanted. Landings, in the order they happened:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Duration_in_minutes_T is 60.0 * Duration_T
var landed: [Callsign_T]Duration_in_minutes_T = {:}    # in the order they landed

landed[afr] = 12.0
landed[baw] = 3.0
```

Written `{Callsign_T}Duration_in_minutes_T`, the order is simply not part of the type:
`{…}` promises none, so each backend is free to use whatever it has — Python
happens to keep insertion order, Nim uses hash order — and a program that
reads the landings back in order is relying on something it was never
given. `[Callsign_T]` makes the order part of the contract. The brackets
are the difference.

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

The same question — were the keys known before the program ran? — decides
what a loop gives you. `for x in c`, and `x in c` with it, give the half of
the mapping you did *not* already know. The ceiling per phase has its keys
fixed by `Flight_Phase_T`; listing them tells you nothing, so a loop over
`ceiling` gives the ceilings, and `x in ceiling` asks whether any phase has
that one. The fleet's keys are whichever callsigns happen to be in the
air, and which ones is exactly the question, so a loop over `fleet` gives
callsigns and `cs in fleet` asks whether that aircraft is here; the
aircraft is reached through its callsign. `landed` is the same, in the
order the aircraft landed. A set is the limiting case: its value half —
present or absent — says nothing, so its elements, which are its keys, are
all there is. One rule, stated once, and every loop in the language follows
from it: the brackets say whether there is an order, the key says what you
iterate.

So is a function. A pure function maps its arguments to a result, and
`rule(phase)` is a lookup like `ceiling[phase]` — the difference is that
one is *computed* and the other *stored*. Adascript writes a function type
the way a `def` writes its signature, parameters, an arrow, the result:

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Ceiling_Rule_T is (Flight_Phase_T) -> Altitude_T   # computed, not stored

def published(phase: Flight_Phase_T) -> Altitude_T:
    return ceiling[phase]

def over_ceiling(a: Aircraft_T, rule: Ceiling_Rule_T) -> bool:
    return a.altitude > rule(a.phase)
```

It is tempting to go further and spell it `{Flight_Phase_T}Altitude_T`, and
let the compiler decide from context whether that is a table or a function.
I decided against it. The two share only the lookup: a table can be
iterated, counted, tested with `in` and written to; a function can only be
called, but it can answer for a domain no table could hold. A parameter, a
field, a return type carry no value to guess from, and a reader who cannot
tell which one they have cannot tell what they may do with it. The type
says it, and the arrow is how every signature already says it.

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
let pair : Fix_T              = (lat: Latitude_T(51.5), lon: Longitude_T(-0.1))   # named tuple
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

| Adascript | Read aloud | Python | Nim |
|-----------|-----------|--------|-----|
| `{Callsign_T}[]Waypoint_T` | for each callsign, a list of waypoints | `Dict[Callsign_T, List[Waypoint_T]]` | `Table[Callsign_T, seq[Waypoint_T]]` |
| `[Phase_T]Altitude_T` | one altitude for every phase | `Dict[Phase_T, Altitude_T]` | `array[Phase_T, Altitude_T]` |
| `{}Callsign_T` | a set of callsigns | `Set[Callsign_T]` | `HashSet[Callsign_T]` |
| `?Altitude_T` | an altitude, or nothing | `Optional[Altitude_T]` | `Option[Altitude_T]` |
| `[Callsign_T]Duration_in_minutes_T` | minutes per callsign, in arrival order | `dict[Callsign_T, Duration_in_minutes_T]` | `OrderedTable[Callsign_T, Duration_in_minutes_T]` |
| `(Flight_Phase_T) -> Altitude_T` | an altitude computed from a phase | `Callable[[Flight_Phase_T], Altitude_T]` | `proc(a0: Flight_Phase_T): Altitude_T` |

The others all put the container's *name* first and its contents inside
brackets, so the reader opens a bracket, holds it, and closes it. At one level
that is a small tax. At two it is why people stop writing the annotation at
all — and a type annotation nobody writes is worth nothing.

I make no claim that every sigil here is unprecedented; Go writes a slice
`[]T` and a map `map[K]V`, and anyone designing in this space will land near
`[]T` eventually. What is Adascript's own is the *family*: that the list, the set, the
ordered mapping and the unordered one are the four answers to two questions,
that the optional joins them under the same rule — "container first,
element after, no brackets to balance" — and that they stack. I did not take it from another language,
because I could not find one that had it.

### What the notation was weighed against

A notation is a set of choices, and a reader trusts it more when they can see
what it was set against. Three of them, in the order a reader meets them:

- **`?T`, not `T | None`.** An optional is the commonest union and it is not
  really a union: it is "this, or nothing". Written `T | None` it would be one
  more member list to read, and it would not stack with the rest. As a prefix it
  composes like the other containers, `?[]Fix_T`, read left to right.
- **`!F` marks the failure, not a tuple.** Go returns `(value, error)`, and the
  error can be ignored. A union `Path | Failure_T` alone does not say which side
  is the failure; the `!` does, and so a failure that is dropped can be refused,
  which a pair cannot do.
- **The annotation is the ordinary way to declare, and `let` and `var` say
  whether it can change.** Inference would save the writer four characters and
  cost every later reader the trip, as argued above. Two short words buy the
  reader the type and the mutability on the same line.

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
for cs in [afr, baw]:
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

## What the compiler holds you to

The typing in this document is one idea asked with increasing strictness: what
may a value of this type be mixed with, and what may it hold? Each answer is one
line of declaration, and each catches a bug the line above it lets through:

| Rung | Written | The compiler refuses | The bug it catches |
|------|---------|----------------------|--------------------|
| a name | `type Flight_Number_T is Natural` | nothing: it documents | a signature nobody can read |
| distinct | `type metre_T is distinct float` | mixing with any other type | a duration passed where a distance belongs |
| a relation | `type Speed_T is Distance_T / Duration_T` | arithmetic nobody declared | `speed * speed` taken for a distance |
| a scale | `type Altitude_T is 30.48 * Distance_T` | a unit mixed in silently | the factor applied twice |
| a range, a wrap | `type Latitude_T is Degree_T range -90 .. 90` | values outside the set | a latitude of 95, a bearing of 370 |
| a check | `type Callsign_T is str where c: ...` | any value failing a predicate | a callsign that is not one |

One domain, all the rungs, as the program writes them:

<!-- from: EXAMPLES/DOC/why_ladder_snippets.ady -->
```python
type Flight_Number_T is Natural                      # a name: documents, refuses nothing
from units import metre_T, second_T
type Distance_T is metre_T                           # an alias: the same type, named for the quantity
type Duration_T is second_T
type Speed_T is Distance_T / Duration_T              # a relation: speed x duration is distance
type Altitude_T is 30.48 * Distance_T                # a scale: a flight level, hundreds of feet
type Degree_T is distinct float
type Latitude_T is Degree_T range -90 .. 90          # a range: values outside it are refused
type Bearing_T is Degree_T mod 360                   # a wrap: 370 is 10
type Callsign_T is str where c: c == /^[A-Z]{3}\d{1,4}$/   # a check: any predicate
```

None of it is a feature to learn separately. The first line costs nothing and
already helps a reader; each rung after it is bought only for the quantity
whose mix-up would hurt. `float range 0..1` and `float where 0 <= x <= 1` say
the same thing about the values; the difference is how a bad one is met, which
is a stop at its line for a range, and a failure the caller must handle for a
check. The sections below take the rungs in turn, each with the bug that
justifies it.


### Aliases document, and `distinct` enforces

An advocacy document that overclaims is worth less than no document, so,
precisely: **a scalar type alias is documentation; a distinct type is
enforcement.**

<!-- from: EXAMPLES/DOC/why_alias_snippets.ady -->
```python
type Velocity_T is float
type Height_T is float

let v: Velocity_T = 250.0
let h: Height_T = v          # an alias: compiles, on both backends
```

`Velocity_T` gives you the name in the signature, in the review and in the
grep, and by the argument above that is most of the benefit. It does not
give you the compiler refusing to put a speed where a height belongs. `distinct`
does:

<!-- from: EXAMPLES/DOC/why_alias_snippets.ady -->
```python
from units import metre_T, second_T
type Distance_T is metre_T               # the quantity, named where a signature reads it
type Duration_T is second_T
type Speed_T is Distance_T / Duration_T  # metres per second: a unit made from two others

def flown(speed: Speed_T, time: Duration_T) -> Distance_T:
    return speed * time           # Speed x Duration is Distance: the type says so

let speed: Speed_T = 250.0        # a literal takes the type it is given to
let far: Distance_T = flown(speed, 2.0)
# let wrong: Distance_T = speed   -- refused, on both backends
# let bad: Distance_T = speed * speed  -- refused: speed times speed is not a distance
```

A `metre_T` (the stdlib's, `distinct float`) keeps everything a `float` can do — with another `metre_T`. It
mixes with nothing else: not a `float` variable, not a `Speed_T`, not a
`second_T`. It is Ada's derived type, and like Ada it lets a literal take
whatever type its context asks for, so `250.0` needs no ceremony.

Two of those lines are aliases, and they are there for the reader.
`metre_T` says how the quantity is measured, and comes from the stdlib. `Distance_T` says what it is, which is what a signature
needs: `flown(speed, time) -> Distance_T` reads as physics, and the day the
program counts in something else only the declaration changes. The alias is
the same type under a second name, so there is nothing to convert, and a
`Distance_T` goes where a `metre_T` is wanted, in either direction. What the
stdlib declares from nothing is only the basic units, one `distinct float` for each
measure; a speed, an altitude or a latitude is always made from them, so
that no quantity in the program is a bare `float` that someone has to
remember the meaning of. The alias is read within the module that declares
it.

The fifth line is the one that matters. A unit is not only a name that
refuses to mix; it is a *relation*, and most of what goes wrong with
quantities goes wrong when they meet. `type Speed_T is Distance_T / Duration_T`
says what dividing a distance by a duration makes, and everything else follows from it:
speed times duration is distance, in either order, and distance over speed is duration.
`flown` needs no `float()` on the way in and no conversion on the way out,
and the compiler checks the one line where the units meet, which is the line
a reviewer would read anyway. What it does not say does not exist: `speed *
speed` is refused, because speed times speed is not a speed, and `distance *
duration` because nobody declared a metre-second. Multiplying by a plain number
scales, so `speed * 2.0` is still a speed.

### Money, in dollars and euros

The commoner case is money, and it is the same idea. An amount of dollars is
not a number: it cannot be added to euros, or squared, or passed where euros
are wanted — but it can be scaled by a quantity, a tax rate or a discount,
which are plain numbers. The exchange rate is a unit of its own, euros per
dollar, and once it is declared the conversion routine type-checks itself:

<!-- from: EXAMPLES/DOC/why_alias_snippets.ady -->
```python
type Dollar_T is distinct float
type Euro_T   is distinct float
type Rate_T   is Euro_T / Dollar_T   # euros per dollar

def to_euro(amount: Dollar_T, rate: Rate_T) -> Euro_T:
    return amount * rate             # dollars x (euros per dollar) is euros

const Max_Allowed_Quantity: int = 100
type Quantity_T is 0 .. Max_Allowed_Quantity   # never negative, never absurd

let price: Dollar_T = 19.99
let quantity: Quantity_T = 3
let rate: Rate_T = 0.92
let euros: Euro_T = to_euro(price * quantity, rate)   # a count scales a price
# let bad: Dollar_T = price + euros  -- refused: dollars plus euros
# let sq: Dollar_T = price * price   -- refused: dollars squared
```

The quantity is a type too, and for the same reason: a bare `int` says how a
count is stored, `Quantity_T` says it is never negative and never above
`Max_Allowed_Quantity`. Nim holds it to that — a literal outside the range
does not compile, and a computed one stops the program at its line — so a
refund entered as a quantity of minus three is a crash on the line that made
it, not a negative total in a ledger. (The Python backend keeps a plain
`int` for a range, so there the check is Nim's.)

The mistakes this catches are the ones that reach production: a total that
adds a dollar figure to a euro figure, a conversion applied twice, or applied
the wrong way round. `usd / rate` does not compile, because dividing dollars
by euros-per-dollar is not a currency. `TESTS/test_money.ady` is a whole
order — lines, tax, a discount, a budget, and a conversion of each line — and
the compiler holds every step to it.

Nim's ecosystem has libraries that do this for every combination
automatically, tracking the exponent of each base unit. I chose the other
end deliberately. Here every combination a program uses has a name, and the
name is in the signature, in the grep and in the compiler's message —
`Speed_T`, not an exponent vector. The price is writing down the
combinations, which a program has to name to be read anyway, and the gain is
that there is nothing to learn beyond `type C is A / B`.

### Scaled units: kilometres and miles

Kilometres and miles are the next step, and the one most languages stop at.
A distance in kilometres is not a distance in metres, and the bug is rarely
the missing multiplication; it is the multiplication done twice, or in the
wrong direction, or not at all because both sides were `float`. Adascript
lets a unit say what multiple of another it is, and the conversions are
generated from that one line:

<!-- from: EXAMPLES/physics_calc.ady -->
```python
const METRES_PER_MILE: float = 1609.344         # exact, by definition

from units import metre_T, second_T, kilogram_T

type Distance_T          is metre_T             # the quantity, as a signature reads it
type Duration_T          is second_T
type Mass_T              is kilogram_T

type Distance_in_km_T    is 1000.0 * Distance_T            # a km is 1000 m
type Distance_in_miles_T is METRES_PER_MILE * Distance_T   # a mile is 1609.344 m
```

`type Distance_in_km_T is 1000.0 * Distance_T` says a kilometre is a thousand
metres. It is a unit of its own: a mile plus a metre is refused, and so is a
mile divided by a time, because no one declared miles per second. The way
across is a conversion that is written where it happens, `Distance_T(mi)`
to multiply and `Distance_in_miles_T(d)` to divide, and nobody has to write
`* 1609.344` or remember which way it goes. A speed scales the same way, so
`Velocity_in_kmh_T(average)` and `Velocity_in_mph_T(average)` are one call
each, and the round trip is checked in the example rather than trusted:

<!-- from: EXAMPLES/physics_calc.ady -->
```python
    let marathon_mi: Distance_in_miles_T = 26.2188
    let marathon_m:  Distance_T          = Distance_T(marathon_mi)
    let average:   Velocity_T = Distance_T(marathon_mi) / record_t
    print(f"                      {Velocity_in_kmh_T(average):.4f} km/h")
    let back_mi: Distance_in_miles_T = Distance_in_miles_T(marathon_m)
    assert near(float(back_mi), float(marathon_mi), 1e-9)
```

The conversion converts by itself, so a program never carries the factor
around. A route check measures in metres and reports in kilometres, and the
line that crosses between them says only which unit it wants:

<!-- from: EXAMPLES/MAP_UTILS/route_check.ady -->
```python
    let across: metre_T = cross / length                    # a square over a length: a length
    let along: metre_T = dot / length
    return Fix_T(Kilometers_T(along), Kilometers_T(abs(across)), side_of_track(across))
```

Written out by hand it would be `Kilometers_T(float(along) / 1000.0)`: correct, and exactly
the arithmetic that goes wrong when someone writes `* 1000.0` instead, or
divides a value that was already in kilometres. With the factor in one
declaration, `float(metre_T(k))` is the number of metres in `k`, on the Nim
backend and the Python one alike.

### The Mars Climate Orbiter

The best-known unit failure in spaceflight is this one. On 23 September 1999 the
Mars Climate Orbiter reached Mars about 57 km above the surface, not the planned
226 km, and was lost. The ground software wrote the thruster impulses of its
wheel-desaturation burns in pound-force seconds; the navigation software read
them as newton-seconds, as the interface specification said it should. Every
routine was correct and every number was right. One factor of 4.45 sat between
two programs that both held the value in a `float`, so nothing could notice.
In Adascript the two units are two types, and one line says how they relate:

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
type Impulse_T  is Mass_T * Speed_T                        # N s, which is kg m/s: what the navigation expects
type Impulse_in_lbf_s_T is 4.4482216152605 * Impulse_T    # one pound-force second is 4.448 N s
```

The navigation takes an `Impulse_T`, the file is in `Impulse_in_lbf_s_T`, and the
call that was the mission's loss does not compile:

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
#     let wrong: Speed_T = speed_change(SMALL_FORCES, SPACECRAFT)
```

The way across is the conversion, on the line where the units meet, and a
reviewer can see it:

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
def in_newton_seconds(file: [*]Impulse_in_lbf_s_T) -> []Impulse_T:
    return [Impulse_T(p) for p in file]
```

`EXAMPLES/mars_climate_orbiter.ady` runs the whole thing with made-up numbers:
thirty small burns, a cruise of eight months, and the 4.45 between the right
speed change and the one the 1999 navigation took, which drifts the spacecraft
by about 173 km, the order of the real miss. The Makefile checks that the wrong
call is refused. What it takes is one declaration, which the program needed
anyway to be read; and the mistake that cost a spacecraft becomes an error on
the line that made it.

### Constants in the unit they are read in

A constant is best declared in the unit it is read in, and converted where it
is used. The Earth-Moon landing simulation (`EXAMPLES/MOON/moon_sim.ady`)
keeps its altitudes the way the mission plan gives them, in kilometres, and
the arithmetic that needs metres says so on the line that needs them:

<!-- from: EXAMPLES/MOON/moon_sim.ady -->
```python
    const LEO_ALT: Kilometers_T = 200.0
    const LOI_PERI_ALT: Kilometers_T = 100.0
```

<!-- from: EXAMPLES/MOON/moon_sim.ady -->
```python
        let r0: metre_T = R_EARTH + metre_T(self.LEO_ALT)
```

There are two reasons to prefer it to `const LEO_ALT: metre_T = metre_T(Kilometers_T(200.0))`.
The declaration reads like the number in the mission plan, with no conversion
to check by eye, and it prints in its own unit (`{self.LEO_ALT:.0f} km`)
without converting back. And the compiler holds every use to it: write
`R_EARTH + self.LEO_ALT` and it does not compile, because metres plus
kilometres is not a sum. A conversion forgotten in a constant that was
converted once, at the top, cannot be found; a conversion forgotten at a use
is refused on that line. The conversion is not a cast to be avoided: it is the
one place where the program says that a kilometre is a thousand metres.

### Money in whole cents

Money is where a conversion has to state its *policy*, and the same
declaration does it. Keep the ledger in whole cents, an `int`, so that sums,
counts and splits are exact; see it in dollars, a float, for tax and exchange
rates; and the only way back to cents is a conversion that rounds, to the
nearest cent with halves away from zero, written on the line where it
happens:

<!-- from: TESTS/test_cents.ady -->
```python
type Dollar_in_cent_T is distinct int
type Dollar_T         is 100 * Dollar_in_cent_T
type Euro_in_cent_T   is distinct int
type Euro_T           is 100 * Euro_in_cent_T
type Eur_per_usd_T    is Euro_T / Dollar_T      # a rate that changes: a value

def to_euro(amount: Dollar_in_cent_T, rate: Eur_per_usd_T) -> Euro_in_cent_T:
    return Euro_in_cent_T(Dollar_T(amount) * rate)    # the one rounding
```

<!-- from: TESTS/test_cents.ady -->
```python
assert line // 3 == price
assert Dollar_in_cent_T(Dollar_T(1.005)) == 101  # 1.005 * 100 is 100.49999999999999
assert Dollar_in_cent_T(Dollar_T(-0.125)) == -13
let tax: Dollar_in_cent_T = Dollar_in_cent_T(Dollar_T(line) * 0.08)
assert tax == 480                                # 479.76 cents
```

The cents are never silently a float: cents times `1.5` is refused, cents
plus dollars is refused, cents made from a float is refused, and a fractional
factor such as `0.5 * C_T` is refused when the type is declared. Float
arithmetic on money is where a lost cent comes from, and here it can only
happen at a conversion you can point at.

A distance in metres, kilometres and nautical miles shows how they are used
together. The metre is the base unit, and the other two are declared as
multiples of it:

<!-- from: EXAMPLES/distance_units.ady -->
```python
type Distance_T is distinct float                     # metres
type Distance_in_km_T is 1000.0 * Distance_T          # a kilometre is 1000 m
type Distance_in_nm_T is 1852.0 * Distance_T          # a nautical mile is 1852 m, by definition
```

Each value is written in the unit it is given in, and a mixed sum goes through
the base unit, on the line where the conversion happens:

<!-- from: EXAMPLES/distance_units.ady -->
```python
let runway: Distance_T = 3200.0                       # given in metres
let transfer: Distance_in_km_T = 12.5                 # the road leg, given in kilometres
let sector: Distance_in_nm_T = 40.0                   # the flight leg, given in nautical miles

# Mixing them goes through the base unit, where the conversion is written:
let total: Distance_T = runway + Distance_T(transfer) + Distance_T(sector)
```

The total prints as `89.780 km = 48.477 nm = 89780.0 m`, and reading it in
another unit is the same conversion the other way:
`Distance_in_nm_T(total)`. `runway + transfer` is refused, metres plus
kilometres, and so is `let wrong: Distance_in_nm_T = transfer`; the
compiler's message names both types.

Conversion functions are no longer required. In the aerospace code I have
worked on, mixing metres and nautical miles meant a pair of hand-written
helpers (`m_to_nm`, `nm_to_m`), each with its factor of 1852 typed in by
hand, each a place to get the factor or the direction wrong, and neither
known to the compiler. Here the conversion factor is part of the type
declaration, and the compiler enforces it transparently: the factor is written
once, as in `type Distance_in_km_T is 1000.0 * Distance_T` above, and every
conversion in either direction is derived from that line. A nautical mile
is declared the same way, as `1852.0` metres. There is no function to write,
to test or to call by mistake.

This is, as far as I know, unusual. Most languages give you either a units
library that tracks exponents and is invisible at the call site, or nothing.
Here the scale is one line, the conversion in both directions comes with it,
and the rounding policy is a visible call. One honest limit: scaled units are
Nim only. A conversion depends on the type of its argument, which the Python
backend cannot always see, so `ady2py` refuses the declaration with a message
saying the program is built by `ady2nim` only, and `make test` checks that it
does. Plain `distinct` units and derived units such as `Speed_T` work on both.

### Narrowed and wrapping ranges

A unit can also be narrowed to a range, and a range can be made to wrap. A
latitude is a `Degree_T` that is only ever between -90 and 90, and it goes up
to a `Degree_T` with no cast but comes down only through a checked
conversion:

<!-- from: TESTS/test_narrowed_type.ady -->
```python
type Degree_T is distinct float
type Latitude_T is Degree_T range -90 .. 90
type Longitude_T is Degree_T range -180 .. 180
```

<!-- from: TESTS/test_narrowed_type.ady -->
```python
    let lat: Latitude_T = Latitude_T(45.5)
    let wide: Degree_T = lat                  # up to the parent: no cast
    let sum: Degree_T = lat + Degree_T(1.0)  # arithmetic is the parent's
    let back: Latitude_T = Latitude_T(sum)     # down: checked
```

Latitude and longitude are siblings, so a point built with the two swapped does
not compile, which two plain `Degree_T` would have let through. A bearing is
the other case: 360 is north again, so the type wraps rather than refuses, and
the `modulo` helper that every bearing calculation carries is gone:

<!-- from: TESTS/test_mod_type.ady -->
```python
type Degree_T is distinct float
type Bearing_T is Degree_T mod 360
```

<!-- from: TESTS/test_mod_type.ady -->
```python
    let b: Bearing_T = Bearing_T(-10.0)
    show(b)                                    # up to the parent, no cast
    show(turn(b, Degree_T(30.0)))
    show(turn(Bearing_T(350.0), Degree_T(20.0)))
```

That prints 350.0, 20.0 and 10.0, on both backends, with the sign of the
divisor that Python's `%` has. The operators read as the mathematics does,
because a name may be defined more than once for different parameter types:
`velocity * t` is a distance and `velocity * 2.0` a velocity, and `a * b` of two
vectors is their dot product, where the code would otherwise carry `over`,
`per` and `dot_product` helpers.

### An index that comes round

The same type earns its keep where an index must come round. A ring buffer's
index is a mod type, and it is also the type of the array it indexes, so the
capacity is written once and there is no `% CAPACITY` and no cast anywhere in
the class:

<!-- from: TESTS/test_ring_buffer.ady -->
```python
const CAPACITY: int = 4
type Index_T is mod CAPACITY
type Count_T is int range 0 .. CAPACITY      # how many are held: 0 to CAPACITY, one more than an index

class Ring:
    var items: [Index_T]int
    var head: Index_T                  # a mod type starts at 0
    var tail: Index_T
    var count: Count_T

    def push(self, x: int):
        self.head += 1                 # a literal is an Index_T; it comes round at CAPACITY
        self.items[self.head] = x      # head is the newest slot
        if self.count == CAPACITY:
            self.tail += 1             # full: the oldest is overwritten
        else:
            self.count += 1

    def pop(self) -> ?int:
        if self.count == 0:
            return None
        self.tail += 1                 # tail is the slot last read
        self.count -= 1
        return self.items[self.tail]

    def latest(self, back: Index_T) -> int:
        return self.items[self.head - back]         # back = 0 is the newest
```

The count is a range type, not a mod type: it runs from 0 to the capacity,
one value more than an index has, and a full buffer must not wrap to empty. The
types say which is which.

### A type that carries its check

A bare `str` is where this matters most, because a string will hold anything.
A callsign, a date and the name of a zone are all `str`, so any of them goes
where any other is wanted, and any text at all goes where a callsign is wanted.
`distinct` fixes the first of those and not the second:

<!-- from: EXAMPLES/DOC/why_alias_snippets.ady -->
```python
type Callsign_T is distinct str
let loose: Callsign_T = "not a callsign !!"    # compiles: nothing says which strings are callsigns
```

A `Callsign_T` can no longer be taken for a zone's name, but `"not a callsign
!!"` is one. So a bare `str` has to be validated somewhere, and the question is
where. In most code it is a function the caller is trusted to call, which
returns a string again. In the geo-server example the rule is one line of the
type, and there is no other way to make a callsign:

<!-- from: EXAMPLES/GEO_SERVER/geo_server.ady -->
```python
type Callsign_T is str where c: c == /^[A-Z][A-Z0-9-]{1,11}\z/
```

`Callsign_T("sentinel")` is a failure that says what was offered, and
`Callsign_T("CA-1")` is a callsign. A plain `str` does not go where a callsign
is wanted, because nobody has checked it, and a callsign goes up to `str`
where text is wanted. A date, a period and a sequence number are the same
case, and the rest of this section is about them.

A range says a number is between two bounds. Much of what makes a value valid
is not a range: a date is digits, a period is three of them, a probability
table adds up to one. The usual answer is a function that checks and returns a
code, `check_date(text) -> (str, Rc_T)`, which every caller has to remember to
call, and whose result is a plain string again, so that nothing downstream can
tell the checked from the unchecked. Ada 2012 has the idea, as a subtype with a `Dynamic_Predicate`, and Adascript
takes it from there. What it changes is how the check is met. The checked type
is a type of its own, not a subtype that mixes freely with its base, so the only
way in is the check; and the check does not raise, it returns a failure the
caller must deal with, which is the same rule as everywhere else. Adascript puts
the check in the type:

<!-- from: EXAMPLES/CFMU/ftps_common.ady -->
```python
type Period_T is str where p: p == "" or p == /^\d{3}$/
type Date_T   is str where d: d == /^\d+$/ or d == ""
type Sequence_T is str where s: s == "" or s == "ALL" or s == /^\d$/
```

The condition is any expression over the one variable. A `Date_T` is a type of
its own: it goes up to `str` where a string is wanted, but a `str` does not
come down to it. The only way in is the check, `Date_T(text)`, and the check
can fail, so it is a `Date_T | !ParseFailure_T`, taken like any other failure.
Past the guard the value is known to be valid, and a function that takes a
`Date_T` has nothing to validate:

<!-- from: EXAMPLES/CFMU/ftps_list.ady -->
```python
let sd_val: Date_T | !ParseFailure_T = Date_T(start_date)
if sd_val is ParseFailure_T:
  refuse("start_date", "numeric", sd_val)
```

The base can be any type, and the variable can be left out, in which case the
condition speaks of `x`. A probability is `type Prob_T is float where 0 <= x <=
1`, which says what `float range 0..1` says but refuses with a value instead of
trusting the caller. And a check can be about a whole: a distribution over the
faces of a die is a table of probabilities that adds up to one, and the two
levels are two types, because the entries being fine does not make the table
fine:

<!-- from: TESTS/test_where_type.ady -->
```python
type Dice_T is 1 .. 6
type Pdf_T is [Dice_T]Prob_T where pdf: abs(sum(pdf[d] for d in Dice_T) - 1.0) < 1e-9

def loaded() -> Pdf_T | !ParseFailure_T:
    var table: [Dice_T]Prob_T = {:}
    for d in Dice_T:
        do:
            p <- Prob_T(0.2)            # each 0.2 is a fine Prob_T ...
        table[d] = p
    return Pdf_T(table)             # ... but six of them add up to 1.2: refused here
```

Arithmetic on a checked number is the base's, so a sum of probabilities is a
plain float and never claims to have passed the check. Nim only for now:
`ady2py` refuses the declaration.

What the same probability costs elsewhere shows what the line is worth. In Ada
it is a subtype, which a plain `Float` mixes with and which raises when it is
violated:

```ada
subtype Probability is Float range 0.0 .. 1.0;
```

In Rust it is a struct, a constructor that returns a `Result`, and an accessor,
for every checked type:

```rust
pub struct ProbError(f64);
pub struct Prob(f64);
impl Prob {
    pub fn new(x: f64) -> Result<Prob, ProbError> {
        if (0.0..=1.0).contains(&x) { Ok(Prob(x)) } else { Err(ProbError(x)) }
    }
    pub fn get(self) -> f64 { self.0 }
}
```

In Python it is a function that raises, and returns a plain `float` that nothing
downstream can tell from an unchecked one:

```py
def prob(x: float) -> float:
    if not 0 <= x <= 1:
        raise ValueError(x)
    return x
```

In Adascript it is one line, and the conversion that checks it returns the
failure instead of raising:

<!-- from: TESTS/test_where_type.ady -->
```python
type Prob_T is float where 0 <= x <= 1
```

### What is checked where

Not every name should be distinct. Conversions are work, and a value that
is meant to mix with its base — an epoch plus a number of seconds — is
better as an alias. Make distinct the quantities whose mixing would be a
bug: units, and the identifiers of different things that happen to share a
representation.

What is checked where is not symmetric, and it is worth saying so. On the
Nim backend the compiler checks every use. The Python backend has no type
checker of its own, so it works out the unit of arithmetic over typed names
— `v * 2.0 + d` is a speed plus a distance — and refuses what it can see: a
declaration or an assignment of another type, and an operator between units
that does not exist. A wrong argument is caught when the same source is built
for Nim — which is one more reason `make test` builds everything for both.

Where else Adascript enforces a distinction: an enumeration is a real
type (index an `[E]T` with a string and it will not compile), `Natural` and
`Positive` are range-checked at run time, a record is nominal, `?T` is not
`T`, and `Path` is a distinct string — `p = s` is an error on both backends
and `Path(s)` is how you mean it.

### Using the units

The rungs above are tools, and a program uses them in a fixed order. It helps
to know the order before reading the declarations.

1. **Declare the base units distinct, once, in the unit the program computes
   in.** Metres, seconds, kilograms: the stdlib's `units` module has them
   (`metre_T`, `second_T`, `kilogram_T`), each a `distinct float`, and nothing else in the program is a bare `float` that means
   a length. A program that wants its signatures to read as quantities names
   the unit for how it is measured and the alias for what it is, `Distance_T
   is metre_T`; the Orbiter below does so for mass, distance and duration. Do not
   declare your own `distinct float` for a metre or a second: two libraries that
   did would hold two types that never mix.
2. **Derive the rest from them.** A speed is `Distance_T / Duration_T`, an impulse
   is `Mass_T * Speed_T`. Do not declare a speed as a second `distinct float`:
   then nothing relates it to the distance and the time it came from, and the
   compiler cannot refuse `speed * speed` where a distance is wanted.
3. **Scale for the units the outside world speaks.** A pound-force second or a
   kilometre is a multiple of a unit you already have. Declare it as one, and
   write the conversion only where the value crosses.
4. **Check at the boundary, then work in the plain unit.** A number that comes
   from a file, a sensor or a person has to pass a test once. Declare a
   checked type over the unit, convert on the way in, and the rest of the
   program keeps using the unit, because a checked value goes back up to its
   base without a cast.

<!-- from: EXAMPLES/mars_climate_orbiter.ady -->
```python
from units import kilogram_T, metre_T, second_T

type Mass_T     is kilogram_T
type Distance_T is metre_T
type Duration_T is second_T
type Speed_T    is Distance_T / Duration_T                 # m/s
type Impulse_T  is Mass_T * Speed_T                        # N s, which is kg m/s: what the navigation expects
type Impulse_in_lbf_s_T is 4.4482216152605 * Impulse_T    # one pound-force second is 4.448 N s
```

Step four is the one that is easy to miss. A derived unit cannot carry a range
of its own, because a division is not a place where a value is made. What can
carry one is a type declared over it:

<!-- from: TESTS/test_where_type.ady -->
```python
type Legal_Speed_T is Speed_T where v: float(v) <= 299_792_458.0    # no faster than light
let legal: Legal_Speed_T | !ParseFailure_T = Legal_Speed_T(pace)
let up: Speed_T = legal                      # up to the unit, no cast
let warp: Legal_Speed_T | !ParseFailure_T = Legal_Speed_T(leg / Duration_T(1e-9))
assert warp is ParseFailure_T
```

`Legal_Speed_T` is a speed in every way that matters: it has `Speed_T`'s
arithmetic, and it goes up to `Speed_T` freely. What it adds is that the only
way in is a conversion that can say no. Use it where a speed enters the
program, not on every speed inside it: a value that has passed once does not
need to pass again, and arithmetic on it is a plain `Speed_T`, which makes no
claim.

What to avoid follows from the same order. A bare `float` in a signature that
means a unit gives the compiler nothing to check. A second base unit for
something that is a ratio of two others gives it nothing to relate. And a
conversion written inside the computation, rather than at the boundary, is the
factor applied twice that the Orbiter lost a spacecraft to.

---

## Test the type, then use the value

Most languages make you say a thing twice: once to ask what a value is, and
again to get it back as that. Python's `isinstance` leaves the name as wide as
it was, so the next line still carries a cast, an `assert`, or a comment
promising it is fine. TypeScript narrows, but only by its own rules. Nim's
variant objects need the field spelled out in every branch.

Adascript narrows on the test, and the test reads as the sentence:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/frontend/dijkstra_js_events.ady -->
```python
class Selection:
    var what: NodeView | EdgeView | None

    def change_cost(self):
        let picked: NodeView | EdgeView | None = self.what
        if picked is EdgeView:
            picked.change_cost()

    def remove(self):
        let picked: NodeView | EdgeView | None = self.what
        case picked:
            when NodeView | EdgeView:
                picked.delete()
            when None:
                pass
```

Only an edge has a cost to change, so `change_cost` asks `picked is EdgeView`, and
on the next line `picked` is an `EdgeView`, not "maybe an `EdgeView`". Either
kind can be deleted, so `remove` names both in one `when`; the body is checked
once for each of them, and it would not compile if one of them had no
`delete`. The third arm says there is nothing to delete.

That is how the Dijkstra page deletes what the reader selected. There is no `Selected_T`
declared for it, no tag field to keep in step with the value, no cast, and no
branch that can be forgotten: a `case` over a union names every member, or says
`when others`, as one over an enum does. The same code runs on both backends,
a chain of class tests on Python and a `OneOf` variant on Nim.

The rule behind it is short, and it is why the code reads the way it does:

- `x is A` tests the **type**. `A` is a type, and inside the branch `x` is an `A`.
- `x == A` tests the **value**. `A` is a value, an enum member or a constant,
  and nothing is narrowed.
- `case x:` over a **union** tests the type, member by member, and narrows as
  `is` does; over an enum, an int or a string it compares values. A union has
  members and no values to compare, so there is nothing for the two readings to
  collide on.

So you test the type once, and use the value as the thing it now is. `A | B |
None` says "one of these, or nothing" in the signature, where a reader looks
for it, and the `case` that takes it apart is checked against that line. It
costs nothing to write, which is what makes people write it.

---

## A failure belongs in the signature

A signature that says `-> Path` is telling half the truth when the function
can fail. C returns an error code nothing obliges anyone to check. The shell sets `$?` and
moves on. Python and Ada raise an exception that appears nowhere in the
signature, so the reader has to know the body to know the contract. In
every case the failure is real and the page does not show it.

Adascript prefers that to an exception, and the reason is that the
handling is where you can see it. With an exception, what is done about a
failure is written wherever the handler happens to be -- a `try` some
distance up the call stack, or none at all -- and neither the call nor the
functions it passes through show anything. With a failure value the call
takes its result and either deals with it on the next line, next to what
caused it, or passes it up to its own caller -- which is one `do:` step, and
is in that function's signature too, so every caller can see it can fail and
decides where it is handled. The built-in shell and `Path` operations are
written this way too, and a failure that is dropped is refused.

Adascript lets the return type say both halves: `-> Path | !Failure_T`,
*either* a path *or* the failure that says why there is none; the `!`
marks which is which. A failure is a type like any other — an ordinary
record:

<!-- from: TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady -->
```python
type ErrKind_T is enum CMD_FAILED, NOT_A_BACKUP_DEST, SOURCE_MISSING, STILL_RUNNING, NO_SPACE, BAD_ARGUMENTS

type Failure_T is record:
    kind:   ErrKind_T
    detail: str    # the command that failed, the path at fault, or what went wrong
    stderr: str    # what a failed command said; "" for any other failure
    fix:    str    # a command that would fix it; "" when there is none
```

A function returns its value or a failure, and there is nothing to wrap —
the type of what is returned says which it is:

<!-- from: TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady -->
```python
def run_checked(cmd: str, ssh: ?SSH = None) -> str | !Failure_T:
    let r: CmdResult = run_cmd(cmd, ssh)
    if r.returncode != 0:
        return failure(CMD_FAILED, cmd, r.stderr.strip())
    return r.stdout
```

A chain of steps that must all succeed is written as a chain, and the
first failure leaves the function with its reason intact. Nothing in it is
error-handling code; the `do:` block is the error handling:

<!-- from: TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady -->
```python
    # One railway: the lock is released only once `latest` points at this
    # backup. If the link fails, the lock stays, and the next run finds an
    # interrupted backup to resume rather than a finished one with no link.
    do:
        rm_file(dest_f / "latest", dest_is_ssh(ssh))
        ln_s(Path(dest.name), dest_f / "latest", dest_is_ssh(ssh))
        rm_file(inprogress_file, ssh)
```

And one place, at the top, decides what the user is told and which status
the program exits with. `outcome is Failure_T` asks which of the two it
holds; a `case` over the failure's kind inside `report` is exhaustive, so a
new kind of failure nobody reports does not compile:

<!-- from: TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady -->
```python
    let outcome: None | !Failure_T = backup(
        ...
    )
    if outcome is Failure_T:
        report(outcome)
        quit(1)
```

The built-in operations that can fail are on these tracks already:

| The call | Its result | The failure's fields |
|---|---|---|
| `shell: cmd` | `str \| !ShellFailure_T` | `command`, `code`, `stderr` |
| `p.mkdir()`, `p.write_text(s)` | `None \| !PathFailure_T` | `op`, `path`, `base`, `reason` |
| `p.relative_to(base)` | `Path \| !PathFailure_T` | `op`, `path`, `base`, `reason` |
| `p.read_text()` | `str \| !PathFailure_T` | `op`, `path`, `base`, `reason` |
| `p.read_lines()` | `[]str \| !PathFailure_T` | `op`, `path`, `base`, `reason` |
| `parse_float(s)` | `float \| !ParseFailure_T` | `what`, `text` |
| `parse_int(s)` | `int \| !ParseFailure_T` | `what`, `text` |
| `parse_enum(E, s)`, `parse_enum(E, n)` | `E \| !ParseFailure_T` | `what`, `text` |
| `input(prompt)`, `stdin.readLine()` | `str \| !InputFailure_T` | `reason` |

This is railway-oriented programming — Scott Wlaschin's name for it — and it
is not new: F#'s and Rust's `Result` and Zig's error unions all do it. What the notation adds is
that it costs nothing to write. The test narrows the name — past
`if r is Failure_T: return`, `r` *is* the path, with nothing to unwrap —
and the same source runs on both backends.

The case for it is not a theory. `rsync_time_machine.ady` is a port of a
real backup tool, and it ignored the exit status of every command that
changed something. Rewritten this way, it gave up
three bugs that `make test`, which only compiled it, had never seen:

- A failed `ln -s latest` was ignored: the lock was removed and the run
  reported success, with no `latest` link at all. It now fails, names the
  command and what it printed, and keeps the lock so the next run resumes.
- On a full disk it was meant to expire the oldest backup and retry. It
  expired the newest — the one in progress — freed nothing, retried a
  hundred times and exited 0, with `latest` pointing at a directory it had
  just deleted.
- Every retry reused one log, and rsync appends: the first "No space left"
  was read again after every attempt, successful or not. With the first
  bug fixed, it went on to expire every backup there was.

The first bug is the kind the signature now prevents: once `ln_s` says
`-> None | !Failure_T`, it cannot be called and its failure thrown away. A
bare `ln_s(...)` as a statement does not compile, on either backend —
the result has to be taken, by a `do:` step, a test or a `return`. The
other two came to light because failures had become values a test could
look at. `TOOLS/RSYNC_TIME_MACHINE/test/rsync_time_machine_test.sh` now runs
the tool against real folders, with a disk that fills up; the old version
fails six of its fifteen checks.

### Even a constructor

In Python and Java a constructor cannot say that it failed: it returns nothing,
and the only way out is an exception. In Rust and Zig the question does not
arise, because there is no constructor, only a function by convention called
`new` or `init`. Swift comes nearest: an initialiser can fail, but `init?`
gives back nil and says nothing of why, and `init throws` is an exception
again. Adascript keeps the constructor and lets it fail with a *value*: the
signature names the failure type, the call is taken like any other failure, and
a failure that is dropped is refused. It is odd, once seen, that it was ever
otherwise: building a value from outside data is the commonest thing that can
go wrong, and the constructor was the one routine that could not say so. The
signature says it, as it does for any routine:

<!-- from: EXAMPLES/clsworkspace.ady -->
```python
    def __init__(self, data: JsonNode):
        self.data = data

    def __init__(self, payload: Json_T) -> None | !ConfigFailure_T:
        try:
            self.data = parseJson(str(payload))
        except JsonParsingError:
            return ConfigFailure_T("CONFIG payload", "is not JSON")
        if self.data.kind != JObject or not self.data.hasKey("name"):
            return ConfigFailure_T("CONFIG payload", "is not a workspace")
```

A `return` of the failure abandons the construction; reaching the end builds the
object. The first constructor cannot fail and says nothing, and the two
overload by their parameters. The call of the second is a `WorkspaceConfig |
!ConfigFailure_T`, taken like any other failure, so that a commit subject which
is not ours is skipped where it is read instead of being caught somewhere else:

<!-- from: EXAMPLES/clsworkspace.ady -->
```python
            let config: WorkspaceConfig | !ConfigFailure_T = WorkspaceConfig(Json_T(rest))
            continue if config is ConfigFailure_T
```

A `do:` step takes it the same way, and a dropped failure is refused. Nim only
for now: Python's `__init__` returns nothing, so `ady2py` refuses the form.

### The same chain in other notations

[trcks](https://github.com/christophgietl/trcks) is a Python library for
railway-oriented programming, and its README has one small example: look up a
user by e-mail, then the user's subscription, then compute the fee, where each
of the first two can fail. Here is the function that chains the three, in
trcks's object-oriented style (the helpers return `("success", value)` or
`("failure", description)` tuples, typed as `Result[...]`, and the chain
needs `Wrapper` and the `map_*` methods):

```py
def get_subscription_fee_by_email(user_email: str) -> Result[FailureDescription, float]:
    return (
        Wrapper(core=user_email)
        .map_to_result(get_user_id)
        .map_success_to_result(get_subscription_id)
        .map_success(get_subscription_fee)
        .core
    )
```

Its functional style swaps the `Wrapper` for `pipe(user_email, get_user_id,
r.map_success_to_result(get_subscription_id), r.map_success(get_subscription_fee))`.
In Haskell the `Either` monad does it, with `do` notation, and in Rust it is
`Result` and the `?` operator:

```haskell
getSubscriptionFeeByEmail :: String -> Either Failure Double
getSubscriptionFeeByEmail email = do
  userId         <- getUserId email
  subscriptionId <- getSubscriptionId userId
  pure (getSubscriptionFee subscriptionId)
```

```rust
fn get_subscription_fee_by_email(email: &str) -> Result<f64, Failure> {
    let user_id = get_user_id(email)?;
    let subscription_id = get_subscription_id(user_id)?;
    Ok(get_subscription_fee(subscription_id))
}
```

In Adascript it is the `do:` block, and it is the whole chain; the full
program, which `make test` runs on both backends and compares, is
`EXAMPLES/trcks_example.ady`:

<!-- from: EXAMPLES/trcks_example.ady -->
```python
type Failure_T is record:
    description: str

def get_user_id(user_email: str) -> int | !Failure_T:
    case user_email:
        when "erika.mustermann@domain.org":
            return 1
        when "john_doe@provider.com":
            return 2
        when others:
            return Failure_T("User does not exist")

def get_subscription_id(user_id: int) -> int | !Failure_T:
    if user_id == 1:
        return 42
    return Failure_T("User does not have a subscription")

def get_subscription_fee(subscription_id: int) -> float:
    return float(subscription_id) * 0.1

def get_subscription_fee_by_email(user_email: str) -> float | !Failure_T:
    do:
        user_id         <- get_user_id(user_email)
        subscription_id <- get_subscription_id(user_id)
    return get_subscription_fee(subscription_id)
```

What differs is what each one asks the reader to know:

| | trcks (Python) | Haskell | Rust | Adascript |
|---|---|---|---|---|
| The two tracks | `Result`, `("success", x)` / `("failure", e)` tuples | `Either`, `Left` / `Right` | `Result`, `Ok` / `Err` | `T \| !Failure_T`; a plain `return` of a value or of the failure |
| The chain | `Wrapper` and `map_to_result`, `map_success_to_result`, `map_success`, or `pipe` with `r.map_*` | the `Either` monad, `do` and `pure` | `?` after each call | `x <- step()` in a `do:` block |
| A plain function in the chain | wrapped by `map_success` | `pure`, or `fmap` | called on the unwrapped value | called on the value |
| Where the failure types come in | a `Literal` per failure, joined with `\|` | a data type | an enum | one record, marked `!` |
| A dropped failure | a type checker may notice | a warning for an unused result | `#[must_use]` warns | refused by the compiler |
| Library to learn | `trcks` | the standard `Either` and `Monad` | the standard `Result` | none |

The Haskell and Rust versions are as short as the Adascript one, because
their languages were built around the idea, and an Adascript reader who knows
either will read the `do:` block as the same thing. The difference is for
everyone else: the chain is a block of two lines that reads top to bottom,
the types say what can fail, and there is no vocabulary to learn first.
Python gets there only by a library whose function names carry the meaning.

---

## Objections

**"Why not Ada?"** Ada has the typing and I took it. What it asks in return is
ceremony and a build, and its derived types need an operator written by hand
for every unit relation: a speed times a duration is a distance only because somebody wrote
`function "*"` for that pair. Here the relation is the line `type Speed_T is
Distance_T / Duration_T`, and the operators follow from it. Adascript is Ada's typing
in Python's syntax, and it also produces Python.

**"Why not F# units of measure, or a units library?"** F# is the closest
rival and the honest comparison. It tracks the exponent of each base unit, so a
speed is `m/s` and an area is `m^2` without anyone naming them, and that is more
general than what Adascript does. I chose the other end deliberately: every
combination a program uses has a name, and the name is in the signature, in the
grep and in the compiler's message. The price is writing the combinations down,
which a program has to name to be read anyway. Rust's newtypes work too, at the
cost of a struct, a constructor and the operator implementations for each unit.

**"Isn't this just more annotation?"** For a name, no: `type Altitude_T is
Natural` is one line and already documents. The strict rungs are paid for only
by the quantities whose mix-up would hurt, and a program with no such quantity
does not use them.

**"What does it cost?"** Writing the types down, and the split between the two
backends. Scaled units, failing constructors and types with a check are built by
`ady2nim` only today; `ady2py` refuses them with a message saying so. The last
section lists exactly what each backend does not do.

---

## What is not yet true

The Nim backend is the reference one; the Python backend is less
supported, and only Nim supports every feature. The gaps are listed per
backend, so you can see what each one will not do for you.

### Nim (`ady2nim`)

Everything in this document is built, except:

- **Which side a returned `T | !F` value is on** is read from its type. Where
  the backend cannot work the type out it assumes the value side, and Nim's
  own type check then refuses a failure put there by mistake: correct, but
  the message names the generated code rather than the line.
- **Exceptions** do not become failures: a call that raises is not turned
  into a `T | !F` at the boundary by itself, and there is no adapter yet.
- **Unions** are at most ten members. `A | B | None` is the optional of
  `A | B`: it reads as written, `case x:` takes `when A`, `when B` and
  `when None`, and behind the scenes it is `?Name` for a union type the
  transpiler declares for it.
- **Units cannot be raised to a power.** An area is `Length_T * Length_T`,
  declared by name; there is no `Length_T ** 2`. That is deliberately
  smaller than Nim's dimensional-analysis libraries.
- **A literal whose context Nim cannot see**, an argument to something that
  is not a known routine for one, needs the type written: `V(x)`.

### Python (`ady2py`)

Everything under Nim above applies here too. In addition, the Python
backend does not do these, and building the same source for Nim is what
catches them:

- **It does not check an argument's type**, so a wrong unit passed to a
  function, or a plain `f(3)` where a `T | !F` is expected, is not
  caught.
- **A conversion between two unrelated distinct types** is accepted and keeps
  the number: `Duration_T(d)` for a `Distance_T` `d`. Nim refuses it by
  name.
- **An untested failure used as a value** fails when that line runs, not
  before. Nim refuses it at compile time.
- **Unions** are at most ten members.
- **A constructor that can fail** is refused by `ady2py`: Python's `__init__`
  returns nothing, so the same source needs a function returning `C | !F` there.
- **A type with a check** (`type D is str where d: ...`) is refused by `ady2py`:
  there is no Python type to carry it, so the same source needs a validating
  function there.

---

## Why I wrote it

I started this language more than ten years ago as a dialect of Python. It was
called py2py then, because it generated valid Python from the dialect. I have
spent a long career in aerospace building complex systems, and I have written
them in C, C++, AWK, Bash, Ada, Python and Nim.

When optional typing was added to Python I was disappointed. It made Python
more verbose and added little compared with what explicit typing could give.
So I looked at Ada first, and then at Nim. Nim is a great language, inspired by
Python and by Ada. But none of the three satisfied me:

- **Python**'s type annotations are ugly, and nothing checks them.
- **Ada** is verbose.
- **Nim**'s syntax is sometimes weird, and its type syntax was not optimal.

---

## Further reading

- `README.md` — the language reference
- `DOCS/BOOK/` — the book, chapter by chapter
- `DOCS/ADASCRIPT_FOR_AWK.md` — for text and record processing
- `DOCS/ADASCRIPT_FOR_SHELL.md` — for scripts and system tools
- `EXAMPLES/` — every one of them compiled and run on both backends by
  `make test`

