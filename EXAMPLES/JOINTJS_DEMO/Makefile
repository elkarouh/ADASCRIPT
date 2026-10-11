.PHONY: all clean run

PORT ?= 8800
OPEN ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)

all: roi.js

roi.js: roi_glue.ady
	ady2nim js roi_glue.ady
	cp -L roi_glue.js $@
	rm -f roi_glue.js

run: roi.js
	@ss -tlnp 2>/dev/null | grep -q ":$(PORT) " || python3 -m http.server $(PORT) --bind 127.0.0.1 &
	@sleep 0.3
	@if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then \
	    curl -s -X PUT "http://localhost:9222/json/new?http://127.0.0.1:$(PORT)/index.html" > /dev/null; \
	else \
	    $(OPEN) http://127.0.0.1:$(PORT)/index.html; \
	fi

clean:
	rm -f roi.js
