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
# The two shapes that matter, as they resolve on the real system:
#
#   ordinary      ALPHA/SUB!44.0.0.1   ->  ALPHA.SUB.44.0.0.1
#   project branch ALPHA/SUB!TBO.44    ->  ALPHA.SUB.TBO.44
#
# cc_pattern PROJECT_BASELINE_ID describes the second -- SYSTEM.SUBSYS with a
# project name and a build counter after it -- so a match is a branch and a
# branch is what a search without -all leaves out. The first has a version
# where the project name would be and does not match.
for sys in ALPHA BETA; do
    ORD=$REAL/$sys/SUB!44.0.0.1
    PRJ=$REAL/$sys/SUB!TBO.44
    mkdir -p "$ORD/build_E1/sources/deep" "$ORD/sources/special_files" \
             "$ORD/build_E1/special_files" "$PRJ/build_E1/sources"
    echo "the remote call"   > "$ORD/build_E1/sources/main.adb"
    echo "a remote queue"    > "$ORD/build_E1/sources/deep/queue.ksh"
    echo "remote extra"      > "$ORD/build_E1/special_files/extra.txt"
    echo "remote compressed" | gzip > "$ORD/build_E1/sources/skip.gz"
    # A name with a space in it: the file list is one path per line, and a
    # find piped into a bare xargs splits it into two names that do not exist.
    echo "remote spaced"     > "$ORD/build_E1/sources/two words.txt"
    echo "remote in branch"  > "$PRJ/build_E1/sources/main.adb"
    mkdir -p "$OT/$sys"
    ln -s "$ORD" "$OT/$sys/SUB.LATEST"
    ln -s "$PRJ" "$OT/$sys/SUB.TBO.LATEST"
done

# The CM helpers, as they are on the real system: shell *functions* in a
# Caux_functions file, not programs. Run as commands they do not exist, and
# a command that does not exist prints nothing -- which is what an empty
# answer looks like too. cc_pattern's answer is a perl regexp, (?:...) and
# \d and all, which is not what grep -E reads.
mkdir -p "$WORK/bin" "$WORK/progs"
cat > "$WORK/bin/Caux_functions" <<'EOF'
# The closure helpers are functions here too, as they are on the real system.
get_topmost_subsystems() { printf '%s\n' 'SUB OTHER'; }
Psort() { read -r d; printf '%s\n' "$d"; }
cc_pattern() {
  case "$1" in
    SYSTEM)              printf '%s\n' '(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)' ;;
    PROJECT_BASELINE_ID) printf '%s\n' '(?^:(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)\.(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)\.(?^:(?<project_name_uc>(?:(?^:(?:[[:digit:][:upper:]_]))){1,20}))\.(?^:(?<build_counter>[[:digit:]]+)))' ;;
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
# The same answers, from a program rather than a sourced function.
case "$1" in
  SYSTEM)              printf '%s\n' '(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)' ;;
  PROJECT_BASELINE_ID) printf '%s\n' '(?^:(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)\.(?^:(?:(?^:(?:[[:digit:][:upper:]_])))+)\.(?^:(?<project_name_uc>(?:(?^:(?:[[:digit:][:upper:]_]))){1,20}))\.(?^:(?<build_counter>[[:digit:]]+)))' ;;
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
check "matches found"              8 "$("$PGREP" -no_colors remote | grep -c ':.*remote')"
check "the branch is not searched" 0 "$("$PGREP" -no_colors remote | grep -c 'in branch')"

# -all brings them back.
check "-all searches the branches" 4 "$("$PGREP" -all -no_colors remote | grep -c '^!=====')"
check "-all finds the branch"      2 "$("$PGREP" -all -no_colors remote | grep -c 'in branch')"

# The rest of the options, on the same tree.
check "-subsys narrows"            1 "$("$PGREP" -subsys alpha -no_colors remote | grep -c '^!=====')"
check "-no-grep lists files"       8 "$("$PGREP" -no-grep | grep -c '/')"
check "a name with a space is one" 2 "$("$PGREP" -no_colors remote | grep -c 'two words.txt:')"
check "-ada takes only .ad?"       2 "$("$PGREP" -ada -no-grep | grep -c '\.adb$')"
check "-ppat filters on the path"  2 "$("$PGREP" -ppat deep -no-grep | grep -c 'queue.ksh')"
check "a .gz is never searched"    0 "$("$PGREP" -no-grep | grep -c '\.gz')"
check "special_files are searched" 2 "$("$PGREP" -no-grep | grep -c 'special_files')"
check "-basenames cuts the path"   6 "$("$PGREP" -basenames -no_colors remote | grep -c '^[a-z]*\.[a-z]*:')"

# --- -closure, which resolves through the CM helpers -----------------------
#
# ALPHA is a SYSTEM, so it resolves through its topmost subsystem to
# ALPHA/SUB.LATEST; Psort puts the closure in order. Recognising the name as
# a SYSTEM is a cc_pattern match, and cc_pattern answers in perl: with
# `grep -E` asking the question, no name is ever a SYSTEM, `-closure ALPHA`
# resolves to the directory ALPHA, and Psort is handed something that is not
# a build.
CM_ROOT=$OT
export CM_ROOT
# A closure names its own builds, so the headers are -verbose's business.
check "-closure resolves a SYSTEM"  1 "$("$PGREP" -closure ALPHA -verbose -no_colors remote 2>/dev/null | grep -c '^!=====')"
check "...and searches it"          4 "$("$PGREP" -closure ALPHA -no_colors remote | grep -c ':.*remote')"
check "-closure says the directory" 1 "$("$PGREP" -closure ALPHA -verbose -no_colors remote 2>/dev/null | grep -c '^Closure *: ALPHA.SUB.LATEST')"
# On a view context, a $CONTEXT_CM_BASELINE naming a baseline of the same
# system wins over .LATEST -- and off one, it does not. The two resolve to
# the same build here, which is why this is a check on the Closure line
# rather than on what comes back.
check "a view context wins"         1 \
    "$(CONTEXT_CM_BASELINE=ALPHA.SUB.44.0.0.1 "$PGREP" -closure ALPHA -verbose -no_colors remote 2>/dev/null | grep -c '^Closure *: ALPHA.SUB.44.0.0.1')"
check "...and another system's not" 1 \
    "$(CONTEXT_CM_BASELINE=BETA.SUB.44.0.0.1 "$PGREP" -closure ALPHA -verbose -no_colors remote 2>/dev/null | grep -c '^Closure *: ALPHA.SUB.LATEST')"

# A baseline ID is not a SYSTEM: its first dot is the directory separator.
check "-closure takes a baseline"   4 "$("$PGREP" -closure ALPHA.SUB.LATEST -no_colors remote | grep -c ':.*remote')"
# The branches are a closure's own business: -closure says which builds.
check "-closure is not filtered"    1 "$("$PGREP" -closure ALPHA.SUB.TBO.LATEST -no_colors remote | grep -c 'in branch')"
unset CM_ROOT

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
    PROJECT_BASELINE_ID) printf '%s\n' '.*' ;;
    *)                   printf '%s\n' '[A-Z][A-Z0-9_]*' ;;
  esac
}
EOF
check "all-branches says so"       1 "$("$PGREP" -no_colors remote 2>&1 >/dev/null | grep -c 'every subsystem looked like')"

[ "$fails" -eq 0 ] || exit 1
