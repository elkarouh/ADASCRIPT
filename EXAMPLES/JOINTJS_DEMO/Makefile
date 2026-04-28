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
	@xdg-open http://127.0.0.1:$(PORT)/index.html

clean:
	rm -f roi.js
