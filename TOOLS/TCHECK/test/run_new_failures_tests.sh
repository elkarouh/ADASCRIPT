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
# tlog BASELINE BUILD SUBTYPE: a Tlog, its sections from stdin
tlog() {
    d="$OT/TACT/TACT_CONFIG.$1/build_G!31.$2.L8/saved_logs/tacot_corico.LATEST/TACT_REGRESS_LOGS/LATEST"
    mkdir -p "$d"
    cat > "$d/Tlog-$3.log"
}
# 30.0.0.9: alpha newly fails in IP in and mono, gamma crashed, beta still
# fails as it did in 30.0.0.8, and delta fails in an OP build that had no
# Tlog before. The sections also hold lines naming no test -- their second
# word is mrun, Check, Tlog:, all: a test is an .el file.
tlog 30.0.0.9 IP in <<'TLOG'
Crashed Tests
  CRASH test_gamma.el      signal 11
  ==> mrun had crashed too
New tests failing
  FAIL  test_alpha.el      diff
  FAIL  test_beta.el       diff
  --> Check the logs of the failing tests
  In Tlog: /cm/ot/TACT/TACT_CONFIG.30.0.0.9/some.log
  ==> all 2 listed
Tests still failing
Tlog summary
TLOG
tlog 30.0.0.9 IP mono <<'TLOG'
New tests failing
  FAIL  test_alpha.el      diff
Tlog summary
TLOG
tlog 30.0.0.9 OP assert <<'TLOG'
New tests failing
  FAIL  test_delta.el      assertion
Tlog summary
TLOG
tlog 30.0.0.8 IP in <<'TLOG'
New tests failing
  FAIL  test_beta.el       diff
Tlog summary
TLOG
# 30.0.0.10: the same failures as 30.0.0.9 -- nothing new
for sub in in mono; do
    d="build_G!31.IP.L8/saved_logs/tacot_corico.LATEST/TACT_REGRESS_LOGS/LATEST"
    mkdir -p "$OT/TACT/TACT_CONFIG.30.0.0.10/$d"
    cp "$OT/TACT/TACT_CONFIG.30.0.0.9/$d/Tlog-$sub.log" "$OT/TACT/TACT_CONFIG.30.0.0.10/$d/"
done

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
