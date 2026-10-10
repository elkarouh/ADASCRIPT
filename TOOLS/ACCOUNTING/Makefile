# TOOLS/ACCOUNTING: a tool to learn accounting with, after Martin Kleppmann's
# "Accounting for Computer Scientists". Needs karax >= 1.5.0 for the pages
# (nimble install karax@1.5.0) and db_connector for the ledger
# (nimble install db_connector).
#
#   make app        the tool: the books drawn in the browser, kept by clicking
#                   (ledger_server serves accounting_app; each scenario,
#                   scenarios/NAME.books, gets a database NAME.db there)
#   make ledger     build the ledger's command line (./ledger -h, ./ledger list)
#   make gui        the example as a static web page      (accounting_gui.ady)
#   make test       the model and the ledger, no GUI (Nim only)
#   make all        build the programs and the pages, open none
#
# $(OPEN) is xdg-open, or open on a Mac; `make gui OPEN=firefox` picks one.

# This checkout's own transpiler, so that its STDLIB (the db module the ledger
# imports) is the one used, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8802

.PHONY: all app ledger ledger_server gui test clean

all: ledger ledger_server build/accounting_gui.html build/accounting_app.js

ledger: ledger.ady gnucash.ady beancount.ady journal.ady erp_csv.ady plain_books.ady books_text.ady accounting_model.ady
	@echo "building ledger"
	@$(ADY2NIM) c ledger.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

ledger_server: ledger_server.ady htmx_page.ady accounting_gui.ady ledger.ady gnucash.ady beancount.ady journal.ady erp_csv.ady plain_books.ady books_text.ady accounting_model.ady
	@echo "building ledger_server"
	@$(ADY2NIM) c ledger_server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

build/accounting_gui.html: accounting_gui.ady accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/accounting_gui.log \
	    || { cat build/accounting_gui.log; rm -f $@; exit 1; }

build/accounting_app.js: accounting_app.ady accounting_gui.ady books_text.ady accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/accounting_app.log 2>&1 || { cat build/accounting_app.log; exit 1; }
	@cp -L accounting_app.js $@ && rm -f accounting_app.js
	@cp app.html htmx.min.js build/

gui: build/accounting_gui.html
	$(OPEN) $(CURDIR)/$<

app: ledger_server build/accounting_app.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./ledger_server --port $(PORT)

test:
	$(ADY2NIM) c -r test_accounting_model.ady 2>/dev/null
	$(ADY2NIM) c -r test_ledger.ady 2>/dev/null
	$(ADY2NIM) c -r test_gnucash.ady 2>/dev/null
	$(ADY2NIM) c -r test_beancount.ady 2>/dev/null
	$(ADY2NIM) c -r test_journal.ady 2>/dev/null
	$(ADY2NIM) c -r test_erp.ady 2>/dev/null
	$(ADY2NIM) c -r test_htmx.ady 2>/dev/null

clean:
	rm -rf build *.js scenarios/*.db $(basename $(wildcard *.ady))
