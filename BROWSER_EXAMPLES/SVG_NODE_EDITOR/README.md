# BROWSER_EXAMPLES/SVG_NODE_EDITOR -- a node editor in SVG

Process nodes, each with three inputs on its left and three outputs on its right, and orange bezier
connectors between them. It is the editor of https://codepen.io/osublake/embed/OxWjgq written in
Adascript, with no JavaScript and no DOM calls in the source. It has the shape of `BROWSER_EXAMPLES/DIJKSTRA_HTMX`:
a native server that keeps the diagram in a file, and a small script for what must follow the mouse.

```
make app        # builds the script and the server, starts it and opens the page (http://127.0.0.1:8802/)
make test       # the model, the page, the requests and the file, no server
```

You need karax 1.5.0 or later: `nimble install karax@1.5.0`.

| What you do | What happens |
|---|---|
| double-click the space | a new node there; you are asked its title |
| drag a node by its body or title | it moves, kept inside the drawing; its connectors follow, and where you let go is kept |
| press on a port and drag | a connector is drawn from that port to the mouse |
| let go on a port of the other kind (output to input) of another node | the connector is made and kept |
| let go anywhere else | the connector is removed |
| click a node or a connector | it is selected (outlined) |
| Delete, Backspace | the selection goes (a node, with its connectors, after asking) |
| Escape | the selection is cleared |

The server keeps the diagram in `diagram.txt`, in the directory it runs in, written after every
change; if there is none, the four nodes of the original are made. A line a node, a line a connector:

```
node 0 50 50 Process 1       its id, top left corner and title
link 0 2 3 2                 from output 2 of node 0 to input 2 of node 3
```

A node keeps its id for good, so deleting one does not renumber the ports of the others.

## The files

| File | What it knows |
|---|---|
| `backend/node_editor_model.ady` | the model: a class `Diagram` of `Node_T`s (each with its `Port_T`s) and `Link_T`s (each joining two `Pin_T`s, a node id and a port) with its methods (`add_node`, `move`, `remove_node`, `add_link`, `remove_link`, each refusing with a `Refusal_T` or done), the geometry (where each port is), `text` and `Diagram(text)`, which write the file and read it back. Compiled both ways. No HTML, no HTTP. |
| `backend/node_editor_request.ady` | the fields of a request: `field_of`, `number_of`, `port_of`. |
| `backend/node_editor_gui.ady` | how to draw it: the nodes as SVG with `html:` blocks, the page, the diagram as text for the script. The connectors are not drawn here; the script draws them. |
| `backend/node_editor_events_gui.ady` | what each request does: `Session.answer(method, path, fields)` calls the model, saves the file, and returns the page. No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP and nothing else. |
| `frontend/node_editor_js_events.ady` | the browser side, compiled to JavaScript: a `View` built from the diagram text draws the connectors, follows the mouse, and sends every change to the server (`request`, from the stdlib's `browser`); the page the server answers with takes the place of the old one. |
| `tests/test_node_editor.ady` | tests of the model, of the page through `Session.answer`, and of the file. |
| `frontend/htmx.min.js` | htmx, vendored. |

The drag of a node is the stdlib's `svg_drag`, the page (finding elements, questions, keys) its `browser`
module, and a connector's curve `svg_path.connector_d`, with the original's weight of 0.675.

## Differences from the original

The original moves everything with GSAP (TweenMax, Draggable) and finds a dropped end with
`Draggable.hitTest`. Here the model knows where every port is, so a press and a release are tested
against the ports' positions, and nothing is loaded from a CDN. A connector that already exists is not
made a second time. Creating and deleting nodes and connectors, and the file, are not in the original.
