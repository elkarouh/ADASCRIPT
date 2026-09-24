#!/bin/sh
# Tblame against a small git tree built here, standing in for an NM
# workspace. No real NM/CM site is required: Psort and where_workspace are
# stubbed on PATH, exactly enough for the paths this test exercises.
set -e

TBLAME=${1:-../Tblame}
[ -x "$TBLAME" ] || { echo "SKIP (Tblame not built)"; exit 0; }
TBLAME=$(cd "$(dirname "$TBLAME")" && pwd)/$(basename "$TBLAME")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

# --- a tiny "NM" workspace: one repo at NM/sysA/subA, three commits ------
NM=$WORK/NM
REPO=$NM/sysA/subA
mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email a@b.test
git -C "$REPO" config user.name "Alice A"

printf 'line1\nline2\nline3\n' > "$REPO/fileA.txt"
# A /cm/ot/.../build_X/sources/<file> context path only excludes the single
# build_X segment (see match_context_path's own column comments); the rest,
# "sources/<file>", is the captured relative path -- so an alternate repo
# is expected to mirror a sources/ layout, not a flat one. Only the
# context-path/-alternate check below needs this; the workspace-path
# checks pass an absolute path straight through and never touch it.
mkdir -p "$REPO/sources"
cp "$REPO/fileA.txt" "$REPO/sources/fileA.txt"
git -C "$REPO" add fileA.txt sources/fileA.txt
GIT_AUTHOR_DATE=2024-01-01T00:00:00 GIT_COMMITTER_DATE=2024-01-01T00:00:00 \
    git -C "$REPO" commit -q -m "SC-1001 initial fileA"
git -C "$REPO" tag TESTBASELINE

git -C "$REPO" config user.name "Bob B"
printf 'line1\nline2-changed\nline3\nline4\n' > "$REPO/fileA.txt"
git -C "$REPO" add fileA.txt
GIT_AUTHOR_DATE=2024-02-01T00:00:00 GIT_COMMITTER_DATE=2024-02-01T00:00:00 \
    git -C "$REPO" commit -q -m "SC-1002 tweak fileA"

printf 'x1\nx2\nx3\n' > "$REPO/fileB.txt"
git -C "$REPO" add fileB.txt
GIT_AUTHOR_DATE=2024-03-01T00:00:00 GIT_COMMITTER_DATE=2024-03-01T00:00:00 \
    git -C "$REPO" commit -q -m "SC-2001 SC-2002 SC-2003 multi-ticket fileB"

# The ksh original checks "{alternate}/.git" at the top level (an alternate
# is a single repo) but revision_of_context_file checks
# "{alternate}/{system}/{subsystem}/.git" (an alternate is a multi-repo
# root) -- two different shapes for the same variable, in two different
# functions, neither of which this translation invented or could resolve
# without the real site to check against. A second, unrelated repo at the
# NM root satisfies the first check without disturbing the per-subsystem
# repo the second one (and every workspace-path query above) actually uses.
git -C "$NM" init -q

# --- site tools that Tblame shells out to, stubbed just enough ----------
mkdir -p "$WORK/bin"
# Psort's real job is topological/reverse-chronological sorting of context
# paths; here it only needs to hand the one candidate path straight back so
# revision_of_context_file's own regex + baseline check can find it.
cat > "$WORK/bin/Psort" <<'EOF'
#!/bin/sh
cat
EOF
chmod +x "$WORK/bin/Psort"

BASE_PATH=$PATH
PATH=$WORK/bin:$PATH
export PATH
CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY=$NM
export CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY

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

INPUT=$WORK/input.txt
cat > "$INPUT" <<EOF
$NM/sysA/subA/fileA.txt:1:some info A
$NM/sysA/subA/fileA.txt:2:info B
$NM/sysA/subA/fileA.txt:2:info B again (duplicate line+file)
$NM/sysA/subA/fileA.txt:4:info D
this line does not match anything
$NM/sysA/subA/fileB.txt:2:info X
EOF

# --- workspace-path branch, default columns ------------------------------
# line1 is unchanged since the first commit (Alice); line2/line4 are Bob's
# second commit; the unmatched line is buffered and printed right before
# the row that follows it; fileB's line 2 carries three SC tickets.
OUT=$("$TBLAME" < "$INPUT")
check "line1 -> first commit's author"       "Alice A" "$(printf '%s\n' "$OUT" | sed -n '1p' | awk '{print $3, $4}')"
check "line2 -> second commit's author"      "Bob B"   "$(printf '%s\n' "$OUT" | sed -n '2p' | awk '{print $3, $4}')"
check "duplicate line request, same result"  "$(printf '%s\n' "$OUT" | sed -n '2p')" "$(printf '%s\n' "$OUT" | sed -n '3p')"
check "line4, same commit as line2 (cache)"  "Bob B"   "$(printf '%s\n' "$OUT" | sed -n '4p' | awk '{print $3, $4}')"
check "unmatched line passed through"        1 "$(printf '%s\n' "$OUT" | grep -c '^this line does not match anything$')"
check "multi-ticket sc_hint shows the count" "SC-2001(+2)" "$(printf '%s\n' "$OUT" | sed -n '7p' | awk '{print $2}')"

# --- full column set: the ksh original's sc_hint/output-array name
#     collision crashed here (see the module docstring); Adascript has no
#     such collision to hit.
FULL="checksum date user sc_hint sc_first sc_all file_original file_name file_workspace reference reference_blame"
FULL_OUT=$("$TBLAME" $FULL < "$INPUT")
check "full column set doesn't crash"        6 "$(printf '%s\n' "$FULL_OUT" | grep -c '.')"
check "sc_all lists every ticket"            "SC-2001,SC-2002,SC-2003" "$(printf '%s\n' "$FULL_OUT" | sed -n '7p' | grep -o 'SC-2001,SC-2002,SC-2003')"

# --- -filter_unmatched drops the pass-through line -----------------------
check "-filter_unmatched drops it" 0 \
    "$("$TBLAME" -filter_unmatched user < "$INPUT" | grep -c 'does not match')"

# --- -since drops everything before the cutoff ---------------------------
# 1709251200 is the fileB commit's own timestamp (2024-03-01): everything
# from the two earlier commits on fileA is strictly before it and dropped,
# fileB's row (same committer name, third commit) is kept.
SINCE_OUT=$("$TBLAME" -since 1709251200 user reference < "$INPUT")
check "-since keeps the later commit's row" 1 \
    "$(printf '%s\n' "$SINCE_OUT" | grep -c 'info X')"
check "-since drops the earlier ones" 0 \
    "$(printf '%s\n' "$SINCE_OUT" | grep -c 'info B\|info D\|some info A')"

# --- "- FILENAME": read files directly instead of stdin -----------------
check "- FILENAME reads the file's own lines" 4 \
    "$("$TBLAME" reference_blame - "$REPO/fileA.txt" | grep -c '| line')"

# --- context path (/cm/ot/...) through -alternate + a git tag -----------
# TESTBASELINE was tagged on the FIRST commit, before line 2 became
# "line2-changed" -- a distinct blame result from the workspace-path
# queries above proves the revision was actually resolved and used, not
# just defaulted to HEAD.
CM_INPUT=$WORK/cm_input.txt
printf '%s\n' "/cm/ot/sysA/subA!TESTBASELINE/build_E1/sources/fileA.txt:2:cm info" > "$CM_INPUT"
# -alternate takes the NM repository ROOT, not a specific subsystem repo --
# Tblame joins it with the path's own system/subsystem (sysA/subA here).
CM_OUT=$("$TBLAME" -alternate "$NM" user reference_blame < "$CM_INPUT")
check "context path resolves the tagged revision" "Alice A | line2" "$CM_OUT"

# --- a context path whose subsystem is not checked out -------------------
# sysB/subB has no repo under the alternate root. Asking whether
# "<root>/sysB/subB/.git" is readable must answer "no" and move on, as the
# ksh original's [[ -r ... ]] does -- not die with "No such file or
# directory", which the Nim build did when -r went through
# getFilePermissions.
printf '%s\n' "/cm/ot/sysB/subB!TESTBASELINE/build_E1/sources/f.txt:1:x" > "$CM_INPUT"
set +e
"$TBLAME" -alternate "$NM" user < "$CM_INPUT" > "$WORK/nocheckout.out" 2> "$WORK/nocheckout.err"
rc=$?
set -e
check "missing subsystem: exits cleanly"   0 "$rc"
check "missing subsystem: no crash"        0 "$(grep -c 'unhandled exception\|Traceback' "$WORK/nocheckout.err")"
check "missing subsystem: says it, once"   1 "$(grep -c 'Could not retrieve blame data' "$WORK/nocheckout.err")"

echo
if [ "$fails" -eq 0 ]; then
    echo "All checks passed."
else
    echo "$fails check(s) FAILED."
fi
PATH=$BASE_PATH
[ "$fails" -eq 0 ] || exit 1
