# ROI_HTMX -- the ROI_JOINTJS page, without JointJS

`EXAMPLES/ROI_JOINTJS` draws a return-on-investment diagram with the JointJS
library: boxes with fields in them, joined by arrows. This is the same page in
the architecture of `TOOLS/ACCOUNTING` and `EXAMPLES/DIJKSTRA_HTMX`: the program
is native, the diagram is an SVG that the server draws, and htmx carries each
change. There is no diagram library; the one script of our own is the drag.

```
make app          # builds the server and the script, starts it and opens http://127.0.0.1:8820/
make test         # the model, the page and the requests, no server
```

Put in some money, the year you invested it, and how you split it between gold,
bitcoin and the S&P 500 (prices of 2013 to 2023). The page shows what each part
is worth now and the return on the whole. When you change one share the others
give or take the difference, the first one first, and none goes below 0.

How a box and an arrow are drawn, without JointJS:

- a box is a `<rect>` and, on top of it, a `<foreignObject>`: a piece of HTML (labels,
  number fields, a year list) placed inside the SVG;
- an arrow is two `<path>`s, a black one underneath and the colour on it, with a
  marker for the head;
- a box that is dragged moves in the browser, with its arrows (`frontend/roi_js_events.ady`,
  built on the library's `svg_drag`, as in `TOOLS/ACCOUNTING`); letting go sends `PUT /move`;
- a field that is changed asks `GET /all` with its value and what it is
  (`changed=gold&value=40`); the server changes the plan, works out the values and
  sends the whole diagram, which htmx puts in place of the old one.

Drag a box (the investment, a product, or the big box of the results, which takes its three
results along) and its arrows follow, as curves, at once; where you let go is kept. Only the
box itself can be taken hold of, not the fields in it.

The plan, and where the boxes are, are kept in memory: it starts again when the server does.

| File | What it knows |
|---|---|
| `backend/roi_model.ady` | the model: the prices, a `Plan` (money, year, the three shares, where the boxes are), `evaluate` for what it is worth now, `set_share` for the rebalancing, `move_block` for a drop. No HTML, no HTTP. |
| `backend/roi_gui.ady` | how to draw it: a function from the plan to HTML; `box_html`, `arrow_html` and one function for the contents of each kind of box. |
| `backend/roi_events.ady` | what each request does: `answer(method, path, fields)` changes the plan and returns the diagram. Holds the plan. No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP, and nothing else: hands each request to `answer`, and serves the two scripts. |
| `frontend/roi_js_events.ady` | the browser side, compiled to JavaScript: moves a box and redraws its arrows while the mouse moves, then sends the new place. |
| `frontend/htmx.min.js` | htmx, vendored. |
| `test_roi.ady` | tests of the model, and of the page through `answer`, as the browser would ask. |
