# TOOLS/ACCOUNTING: a tool to learn accounting with, after Martin Kleppmann's
# "Accounting for Computer Scientists". Needs karax >= 1.5.0 for the pages
# (nimble install karax@1.5.0) and db_connector for the ledger
# (nimble install db_connector).
#
#   make app        the tool: the books drawn in the browser, kept by clicking
#                   (ledger_server draws the page, backend/htmx_page.ady; each scenario,
#                   scenarios/NAME.books, gets a database NAME.db there)
#   make ledger     build the ledger's command line (backend/ledger -h, backend/ledger list)
#   make gui        the example as a static web page      (backend/accounting_gui.ady)
#   make test       the model and the ledger, no GUI (Nim only)
#   make all        build the programs and the pages, open none
#
# $(OPEN) is xdg-open, or open on a Mac; `make gui OPEN=firefox` picks one.

# backend/   compiled to C: the ledger, the server, the page it draws
# frontend/  compiled to JavaScript: drag.ady, and the vendored htmx.min.js
# shared/    compiled both ways: the model, and the routing of the arrows, which drag.ady redoes in the browser
# tests/     the tests (native)

# This checkout's own transpiler, so that its STDLIB (the db module the ledger
# imports) is the one used, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)
PORT    ?= 8802

.PHONY: all app ledger ledger_server gui test clean

all: ledger ledger_server build/accounting_gui.html build/drag.js build/htmx.min.js

# ady2nim keeps its own cache and rebuilds only what changed, so these always run it.
ledger:
	@echo "building backend/ledger"
	@$(ADY2NIM) c backend/ledger.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

ledger_server:
	@echo "building backend/ledger_server"
	@$(ADY2NIM) c backend/ledger_server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

build/accounting_gui.html: backend/accounting_gui.ady shared/routes.ady shared/accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/accounting_gui.log \
	    || { cat build/accounting_gui.log; rm -f $@; exit 1; }

build/drag.js: frontend/drag.ady shared/routes.ady shared/accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/drag.log 2>&1 || { cat build/drag.log; exit 1; }
	@cp -L frontend/drag.js $@ && rm -f frontend/drag.js

# frontend/htmx.min.js is vendored (in git); if it was deleted, it is restored from git.
frontend/htmx.min.js:
	git checkout -- frontend/htmx.min.js

build/htmx.min.js: frontend/htmx.min.js
	@mkdir -p build
	@cp frontend/htmx.min.js $@

gui: build/accounting_gui.html
	$(OPEN) $(CURDIR)/$<

app: ledger_server build/drag.js build/htmx.min.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./backend/ledger_server --port $(PORT)

test:
	$(ADY2NIM) c -r tests/test_accounting_model.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_ledger.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_gnucash.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_beancount.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_journal.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_erp.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_htmx.ady 2>/dev/null

clean:
	rm -rf build scenarios/*.db $(foreach d,backend shared frontend tests,$(basename $(wildcard $(d)/*.ady)))
	rm -f frontend/drag.js              # frontend/htmx.min.js is not built here, and stays
