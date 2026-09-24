#!/bin/sh
# Tcheck_tact -focus changes against a CM tree built here: a TACT baseline,
# the CFMUTEST changes report Psort points it at, and one view build.
set -e

TCHECK=${1:-../Tcheck_tact}
[ -x "$TCHECK" ] || { echo "SKIP (Tcheck_tact not built)"; exit 0; }
TCHECK=$(cd "$(dirname "$TCHECK")" && pwd)/$(basename "$TCHECK")
HERE=$(cd "$(dirname "$0")" && pwd)

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

OT=$WORK/cm/ot
mkdir -p "$OT/TACT/TACT_CONFIG.30.0.0.9" "$OT/TACT/TACT_CONFIG.30.0.0.8" "$OT/CFMUTEST/baseline_reports" "$WORK/bin"
cp "$HERE/changes_report.sample" "$OT/CFMUTEST/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.30.0.0.8.changes_report"
# alice's view was built; nobody else's
mkdir -p "$OT/TACT/test_reports/TACT.TACT_CONFIG.ALICE.FIX_B-G!31.IP.L8" \
         "$OT/TACT/test_reports/TACT.TACT_CONFIG.30.0.0.3-G!31.IP.L8"

# Psort -b answers the CFMUTEST baseline built on the TACT one it is fed.
cat > "$WORK/bin/Psort" <<'PSORT'
#!/bin/sh
read -r tact
[ "$1" = "-b" ] && [ "$tact" = "/cm/ot/TACT/TACT_CONFIG.30.0.0.9" ] || exit 1
echo "/cm/ot/CFMUTEST/CFMUTEST_CONFIG!30.0.0.8"
PSORT
chmod +x "$WORK/bin/Psort"
PATH=$WORK/bin:$PATH
TCHECK_CM_OT=$OT
CONTEXT_CM_BASELINE=x
export PATH TCHECK_CM_OT CONTEXT_CM_BASELINE

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

OUT=$("$TCHECK" -focus changes 30.0.0.9)
users() { printf '%s\n' "$OUT" | sed -n 's/^=* Files committed by user \([^ ]*\) =*$/\1/p' | tr '\n' ' '; }
section() {  # the lines under one user's heading
    printf '%s\n' "$OUT" | awk -v u="$1" '/^=====/ { on = index($0, "user " u " ") > 0; next } on'
}

check "committers, in order of first appearance" "alice bob carol " "$(users)"
check "integration-only change not listed"       0 "$(printf '%s\n' "$OUT" | grep -c 'a.doc' || true)"
check "changed directory not listed"             0 "$(printf '%s\n' "$OUT" | grep -c 'TACT_CONFIG/sources/$' || true)"
check "alice: one entry for b, not one per version" 1 "$(section alice | grep -c '^FILE CHANGED: .*/b\.adb$')"
check "bob credited with b too"                  1 "$(section bob | grep -c '^FILE CHANGED: .*/b\.adb$')"
check "the diff shown for a changed file"        'DIFF        :#emacs:(ediff-files "/cm/vobs/t1/TACT/TACT_CONFIG/sources/b.adb@@/main/8" "/cm/vobs/t1/TACT/TACT_CONFIG/sources/b.adb@@/main/9")' \
    "$(section alice | grep '^DIFF')"
check "the view it came from"                    'FROM VIEW   : TACT.TACT_CONFIG.30.0.0.3.alice.fix_b/1 REVIEWED_BY_bob REVIEW_OK="Yes"' \
    "$(section alice | grep '^FROM VIEW')"
check "alice's view build, found"                1 "$(section alice | grep -c '^VIEW BUILD DIR: .*TACT.TACT_CONFIG.ALICE.FIX_B-G!31.IP.L8$')"
check "...next to the reference baseline's"     1 "$(section alice | grep -c '^REFERENCE BASELINE DIR: .*TACT.TACT_CONFIG.30.0.0.3-G!31.IP.L8$')"
check "...with the ediff between their failures" 1 "$(section alice | grep -c '^(ediff-files ".*30.0.0.3-G!31.IP.L8/general.results.failed-in" ".*FIX_B-G!31.IP.L8/general.results.failed-in")$')"
check "bob's view has no build"                  1 "$(section bob | grep -c '^NO VIEW BUILD FOUND FOR THIS VIEW$')"
check "an added file: its path, not its version" "FILE ADDED: /cm/vobs/i1/IFPS/CUA_IDL/sources/new_thing.ads" \
    "$(section carol | grep '^FILE ADDED')"
check "carol: added and changed, no DIFF for added" "FILE ADDED FILE CHANGED DIFF" \
    "$(section carol | grep -o '^FILE [A-Z]*\|^DIFF' | tr '\n' ' ' | sed 's/ $//')"
check "TOOL.COMMON merges are integration ones"  0 "$(printf '%s\n' "$OUT" | grep -c 'tool.ksh' || true)"
check "a changed directory's merges credit nobody" 0 "$(section carol | grep -c 'b\.adb' || true)"
check "removals, with no view, listed apart"     "FILE DELETED: /cm/vobs/i1/IFPS/CUA_IDL/sources/old_thing.ads
FILE DELETED: /cm/vobs/i1/IFPS/CUA_IDL/sources/old_thing.adb" \
    "$(printf '%s\n' "$OUT" | sed -n '/no view recorded/,/^$/p' | grep '^FILE')"
check "ends with the report's emacs link"        1 "$(printf '%s\n' "$OUT" | grep -c 'find-file ".*CFMUTEST.CFMUTEST_CONFIG.30.0.0.8.changes_report"')"

# --- when there is nothing to report on, it says so ----------------------
check "no CFMUTEST baseline: says so"            1 "$("$TCHECK" -focus changes 30.0.0.8 2>&1 | grep -c 'Psort -b names no CFMUTEST baseline for TACT_CONFIG.30.0.0.8' || true)"
rm "$OT/CFMUTEST/baseline_reports/"*
check "no report: says so"                       1 "$("$TCHECK" -focus changes 30.0.0.9 2>&1 | grep -c 'no changes report for CFMUTEST_CONFIG 30.0.0.8' || true)"

echo
if [ "$fails" -eq 0 ]; then
    echo "All checks passed."
else
    echo "$fails check(s) FAILED."
fi
[ "$fails" -eq 0 ] || exit 1
