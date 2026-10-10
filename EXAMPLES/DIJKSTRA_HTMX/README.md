# DIJKSTRA_HTMX -- an algorithm with a GUI drawn by the server

The smallest version of the architecture of `TOOLS/ACCOUNTING`: the program is
native, the browser only shows what the server draws, and htmx carries the
clicks.

```
make app                      # builds drag.js and the server, starts it and opens the page
make test                     # the algorithm and the page, no server
# or by hand:
ady2nim js frontend/drag.ady   # the one script of our own, frontend/drag.js
ady2nim c -r backend/server.ady # then open http://127.0.0.1:8810/ (run from this directory)
ady2nim c -r test_dijkstra.ady # the algorithm and the page, no server
```

Click a node to start from, another to go to; the shortest way is drawn in
orange. Change a cost in the table and the way is found again. Drag a node and
its edges follow; where you let go is kept in the page and drawn by the server.

| File | What it knows |
|---|---|
| `backend/dijkstra_model.ady` | the model, a placeholder: the nodes, edges and costs, and `build_graph`, which makes of them the graph the library's `shortest_route` (`TO_NIM/STDLIB/graphs.ady`). Replace it with your own; no HTML, no HTTP. |
| `backend/page.ady` | how to draw it: the SVG, the form, the text. A function from the settings to HTML. |
| `backend/server.ady` | HTTP: four routes (`/`, `/all`, `/htmx.min.js`, `/drag.js`). |
| `frontend/drag.ady` | the browser side, compiled to JavaScript: moves a node and redraws its edges while the mouse moves (the server could not keep up with every frame), then writes the place into the form and asks the server for the page, which draws the same. About 100 lines. |
| `test_dijkstra.ady` | tests of the first two, by calling them; nothing is started. |
| `frontend/htmx.min.js` | htmx, vendored (14 KB gzipped). |

`backend/` is native (compiled to C), `frontend/` is what the browser runs (JavaScript: our `drag.ady` and the vendored htmx). Nothing is compiled both ways here, so there is no `shared/`; the accounting tool has one, for the arrow routing that the server and `drag.ady` must agree on.

## How it works

* The server **keeps no state**. What the page shows (the costs, the two nodes
  picked) is the fields of the form `#state` in the page.
* A click or a change asks `GET /all` with the form's fields, plus a one-shot
  field for what was just clicked (`pick`, `act`); the answer is the whole
  page, and htmx swaps it in. (`hx-get`, `hx-include="#state"`, `hx-vals`,
  `hx-target="#all"`, `hx-swap="outerHTML"`: five attributes, all in `backend/page.ady`.)
* So the page is a pure function, `all_text(query)`, and testing the GUI is
  testing a function: see the last lines of `test_dijkstra.ady`.
* The algorithm never learns about any of it. A different front end (a command
  line, a test) uses `build_graph` and `shortest_route` unchanged.

## When it fits, and when it does not

It fits when an answer is cheap to compute and a round trip per click is fine:
algorithms, forms, tables, dashboards, a graph that is re-drawn. Everything
stays in one language, and what the browser runs is almost nothing.

It does not fit what must follow the mouse every frame. That is what
`drag.ady` is for: the same language, compiled to JavaScript, doing only the
moving; the page and the answer are still the server's. A drag is the one place
where the drawing exists twice (here the straight line of an edge, in
`../../TOOLS/ACCOUNTING/frontend/drag.ady` the same `routes_of` the server
uses), so keep that part small.
