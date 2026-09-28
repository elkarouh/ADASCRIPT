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

echo
if [ $fails -eq 0 ]; then echo "All checks passed."; else echo "$fails check(s) FAILED."; exit 1; fi
