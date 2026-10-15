# Build and test ada_indent.
#
#   make          build bin/ada_indent
#   make test     the table cases and fixtures (tests/run_tests.py), then the
#                 metamorphic check (tools/metamorphic_check.py)
#   make test-lsp the language server's tests (needs pygls and lsprotocol)
#   make clean
#
# Needs GNAT and gprbuild, run through the `g` wrapper (g gprbuild, g gprclean).
# Without it: make GPRBUILD=gprbuild GPRCLEAN=gprclean

GPRBUILD ?= g gprbuild
GPRCLEAN ?= g gprclean
BIN      := bin/ada_indent
PYTHON   ?= python3

.PHONY: all test test-lsp clean
all: $(BIN)

$(BIN): $(wildcard src/*.ad[sb]) ada_indent.gpr
	$(GPRBUILD) -q -P ada_indent.gpr

test: $(BIN)
	$(PYTHON) tests/run_tests.py --bin $(CURDIR)/$(BIN)
	$(PYTHON) tools/metamorphic_check.py --bin $(CURDIR)/$(BIN)

test-lsp: $(BIN)
	$(PYTHON) lsp/test_lsp.py     # needs: pip install pygls lsprotocol

clean:
	$(GPRCLEAN) -q -P ada_indent.gpr || true
	rm -rf obj bin
