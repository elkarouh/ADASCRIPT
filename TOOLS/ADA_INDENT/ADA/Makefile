# Build and test ada_indent.
#
#   make          build bin/ada_indent
#   make test     the table cases and fixtures (tests/run_tests.py), then the
#                 metamorphic check (tools/metamorphic_check.py)
#   make lsp      start the language server proxy on stdin/stdout (LSP_ARGS=... for options)
#   make test-lsp the language server proxy's tests
#   make clean
#
# Needs GNAT and gprbuild, run through the `g` wrapper (g gprbuild, g gprclean).
# Without it: make GPRBUILD=gprbuild GPRCLEAN=gprclean

GPRBUILD ?= g gprbuild
GPRCLEAN ?= g gprclean
BIN      := bin/ada_indent
PYTHON   ?= python3

.PHONY: all test lsp test-lsp clean
all: $(BIN)

$(BIN): $(wildcard src/*.ad[sb]) ada_indent.gpr
	$(GPRBUILD) -q -P ada_indent.gpr

test: $(BIN)
	$(PYTHON) tests/run_tests.py --bin $(CURDIR)/$(BIN)
	$(PYTHON) tools/metamorphic_check.py --bin $(CURDIR)/$(BIN)

LSP_ARGS ?=

lsp: $(BIN)
	@$(PYTHON) lsp/ada_indent_proxy.py --ada-indent $(CURDIR)/$(BIN) $(LSP_ARGS)

test-lsp: $(BIN)
	$(PYTHON) lsp/test_proxy.py

clean:
	$(GPRCLEAN) -q -P ada_indent.gpr || true
	rm -rf obj bin
