#!/bin/sh
# Pgrep's all-subsystems path, against a CM tree built here.
#
# This path -- which builds the subsystem list, drops the project branches
# and searches what is left -- had no test, because it reads /cm/ot and a
# machine either has one or does not. Three bugs hid in it in a row, each
# silent: a filter that kept the project branches instead of dropping them,
# a perl regexp tested with grep -E, and a baseline ID built by removing
# "/cm/ot/" from the middle of a path rather than cutting everything up to
# it. Every one of them came out as "no match", which is a valid answer.
#
# $PGREP_CM_OT points the program at the fixture. The CM helpers it consults
# are here too, on the PATH.
set -e

PGREP=${1:-../Pgrep}
[ -x "$PGREP" ] || { echo "SKIP (Pgrep not built)"; exit 0; }
PGREP=$(cd "$(dirname "$PGREP")" && pwd)/$(basename "$PGREP")

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT INT TERM

# The builds live somewhere else and are reached through the /cm/ot names,
# as they are on a real site: the resolved path has a prefix before /cm/ot.
REAL=$WORK/auto/local_build/ws/ssd1/cm/ot
OT=$WORK/cm/ot
for sys in ALPHA BETA; do
    mkdir -p "$REAL/$sys/SUB.44.0.0.A/build_E1/sources/deep"
    mkdir -p "$REAL/$sys/SUB!TBO.44.0.0.A/build_E1/sources"
    mkdir -p "$REAL/$sys/SUB.44.0.0.A/sources/special_files"
    mkdir -p "$REAL/$sys/SUB.44.0.0.A/build_E1/special_files"
    echo "the remote call"   > "$REAL/$sys/SUB.44.0.0.A/build_E1/sources/main.adb"
    echo "a remote queue"    > "$REAL/$sys/SUB.44.0.0.A/build_E1/sources/deep/queue.ksh"
    echo "remote extra"      > "$REAL/$sys/SUB.44.0.0.A/build_E1/special_files/extra.txt"
    echo "remote compressed" | gzip > "$REAL/$sys/SUB.44.0.0.A/build_E1/sources/skip.gz"
    echo "remote in branch"  > "$REAL/$sys/SUB!TBO.44.0.0.A/build_E1/sources/main.adb"
    mkdir -p "$OT/$sys"
    ln -s "$REAL/$sys/SUB.44.0.0.A"      "$OT/$sys/SUB.LATEST"
    ln -s "$REAL/$sys/SUB!TBO.44.0.0.A"  "$OT/$sys/SUB.TBO.LATEST"
done

# The CM helpers, as they are on the real system: shell *functions* in a
# Caux_functions file, not programs. Run as commands they do not exist, and
# a command that does not exist prints nothing -- which is what an empty
# answer looks like too. cc_pattern's answer is a perl regexp, (?:...) and
# \d and all, which is not what grep -E reads.
mkdir -p "$WORK/bin" "$WORK/progs"
cat > "$WORK/bin/Caux_functions" <<'EOF'
cc_pattern() {
  case "$1" in
    SYSTEM)              printf '%s\n' '[A-Z][A-Z0-9_]*' ;;
    PROJECT_BASELINE_ID) printf '%s\n' '(?:[A-Z][A-Z0-9_]*)\.\w+\.\d+\.\d+\.\d+\.\w+' ;;
    *)                   printf '%s\n' '.*' ;;
  esac
}
EOF
# A ksh standing in for the site's: all that matters is that it sources the
# file and runs the function.
printf '#!/bin/sh\nexec /bin/sh "$@"\n' > "$WORK/bin/ksh"
chmod +x "$WORK/bin/ksh"

# The same helper as a program, for the site where it is one.
cat > "$WORK/progs/cc_pattern" <<'EOF'
#!/bin/sh
case "$1" in
  SYSTEM)              printf '%s\n' '[A-Z][A-Z0-9_]*' ;;
  PROJECT_BASELINE_ID) printf '%s\n' '(?:[A-Z][A-Z0-9_]*)\.\w+\.\d+\.\d+\.\d+\.\w+' ;;
  *)                   printf '%s\n' '.*' ;;
esac
EOF
chmod +x "$WORK/progs/cc_pattern"

BASE_PATH=$PATH
PATH=$WORK/bin:$PATH
export PATH CM_ENV_ID=E1
PGREP_CM_OT=$OT
export PGREP_CM_OT

fails=0
check() {
    name=$1; want=$2; got=$3
    if [ "$want" = "$got" ]; then
        printf '  %-52s OK\n' "$name"
    else
        printf '  %-52s FAIL (want %s, got %s)\n' "$name" "$want" "$got"
        fails=$((fails + 1))
    fi
}

# The project branches are dropped, so two subsystems and not four.
check "subsystems searched"        2 "$("$PGREP" -no_colors remote | grep -c '^!=====')"
check "matches found"              6 "$("$PGREP" -no_colors remote | grep -c ':.*remote')"
check "the branch is not searched" 0 "$("$PGREP" -no_colors remote | grep -c 'in branch')"

# -all brings them back.
check "-all searches the branches" 4 "$("$PGREP" -all -no_colors remote | grep -c '^!=====')"
check "-all finds the branch"      2 "$("$PGREP" -all -no_colors remote | grep -c 'in branch')"

# The rest of the options, on the same tree.
check "-subsys narrows"            1 "$("$PGREP" -subsys alpha -no_colors remote | grep -c '^!=====')"
check "-no-grep lists files"       6 "$("$PGREP" -no-grep | grep -c '/')"
check "-ada takes only .ad?"       2 "$("$PGREP" -ada -no-grep | grep -c '\.adb$')"
check "-ppat filters on the path"  2 "$("$PGREP" -ppat deep -no-grep | grep -c 'queue.ksh')"
check "a .gz is never searched"    0 "$("$PGREP" -no-grep | grep -c '\.gz')"
check "special_files are searched" 2 "$("$PGREP" -no-grep | grep -c 'special_files')"
check "-basenames cuts the path"   6 "$("$PGREP" -basenames -no_colors remote | grep -c '^[a-z]*\.[a-z]*:')"

# The helper as a program and no ksh to be found: the direct call is the
# fallback, so a site whose helpers really are programs still works.
check "helpers as programs, no ksh" 2 \
    "$(PATH=$WORK/progs:$BASE_PATH "$PGREP" -no_colors remote | grep -c '^!=====')"

# Neither: the pattern cannot be had, and searching everything or nothing
# would both be guesses. It says so and stops.
check "no helper at all is an error" 1 \
    "$(PATH=$BASE_PATH "$PGREP" -no_colors remote 2>&1 >/dev/null | grep -c 'gave nothing')"
# `|| status=$?` rather than a substitution: with set -e a failing command
# inside one takes the script with it, and an empty capture is not a status.
status=0
PATH=$BASE_PATH "$PGREP" -no_colors remote >/dev/null 2>&1 || status=$?
check "...with a failing status"     1 "$status"

# A pattern that matches nothing is a broken filter, not an empty result.
cat > "$WORK/bin/Caux_functions" <<'EOF'
cc_pattern() {
  case "$1" in
    PROJECT_BASELINE_ID) printf '%s\n' 'NOTHING_MATCHES_THIS' ;;
    *)                   printf '%s\n' '[A-Z][A-Z0-9_]*' ;;
  esac
}
EOF
check "an empty filter says so"    1 "$("$PGREP" -no_colors remote 2>&1 >/dev/null | grep -c 'no subsystem matched')"

[ "$fails" -eq 0 ] || exit 1
