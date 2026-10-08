# EXAMPLES/HTML: pages written with html: blocks. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make objects    the accounting page of Kleppmann's article (accounting_objects.ady)
#   make card       one widget                               (html_card.ady)
#   make app        a page as a tree of widgets              (html_app.ady)
#   make counter    a counter in the browser, with events    (html_counter.ady)
#   make test       the accounting model on its own, no GUI (Nim only)
#   make all        build every page into build/, open none
#
# Each target builds its page into build/ and opens it in the browser:
# $(OPEN) is xdg-open, or open on a Mac; `make objects OPEN=firefox` picks one.

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8801

PAGES := html_card html_app accounting_objects

.PHONY: all objects card app counter test clean

all: $(PAGES:%=build/%.html) build/html_counter.js

# A page is the program's output. Its compile messages go to a log, shown
# only when the build fails.
build/%.html: %.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/$*.log \
	    || { cat build/$*.log; rm -f $@; exit 1; }

objects: build/accounting_objects.html
	$(OPEN) $(CURDIR)/$<
card:    build/html_card.html
	$(OPEN) $(CURDIR)/$<
app:     build/html_app.html
	$(OPEN) $(CURDIR)/$<

# The counter needs a page that loads its script, and a server for it.
build/html_counter.js: html_counter.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js html_counter.ady > build/html_counter.log 2>&1 \
	    || { cat build/html_counter.log; exit 1; }
	@cp -L html_counter.js $@ && rm -f html_counter.js
	@cp index.html build/index.html

counter: build/html_counter.js
	@echo "serving http://127.0.0.1:$(PORT)/index.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/index.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

# accounting_model.ady has no GUI in it, so it is tested without karax. Nim
# only: its Dollars_T is a scaled unit, which ady2py does not build.
test:
	$(ADY2NIM) c -r test_accounting_model.ady 2>/dev/null

# Everything generated: build/, any page written next to the sources (all
# .html but index.html), the counter's script, and the binaries ady2nim
# leaves beside each .ady.
clean:
	rm -rf build html_counter.js $(filter-out index.html,$(wildcard *.html)) \
	    $(basename $(wildcard *.ady))
