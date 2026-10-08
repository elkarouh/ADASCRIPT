# EXAMPLES/HTML: pages written with html: blocks. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make gui        the accounting page of Kleppmann's article (accounting_gui.ady)
#   make live       the same page, its graph's nodes dragged with the mouse (accounting_live.ady)
#   make card       one widget                               (html_card.ady)
#   make app        a page as a tree of widgets              (html_app.ady)
#   make counter    a counter in the browser, with events    (html_counter.ady)
#   make test       the accounting model on its own, no GUI (Nim only)
#   make all        build every page into build/, open none
#
# Each target builds its page into build/ and opens it in the browser:
# $(OPEN) is xdg-open, or open on a Mac; `make gui OPEN=firefox` picks one.

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8801

PAGES := html_card html_app accounting_gui

.PHONY: all gui live card app counter test clean

all: $(PAGES:%=build/%.html) build/html_counter.js build/accounting_live.js

# A page is the program's output. Its compile messages go to a log, shown
# only when the build fails.
build/%.html: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/$*.log \
	    || { cat build/$*.log; rm -f $@; exit 1; }

# The accounting pages are built from the model and, for the live one, from
# accounting_gui.ady too: a change to either rebuilds them.
build/accounting_gui.html: accounting_model.ady
build/accounting_live.js:  accounting_model.ady accounting_gui.ady

gui:     build/accounting_gui.html
	$(OPEN) $(CURDIR)/$<
card:    build/html_card.html
	$(OPEN) $(CURDIR)/$<
app:     build/html_app.html
	$(OPEN) $(CURDIR)/$<

# A page with events is a script, built by `ady2nim js`, and a page that
# loads it (index.html for the counter, live.html for the accounts), served.
build/%.js: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/$*.log 2>&1 || { cat build/$*.log; exit 1; }
	@cp -L $*.js $@ && rm -f $*.js
	@cp index.html live.html build/

counter: build/html_counter.js
	@echo "serving http://127.0.0.1:$(PORT)/index.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/index.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

live: build/accounting_live.js
	@echo "serving http://127.0.0.1:$(PORT)/live.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/live.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

# accounting_model.ady has no GUI in it, so it is tested without karax. Nim
# only: its Dollars_T is a scaled unit, which ady2py does not build.
test:
	$(ADY2NIM) c -r test_accounting_model.ady 2>/dev/null

# Everything generated: build/, any page written next to the sources (all
# .html but index.html and live.html), the scripts, and the binaries ady2nim
# leaves beside each .ady.
clean:
	rm -rf build *.js $(filter-out index.html live.html,$(wildcard *.html)) \
	    $(basename $(wildcard *.ady))
