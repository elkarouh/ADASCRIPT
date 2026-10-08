# TOOLS/ACCOUNTING: a tool to learn accounting with, after Martin Kleppmann's
# "Accounting for Computer Scientists". Needs karax >= 1.5.0 for the pages
# (nimble install karax@1.5.0) and db_connector for the ledger
# (nimble install db_connector).
#
#   make ledger     build the ledger program (./ledger -h)
#   make example    a database, accounting.db, holding the example company's year
#   make gui        the example as a web page            (accounting_gui.ady)
#   make live       the same page, its nodes dragged with the mouse (accounting_live.ady)
#   make test       the model and the ledger, no GUI (Nim only)
#   make all        build the program and both pages, open none
#
# $(OPEN) is xdg-open, or open on a Mac; `make gui OPEN=firefox` picks one.

# This checkout's own transpiler, so that its STDLIB (the db module the ledger
# imports) is the one used, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8802

.PHONY: all ledger example gui live test clean

all: ledger build/accounting_gui.html build/accounting_live.js

ledger: ledger.ady accounting_model.ady
	@echo "building ledger"
	@$(ADY2NIM) c ledger.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

# A fresh database each time: the example goes in an empty one.
example: ledger
	rm -f accounting.db
	./ledger example
	./ledger show

build/accounting_gui.html: accounting_gui.ady accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/accounting_gui.log \
	    || { cat build/accounting_gui.log; rm -f $@; exit 1; }

build/accounting_live.js: accounting_live.ady accounting_gui.ady accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/accounting_live.log 2>&1 || { cat build/accounting_live.log; exit 1; }
	@cp -L accounting_live.js $@ && rm -f accounting_live.js
	@cp live.html build/

gui: build/accounting_gui.html
	$(OPEN) $(CURDIR)/$<

live: build/accounting_live.js
	@echo "serving http://127.0.0.1:$(PORT)/live.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/live.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

test:
	$(ADY2NIM) c -r test_accounting_model.ady 2>/dev/null
	$(ADY2NIM) c -r test_ledger.ady 2>/dev/null

clean:
	rm -rf build *.js accounting.db $(basename $(wildcard *.ady))
