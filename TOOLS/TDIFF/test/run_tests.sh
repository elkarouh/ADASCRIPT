#!/bin/sh
# Tdiff against a small NM-shaped superproject built here: four submodules
# at <system>/<subsystem>, two workspace baselines (superproject commits),
# and the NM baselines 30.0.0.1 and 30.0.0.2 as tags inside each submodule.
set -e

TDIFF=${1:-../Tdiff}
TBLAME=${2:-../../TBLAME/Tblame}
[ -x "$TDIFF" ] || { echo "SKIP (Tdiff not built)"; exit 0; }
TDIFF=$(cd "$(dirname "$TDIFF")" && pwd)/$(basename "$TDIFF")
[ -x "$TBLAME" ] && TBLAME=$(cd "$(dirname "$TBLAME")" && pwd)/$(basename "$TBLAME")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

as() {  # as "Name" git ARGS... -- author and committer both Name
    name=$1; shift
    GIT_AUTHOR_NAME="$name" GIT_COMMITTER_NAME="$name" \
    GIT_AUTHOR_EMAIL=x@y.test GIT_COMMITTER_EMAIL=x@y.test \
    GIT_AUTHOR_DATE=$DATE GIT_COMMITTER_DATE=$DATE "$@"
}

# --- the subsystems, as standalone repositories first --------------------
DATE=2024-01-01T00:00:00
for s in subA subB subC subD; do
    git init -q "$WORK/src/$s"
    printf 'l1\nl2\nl3\n' > "$WORK/src/$s/f.txt"
    git -C "$WORK/src/$s" add f.txt
    as "Alice A" git -C "$WORK/src/$s" commit -q -m "SC-1 initial $s"
done

# --- the superproject: NM/<system>/<subsystem> ---------------------------
NM=$WORK/NM
git init -q "$NM"
for p in sysA/subA sysA/subB sysB/subC sysB/subD; do
    git -C "$NM" -c protocol.file.allow=always submodule add -q "$WORK/src/${p#*/}" "$p"
done
as "Alice A" git -C "$NM" commit -q -m "Baseline workspace 'one'."
for p in sysA/subA sysA/subB sysB/subC sysB/subD; do git -C "$NM/$p" tag 30.0.0.1; done

# --- what the second baseline changes ------------------------------------
# subA: two commits, three tickets, two people; subC: a deletion only;
# subD: a change, in a submodule that ends up not checked out; subB: none.
DATE=2024-02-01T00:00:00
printf 'l1\nl2-new\nl3\nl4\n' > "$NM/sysA/subA/f.txt"
as "Alice A" git -C "$NM/sysA/subA" commit -q -am "SC-2 SC-3 tweak"
DATE=2024-03-01T00:00:00
printf 'l0\nl1\nl2-new\nl3\nl4\n' > "$NM/sysA/subA/f.txt"
as "Bob B" git -C "$NM/sysA/subA" commit -q -am "SC-4 prepend"
printf 'l1\nl3\n' > "$NM/sysB/subC/f.txt"
as "Carol C" git -C "$NM/sysB/subC" commit -q -am "SC-5 drop l2"
printf 'l1\nl2\nl3\nd4\n' > "$NM/sysB/subD/f.txt"
as "Dan D" git -C "$NM/sysB/subD" commit -q -am "SC-7 extend"
git -C "$NM" add sysA sysB
as "Bob B" git -C "$NM" commit -q -m "Baseline workspace 'two'."
for p in sysA/subA sysA/subB sysB/subC sysB/subD; do git -C "$NM/$p" tag 30.0.0.2; done
git -C "$NM" submodule deinit -q sysB/subD

CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY=$NM
export CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY
# From outside the superproject, as a user would run it.
cd "$WORK"

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

LINES="$NM/sysA/subA/f.txt:1:l0
$NM/sysA/subA/f.txt:3:l2-new
$NM/sysA/subA/f.txt:5:l4"

# --- the default: the previous baseline against the checkout -------------
"$TDIFF" > "$WORK/out" 2> "$WORK/err"
check "default: the lines HEAD^..checkout adds"      "$LINES" "$(cat "$WORK/out")"
check "default: a deletion alone lists nothing"      0 "$(grep -c subC "$WORK/out" || true)"
check "default: says what is not checked out"        1 "$(grep -c 'not checked out, not listed: sysB/subD$' "$WORK/err")"
check "default: unchanged submodule not mentioned"   0 "$(grep -c subB "$WORK/out" "$WORK/err" | awk -F: '{s+=$2} END{print s}')"

# --- two superproject commits ---------------------------------------------
"$TDIFF" HEAD^ HEAD > "$WORK/out" 2> "$WORK/err"
check "HEAD^ HEAD: the same lines"                   "$LINES" "$(cat "$WORK/out")"
check "HEAD^ HEAD: warns Tblame blames the checkout" 1 "$(grep -c 'Tblame blames the checkout' "$WORK/err")"

# --- two NM baselines, tags in each submodule -----------------------------
"$TDIFF" 30.0.0.1 30.0.0.2 > "$WORK/out" 2> "$WORK/err"
check "baselines: the same lines"                    "$LINES" "$(cat "$WORK/out")"
check "baselines, one given: against the checkout"   "$LINES" "$("$TDIFF" 30.0.0.1 2>/dev/null)"

# --- -commits: who, when, which ticket ------------------------------------
"$TDIFF" -commits > "$WORK/out" 2> "$WORK/err"
check "-commits: one row per commit"                 3 "$(wc -l < "$WORK/out" | tr -d ' ')"
check "-commits: the multi-ticket one"               "2024.02.01 SC-2(+1) Alice A" \
    "$(grep 'SC-2 SC-3 tweak' "$WORK/out" | awk '{print $2, $3, $4, $5}')"
check "-commits: newest first, with its submodule"   "SC-4 Bob B sysA/subA | SC-4 prepend" \
    "$(sed -n 1p "$WORK/out" | cut -d' ' -f3- | tr -s ' ')"
check "-commits: a deletion is a commit too"         "SC-5 Carol C sysB/subC | SC-5 drop l2" \
    "$(grep subC "$WORK/out" | cut -d' ' -f3- | tr -s ' ')"

# --- uncommitted work in a checkout is part of "the checkout" -------------
printf 'l5\n' >> "$NM/sysA/subA/f.txt"
check "checkout: uncommitted line listed"            "$NM/sysA/subA/f.txt:6:l5" "$("$TDIFF" 2>/dev/null | tail -1)"
git -C "$NM/sysA/subA" checkout -q f.txt

# --- Tdiff | Tblame: who wrote each changed line --------------------------
if [ -x "$TBLAME" ]; then
    check "| Tblame: who wrote each line"            "Bob B | l0
Alice A | l2-new
Alice A | l4" "$("$TDIFF" 2>/dev/null | "$TBLAME" user reference_blame | tr -s ' ')"
fi

# --- what goes wrong, said plainly ----------------------------------------
set +e
"$TDIFF" 99.9.9.9 > "$WORK/out" 2> "$WORK/err"; rc=$?
set -e
check "unknown baseline: exits 1"                    1 "$rc"
check "unknown baseline: says to fetch the tags"     1 "$(grep -c 'fetch --tags' "$WORK/err")"

# A superproject commit recording a submodule commit that was never fetched.
GIT_INDEX_FILE=$WORK/index git -C "$NM" read-tree HEAD
GIT_INDEX_FILE=$WORK/index git -C "$NM" update-index --cacheinfo 160000,1234567890123456789012345678901234567890,sysA/subB
TREE=$(GIT_INDEX_FILE=$WORK/index git -C "$NM" write-tree)
UNFETCHED=$(as "Eve E" git -C "$NM" commit-tree -p HEAD -m "Baseline workspace 'three'." "$TREE")
"$TDIFF" HEAD "$UNFETCHED" > "$WORK/out" 2> "$WORK/err"
check "unfetched commit: says to fetch"              1 "$(grep -c '^.*sysA/subB: cannot compare .*git -C .*sysA/subB fetch)$' "$WORK/err")"
check "unfetched commit: nothing else listed"        "" "$(cat "$WORK/out")"

echo
if [ "$fails" -eq 0 ]; then
    echo "All checks passed."
else
    echo "$fails check(s) FAILED."
fi
[ "$fails" -eq 0 ] || exit 1
