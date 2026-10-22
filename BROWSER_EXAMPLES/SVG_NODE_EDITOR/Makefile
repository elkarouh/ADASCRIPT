# BROWSER_EXAMPLES/SVG_NODE_EDITOR: a node editor with a GUI the server draws, for htmx. Needs karax >= 1.5.0
# (nimble install karax@1.5.0). The diagram is kept in diagram.txt, in the directory the server runs in.
#
#   make app      build node_editor_js_events.js and the server, start it, open the page
#   make test     the model, the page, the requests and the file, no server
#   make all      build the server and node_editor_js_events.js, start nothing
#   make clean    remove what was built
#
# $(OPEN) is xdg-open, or open on a Mac; on WSL, PowerShell opens the Windows browser.
# `make app OPEN=firefox` picks one.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
PORT    ?= 8802

.PHONY: all app test clean

all: server frontend/node_editor_js_events.js

# ady2nim keeps its own cache and rebuilds only what changed, so this always runs it.
server: backend/node_editor_model.ady backend/node_editor_request.ady backend/node_editor_gui.ady backend/node_editor_events_gui.ady backend/server.ady
	@echo "building backend/server"
	@$(ADY2NIM) c backend/server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

# The one script of our own, Adascript compiled to JavaScript; the server sends it as /node_editor_js_events.js.
# backend/ is native (C), frontend/ is what the browser runs; the model is compiled both ways.
frontend/node_editor_js_events.js: frontend/node_editor_js_events.ady backend/node_editor_model.ady
	@echo "building frontend/node_editor_js_events.js"
	@$(ADY2NIM) js frontend/node_editor_js_events.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

app: all
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./backend/server $(PORT)

test:
	$(ADY2NIM) c -r tests/test_node_editor.ady 2>/dev/null

clean:
	rm -rf backend/server tests/test_node_editor test_node_editor frontend/node_editor_js_events.js build.log build \
	    backend/node_editor_model backend/node_editor_gui backend/node_editor_request backend/node_editor_events_gui
