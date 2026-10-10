# EXAMPLES/DIJKSTRA_HTMX: an algorithm with a GUI the server draws, for htmx.
# Needs karax >= 1.5.0 (nimble install karax@1.5.0).
#
#   make app      build drag.js and the server, start it, open the page
#   make test     the algorithm and the page, no server
#   make all      build the server and drag.js, start nothing
#   make clean    remove what was built
#
# $(OPEN) is xdg-open, or open on a Mac; `make app OPEN=firefox` picks one.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8810

.PHONY: all app test clean

all: server frontend/drag.js

# ady2nim keeps its own cache and rebuilds only what changed, so these always run it.
server: backend/dijkstra_model.ady backend/dijkstra_gui.ady backend/server.ady
	@echo "building backend/server"
	@$(ADY2NIM) c backend/server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

# The one script of our own, Adascript compiled to JavaScript; the server sends it as /drag.js.
# backend/ is native (C), frontend/ is what the browser runs; there is nothing to share.
frontend/drag.js: frontend/drag.ady
	@echo "building frontend/drag.js"
	@$(ADY2NIM) js frontend/drag.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

# frontend/htmx.min.js is vendored (in git); if it was deleted, it is restored from git.
frontend/htmx.min.js:
	git checkout -- frontend/htmx.min.js

app: all frontend/htmx.min.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./backend/server $(PORT)

test:
	$(ADY2NIM) c -r test_dijkstra.ady 2>/dev/null

clean:
	rm -f backend/server test_dijkstra frontend/drag.js build.log
