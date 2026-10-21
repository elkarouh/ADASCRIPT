# OPLOG: the ARCHIVED_OPLOG decoder, and a map of one flight from it.
#
#   make                          build decode_oplog and oplog_map.js (ady2nim js)
#   make page CALLSIGN=SAS123    write the flight's page, flight.html, from sample_oplog.txt
#   make run  CALLSIGN=SAS123    ... then serve this directory and open it
#   make clean                    remove what was built
#
# The page loads Leaflet and the OpenStreetMap tiles from the internet.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
PORT ?= 8803
CALLSIGN ?= SAS123
OPEN ?= $(shell command -v xdg-open || command -v open || command -v wslview || echo true)

.PHONY: all page run clean

all: decode_oplog oplog_map.js

decode_oplog: decode_oplog.ady
	@echo "building $@"
	@$(ADY2NIM) c -o:decode_oplog decode_oplog.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

oplog_map.js: oplog_map.ady
	@echo "building $@"
	@$(ADY2NIM) js oplog_map.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log
	@# ady2nim leaves a link to its cache build; the page gets a copy of the file
	@cp -L oplog_map.js oplog_map.tmp && mv oplog_map.tmp oplog_map.js

page: all
	./decode_oplog sample_oplog.txt --callsign $(CALLSIGN) --html flight.html

run: page
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/flight.html) &
	python3 -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f decode_oplog oplog_map.js oplog_map.tmp flight.html build.log
