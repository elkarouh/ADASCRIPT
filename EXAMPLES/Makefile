# EXAMPLES: the programs in this directory.
#
#   make all      compile each top-level .ady (compile only, nothing is run)
#   make clean    remove what ady2nim left beside the sources, and clean
#                 the subdirectories that have a Makefile of their own
#
# The subdirectories build themselves (make -C HTML app, ...); the root
# Makefile's `make test` is what runs the examples and checks their output.

# This checkout's own transpiler, whatever ady2nim is first on PATH.
PYTHON  ?= $(shell command -v python3.12 2>/dev/null || command -v python3.14 || command -v python3)
ADY2NIM ?= $(PYTHON) $(abspath $(CURDIR)/../TO_NIM/ady2nim.py)

SOURCES := $(wildcard *.ady)
SUBDIRS := $(patsubst %/Makefile,%,$(wildcard */Makefile))

.PHONY: all clean

all:
	@for f in $(SOURCES); do \
	    echo "building $$f"; \
	    $(ADY2NIM) c $$f > build.log 2>&1 || { cat build.log; rm -f build.log; exit 1; }; \
	done; rm -f build.log

# ady2nim leaves a symlink to the built binary next to each source (the
# binary itself is in its cache), and a .nim beside it. Only symlinks and
# generated files go; a program that is not built from a .ady stays.
clean:
	@echo "Removing binary symlinks and generated files from EXAMPLES/..."
	@for f in $(SOURCES); do \
	    name=$${f%.ady}; \
	    if [ -L $$name ]; then rm -f $$name; fi; \
	    rm -f $$name.nim; \
	done
	@for d in $(SUBDIRS); do $(MAKE) --no-print-directory -C $$d clean; done
	@echo "Done."
