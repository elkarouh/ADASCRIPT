#!/usr/bin/env bash
#
# sh_janitor.sh -- the same job as sh_janitor.ady, in the shell.
#
#     ./sh_janitor.sh [WORKDIR]
#
# This is the version the .ady file is named after: the log-rotation script
# every site has written. It is written the way those are written, not
# sabotaged -- and the filename with a space in it goes through it the way
# it goes through them.
#
# Run the two on the same fixture and diff the reports. They do not match,
# and that is the point of DOCS/ADASCRIPT_FOR_SHELL.md section 12.
#
# The quoting bug is fixable -- `find -print0 | while IFS= read -r -d ''`
# instead of `for f in $(ls)`, and quotes on every expansion after it. What
# is not fixable in the shell is the rest: ACTION is a string that nothing
# checks, the four tests of it are four chances for a typo that is a silent
# no-op, and `&` plus `wait` gives one exit status for the lot rather than
# one per job.

set -u

BIG_ENOUGH=64          # bytes; a real one would say 10 MB

build_fixture() {
    local d=/tmp/sh_janitor_sh
    rm -rf "$d"
    mkdir -p "$d"
    printf 'x%.0s' $(seq 200) > "$d/app.log"
    printf 'x%.0s' $(seq 300) > "$d/quiet service.log"   # a space, on purpose
    printf 'x%.0s' $(seq 3)   > "$d/tiny.log"
    printf 'x%.0s' $(seq 128) > "$d/build.out"
    printf 'x%.0s' $(seq 10)  > "$d/scratch.tmp"
    printf 'x%.0s' $(seq 10)  > "$d/editor backup~"
    printf 'x%.0s' $(seq 20)  > "$d/app.conf"
    printf 'x%.0s' $(seq 20)  > "$d/.hidden"
    printf 'x%.0s' $(seq 20)  > "$d/old.log.gz"
    echo "$d"
}

# What is to become of a file. A string in a variable, and the four places
# that test it below are four chances for a typo the shell will not mention.
decide() {
    local name=$1 size=$2
    case "$name" in
        *.gz)              echo SKIP     ;;   # already done
        .*)                echo SKIP     ;;   # dotfile
        *.log|*.out|*.err)
            if [ "$size" -ge "$BIG_ENOUGH" ]; then echo COMPRESS; else echo KEEP; fi ;;
        *.tmp|*~)          echo DELETE   ;;
        *)                 echo KEEP     ;;
    esac
}

if ! command -v gzip >/dev/null 2>&1; then
    echo "sh_janitor: gzip is not installed"
    exit 1
fi

if [ $# -ge 1 ]; then DIR=$1; else DIR=$(build_fixture); fi
if [ ! -d "$DIR" ]; then
    echo "sh_janitor: $DIR is not a directory"
    exit 2
fi

n_compress=0; n_delete=0; n_keep=0; n_skip=0
b_compress=0; b_delete=0; b_keep=0; b_skip=0
failed=0

# Here is the line. `ls` writes one name per line, the shell splits that on
# whitespace, and "quiet service.log" becomes "quiet" and "service.log" --
# two names, neither of which exists.
for f in $(ls -A "$DIR"); do
    path=$DIR/$f
    [ -f "$path" ] || continue
    size=$(wc -c < "$path")
    action=$(decide "$f" "$size")

    case "$action" in
        COMPRESS) n_compress=$((n_compress + 1)); b_compress=$((b_compress + size)) ;;
        DELETE)   n_delete=$((n_delete + 1));     b_delete=$((b_delete + size))     ;;
        KEEP)     n_keep=$((n_keep + 1));         b_keep=$((b_keep + size))         ;;
        SKIP)     n_skip=$((n_skip + 1));         b_skip=$((b_skip + size))         ;;
    esac

    case "$action" in
        COMPRESS) gzip -f -- "$path" & ;;
        DELETE)   rm -f -- "$path"     ;;
    esac
done

# One wait for all of them, because that is what `wait` with no argument
# does: it reports that the last one finished, not which of them failed.
wait || failed=$((failed + 1))

echo "--- sh_janitor $DIR ---"
printf '  %-8s %2d file(s), %4d bytes\n' COMPRESS "$n_compress" "$b_compress"
printf '  %-8s %2d file(s), %4d bytes\n' DELETE   "$n_delete"   "$b_delete"
printf '  %-8s %2d file(s), %4d bytes\n' KEEP     "$n_keep"     "$b_keep"
printf '  %-8s %2d file(s), %4d bytes\n' SKIP     "$n_skip"     "$b_skip"
printf '  %d failure(s)\n' "$failed"
[ "$failed" -gt 0 ] && exit 1
exit 0
