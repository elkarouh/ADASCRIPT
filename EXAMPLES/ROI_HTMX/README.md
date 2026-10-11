# ROI_HTMX -- the JOINTJS_DEMO page, without JointJS

`EXAMPLES/JOINTJS_DEMO` draws a return-on-investment diagram with the JointJS
library: boxes with fields in them, joined by arrows. This is the same page in
the architecture of `TOOLS/ACCOUNTING` and `EXAMPLES/DIJKSTRA_HTMX`: the program
is native, the diagram is an SVG that the server draws, and htmx carries each
change. There is no diagram library and no script of our own.

```
make app          # builds the server, starts it and opens http://127.0.0.1:8820/
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
- a field that is changed asks `GET /all` with its value and what it is
  (`changed=gold&value=40`); the server changes the plan, works out the values and
  sends the whole diagram, which htmx puts in place of the old one.

The plan is kept in memory: it starts again when the server does.

| File | What it knows |
|---|---|
| `backend/roi_model.ady` | the model: the prices, a `Plan` (money, year, the three shares), `evaluate` for what it is worth now, `set_share` for the rebalancing. No HTML, no HTTP. |
| `backend/roi_gui.ady` | how to draw it: a function from the plan to HTML; `box_html`, `arrow_html` and one function for the contents of each kind of box. |
| `backend/roi_events.ady` | what each request does: `answer(method, path, fields)` changes the plan and returns the diagram. Holds the plan. No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP, and nothing else: hands each request to `answer`, and serves htmx. |
| `frontend/htmx.min.js` | htmx, vendored. |
| `test_roi.ady` | tests of the model, and of the page through `answer`, as the browser would ask. |
