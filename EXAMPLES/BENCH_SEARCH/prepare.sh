#!/bin/sh
# prepare.sh -- build the benchmark's data, the way tests/perf of
# https://github.com/Anode1/ais makes it, without the files that repository's
# author has and we do not (a home directory of paths, /usr/share/dict/words).
#
#   sh prepare.sh [DIR] [N]        defaults: /tmp/bench_search_data, 1000000
#
# Needs a clone of the repository (ais_dir below), a C compiler, and Python 3.
# Writes DIR/store and DIR/idx/ (the posting lists, built by ais itself).
set -e
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dir=${1:-/tmp/bench_search_data}
n=${2:-1000000}
ais_dir=${AIS_DIR:-$HOME/ais}                    # git clone https://github.com/Anode1/ais
values_root=${VALUES_ROOT:-/usr/lib}             # any tree: its file paths are the values

[ -d "$ais_dir/tests/perf" ] || { echo "clone https://github.com/Anode1/ais to $ais_dir (or set AIS_DIR)"; exit 1; }
mkdir -p "$dir"

# a word list: 6000 pronounceable lowercase words, seeded, in place of the dict
python3 - "$dir/words" <<'PY'
import random, sys
rng = random.Random(1)
cons, vow = "bcdfghjklmnprstvwz", "aeiou"
words = set()
while len(words) < 6000:
    words.add("".join(rng.choice(cons) + rng.choice(vow)
                      for _ in range(rng.choice([2, 3, 3, 4]))))
open(sys.argv[1], "w").write("\n".join(sorted(words)) + "\n")
PY

# their generator, pointed at our two inputs (their file is not modified)
sed -e "s#^KUL_ROOT   = .*#KUL_ROOT   = \"$values_root\"#" \
    -e "s#^DICT_PATH  = .*#DICT_PATH  = \"$dir/words\"#" \
    "$ais_dir/tests/perf/gen.py" > "$dir/gen_local.py"
python3 "$dir/gen_local.py" "$dir/data" "$n"      # ~2.5 min for 1M records

make -C "$ais_dir/c" >/dev/null
"$ais_dir/c/ais" -f "$dir/data" -y --compact       # the posting lists
echo "$dir/data is ready"
