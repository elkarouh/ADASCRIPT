.PHONY: all clean run

PORT ?= 8800

all: roi.js

roi.js: roi_glue.ady
	py2nim js roi_glue.ady
	cp -L roi_glue.js $@
	rm -f roi_glue.js

run: roi.js
	@python3 -m http.server $(PORT) --bind 127.0.0.1 &
	@sleep 0.3
	@if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then \
	    curl -s -X PUT "http://localhost:9222/json/new?http://127.0.0.1:$(PORT)/index.html" > /dev/null; \
	else \
	    xdg-open http://127.0.0.1:$(PORT)/index.html; \
	fi

clean:
	rm -f roi.js
