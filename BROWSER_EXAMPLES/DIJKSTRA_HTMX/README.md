# DIJKSTRA_HTMX -- an algorithm with a GUI drawn by the server

The smallest version of the architecture of `BROWSER_EXAMPLES/ACCOUNTING`: the program is
native, the browser only shows what the server draws, and htmx carries the
clicks.

The tutorial, `docs/TUTORIAL.md`, builds it step by step: the objects in the model, their
picture, the events, and why htmx.

![The files of this example and what each imports](docs/dependencies.png)

```
make app                      # builds dijkstra_js_events.js and the server, starts it and opens the page
make test                     # the model, the page and the requests, no server
# or by hand:
ady2nim js frontend/dijkstra_js_events.ady   # the one script of our own, frontend/dijkstra_js_events.js
ady2nim c -r backend/server.ady # then open http://127.0.0.1:8810/ (run from this directory)
ady2nim c -r tests/test_dijkstra.ady # the model, the page and the requests, no server
```

Click a node to start from, another to go to; the shortest way is drawn in
orange. The drawing is the network, and every part of it can be
created, changed and deleted: add a node or an edge, change a cost, and delete from the
right-click menu or with the Delete key. Drag a node and its edges follow; where you let go is kept. The server
keeps the network in `graph.txt` (in the directory it runs in), written after
every change; Reset puts the sample back. Open it in two tabs: a change made in one shows in
the other.

| File | What it knows |
|---|---|
| `backend/dijkstra_model.ady` | the model, a placeholder: a class `Network` of `Node_T`s (a name each), `Edge_T`s and the places the reader put the nodes, with its methods (`add_node`, `remove_node`, `add_edge`, `set_cost`, `remove_edge`, `put`, `forget_places`, each `add`, `remove` or `set` refusing with a `Refusal_T` (its `message` is what the page shows), or done; `names`, `edge_at`, `text`, `build_graph`, which makes of it the graph the library's `shortest_route` wants, `TO_NIM/STDLIB/graphs.ady`); `Network(text)`, a second constructor, reads it back from text. Its last part is the layout, where each node is drawn when the reader has not put it somewhere: `place_of` (the places the model keeps, else `new_spot`, the layout algorithm: evenly spaced round an ellipse, in the model's order), and `inside`, which keeps a node within the drawing's margin. Compiled both ways: the server draws the page with it, and the browser's `NetworkView` moves nodes with it. Replace it with your own; no HTML, no HTTP. |
| `backend/dijkstra_commands.ady` | the vocabulary of the page and the server: a `Command` (a `Command_Of` the app's things, from the stdlib's `commands.ady`) is a verb (`CREATE`, `READ`, `UPDATE`, `DELETE`), what it is done to (`NODE`, `EDGE`, the `NETWORK` that is read) and its fields; one function per command (`create_node`, `update_node`, `delete_node`, `create_edge`, `update_edge`, `delete_edge`, `read_network`); `c.method()` and `c.url()` put it on the wire, `command_of` reads it back. Compiled both ways, like the model: the page makes commands, the server carries them out, and what changed goes out in the same verbs. No HTML, no HTTP. |
| `backend/dijkstra_gui.ady` | how to draw it: the SVG, the buttons, the form `#state`, the menus, the text. A function from the network and what is picked to HTML: `all_html` for the page, `problem_html` for the answer to a command, `to_html` for the drawing and for each node and edge in it. |
| `backend/dijkstra_events_gui.ady` | what each request does: `Session.answer(method, path, fields)` makes it a `Page_Request` (the stdlib's `page_server.ady`: its method, path and fields, read once) and reads it back into a `Command` (`command_of`); a read returns the page; a change (`carry_out`) calls the model, answers only whether it went through (`#problem`), and publishes the `Change` on its channel (`NODES_CHAN`, `EDGES_CHAN`). A `Session` holds the network and the file it is kept in (`keep` writes it). No HTTP, so the tests call it. |
| `backend/server.ady` | HTTP, and who hears of a change: hands each request to `session.answer`, serves the two scripts, keeps `GET /events` open for every page (the stdlib's `page_server.ady`: `News`), and subscribes `keep` (writes `graph.txt`) and `tell` (writes the change to every open page) to the session's channels. |
| `frontend/dijkstra_js_events.ady` | the browser side, compiled to JavaScript, built like the server: a blackboard of its own. Every gesture publishes a command (`backend/dijkstra_commands.ady`) on the channel `commands_channel`, and two observers (the stdlib blackboard's `Observer`: an object that subscribes itself, its `callback` what it does) carry it out: `Liaison_Officer` sends the server what is the model's (its `callback`, the one place the page talks to the server), and `Mouse_Follower` draws a draft (a node still held, `move_node`) here and now, which the liaison keeps in the browser (the server could not keep up with every frame). What `GET /events` says changed goes on the channel `changes_channel`, and `Page_Refresher` reads the page again (`GET /all`, into `#all`), whichever page made it. |
| `tests/test_dijkstra.ady` | tests of the model, and of the page through `session.answer`, as the browser would ask (a command, then the page read again), and of what a subscriber hears; nothing is started. |
| `frontend/htmx.min.js` | htmx, vendored (14 KB gzipped). |

`backend/` is native (compiled to C), `frontend/` is what the browser runs (JavaScript: our `dijkstra_js_events.ady` and the vendored htmx). The model (its layout included) and the commands are compiled both ways: the page carries the network, its places included, as the server keeps it (a hidden `pre#network`), and `dijkstra_js_events.ady` builds its `NetworkView`, a kind of `Network`, from that with the same `Network(text)`, so where a node is drawn is computed from the model, never read off the drawing.

## How it works

The routes are a small REST interface on two collections. Commands in, events out: the read answers the whole page; a command answers only whether it went through (the paragraph `#problem`, empty when it did), and each change it made is told to every open page, which reads itself again:

| Request | Does | Fields |
|---|---|---|
| `GET /all` | read: the page | `start`, `goal`, `pick`, `act` |
| `POST /nodes` | create a node | `name` |
| `PUT /nodes` | move a node (a drag) | `name`, `x`, `y` |
| `DELETE /nodes` | delete a node, and its edges | `name` |
| `POST /edges` | create an edge | `a`, `b`, `cost` |
| `PUT /edges` | change a cost | `a`, `b`, `cost` |
| `DELETE /edges` | delete an edge | `a`, `b` |
| `POST /relayout` | every node where the layout puts it | |
| `POST /reset` | put the sample back | |
| `GET /events` | the changes, as they are made: a stream every open page follows, and draws itself again on | |

* The **network** is the server's (the model, kept in `graph.txt` by a subscriber, after every change). **What the
  reader has picked** (the start and the goal) is the page's: the fields of the
  form `#state`, sent with every request, so the server keeps no session.
* The toolbar's buttons (Relayout, Reset) name their request in htmx attributes
  (`hx-post`, `hx-confirm`; `hx-target="#problem"`, `hx-swap="outerHTML"`), and the
  first page loads itself with `hx-get="/all"`, all in `backend/dijkstra_gui.ady`. htmx
  sends it and swaps in the answer; the page is drawn again on the news of the change.
* A gesture on the drawing (a click on a node, a drag, a wire, a double-click, a
  menu, the Delete key) has no button: it makes a **command**, Create, Read, Update or
  Delete of a node or an edge, and publishes it on the page's blackboard: `commands_channel.publish(delete_node(n))`
  (`backend/dijkstra_commands.ady`). The liaison sends it on; a draft (a node still held) it
  keeps in the browser. Several gestures make the same command (Delete,
  Backspace and the menu's "Delete node" all make `delete_node`), and nothing after the
  command knows which gesture it was. The verb is the HTTP method, the thing the URL;
  the browser module's `send_request` sends it with `#state`, into `#problem` (a read, into
  `#all`). So the page holds no hidden forms or buttons for the script to fill in and press.
* A mistake (a name taken, an edge that is there already) comes back as a line
  in red on the page that made it; nothing is changed, and no other page hears of it.
* Who hears of a change is decided by subscribing, not in `answer`: the `Network` is the
  blackboard, `Session.answer` the control, and `keep` (the file) and `tell` (every open page)
  knowledge sources that know nothing of each other. The page has a blackboard of its own
  (`commands_channel` out, `changes_channel` in), and the liaison between the two. See "The blackboard" and
  "Two blackboards and a liaison" in `docs/TUTORIAL.md`.
* So testing the GUI is calling `session.answer(method, path, fields)`, reading the
  page, and subscribing to hear what changed: see `tests/test_dijkstra.ady`.
* The algorithm never learns about any of it. A different front end (a command
  line, a test) uses the model, `build_graph` and `shortest_route` unchanged.

## When it fits, and when it does not

It fits when an answer is cheap to compute and a round trip or two per click is fine
(a change is a command, then the page read again):
algorithms, forms, tables, dashboards, a graph that is re-drawn. Everything
stays in one language, and what the browser runs is almost nothing.

It does not fit what must follow the mouse every frame. That is what
`dijkstra_js_events.ady` is for: the same language, compiled to JavaScript, doing only the
moving; the page and the answer are still the server's. A drag is the one place
where the drawing exists twice (here the straight line of an edge, in
`../ACCOUNTING/frontend/accounting_js_events.ady` the same `routes_of` the server
uses), so keep that part small.
