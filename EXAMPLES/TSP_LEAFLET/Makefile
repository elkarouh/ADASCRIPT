# TSP_LEAFLET: the travelling salesman algorithms of ../tsp_algorithms.ady, run on real cities in the
# browser and drawn with Leaflet.js.
#
#   make        build tsp_map.js (ady2nim js)
#   make run    build it, serve this directory and open the page
#   make window build it and open it in a native window (tsp_window.ady; needs Nim's webview
#               package and, on Linux, libwebkit2gtk-4.1)
#   make clean  remove what was built
#
# The page loads Leaflet and the OpenStreetMap tiles from the internet.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
PORT ?= 8803
# $(OPEN) is xdg-open, or open on a Mac; on WSL, PowerShell opens the Windows browser.
# `make run OPEN=firefox` picks one.
OPEN ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)

.PHONY: all run window clean

all: tsp_map.js

tsp_map.js: tsp_map.ady ../tsp_algorithms.ady
	@echo "building $@"
	@$(ADY2NIM) js tsp_map.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log
	@# ady2nim leaves a link to its cache build; the page gets a copy of the file
	@cp -L tsp_map.js tsp_map.tmp && mv tsp_map.tmp tsp_map.js

run: tsp_map.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/tsp_map.html) &
	python3 -m http.server $(PORT) --bind 127.0.0.1

window: tsp_map.js
	$(ADY2NIM) c -r --path:$$(nimble path webview) tsp_window.ady

clean:
	rm -f tsp_window tsp_map.js tsp_map tsp_map.tmp build.log
