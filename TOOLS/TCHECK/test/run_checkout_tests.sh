#!/bin/sh
# Tcheckout against real repositories built here: an upstream submodule
# (TACT/UIF: two files over two tagged baselines, filtering allowed), a
# superproject recording it, and a workspace cloned from that without its
# submodules -- the case Tcheck_tact's diff links check the file out for.
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

# another submodule, to check out in full
lib=$WORK/scm/nm/ifps.opif_lib.git
git init -q "$lib"
printf 'x\n' > "$lib/x.ads"
git -C "$lib" add . && git -C "$lib" commit -qm one

# the superproject, recording them, TACT/UIF at 30.0.0.2; the workspace,
# without them
nm=$WORK/scm/nm/nm.git
git init -q "$nm"
git -C "$nm" submodule add -q --name TACT.UIF ../tact.uif.git TACT/UIF
git -C "$nm" submodule add -q --name IFPS.OPIF_LIB ../ifps.opif_lib.git IFPS/OPIF_LIB
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

# -l and -u: the files checked out, and out again
git -C "$ws" submodule update -q --init IFPS/OPIF_LIB      # in full: not Tcheckout's
"$TCHECKOUT" -root "$ws" TACT/UIF/sources/a.adb >/dev/null 2>&1
check "-l: the files checked out"                    "TACT/UIF/sources/b.adb TACT/UIF/sources/a.adb" \
    "$("$TCHECKOUT" -root "$ws" -l | tr '\n' ' ' | sed 's/ $//')"
check "...a submodule's"                             "TACT/UIF/sources/b.adb TACT/UIF/sources/a.adb" \
    "$("$TCHECKOUT" -root "$ws" -l TACT/UIF/ | tr '\n' ' ' | sed 's/ $//')"
check "...none of another's"                         "" "$("$TCHECKOUT" -root "$ws" -l IFPS/OPIF_LIB)"
out=$("$TCHECKOUT" -root "$ws" -u TACT/UIF/sources/a.adb 2>&1) || { echo "$out"; exit 1; }
check "-u: the file taken out"                       "no b 2" "$([ -e "$sub/sources/a.adb" ] && echo yes || echo no) $(cat "$sub/sources/b.adb")"
check "...off the list"                              "TACT/UIF/sources/b.adb" "$("$TCHECKOUT" -root "$ws" -l)"
check "...the submodule clean"                       "" "$(git -C "$sub" status --porcelain)"
rc=0; out=$("$TCHECKOUT" -root "$ws" -u TACT/UIF/sources/a.adb 2>&1) || rc=$?
check "...not twice"                                 "1 1" "$rc $(printf '%s\n' "$out" | grep -c 'a.adb is not checked out')"
printf 'mine\n' >> "$sub/sources/b.adb"
rc=0; out=$("$TCHECKOUT" -root "$ws" -u TACT/UIF/sources/b.adb 2>&1) || rc=$?
check "...nor a file with changes"                   "1 1 yes" \
    "$rc $(printf '%s\n' "$out" | grep -c 'has changes') $(grep -q mine "$sub/sources/b.adb" && echo yes)"
git -C "$sub" checkout -q -- sources/b.adb
out=$("$TCHECKOUT" -root "$ws" -u TACT/UIF/sources/b.adb 2>&1) || { echo "$out"; exit 1; }
check "the last: the submodule deinitialised"        "" "$(ls -A "$sub")"
check "...its clone kept"                            "1 yes" \
    "$(printf '%s\n' "$out" | grep -c 'clone kept') $([ -d "$ws/.git/modules/TACT.UIF" ] && echo yes)"
check "...git sees it not initialised"               "-" "$(git -C "$ws" submodule status TACT/UIF | cut -c1)"
check "...nothing listed"                            "" "$("$TCHECKOUT" -root "$ws" -l)"
out=$("$TCHECKOUT" -root "$ws" TACT/UIF/sources/a.adb 2>&1) || { echo "$out"; exit 1; }
check "...checked out again: that file alone"        "reused a 2 no" \
    "$(printf '%s\n' "$out" | grep -q reusing && echo reused) $(cat "$sub/sources/a.adb") $([ -e "$sub/sources/b.adb" ] && echo yes || echo no)"
rc=0; out=$("$TCHECKOUT" -root "$ws" -u IFPS/OPIF_LIB/x.ads 2>&1) || rc=$?
check "-u: not a submodule checked out in full"      "1 1 x" \
    "$rc $(printf '%s\n' "$out" | grep -c 'checked out in full') $(cat "$ws/IFPS/OPIF_LIB/x.ads")"

# a DIFF link, as Tcheck_tact writes it for a submodule not checked out,
# evaluated by Emacs: the file checked out, then its versions compared
if command -v emacs >/dev/null 2>&1; then
    git -C "$ws" submodule deinit -q -f TACT/UIF
    f=$sub/sources/b.adb
    link="(when (eql 0 (shell-command \"Tcheckout -root $ws TACT/UIF/sources/b.adb\")) (vc-version-ediff (list \"$f\") \"30.0.0.1\" \"30.0.0.2\"))"
    shown='(dolist (n (sort (mapcar (function buffer-name) (buffer-list)) (function string<))) (when (string-match "b[.]adb[.]~" n) (with-current-buffer n (message "SHOWN %s=%s" n (string-trim (buffer-string))))))'
    got=$(cd / && PATH=$(dirname "$TCHECKOUT"):$PATH emacs --batch -Q --eval "(progn (require 'vc) $link $shown)" 2>&1 |
          sed -n 's/^SHOWN //p' | tr '\n' ' ')
    check "a DIFF link, in Emacs: checked out, compared" "b.adb.~30.0.0.1~=b 1 b.adb.~30.0.0.2~=b 2 " "$got"
else
    echo "  SKIP a DIFF link in Emacs (no emacs)"
fi

echo
if [ $fails -eq 0 ]; then echo "All checks passed."; else echo "$fails check(s) FAILED."; exit 1; fi
