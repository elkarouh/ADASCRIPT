# ADASCRIPT/Makefile — build and test all examples
# -------------------------------------------------------
# Usage:
#   make compile    transpile + compile every example (no run)
#   make test       compile then run the full test suite
#   make clean      remove cached build artefacts and binary symlinks
#
# Requirements: see requirements.txt
# -------------------------------------------------------

PYTHON := $(shell command -v python3.12 2>/dev/null || command -v python3.14)
export PYTHONPATH := $(HOME)/Downloads/hparsec:$(PYTHONPATH)
PY2NIM := $(PYTHON) $(CURDIR)/TO_NIM/py2nim.py
EXDIR  := $(CURDIR)/EXAMPLES
AIDIR  := $(CURDIR)/ADA_INDENT

# Prepend choosenim's bin dir so Nim 2.x is used instead of any system Nim 1.x.
export PATH := /root/.nimble/bin:$(HOME)/.nimble/bin:$(HOME)/Downloads:$(PATH)

.PHONY: test compile clean install uninstall

# Where 'make install' puts the py2nim / py2py launchers.
# Override with: make install PREFIX=$HOME/.local
PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

# -----------------------------------------------------------------------
# Libraries — no main block; compile only, never run
# -----------------------------------------------------------------------
LIBS := \
    state_search.ady \
    shortest_path.ady \
    timetable_engine.ady

# -----------------------------------------------------------------------
# Self-contained — no stdin, no mandatory args
# -----------------------------------------------------------------------
STANDALONE := \
    monty_hall.ady \
    sudoku.ady \
    prisoners.ady \
    graph.ady \
    floyd.ady \
    dijkstra.ady \
    geo_server.ady \
    openarray_demo.ady \
    test_inline_suite.ady \
    test_state_search.ady \
    test_shortest_path.ady \
    primes.ady \
    test_ownership.ady \
    test_iters.ady \
    test_regex.ady \
    td_learning/sarsa.ady \
    td_learning/qlearning.ady \
    test_do_block.ady

# -----------------------------------------------------------------------
# Stdin tests — piped from a sample file
# -----------------------------------------------------------------------
STDIN_EXAMPLES := \
    awk_example.ady \
    test_awk.ady \
    average_line.ady

# -----------------------------------------------------------------------
# Arg tests — run with explicit arguments
# -----------------------------------------------------------------------
ARG_EXAMPLES := \
    argparse.ady \
    phonecode.ady \
    spell.ady \
    git1.ady

# -----------------------------------------------------------------------
# Expect tests — require bc to be installed
# -----------------------------------------------------------------------
EXPECT_EXAMPLES := \
    test_expect.ady \
    test_shell_block.ady

# -----------------------------------------------------------------------
# Timetable tests — require db_connector (nimble) + a populated SQLite DB
# -----------------------------------------------------------------------
TIMETABLE_EXAMPLES := \
    timetable_backtrack.ady \
    timetable_sa.ady

# -----------------------------------------------------------------------
# ADA_INDENT unit tests — self-checking runners in ADA_INDENT/ (assert +
# print "all ... passed"). Transpiled, compiled and run with py2nim -r.
# -----------------------------------------------------------------------
ADA_INDENT_TESTS := \
    test_ada_lexer.ady \
    test_ada_line_fmt.ady \
    test_ada_indent.ady

# -----------------------------------------------------------------------
# Skipped at runtime (compiled only):
#   tsp.ady         — matplotlib not installed by default (pyimport)
#   lv.ady          — requires clv shell utility
#   lolcate/lolcate.ady — integration test (requires fd + rg)
# -----------------------------------------------------------------------
COMPILE_ONLY := \
    tsp.ady \
    lv.ady \
    lolcate/lolcate.ady \
    dp/jacks.ady

ALL_COMPILE := \
    $(LIBS) \
    $(STANDALONE) \
    $(STDIN_EXAMPLES) \
    $(ARG_EXAMPLES) \
    $(EXPECT_EXAMPLES) \
    $(TIMETABLE_EXAMPLES) \
    $(COMPILE_ONLY)

# -----------------------------------------------------------------------
# _compile_one — internal helper: compile a single file, print OK/FAIL.
# On failure, re-run and show the error lines, then abort.
# -----------------------------------------------------------------------
define compile_one
	printf '  %-42s' "$(1)"; \
	if $(PY2NIM) c $(EXDIR)/$(1) >/dev/null 2>&1; then \
	    echo OK; \
	else \
	    echo FAIL; \
	    $(PY2NIM) c $(EXDIR)/$(1) 2>&1 | grep -E 'Error:' | head -5; \
	    exit 1; \
	fi
endef

# -----------------------------------------------------------------------
# compile — transpile + build everything
# -----------------------------------------------------------------------
compile:
	@echo "=== Compiling $(words $(ALL_COMPILE)) examples ==="
	@$(foreach f,$(ALL_COMPILE),$(call compile_one,$(f));)
	@echo "=== Compile step complete ==="

# -----------------------------------------------------------------------
# test — compile everything, then run the runnable subset
# -----------------------------------------------------------------------
test: compile
	@echo ""

	@echo "=== Self-contained examples ==="
	@for f in $(STANDALONE); do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo "=== Stdin examples (piped from test_awk_sample.txt) ==="
	@for f in $(STDIN_EXAMPLES); do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name < $(EXDIR)/test_awk_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo "=== Arg examples ==="
	@printf '  %-42s' "phonecode.ady (test_words.txt test_phones.txt)"; \
	    $(EXDIR)/phonecode $(EXDIR)/test_words.txt $(EXDIR)/test_phones.txt \
	        >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "argparse.ady (test_words.txt)"; \
	    $(EXDIR)/argparse $(EXDIR)/test_words.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "spell.ady (big.txt speling)"; \
	    $(EXDIR)/spell $(EXDIR)/big.txt speling >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }
	@# git1 --version is the only invocation with no side effects: every other
	@# subcommand creates, moves or deletes a repo in the working directory.
	@printf '  %-42s' "git1.ady (--version)"; \
	    $(EXDIR)/git1 --version >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }

	@echo "=== Expect / shell examples (require bc) ==="
	@for f in $(EXPECT_EXAMPLES); do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo "=== Timetable examples (built-in default problem) ==="
	@for f in $(TIMETABLE_EXAMPLES); do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo "=== ADA_INDENT unit tests (transpile + compile + run) ==="
	@for f in $(ADA_INDENT_TESTS); do \
	    printf '  %-42s' "$$f"; \
	    $(PY2NIM) $(AIDIR)/$$f -r >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo ""
	@echo "All tests passed."

# -----------------------------------------------------------------------
# clean — remove caches and binary symlinks produced by py2nim
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# install — put 'py2nim' and 'py2py' on PATH
#
#   Clone the repo, run 'make install', and every .ady file with a
#   '#!/usr/bin/env py2nim' shebang becomes directly executable from any
#   directory.  The launchers are wrappers rather than symlinks so they can
#   pin the interpreter: the scripts' own shebang says python3, which on
#   many systems is older than the 3.12 the tokenizer needs.
# -----------------------------------------------------------------------
install:
	@echo "=== Installing Adascript from $(CURDIR) ==="
	@if [ -z "$(PYTHON)" ]; then \
	    echo "  error: no python3.12 or python3.14 found on PATH."; \
	    echo "         The transpiler needs Python >= 3.12 — its tokenizer uses"; \
	    echo "         FSTRING_START tokens, which older versions do not emit."; \
	    exit 1; \
	fi
	@echo "  python      $(PYTHON)"
	@if [ ! -f "$(CURDIR)/HPARSEC/hek_parsec.py" ]; then \
	    echo "  hparsec     submodule empty — fetching"; \
	    git -C "$(CURDIR)" submodule update --init HPARSEC || { \
	        echo "  error: could not fetch the HPARSEC submodule; it holds the"; \
	        echo "         parser engine and nothing works without it."; exit 1; }; \
	fi
	@echo "  hparsec     $(CURDIR)/HPARSEC"
	@set -e; \
	dir="$(BINDIR)"; \
	if ! mkdir -p "$$dir" 2>/dev/null || [ ! -w "$$dir" ]; then \
	    dir="$$HOME/.local/bin"; mkdir -p "$$dir"; \
	    echo "  note        $(BINDIR) is not writable — using $$dir"; \
	fi; \
	for tool in py2nim:TO_NIM py2py:TO_PYTHON; do \
	    name=$${tool%%:*}; sub=$${tool##*:}; \
	    printf '#!/bin/sh\n# Adascript launcher — generated by "make install" in %s\nexec %s %s/%s/%s.py "$$@"\n' \
	        "$(CURDIR)" "$(PYTHON)" "$(CURDIR)" "$$sub" "$$name" > "$$dir/$$name"; \
	    chmod +x "$$dir/$$name"; \
	    echo "  installed   $$dir/$$name"; \
	done; \
	case ":$$PATH:" in \
	    *":$$dir:"*) ;; \
	    *) echo ""; \
	       echo "  $$dir is not on your PATH. Add it, e.g.:"; \
	       echo "      echo 'export PATH=\"$$dir:\$$PATH\"' >> ~/.bashrc" ;; \
	esac; \
	echo ""; \
	echo "=== Verifying ==="; \
	tmp=$$(mktemp -d); \
	printf 'var x: int = 41\nprint x + 1\n' > "$$tmp/hello.ady"; \
	if [ "$$("$$dir/py2py" -c "$$tmp/hello.ady" 2>/dev/null | tail -1)" = "42" ]; then \
	    echo "  py2py       OK (transpiled and ran a test program)"; \
	else \
	    echo "  py2py       FAILED"; rm -rf "$$tmp"; exit 1; \
	fi; \
	rm -rf "$$tmp"; \
	if command -v nim >/dev/null 2>&1; then \
	    echo "  nim         $$(nim --version 2>/dev/null | head -1)"; \
	else \
	    echo "  nim         not found — the Nim backend (py2nim) needs it."; \
	    echo "              Install with choosenim: https://nim-lang.org/install.html"; \
	fi
	@echo ""
	@echo "Done. Optional extras, needed only by some examples:"
	@echo "  nimble install nimpy db_connector   # pyimport bridge, SQLite"
	@echo "  apt install bc libpcre3             # expect tests, regex runtime"
	@echo "  see requirements.txt for the full list"

uninstall:
	@set -e; \
	for dir in "$(BINDIR)" "$$HOME/.local/bin"; do \
	    for name in py2nim py2py; do \
	        if [ -e "$$dir/$$name" ]; then \
	            rm -f "$$dir/$$name"; echo "  removed $$dir/$$name"; \
	        fi; \
	    done; \
	done; \
	echo "Done."

clean:
	@echo "Removing build cache..."
	@# $$HOME, not $HOME: make would read that as $(H) followed by OME and
	@# delete a stray ./OME directory, leaving the real cache in place.
	@rm -rf $$HOME/.cache/hparsec/
	@echo "Removing binary symlinks from EXAMPLES/..."
	@for f in $(ALL_COMPILE); do \
	    name=$${f%.ady}; \
	    rm -f $(EXDIR)/$$name; \
	done
	@echo "Done."
