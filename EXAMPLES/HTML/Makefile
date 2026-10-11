# EXAMPLES/HTML: pages written with html: blocks. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make card       one widget                               (html_card.ady)
#   make app        a page as a tree of widgets, served      (html_app.ady)
#   make all        build every page into build/, open none
#
# The worked web apps are elsewhere: TOOLS/ACCOUNTING (Kleppmann's accounting,
# which started here) and EXAMPLES/DIJKSTRA_HTMX, both drawn on the server and
# kept up to date by htmx.
#
# Each target builds its page into build/ and opens it in the browser:
# $(OPEN) is xdg-open, or open on a Mac; `make card OPEN=firefox` picks one.

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
PORT    ?= 8801

PAGES := html_card

.PHONY: all card app clean

all: $(PAGES:%=build/%.html) build/html_app.js

# A page is the program's output. Its compile messages go to a log, shown
# only when the build fails.
build/%.html: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/$*.log \
	    || { cat build/$*.log; rm -f $@; exit 1; }

card:    build/html_card.html
	@echo "serving http://127.0.0.1:$(PORT)/html_card.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/html_card.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

# A page with events is a script, built by `ady2nim js`, and a page that
# loads it (index.html), served.
build/%.js: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/$*.log 2>&1 || { cat build/$*.log; exit 1; }
	@cp -L $*.js $@ && rm -f $*.js

app: build/html_app.js
	@cp index.html build/
	@echo "serving http://127.0.0.1:$(PORT)/index.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/index.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

# Everything generated: build/, any page written next to the sources (all
# .html but index.html), the scripts, and the binaries ady2nim
# leaves beside each .ady.
clean:
	rm -rf build *.js $(filter-out index.html,$(wildcard *.html)) \
	    $(basename $(wildcard *.ady))
