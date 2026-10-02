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
# Scratch space: each user's own. Two people running the tests on one
# machine must not meet in /tmp, where the other's files are not theirs to
# overwrite -- a test found the first one's and failed. Exported, so the
# examples' fixtures go there too.
TMPDIR ?= /tmp/adascript-test-$(shell id -un)
export TMPDIR
$(shell mkdir -p $(TMPDIR))
TOOLDIR:= $(CURDIR)/TOOLS
AIDIR  := $(TOOLDIR)/ADA_INDENT
G1DIR  := $(TOOLDIR)/GIT1
PGDIR  := $(TOOLDIR)/PGREP
TBDIR  := $(TOOLDIR)/TBLAME
TDDIR  := $(TOOLDIR)/TDIFF
TCDIR  := $(TOOLDIR)/TCHECK
RTDIR  := $(TOOLDIR)/RSYNC_TIME_MACHINE
C5DIR  := $(TOOLDIR)/C500

# Prepend choosenim's bin dir so Nim 2.x is used instead of any system Nim 1.x.
export PATH := /root/.nimble/bin:$(HOME)/.nimble/bin:$(HOME)/Downloads:$(PATH)

.PHONY: test test-vi compile clean install uninstall

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
    GEO_SERVER/geo_server.ady \
    GEO_SERVER/test_geo_server.ady \
    MAP_UTILS/map_utils.ady \
    MAP_UTILS/test_map_utils.ady \
    MAP_UTILS/test_hek_map_utils.ady \
    MAP_UTILS/route_check.ady \
    openarray_demo.ady \
    test_inline_suite.ady \
    test_state_search.ady \
    test_shortest_path.ady \
    primes.ady \
    test_ownership.ady \
    ownership_tour.ady \
    test_iters.ady \
    test_graphs.ady \
    test_ansi.ady \
    test_queues.ady \
    test_regex.ady \
    test_regex_g.ady \
    test_env_default.ady \
    test_env_optional.ady \
    test_optional_truthy.ady \
    test_self_ref.ady \
    test_char_slice.ady \
    pyimport_similar.ady \
    test_pyobject_calls.ady \
    td_learning/sarsa.ady \
    td_learning/qlearning.ady \
    PROJECT/dispatch.ady \
    PROJECT/test_geometry.ady \
    test_do_block.ady \
    test_result.ady \
    test_optional_spelling.ady \
    test_union.ady \
    test_case_ranges.ady \
    test_contextmanager_fstring.ady \
    test_stmt_modifier.ady \
    test_str_join.ady \
    test_which.ady \
    test_shell_stdin_status.ady \
    test_strip_chars.ady \
    test_path_call.ady \
    test_path_relative_to.ady \
    test_path_io.ady \
    test_parse.ady \
    trcks_example.ady \
    test_nimport_modules.ady \
    test_nimport_qualified.ady \
    test_vi_highlight.ady \
    test_vi_save.ady \
    test_str_partition.ady \
    test_and_or_mix.ady \
    test_enum_values.ady \
    test_case_narrowed.ady \
    test_not_operand.ady \
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
    test_ordered_map.ady \
    test_function_type.ady \
    test_distinct.ady \
    test_units.ady \
    test_money.ady \
    test_subrange_array.ady \
    test_variant_literal.ady \
    test_set_operators.ady \
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
    test_char_table_literal.ady \
    test_param_nested_mutation.ady \
    test_method_named_field.ady \
    test_seq_field_concat.ady \
    test_image_method.ady \
    test_run_discard.ady \
    test_split_unpack.ady \
    test_path_lines.ady \
    test_in_loop_var.ady \
    test_docstring_oneline.ady \
    test_class_fields_per_instance.ady \
    test_pure_method_calls.ady \
    test_definition_order.ady \
    test_ctor_trailing_underscore.ady \
    test_indexed_table_items.ady \
    test_case_trailing_comment.ady \
    test_call_result_type.ady

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
#   BENCH_SEARCH/bench_search.ady — a timing program: its output is the clock
# -----------------------------------------------------------------------
COMPILE_ONLY := \
    tsp.ady \
    test_input.ady \
    VI/vi_nim.ady \
    VI/vi_raw.ady \
    dp/jacks.ady \
    BENCH_SEARCH/bench_search.ady \
    awk_logscan.ady \
    sh_janitor.ady \
    config_check.ady \
    html_body.ady \
    DOC/awk_snippets.ady \
    DOC/shell_snippets.ady \
    DOC/why_snippets.ady \
    DOC/why_alias_snippets.ady \
    DOC/string_snippets.ady \
    DOC/type_snippets.ady \
    DOC/awk_paragraph.ady \
    test_die_warn.ady \
    test_print_bare.ady

# Run on both backends and their output compared, below: the Nim run there
# is the one they get, so the self-contained loop leaves them out.
BOTH_BACKENDS_COMPARED := test_do_block test_result test_optional_spelling \
    test_union test_case_ranges test_contextmanager_fstring \
    test_ordered_map test_function_type test_distinct test_units test_money \
    test_subrange_array test_variant_literal test_set_operators \
    test_path_relative_to test_path_io test_parse trcks_example \
    test_nimport_modules test_nimport_qualified test_vi_highlight test_vi_save test_str_partition test_and_or_mix test_enum_values test_case_narrowed test_not_operand

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
# _compile_one — internal helper: compile a single file, silently when it
# builds: each file is listed where it is run, and a second line for its
# compilation only doubled the report. On failure, name the file, re-run
# and show the error lines, then abort.
# -----------------------------------------------------------------------
define compile_one
	if ! $(ADY2NIM) c $(EXDIR)/$(1) >/dev/null 2>&1; then \
	    printf '  %-42s%s\n' "$(1)" FAIL; \
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
	if ! $(ADY2NIM) c $(CURDIR)/$(1) >/dev/null 2>&1; then \
	    printf '  %-42s%s\n' "$(1)" FAIL; \
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
# Tcheck_tact is here for the plainer reason: nothing was
# asking it to compile, so a transpiler change that broke it did so
# silently. Tcheck_tact carried `bt.get()` as a workaround for a guard the
# transpiler did not read, and when the guard started working the explicit
# get became a second one -- `bt.get().getOrDefault()`, which does not
# compile. The whole suite stayed green through it.
#
# rsync_time_machine is also run, by its test script below, when rsync is
# installed; c500 by its own, on both backends; lolcate and lv are
# compiled only (running them needs fd and rg, and clv).
TOOL_PROGRAMS := \
    TOOLS/GIT1/git1.ady \
    TOOLS/ADA_INDENT/ada_indent.ady \
    TOOLS/PGREP/Pgrep.ady \
    TOOLS/TCHECK/Tcheck_tact.ady \
    TOOLS/TCHECK/make_comparable.ady \
    TOOLS/TCHECK/Tcheckout.ady \
    TOOLS/TBLAME/Tblame.ady \
    TOOLS/TDIFF/Tdiff.ady \
    TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady \
    TOOLS/LOLCATE/lolcate.ady \
    TOOLS/C500/c500.ady \
    TOOLS/LV/lv.ady \
    TOOLS/THIST/Thist.ady \
    TOOLS/LISPY/lispy.ady

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
	@printf '  %-42s%s\n' "all $(words $(ALL_COMPILE))" OK
	@echo "=== Compiling $(words $(TOOL_PROGRAMS)) tools ==="
	@$(foreach t,$(TOOL_PROGRAMS),$(call compile_one_tool,$(t));)
	@printf '  %-42s%s\n' "all $(words $(TOOL_PROGRAMS))" OK
	@echo "=== Compile step complete ==="

# -----------------------------------------------------------------------
# The vi tests: key scripts typed into vi_py.ady (curses, the Python backend)
# and vi_nim.ady and vi_raw.ady (Nim) in a pty of their own, and the files they save
# compared. Shared by `test` and by `test-vi`, which runs them alone.
# -----------------------------------------------------------------------
define vi_tests
	@echo "=== vi, typed keys in a pty of its own: vi_py.ady (curses, Python), vi_nim.ady (illwill) and vi_raw.ady (Nim) ==="
	@printf '  %-62s' "EXAMPLES/VI/vi_py.ady (69 key scripts, 9 screen checks)"; \
	    if ! $(PYTHON) -c 'import curses, pty' 2>/dev/null; then echo "SKIP (no curses or pty)"; else \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/VI/vi_py.ady > $(TMPDIR)/ady_vi.py || { echo FAIL; exit 1; }; \
	    $(PYTHON) $(EXDIR)/VI/test_vi.py $(TMPDIR)/ady_vi.py > $(TMPDIR)/ady_vi.out 2>&1 \
	        && echo OK || { echo FAIL; grep -A2 FAIL $(TMPDIR)/ady_vi.out | head -20; grep -q FAIL $(TMPDIR)/ady_vi.out || tail -n 8 $(TMPDIR)/ady_vi.out; exit 1; }; fi
	@printf '  %-62s' "EXAMPLES/VI/vi_nim.ady (72 key scripts, 9 screen checks)"; \
	    if ! $(PYTHON) -c 'import pty' 2>/dev/null; then echo "SKIP (no pty)"; else \
	    $(PYTHON) $(EXDIR)/VI/test_vi.py $(EXDIR)/VI/vi_nim > $(TMPDIR)/ady_vi_nim.out 2>&1 \
	        && echo OK || { echo FAIL; grep -A2 FAIL $(TMPDIR)/ady_vi_nim.out | head -20; grep -q FAIL $(TMPDIR)/ady_vi_nim.out || tail -n 8 $(TMPDIR)/ady_vi_nim.out; exit 1; }; fi
	@printf '  %-62s' "EXAMPLES/VI/vi_raw.ady (72 key scripts, 9 screen checks)"; \
	    if ! $(PYTHON) -c 'import pty' 2>/dev/null; then echo "SKIP (no pty)"; else \
	    $(PYTHON) $(EXDIR)/VI/test_vi.py $(EXDIR)/VI/vi_raw > $(TMPDIR)/ady_vi_raw.out 2>&1 \
	        && echo OK || { echo FAIL; grep -A2 FAIL $(TMPDIR)/ady_vi_raw.out | head -20; grep -q FAIL $(TMPDIR)/ady_vi_raw.out || tail -n 8 $(TMPDIR)/ady_vi_raw.out; exit 1; }; fi
endef

# -----------------------------------------------------------------------
# test-vi — the vi tests alone: build vi_nim.ady and vi_raw.ady, then run them (about 15 s)
# -----------------------------------------------------------------------
.PHONY: test-vi
test-vi:
	@mkdir -p $(TMPDIR)
	@for v in vi_nim vi_raw; do \
	    if ! $(ADY2NIM) c $(EXDIR)/VI/$$v.ady >/dev/null 2>&1; then \
	        echo "  EXAMPLES/VI/$$v.ady                    FAIL (does not build)"; \
	        $(ADY2NIM) c $(EXDIR)/VI/$$v.ady 2>&1 | grep -E 'Error:' | head -5; exit 1; \
	    fi; \
	done
	$(vi_tests)

# -----------------------------------------------------------------------
# test — compile everything, then run the runnable subset
# -----------------------------------------------------------------------
test: compile
	@echo ""

	@echo "=== Self-contained examples ==="
	@for f in $(filter-out $(addsuffix .ady,$(BOTH_BACKENDS_COMPARED)),$(STANDALONE)); do \
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

	@# $0 is the program's path on both backends -- PROG is its name.
	@echo "=== \$$0 is the program's path, both backends ==="
	@printf 'let source: Path = Path($$0).parent / "ady_dollar0.ady"\nassert -f source\nprint "ok"\n' \
	    > $(TMPDIR)/ady_dollar0.ady
	@printf '  %-42s' "\$$0 (nim)"; \
	    cd $(TMPDIR) && XDG_CACHE_HOME=$(TMPDIR)/ady_dollar0_cache $(ADY2NIM) c ady_dollar0.ady >/dev/null 2>&1 \
	    && cd / && $(TMPDIR)/ady_dollar0 2>&1 | grep -qx ok && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "\$$0 (python)"; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TMPDIR)/ady_dollar0.ady > $(TMPDIR)/ady_dollar0_py.py \
	    && cd / && $(PYTHON) $(TMPDIR)/ady_dollar0_py.py 2>&1 | grep -qx ok && echo OK || { echo FAIL; exit 1; }
	@rm -rf $(TMPDIR)/ady_dollar0.ady $(TMPDIR)/ady_dollar0 $(TMPDIR)/ady_dollar0_py.py $(TMPDIR)/ady_dollar0_cache

	@# Output cut short -- `prog | head` -- ends a Nim program quietly, with
	@# status 141 as SIGPIPE ends a C one: no "Broken pipe" stack trace.
	@echo "=== Output cut short: no Broken pipe trace (nim) ==="
	@printf 'for i in range(100000):\n    stdout.write(f"line {i}\\n")\nraise RuntimeError("other")\n' \
	    > $(TMPDIR)/ady_pipe.ady
	@printf '  %-42s' "prog | head -1"; \
	    cd $(TMPDIR) && XDG_CACHE_HOME=$(TMPDIR)/ady_pipe_cache $(ADY2NIM) c ady_pipe.ady >/dev/null 2>&1 \
	    && { ./ady_pipe 2>ady_pipe.err; echo $$? > ady_pipe.rc; } | head -1 >/dev/null \
	    && [ "$$(cat ady_pipe.rc)" = 141 ] && [ ! -s ady_pipe.err ] && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "...another error still reported"; \
	    cd $(TMPDIR) && ./ady_pipe 2>&1 >/dev/null | grep -q 'unhandled exception: other' && echo OK || { echo FAIL; exit 1; }
	@rm -rf $(TMPDIR)/ady_pipe.ady $(TMPDIR)/ady_pipe $(TMPDIR)/ady_pipe.err $(TMPDIR)/ady_pipe.rc $(TMPDIR)/ady_pipe_cache

	@# A change to a bundled support file -- TO_NIM/STDLIB/stdlib.nim -- has
	@# to rebuild the programs using it: ady2nim used to call them up to date
	@# and keep the old code until `make clean`. On a copy of the transpiler,
	@# whose stdlib.nim can be edited, with a cache of its own.
	@echo "=== a changed stdlib.nim rebuilds what uses it ==="
	@printf '  %-42s' "stdlib.nim edited after a build"; \
	    d=$$(mktemp -d); \
	    cp -r $(CURDIR)/TO_NIM $(CURDIR)/TO_PYTHON $(CURDIR)/GRAMMAR $(CURDIR)/HPARSEC $$d/ && \
	    mkdir $$d/src && \
	    printf 'from stdlib import Counter_T\nlet c: Counter_T[str] = Counter_T(["a", "b", "a"])\nprint c.total()\n' > $$d/src/cnt.ady && \
	    XDG_CACHE_HOME=$$d/cache $(PYTHON) $$d/TO_NIM/ady2nim.py c $$d/src/cnt.ady >/dev/null 2>&1 && \
	    before=$$($$d/src/cnt) && sleep 1 && \
	    $(PYTHON) -c 'import sys; p = sys.argv[1]; s = open(p).read(); \
	        old = "  for v in c.values: result += v\n"; assert old in s; \
	        open(p, "w").write(s.replace(old, old + "  result += 100\n"))' $$d/TO_NIM/STDLIB/stdlib.nim && \
	    XDG_CACHE_HOME=$$d/cache $(PYTHON) $$d/TO_NIM/ady2nim.py c $$d/src/cnt.ady >/dev/null 2>&1 && \
	    after=$$($$d/src/cnt); \
	    rm -rf $$d; \
	    if [ "$$before" = 3 ] && [ "$$after" = 103 ]; then echo OK; \
	    else echo "FAIL (before: $$before, after the edit: $$after, want 3 then 103)"; exit 1; fi

	@# The transpiler's own tests: translations and the errors it must raise.
	@echo "=== ady2nim --test ==="
	@printf '  %-42s' "ady2nim.py --test"; \
	    $(ADY2NIM) --test > $(TMPDIR)/ady2nim_selftest.out 2>&1 \
	    && echo OK || { echo FAIL; grep -v PASS $(TMPDIR)/ady2nim_selftest.out; exit 1; }
	@rm -f $(TMPDIR)/ady2nim_selftest.out

	@# A type declared twice is refused on both backends, naming the first.
	@echo "=== a type declared twice, both backends ==="
	@printf 'type A is int\n"""\ntype B is int\n"""\ntype B is int\nclass A:\n    var x: int = 0\n' \
	    > $(TMPDIR)/ady_dup_type.ady
	@for tr in TO_NIM/ady2nim.py TO_PYTHON/ady2py.py; do \
	    printf '  %-42s' "duplicate type ($$tr)"; \
	    if $(PYTHON) $(CURDIR)/$$tr $(TMPDIR)/ady_dup_type.ady > $(TMPDIR)/ady_dup_type.out 2>&1; then \
	        echo "FAIL (accepted)"; exit 1; \
	    fi; \
	    grep -q "line 6: type 'A' is already declared, at line 1" $(TMPDIR)/ady_dup_type.out \
	        && echo OK || { echo FAIL; cat $(TMPDIR)/ady_dup_type.out; exit 1; }; \
	done
	@rm -f $(TMPDIR)/ady_dup_type.ady $(TMPDIR)/ady_dup_type.out

	@# A bare print is an empty line on both backends: compared from outside.
	@echo "=== bare print, both backends ==="
	@printf 'a\n\nb\n\n\nc\n' > $(TMPDIR)/ady_print_bare.want
	@printf '  %-42s' "test_print_bare.ady (nim)"; \
	    $(EXDIR)/test_print_bare | cmp -s - $(TMPDIR)/ady_print_bare.want \
	        && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "test_print_bare.ady (python)"; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_print_bare.ady | $(PYTHON) - \
	        | cmp -s - $(TMPDIR)/ady_print_bare.want && echo OK || { echo FAIL; exit 1; }
	@rm -f $(TMPDIR)/ady_print_bare.want

	@# Each instance has fields of its own on Python too, set once: a field
	@# its __init__ sets first thing is not set to its zero before.
	@echo "=== class fields per instance (python) ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_class_fields_per_instance.ady \
	    > $(TMPDIR)/test_class_fields_per_instance.py
	@printf '  %-42s' "test_class_fields_per_instance.ady (python)"; \
	    $(PYTHON) $(TMPDIR)/test_class_fields_per_instance.py | grep -qx ok && echo OK || { echo FAIL; exit 1; }
	@printf '  %-42s' "...a field __init__ sets is set once"; \
	    [ "$$(grep -c 'self.vehicles = \[\]' $(TMPDIR)/test_class_fields_per_instance.py)" = 1 ] \
	    && [ "$$(grep -c 'self.opened = ' $(TMPDIR)/test_class_fields_per_instance.py)" = 2 ] \
	    && echo OK || { echo FAIL; exit 1; }
	@rm -f $(TMPDIR)/test_class_fields_per_instance.py

	@# A comment block after a case whose last branch is on one line stays
	@# a comment after it, rather than landing in that branch's head.
	@echo "=== a comment after a one-line case branch (python) ==="
	@printf '  %-42s' "test_case_trailing_comment.ady (python)"; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_case_trailing_comment.ady | $(PYTHON) - \
	    | grep -qx 'test_case_trailing_comment: ok' && echo OK || { echo FAIL; exit 1; }

	@# rsync_time_machine against real folders, when rsync is there: a step
	@# that fails stops the run, and a full disk expires the oldest backup.
	@echo "=== rsync_time_machine, both backends ==="
	@if command -v rsync >/dev/null 2>&1; then \
	    printf '  %-42s\n' "rsync_time_machine (nim)"; \
	    $(RTDIR)/test/rsync_time_machine_test.sh $(TMPDIR)/ady_rtm_nim $(RTDIR)/rsync_time_machine \
	        || { echo FAIL; exit 1; }; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(RTDIR)/rsync_time_machine.ady > $(TMPDIR)/ady_rtm.py || exit 1; \
	    printf '  %-42s\n' "rsync_time_machine (python)"; \
	    $(RTDIR)/test/rsync_time_machine_test.sh $(TMPDIR)/ady_rtm_py $(PYTHON) $(TMPDIR)/ady_rtm.py \
	        || { echo FAIL; exit 1; }; \
	    rm -f $(TMPDIR)/ady_rtm.py; \
	else \
	    printf '  %-42s%s\n' "rsync_time_machine" "skipped (no rsync)"; \
	fi
	@# c500, the C to WebAssembly compiler: the module it emits for each
	@# C program in its test/, the same from both backends.
	@echo "=== c500, both backends ==="
	@$(C5DIR)/test/run_c500_tests.sh $(C5DIR)/c500 || exit 1
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(C5DIR)/c500.ady > $(TMPDIR)/ady_c500.py || exit 1
	@$(C5DIR)/test/run_c500_tests.sh $(PYTHON) $(TMPDIR)/ady_c500.py || exit 1
	@rm -f $(TMPDIR)/ady_c500.py

	@# do: and `T | E` say the same on both backends: the Python one
	@# used to drop a do: block altogether, leaving its names unbound.
	@echo "=== unions, T | F and do:, both backends ==="
	@# Refused on both backends: union members nothing can tell apart, a
	@# failure nobody takes -- a bare call whose `T | !F` result is thrown
	@# away -- a shell failure left unconverted, a case missing a side.
	@printf 'var x: []int | []str\n' > $(TMPDIR)/ady_refuse_1.ady
	@printf 'type Bad_T is record:\n    why: str\n\ndef step(n: int) -> None | !Bad_T:\n    if n < 0:\n        return Bad_T(why="neg")\n\ndef run() -> None:\n    step(-1)\n' \
	    > $(TMPDIR)/ady_refuse_2.ady
	@printf 'type Bad_T is record:\n    why: str\n\ndef a() -> None | !Bad_T:\n    do:\n        shell: true\n' \
	    > $(TMPDIR)/ady_refuse_3.ady
	@printf 'type Bad_T is record:\n    why: str\n\ndef f() -> int | !Bad_T:\n    return 1\n\nlet h: int | !Bad_T = f()\ncase h:\n    when Bad_T:\n        print "b"\n' \
	    > $(TMPDIR)/ady_refuse_4.ady
	@printf 'type Bad_T is record:\n    why: str\n\nvar x: int | !Bad_T\nvar y: str | Bad_T\n' \
	    > $(TMPDIR)/ady_refuse_5.ady
	@printf 'type Bad_T is failure record:\n    why: str\n' > $(TMPDIR)/ady_refuse_6.ady
	@printf 'type Bad_T is record:\n    why: str\n\ndef f(s: str) -> int | Bad_T:\n    return len(s)\n\ndef g(s: str) -> int | Bad_T:\n    do:\n        n <- f(s)\n    return f(s)\n' \
	    > $(TMPDIR)/ady_refuse_7.ady
	@printf 'def f(n: int) -> str:\n    case n:\n        when 34 | 92: return "esc"\n        when 32..126: return "lit"\n        when others: return "esc"\n' \
	    > $(TMPDIR)/ady_refuse_8.ady
	@# Type parameters are declared and named, never inferred: a bare call of a
	@# generic function, and a lone capital in a signature nobody declared.
	@printf 'def first_of[T](xs: []T) -> T:\n    return xs[0]\n\nprint first_of([7, 8])\n' \
	    > $(TMPDIR)/ady_refuse_9.ady
	@printf 'def first_of(xs: []T) -> T:\n    return xs[0]\n\nprint first_of[int]([7, 8])\n' \
	    > $(TMPDIR)/ady_refuse_10.ady
	@# A derived unit combines two units, and says how to name the middle of
	@# a chain; and a syntax error is a failure -- ady2py used to print it,
	@# translate what came before it, and exit 0.
	@printf 'type Mass_T is distinct float\ntype Speed_T is distinct float\ntype Energy_T is Mass_T * Speed_T * Speed_T\n' \
	    > $(TMPDIR)/ady_refuse_11.ady
	@printf 'let a: int = 1\nlet y: int = (a b)\nprint a\n' \
	    > $(TMPDIR)/ady_refuse_12.ady
	@# A bare variant literal fills the fields of its kind, in order.
	@printf 'type K_T is enum A, B\n\ntype V_T (kind: K_T) is record:\n    case kind is\n        when A:\n            n: int\n        when B:\n            pass\n\nprint A(1, 2).kind\n' \
	    > $(TMPDIR)/ady_refuse_13.ady
	@printf 'type K_T is enum A, B\n\ntype V_T (kind: K_T) is record:\n    case kind is\n        when A:\n            n: int\n            m: int\n        when B:\n            pass\n\nprint A(n=1, 2).kind\n' \
	    > $(TMPDIR)/ady_refuse_14.ady
	@# relative_to can fail, so its result is taken, not dropped.
	@printf 'let b: Path = Path("/a")\nlet p: Path = Path("/a/b")\np.relative_to(b)\n' \
	    > $(TMPDIR)/ady_refuse_15.ady
	@# mkdir can fail too: its result is taken, not dropped.
	@printf 'let d: Path = Path("/tmp")\nd.mkdir()\n' > $(TMPDIR)/ady_refuse_16.ady
	@# writing a file can fail too: its result is taken, not dropped.
	@printf 'let f: Path = Path("/tmp/x")\nf.write_text("x")\n' > $(TMPDIR)/ady_refuse_17.ady
	@# a conversion can fail, so its result is taken, not dropped.
	@printf 'let t: str = "1"\nparse_float(t)\n' > $(TMPDIR)/ady_refuse_18.ady
	@printf 'let t: str = "1"\nparse_int(t)\n' > $(TMPDIR)/ady_refuse_19.ady
	@printf 'input("name: ")\n' > $(TMPDIR)/ady_refuse_20.ady
	@printf 'stdin.readLine()\n' > $(TMPDIR)/ady_refuse_21.ady
	@# from M import A: the file may use A and what it carries, not M's other names.
	@printf 'def helper() -> int:\n    return 1\n\ndef other() -> int:\n    return 2\n' > $(TMPDIR)/ady_refuse_mod.ady
	@printf 'from ady_refuse_mod import helper\nprint other()\n' > $(TMPDIR)/ady_refuse_22.ady
	@# import M binds M, as Python's: M's names are M.name, not bare; and
	@# M.name cannot be used beside a name of the file's own that M also declares.
	@printf 'import ady_refuse_mod\nprint helper()\n' > $(TMPDIR)/ady_refuse_23.ady
	@printf 'import ady_refuse_mod\ndef helper() -> int:\n    return 3\nprint ady_refuse_mod.helper()\n' > $(TMPDIR)/ady_refuse_24.ady
	@# a rename onto a name the file already gives a meaning of its own
	@printf 'from ady_refuse_mod import helper as h\nlet h: int = 2\nprint h\n' > $(TMPDIR)/ady_refuse_25.ady
	@# a rename takes the old name away, as in Python
	@printf 'from ady_refuse_mod import helper as h\nprint helper()\n' > $(TMPDIR)/ady_refuse_26.ady
	@printf 'import ady_refuse_mod as m\nprint ady_refuse_mod.helper()\n' > $(TMPDIR)/ady_refuse_27.ady
	@# enum values: all or none, ascending; gaps cannot index, iterate or step
	@printf 'type K is enum A = 1, B, C = 3\nprint 1\n' > $(TMPDIR)/ady_refuse_28.ady
	@printf 'type K is enum A = 5, B = 1\nprint 1\n' > $(TMPDIR)/ady_refuse_29.ady
	@printf 'type K is enum A = 1, B = 1\nprint 1\n' > $(TMPDIR)/ady_refuse_30.ady
	@printf 'type K is enum:\n    A = 0\n    B\nprint 1\n' > $(TMPDIR)/ady_refuse_31.ady
	@printf 'type K is enum A = 0, B = 2\nvar t: [K]int\nprint 1\n' > $(TMPDIR)/ady_refuse_32.ady
	@printf 'type K is enum A = 0, B = 2\nfor x in K:\n    print x\n' > $(TMPDIR)/ady_refuse_33.ady
	@printf "type K is enum A = 0, B = 2\nlet v: K = A\nprint v'Next\n" > $(TMPDIR)/ady_refuse_34.ady
	@for tr in TO_NIM/ady2nim.py TO_PYTHON/ady2py.py; do \
	    for c in "1:members no one can tell apart:cannot be told apart" \
	             "2:a dropped failure:drops a failure" \
	             "3:a shell failure unconverted:convert it with" \
	             "4:a case missing a member:must cover every member" \
	             "5:a failure left unmarked:mark it \`!Bad_T\`" \
	             "6:the old failure record:an ordinary record now" \
	             "7:a do step on a union with no !:if one member is, mark it" \
	             "8:overlapping case labels:34 is covered by two branches" \
	             "9:a generic call that infers its types:does not infer type arguments" \
	             "10:a type parameter nobody declared:not declared" \
	             "11:a unit made of three factors:has no name" \
	             "12:a syntax error is a failure:Parse error" \
	             "13:too many fields in a literal:takes 1 field" \
	             "14:a positional field after a named one:follows one given by name" \
	             "15:a dropped Path.relative_to:drops a failure" \
	             "16:a dropped Path.mkdir:drops a failure" \
	             "17:a dropped Path.write_text:drops a failure" \
	             "18:a dropped parse_float:drops a failure" \
	             "19:a dropped parse_int:drops a failure" \
	             "20:a dropped input():drops a failure" \
	             "21:a dropped stdin.readLine():drops a failure" \
	             "22:a name left out of a from-list:is not imported from" \
	             "23:a bare name after import M:write ady_refuse_mod.helper" \
	             "24:M.name beside the file's own name:cannot be told from" \
	             "25:a rename onto the file's own name:gives 'h' a meaning of its own" \
	             "26:the old name after from M import A as B:is imported from ady_refuse_mod as" \
	             "27:the module after import M as N:is imported as 'm'" \
	             "28:a mix of valued and bare members:either every member has a value or none does" \
	             "29:values that descend:they must ascend" \
	             "30:a repeated value:they must ascend" \
	             "31:a mix, in the block form:either every member has a value or none does" \
	             "32:a gapped enum as an array index:cannot be used as an array index" \
	             "33:a gapped enum iterated:cannot be iterated" \
	             "34:'Next of a gapped enum:cannot be stepped"; do \
	        n=$${c%%:*}; rest=$${c#*:}; what=$${rest%%:*}; want=$${rest#*:}; \
	        printf '  %-42s' "$$what ($$(basename $$tr .py))"; \
	        if $(PYTHON) $(CURDIR)/$$tr $(TMPDIR)/ady_refuse_$$n.ady > $(TMPDIR)/ady_refuse.out 2>&1; then \
	            echo "FAIL (accepted)"; exit 1; \
	        fi; \
	        grep -q "$$want" $(TMPDIR)/ady_refuse.out \
	            && echo OK || { echo FAIL; cat $(TMPDIR)/ady_refuse.out; exit 1; }; \
	    done; \
	done
	@rm -f $(TMPDIR)/ady_refuse_[0-9]*.ady $(TMPDIR)/ady_refuse.out
	@# A distinct type mixes with nothing else: not its base, not another
	@# distinct type on the same base. Nim's compiler refuses each of these;
	@# the Python backend refuses those it can see -- a typed name given, or
	@# an operator between two typed names -- and leaves a wrong argument to
	@# Nim, whose signature it does not record.
	@echo "=== distinct types do not mix, both backends ==="
	@printf 'type Velocity_T is distinct float\ntype Distance_T is distinct float\ntype Duration_T is distinct float\ntype Rate_T is Distance_T / Duration_T\ndef fly(v: Velocity_T) -> Velocity_T:\n    return v\nvar v: Velocity_T = 1.0\nvar d: Distance_T = 2.0\nvar t: Duration_T = 1.0\nvar f: float = 3.0\ntype Dollar_T is distinct float\ntype Euro_T is distinct float\ntype FX_T is Euro_T / Dollar_T\nvar usd: Dollar_T = 10.0\nvar eur: Euro_T = 9.0\nvar fx: FX_T = 0.9\nvar n: int = 3\n' \
	    > $(TMPDIR)/ady_distinct_hdr.ady
	@# `*` and `/` scale, so the product of two units is refused unless a
	@# derived unit says what it makes; a unit made of two others gives its
	@# result the right unit, and only that one.
	@for c in "1:py:another distinct type given:let e: Distance_T = v" \
	          "2:py:its base type given:let e: Distance_T = f" \
	          "3:py:given to its base type:let g: float = d" \
	          "4:py:assigned another distinct type:d = v" \
	          "5:py:added to another distinct type:let e: Distance_T = v + d" \
	          "6:py:compared with another distinct:let b: bool = v < d" \
	          "7:nim:passed for another distinct:let w: Velocity_T = fly(d)" \
	          "8:py:a unit times itself:let e: Velocity_T = v * v" \
	          "9:py:two units with no relation:let e: Distance_T = d * t" \
	          "10:py:a quotient in the wrong unit:let e: Duration_T = d / t" \
	          "11:py:a plain number over a unit:let e: Rate_T = 1.0 / t" \
	          "12:py:a scaled unit in the wrong type:let e: Distance_T = v * 2.0" \
	          "13:py:a derived unit and its neighbour:let e: Distance_T = d / t + v" \
	          "14:py:dollars plus euros:let e: Dollar_T = usd + eur" \
	          "15:py:dollars squared:let e: Dollar_T = usd * usd" \
	          "16:py:a rate applied to the wrong currency:let e: Euro_T = eur * fx" \
	          "17:py:a rate applied the wrong way round:let e: Euro_T = usd / fx" \
	          "18:py:a plain number as money:let e: Dollar_T = f"; do \
	    n=$${c%%:*}; rest=$${c#*:}; who=$${rest%%:*}; rest=$${rest#*:}; \
	    what=$${rest%%:*}; line=$${rest#*:}; \
	    { cat $(TMPDIR)/ady_distinct_hdr.ady; echo "$$line"; } > $(TMPDIR)/ady_distinct_$$n.ady; \
	    printf '  %-42s' "$$what (ady2nim)"; \
	    if (cd $(TMPDIR) && XDG_CACHE_HOME=$(TMPDIR)/ady_distinct_cache $(ADY2NIM) c ady_distinct_$$n.ady) \
	            > $(TMPDIR)/ady_distinct.out 2>&1; then echo "FAIL (accepted)"; exit 1; fi; \
	    grep -q "type mismatch" $(TMPDIR)/ady_distinct.out \
	        && echo OK || { echo FAIL; cat $(TMPDIR)/ady_distinct.out; exit 1; }; \
	    if [ "$$who" = py ]; then \
	        printf '  %-42s' "$$what (ady2py)"; \
	        if $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TMPDIR)/ady_distinct_$$n.ady \
	                > $(TMPDIR)/ady_distinct.out 2>&1; then echo "FAIL (accepted)"; exit 1; fi; \
	        grep -q "does not mix\|has no unit" $(TMPDIR)/ady_distinct.out \
	            && echo OK || { echo FAIL; cat $(TMPDIR)/ady_distinct.out; exit 1; }; \
	    fi; \
	done
	@printf '  %-42s' "conversions, scaling and derived units"; \
	    { cat $(TMPDIR)/ady_distinct_hdr.ady; printf 'let e: Distance_T = Distance_T(f)\nlet g: float = float(d)\nlet r: Rate_T = d / t\nlet back: Distance_T = r * t\nlet eta: Duration_T = d / r\nlet s: Velocity_T = v * 2.0 + v / 4.0\nlet q: float = v / v\nlet cost: Dollar_T = usd * n + usd / 2\nlet paid: Euro_T = usd * fx\nlet owed: Dollar_T = eur / fx\nprint e, g, back, eta, s, q, cost, paid, owed\n'; } \
	        > $(TMPDIR)/ady_distinct_ok.ady; \
	    (cd $(TMPDIR) && XDG_CACHE_HOME=$(TMPDIR)/ady_distinct_cache $(ADY2NIM) c ady_distinct_ok.ady >/dev/null 2>&1) \
	    && $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TMPDIR)/ady_distinct_ok.ady >/dev/null 2>&1 \
	    && echo OK || { echo FAIL; exit 1; }
	@rm -rf $(TMPDIR)/ady_distinct_* $(TMPDIR)/ady_distinct.out
	@for t in $(BOTH_BACKENDS_COMPARED); do \
	    printf '  %-42s' "$$t.ady (python = nim)"; \
	    $(EXDIR)/$$t > $(TMPDIR)/ady_$$t.nim.out 2>&1 || { echo "FAIL (nim)"; exit 1; }; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/$$t.ady > $(TMPDIR)/ady_$$t.py \
	        && $(PYTHON) $(TMPDIR)/ady_$$t.py > $(TMPDIR)/ady_$$t.py.out 2>&1 \
	        && cmp -s $(TMPDIR)/ady_$$t.nim.out $(TMPDIR)/ady_$$t.py.out \
	        && echo OK || { echo FAIL; diff $(TMPDIR)/ady_$$t.nim.out $(TMPDIR)/ady_$$t.py.out; exit 1; }; \
	    rm -f $(TMPDIR)/ady_$$t.nim.out $(TMPDIR)/ady_$$t.py $(TMPDIR)/ady_$$t.py.out; \
	done

	@echo "=== Stdin examples (piped from test_awk_sample.txt) ==="
	@for f in $(STDIN_EXAMPLES); do \
	    name=$${f%.ady}; \
	    printf '  %-42s' "$$f"; \
	    $(EXDIR)/$$name < $(EXDIR)/test_awk_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }; \
	done

	@echo "=== input() is a failure-typed result (two lines piped in, on both backends) ==="
	@printf '  %-42s' "test_input.ady (python = nim)"; \
	    printf 'ann\nlee\n' | $(EXDIR)/test_input > $(TMPDIR)/ady_input_nim.out 2>&1; \
	    $(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(EXDIR)/test_input.ady > $(TMPDIR)/ady_input.py; \
	    printf 'ann\nlee\n' | $(PYTHON) $(TMPDIR)/ady_input.py > $(TMPDIR)/ady_input_py.out 2>&1; \
	    if grep -q 'test_input OK' $(TMPDIR)/ady_input_nim.out && cmp -s $(TMPDIR)/ady_input_nim.out $(TMPDIR)/ady_input_py.out; then \
	        echo OK; else echo FAIL; diff $(TMPDIR)/ady_input_nim.out $(TMPDIR)/ady_input_py.out; exit 1; fi

	@echo "=== CFMU examples (fed their own samples) ==="
	@printf '  %-42s' "CFMU/Tstatus_monitor.ady"; \
	    $(EXDIR)/CFMU/Tstatus_monitor < $(EXDIR)/CFMU/tstatus_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }
	@# Vcheck takes a log file rather than stdin; a path that exists is used
	@# as-is, which is what makes it runnable here.
	@printf '  %-42s' "CFMU/Vcheck_coded_flight.ady"; \
	    $(EXDIR)/CFMU/Vcheck_coded_flight $(EXDIR)/CFMU/vcheck_sample.txt >/dev/null 2>&1 \
	        && echo OK || { echo FAIL; exit 1; }

	@echo "=== Examples fed their own samples, against their awk / sh twins ==="
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
	@# builds its own fixture under $$TMPDIR, so the report is the same every
	@# run -- and the filename with a space in it is the point of the check.
	@printf '  %-42s' "sh_janitor.ady"; \
	    $(EXDIR)/sh_janitor >/dev/null 2>&1 \
	        && test -f "$(TMPDIR)/ady_janitor/quiet service.log.gz" \
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
	@for input in $(TMPDIR)/ady_config_check/app.conf $(EXDIR)/config_check_other.conf; do \
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
	        && test -f "$(TMPDIR)/sh_janitor_sh/quiet service.log" \
	        && test -f "$(TMPDIR)/sh_janitor_sh/editor backup~" \
	        && echo OK || { echo FAIL; cat $(TMPDIR)/ady_janitor_sh.out; exit 1; }
	@echo "=== The documents' snippets ==="
	@# The documents' own snippets, so that what DOCS/*.md quotes is code
	@# that ran rather than code that was written down. check-quotes below
	@# is what ties each block to the file it came from.
	@for f in DOC/awk_snippets.ady DOC/why_snippets.ady DOC/why_alias_snippets.ady DOC/string_snippets.ady DOC/type_snippets.ady; do \
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

	$(vi_tests)

	@# lispy wants a terminal for its prompt, but it can be run without one.
	@echo "=== lispy ==="
	@# lispy checks itself before it offers a prompt, so an empty stdin runs
	@# the whole suite and then leaves at EOF. It went unbuilt for a long
	@# while without anyone noticing, which is the argument for it being here.
	@printf '  %-42s' "TOOLS/LISPY/lispy.ady (self-test)"; \
	    $(TOOLDIR)/LISPY/lispy < /dev/null 2>&1 \
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
	@# Nim only: Tcheck_tact is split into modules (LIBS/), and the Python
	@# backend cannot follow a nimport.
	@echo "=== Tcheck_tact -focus changes: the tests the Tlogs report failing ==="
	@$(TCDIR)/test/run_new_failures_tests.sh $(TCDIR)/Tcheck_tact
	@echo "=== Tcheck_tact -focus IP/OP/SIP: what it looked for and did not find ==="
	@$(TCDIR)/test/run_missing_tests.sh $(TCDIR)/Tcheck_tact
	@# Each of Tcheck_tact's modules carries its own tests, under
	@# `if __name__ == "__main__"`: built alone, the module runs them.
	@echo "=== Tcheck_tact's modules, their own tests ==="
	@for m in tcheck_common tlog replays baselines csystem_log changes_report; do \
	    printf '  %-42s' "LIBS/$$m.ady"; \
	    $(ADY2NIM) c $(TCDIR)/LIBS/$$m.ady >/dev/null 2>&1 \
	        && CM_ENV_ID='G!31.IP.L8' $(TCDIR)/LIBS/$$m >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done
	@# make_comparable, which Tcheck_tact runs on the logs it compares:
	@# the volatile parts replaced, in place.
	@echo "=== make_comparable ==="
	@printf '  %-42s' "make_comparable (pid, hex address)"; \
	    f=$$(mktemp) && printf 'started pid 4242\ncrash at 0x7ffd1234\n' > $$f && \
	    $(TCDIR)/make_comparable $$f 30.0.0.1 2>/dev/null && \
	    got=$$(cat $$f); rm -f $$f; \
	    if [ "$$got" = "$$(printf 'started pid <PID>\ncrash at <TRACE>')" ]; then echo OK; \
	    else echo "FAIL: $$got"; exit 1; fi
	@# Treport.ksh, the standalone ksh translation: the same checks
	@# Under ksh93, and under zsh in ksh emulation -- zsh run as ksh, which
	@# is what /bin/ksh is on some machines.
	@# The changes tests and the new-failures ones -- bar -exit-code, which
	@# Treport.ksh has not.
	@echo "=== Treport.ksh, the same checks (ksh93) ==="
	@if command -v ksh >/dev/null 2>&1 && ksh -c '[ -z "$$ZSH_VERSION" ]' 2>/dev/null; then \
	    $(TCDIR)/test/run_changes_tests.sh $(TCDIR)/test/ksh_treport && \
	    NO_EXIT_CODE=1 $(TCDIR)/test/run_new_failures_tests.sh $(TCDIR)/test/ksh_treport; \
	else echo "  SKIP (no ksh93)"; fi
	@echo "=== Treport.ksh, the same checks (zsh as ksh) ==="
	@if command -v zsh >/dev/null 2>&1; then \
	    d=$$(mktemp -d) && ln -s "$$(command -v zsh)" $$d/ksh && \
	    KSH=$$d/ksh $(TCDIR)/test/run_changes_tests.sh $(TCDIR)/test/ksh_treport && \
	    KSH=$$d/ksh NO_EXIT_CODE=1 $(TCDIR)/test/run_new_failures_tests.sh $(TCDIR)/test/ksh_treport; \
	    rc=$$?; rm -rf $$d; [ $$rc -eq 0 ]; \
	else echo "  SKIP (no zsh)"; fi
	@# Tcheckout.ady, on both backends, and Tcheckout.ksh: the same checks.
	@echo "=== Tcheckout: one file of a submodule not checked out ==="
	@$(TCDIR)/test/run_checkout_tests.sh $(TCDIR)/Tcheckout
	@echo "=== Tcheckout, the same checks on the Python backend ==="
	@$(PYTHON) $(CURDIR)/TO_PYTHON/ady2py.py $(TCDIR)/Tcheckout.ady > $(TCDIR)/test/Tcheckout_py.py
	@printf '#!/bin/sh\nexec $(PYTHON) %s "$$@"\n' "$(TCDIR)/test/Tcheckout_py.py" \
	    > $(TCDIR)/test/tcheckout_py && chmod +x $(TCDIR)/test/tcheckout_py
	@$(TCDIR)/test/run_checkout_tests.sh $(TCDIR)/test/tcheckout_py
	@rm -f $(TCDIR)/test/Tcheckout_py.py $(TCDIR)/test/tcheckout_py
	@echo "=== Tcheckout.ksh, the same checks ==="
	@$(TCDIR)/test/run_checkout_tests.sh $(TCDIR)/Tcheckout.ksh

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
	@# The editors' highlighting of regex literals against the transpiler's
	@# tokenizer: VS Code and Emacs must see a regex exactly where it does,
	@# over every .ady here, and no quote inside one may open a string.
	@# SKIPs, saying what to install, without node's vscode-textmate or
	@# emacs's nim-mode.
	@echo "=== Editor highlighting of regex literals ==="
	@PYTHON=$(PYTHON) sh $(CURDIR)/LSP/test/run_editor_tests.sh

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
