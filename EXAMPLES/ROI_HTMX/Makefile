# EXAMPLES/ROI_HTMX: the JOINTJS_DEMO page without JointJS: the boxes and arrows are an
# SVG the server draws, and htmx carries each change. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make app      build the server, start it, open the page
#   make test     the model, the page and the requests, no server
#   make clean    remove what was built
#
# $(OPEN) is xdg-open, or open on a Mac; on WSL, PowerShell opens the Windows browser.
# `make app OPEN=firefox` picks one.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
PORT    ?= 8820

.PHONY: all app test clean

all: server

# ady2nim keeps its own cache and rebuilds only what changed, so this always runs it.
server: backend/roi_model.ady backend/roi_gui.ady backend/roi_events.ady backend/server.ady
	@echo "building backend/server"
	@$(ADY2NIM) c backend/server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

# frontend/htmx.min.js is vendored (in git); if it was deleted, it is restored from git.
frontend/htmx.min.js:
	git checkout -- frontend/htmx.min.js

app: server frontend/htmx.min.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./backend/server $(PORT)

test:
	$(ADY2NIM) c -r test_roi.ady 2>/dev/null

clean:
	rm -f backend/server test_roi build.log
