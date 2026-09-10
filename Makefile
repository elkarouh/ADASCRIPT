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
ADY2NIM := $(PYTHON) $(CURDIR)/TO_NIM/ady2nim.py
EXDIR  := $(CURDIR)/EXAMPLES
AIDIR  := $(CURDIR)/ADA_INDENT

# Prepend choosenim's bin dir so Nim 2.x is used instead of any system Nim 1.x.
export PATH := /root/.nimble/bin:$(HOME)/.nimble/bin:$(HOME)/Downloads:$(PATH)

.PHONY: test compile clean install uninstall

# Where 'make install' puts the ady2nim / ady2py launchers.
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
    test_graphs.ady \
    test_queues.ady \
    test_regex.ady \
    test_regex_g.ady \
    test_env_default.ady \
    test_env_optional.ady \
    test_optional_truthy.ady \
    test_self_ref.ady \
    test_char_slice.ady \
    td_learning/sarsa.ady \
    td_learning/qlearning.ady \
    PROJECT/dispatch.ady \
    PROJECT/test_geometry.ady \
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
# CFMU — the build-status monitor, fed its own sample of tacot_corico output
# -----------------------------------------------------------------------
CFMU_EXAMPLES := \
    CFMU/Tstatus_monitor.ady \
    CFMU/Vcheck_coded_flight.ady

# -----------------------------------------------------------------------
# ADA_INDENT unit tests — self-checking runners in ADA_INDENT/ (assert +
# print "all ... passed"). Transpiled, compiled and run with ady2nim -r.
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
    dp/jacks.ady \
    INTERACTIVE/lispy.ady

ALL_COMPILE := \
    $(LIBS) \
    $(STANDALONE) \
    $(STDIN_EXAMPLES) \
    $(CFMU_EXAMPLES) \
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
	if $(ADY2NIM) c $(EXDIR)/$(1) >/dev/null 2>&1; then \
	    echo OK; \
	else \
	    echo FAIL; \
	    $(ADY2NIM) c $(EXDIR)/$(1) 2>&1 | grep -E 'Error:' | head -5; \
	    exit 1; \
	fi
endef

# -----------------------------------------------------------------------
# compile — transpile + build everything
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# lint-emitters — no grammar rule may be registered twice in one backend.
#
# @method(X) is a setattr, so a second registration of the same rule silently
# overwrites the first and the earlier definition becomes unreachable. That
# is not hypothetical: try_except carried two copies for long enough that the
# dead one predated inline header comments in a try body, and a reader coming
# down the file met the stale one first. Six such pairs were found at once,
# four of them already drifted apart.
#
# This catches only the shadowed kind. A rule registered on a class no node is
# ever built from -- simple_stmt, being a choice that hands back its child --
# is invisible here and shows up only as an emitter that never fires.
# -----------------------------------------------------------------------
.PHONY: lint-emitters
lint-emitters:
	@echo "=== No grammar rule is registered twice ==="
	@for d in TO_NIM TO_PYTHON; do \
	    printf '  %-42s' "$$d/*.py"; \
	    dups=$$(grep -h '^@method(' $(CURDIR)/$$d/*.py \
	            | sed 's/^@method(\(.*\))$$/\1/' | sort | uniq -d); \
	    if [ -n "$$dups" ]; then \
	        echo FAIL; \
	        echo "  registered more than once -- the later one wins, the rest are dead:"; \
	        for r in $$dups; do \
	            echo "    $$r"; \
	            grep -ln "^@method($$r)" $(CURDIR)/$$d/*.py | sed 's/^/      /'; \
	        done; \
	        exit 1; \
	    fi; \
	    echo OK; \
	done

compile: lint-emitters
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

	@echo "=== CFMU examples (fed their own samples) ==="
	@printf '  %-42s' "CFMU/Tstatus_monitor.ady"; \
	    $(EXDIR)/CFMU/Tstatus_monitor < $(EXDIR)/CFMU/tstatus_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }
	@# Vcheck takes a log file rather than stdin; a path that exists is used
	@# as-is, which is what makes it runnable here.
	@printf '  %-42s' "CFMU/Vcheck_coded_flight.ady"; \
	    $(EXDIR)/CFMU/Vcheck_coded_flight $(EXDIR)/CFMU/vcheck_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }

	@# lispy checks itself before it offers a prompt, so an empty stdin runs
	@# the whole suite and then leaves at EOF. It went unbuilt for a long
	@# while without anyone noticing, which is the argument for it being here.
	@printf '  %-42s' "INTERACTIVE/lispy.ady (self-test)"; \
	    $(EXDIR)/INTERACTIVE/lispy < /dev/null 2>&1 \
	        | grep -q "lispy: all tests passed" && echo OK || { echo FAIL; exit 1; }

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
	@# The output is checked, not just the exit status. A suite that never
	@# runs exits 0 too: ada_indent.ady once lost its `__main__` guard, so
	@# importing it ran main(), which read the empty stdin and quit(0) before
	@# a single test started -- and this step said OK for all 52 of them.
	@for f in $(ADA_INDENT_TESTS); do \
	    printf '  %-42s' "$$f"; \
	    out=$$($(ADY2NIM) $(AIDIR)/$$f -r 2>&1); rc=$$?; \
	    if [ $$rc -eq 0 ] \
	       && printf '%s' "$$out" | grep -q 'passed' \
	       && ! printf '%s' "$$out" | grep -qE '[1-9][0-9]* failed'; then \
	        echo OK; \
	    else \
	        echo FAIL; printf '%s\n' "$$out" | tail -20; exit 1; \
	    fi; \
	done

	@# test_env_default.ady and test_env_optional.ady pass standalone, but
	@# the cases that give each its point -- `:-` rather than plain `-`,
	@# and presence rather than truthiness -- need a variable that is *set*
	@# and empty, and Adascript can read the environment but not write it.
	@echo "=== Env default (set-but-empty case) ==="
	@printf '  %-42s' "test_env_default.ady (ADY_TEST_EMPTY=)"; \
	    ADY_TEST_EMPTY= $(EXDIR)/test_env_default >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "test_env_optional.ady (ADY_TEST_EMPTY=)"; \
	    ADY_TEST_EMPTY= $(EXDIR)/test_env_optional >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }

	@# -t has to resolve nimport'd dependencies, not just translate the one
	@# file: it writes to the very path a later build reads, so a .nim
	@# emitted without the imported module's declarations poisons the cache.
	@# test_awk.ady is the case -- its class inherits its constructor from
	@# awk.ady -- and the check is that a build straight after a -t works.
	@# A throwaway XDG_CACHE_HOME gives it a cache of its own, so the check
	@# starts cold and leaves the real cache alone either way.  Not a
	@# throwaway HOME: that moves the Nim toolchain out of reach too, and a
	@# choosenim install -- the one the docs recommend -- then cannot compile
	@# anything, so the step failed for a reason that had nothing to do with
	@# the transpiler.
	@echo "=== Transpile-only, then build (ady2nim -t) ==="
	@printf '  %-42s' "test_awk.ady (-t then -r)"; \
	    tmp=$$(mktemp -d); \
	    XDG_CACHE_HOME=$$tmp $(ADY2NIM) -t $(EXDIR)/test_awk.ady >/dev/null 2>&1 \
	      && XDG_CACHE_HOME=$$tmp $(ADY2NIM) $(EXDIR)/test_awk.ady -r </dev/null >/dev/null 2>&1 \
	      && { echo OK; rm -rf $$tmp; } \
	      || { echo FAIL; rm -rf $$tmp; exit 1; }

	@# The one js-backend module. It is a library, not a program, so the
	@# check is that `nim js` accepts it -- nothing else in this target
	@# exercises the js path, and a dict literal is emitted differently
	@# there (js{...} rather than {...}.toTable), so a native-only run
	@# would not have caught a break.
	@echo "=== JS backend (compile only) ==="
	@printf '  %-42s' "STDLIB/jointjs.ady (ady2nim js)"; \
	    $(ADY2NIM) js $(CURDIR)/TO_NIM/STDLIB/jointjs.ady >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }

	@echo ""
	@echo "All tests passed."

# -----------------------------------------------------------------------
# clean — remove caches and binary symlinks produced by ady2nim
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# install — put 'ady2nim' and 'ady2py' on PATH
#
#   Clone the repo, run 'make install', and every .ady file with a
#   '#!/usr/bin/env ady2nim' shebang becomes directly executable from any
#   directory.  The launchers are wrappers rather than symlinks so they can
#   pin the interpreter: the scripts' own shebang says python3, which on
#   many systems is older than the 3.12 the tokenizer needs.
#
#   The tools were called py2nim and py2py until the language outgrew the
#   name, and .ady files in the wild still carry that shebang, so both
#   legacy names are installed as aliases of the new ones.
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
	    echo "  error: HPARSEC/hek_parsec.py is missing from this checkout; it"; \
	    echo "         holds the parser engine and nothing works without it."; \
	    exit 1; \
	fi
	@echo "  hparsec     $(CURDIR)/HPARSEC"
	@set -e; \
	dir="$(BINDIR)"; \
	if ! mkdir -p "$$dir" 2>/dev/null || [ ! -w "$$dir" ]; then \
	    dir="$$HOME/.local/bin"; mkdir -p "$$dir"; \
	    echo "  note        $(BINDIR) is not writable — using $$dir"; \
	fi; \
	for tool in ady2nim:TO_NIM:py2nim ady2py:TO_PYTHON:py2py; do \
	    name=$${tool%%:*}; rest=$${tool#*:}; sub=$${rest%%:*}; legacy=$${tool##*:}; \
	    printf '#!/bin/sh\n# Adascript launcher — generated by "make install" in %s\nexec %s %s/%s/%s.py "$$@"\n' \
	        "$(CURDIR)" "$(PYTHON)" "$(CURDIR)" "$$sub" "$$name" > "$$dir/$$name"; \
	    chmod +x "$$dir/$$name"; \
	    echo "  installed   $$dir/$$name"; \
	    cp "$$dir/$$name" "$$dir/$$legacy"; \
	    chmod +x "$$dir/$$legacy"; \
	    echo "  installed   $$dir/$$legacy (alias for $$name)"; \
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
	if [ "$$("$$dir/ady2py" -c "$$tmp/hello.ady" 2>/dev/null | tail -1)" = "42" ]; then \
	    echo "  ady2py       OK (transpiled and ran a test program)"; \
	else \
	    echo "  ady2py       FAILED"; rm -rf "$$tmp"; exit 1; \
	fi; \
	rm -rf "$$tmp"; \
	if command -v nim >/dev/null 2>&1; then \
	    echo "  nim         $$(nim --version 2>/dev/null | head -1)"; \
	else \
	    echo "  nim         not found — the Nim backend (ady2nim) needs it."; \
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
	    for name in ady2nim ady2py py2nim py2py; do \
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
	@# The same place ady2nim writes to: XDG_CACHE_HOME when it is set,
	@# ~/.cache otherwise.
	@rm -rf $${XDG_CACHE_HOME:-$$HOME/.cache}/adascript/
	@# The cache lived under ~/.cache/hparsec until it was named after the
	@# language rather than the parser engine; sweep the old tree too, or it
	@# sits there for good holding artifacts nothing will ever read again.
	@rm -rf $${XDG_CACHE_HOME:-$$HOME/.cache}/hparsec/
	@echo "Removing binary symlinks from EXAMPLES/..."
	@for f in $(ALL_COMPILE); do \
	    name=$${f%.ady}; \
	    rm -f $(EXDIR)/$$name; \
	done
	@echo "Done."
