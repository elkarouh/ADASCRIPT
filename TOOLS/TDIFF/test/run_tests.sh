#!/bin/sh
# Tdiff against an alternate built here: two submodules, each tagged
# 30.0.0.1/30.0.0.2, one of them renaming a file between the two -- and
# Psort/list_subsystems/list_cfmutest_subsystems/readlink stubbed on PATH,
# so baseline resolution runs without the real NM site tools.
#
# Workspace-descriptor resolution (Cget_viewspace_name, Clsworkspace, the
# merge-base/integration-branch logic) is not exercised here: it was
# instead checked by hand against the real Tdiff.ksh and a real NM
# alternate, byte-for-byte identical on -name/-status and the checked-out
# tree content, across 77 changed files in a real baseline-to-baseline
# diff. There is no fixture for Clsworkspace's output format to stand on
# here.
set -e
unset NM_REPOSITORY_ALTERNATE CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY CONTEXT_CM_BASELINE

TDIFF=${1:-../Tdiff}
[ -x "$TDIFF" ] || { echo "SKIP (Tdiff not built)"; exit 0; }
TDIFF=$(cd "$(dirname "$TDIFF")" && pwd)/$(basename "$TDIFF")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

as() {  # as "Name" git ARGS... -- author and committer both Name
    name=$1; shift
    GIT_AUTHOR_NAME="$name" GIT_COMMITTER_NAME="$name" \
    GIT_AUTHOR_EMAIL=x@y.test GIT_COMMITTER_EMAIL=x@y.test \
    GIT_AUTHOR_DATE=$DATE GIT_COMMITTER_DATE=$DATE "$@"
}

# --- the alternate: two submodules, tagged 30.0.0.1 and 30.0.0.2 ----------
ALT=$WORK/alt
mkdir -p "$ALT/sysA" "$ALT/sysB"

DATE=2024-01-01T00:00:00
git init -q "$ALT/sysA/subA"
printf 'a 1\n' > "$ALT/sysA/subA/f.txt"
git -C "$ALT/sysA/subA" add f.txt
as "Alice A" git -C "$ALT/sysA/subA" commit -q -m one
git -C "$ALT/sysA/subA" tag 30.0.0.1
DATE=2024-02-01T00:00:00
printf 'a 2\n' > "$ALT/sysA/subA/f.txt"
as "Alice A" git -C "$ALT/sysA/subA" commit -q -am two
git -C "$ALT/sysA/subA" tag 30.0.0.2

DATE=2024-01-01T00:00:00
git init -q "$ALT/sysB/subB"
printf 'b 1\n' > "$ALT/sysB/subB/old.txt"
git -C "$ALT/sysB/subB" add old.txt
as "Bob B" git -C "$ALT/sysB/subB" commit -q -m one
git -C "$ALT/sysB/subB" tag 30.0.0.1
DATE=2024-02-01T00:00:00
git -C "$ALT/sysB/subB" mv old.txt new.txt
as "Bob B" git -C "$ALT/sysB/subB" commit -q -m two
git -C "$ALT/sysB/subB" tag 30.0.0.2

cat > "$ALT/.gitmodules" <<'EOF'
[submodule "sysA.subA"]
	path = sysA/subA
	url = ../sysA.subA.git
[submodule "sysB.subB"]
	path = sysB/subB
	url = ../sysB.subB.git
EOF

# --- the site tools Tdiff shells out to, stubbed -------------------------
BIN=$WORK/bin
mkdir -p "$BIN"

cat > "$BIN/Psort" <<'EOF'
#!/bin/sh
cat   # the context path given on stdin, passed straight through
EOF

cat > "$BIN/list_subsystems" <<'EOF'
#!/bin/sh
# -format '%S/%s %v': "<sys>/<sub> <version>" per submodule in the
# baseline's closure -- here, always both fixture submodules, at whichever
# of 30.0.0.1/30.0.0.2 the piped-in context path names.
read -r path
case "$path" in
    *30.0.0.1*) ver=30.0.0.1 ;;
    *30.0.0.2*) ver=30.0.0.2 ;;
    *) exit 0 ;;
esac
printf 'sysA/subA %s\n' "$ver"
printf 'sysB/subB %s\n' "$ver"
EOF

cat > "$BIN/list_cfmutest_subsystems" <<'EOF'
#!/bin/sh
# $1 a baseline ending .LATEST or .LATEST_GOOD, -select PREFIX: resolved
# to 30.0.0.2 in this fixture, whichever is asked for.
case "$1" in
    *.LATEST|*.LATEST_GOOD) echo "CFMUTEST.CFMUTEST_CONFIG.30.0.0.2" ;;
    *) ;;
esac
EOF

cat > "$BIN/readlink" <<EOF
#!/bin/sh
if [ "\$1" = "-e" ] && [ "\$2" = "/cm/ot/CFMUTEST/CFMUTEST_CONFIG.LATEST" ]; then
    echo "/fake/cm/ot/CFMUTEST/CFMUTEST_CONFIG.30.0.0.2"
    exit 0
fi
exec $(command -v readlink) "\$@"
EOF

chmod +x "$BIN"/*
PATH=$BIN:$PATH
export PATH

fails=0
check() {
    name=$1; want=$2; got=$3
    if [ "$want" = "$got" ]; then printf '  %-52s OK\n' "$name"
    else printf '  %-52s FAIL\n    want: %s\n    got:  %s\n' "$name" "$want" "$got"; fails=$((fails + 1)); fi
}

# From outside the alternate, as a user would run it.
cd "$WORK"

# --- CLI validation --------------------------------------------------------
"$TDIFF" -help > "$WORK/out" 2>&1
check "-help: mentions -alternate"            1 "$(grep -c -- '-alternate' "$WORK/out")"
rc=0; "$TDIFF" -bogus > /dev/null 2>"$WORK/err" || rc=$?
check "an unrecognised option: exits 1"       1 "$rc"
check "...says so"                            1 "$(grep -c 'Unrecognised option' "$WORK/err")"
rc=0; "$TDIFF" -alternate "$ALT" a b c > /dev/null 2>"$WORK/err" || rc=$?
check "three descriptors: refused"            1 "$(grep -c 'Too many arguments' "$WORK/err")"
rc=0; "$TDIFF" -head 30.0.0.1 > /dev/null 2>"$WORK/err" || rc=$?
check "-head with a descriptor: refused"      1 "$(grep -c -- '-head/-H' "$WORK/err")"
rc=0; "$TDIFF" 30.0.0.1 > /dev/null 2>"$WORK/err" || rc=$?
check "no alternate: refused"                 1 "$(grep -c 'alternate' "$WORK/err")"

# --- two explicit baselines ------------------------------------------------
# context_refs resolves to the baseline's own tag string in each
# submodule, not a hash: -revision reports that string as given, exactly
# as Tdiff.ksh's left_refs/right_refs associative arrays would.
"$TDIFF" -alternate "$ALT" -revision 30.0.0.1 30.0.0.2 > "$WORK/out" 2>"$WORK/err"
check "-revision: both submodules, both revisions" "sysA/subA 30.0.0.1 30.0.0.2
sysB/subB 30.0.0.1 30.0.0.2" "$(cat "$WORK/out")"

"$TDIFF" -alternate "$ALT" -name 30.0.0.1 30.0.0.2 > "$WORK/out" 2>"$WORK/err"
check "-name: the changed files, prefixed"    "sysA/subA/f.txt
sysB/subB/new.txt" "$(cat "$WORK/out")"

"$TDIFF" -alternate "$ALT" -status 30.0.0.1 30.0.0.2 > "$WORK/out" 2>"$WORK/err"
check "-status: a rename, status R"           "M sysA/subA/f.txt
R sysB/subB/new.txt" "$(cat "$WORK/out")"

# --- a single descriptor: against the baseline before it -------------------
"$TDIFF" -alternate "$ALT" -name 30.0.0.2 > "$WORK/out" 2>"$WORK/err"
check "one descriptor: against the previous baseline" "sysA/subA/f.txt
sysB/subB/new.txt" "$(cat "$WORK/out")"

# --- LATEST, resolved through list_cfmutest_subsystems ---------------------
"$TDIFF" -alternate "$ALT" -name LATEST > "$WORK/out" 2>"$WORK/err"
check "LATEST: resolved, same as 30.0.0.2"    "sysA/subA/f.txt
sysB/subB/new.txt" "$(cat "$WORK/out")"

# --- an unsupported baseline shorthand -------------------------------------
rc=0; "$TDIFF" -alternate "$ALT" '???' > /dev/null 2>"$WORK/err" || rc=$?
check "unsupported baseline format: exits 1"  1 "$rc"
check "...says so"                            1 "$(grep -c 'Unsupported baseline format' "$WORK/err")"

# --- the directory-tree diff: both sides sparse-checked-out, the rename's --
# --- old and new names present on both, so the tool diffing them sees it --
"$TDIFF" -alternate "$ALT" -x '' -directory "$WORK" 30.0.0.1 30.0.0.2 > "$WORK/out" 2>"$WORK/err"
left=$(sed -n '1p' "$WORK/out"); right=$(sed -n '2p' "$WORK/out")
check "directory diff: the old content, left"  "a 1" "$(cat "$left/sysA/subA/f.txt")"
check "directory diff: the new content, right" "a 2" "$(cat "$right/sysA/subA/f.txt")"
check "directory diff: the rename, old name left"  "b 1" "$(cat "$left/sysB/subB/old.txt" 2>/dev/null)"
check "directory diff: the rename, new name right" "b 1" "$(cat "$right/sysB/subB/new.txt" 2>/dev/null)"
rm -rf "$left" "$right" 2>/dev/null

echo
if [ "$fails" -eq 0 ]; then
    echo "All checks passed."
else
    echo "$fails check(s) FAILED."
fi
[ "$fails" -eq 0 ] || exit 1
