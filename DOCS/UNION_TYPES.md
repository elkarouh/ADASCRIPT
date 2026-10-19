# Union types: one type per case

This tutorial compares three ways to model data whose shape depends on
which case it is in: a variant record, a class hierarchy, and a union of
records. The example is the drag in `TO_NIM/STDLIB/svg_drag.ady`.

## The problem

A mouse drag has three moments: nothing is held, a shape is held, and the
drag has ended. A held shape has a node, a place where the mouse went down,
and a centre. Nothing is held has none of those.

## Variant record

The first version used one record with a discriminant:

<!-- illustrative: the variant record svg_drag.ady used before its states became a union; kept to compare -->
```python
type Phase_T is enum IDLE, PRESSED, DRAGGING, DROPPED

type Grip_T (phase: Phase_T) is record:
    case phase is
        when PRESSED | DRAGGING:
            node:   Element_T
            down:   Screen_T
            centre: Spot_T
            now:    Spot_T
        when others:
            pass
```

Every value has the same type, and the phase is a field. Reading `grip.node`
is valid only in some phases, and the compiler cannot check that. The check
is a runtime error, and the `case grip.phase:` sits in every listener.

## Class hierarchy

Object-oriented code would say `Grip` is a base class with subclasses:

<!-- illustrative: a Python-style class sketch for comparison, not Adascript -->
```python
class Grip:
    pass

class Held(Grip):
    node: Element_T
    down: Screen_T
    centre: Spot_T
    now: Spot_T

class Idle(Grip):
    pass
```

This reads well for one level of subclass. Two costs show up quickly. A
listener that takes a `Grip` has to test with `isinstance` or override a
method, and both spread the logic across classes. And with each new state,
the question "which states have a node?" is answered by reading several
classes instead of one line.

Inheritance is worth its cost when several subclasses share real behaviour
and the depth stays small. For the states of one value, the shared part is
usually a few fields, which a union expresses without a base class.

## Union of records

Each state is a record, and the value is a union of them:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
type Idle_T is record: pass
type Held_T is record:
    node:   Element_T
    down:   Screen_T
    centre: Spot_T
    now:    Spot_T
    moved:  bool
type Ended_T is record: pass

type Grip_T is Idle_T | Held_T | Ended_T

var grip: Grip_T = Idle_T()
```

A state is named like a function, `Held_T(node=..., ...)`. A test names the
state, `if grip is Held_T:`, and inside that branch `grip.node` is valid. The
compiler checks each field access against the state the test proved.

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
def on_move(e: Event):
    if grip is Held_T:
        let dx: Pixel_T = at.x - grip.down.x
        let dy: Pixel_T = at.y - grip.down.y
        return if not grip.moved and abs(dx) < MOVED and abs(dy) < MOVED
        let now: Spot_T = setup.hooks.moved_cb(grip.node, grip.centre, wanted)
        grip = Held_T(node=grip.node, down=grip.down, centre=grip.centre, now=now, moved=true)
```

The flag `moved` replaces a second state. It is set once, when the mouse
passes the threshold, so the check on the return can see it. Writing the
drag as two states, one for "pressed" and one for "dragging", would have
repeated the whole body in two branches.

## Why this is more intuitive

- **One type per case.** `Held_T` has a node. `Idle_T` has nothing. The type
  says which fields exist, so no field is read by mistake.
- **Names are values.** `Idle_T()` builds a grip in that state. No separate
  phase enum to keep in step with the record.
- **Tests and reads sit together.** `if grip is Held_T:` shows what is valid
  inside the branch, instead of a discriminant checked by hand.
- **Flat.** There is no base class to find and no override to chase. Each
  state is one short record, and the union lists the states in one line.

## Caveats

- A union with an assignment inside its own test needs care. Under
  `if grip is Held_T:`, the transpiler renders `grip = ...` as a field write
  unless the assignment target is the whole name. The fix that was made in
  `hek_nim_stmt.py` (`_whole_target`) handles this.
- Two states that share most fields still repeat those fields. A shared
  record can hold them, with a flag for the difference, as `Held_T` does.
- A union's members are not related by inheritance. A function that works on
  any state takes the union, and a function for one state takes that record.

## Summary

Use a variant record when one shape has a few optional parts. Use a class
hierarchy when several types share real behaviour and the depth is small.
Use a union of records when each state carries its own data and the code
asks which state it is in. For the drag, that is one line per state and one
`if` per listener.
