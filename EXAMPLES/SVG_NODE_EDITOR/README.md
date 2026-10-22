# EXAMPLES/SVG_NODE_EDITOR -- a node editor in SVG

Four process nodes, each with three inputs on its left and three outputs on its right, and orange
bezier connectors between them. It is the editor of https://codepen.io/osublake/embed/OxWjgq
written in Adascript, with no JavaScript and no DOM calls in the source.

```
make app        # build the page and the script, serve them, open the page
make all        # build build/index.html and build/node_editor_js_events.js, open none
```

You need karax 1.5.0 or later: `nimble install karax@1.5.0`.

| What you do | What happens |
|---|---|
| drag a node by its body or title | it moves, kept inside the drawing; the connectors at its ports follow |
| press on a port and drag | a connector is drawn from that port to the mouse |
| let go on a port of the other kind (output to input) of another node | the connector snaps to it and stays |
| let go anywhere else | the connector is removed |

## The files

| File | What it is | Runs as |
|---|---|---|
| `backend/node_editor_model.ady` | the geometry: sizes, where each port is, the `Port_T` and `Link_T` values | imported by both |
| `backend/node_editor_gui.ady` | the page: an `html:` block draws the SVG, and the program prints it | native, `ady2nim c -r` |
| `frontend/node_editor_js_events.ady` | what the reader does: the editor keeps where the nodes are and which ports are joined, and draws the connectors from that | browser, `ady2nim js` |

`backend/` is native and `frontend/` is what the browser runs, as in `EXAMPLES/DIJKSTRA_HTMX`; the model is compiled
both ways, so the page and the script agree on where every port is.

The drag of a node is the stdlib's `svg_drag`, the page (finding elements, reading `data_*`
attributes, replacing the connectors' layer) its `browser` module, and a connector's curve
`svg_path.connector_d`, with the original's weight of 0.675.

## Differences from the original

The original moves everything with GSAP (TweenMax, Draggable) and finds a dropped end with
`Draggable.hitTest`. Here the model knows where every port is, so a release is tested against
the ports' positions, and nothing is loaded from a CDN. A connector that already exists is not added a second time.
