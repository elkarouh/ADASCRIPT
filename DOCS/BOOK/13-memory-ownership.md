# Chapter 13 — Memory Ownership

Every value has to live somewhere, and something has to decide when it stops
living there. Python decides with a garbage collector: you never say, and the
runtime works it out, eventually. Nim's ARC decides at compile time: the
value is freed when its owner's scope ends, with no collector and no pause.

Adascript compiles to both, so it cannot pick one. What it offers instead is
a small vocabulary — `own`, `lent`, `move`, `drop`, `with own` — for writing
down what you already know about a value's lifetime, and one decorator,
`@virtual`, that changes what a value *is*: copied on every assignment, or
shared by every name that holds it. On Nim the vocabulary guides ARC, and
`@virtual` is the difference between an `object` and a `ref object`. On
Python most of the vocabulary is stripped, because the GC does not need
it — but every composite is already a reference, which is the fact the
rest of this chapter keeps coming back to.

This chapter starts with what happens when you write nothing down at all —
the default that decides whether assignment copies or shares, on a plain
`record` or `class`, with no annotation in sight — and then covers the
vocabulary for the cases the default gets wrong, and the three places where
the backends stop agreeing, which are the ones you have to know.

## 13.1 The vocabulary, and what it actually emits

Five forms. The middle column is what the Nim backend emits today, and the
right-hand one what Python gets; both were read out of the generated code
rather than from the design notes.

| Adascript | Nim | Python |
|---|---|---|
| `own x: T = e` | `var x: T = e` | `x: T = e` |
| `param: lent T` | `param: T` | `param: T` |
| `param: own T` | `param: sink T` | `param: T` |
| `move(x)` | `move(x)` | `x` (a plain alias) |
| `drop(x)` | `` `=destroy`(x); `=wasMoved`(x) `` | `del x` |
| `with own x = e:` | `block:` with `var x = e` | `try:` / `finally: del x` |

Two of those rows deserve reading twice.

`lent` **emits nothing at all.** The Nim output for `def energy(f: lent
Frame_T)` is `proc energy(f: Frame_T)`. Nim chooses its own passing
convention for a large object, and it is generally the one you wanted, so
the annotation costs nothing — but it is a promise to the reader, not an
instruction to the compiler. Nothing checks that the callee does not store
what it borrowed.

`own` **on a declaration is `var`.** `own x: T = e` and `var x: T = e`
generate the same line. The word marks which name is responsible for the
value, for a reader deciding whether they may keep a reference to it.

That is worth saying plainly, because it sets the honest expectation for the
rest of the chapter: **these are annotations, not a borrow checker.** They
make intent legible and they let ARC do its job; they do not make a
lifetime mistake impossible. What they do instead is make it *nameable*,
which is most of the value in a language where the alternative is not
thinking about it at all.

## 13.2 Value types, reference types, and Adascript's pointer

Before deciding what to write down about a value's lifetime, it helps to
know what happens when you write nothing down at all — because the two
backends do not agree here either, and the disagreement has nothing to do
with the five words above. It is about plain assignment.

**On Nim, every composite is a value type unless you say otherwise:** a
`record`, a plain `class`, a `[]T`, a `{}`. Assigning one, appending it to
a collection, or passing it to a function copies it; two names never share
one value unless you go out of your way to arrange it. **On Python, every
composite is a reference:** assigning, appending, and passing all share the
one object, whether you meant to or not. Chapter 8 §8.1 already shows the
`[]T` case — "unlike Python, the Nim backend has value semantics for
seqs" — and a `record` and a plain `class` follow the same rule. It is
worth watching fail before it is worth being told:

```python
class Box:
    var value: int = 0

var boxes: []Box = []
var a: Box = Box()
a.value = 1
boxes.append(a)
a.value = 2
print "boxes[0].value =", boxes[0].value
```

```
Nim:    boxes[0].value = 1      # append copied the value that existed then
Python: boxes[0].value = 2      # boxes[0] and a are the same object
```

Nothing here used `own`, `move`, or `drop` — this is what an ordinary
`class` does with no annotation at all. It is also why the vocabulary in
§13.1 is about avoiding a *copy*: on a value type there is no shared
mutation to lose track of, because there was never any sharing.

### `@virtual`: the one word that means "pointer" on both backends

A `@virtual class` compiles to a Nim `ref object` (§9.4) — a
heap-allocated, reference-counted handle — and a Python object was always
one of those. Mark the same `Box` `@virtual` and the trap above closes, on
both backends at once:

```python
@virtual
class Box:
    var value: int = 0
```

```
Nim:    boxes[0].value = 2
Python: boxes[0].value = 2
```

This is the only annotation in the language that changes what plain
assignment *means*, rather than annotating intent around an assignment
that behaves the same either way. Reach for it when:

- **Several names, or a name and a collection, must see the same
  mutations.** A cache entry looked up by id, a graph node reached from
  several edges, a widget held by both its parent and an event queue.
- **A free function mutates what you hand it through more than one call.**
  A direct field assignment in a function's own body is enough for the
  transpiler to make that one parameter a Nim `var` for you — the same
  detection §9.2 describes for a method's `self`, generalised to any
  parameter of any function. But it looks at one body at a time: write
  `def bump(b): really_bump(b)` where `really_bump` does the assigning,
  and `bump`'s own body contains no assignment for the heuristic to find,
  so its `b` is never marked `var` — and Nim refuses to compile the call
  to `really_bump`, on a `record` exactly as on a plain `class`. It is a
  compile error, not a silent wrong answer, but it is one that stops
  existing the moment `Box` is `@virtual`: a reference is mutable through
  any handle, at any depth, and no parameter has to be inferred as
  anything.
- **Identity is the point, not the fields** — a linked list, a tree with
  parent pointers, any structure where "the same node" has to mean the
  same node rather than one that compares equal.
- **Cross-module dynamic dispatch** — the reason §9.4 introduces the
  decorator in the first place.

The cost is real, and it sits on the Nim side: a `@virtual` value is always
on the heap and always refcounted, where a plain `object` can live inline —
on the stack, or embedded in whatever contains it — and costs nothing to
tear down. That is the trade this section is about: a value type is cheap
and private by default, and `@virtual` buys sharing at the price of an
allocation. `lent` and `own` do not buy sharing; they buy back the "cheap"
half of that trade on a value type that was never going to be shared in
the first place — a `lent Frame_T` parameter reads a value that was never
copied to begin with, which is a different problem from the one `@virtual`
solves, and the two are not substitutes for each other.

One combination is worth flagging before the next section shows why:
`move` and `drop` on a `@virtual` value do not give you merely a different
number on each backend, the way they do on a record. On Nim they leave the
old name pointing at nothing, and reading it dereferences a null pointer.

## 13.3 A tour

`EXAMPLES/ownership_tour.ady` runs on both backends. A frame of samples,
big enough that copying it would be a waste:

```python
type Frame_T is record:
    """A block of samples. Big enough that copying it would be a waste."""
    id:      Natural  = 0
    samples: []int    = []


def load(id: Natural, n: Natural) -> Frame_T:
    """Build a frame. The caller becomes its owner."""
    var s: []int = []
    for i in 0 ..< n:
        s.append(i * i)
    Frame_T(id=id, samples=s)
```

**`lent` — I will read it and give it back.**

```python
def energy(f: lent Frame_T) -> Natural:
    var total: Natural = 0
    for v in f.samples:
        total += v
    total
```

The caller keeps ownership. The promise is threefold and worth spelling out,
since nothing enforces it: the callee will not mutate the value, will not
store it anywhere that outlives the call, and will not pass it on to
something that will.

**`own` on a parameter — hand it over and forget it.**

```python
def archive(f: own Frame_T) -> str:
    """Takes the frame. The caller's binding is dead after this call."""
    f"archived frame {f.id} ({f.samples'Length} samples)"
```

This is Nim's `sink`. The caller is giving the value away, so ARC may let the
callee consume it instead of copying. The caller's name is not usable
afterwards — not "should not be", *is not*: what it holds is undefined.

**`with own` — the scope is the lifetime.**

```python
    with own scratch = load(2, 4):
        print describe(scratch)
    print "scratch is gone"
```

**`move` — the same value, a new owner.**

```python
    own source: Frame_T = load(5, 4)
    own target: Frame_T = move(source)
    print describe(target)             # the same frame, under a new name
```

**`drop` — release before the scope ends.**

```python
    own big: Frame_T = load(4, 5)
    print describe(big)
    drop(big)                          # the memory goes back now
    print "big released early"
```

## 13.4 The two places the backends disagree

Everything above prints the same on both backends. These two do not, and
both involve reading a value that you have already given away — plus a
third, sharper case, once the value in question is a `@virtual` one.

### Reading a moved-from value

The last thing `ownership_tour.ady` prints is deliberately this:

```python
    print f"the moved-from value reports {source.samples'Length} samples"
```

```
$ EXAMPLES/ownership_tour | tail -3       # the Nim build
the moved-from value reports 0 samples

$ ady2py EXAMPLES/ownership_tour.ady -c   # the Python one
the moved-from value reports 4 samples
```

Nim's `move` really moves: the sequence is taken out of `source`, which is
left zeroed. Python's has nothing to move to — `target = source` binds a
second name to the same object, and the first still sees all four samples.

Neither number is wrong, because the question is not defined. That is the
rule: **after `move(x)`, `x` is not a value you may read.** The language
cannot stop you, the two backends will each answer something, and the
answers differ.

### Reading a dropped value

```python
own c: Buf_T = Buf_T(data=[1, 2, 3])
drop(c)
print "after drop: " + str(c.data'Length)      # do not do this
```

(That one is not in `EXAMPLES/`: a program that raises on one backend and
prints a number on the other is not something to ship. Both transcripts
below were measured from it.)

```
Nim:    after drop: 0
Python: UnboundLocalError: cannot access local variable 'c'
        where it is not associated with a value
```

Here Python is the one that behaves well: `del c` removes the binding, so the
next read is an error with a line number. Nim's `=wasMoved` leaves a zeroed
value that reads as an empty buffer, silently, and a zero that means
"destroyed" is indistinguishable from a zero that means zero.

### Reading a moved-from or dropped reference

Do the same two things to a `@virtual` value and Nim stops being silently
wrong — it crashes:

```python
@virtual
class Box:
    var value: int = 0

own source: Box = Box()
source.value = 42
own target: Box = move(source)
print f"moved-from reports {source.value}"
```

```
Nim:    SIGSEGV: Illegal storage access. (Attempt to read from nil?)
Python: moved-from reports 42
```

`move` on a reference sets the old name to `nil` rather than zeroing a
buffer in place, so reading a field through it dereferences a null
pointer. `drop` on a `@virtual` value crashes the same way, for the same
reason. Python, meanwhile, is unaffected by which kind of value it is:
`move` is still a plain alias and `drop` is still `del`, so a moved-from
reference reads back its old contents and a dropped one raises
`NameError` — exactly as a record would.

So the risk is asymmetric in a way the record case is not: on a value
type, a stale read is a wrong number on one backend and a correct one on
the other; on a `@virtual` value, it is a wrong number on Python and a
crash on Nim. `with own` closes this the same way it closes the record
case — the name does not exist after the block, on either backend, so
there is nothing left to dereference — and that is worth remembering
precisely because bare `own` + `move`/`drop` is the one place in this
chapter where the failure mode is not "wrong" but "down".

This threefold asymmetry is the argument of the next section.

## 13.5 What to use, and when

The five forms below all assume the decision in §13.2 has already been
made the ordinary way: the value is exclusively owned, a `record` or a
plain `class`, and what is left to decide is how cheaply it can be lent,
moved, or released. If what you actually need is for two names — or a
name and a collection — to see the same mutations, that is not one of
these five; it is `@virtual`, decided before any of them apply.

In the order you should reach for them:

**`lent` on any parameter a function only reads.** The cheapest of the five —
it costs one word, it is always true or always false, and a reader can check
it against the body in a second. Use it on the big ones: a table, a graph, a
board, a frame of samples. `EXAMPLES/td_learning/qlearning.ady` does exactly
this, on the Q-table that every step reads and no step owns:

```python
def choose_action(qtable: lent QTable_T, state: Coord_T, epsilon: Prob_T) -> Action_T:
```

**`own` on a declaration when a reader might wonder who frees it.** On a
local `int` it is noise. On the buffer that three functions are handed a
reference to, it is the answer to the question a reader is about to ask.

**`with own` whenever the lifetime really is a scope.** This is the one to
prefer over `drop`, and the reason is in the previous section: on Nim, using
the name after the block is a *compile error*, because the name does not
exist out there —

```
Error: undeclared identifier: 'scratch'
```

— while using a name after `drop(name)` compiles fine and reads as zero. A
speculative copy inside a search, a scratch buffer per iteration, a frame
that must not outlive the loop: put them in `with own` and the mistake
becomes impossible to write rather than merely unwise.

**`own` on a parameter when the callee really consumes the value.** A builder
that takes a buffer and returns a wrapper around it; a queue's `push`. It is
a promise to the caller that the copy will not happen, and a promise from the
caller that they are done with it.

**`move` last, and only where the source is about to go out of scope
anyway.** It is the one form whose misuse is silent and backend-dependent —
and, on a `@virtual` value, not silent at all (§13.4). If what you want is
"the value now lives over there", and the old name dies two lines later,
`move` says so and saves the copy. If the old name lives on, you do not
want `move`; you want to be sharing, which is a `@virtual class` (§13.2),
where an ordinary assignment already does it.

And the case for not writing any of them: **a value whose lifetime is
obvious does not need an annotation.** A local that lives for six lines and
dies at the end of the function is handled correctly by both backends with
nothing written down. Ownership vocabulary is for the values where a reader
would otherwise have to work it out — the big ones, the shared ones, the ones
that escape.

## 13.6 What this is not

No borrow checker. Nothing verifies that a `lent` parameter is not stored,
that a moved-from value is not read, or that two names do not both think they
own one value. The annotations are checked for *syntax* and then mostly
erased; the guarantees are Nim's ARC rules, and ARC trusts you.

No shared ownership among value types. A `record` or a plain `class` has
exactly one owner, matching Nim's ARC, and there is no `Rc`/`Arc`/
`shared_ptr` escape hatch for one. That is not a gap — needing several
owners is not a defect in the value, it is a sign the value should have
been a reference, which is what `@virtual` is for (§13.2): a Nim `ref
object`, reference-counted, and on Python the ordinary reference semantics
every object already has.

No custom destructors from Adascript. `=destroy` can be written in Nim and
reached through `nimraw:`, but there is no Adascript spelling for "run this
when the value dies".

Cycles need ORC. ARC alone leaks a cycle; Nim's ORC collects them, and that
is a compiler flag rather than something this vocabulary expresses.

And on Python, all of it is advisory. `drop` is a `del`, `with own` is a
`try`/`finally`, and everything else is erased. A program that depends on a
destructor running at a particular moment is a program that behaves
differently on the two backends — which brings this chapter back to the
previous one's contract: the source is one program, and the parts of it that
are about *when memory is released* are the parts where you have to know
which backend you are compiling for.

## 13.7 Reference

| Form | Means | Nim | Python | Misuse |
|---|---|---|---|---|
| `own x: T = e` | this name owns the value | `var x: T = e` | `x: T = e` | none; it is documentation |
| `param: lent T` | borrowed, read-only | `param: T` | `param: T` | storing it — unchecked |
| `param: own T` | consumed by the callee | `param: sink T` | `param: T` | reading the caller's name after the call |
| `move(x)` | transfer to a new owner | `move(x)` | alias | reading `x` — **differs per backend** |
| `drop(x)` | destroy now | `=destroy` + `=wasMoved` | `del x` | reading `x` — **differs per backend** |
| `with own x = e:` | lifetime is the block | `block:` | `try`/`finally` | reading `x` after — compile error on Nim |
| `@virtual class` | every name shares one value | `ref object` | reference (the default) | `move`/`drop` then reading it — **crashes on Nim** |

Rules of thumb, in one line each:

- Decide sharing first: `@virtual` if several names must see the same
  mutations, nothing if each should have its own copy.
- `lent` on every big read-only parameter.
- `with own` in preference to `drop` — doubly so on a `@virtual` value,
  where the bare form does not just disagree across backends, it crashes.
- `move` only when the source is dying anyway.
- Nothing at all when the lifetime is obvious.
- Never read a name after `move`, `drop`, or handing it to an `own` parameter.

---

*Next: [Chapter 14 — Programming in the Large: Modules, Projects, and Builds](14-programming-in-the-large.md)*
