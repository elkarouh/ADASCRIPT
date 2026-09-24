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
TMPDIR ?= /tmp
TOOLDIR:= $(CURDIR)/TOOLS
AIDIR  := $(TOOLDIR)/ADA_INDENT
G1DIR  := $(TOOLDIR)/GIT1
PGDIR  := $(TOOLDIR)/PGREP
TBDIR  := $(TOOLDIR)/TBLAME
TDDIR  := $(TOOLDIR)/TDIFF
TCDIR  := $(TOOLDIR)/TCHECK

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
#
# pyimport_similar.ady is the one file in here that pyimports on purpose: it
# is the worked example for when the bridge is worth its cost, so it has to
# be exercised rather than described. It runs rather than compile-only
# because difflib ships with Python -- unlike tsp.ady below, which wants
# matplotlib and therefore only compiles. `make test` already requires
# nimpy; see README.md.
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
    ownership_tour.ady \
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
    pyimport_similar.ady \
    td_learning/sarsa.ady \
    td_learning/qlearning.ady \
    PROJECT/dispatch.ady \
    PROJECT/test_geometry.ady \
    test_do_block.ady \
    test_stmt_modifier.ady \
    test_str_join.ady \
    test_which.ady \
    test_shell_stdin_status.ady \
    test_strip_chars.ady \
    test_path_call.ady \
    test_shell_throughput.ady \
    test_shell_braces.ady \
    test_param_mutation.ady \
    test_fstring_replace_sugar.ady \
    test_char_default.ady \
    test_any_all.ady \
    test_option_guard_modifier.ady \
    test_init_calls_method.ady \
    test_enum_array_enumerate.ady \
    test_enum_array_zero_fill.ady \
    test_case_guard_or.ady \
    test_method_param_names.ady \
    test_pure_method_self.ady \
    test_class_name_prefix_field.ady \
    test_record_name_prefix_field.ady \
    test_file_test_access.ady \
    test_enumerate_start.ady \
    test_field_subscript_empty_dict.ady \
    test_die_warn_own.ady \
    test_subscript_call_target.ady \
    test_method_shell_field.ady \
    test_method_result_concat.ady \
    test_str_removeprefix.ady \
    test_shell_revision_braces.ady \
    test_exit_modifier.ady \
    test_regex_quote.ady \
    test_shell_backslash.ady \
    test_shell_keyword_target.ady \
    test_char_table_literal.ady

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
# CFMU — the build-status monitor, fed its own sample of tacot_corico output
# -----------------------------------------------------------------------
CFMU_EXAMPLES := \
    CFMU/Tstatus_monitor.ady \
    CFMU/Vcheck_coded_flight.ady

# The rest of CFMU/ drives lftp against a real FTPS server and queries an
# Oracle-backed configuration, so there is nothing to run here -- but there is
# something to compile. They were outside every list until now, which is how
# cfmu_get_file_type.ady came to sit in the repository not compiling at all:
# nothing ever asked it to. Compile-only is the whole coverage these can have,
# and it is enough to catch that.
CFMU_COMPILE_ONLY := \
    CFMU/cfmu_ftps_get_ft.ady \
    CFMU/cfmu_ftps_put_formatted.ady \
    CFMU/cfmu_ftps_recover.ady \
    CFMU/cfmu_get_file_type.ady \
    CFMU/cfmu_get_pattern_for_ftps.ady \
    CFMU/cfmu_list_ftp_server.ady \
    CFMU/ftps_common.ady \
    CFMU/ftps_delete.ady \
    CFMU/ftps_get.ady \
    CFMU/ftps_invalid_scan.ady \
    CFMU/ftps_list.ady \
    CFMU/ftps_mkslinks.ady \
    CFMU/ftps_mkslinks.locked.ady \
    CFMU/ftps_put.ady \
    CFMU/ftps_rename.ady

# -----------------------------------------------------------------------
# ADA_INDENT unit tests — self-checking runners in TOOLS/ADA_INDENT/ (assert +
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
#   rsync_time_machine.ady — needs rsync to run, so compile-only here
# -----------------------------------------------------------------------
COMPILE_ONLY := \
    tsp.ady \
    lv.ady \
    lolcate/lolcate.ady \
    rsync_time_machine.ady \
    dp/jacks.ady \
    INTERACTIVE/lispy.ady \
    awk_logscan.ady \
    sh_janitor.ady \
    config_check.ady \
    html_body.ady \
    DOC/awk_snippets.ady \
    DOC/shell_snippets.ady \
    DOC/why_snippets.ady \
    DOC/string_snippets.ady \
    DOC/type_snippets.ady \
    DOC/awk_paragraph.ady \
    test_die_warn.ady

ALL_COMPILE := \
    $(LIBS) \
    $(STANDALONE) \
    $(STDIN_EXAMPLES) \
    $(CFMU_EXAMPLES) \
    $(CFMU_COMPILE_ONLY) \
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
# compile_one_tool — the same, for a program that lives in its own
# directory rather than under EXAMPLES/: $(1) is a path from the repository
# root, so the tool keeps its README and its editor integration beside it.
# -----------------------------------------------------------------------
define compile_one_tool
	printf '  %-42s' "$(1)"; \
	if $(ADY2NIM) c $(CURDIR)/$(1) >/dev/null 2>&1; then \
	    echo OK; \
	else \
	    echo FAIL; \
	    $(ADY2NIM) c $(CURDIR)/$(1) 2>&1 | grep -E 'Error:' | head -5; \
	    exit 1; \
	fi
endef

# The programs under TOOLS/, built here so that `make clean`
# followed by `make test` leaves both of them on disk.
#
# ada_indent is on this list for a reason beyond symmetry: the three editor
# harnesses below drive the *binary*, and each SKIPs when it is missing. The
# ADA_INDENT test files above build themselves but not it -- they import the
# module, and importing leaves no binary behind -- so after a clean the
# three reported "SKIP (ada_indent not built)" and the editor integrations
# went unchecked in exactly the run that was meant to check everything.
#
# The two TCHECK programs are here for the plainer reason: nothing was
# asking them to compile, so a transpiler change that broke one broke it
# silently. Tcheck_tact carried `bt.get()` as a workaround for a guard the
# transpiler did not read, and when the guard started working the explicit
# get became a second one -- `bt.get().getOrDefault()`, which does not
# compile. The whole suite stayed green through it.
TOOL_PROGRAMS := \
    TOOLS/GIT1/git1.ady \
    TOOLS/ADA_INDENT/ada_indent.ady \
    TOOLS/PGREP/Pgrep.ady \
    TOOLS/TCHECK/Tcheck_tact.ady \
    TOOLS/TCHECK/Ttroubleshoot.ady \
    TOOLS/TBLAME/Tblame.ady \
    TOOLS/TDIFF/Tdiff.ady

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

.PHONY: check-quotes
check-quotes:
	@echo "=== Every code block in DOCS/ is code that exists ==="
	@$(PYTHON) $(CURDIR)/DOCS/check_quotes.py || exit 1

compile: lint-emitters check-quotes
	@echo "=== Compiling $(words $(ALL_COMPILE)) examples ==="
	@$(foreach f,$(ALL_COMPILE),$(call compile_one,$(f));)
	@echo "=== Compiling $(words $(TOOL_PROGRAMS)) tools ==="
	@$(foreach t,$(TOOL_PROGRAMS),$(call compile_one_tool,$(t));)
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

	@# die() and warn() end a run on purpose, so they are checked from
	@# outside: what reaches stderr, that nothing reaches stdout, and the
	@# exit status die() was given -- on both backends.
	@echo "=== die / warn / PROG builtins, both backends ==="
	@printf 'test_die_warn: a warning, and on we go\ntest_die_warn: n must be positive, got -1\n' \
	    > $(TMPDIR)/ady_die_warn.want
	@printf '  %-42s' "test_die_warn.ady (nim)"; \
	    $(EXDIR)/test_die_warn > $(TMPDIR)/ady_die_warn.out 2> $(TMPDIR)/ady_die_warn.err; \
	    rc=$$?; [ $$rc -eq 3 ] && [ ! -s $(TMPDIR)/ady_die_warn.out ] \
	        && cmp -s $(TMPDIR)/ady_die_warn.err $(TMPDIR)/ady_die_warn.want \
	        && echo OK || { echo "FAIL (rc=$$rc)"; cat $(TMPDIR)/ady_die_warn.err; exit 1; }
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_die_warn.ady > $(TMPDIR)/test_die_warn.py
	@printf '  %-42s' "test_die_warn.ady (python)"; \
	    $(PYTHON) $(TMPDIR)/test_die_warn.py > $(TMPDIR)/ady_die_warn.out 2> $(TMPDIR)/ady_die_warn.err; \
	    rc=$$?; [ $$rc -eq 3 ] && [ ! -s $(TMPDIR)/ady_die_warn.out ] \
	        && cmp -s $(TMPDIR)/ady_die_warn.err $(TMPDIR)/ady_die_warn.want \
	        && echo OK || { echo "FAIL (rc=$$rc)"; cat $(TMPDIR)/ady_die_warn.err; exit 1; }
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_die_warn_own.ady > $(TMPDIR)/test_die_warn_own.py
	@printf '  %-42s' "test_die_warn_own.ady (python)"; \
	    $(PYTHON) $(TMPDIR)/test_die_warn_own.py >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }
	@rm -f $(TMPDIR)/ady_die_warn.* $(TMPDIR)/test_die_warn.py $(TMPDIR)/test_die_warn_own.py

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
	@# awk_logscan is the worked example in DOCS/ADASCRIPT_FOR_AWK.md, so the
	@# check is on its output, not its exit status: the report is what the
	@# document quotes.
	@printf '  %-42s' "awk_logscan.ady"; \
	    $(EXDIR)/awk_logscan < $(EXDIR)/awk_logscan_sample.txt 2>&1 \
	        | grep -q "slowest : 2317 ms" && echo OK || { echo FAIL; exit 1; }
	@# The same report, written in awk, kept next to it. The document says
	@# the two agree byte for byte on this sample; this is where that stops
	@# being an assertion. POSIX awk, so mawk runs it too.
	@# ... on the sample, and on a log with no requests in it, which is the
	@# input that once crashed the Adascript side.
	@for input in awk_logscan_sample.txt awk_logscan_norecords.txt; do \
	    name=$${input%.txt}; name=$${name#awk_logscan_}; \
	    printf '  %-42s' "awk_logscan.awk == .ady ($$name)"; \
	    awk -f $(EXDIR)/awk_logscan.awk $(EXDIR)/$$input \
	        > $(TMPDIR)/ady_logscan_awk.out 2>&1; \
	    $(EXDIR)/awk_logscan < $(EXDIR)/$$input \
	        > $(TMPDIR)/ady_logscan_ady.out 2>&1; \
	    cmp -s $(TMPDIR)/ady_logscan_awk.out $(TMPDIR)/ady_logscan_ady.out \
	        && echo OK || { echo FAIL; \
	           diff $(TMPDIR)/ady_logscan_awk.out $(TMPDIR)/ady_logscan_ady.out | head -10; \
	           exit 1; }; \
	done
	@# sh_janitor is the worked example in DOCS/ADASCRIPT_FOR_SHELL.md. It
	@# builds its own fixture under /tmp, so the report is the same every
	@# run -- and the filename with a space in it is the point of the check.
	@printf '  %-42s' "sh_janitor.ady"; \
	    $(EXDIR)/sh_janitor >/dev/null 2>&1 \
	        && test -f "/tmp/ady_janitor/quiet service.log.gz" \
	        && echo OK || { echo FAIL; exit 1; }
	@# config_check reports findings and exits 1 when any of them is an
	@# error, which is the point -- so the check is on what it printed.
	@printf '  %-42s' "config_check.ady"; \
	    $(EXDIR)/config_check 2>&1 \
	        | grep -q "200 is outside 1 .. 64" && echo OK || { echo FAIL; exit 1; }
	@# html_body rewrites links to absolute paths, so its output depends on
	@# where the repository is. The stable parts are what it did: the id
	@# taken from the page's own name, the footer gone, and the link made
	@# absolute against this directory.
	@printf '  %-42s' "html_body.ady"; \
	    out=$$($(EXDIR)/html_body $(EXDIR)/html_body_sample.html 2>&1); \
	    echo "$$out" | grep -q 'id="html_body_sample"' \
	        && ! echo "$$out" | grep -q 'test_ignored' \
	        && echo "$$out" | grep -q "href=\"$(EXDIR)/test_alpha.html\"" \
	        && echo OK || { echo FAIL; exit 1; }
	@# The same checker in awk, kept next to it: same schema, same findings,
	@# same bytes. Runs after config_check, which is what writes the fixture.
	@for input in /tmp/ady_config_check/app.conf $(EXDIR)/config_check_other.conf; do \
	    name=$$(basename $$input .conf); name=$${name#config_check_}; \
	    printf '  %-42s' "config_check.awk == .ady ($$name)"; \
	    awk -f $(EXDIR)/config_check.awk $$input > $(TMPDIR)/ady_cfg_awk.out 2>&1; \
	    $(EXDIR)/config_check $$input > $(TMPDIR)/ady_cfg_ady.out 2>&1; \
	    cmp -s $(TMPDIR)/ady_cfg_awk.out $(TMPDIR)/ady_cfg_ady.out \
	        && echo OK || { echo FAIL; \
	           diff $(TMPDIR)/ady_cfg_awk.out $(TMPDIR)/ady_cfg_ady.out | head -10; \
	           exit 1; }; \
	done
	@# sh_janitor.sh is the shell version of the same janitor, and the check
	@# is that it is WRONG: `for f in $$(ls)` splits the name with a space in
	@# it, so two files fall out of the report with no error and exit 0. If
	@# this ever passes, the claim in DOCS/ADASCRIPT_FOR_SHELL.md is stale.
	@printf '  %-42s' "sh_janitor.sh loses the spaced name"; \
	    $(EXDIR)/sh_janitor.sh > $(TMPDIR)/ady_janitor_sh.out 2>&1; \
	    test $$? -eq 0 \
	        && grep -q "COMPRESS  2 file(s)" $(TMPDIR)/ady_janitor_sh.out \
	        && test -f "/tmp/sh_janitor_sh/quiet service.log" \
	        && test -f "/tmp/sh_janitor_sh/editor backup~" \
	        && echo OK || { echo FAIL; cat $(TMPDIR)/ady_janitor_sh.out; exit 1; }
	@# The documents' own snippets, so that what DOCS/*.md quotes is code
	@# that ran rather than code that was written down. check-quotes below
	@# is what ties each block to the file it came from.
	@for f in DOC/awk_snippets.ady DOC/why_snippets.ady DOC/string_snippets.ady DOC/type_snippets.ady; do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name 2>&1 | grep -q "snippets ok" \
	        && echo OK || { echo FAIL; exit 1; }; \
	done
	@printf '  %-42s' "DOC/shell_snippets.ady"; \
	    $(EXDIR)/DOC/shell_snippets one two three 2>&1 \
	        | grep -q "snippets ok" && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "DOC/awk_paragraph.ady"; \
	    $(EXDIR)/DOC/awk_paragraph < $(EXDIR)/DOC/awk_paragraph_sample.txt 2>&1 \
	        | grep -q "record 3: NF=4" && echo OK || { echo FAIL; exit 1; }
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
	@printf '  %-42s' "TOOLS/GIT1/git1.ady (--version)"; \
	    $(G1DIR)/git1 --version >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "TOOLS/PGREP/Pgrep.ady (usage)"; \
	    $(PGDIR)/Pgrep 2>/dev/null | grep -q '^Usage:' && echo OK || { echo FAIL; exit 1; }

	@# The all-subsystems path against a CM tree the test builds: $PGREP_CM_OT
	@# points the program at it, and the cc_pattern it consults there answers
	@# with a perl regexp, as the real one does. Three bugs hid in this path
	@# in a row, each of them silent, because a filter that matches nothing
	@# looks exactly like a site with nothing to search.
	@echo "=== PGREP against a CM tree built for the test ==="
	@$(PGDIR)/test/run_tests.sh $(PGDIR)/Pgrep
	@# ...and the same checks against the Python transpilation, since the two
	@# backends have to agree about every one of them.
	@echo "=== PGREP, the same checks on the Python backend ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(PGDIR)/Pgrep.ady > $(PGDIR)/test/Pgrep_py.py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(PGDIR)/test/Pgrep_py.py" \
	    > $(PGDIR)/test/pgrep_py && chmod +x $(PGDIR)/test/pgrep_py
	@$(PGDIR)/test/run_tests.sh $(PGDIR)/test/pgrep_py
	@rm -f $(PGDIR)/test/Pgrep_py.py $(PGDIR)/test/pgrep_py

	@# Tblame against a throwaway git repo the test builds, standing in for
	@# an NM workspace: both the workspace-path and the /cm/ot/ context-path
	@# branches, batching, since/filter_unmatched, and reading files
	@# directly for "- FILENAME".
	@echo "=== Tblame against a git repo built for the test ==="
	@$(TBDIR)/test/run_tests.sh $(TBDIR)/Tblame
	@# ...and the same checks against the Python transpilation.
	@echo "=== Tblame, the same checks on the Python backend ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TBDIR)/Tblame.ady > $(TBDIR)/test/Tblame_py.py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(TBDIR)/test/Tblame_py.py" \
	    > $(TBDIR)/test/tblame_py && chmod +x $(TBDIR)/test/tblame_py
	@$(TBDIR)/test/run_tests.sh $(TBDIR)/test/tblame_py
	@rm -f $(TBDIR)/test/Tblame_py.py $(TBDIR)/test/tblame_py

	@# Tdiff against a superproject the test builds: four submodules, two
	@# workspace baselines, NM baseline tags inside each submodule -- and
	@# piped into Tblame, built the same way.
	@echo "=== Tdiff against a superproject built for the test ==="
	@$(TDDIR)/test/run_tests.sh $(TDDIR)/Tdiff $(TBDIR)/Tblame
	@echo "=== Tdiff, the same checks on the Python backend ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TDDIR)/Tdiff.ady > $(TDDIR)/test/Tdiff_py.py
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TBDIR)/Tblame.ady > $(TDDIR)/test/Tblame_py.py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(TDDIR)/test/Tdiff_py.py" \
	    > $(TDDIR)/test/tdiff_py && chmod +x $(TDDIR)/test/tdiff_py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(TDDIR)/test/Tblame_py.py" \
	    > $(TDDIR)/test/tblame_py && chmod +x $(TDDIR)/test/tblame_py
	@$(TDDIR)/test/run_tests.sh $(TDDIR)/test/tdiff_py $(TDDIR)/test/tblame_py
	@rm -f $(TDDIR)/test/Tdiff_py.py $(TDDIR)/test/tdiff_py $(TDDIR)/test/Tblame_py.py $(TDDIR)/test/tblame_py

	@# Tcheck_tact -focus changes against a CM tree the test builds: a TACT
	@# baseline, the CFMUTEST changes report Psort points it at, a view build.
	@echo "=== Tcheck_tact -focus changes against a CM tree built for the test ==="
	@$(TCDIR)/test/run_changes_tests.sh $(TCDIR)/Tcheck_tact
	@echo "=== Tcheck_tact -focus changes, the same checks on the Python backend ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TCDIR)/Tcheck_tact.ady > $(TCDIR)/test/Tcheck_tact_py.py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(TCDIR)/test/Tcheck_tact_py.py" \
	    > $(TCDIR)/test/tcheck_py && chmod +x $(TCDIR)/test/tcheck_py
	@$(TCDIR)/test/run_changes_tests.sh $(TCDIR)/test/tcheck_py
	@rm -f $(TCDIR)/test/Tcheck_tact_py.py $(TCDIR)/test/tcheck_py

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
	@# The suites are run, not kept. Each leaves a symlink to its binary
	@# beside its source, and unlike ada_indent -- which the editor
	@# harnesses below go on to drive, and which a user wants on PATH --
	@# a test runner is of no use once it has reported. Left behind they
	@# sit in TOOLS/ADA_INDENT/ pointing into a cache that the next `make clean`
	@# empties, so the link outlives what it points at.
	@for f in $(ADA_INDENT_TESTS); do rm -f $(AIDIR)/$${f%.ady}; done

	@# Metamorphic check: the golden sample and regress/valid_*.adb, each
	@# re-laid-out (keywords moved to the next line, bodies pulled up beside
	@# their 'then', case and spacing changed, ...) must keep every untouched
	@# line at its column. It drives the ada_indent binary built above.
	@printf '  %-42s' "metamorphic_check.py"; \
	    out=$$($(PYTHON) $(AIDIR)/metamorphic_check.py --bin $(AIDIR)/ada_indent 2>&1); rc=$$?; \
	    if [ $$rc -eq 0 ] && printf '%s' "$$out" | grep -q ' 0 failed'; then \
	        echo OK; \
	    else \
	        echo FAIL; printf '%s\n' "$$out" | tail -20; exit 1; \
	    fi

	@# Each editor integration drives the ada_indent binary itself, so each
	@# harness needs the built binary plus its own editor. None of node,
	@# emacs or vim is otherwise a dependency of this repo, so every one of
	@# these SKIPs rather than fails when what it needs is missing. The
	@# point of running them is that the three share a design -- the
	@# --emit-state / --state cache and the rule for invalidating it -- and
	@# could otherwise drift apart silently.
	@#
	@# Each suite was mutation-checked when written: breaking the blank-line
	@# probe, the dedent-keyword list, or the cache's "strictly above" guard
	@# makes the relevant tests fail rather than pass.
	@echo "=== ADA_INDENT editor support ==="
	@printf '  %-42s' "vs_code/test_extension.js"; \
	    if ! command -v node >/dev/null 2>&1; then echo "SKIP (no node)"; \
	    elif [ ! -x "$(AIDIR)/ada_indent" ]; then echo "SKIP (ada_indent not built)"; \
	    else \
	        out=$$(PATH="$(AIDIR):$$PATH" node \
	                 $(AIDIR)/EDITOR_SUPPORT/vs_code/test/test_extension.js 2>&1); \
	        if [ $$? -eq 0 ] && printf '%s' "$$out" | grep -q 'all ok'; then echo OK; \
	        else echo FAIL; printf '%s\n' "$$out" | tail -20; exit 1; fi; \
	    fi
	@printf '  %-42s' "emacs/test-ada-indent.el"; \
	    if ! command -v emacs >/dev/null 2>&1; then echo "SKIP (no emacs)"; \
	    elif [ ! -x "$(AIDIR)/ada_indent" ]; then echo "SKIP (ada_indent not built)"; \
	    else \
	        out=$$(PATH="$(AIDIR):$$PATH" emacs -Q --batch \
	                 -L $(AIDIR)/EDITOR_SUPPORT/emacs \
	                 -l $(AIDIR)/EDITOR_SUPPORT/emacs/test-ada-indent.el \
	                 -f ert-run-tests-batch-and-exit 2>&1); \
	        if [ $$? -eq 0 ] && printf '%s' "$$out" | grep -q '0 unexpected'; then echo OK; \
	        else echo FAIL; printf '%s\n' "$$out" | tail -20; exit 1; fi; \
	    fi
	@printf '  %-42s' "vim/test-ada-indent.vim"; \
	    if ! command -v vim >/dev/null 2>&1; then echo "SKIP (no vim)"; \
	    elif [ ! -x "$(AIDIR)/ada_indent" ]; then echo "SKIP (ada_indent not built)"; \
	    else \
	        out=$$(cd $(AIDIR)/EDITOR_SUPPORT/vim && PATH="$(AIDIR):$$PATH" \
	                 vim -es -N -u NONE -S test-ada-indent.vim 2>&1); \
	        if [ $$? -eq 0 ] && printf '%s' "$$out" | grep -q 'all ok'; then echo OK; \
	        else echo FAIL; printf '%s\n' "$$out" | tail -20; exit 1; fi; \
	    fi

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
	@for t in $(TOOL_PROGRAMS); do \
	    rm -f $(CURDIR)/$${t%.ady}; \
	done
	@# `make test` deletes these as soon as each suite has reported; this is
	@# for the run that stopped before it got there.
	@for f in $(ADA_INDENT_TESTS); do rm -f $(AIDIR)/$${f%.ady}; done
	@echo "Done."
