# Adascript for JavaScript Programmers

JavaScript got the browser right: a page is a tree of elements, events come
to you, and you change what the user sees by changing the tree. It is a fine
language to write a small page in. It gets harder as the page grows, for the
same few reasons every time.

A value can be `undefined` or `null` and nothing in the code says which may
arrive. A `let` can be reassigned three functions away. An object is a bag of
properties, so a typo in a property name is found at runtime, when a user
clicks the button. A state that is "one of four things" is a string, or a
set of booleans that can disagree with each other. And the function that
handles a click is wired to the page by a string nobody checks.

Adascript is for the same kind of page, written so that the compiler checks
those things. It compiles to JavaScript (`ady2nim js`), to native code, and to
Python, from one source. This document is for someone who knows JavaScript
well and wants to know what changes when they write the page in Adascript.

Every Adascript example quoted here is a real file in the repository, and
`make test` checks that the quotes still match. The browser examples come
from `BROWSER_EXAMPLES/DIJKSTRA_HTMX` and `TO_NIM/STDLIB/svg_drag.ady`; the model
examples come from `BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady`. JavaScript
blocks in this document are comparisons, not Adascript, and are not checked.

---

## 1. The problem

Take the smallest useful thing a page does: a click on a node asks a function
for the node's name, or for nothing, and does something with it.

```javascript
function nameOf(node) {
  const name = node.getAttribute("data-name");   // string or null
  return name ? name.toUpperCase() : undefined;  // undefined, not "", when absent
}

const picked = nameOf(document.querySelector("g.node"));
if (picked !== undefined) {
  console.log(picked.length);
}
```

Three things here are invisible to a reader. `getAttribute` may return
`null`, which the function does not say. The function may return `undefined`,
which the caller must remember to test. And `picked.length` is only safe
because of the test above it, which nothing enforces. Each is a bug waiting
for the day the test is forgotten.

Adascript puts the answer in the signature, and makes the compiler read it.

---

## 2. Declarations: `let`, `var`, `const`

JavaScript has `var`, `let` and `const`, and they differ in scope and
hoisting. Adascript has three keywords that differ in one thing only: whether
the name may be assigned again.

| JavaScript | Adascript | Meaning |
|---|---|---|
| `let x = 1` (never reassigned) | `let x: int = 1` | a name bound once; reassigning it is a compile error |
| `let x = 1` (reassigned later) | `var x: int = 1` | a name that may be assigned again |
| `const X = 4.0` | `const X: float = 4.0` | a constant |

The examples annotate every declaration with its type, after a colon, as in
`let nodes: []Node_T = ...`. Lists are written `[]T`, and `[]` is the empty
list.

The compile error for reassigning a `let` is the first thing a JavaScript
programmer meets, and it is the point: most of the `let`s in a JavaScript
file are never reassigned, and the ones that are should say so. Here is the
rule the examples follow. Use `let` by default, `var` when the value changes,
and a module-level `var` only for state that really lives across events.

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady -->
```python
def names(self) -> []str:
    var names: []str = []
    for n in self.nodes:
        names.append(n.name)
    return names
```

`names` is a `var` because it grows; `n` is bound by the `for`, and the loop
itself does not reassign it.

---

## 3. No `undefined`, no `null`: optional types

JavaScript has two absent values, and both are everywhere. Adascript has one,
`None`, and a type that says where it may appear: `?T` is "a `T`, or
`None`".

```javascript
// JavaScript: any of these may be undefined or null, and the code cannot tell which
function clickedName(e) { return e.target.dataset.name; }
```

In Adascript, a function that may find nothing says so:

<!-- from: TO_NIM/STDLIB/browser.ady -->
```python
def find(within: Element_T, css: str) -> ?Element_T:
```

That is the browser module's own `find`, in `TO_NIM/STDLIB/browser.ady`.
The caller then has to deal with `None` before it uses the value. The usual
way is an early return, and the compiler follows it:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
let node: ?Element_T = on(click_of(e), setup.shapes)
return if node is None
```

After the `return`, `node` is an `Element_T`, not a `?Element_T`, and the rest
of the function uses it as one. This is what `svg_drag.ady` does in its
`on_down` listener, before it reads the node's position. The narrowing is done
by the compiler from the `if`; you do not write a cast.

For a default, `or` supplies a value when the left side is `None`. A probe
run for this document shows `name or "anon"` giving `anon` when `name` is
`None`. Where JavaScript writes `x ?? "anon"`, Adascript writes `x or "anon"`.

Note what Adascript does not have: no `undefined` to compare against, no
`!= null` to remember, and no optional chaining to forget. A value that may be
absent has a type that says so, and a value that is not optional cannot be
`None`.

---

## 4. Records instead of objects

A JavaScript object is a bag of properties. Adascript's closest thing is a
record, which is declared with its fields and their types:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady -->
```python
type Node_T is record:
    name: str
```

A node has a name and nothing else. Where it is drawn is decided by the GUI,
not the model, so the model stays the same whatever the layout does.

A record is built by calling its type with the fields in order, or by name:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady -->
```python
self.edges.append(Edge_T(a, b, cost))
```

Fields are read with a dot, as in JavaScript. A record with one fixed set of
fields is a plain record. For a value whose fields depend on which state it
is in, Adascript has a union of records, one per state (§6).

Callbacks are typed the same way. The browser's drag module declares what
each callback takes and returns, then bundles them into a record. A caller
passes the record in the way it would pass an options object:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
type Hooks_T is record:
    moved_cb:   Moved_CB_T
    dropped_cb: Dropped_CB_T
    clicked_cb: Clicked_CB_T
```

---

## 5. Enums instead of strings

A JavaScript program that tracks "which kind of thing this is" stores a
string, `"idle"`, `"pressed"`, and compares strings in several places. A
typo in one comparison is silent. In Adascript the names are an enum:

<!-- from: EXAMPLES/PHONECODE/phonecode.ady -->
```python
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

A name is one the compiler knows, so a misspelt one is an error, not a silent
mismatch the way a string is. Where each state needs different data, the
states are types instead of names (§6).

---

## 6. Unions: data that depends on the state

Suppose the mouse is held down on a node only between the press and the
release. Before the press there is no node, and after the release there is
none either. JavaScript holds this with a nullable variable, and the code
checks it in every function. Adascript states the rule once, in the types:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
type Idle_T is record: pass
type Held_T is record:
    node:   Element_T
    down:   Screen_T
    centre: Spot_T
    now:    Spot_T
    moved:  bool
type Grip_T is Idle_T | Held_T | Ended_T
```

Each state is a record of its own, and `Grip_T` is a union of them. A
`Held_T` has a `node`, and an `Idle_T` has no fields at all. The field is
read only where an `is` test has narrowed the value to a state that has it, so
reading `grip.node` where the grip might be idle is not allowed.

A value is made by naming its state like a function. Bare `Idle_T` is the
type, and `Idle_T()` is a grip in that state:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
var grip: Grip_T = Idle_T()
```

The module-level `var grip` is the one drag there is. Its state is tested by
the listeners with `is`, and each listener changes it by assigning a new value:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
grip = Held_T(node=node, down=screen_of(m), centre=centre, now=centre, moved=false)
```

The assignment replaces the whole value at once, so the state and its fields
are always set together, even when it is made inside the `if` that tested
`grip`.

## 7. Functions, and what they return

A JavaScript function returns whatever it likes. An Adascript function states
its return type, and a function that returns nothing is written without one:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
def shift(node: Element_T, centre: Spot_T, now: Spot_T):
    node.set_attr("transform", f"translate({now.x - centre.x:.1f},{now.y - centre.y:.1f})")
```

Strings are `"..."`, and an `f"..."` is a template literal with the same
idea: `{expr}` in braces, with an optional format after a colon, as in `:.1f`
for one decimal place.

A function that can fail for a reason the caller should read returns the
reason as a value of its own type, `T | !F`: "a `T`, or a failure `F`" that
the caller must look at, as it must look at an optional. The model does this
for every change it accepts. `None` means it was done; a `Refusal_T` says why
it was not:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady -->
```python
def add_node(self, name: str) -> None | !Refusal_T:
    if len(name) == 0 or len(name) > 8:
        return Refusal_T(message="A name is 1 to 8 letters or digits.")
```

The caller asks which it got with `is`, and the tests in `test_dijkstra.ady`
do the same:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/tests/test_dijkstra.ady -->
```python
assert net.add_node("G") is None
assert net.add_node("G") is Refusal_T
```

A failure that is dropped without a look is refused at compile time. The
type is in `DOCS/BOOK/10-optionals.md`, §10.12. The page shows the
refusal's `message` to the user.

---

## 8. The page: finding elements and reacting to clicks

In JavaScript the page is reached through `document`, and everything is a
string. `document.querySelector` returns `null` when nothing matches, and
`setAttribute` takes the name as a string. Adascript's browser module
(`TO_NIM/STDLIB/browser.ady`) keeps the same idea and types each step.

```javascript
// JavaScript: null if nothing matches; the name is a string nobody checks
const shape = document.querySelector("g.node");
shape.setAttribute("transform", "translate(10,10)");
```

In Adascript, the page is `page`, `page.element` finds an element that must be
there, and `set_attr` sets an attribute. The drag module finds its drawing
like this:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
def svg_box() -> BoundingRect:
    page.element(setup.svg).getBoundingClientRect()
```

Where a match may be missing, `find` returns a `?Element_T`, and you narrow it
as in §3.

A function whose first parameter is an element can be called as a method on
it, as `node.set_attr(...)` and `node.number(name)` above show. You do not
need to write `set_attr(node, ...)`.

Clicks come with a `Click_T`, a record that says whether the shift key was
down, what was clicked, and the raw event. The listener is a function with a
typed parameter, and the `on` call finds the shape a click landed on:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
def on_click(e: Event):
    if grip is Ended_T:
        grip = Idle_T()
        e.stopPropagation()
        return
    setup.hooks.clicked_cb(click_of(e))
```

The rule, that a click after a drag is swallowed before htmx sees it, is
written out in the function itself, next to the state it depends on.

---

## 9. Distinct types for units

JavaScript numbers are all one type. A pixel and a unit of a drawing are both
numbers, and nothing stops a pixel being added to a unit. Adascript makes them
two types. The drawing's is in `drawing.ady`, which the server can import too:

<!-- from: TO_NIM/STDLIB/drawing.ady -->
```python
type Unit_in_pixel_T is distinct float
```

and the mouse's is in `svg_drag.ady`, with the scale between them:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
type Pixel_T is distinct float
type Scale_T is Unit_in_pixel_T / Pixel_T
```

The module's own comment says that adding a pixel to a drawing unit does not
compile. The only way across is a `Scale_T`, which says how many units a pixel
is, and `spot_at` in `svg_drag.ady` uses it to turn a mouse position into a
position in the drawing.

A literal converts directly to a distinct type, so you write `4.0` where a
`Pixel_T` is wanted, and no cast is needed:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
const MOVED: Pixel_T = 4.0
```

---

## 10. Modules and imports

A JavaScript module imports named things from a path. Adascript does the same,
and the browser module is an ordinary import:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
from browser import Element_T, page, set_attr, number, Click_T, click_of, on
```

The model is kept apart from the page. `dijkstra_model.ady` does no file I/O
and no HTML, and `BROWSER_EXAMPLES/DIJKSTRA_HTMX/tests/test_dijkstra.ady` runs it with
`ady2nim c -r`, with no server and no browser.

---

## 11. Where the differences show up

| In JavaScript | In Adascript |
|---|---|
| `undefined`, `null` | `None`, and a type `?T` that says where it can be |
| `x ?? d`, `x \|\| d` | `x or d` |
| `if (x !== null)` | `if x is not None:` |
| `===`, `==` | `==`; there is one equality, and it compares values |
| `let x` reassigned later | `var x` |
| `const` | `const`, with a type, fixed at compile time |
| `{ a: 1 }` object | a `type ... is record:` with named fields |
| `"idle"` strings | `enum` members, checked by the compiler |
| `switch` with `break` | `case` with `when`; no fall-through |
| `` `x ${y}` `` | `f"x {y}"` |
| `;` at the end of a line | nothing: indentation makes the block |
| `document.querySelector` | `page.find`, or `page.element` when it must be there |
| `el.setAttribute(n, v)` | `el.set_attr(n, v)` |

---

## 12. Where to go next

- `DOCS/ADASCRIPT_FOR_AWK.md` and `DOCS/ADASCRIPT_FOR_SHELL.md` are the same
  kind of introduction, for readers who come from other languages.
- `DOCS/BOOK/` covers each part of the language in a chapter: types in 02,
  enums in 03, records and variants in 04, optionals in 10, and the
  two backends in 12.
- `BROWSER_EXAMPLES/DIJKSTRA_HTMX/` is the whole thing in one small program: a model,
  a server that draws the page with htmx, and a browser script that handles
  the clicks and drags.
- `TO_NIM/STDLIB/svg_drag.ady` is the drag module in full, with its own
  docstring explaining the three callbacks.
