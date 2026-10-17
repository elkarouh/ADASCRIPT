# Tutorial: a web application in Adascript, from the model to the page

This example is the smallest complete web application in Adascript. You
can run it, change it, and read every line. This tutorial follows one
thing through it, a node, from the data that holds it, to the picture
on the page, to the click that changes it. It also explains why the page
is built with htmx and how the two fit together.

```
make app                  # builds the browser script and the server, opens the page
make test                 # the model and the page, tested without a server
```

## The whole picture

![A request, from a click to the new page](request_flow.svg)

The program is split by what each part knows:

| Layer | Files | Knows about |
|---|---|---|
| The model | `backend/dijkstra_model.ady` | the data and its rules; nothing else |
| The layout | `backend/dijkstra_layout.ady` | where each node is drawn when nobody has put it |
| The page | `backend/dijkstra_gui.ady` | how the data looks as HTML |
| The requests | `backend/dijkstra_events_gui.ady` | what each request does to the data |
| The server | `backend/server.ady` | HTTP, and nothing else |
| The browser | `frontend/dijkstra_js_events.ady` | the gestures that must follow the mouse |

Each layer only calls the one below it. The model never imports HTML,
and the server never looks inside a node. That is what makes each layer
testable on its own (see `tests/test_dijkstra.ady`).

---

## Step 1: define the objects in the model

The model says what a network is. It has three records: a node, an edge,
and the place where the reader has put a node on the drawing.

```adascript
# A node: its name.
type Node_T is record:
    name: str

# An edge: the two nodes it joins, both ways, and its cost.
type Edge_T is record:
    a:    str
    b:    str
    cost: int

# Where a node is drawn: its centre in the drawing.
type Place_T is record:
    x: float
    y: float
```

The network is a class. It holds the three lists and is changed only
through its methods:

```adascript
class Network:
    var nodes: []Node_T                 # in the order they were made
    var edges: []Edge_T                 # each edge once
    var places: {str}Place_T            # where the reader put a node, by name

    def __init__(self, nodes: []Node_T, edges: []Edge_T, places: {str}Place_T):
        self.nodes = nodes
        self.edges = edges
        self.places = places
```

![The model: three records, and the class that holds them](model_objects.svg)

### Methods refuse with a failure, or succeed

Every method that changes the network returns `None | !Refusal_T`. A
refusal is a `Refusal_T`, a record whose message the page shows in red.
Success is the normal end of the method. The caller narrows the result
with `is`, the same way `parse_int` results are read, so a refusal
cannot be ignored by accident. The rules live in the model, and the
page only decides how to show them.

```adascript
type Refusal_T is record:
    message: str

def add_node(self, name: str) -> None | !Refusal_T:
    if len(name) == 0 or len(name) > 8:
        return Refusal_T(message="A name is 1 to 8 letters or digits.")
    for c in name:
        if c not in LETTERS:
            return Refusal_T(message="A name is 1 to 8 letters or digits.")
    if name in self.names():
        return Refusal_T(message=f"There is a node {name} already.")
    self.nodes.append(Node_T(name))
```

### The model is kept in text

`text()` writes the network as one line per node, edge and place, and
`Network(text)` reads it back, through a second constructor. The server saves the file after every
change, and the page carries the same text, so the browser can rebuild
the same network.

```adascript
def text(self) -> str:
    var lines: []str = []
    for n in self.nodes:
        lines.append(f"node {n.name}")
    for e in self.edges:
        lines.append(f"edge {e.a} {e.b} {e.cost}")
    for n in self.nodes:
        if n.name in self.places:
            let p: Place_T = self.places[n.name]
            lines.append(f"at {n.name} {p.x:.0f} {p.y:.0f}")
    return "\n".join(lines) + "\n"
```

### Reading the text back: a second constructor, `case` on the first word

```adascript
for line in text.split("\n"):
    let w: []str = line.split()
    if len(w) == 0:
        continue
    case w[0]:
        when "node":
            if len(w) == 2:
                let added: str = net.add_node(w[1])
        when "edge":
            ...
```

A `case` on a string needs a `when others:` branch, so write one even
when the others do nothing. (The compiler says so if you forget.)

---

## Step 2: decide where each object is drawn

The model stores only the places the reader has chosen. Any node
without one is placed by the layout, which is a pure function of the
network, so the server and the browser agree on it without talking.

```adascript
# Where the node NAME of NET is drawn: where the reader put it, else where the layout puts it.
def place_of(net: Network, name: str) -> Place_T:
    if name in net.places:
        return net.places[name]
    for i in range(len(net.nodes)):
        if net.nodes[i].name == name:
            return new_spot(i, len(net.nodes))
    return Place_T(0.0, 0.0)
```

`new_spot` spreads the nodes evenly round an ellipse. The layout is
imported by both the server (`dijkstra_gui.ady`) and the browser
(`dijkstra_js_events.ady`), which is why it is kept in its own file, with
no HTML in it.

---

## Step 3: give the objects a picture

The page is written by functions that return `Html`. An `html:` block
writes markup as Adascript code, with indentation for nesting, and a
`+` to insert another piece:

```adascript
# A node: its circle and name, and a port (the dot on its right) from which a wire is drawn to another.
def to_html(n: Node_T, at: Place_T, role: str) -> Html:
    let cx: str = f"{at.x:.0f}"
    let cy: str = f"{at.y:.0f}"
    let ty: str = f"{at.y + 5.0:.0f}"
    let px: str = f"{at.x + 24.0:.0f}"
    let css: str = "node " + role
    html:
        g class=css data_name=n.name data_x=cx data_y=cy:
            circle cx=cx cy=cy r="24"
            stext class="name" x=cx y=ty: n.name
            circle class="port" cx=px cy=cy r="6"
```

Three things to note:

- **The object is an argument.** `to_html` takes a `Node_T` and the
  place it is drawn at. It knows nothing else about the network.
- **Attributes are names.** `class=css` puts the value of the variable
  `css`; `class="name"` puts the text. Attribute names with a dash are
  written with an underscore, `data_name` (see *Why htmx and how* below).
- **The picture of one object is one function.** The picture of the
  whole network is another, which calls these in turn:

```adascript
def to_html(net: Network, p: Params_T, way: []str) -> Html:
    let box: str = f"0 0 {WIDTH:.0f} {HEIGHT:.0f}"
    html:
        svg viewBox=box class="graph":
            for e in net.edges:
                + to_html(e, uses(way, e), place_of(net, e.a), place_of(net, e.b))
            for n in net.nodes:
                + to_html(n, place_of(net, n.name), ("start" if n.name == p.start else ("goal" if n.name == p.goal else ("way" if n.name in way else ""))))
            path id="wire" class="wire" visibility="hidden" d="M 0 0 L 0 0"
```

The edges are drawn first, so each node sits on top of the lines that
end at it.

### The page is parts, and each part is one function

![The page, part by part](page_parts.svg)

The whole page is `all_html`, which puts its parts in one `div`. The
hidden forms (`#state`, `#move`, `#gesture`) carry values that the
buttons send, so the requests carry the choice the reader has made.

### The look goes beside the code that uses it

The CSS of a node is defined next to `to_html` for the node, so one
place says both what a node is and how it looks:

```adascript
const NODE_STYLE: str = """
g.node { cursor: grab; }
g.node circle { fill: #fff; stroke: #7b8794; stroke-width: 2; }
g.node.start circle { fill: #e3f2e5; stroke: var(--start); stroke-width: 4; }
g.node.selected circle { stroke: var(--accent); stroke-width: 4; }
"""
```

`ALL_STYLE` joins the parts together for the page. A page-wide rule (the
body, the buttons) stays in `STYLE`.

---

## Step 4: handle the events

There are two kinds of event, and the example uses each for what it
does best.

**Most events go to the server.** A button says what to ask for, in its
attributes. The browser does nothing itself:

```adascript
button type="button" id="make_node" data_hx_post="/nodes" data_hx_include="#gesture, #state" data_hx_target="#all" data_hx_swap="outerHTML": "Add node"
```

`data_hx_post` names the request. `data_hx_include` names the forms
whose fields are sent. `data_hx_target` and `data_hx_swap` say where
the answer goes.

**The server decides what a request does.** `server.ady` only matches
the path and hands the request on. `Session.answer` does the work, one `case`
per route:

```adascript
class Session:
    ...
    def answer(self, method: str, path: str, fields: str) -> str:
        ...
        case method + " " + path:
            when "GET /all":
                pass
            when "POST /nodes":
                ...
                problem = self.net.add_node(name)
                if problem is None:
                    ...
            when "DELETE /nodes":
                problem = self.net.remove_node(name)
            when "POST /edges":
                problem = self.net.add_edge(a, b, cost_of(fields))
            ...
            when others:
                return ""
        if method != "GET" and problem is None:
            let saved: None | !Refusal_T = self.save()
            if saved is Refusal_T:
                return all_text(self.net, params_of(fields), saved)
        return all_text(self.net, params_of(fields), problem)
```

The routes are listed in a comment above `answer`, in the class. Every answer is the
whole page, which htmx swaps in. A request with an unknown path returns
`""`, and the server answers 404.

![A request, from a click to the new page](request_flow.svg)

**Some events stay in the browser.** A drag must follow the mouse many
times a second, and a server round trip for each move would be too slow.
Those are in `frontend/dijkstra_js_events.ady`, which is compiled to
JavaScript with `ady2nim js`. It sends its final result the same way a
button does: it fills a hidden form, then presses the button.

```adascript
class Selection:
    var what: NodeView | EdgeView | None
    ...
    def remove(self):
        let picked: NodeView | EdgeView | None = self.what
        case picked:
            when NodeView:
                picked.delete()
            when EdgeView:
                picked.delete()
            when None:
                pass
```

What the reader last clicked is a node's view, an edge's view, or nothing, and
the field says so in its type: there is no tag to keep in step with the value.
`case` over a union tests the *type* of each member and narrows: in the first
branch `picked` is a `NodeView`, in the second an `EdgeView`, with no cast. Every
member has to be named, `None` included. A `case` over an enum, an int or a
string compares *values* instead, and a choice that compares different things
still needs an `if` chain: `picked` in `dijkstra_gui.ady` is one.

---

## Step 5: a drag, from the mouse to the page

![Dragging a node: the browser moves it, then the server keeps it](drag_sequence.svg)

Read it from the top:

1. **While the mouse moves**, `moved_cb` runs in the browser. It puts the
   node where the mouse is, the model takes the new place, and `Drawing.redraw_edges`
   draws every edge that ends at it. Nothing goes to the server yet.
2. **On release**, `dropped_cb` fills in the hidden form `#move` with
   the node's name and its new place, and presses `#redraw`.
3. **htmx sends** `PUT /nodes`. `Session.answer` puts the place into the model,
   saves the file, and returns the page.
4. **htmx swaps** the page into `#all`. The new page is the same as the
   one the browser was showing, now drawn from the server's copy.

Here the browser and the server both compute the drawing, which is why
`place_of` is shared: both call the same function on the same network.

---

## Why htmx, and how

![The usual way beside the htmx way](why_htmx.svg)

**Why.** The usual way to make a page change is a JavaScript handler
that fetches JSON and builds the DOM. Then the JavaScript has to know
how the data looks, and the server has to send it in a format that the
JavaScript expects. htmx removes the middle step: the server sends
HTML, and htmx puts it where the attributes say. The page is always what
the server last drew, so there is nothing to keep in step.

**How.** A button, a form or a `div` carries the request in attributes:

| Attribute | Means |
|---|---|
| `data_hx_get="/all"` | send GET to `/all` |
| `data_hx_post`, `data_hx_put`, `data_hx_delete` | send that method |
| `data_hx_include="#gesture, #state"` | send the fields of these forms with it |
| `data_hx_target="#all"` | put the answer in this element |
| `data_hx_swap="outerHTML"` | replace the target, not its contents |
| `data_hx_confirm="..."` | ask first, and send only on yes |
| `data_hx_trigger="load"` | send when the element appears (the first page) |

The attributes are written with underscores, since an Adascript name
cannot contain a dash. `hyphens()` in `dijkstra_gui.ady` turns the whole
page's `data_hx_` into `data-hx-`, the names htmx reads:

```adascript
def hyphens(text: str) -> str:
    return text.replace("data_hx_", "data-hx-")
```

**State.** The network is on the server. The choice the reader has made
(the start and the goal) is in the form `#state`, which every request
sends along. So the server keeps no session, and any page can be
rebuilt from what the request carries.

**Errors.** A refused change returns the whole page again, with the
reason in a red line. Nothing is half-done: the model either did the
change or returned a `Refusal_T`, and the page shows which.

---

## Try it yourself

Each of these changes one layer, so you can see the others not change.

1. **Add a field to the model.** Give `Node_T` a `colour: str`, change
   `add_node` to take it, and make `text()` and `Network(text)` keep it. The
   page does not change until you draw it.
2. **Draw the field.** In `to_html(n: Node_T, …)`, use `n.colour` for the
   circle's `fill`, and add its rule to `NODE_STYLE`.
3. **Add a route.** Add `when "POST /relabel":` to `Session.answer`, read a field
   with `field_of`, and call a new method. Put a button for it in
   `node_buttons_html`, with `data_hx_post="/relabel"`.
4. **Test it without a server.** In `tests/test_dijkstra.ady`, call
   `session.answer("POST", "/relabel", "name=A&colour=red")` and check the page
   contains `red`.

Run `make test` after each step. The model and the page are checked
without a browser; the drag is checked in the browser only.
