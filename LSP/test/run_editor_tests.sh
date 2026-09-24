#!/bin/sh
# The editors' highlighting of regex literals, against the transpiler's own
# tokenizer: over every .ady in the repository, VS Code and Emacs must mark
# a regex exactly where the tokenizer finds one, and no line of the sample
# may be swallowed by a string a quote inside a regex opened. Sublime's
# rules must be the VS Code grammar's (no Sublime Text here to run them).
#
# Each check SKIPs, saying how to get it running, when what it needs is not
# installed -- none of node, emacs, nim-mode or PyYAML is otherwise needed.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PYTHON=${PYTHON:-python3.12}
cd "$ROOT" || exit 1
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM

# the repository's .ady files, and the sample however it is tracked
FILES=$( (git ls-files '*.ady'; echo LSP/test/regex_sample.ady) | sort -u)
"$PYTHON" "$HERE/regex_spans.py" $FILES | sort > "$TMP/want"
fails=0

# compare NAME OUTPUT: the spans must be the tokenizer's, and no line leaks
compare() {
    name=$1; out=$2
    grep -v ': STRING LEAK$' "$out" | sort > "$TMP/got"
    leaks=$(grep ': STRING LEAK$' "$out" | grep "regex_sample.ady" || true)
    if [ -z "$leaks" ] && cmp -s "$TMP/want" "$TMP/got"; then
        echo "OK ($(wc -l < "$TMP/want" | tr -d ' ') regexes)"
    else
        echo FAIL
        comm -23 "$TMP/want" "$TMP/got" | sed 's/^/    missed: /' | head -10
        comm -13 "$TMP/want" "$TMP/got" | sed 's/^/    extra:  /' | head -10
        printf '%s\n' "$leaks" | grep . | sed 's/^/    /' | head -10
        fails=$((fails + 1))
    fi
}

printf '  %-42s' "VS Code grammar (vscode-textmate)"
if ! command -v node >/dev/null 2>&1; then
    echo "SKIP (no node)"
elif ! (cd "$HERE" && node -e "require('vscode-textmate'); require('vscode-oniguruma')") 2>/dev/null; then
    echo "SKIP (cd LSP/test && npm install)"
else
    node "$HERE/textmate_spans.js" $FILES > "$TMP/vscode" 2>&1
    compare vscode "$TMP/vscode"
fi

printf '  %-42s' "Emacs adascript-mode"
if ! command -v emacs >/dev/null 2>&1; then
    echo "SKIP (no emacs)"
elif ! emacs --batch --eval "(progn (require 'package) (package-initialize) (kill-emacs (if (locate-library \"nim-mode\") 0 1)))" >/dev/null 2>&1; then
    echo "SKIP (no nim-mode: M-x package-install RET nim-mode)"
else
    emacs --batch -l "$HERE/emacs_spans.el" $FILES 2>/dev/null > "$TMP/emacs"
    compare emacs "$TMP/emacs"
fi

printf '  %-42s' "Sublime syntax = VS Code grammar's rules"
out=$("$PYTHON" "$HERE/check_sublime.py" 2>&1); rc=$?
if [ $rc -eq 2 ]; then
    echo "SKIP (no PyYAML)"
elif [ $rc -eq 0 ]; then
    echo OK
else
    echo FAIL; printf '%s\n' "$out" | sed 's/^/    /'
    fails=$((fails + 1))
fi

[ $fails -eq 0 ]
