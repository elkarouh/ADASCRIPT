# BROWSER_EXAMPLES -- programs whose page runs in a browser

| Directory | What it shows |
|---|---|
| `SHOPPING_LIST/` | a shopping list in the browser alone, no server: the app of the tutorial in `DOCS/ADASCRIPT_FOR_JAVASCRIPT.md` |
| `HTML/` | pages written as objects with `html:` blocks: a card drawn as SVG, and a page of widgets with buttons |
| `DIJKSTRA_HTMX/` | shortest path, with a GUI the server draws and htmx keeps up to date; `backend/` is native, `frontend/` runs in the browser |
| `ROI_HTMX/` | a return-on-investment diagram in the same shape |
| `ROI_JOINTJS/` | the same diagram drawn in the browser with JointJS |
| `LITTLE_PAGES/` | lots of little HTML pages, one per filter |
| `SVG_NODE_EDITOR/` | a node editor: drag nodes, and connect ports with bezier connectors |
| `ACCOUNTING/` | learning accounting as graph theory: a model, a ledger kept in SQLite, and a page the server draws, with draggable accounts |

Each is built with `make` in its own directory (see its README); `make test` at the top of the
repository checks the ones that have a test. The scripts are written in Adascript and compiled
with `ady2nim js`, using the stdlib's `browser`, `svg_drag` and `svg_path` modules.
