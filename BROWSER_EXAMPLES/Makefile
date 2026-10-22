# BROWSER_EXAMPLES: the programs whose page runs in a browser. Each is a script built by
# `ady2nim js`, most with a page the program draws; they need karax >= 1.5.0
# (nimble install karax@1.5.0). The rest of the examples are in ../EXAMPLES.
#
#   make clean    clean each subdirectory, which has a Makefile of its own
#
# Each subdirectory builds itself: make -C HTML app, make -C SVG_NODE_EDITOR app, ...
# The root Makefile's `make test` is what checks them.

SUBDIRS := $(patsubst %/Makefile,%,$(wildcard */Makefile))

.PHONY: clean

clean:
	@for d in $(SUBDIRS); do $(MAKE) --no-print-directory -C $$d clean; done
