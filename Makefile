# ADASCRIPT/Makefile — build and test all examples
# -------------------------------------------------------
# Usage:
#   make compile    transpile + compile every example (no run)
#   make test       compile then run the full test suite
#   make clean      remove cached build artefacts and binary symlinks
#
# Requirements: see requirements.txt
# -------------------------------------------------------

PYTHON := python3.12
PY2NIM := $(PYTHON) $(CURDIR)/TO_NIM/py2nim.py
EXDIR  := $(CURDIR)/EXAMPLES

# Prepend choosenim's bin dir so Nim 2.x is used instead of any system Nim 1.x.
export PATH := /root/.nimble/bin:$(PATH)

.PHONY: test compile clean

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
    primes.ady

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
    spell.ady

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
# Skipped at runtime (compiled only):
#   tsp.ady         — matplotlib not installed by default (pyimport)
#   lv.ady          — requires clv shell utility
#   lolcate/lolcate.ady — integration test (requires fd + rg)
# -----------------------------------------------------------------------
COMPILE_ONLY := \
    tsp.ady \
    lv.ady \
    lolcate/lolcate.ady

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

	@echo ""
	@echo "All tests passed."

# -----------------------------------------------------------------------
# clean — remove caches and binary symlinks produced by py2nim
# -----------------------------------------------------------------------
clean:
	@echo "Removing build cache..."
	@rm -rf /root/.cache/hparsec/
	@echo "Removing binary symlinks from EXAMPLES/..."
	@for f in $(ALL_COMPILE); do \
	    name=$${f%.ady}; \
	    rm -f $(EXDIR)/$$name; \
	done
	@echo "Done."
