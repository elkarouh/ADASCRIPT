#!/bin/bash
# rsync_time_machine_test.sh -- run rsync_time_machine against real folders.
#
# usage: rsync_time_machine_test.sh WORKDIR COMMAND...
#   COMMAND runs the program: the Nim binary, or python3 on its translation.
#
# What `make test` cannot see by compiling alone: that a step which fails
# stops the run and says so, and what happens when the disk fills up. Two
# stand-ins go first on PATH to make those happen: an `ln` that always
# fails, and an `rsync` that runs out of space once and then works.
set -u
W=$1; shift
rm -rf "$W"; mkdir -p "$W/bin" "$W/src/sub" "$W/dest" "$W/logs"
echo hello > "$W/src/a.txt"; echo world > "$W/src/sub/b.txt"

cat > "$W/bin/ln" <<'EOF'
#!/bin/sh
echo "ln: failed to create symbolic link: Operation not permitted" >&2
exit 1
EOF
REAL_RSYNC=$(command -v rsync)
cat > "$W/bin/rsync" <<EOF
#!/bin/bash
# First call: out of space, as rsync reports it. After that: the real one.
if [ ! -e "$W/ran-out" ]; then
    touch "$W/ran-out"
    prev=""
    for a in "\$@"; do
        [ "\$prev" = "--log-file" ] && echo "rsync: write failed: No space left on device (28)" >> "\$a"
        prev="\$a"
    done
    exit 11
fi
exec "$REAL_RSYNC" "\$@"
EOF
chmod +x "$W/bin/ln" "$W/bin/rsync"
mkdir "$W/bin/ln-only" "$W/bin/rsync-only"
mv "$W/bin/ln" "$W/bin/ln-only/"; mv "$W/bin/rsync" "$W/bin/rsync-only/"

failed=0
check() {   # check DESCRIPTION CONDITION...
    local what=$1; shift
    if "$@"; then printf '    %-58s ok\n' "$what"
    else printf '    %-58s FAILED\n' "$what"; failed=1; fi
}
run() { "$@" --log-dir "$W/logs" > "$W/out" 2>&1; }
backups() { ls "$W/dest" | grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}$'; }

run "$@" "$W/src" "$W/dest"
check "no backup.marker: refused, exit 1"              [ $? -eq 1 ]
check "...and says how to add the marker"               grep -q 'touch ".*backup.marker"' "$W/out"
touch "$W/dest/backup.marker"

run "$@" "$W/nosuch" "$W/dest"
check "missing source: exit 1"                          [ $? -eq 1 ]

run "$@" "$W/src" "$W/dest"
check "first backup: exit 0"                            [ $? -eq 0 ]
check "...latest holds the files"                       [ -f "$W/dest/latest/sub/b.txt" ]
check "...the lock is released"                         [ ! -e "$W/dest/backup.inprogress" ]

sleep 1
run "$@" "$W/src" "$W/dest" --dry-run
check "dry run: exit 0, no second backup"               [ $? -eq 0 -a "$(backups)" -eq 1 ]

rm -rf "$W/dest"/*; touch "$W/dest/backup.marker"
PATH="$W/bin/ln-only:$PATH" run "$@" "$W/src" "$W/dest"
check "ln -s fails: exit 1, not success"                [ $? -eq 1 ]
check "...the failed command is reported"               grep -q 'Command failed: ln -s' "$W/out"
check "...the lock is kept, so the next run resumes"    [ -e "$W/dest/backup.inprogress" ]

rm -rf "$W/dest"/*; touch "$W/dest/backup.marker"
mkdir "$W/dest/2020-01-01-000000" "$W/dest/2020-06-01-000000" "$W/dest/2021-01-01-000000"
PATH="$W/bin/rsync-only:$PATH" run "$@" "$W/src" "$W/dest"
check "out of space once: exit 0"                       [ $? -eq 0 ]
check "...the oldest backup is the one expired"         [ ! -e "$W/dest/2020-01-01-000000" ]
check "...and only that one"                            [ -d "$W/dest/2020-06-01-000000" -a -d "$W/dest/2021-01-01-000000" ]
check "...one retry, not one per attempt's stale log"   [ "$(grep -c 'removing oldest backup' "$W/out")" -eq 1 ]
check "...latest holds the new backup"                  [ -f "$W/dest/latest/sub/b.txt" ]

rm -rf "$W"
exit $failed
