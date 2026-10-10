# DIJKSTRA_HTMX -- an algorithm with a GUI drawn by the server

The smallest version of the architecture of `TOOLS/ACCOUNTING`: the program is
native, the browser only shows what the server draws, and htmx carries the
clicks.

```
ady2nim c -r server.ady        # then open http://127.0.0.1:8810/
ady2nim c -r test_dijkstra.ady # the algorithm and the page, no server
```

Click a node to start from, another to go to; the shortest way is drawn in
orange. Change a cost in the table and the way is found again.

| File | What it knows |
|---|---|
| `dijkstra.ady` | the problem: edges, `shortest_way`. No HTML, no HTTP. |
| `page.ady` | how to draw it: the SVG, the form, the text. A function from the settings to HTML. |
| `server.ady` | HTTP: three routes (`/`, `/all`, `/htmx.min.js`). |
| `test_dijkstra.ady` | tests of the first two, by calling them; nothing is started. |
| `htmx.min.js` | htmx, vendored (14 KB gzipped). |

## How it works

* The server **keeps no state**. What the page shows (the costs, the two nodes
  picked) is the fields of the form `#state` in the page.
* A click or a change asks `GET /all` with the form's fields, plus a one-shot
  field for what was just clicked (`pick`, `act`); the answer is the whole
  page, and htmx swaps it in. (`hx-get`, `hx-include="#state"`, `hx-vals`,
  `hx-target="#all"`, `hx-swap="outerHTML"`: five attributes, all in `page.ady`.)
* So the page is a pure function, `all_text(query)`, and testing the GUI is
  testing a function: see the last lines of `test_dijkstra.ady`.
* The algorithm never learns about any of it. A different front end (a command
  line, a test) uses `shortest_way` unchanged.

## When it fits, and when it does not

It fits when an answer is cheap to compute and a round trip per click is fine:
algorithms, forms, tables, dashboards, a graph that is re-drawn. Everything
stays in one language, and what the browser runs is almost nothing.

It does not fit what must follow the mouse every frame (dragging, drawing). That
is a small script of your own in the browser (Adascript to JavaScript), as
`TOOLS/ACCOUNTING/frontend/drag.ady` does, reusing the same code the server
draws with where it must give the same result. Nothing here needs it: a click
is one request.
