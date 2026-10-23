# BROWSER_EXAMPLES/ACCOUNTING: an app to learn accounting with, after Martin Kleppmann's
# "Accounting for Computer Scientists". Needs karax >= 1.5.0 for the pages
# (nimble install karax@1.5.0) and db_connector for the ledger's GnuCash import
# (nimble install db_connector).
#
#   make app        the tool: the books drawn in the browser, kept by clicking
#                   (server draws the page, backend/accounting_page_gui.ady; each scenario,
#                   scenarios/NAME.books, is kept as it is changed in NAME.kept there)
#   make alone      the same with no server: build the scripts, then open frontend/index.html
#                   (the scenarios kept in the browser's storage)
#   make ledger     build the ledger's command line (backend/ledger -h, backend/ledger list)
#   make gui        the example as a static web page      (backend/accounting_gui.ady)
#   make test       the model and the ledger, no GUI (Nim only)
#   make all        build the programs and the pages, open none
#
# $(OPEN) is xdg-open, or open on a Mac; on WSL, PowerShell opens the Windows browser.
# `make gui OPEN=firefox` picks one.

# backend/   compiled to C: the ledger, the server, the page it draws
# frontend/  compiled to JavaScript: accounting_js_events.ady, and the vendored htmx.min.js
# shared/    compiled both ways: the routing of the arrows and the layout of the accounts, which accounting_js_events.ady redoes in the browser
# tests/     the tests (native)

# This checkout's own transpiler, so that its STDLIB (the db module the ledger
# imports) is the one used, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
# On WSL, PowerShell's Start-Process opens the default browser, given a file: URL.
WINPATH  = $(if $(findstring powershell.exe,$(OPEN)),$(shell echo file:$$(wslpath -m $(1))),$(1))
PORT    ?= 8802

.PHONY: all app alone ledger server gui test clean

all: ledger server build/accounting_gui.html build/accounting_js_events.js build/htmx.min.js

# ady2nim keeps its own cache and rebuilds only what changed, so these always run it.
ledger:
	@echo "building backend/ledger"
	@$(ADY2NIM) c backend/ledger.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

server:
	@echo "building backend/server"
	@$(ADY2NIM) c backend/server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

build/accounting_gui.html: backend/accounting_gui.ady shared/routes.ady backend/accounting_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r $< > $@ 2> build/accounting_gui.log \
	    || { cat build/accounting_gui.log; rm -f $@; exit 1; }

build/accounting_js_events.js: frontend/accounting_js_events.ady shared/routes.ady shared/layout.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js $< > build/drag.log 2>&1 || { cat build/drag.log; exit 1; }
	@cp -L frontend/accounting_js_events.js $@ && rm -f frontend/accounting_js_events.js

# frontend/htmx.min.js is vendored (in git); if it was deleted, it is restored from git.
frontend/htmx.min.js:
	git checkout -- frontend/htmx.min.js

build/htmx.min.js: frontend/htmx.min.js
	@mkdir -p build
	@cp frontend/htmx.min.js $@

# The scenarios and the config, as texts the page alone carries (it has no files to read).
frontend/shipped.ady: generators/ship_scenarios.py accounting.conf $(wildcard scenarios/*.books)
	@echo "building $@"
	@$(PYTHON) generators/ship_scenarios.py $@

# The server, in the page (frontend/frontend_server.ady): frontend/index.html loads it, and it writes
# the page, which loads the others. Nothing to start: the page opens from the file.
frontend/frontend_server.js: frontend/frontend_server.ady frontend/shipped.ady $(wildcard backend/*.ady shared/*.ady)
	@echo "building $@"
	@$(ADY2NIM) js frontend/frontend_server.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

frontend/accounting_js_events.js: build/accounting_js_events.js
	@cp $< $@

alone: frontend/frontend_server.js frontend/accounting_js_events.js
	$(OPEN) "$(call WINPATH,$(CURDIR)/frontend/index.html)"

gui: build/accounting_gui.html
	$(OPEN) "$(call WINPATH,$(CURDIR)/$<)"

app: server build/accounting_js_events.js build/htmx.min.js
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/) &
	./backend/server --port $(PORT)

test:
	$(ADY2NIM) c -r tests/test_accounting_model.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_ledger.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_gnucash.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_beancount.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_journal.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_erp.ady 2>/dev/null
	$(ADY2NIM) c -r tests/test_htmx.ady 2>/dev/null

clean:
	rm -rf build scenarios/*.db scenarios/*.kept frontend/shipped.ady frontend/frontend_server.js $(foreach d,backend shared frontend tests,$(basename $(wildcard $(d)/*.ady)))
	rm -f frontend/accounting_js_events.js              # frontend/htmx.min.js is not built here, and stays
