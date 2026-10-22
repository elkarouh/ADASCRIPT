# BROWSER_EXAMPLES/HTML: pages written with html: blocks. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make card       one widget, drawn as SVG, no server      (html_card.ady)
#   make app        a page as a tree of widgets, served      (html_app.ady)
#   make all        build every page into build/, open none
#
# The worked web apps are elsewhere: BROWSER_EXAMPLES/ACCOUNTING (Kleppmann's accounting,
# which started here) and BROWSER_EXAMPLES/DIJKSTRA_HTMX, both drawn on the server and
# kept up to date by htmx.
#
# `card` builds its SVG into build/ and opens the file in the browser; `app`
# builds a script and serves it. $(OPEN) is the program that opens a page:
# xdg-open, or open on a Mac; `make card OPEN=firefox` picks one.

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
PORT    ?= 8801
# On WSL, PowerShell's Start-Process opens the default browser, given a file: URL.
WINPATH  = $(if $(findstring powershell.exe,$(OPEN)),$(shell echo file:$$(wslpath -m $(1))),$(1))

PAGES := html_card

.PHONY: all card app clean

all: $(PAGES:%=build/%.svg) build/html_app.js

# A page is the program's output. Its compile messages go to a log, shown
# only when the build fails.
build/%.svg: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/$*.log \
	    || { cat build/$*.log; rm -f $@; exit 1; }

card:    build/html_card.svg
	-$(OPEN) "$(call WINPATH,$(CURDIR)/$<)"

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
