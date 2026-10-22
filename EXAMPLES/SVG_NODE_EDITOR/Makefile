# EXAMPLES/SVG_NODE_EDITOR: a node editor drawn as SVG, in the browser. Needs karax >= 1.5.0
# (nimble install karax@1.5.0).
#
#   make app      build the page and the script, serve them, open the page
#   make all      build build/index.html and build/node_editor.js, open none
#   make clean    remove what was built
#
# $(OPEN) is the program that opens a page: xdg-open, or open on a Mac;
# `make app OPEN=firefox` picks one.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../../TO_NIM/ady2nim.py)
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
PORT    ?= 8802

.PHONY: all app clean

all: build/index.html build/node_editor.js

# The page is the output of node_page, run.
build/index.html: node_page.ady node_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) c -r node_page.ady > $@ 2> build/page.log || { cat build/page.log; rm -f $@; exit 1; }

# The script is Adascript compiled to JavaScript.
build/node_editor.js: node_editor.ady node_model.ady
	@mkdir -p build
	@echo "building $@"
	@$(ADY2NIM) js node_editor.ady > build/script.log 2>&1 || { cat build/script.log; exit 1; }
	@cp -L node_editor.js $@ && rm -f node_editor.js

app: all
	@echo "serving http://127.0.0.1:$(PORT)/index.html (Ctrl-C to stop)"
	@(sleep 1; $(OPEN) http://127.0.0.1:$(PORT)/index.html) &
	cd build && python3 -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -rf build node_page node_model *.js
