# BROWSER_EXAMPLES/SVG_NODE_EDITOR -- a node editor in SVG

Process nodes, each with three inputs on its left and three outputs on its right, and orange bezier
connectors between them. It is the editor of https://codepen.io/osublake/embed/OxWjgq written in
Adascript, with no JavaScript and no DOM calls in the source. It has the shape of `BROWSER_EXAMPLES/DIJKSTRA_HTMX`:
a native server that keeps the diagram in a file and tells every open page of each change, and a small script for what must follow the mouse.

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
| (a change, from any open page) | every page is drawn again |

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
| `backend/node_editor_commands.ady` | the one vocabulary of the page and the server: a `Command` (a `Command_Of` this app's things, from the stdlib's `commands.ady`) is Create, Read, Update or Delete of a node, a connector, or the whole diagram (read only), with its fields. On the wire the verb is the HTTP method and the thing the URL (`method`, `url`, and `command_of` back). `move_node` is a draft: the node still held, which stays in the browser. Compiled both ways. |
| `backend/node_editor_gui.ady` | how to draw it: the nodes as SVG with `html:` blocks, the page, the diagram as text for the script. The connectors are not drawn here; the script draws them. |
| `backend/node_editor_events_gui.ady` | what each request does: `Session.answer(method, path, fields)` reads it back into a `Command` and carries it out on the model. A read answers the whole page; a change only the paragraph `#problem` (empty when it went through), and what it changed is published on the session's blackboard (stdlib's `blackboard.ady`): `NODES_CHAN` or `LINKS_CHAN` carries a `Change`. No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP and nothing else, and the two subscribers to the session's changes: `keep`, which writes `diagram.txt`, and `tell`, which tells every open page (`GET /events`, server-sent events, through the stdlib's `page_server.ady`). |
| `frontend/node_editor_js_events.ady` | the browser side, compiled to JavaScript, built as DIJKSTRA_HTMX's is: a blackboard of its own (with the stdlib's `page_board.ady`: the changes channel and the liaison). Every gesture (`Selection`, `Pointer`, `Connector`, each an object whose `__init__` says which event runs which of its methods) publishes a command on `commands_channel`, and two observers (the stdlib blackboard's `Observer`) carry it out: `Liaison_Officer` sends the server what is the diagram's, and brings its news back onto `changes_channel`; `Mouse_Follower` draws a draft (a node still held) here and now. `Page_Refresher` reads the page again on every change, whichever page made it. A `DiagramView`, the model built from the diagram text, draws the connectors. |
| `tests/test_node_editor.ady` | tests of the model, of the page and the changes it publishes through `Session.answer`, and of the file. |
| `frontend/htmx.min.js` | htmx, vendored. |

The drag of a node is the stdlib's `svg_drag`, the page (finding elements, questions, keys) its `browser`
module, and a connector's curve `svg_path.connector_d`, with the original's weight of 0.675.

## Differences from the original

The original moves everything with GSAP (TweenMax, Draggable) and finds a dropped end with
`Draggable.hitTest`. Here the model knows where every port is, so a press and a release are tested
against the ports' positions, and nothing is loaded from a CDN. A connector that already exists is not
made a second time. Creating and deleting nodes and connectors, and the file, are not in the original.
