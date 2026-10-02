#!/bin/sh
# run_c500_tests.sh -- c500 on each C program here, against what it must emit.
#
# usage: run_c500_tests.sh COMMAND...
#   COMMAND runs the compiler: the Nim binary, or python3 on its translation.
#
# Each NAME.c is compiled from stdin; the WebAssembly it prints, and the exit
# status, are compared with NAME.wat. escapes.c has every escape form a C
# literal may use, pointers.c every mix of pointer and int in + and -, and
# pointer_levels.c the error for subtracting pointers of different levels.
# comments.c has every place a comment may sit, and unterminated_comment.c the error
# for one that is never closed.
HERE=$(cd "$(dirname "$0")" && pwd)
fail=0
for c in "$HERE"/*.c; do
    name=$(basename "$c" .c)
    got=$("$@" < "$c" 2>&1; echo "exit $?")
    printf '  %-42s' "$name.c"
    if [ "$got" = "$(cat "$HERE/$name.wat")" ]; then
        echo OK
    else
        echo FAIL
        printf '%s\n' "$got" | diff "$HERE/$name.wat" - | head -10
        fail=1
    fi
done
exit $fail
