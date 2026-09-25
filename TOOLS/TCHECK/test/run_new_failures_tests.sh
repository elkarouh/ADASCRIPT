#!/bin/sh
# Tcheck_tact -focus changes: the newly failed tests, each once, with the
# build type and subtype(s) it fails in -- against a CM tree built here:
# two baselines' IP and OP builds and their Tlogs. Tcheck_tact only;
# Treport.ksh lists the changes alone.
set -e

TCHECK=${1:-../Tcheck_tact}
[ -x "$TCHECK" ] || { echo "SKIP (Tcheck_tact not built)"; exit 0; }
TCHECK=$(cd "$(dirname "$TCHECK")" && pwd)/$(basename "$TCHECK")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

OT=$WORK/cm/ot
# tlog BASELINE BUILD SUBTYPE CRASHED FAILING: a Tlog as Tlog writes one --
# its sections each under a row of dots, those Tcheck_tact reads among
# others it does not -- with the CRASHED and FAILING tests (space-separated
# names) in their sections.
tlog() {
    d="$OT/TACT/TACT_CONFIG.$1/build_G!31.$2.L8/saved_logs/tacot_corico.LATEST/TACT_REGRESS_LOGS/LATEST"
    bl=$1 sub=$3
    mkdir -p "$d"
    {
        echo "========================================================================================"
        echo " HEAVYTEST  : $3"
        echo " TACT_CONFIG: $1"
        echo "260910.171934: Tlog: INFO: Starting: Tlog -d /logs/logging-$3 -w"
        echo
        set -- $4 "|" $5
        n=0; for t; do [ "$t" = "|" ] && break; n=$((n + 1)); done
        echo " .............. Crashed Tests : nb = $n"
        echo
        for t; do shift; [ "$t" = "|" ] && break; echo "CRASHED $t  signal 11 #emacs:(find-file \"/logs/$t\")"; done
        echo
        echo " .............. mrun failing (from separate Tlog) : nb = 0"
        echo
        echo " .............. Check build of TACT.TACT_CONFIG : nb = 2"
        echo
        echo "260910.172150: Tlog: WARNING: Check potential errors below in section #emacs:(search-forward \"Check build of TACT.TACT_CONFIG\")"
        echo
        echo " .............. New tests failing : nb = $#"
        echo
        for t; do echo "FAILED $t   $bl   ok:9    nok:1    #emacs:(progn(find-file \"/logs/out\")(narrow-to-test \"$t\"))"; done
        [ $# -gt 0 ] && echo "[...] all $# lines in file \"new_failing.txt\" #emacs:(find-file \"/logs/new_failing.txt\")"
        echo
        echo " .............. Tests still failing : nb = 0"
        echo
        echo "Worse : nb = 0"
        echo "Same : nb = 0"
        echo "Better : nb = 0"
        echo
        echo " .............. Following tests are now successful (maybe they are new) : nb = 0"
        echo
        echo " .............. Following tests contain known failures : nb = 1"
        echo
        echo "KNOWN NORMAL FAILURE: test_known.el  a known failure increased of 1"
        echo "[...] all 1 lines in file \"known_errors_file.txt\" #emacs:(find-file \"/logs/known.txt\")"
        echo
        echo " .............. Errors in log files."
        echo
        echo " .............. Tlog summary."
        echo
        echo "TLOG SUMMARY: FAILING=1(+1) NOK=1(+1) KNOWN=1 KNOWN_ASSRT=0 SUCCESS=10/100"
        echo "260910.172352: Tlog: INFO: Tlog end"
    } > "$d/Tlog-$sub.log"
}
# 30.0.0.9: alpha newly fails in IP in and mono, gamma crashed, beta still
# fails as it did in 30.0.0.8, and delta fails in an OP build that had no
# Tlog before. Around them, the lines of the sections Tcheck_tact does not
# read, and those in its own that name no test, whose second words --
# mrun, Check, Tlog:, all -- were once listed as new failures.
tlog 30.0.0.9 IP in test_gamma.el "test_alpha.el test_beta.el"
tlog 30.0.0.9 IP mono "" test_alpha.el
tlog 30.0.0.9 OP assert "" test_delta.el
tlog 30.0.0.8 IP in "" test_beta.el
# 30.0.0.10: the same failures as 30.0.0.9 -- nothing new
tlog 30.0.0.10 IP in test_gamma.el "test_alpha.el test_beta.el"
tlog 30.0.0.10 IP mono "" test_alpha.el

TCHECK_CM_OT=$OT
CONTEXT_CM_BASELINE=x
HOME=$WORK            # Tcheck_tact appends to ~/.tcheck_history
export TCHECK_CM_OT CONTEXT_CM_BASELINE HOME

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
# the NEWLY FAILED TESTS section of Tcheck_tact's output for ARGS
section() {
    "$TCHECK" -no-color "$@" 2>/dev/null | sed -n '/^NEWLY FAILED TESTS/,/^$/p' | grep . || true
}

check "each test once, with its builds; tests only" "NEWLY FAILED TESTS vs 30.0.0.8
  test_alpha.el  IP in, IP mono
  test_gamma.el  IP in
  test_delta.el  OP assert" "$(section -focus changes 30.0.0.9)"
check "-short keeps it"                          "$(section -focus changes 30.0.0.9)" "$(section -focus changes -short 30.0.0.9)"
check "none new: says so"                        "NEWLY FAILED TESTS vs 30.0.0.9
  No new failures compared to 30.0.0.9" "$(section -focus changes -short 30.0.0.10)"
set +e
"$TCHECK" -no-color -exit-code -focus changes -short 30.0.0.9 >/dev/null 2>&1; rc_new=$?
"$TCHECK" -no-color -exit-code -focus changes -short 30.0.0.10 >/dev/null 2>&1; rc_none=$?
set -e
check "-exit-code: 1 with new failures, 0 without" "1 0" "$rc_new $rc_none"

echo
if [ $fails -eq 0 ]; then echo "All checks passed."; else echo "$fails check(s) FAILED."; exit 1; fi
