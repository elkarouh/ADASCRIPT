#!/bin/sh
# Each file here is a program a backend must refuse: its `# refused by B: TEXT`
# lines name the backend and what the refusal says. mod_*.ady are modules they
# import. Run from anywhere: check.sh PYTHON
PYTHON=${1:-python3}
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
tmp=${TMPDIR:-/tmp}/ady_refused.$$
status=0
for f in "$here"/*.ady; do
    case $(basename "$f") in mod_*) continue ;; esac
    grep '^# refused by ' "$f" | while IFS= read -r line; do
        backend=${line#\# refused by }; backend=${backend%%:*}
        text=${line#*: }
        printf '  %-42s' "$(basename "$f" .ady) ($backend)"
        case $backend in
            nim) cmd="$PYTHON $root/TO_NIM/ady2nim.py c $f" ;;
            python) cmd="$PYTHON $root/TO_PYTHON/ady2py.py $f" ;;
        esac
        if $cmd > "$tmp" 2>&1; then
            echo "FAIL (accepted)"; exit 1
        fi
        if grep -qF -- "$text" "$tmp"; then echo OK; else echo FAIL; cat "$tmp"; exit 1; fi
    done || status=1
done
rm -f "$tmp"
exit $status
