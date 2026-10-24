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

Sections 2 to 10 go through the language a piece at a time; §11 is a tutorial that builds a
small page with it, step by step, from an empty directory to a shopping list kept in the
browser.

Every Adascript example quoted here is a real file in the repository, and
`make test` checks that the quotes still match. The browser examples come
from `BROWSER_EXAMPLES/DIJKSTRA_HTMX`, `BROWSER_EXAMPLES/SHOPPING_LIST` and `TO_NIM/STDLIB/svg_drag.ady`; the model
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
def text(self) -> str:
    var lines: []str = []
    for n in self.nodes:
        lines.append(f"node {n.name}")
    for e in self.edges:
        lines.append(f"edge {e.a} {e.b} {e.cost}")
    for n in self.nodes:
        if n.name in self.places:
            let p: Spot_T = self.places[n.name]
            lines.append(f"at {n.name} {p.x:.0f} {p.y:.0f}")
    return "\n".join(lines) + "\n"
```

`lines` is a `var` because it grows; `p` is a `let` because it is never
reassigned; `n` and `e` are bound by the `for`, and the loop itself does not
reassign them.

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
type Refusal_T is record:
    message: str
```

A refusal is the message the page shows the reader and nothing else: a value,
compared by its fields, with no methods.

A record is built by calling its type with the fields in order, or by name:

<!-- from: BROWSER_EXAMPLES/DIJKSTRA_HTMX/backend/dijkstra_model.ady -->
```python
return Refusal_T(message=f"There is a node {name} already.")
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
type Drawing_Pixel_T is distinct float
```

and the mouse's is in `svg_drag.ady`, with the scale between them:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
type Physical_Pixel_T is distinct float
type Scale_T is Drawing_Pixel_T / Physical_Pixel_T
```

The module's own comment says that adding a pixel to a drawing unit does not
compile. The only way across is a `Scale_T`, which says how many units a pixel
is, and `spot_at` in `svg_drag.ady` uses it to turn a mouse position into a
position in the drawing.

A literal converts directly to a distinct type, so you write `4.0` where a
`Physical_Pixel_T` is wanted, and no cast is needed:

<!-- from: TO_NIM/STDLIB/svg_drag.ady -->
```python
const MOVED: Physical_Pixel_T = 4.0
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

## 11. A tutorial: a shopping list, step by step

The sections above take the language a piece at a time. This one builds a whole page with it,
in the order a JavaScript programmer would: a page, a script, the data, the drawing, the events,
and keeping the data between visits. The page is a shopping list: type what to buy, click an
item once it is in the basket, and × takes it off the list. It runs in the browser alone, opened
as a file, with no server.

Every file is in `BROWSER_EXAMPLES/SHOPPING_LIST`, and `make test` builds and checks it.

### Step 1: a page and a script

The page is as small as a page can be. It has a place for the script to draw in, and it loads
the script:

```html
<!doctype html>
<!-- The shopping list: shopping_page.js draws it here. Build it with `make`, then open this file. -->
<meta charset="utf-8">
<title>Shopping list</title>
<div id="app"></div>
<script src="shopping_page.js"></script>
```

`shopping_page.js` is not written by hand. It is what `ady2nim js` makes of
`shopping_page.ady`, the way a bundler makes one file of a JavaScript project:

```bash
cd BROWSER_EXAMPLES/SHOPPING_LIST
ady2nim js shopping_page.ady      # writes shopping_page.js; `make` does the same
```

Open `index.html` in the browser, and the page is there. There is no dev server and no build
configuration: one command makes one file.

### Step 2: the data, first, and with no page in it

A JavaScript page tends to keep its data in the page: an array of objects next to the code that
draws it, and sometimes in the elements themselves. In Adascript the data is a module of its
own, `shopping_model.ady`, which knows nothing of elements or events. An item is a record, with
its fields and their types (§4):

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_model.ady -->
```python
type Item_T is record:
    name:   str
    bought: bool
```

The list is a class: its items, and what can be done to them. Adding is the one change that can
be refused, so it says so in its return type (§7). `None` means the item is on the list; a
`Refusal_T` says why it is not:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_model.ady -->
```python
class Shopping_List:
    var items: []Item_T = []

    # NAME on the list, to buy; refused when it is empty or on the list already.
    def want(self, name: str) -> None | !Refusal_T:
        let wanted: str = name.strip()
        if wanted == "":
            return Refusal_T(message="Type what to buy first.")
        if self.has(wanted):
            return Refusal_T(message=f"{wanted} is on the list already.")
        self.items.append(Item_T(name=wanted, bought=False))
        return None
```

The rest is as short. `toggle` flips an item's `bought`, `remove` keeps every item but one, and
`left` counts what is still to buy:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_model.ady -->
```python
    def remove(self, name: str):
        self.items = [item for item in self.items if item.name != name]

    # How many are still to buy.
    def left(self) -> int:
        return len([item for item in self.items if not item.bought])
```

`text` writes the list as text, a line an item, and `load` reads it back; Step 7 keeps that text.

### Step 3: test the data without a browser

Because the model has no page in it, it also compiles to native code, and a test runs it there,
with no browser, no DOM and no test runner to install:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/tests/test_shopping.ady -->
```python
var basket: Shopping_List = Shopping_List()
assert basket.want("milk") is None
assert basket.want("bread") is None
assert basket.want("milk") is Refusal_T
assert basket.want("  ") is Refusal_T
assert basket.left() == 2
```

```bash
make test        # ady2nim c -r tests/test_shopping.ady
```

The same file the page runs is the file the test runs. Nothing is mocked.

### Step 4: draw an item

In JavaScript an item is drawn with a template literal put in `innerHTML`, which is quick to
write and has two traps: the markup is a string nobody checks, and a name the reader typed with
a `<` in it becomes markup. Adascript draws with an `html:` block, in which the tags are code:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_view.ady -->
```python
    def to_html(self, item: Item_T) -> Html:
        let css: str = ("item bought" if item.bought else "item")
        html:
            li class=css data_name=item.name:
                span class="name": item.name
                button type="button" class="remove" data_name=item.name: "×"
```

Indentation nests the elements; `class=css` is the value of `css`, and `class="name"` the
text; `data_name` is written `data-name` in the page. The text is escaped on the way, so a
reader who types `<b>tea</b>` gets an item called `<b>tea</b>`, not bold tea.

The method belongs to a view class, `Item_View`, and the class holds the item's look as well, in
a `style` block. Where JavaScript keeps the CSS in another file, here the rules sit with the
markup they style:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_view.ady -->
```python
class Item_View:
    style "li.item":
        &:                      cursor="pointer" padding="0.4em 0" border_bottom=f"1px solid {LINE}" display="flex" justify_content="space-between"
        &.bought span.name:     color=SOFT text_decoration="line-through"
        button.remove:          border="none" background="none" color=RED cursor="pointer" font_size="1.1em"
```

Each rule is under the element the class draws, `li.item`: `&` is the item itself, and
`button.remove` a button in it. A property is CSS's name with `_` for `-`, and a misspelt one
does not compile. `LINE`, `SOFT` and `RED` are the page's colours, named once at the top of the
file, which CSS variables would do in JavaScript.

### Step 5: draw the page

The list and the page are views too. `List_View` draws the count and every item, asking its
`Item_View` for each one:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_view.ady -->
```python
    def to_html(self, basket: Shopping_List) -> Html:
        html:
            div id="list":
                p class="left": f"{basket.left()} to buy"
                ul:
                    for item in basket.items:
                        + self.items.to_html(item)
```

A `for` in an `html:` block is a loop over elements, where JavaScript would `map` and `join`.
A `+` puts in what another view drew. `Page_View` draws the rest: a box to type in, its button,
a paragraph for what was refused, and the list. Its rules are for the page as a whole, so its
block has no scope, and each selector is written whole:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_view.ady -->
```python
    style "":
        body:                   font_family="system-ui, sans-serif" color=INK max_width="30em" margin="2em auto" padding="0 1em"
        input, button:          font="inherit"
        p#problem:              color=RED min_height="1.2em" margin="0.3em 0"
```

The page puts every view's rules in its own `<style>`, once: `self.style.css() +
self.shown.css()`.

### Step 6: listen to the reader

Now the script, `shopping_page.ady`. A JavaScript programmer would add one listener to the
document and look at what was clicked, rather than a listener on every item, which is lost each
time the list is drawn again. The script does the same, in the words of the stdlib's `browser`
module (§8):

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_page.ady -->
```python
def clicked(e: Event_T):
    let c: Click_T = click_of(e)
    if c.on("#add") is not None:
        add_typed()
        return
    let remove: ?Element_T = c.on("button.remove")
    if remove is not None:
        basket.remove(remove.data("name"))
        changed()
        return
    let item: ?Element_T = c.on("li.item")
    if item is not None:
        basket.toggle(item.data("name"))
        changed()
```

`c.on("li.item")` is the item the click was on or inside, JavaScript's
`e.target.closest("li.item")`, and its type, `?Element_T`, says it may be `None`: the compiler
does not let `item.data(...)` through until the `if` has ruled that out (§3). `data("name")` reads
what `Item_View` wrote in `data_name`. The script never reads the list back out of the page: the
page shows the model, and a click changes the model.

The script starts by drawing the page and naming its listeners:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_page.ady -->
```python
page.element("#app").set_html(page_view.text(basket))
listen("click", clicked)
listen("keydown", pressed)
```

### Step 7: a change, or why not

Adding is where the refusal of Step 2 arrives. The script cannot drop it: a result of type
`None | !Refusal_T` that nobody looks at does not compile, so the "forgot to handle the error"
bug of a JavaScript page cannot be written:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_page.ady -->
```python
def add_typed():
    let done: None | !Refusal_T = basket.want(page.field("name"))
    if done is Refusal_T:
        say(done.message)
        return
    page.fill("name", "")
    changed()
```

`page.field("name")` is the value of the input named `name`, and `page.fill` sets it. `say`
puts the message under the box with `set_text`, not `set_html`: the message has the reader's
words in it, and text is never read as markup.

### Step 8: keep the list

A reload should not lose the list. JavaScript would reach for `localStorage`. Adascript's
`Store` is a set of texts under names, and under `ady2nim js` it keeps them in the browser's
storage; natively, the same code keeps them as files. After every change the script writes the
list's text:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_page.ady -->
```python
def changed():
    say("")
    if not kept.write("list.txt", basket.text()):
        say("The list could not be kept.")
    page.element("#list").set_html(page_view.shown.text(basket))
```

and reads it once, when the page opens. There may be nothing kept yet, which is why `read`
answers `?str`, and the `if` is not optional:

<!-- from: BROWSER_EXAMPLES/SHOPPING_LIST/shopping_page.ady -->
```python
let before: ?str = kept.read("list.txt")
if before is not None:
    basket.load(before)
```

### Step 9: run it, and change it

```bash
make open        # build shopping_page.js, and open index.html
```

Add milk twice to see the refusal, click it to strike it out, reload to see it kept. Then try
a change in each layer, and watch the others stay as they were:

1. **The data.** Give `Item_T` a `count: int`, so that wanting milk again counts two in place
   of refusing it. Change `want`, `text` and `load`, and the test first.
2. **The drawing.** Show the count in `Item_View.to_html`, after the name.
3. **The look.** Make a bought item green with a rule in `Item_View`'s style block.
4. **The events.** A double click on an item could ask for a new name: `listen("dblclick", ...)`
   and the browser module's `ask`.

---

## 12. Where the differences show up

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
| `el.textContent = t`, `el.innerHTML = h` | `el.set_text(t)`, `el.set_html(h)` |
| `` `<li>${name}</li>` `` | an `html:` block, its text escaped |
| a stylesheet beside the code | a `style` block in the view class |
| `localStorage` | a `Store` |

---

## 13. Where to go next

- `DOCS/ADASCRIPT_FOR_AWK.md` and `DOCS/ADASCRIPT_FOR_SHELL.md` are the same
  kind of introduction, for readers who come from other languages.
- `DOCS/BOOK/` covers each part of the language in a chapter: types in 02,
  enums in 03, records and variants in 04, optionals in 10, and the
  two backends in 12.
- `BROWSER_EXAMPLES/SHOPPING_LIST/` is §11's app, to change and run.
- `BROWSER_EXAMPLES/DIJKSTRA_HTMX/` is the whole thing in one small program: a model,
  a server that draws the page with htmx, and a browser script that handles
  the clicks and drags.
- `TO_NIM/STDLIB/svg_drag.ady` is the drag module in full, with its own
  docstring explaining the three callbacks.
