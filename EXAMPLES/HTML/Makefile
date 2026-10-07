.PHONY: all run clean

PORT ?= 8801

all: html_counter.js

html_counter.js: html_counter.ady
	ady2nim js html_counter.ady
	cp -L html_counter.js $@.tmp && mv $@.tmp $@

run: all
	@echo "http://127.0.0.1:$(PORT)/index.html"
	python3 -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f html_counter.js
