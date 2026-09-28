#!/bin/sh
# Tcheck_tact -focus IP/OP/SIP when what it looks for is not there: it says
# so, and where it looked -- against a CM tree built here. It printed its
# TESTS heading and nothing else for a baseline without the build asked
# for, and did not say which Tlog a build "not ready yet" lacked.
set -e

TCHECK=${1:-../Tcheck_tact}
[ -x "$TCHECK" ] || { echo "SKIP (Tcheck_tact not built)"; exit 0; }
TCHECK=$(cd "$(dirname "$TCHECK")" && pwd)/$(basename "$TCHECK")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

OT=$WORK/cm/ot
BL=$OT/TACT/TACT_CONFIG.30.0.0.135
TCHECK_CM_OT=$OT
HOME=$WORK            # Tcheck_tact appends to ~/.tcheck_history
export TCHECK_CM_OT HOME

fails=0
check() {
    name=$1; want=$2; got=$3
    if [ "$want" = "$got" ]; then
        printf '  %-52s OK\n' "$name"
    else
        printf '  %-52s FAIL\n    want: %s\n    got:  %s\n' "$name" "$want" "$got"
        fails=$((fails + 1))
    fi
}
tests() { "$TCHECK" -no-color "$@" 2>/dev/null | sed -n '/^TESTS/,$p'; }

mkdir -p "$BL"
check "no build at all" "TESTS
No OP build in $BL
  it has no build_G!* directory" "$(tests -focus OP in -short 30.0.0.135)"

mkdir -p "$BL/build_G!31.IP.L8/saved_logs" "$BL/build_G!92.OP.L8/saved_logs"
check "builds, but not the one asked for" "TESTS
No OP build in $BL
  its builds: build_G!31.IP.L8
  set aside, variants Tcheck_tact does not read: build_G!92.OP.L8" "$(tests -focus OP in -short 30.0.0.135)"

mkdir -p "$BL/build_G!31.OP.L8/saved_logs"
check "the build, without the Tlog asked for" "TESTS
PROCESSING build_G!31.OP.L8 ...
\"OP in\" build not ready yet
  no Tlog at $BL/build_G!31.OP.L8/saved_logs/tacot_corico.LATEST/TACT_REGRESS_LOGS/LATEST/Tlog-in.log" "$(tests -focus OP in -short 30.0.0.135)"

check "a subtype not expected of it, when asked for" "TESTS
PROCESSING build_G!31.IP.L8 ...
\"IP lo\" build not ready yet
  no Tlog at $BL/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/TACT_REGRESS_LOGS/LATEST/Tlog-lo.log" "$(tests -focus IP lo -short 30.0.0.135)"

# -focus replay: the replay's log in the baseline, and its replay dir,
# looked for in the OP build's saved_logs -- replays run on the OP build,
# so launched in the IP build's environment too
CM_ENV_ID='G!31.IP.L8'
export CM_ENV_ID
replays() { "$TCHECK" -no-color "$@" 2>/dev/null | sed -n '/^REPLAYS/,$p'; }
check "no replay log" "REPLAYS
WARNING: no performance replay log in $BL
  looked for build_*OP*/saved_logs/Treplay_*.log" "$(replays -focus replay performance -short 30.0.0.135)"

SAMPLES=$(cd "$(dirname "$0")" && pwd)/samples
cp "$SAMPLES"/Treplay_*run_prequal*.log "$BL/build_G!31.OP.L8/saved_logs/"
check "another replay's log only" "REPLAYS
WARNING: no performance replay log in $BL
  looked for build_*OP*/saved_logs/Treplay_*.log
  its replays: run_prequal" "$(replays -focus replay performance -short 30.0.0.135)"

check "no replay dir: what, where, how far back" \
    "no performance replay dir: no $BL/build_G!31.OP.L8/saved_logs/replay_dir*TAC_LO3*/work/logging/LOGS, nor in the baselines before, back to 30.0.0.116" \
    "$("$TCHECK" -no-color -focus replay performance 30.0.0.135 2>/dev/null | grep "^no performance replay dir: no $BL/")"
check "and no line per baseline tried" "" \
    "$("$TCHECK" -no-color -focus replay performance 30.0.0.135 2>&1 >/dev/null | grep 'trying' || true)"

# -focus build_info: the summary of check_run_test_programs.log diffed with
# the previous baseline's -- which had no TACT_CONFIG style difference, and
# a SEVERE message fixed since; and the Csystem_build.log comparison, a command
# printed rather than meld opened
PREV=$OT/TACT/TACT_CONFIG.30.0.0.134
for bl in "$BL" "$PREV"; do
    mkdir -p "$bl/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/work"
done
cp "$SAMPLES/check_run_test_programs.log" "$BL/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/work/"
{ grep -v 'check of TACT_CONFIG scripts\|TACT_CONFIG_style_errors_test\|/TACT_CONFIG\.RESULT' "$SAMPLES/check_run_test_programs.log"
  echo '260923.225938: old_program: SEVERE: something fixed since'
} > "$PREV/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/work/check_run_test_programs.log"
# an older one in a test's LOGS directory, which is not the build's
STRAY="$PREV/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/work/logging-in/LOGS_a_test"
mkdir -p "$STRAY"
echo '260101.000000: check_run_test_programs_log: SEVERE: a stray log' > "$STRAY/check_run_test_programs.log"
touch -d '2020-01-01' "$STRAY/check_run_test_programs.log"
# the two files TACT_CONFIG VAR_CHECK's ediff compares, where it says, in
# the CM tree
KSH=$OT/TACT/TACT_CONFIG.30.0.0.134/build_G.31.IP.L8/sources/test
mkdir -p "$KSH" "$OT/TACT/TACT_CONFIG!30.0.0.134/build_G!31.IP.L8/user_output/KSH_STYLE_SCANNER"
cp "$SAMPLES/COMMON_CONFIG.BASELINE.RESULT.VAR_CHECK.txt" "$KSH/new_TACT_CONFIG_style_errors_test.BASELINE.RESULT.VAR_CHECK.txt"
cp "$SAMPLES/COMMON_CONFIG.RESULT.VAR_CHECK" "$OT/TACT/TACT_CONFIG!30.0.0.134/build_G!31.IP.L8/user_output/KSH_STYLE_SCANNER/TACT_CONFIG.RESULT.VAR_CHECK.30489"
info=$("$TCHECK" -no-color -f -focus build_info 30.0.0.135 2>/dev/null)
check "build_info: no Csystem_build.log, said so" \
    "  no $PREV/build_G!31.IP.L8/Csystem_build.log
  no $BL/build_G!31.IP.L8/Csystem_build.log" \
    "$(echo "$info" | sed -n '/^Compare Csystem_build.log:/,$p' | grep '^  no ')"
for bl in "$BL" "$PREV"; do echo 'Csystem ...' > "$bl/build_G!31.IP.L8/Csystem_build.log"; done
info=$("$TCHECK" -no-color -f -focus build_info 30.0.0.135 2>/dev/null)
check "build_info: the summary diffed with the previous one's" "Compare the check_run_test_programs.log summary with 30.0.0.134's:
  + 7 ksh style differences with the previous baseline:
  +   TACT_CONFIG VAR_CHECK
  +     ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
  +     ./sources/regression_testing.ksh  new used not defined: CM_HOST PERL_VERSION; gone defined not used: OLD_WORK_DIR
  - 6 ksh style differences with the previous baseline:
  -   1 SEVERE from old_program: something fixed since" \
    "$(echo "$info" | sed -n '/^Compare the check_run_test_programs/,/^Compare Csystem/p' | grep -v '^Compare Csystem' | grep -v '#emacs:')"
check "build_info: the newest log, not a test's older one" \
    "  #emacs:(progn(find-file \"$PREV/build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/work/check_run_test_programs.log\"))" \
    "$(echo "$info" | sed -n '/^Compare the check_run_test_programs/{n;p;}')"
check "build_info: the Csystem_build.log command, printed" \
    "  meld /tmp/reports/30.0.0.134_Csystem_build.log /tmp/reports/30.0.0.135_Csystem_build.log" \
    "$(echo "$info" | sed -n '/^Compare Csystem_build.log:/{n;p;}')"

# -focus build_info: who changed the scripts of a style difference, per the
# baseline's changes report -- none at first, and it says why; then one in
# which alice changed regression_testing.ksh, and nobody find_current_ops.ksh
style() { echo "$info" | sed -n '/^  7 ksh style differences/,/SEVERE from/p' | grep -v 'SEVERE\|#emacs:'; }
check "build_info: no changes report, said so" \
    "  7 ksh style differences with the previous baseline:
    who changed their scripts: WARNING: Psort -b names no CFMUTEST baseline for TACT_CONFIG.30.0.0.135
      ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
      ./sources/regression_testing.ksh  new used not defined: CM_HOST PERL_VERSION; gone defined not used: OLD_WORK_DIR" \
    "$(style)"
mkdir -p "$WORK/bin" "$OT/CFMUTEST/baseline_reports"
cat > "$WORK/bin/Psort" <<'PSORT'
#!/bin/sh
read -r tact
[ "$1" = "-b" ] && [ "$tact" = "/cm/ot/TACT/TACT_CONFIG.30.0.0.135" ] || exit 1
echo "/cm/ot/CFMUTEST/CFMUTEST_CONFIG!30.0.0.105"
PSORT
chmod +x "$WORK/bin/Psort"
cat > "$OT/CFMUTEST/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.30.0.0.105.changes_report" <<'REPORT'
===== Differences between TACT.TACT_CONFIG.30.0.0.134 and TACT.TACT_CONFIG.30.0.0.135
      Merge from <- 1234abcd alice.fix_env RELATED_CHANGES="SC-1 "
      changed 5678ef01:TACT/TACT_CONFIG/sources/regression_testing.ksh RELATED_CHANGES="SC-1 " review-ok: yes; reviewed-by: bob; review-date: 260925.101010;
REPORT
info=$(PATH=$WORK/bin:$PATH "$TCHECK" -no-color -f -focus build_info 30.0.0.135 2>/dev/null)
check "build_info: who changed each script, per the report" \
    "  7 ksh style differences with the previous baseline:
      ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
        not in the changes report
      ./sources/regression_testing.ksh  new used not defined: CM_HOST PERL_VERSION; gone defined not used: OLD_WORK_DIR
        changed by alice.fix_env: 5678ef01 SC-1, reviewed by bob on 260925.101010" \
    "$(style)"

echo
if [ $fails -eq 0 ]; then echo "All checks passed."; else echo "$fails check(s) FAILED."; exit 1; fi
