# LEAFLET: route_check on a Leaflet.js map, written in Adascript.
#
#   make        build leaflet_map.js (ady2nim js)
#   make run    build it, serve this directory and open the page
#   make clean  remove what was built
#
# The page loads Leaflet and the OpenStreetMap tiles from the internet.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../../TO_NIM/ady2nim.py)
PORT ?= 8802
OPEN ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)

.PHONY: all run clean

all: leaflet_map.js

leaflet_map.js: leaflet_map.ady ../map_base.ady ../map_flat.ady ../map_geo.ady ../regions.ady ../route_check.ady
	@echo "building $@"
	@$(ADY2NIM) js leaflet_map.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log
	@# ady2nim leaves a link to its cache build; the page gets a copy of the file
	@cp -L leaflet_map.js leaflet_map.tmp && mv leaflet_map.tmp leaflet_map.js

run: leaflet_map.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/leaflet_map.html) &
	python3 -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f leaflet_map.js leaflet_map leaflet_map.tmp build.log
