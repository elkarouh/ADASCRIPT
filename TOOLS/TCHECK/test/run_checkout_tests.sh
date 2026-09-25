#!/bin/sh
# Tcheckout against real repositories built here: an upstream submodule
# (TACT/UIF: two files over two tagged baselines, filtering allowed), a
# superproject recording it, and a workspace cloned from that without its
# submodules -- the case Tcheck_tact's CHECKOUT links are for.
set -e

TCHECKOUT=${1:-../Tcheckout}
TCHECKOUT=$(cd "$(dirname "$TCHECKOUT")" && pwd)/$(basename "$TCHECKOUT")
command -v git >/dev/null 2>&1 || { echo "SKIP (no git)"; exit 0; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GIT_CONFIG_NOSYSTEM=1 HOME=$WORK        # no one's git configuration but this
git config --global init.defaultBranch main
git config --global protocol.file.allow always  # submodules from local paths

# laid out as NM's: the repositories side by side on the server, the
# submodules named <SYSTEM>.<SUBSYSTEM>, with URLs relative to the
# superproject's (../tact.uif.git)
# the submodule upstream: a.adb and b.adb, both changed in 30.0.0.2
up=$WORK/scm/nm/tact.uif.git
git init -q "$up"
mkdir "$up/sources"
printf 'a 1\n' > "$up/sources/a.adb"; printf 'b 1\n' > "$up/sources/b.adb"
git -C "$up" add . && git -C "$up" commit -qm one && git -C "$up" tag 30.0.0.1
printf 'a 2\n' > "$up/sources/a.adb"; printf 'b 2\n' > "$up/sources/b.adb"
git -C "$up" commit -qam two && git -C "$up" tag 30.0.0.2
git -C "$up" config uploadpack.allowFilter true
git -C "$up" config uploadpack.allowAnySHA1InWant true

# the superproject, recording it at 30.0.0.2; the workspace, without it
nm=$WORK/scm/nm/nm.git
git init -q "$nm"
git -C "$nm" submodule add -q --name TACT.UIF ../tact.uif.git TACT/UIF
git -C "$nm" commit -qm "Baseline workspace"
ws=$WORK/ws
git clone -q "file://$nm" "$ws"
recorded=$(git -C "$nm" rev-parse HEAD:TACT/UIF)

fails=0
check() {
    name=$1; want=$2; got=$3
    if [ "$want" = "$got" ]; then printf '  %-52s OK\n' "$name"
    else printf '  %-52s FAIL\n    want: %s\n    got:  %s\n' "$name" "$want" "$got"; fails=$((fails + 1)); fi
}
sub=$ws/TACT/UIF

check "the workspace starts without the submodule"  "" "$(ls -A "$sub")"
out=$("$TCHECKOUT" -root "$ws" TACT/UIF/sources/b.adb 2>&1) || { echo "$out"; exit 1; }
check "the file, checked out"                        "b 2" "$(cat "$sub/sources/b.adb")"
check "...alone"                                     no "$([ -e "$sub/sources/a.adb" ] && echo yes || echo no)"
check "...at the commit the superproject records"    "$recorded" "$(git -C "$sub" rev-parse HEAD)"
check "...from the relative URL, resolved"          "file://$up" "$(git -C "$sub" remote get-url origin)"
check "...cloned without the files' contents"        blob:none "$(git -C "$sub" config remote.origin.partialclonefilter)"
check "...its repository where git keeps submodules" "$(git -C "$ws" rev-parse --absolute-git-dir)/modules/TACT.UIF" \
    "$(git -C "$sub" rev-parse --absolute-git-dir)"
check "git sees the submodule initialised"           "$recorded TACT/UIF" "$(git -C "$ws" submodule status TACT/UIF | awk '{ print $1, $2 }' | tr -d ' +-' | sed 's/TACT/ TACT/')"
check "...the other files' contents not fetched"    yes "$(git -C "$sub" rev-list --objects --missing=print --all | grep -q '^?' && echo yes || echo no)"
check "the diff between baselines works"             "+b 2" "$(git -C "$sub" diff 30.0.0.1 30.0.0.2 -- sources/b.adb | grep '^+b')"
check "...and between commits"                       "-b 1" "$(git -C "$sub" diff HEAD^ HEAD -- sources/b.adb | grep '^-b')"
out=$("$TCHECKOUT" -root "$ws" TACT/UIF/sources/a.adb 2>&1)
check "another file of it: added"                    "a 2" "$(cat "$sub/sources/a.adb")"
check "...said so"                                   1 "$(printf '%s\n' "$out" | grep -c 'adding sources/a.adb to the sparse checkout')"
check "a file checked out already: nothing to do"    1 "$("$TCHECKOUT" -root "$ws" TACT/UIF/sources/a.adb 2>&1 | grep -c 'checked out already')"
check "the workspace from the environment"           1 "$(CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY=$ws "$TCHECKOUT" TACT/UIF/sources/b.adb 2>&1 | grep -c 'checked out already')"
# deinitialised since: its repository is still in .git/modules, and reused
git -C "$ws" submodule deinit -q -f TACT/UIF
check "deinitialised: the submodule gone"            "" "$(ls -A "$sub")"
out=$("$TCHECKOUT" -root "$ws" TACT/UIF/sources/b.adb 2>&1) || { echo "$out"; exit 1; }
check "...checked out again, its repository reused"  "1 b 2" "$(printf '%s\n' "$out" | grep -c 'reusing') $(cat "$sub/sources/b.adb")"
check "...at the recorded commit"                    "$recorded" "$(git -C "$sub" rev-parse HEAD)"
set +e
out=$("$TCHECKOUT" -root "$ws" IFPS/NONE/x.adb 2>&1); rc=$?
set -e
check "not a submodule: refused"                     "1 1" "$rc $(printf '%s\n' "$out" | grep -c 'IFPS/NONE is not a submodule')"
rc=0; out=$("$TCHECKOUT" -root "$ws" TACT/UIF/ 2>&1) || rc=$?
check "a submodule, not a file: refused"             "1 1" "$rc $(printf '%s\n' "$out" | grep -c 'not a file: TACT/UIF/')"

echo
if [ $fails -eq 0 ]; then echo "All checks passed."; else echo "$fails check(s) FAILED."; exit 1; fi
