# BROWSER_EXAMPLES/SHOPPING_LIST: the app of DOCS/ADASCRIPT_FOR_JAVASCRIPT.md's tutorial.
#
#   make            build shopping_page.js; then open index.html in a browser (no server)
#   make test       check the model, natively, with no page
#   make open       build, and open index.html
#   make clean      remove what make built

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || echo true)

.PHONY: all test open clean

all: shopping_page.js

shopping_page.js: shopping_page.ady shopping_view.ady shopping_model.ady
	@echo "building $@"
	@$(ADY2NIM) js shopping_page.ady > build.log 2>&1 || { cat build.log; exit 1; }
	@rm -f build.log

test:
	$(ADY2NIM) c -r tests/test_shopping.ady 2>/dev/null

open: all
	$(OPEN) "$(CURDIR)/index.html"

clean:
	rm -f shopping_page.js build.log tests/test_shopping
