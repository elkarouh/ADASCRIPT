# Build and test the Ada translation of ada_indent.
#
#   make            build bin/ada_indent
#   make test       golden files come back unchanged (as they are, and with all
#                   leading whitespace stripped), then metamorphic_check.py
#   make compare    byte-for-byte against the Adascript build, REF=../ada_indent
#                   (stdout, stderr and --emit-state), over the same inputs
#   make clean
#
# Needs GNAT and gprbuild, run through the `g` wrapper (g gprbuild, g gprclean).
# Without it: make GPRBUILD=gprbuild GPRCLEAN=gprclean

GPRBUILD ?= g gprbuild
GPRCLEAN ?= g gprclean
BIN      := bin/ada_indent
REF      ?= ../ada_indent
PYTHON   ?= python3
FILES    := ../ada_indent_sample_test.adb $(wildcard ../regress/valid_*.adb)
ALL      := ../sample.adb $(FILES) $(wildcard ../regress/invalid_*.adb)

.PHONY: all test compare clean
all: $(BIN)

$(BIN): $(wildcard src/*.ad[sb]) ada_indent.gpr
	$(GPRBUILD) -q -P ada_indent.gpr

test: $(BIN)
	@fail=0; \
	for f in $(FILES); do \
	    $(BIN) -q $$f | cmp -s - $$f || { echo "FAIL (not a fixpoint): $$f"; fail=1; }; \
	    sed 's/^[[:space:]]*//' $$f | $(BIN) -q | cmp -s - $$f \
	        || { echo "FAIL (stripped copy): $$f"; fail=1; }; \
	done; \
	[ $$fail = 0 ] || exit 1; \
	echo "fixpoint: ok ($(words $(FILES)) files)"
	$(PYTHON) ../metamorphic_check.py --bin $(CURDIR)/$(BIN)

compare: $(BIN)
	@[ -x $(REF) ] || { echo "no reference build at $(REF): run  ady2nim ../ada_indent.ady"; exit 1; }
	@fail=0; \
	for f in $(ALL); do \
	    for opt in -q --emit-state; do \
	        $(REF) $$opt $$f > /tmp/ai_ref.out 2>&1; \
	        $(BIN) $$opt $$f > /tmp/ai_ada.out 2>&1; \
	        cmp -s /tmp/ai_ref.out /tmp/ai_ada.out || { echo "DIFF $$opt $$f"; fail=1; }; \
	    done; \
	done; \
	[ $$fail = 0 ] && echo "compare: identical ($(words $(ALL)) files)"

clean:
	$(GPRCLEAN) -q -P ada_indent.gpr || true
	rm -rf obj bin
