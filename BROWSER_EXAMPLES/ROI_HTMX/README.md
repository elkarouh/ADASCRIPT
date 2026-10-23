# ROI_HTMX -- the ROI_JOINTJS page, without JointJS

`BROWSER_EXAMPLES/ROI_JOINTJS` draws a return-on-investment diagram with the JointJS
library: boxes with fields in them, joined by arrows. This is the same page in
the architecture of `BROWSER_EXAMPLES/ACCOUNTING` and `BROWSER_EXAMPLES/DIJKSTRA_HTMX`: the program
is native, the diagram is an SVG that the server draws, and htmx carries each
change. There is no diagram library; the one script of our own is the drag, and
the page kept up with the server.

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
- every request is a command, in one vocabulary the page and the server share
  (`backend/roi_commands.ady`): Read the portfolio (`GET /all`), or Update the investment
  (`PUT /investment`, funds or year), a share (`PUT /shares`, product and percentage) or a
  block (`PUT /blocks`, its name and centre);
- a field that is changed sends itself, with the command its hx-* attributes name. The answer
  is only the paragraph `#problem`: empty, or why not (a year with no prices, a negative sum);
- a box that is dragged moves in the browser, with its arrows (`frontend/roi_js_events.ady`,
  built on the library's `svg_drag`); letting go sends `PUT /blocks`;
- a change that went through is published on the server's channels, and `GET /events` tells
  every open page, which reads itself again: a second tab follows every change.

The script is built as `BROWSER_EXAMPLES/DIJKSTRA_HTMX`'s is: the drag publishes commands on the
page's blackboard, and observers carry them out (the liaison officer sends them, the mouse follower
draws a block still held, the page refresher reads the page again on the server's news).

Drag a box (the investment, a product, or the big box of the results, which takes its three
results along) and its arrows follow, as curves, at once; where you let go is kept. Only the
box itself can be taken hold of, not the fields in it.

The portfolio, and where the boxes are, are kept in memory: it starts again when the server does.

| File | What it knows |
|---|---|
| `backend/roi_model.ady` | the model, with no HTML, no HTTP and no places: an `Investment` (money, year), an `InvestmentPercentage` (product, percentage) for each of the three products, held with it by a `Portfolio`, which also owns the rebalancing (`set_share`); `evaluate` gives an `Outcome`, a `ProductOutcome` for each product and the overall performance. Each box of the drawing is one of these. |
| `backend/roi_layout.ady` | where the boxes are: a `Layout` of centres, what a drag changes (`move_block`), and the size of the drawing. The model knows none of it. |
| `backend/roi_gui.ady` | how to draw it: a `to_html` for each model type (what it looks like inside its box), and the boxes, the arrows and the page around them, from the portfolio and the layout. |
| `backend/roi_commands.ady` | the commands, the one vocabulary of the page and the server: their verbs, what they are done to, their method and URL on the wire, and `command_of`, which reads a request back. Compiled both ways. |
| `backend/roi_events.ady` | what each request does: a `Session` holds the portfolio and the layout, `answer(method, path, fields)` reads the request into a command, carries it out and publishes what changed on its channels. No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP, and nothing else: hands each request to the session, serves the two scripts, and tells every page following `GET /events` of each change. |
| `frontend/roi_js_events.ady` | the browser side, compiled to JavaScript: the blackboard, its observers, and the drag of a box. |
| `frontend/htmx.min.js` | htmx, vendored. |
| `test_roi.ady` | tests of the model, and of the page through a `Session`, as the browser would ask, with the changes it publishes. |
