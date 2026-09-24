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
# alice's branch was built, against the baseline before this one; bob's was not
mkdir -p "$OT/TACT/test_reports/TACT.TACT_CONFIG.ALICE.FIX_B-G!31.IP.L8" \
         "$OT/TACT/test_reports/TACT.TACT_CONFIG.30.0.0.8-G!31.IP.L8"

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
entry() {  # the FILE line naming $2 in user $1's section, and the lines under it
    section "$1" | awk -v f="$2" '/^-----/ { on = 0 } /^FILE / { on = index($0, f) > 0 } on'
}

check "committers, in order of first appearance" "carol alice bob " "$(users)"
check "a change under its branch's merge"        "FILE CHANGED: CFMUTEST/CFMUTEST_CONFIG/special_files/mail_list" \
    "$(section carol | grep '^FILE')"
check "baseline syncs are nobody's branch"       1 "$(entry alice b.adb | grep -c '^COMMITS     : c3fb81031 13e00da4a bc399bc5f$')"
check "one entry per file, every commit in it"   1 "$(section alice | grep -c '^FILE CHANGED: TACT/UIF/sources/b.adb$')"
check "its tickets, once each"                   "TICKETS     : SC-2" "$(entry alice b.adb | grep '^TICKETS')"
check "the nearest branch wins: bob's b.adb"     "COMMITS     : 33340af6c" "$(entry bob b.adb | grep '^COMMITS')"
check "...and bob's added file"                  "FILE ADDED: TACT/UIF/sources/c.ads" "$(section bob | grep '^FILE ADDED')"
check "a branch merged in two sections, once"    1 "$(section alice | grep -c '^FROM BRANCH : alice.fix_b$')"
check "removed and added, by path"               "FILE DELETED: IFPS/OPIF_LIB/sources/old_thing.ads
FILE ADDED: IFPS/OPIF_LIB/sources/new_thing.ads" "$(section alice | grep '^FILE DELETED\|^FILE ADDED')"
check "alice's branch build, found"              1 "$(section alice | grep -c '^VIEW BUILD DIR: .*TACT.TACT_CONFIG.ALICE.FIX_B-G!31.IP.L8$')"
check "...next to the previous baseline's"       1 "$(section alice | grep -c '^REFERENCE BASELINE DIR: .*TACT.TACT_CONFIG.30.0.0.8-G!31.IP.L8$')"
check "...with the ediff between their failures" 1 "$(section alice | grep -c '^(ediff-files ".*30.0.0.8-G!31.IP.L8/general.results.failed-in" ".*FIX_B-G!31.IP.L8/general.results.failed-in")$')"
check "bob's branch has no build"                1 "$(section bob | grep -c '^NO VIEW BUILD FOUND FOR THIS BRANCH$')"
check "under an integration merge only: listed apart" "FILE DELETED: IFPS/OPIF_LIB/sources/Pmake.out" \
    "$(printf '%s\n' "$OUT" | sed -n '/no branch merged above them/,/^$/p' | grep '^FILE')"
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
