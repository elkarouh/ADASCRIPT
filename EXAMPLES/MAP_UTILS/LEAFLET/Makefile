# LEAFLET: route_check on a Leaflet.js map, written in Adascript.
#
#   make        build leaflet_map.js (ady2nim js)
#   make run    build it, serve this directory and open the page
#   make clean  remove what was built
#
# The page loads Leaflet and the OpenStreetMap tiles from the internet.

PORT ?= 8802
OPEN ?= $(shell command -v xdg-open || command -v open || command -v wslview || echo true)

.PHONY: all run clean

all: leaflet_map.js

leaflet_map.js: leaflet_map.ady ../map_base.ady ../map_flat.ady ../map_geo.ady ../regions.ady ../route_check.ady
	@echo "building $@"
	@ady2nim js leaflet_map.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

run: leaflet_map.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/leaflet_map.html) &
	python3 -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f leaflet_map.js leaflet_map build.log
