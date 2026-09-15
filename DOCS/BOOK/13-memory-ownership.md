# Chapter 13 — Memory Ownership

Every value has to live somewhere, and something has to decide when it stops
living there. Python decides with a garbage collector: you never say, and the
runtime works it out, eventually. Nim's ARC decides at compile time: the
value is freed when its owner's scope ends, with no collector and no pause.

Adascript compiles to both, so it cannot pick one. What it offers instead is
a small vocabulary — `own`, `lent`, `move`, `drop`, `with own` — for writing
down what you already know about a value's lifetime. On Nim that writing-down
guides ARC. On Python it is mostly stripped, because the GC does not need it.

This chapter is about when each one is worth writing, and about the two
places where the backends stop agreeing, which are the two you have to know.

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

## 13.2 A tour

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

## 13.3 The two places the backends disagree

Everything above prints the same on both backends. These two do not, and
both involve reading a value that you have already given away.

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

This asymmetry is the argument of the next section.

## 13.4 What to use, and when

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
anyway.** It is the one form whose misuse is silent and backend-dependent. If
what you want is "the value now lives over there", and the old name dies two
lines later, `move` says so and saves the copy. If the old name lives on,
you do not want `move`; you want to be sharing, which for a `class` (a Nim
`ref object`) is what an ordinary assignment already does.

And the case for not writing any of them: **a value whose lifetime is
obvious does not need an annotation.** A local that lives for six lines and
dies at the end of the function is handled correctly by both backends with
nothing written down. Ownership vocabulary is for the values where a reader
would otherwise have to work it out — the big ones, the shared ones, the ones
that escape.

## 13.5 What this is not

No borrow checker. Nothing verifies that a `lent` parameter is not stored,
that a moved-from value is not read, or that two names do not both think they
own one value. The annotations are checked for *syntax* and then mostly
erased; the guarantees are Nim's ARC rules, and ARC trusts you.

No shared ownership. There is no `Rc`/`Arc`/`shared_ptr` equivalent. When
several owners are genuinely needed, use a `class` — on Nim that is a `ref
object`, which is reference-counted, and reference semantics are what you
wanted. Records are value types and get copied.

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

## 13.6 Reference

| Form | Means | Nim | Python | Misuse |
|---|---|---|---|---|
| `own x: T = e` | this name owns the value | `var x: T = e` | `x: T = e` | none; it is documentation |
| `param: lent T` | borrowed, read-only | `param: T` | `param: T` | storing it — unchecked |
| `param: own T` | consumed by the callee | `param: sink T` | `param: T` | reading the caller's name after the call |
| `move(x)` | transfer to a new owner | `move(x)` | alias | reading `x` — **differs per backend** |
| `drop(x)` | destroy now | `=destroy` + `=wasMoved` | `del x` | reading `x` — **differs per backend** |
| `with own x = e:` | lifetime is the block | `block:` | `try`/`finally` | reading `x` after — compile error on Nim |

Rules of thumb, in one line each:

- `lent` on every big read-only parameter.
- `with own` in preference to `drop`.
- `move` only when the source is dying anyway.
- Nothing at all when the lifetime is obvious.
- Never read a name after `move`, `drop`, or handing it to an `own` parameter.

---

*Next: [Chapter 14 — Programming in the Large: Modules, Projects, and Builds](14-programming-in-the-large.md)*
