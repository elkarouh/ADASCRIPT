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

Types and classes, one per concept. Enumerations for anything with a closed
set of values — a phase of flight, a message kind, a state. Records for
anything with parts. Names ending `_T` so a reader can see at a glance what is
a type.

<!-- from: EXAMPLES/DOC/why_snippets.ady -->
```python
type Callsign_T     is str
type Altitude_T     is Natural        # feet
type Velocity_T     is float          # knots
type Flight_Phase_T is enum CLIMB, CRUISE, DESCENT, HOLD

type Aircraft_T is record:
    callsign: Callsign_T     = ""
    phase:    Flight_Phase_T = CLIMB
    altitude: Altitude_T     = 0
    speed:    Velocity_T     = 0.0
```

Four lines of vocabulary and a record, and the layer has a boundary.

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

Four lines, and the shape of the whole program is decided. A reader who has
seen those four lines knows what can be asked of this code and what cannot.

### 3. Only then, write what it does

By the time you get here the code is short, because the hard decisions are
already made and visible.

---

## The notation

Step 2 is why Adascript has a notation of its own for collections. Every
container is written as a **prefix on the element type**, so the declaration
reads left to right as a sentence:

| Written | Read as |
|---------|---------|
| `[]T` | a list of T |
| `{K}V` | a mapping from K to V |
| `{}T` | a set of T |
| `[E]T` | one T for each member of the enum E |
| `?T` | a T, possibly absent |
| `Fix_T is tuple:` | a named tuple, fields by name |

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
`[]T` eventually. What is Adascript's own is the *family*: that the set, the
enum-indexed array and the optional join the list and the mapping under one
rule, that the rule is "container first, element after, no brackets to
balance", and that they stack. I did not take it from another language,
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

There is no plumbing in it. `by_phase[a.phase]` works because the phase *is*
an index; `for phase in Flight_Phase_T` walks the domain in declaration order
and cannot miss a member; `ceiling[a.phase]` is a table lookup that cannot be
misspelled. None of that is clever. It is what happens when step 1 and step 2
were done first.

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
