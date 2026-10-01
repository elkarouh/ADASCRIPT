#!/usr/bin/env bash
# g_hist: step through a file's git history in meld, newest change first.
# Follows renames, handles deleted revisions, and works from any directory.
set -euo pipefail

usage() { echo "usage: ${0##*/} path/to/file" >&2; exit 2; }
[[ $# -eq 1 ]] || usage
FILE=$1

# Use zenity when a display is available, otherwise fall back to the terminal.
if command -v zenity >/dev/null && [[ -n ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]]; then
  gui=1
else
  gui=0
fi

msg_error() {
  echo "error: $*" >&2
  (( gui )) && { zenity --error --no-markup --text="$*" || true; }
}
msg_info() {
  echo "$*"
  (( gui )) && { zenity --info --no-markup --text="$*" || true; }
}
die() { msg_error "$*"; exit 1; }

# ask "title" "text": returns 0 to continue, 1 to stop
ask() {
  if (( gui )); then
    zenity --question --no-markup --title="$1" --text="$2" \
      --ok-label="Continue" --cancel-label="Stop"
  else
    local a
    read -r -p "$2 [Y/n] " a || return 1
    [[ ! $a =~ ^[Nn] ]]
  fi
}

command -v git   >/dev/null || die "git is not installed"
command -v meld  >/dev/null || die "meld is not installed"

# A file in a git work tree is used as it is. Otherwise a file of NM -- <system>/
# <subsystem>/<path>, or a path below the NM workspace, whose submodule is not
# checked out -- is checked out alone first, by Tcheckout, as Treport's diff links
# do. The places Tcheckout uses: the workspace, else the cache of the diff links.
nm_root() {
  echo "${CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY:-${TCHECK_NM_CACHE:-$HOME/Downloads/.cache/tcheck/NM}}"
}
inside_git() {
  local d
  d=$(dirname -- "$(realpath -m -- "$1")")
  [[ -d $d ]] && git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1
}
if ! { [[ -e $FILE ]] && inside_git "$FILE"; }; then
  nmroot=$(nm_root)
  target=
  if [[ $FILE == "$nmroot"/* ]]; then
    target=${FILE#"$nmroot"/}
  elif [[ $FILE != /* && $FILE != .* && $FILE == */*/* ]]; then
    target=$FILE
  fi
  if [[ -z $target ]]; then
    [[ -e $FILE ]] || die "File not found: $FILE"
    die "$FILE is not inside a git repository"
  fi
  command -v Tcheckout >/dev/null \
    || die "$FILE is not in a git repository; it names the NM file $target, which Tcheckout would check out, and Tcheckout is not installed"
  echo "Checking out $target, alone (Tcheckout), in $nmroot"
  out=$(Tcheckout "$target" 2>&1) || die "Tcheckout $target: $out"
  FILE=$nmroot/$target
fi

abs=$(realpath -- "$FILE")

# Ask git from the file's own directory, so this works from any cwd.
root=$(git -C "$(dirname -- "$abs")" rev-parse --show-toplevel 2>/dev/null) \
  || die "$FILE is not inside a git repository"

rel=${abs#"$root"/}
[[ $rel != "$abs" ]] || die "$FILE is not inside the git repo at $root"

echo "Repo root:     $root"
echo "Repo-rel path: $rel"

git_() { git -C "$root" "$@"; }

# G_HIST_DEBUG=1 g_hist FILE   says on stderr what git answered for every
# commit and how the names were made.
dbg() { [[ -z ${G_HIST_DEBUG:-} ]] || echo "g_hist debug: $*" >&2; }
raw() { local out; out=$(git_ "$@" 2>&1) && echo "${out//$'\n'/ | }" || echo "<exit $?> ${out//$'\n'/ | }"; }
probe_repo() {
  [[ -n ${G_HIST_DEBUG:-} ]] || return 0
  local all
  all=$(git_ tag --list)
  dbg "git                  : [$(raw --version)]"
  dbg "file                 : $abs"
  dbg "repo root, rel path  : $root, $rel"
  dbg "git dir              : [$(raw rev-parse --git-dir)]"
  dbg "superproject         : [$(raw rev-parse --show-superproject-working-tree)]"
  dbg "shallow              : [$(raw rev-parse --is-shallow-repository)]"
  dbg "GIT_DIR, GIT_WORK_TREE : [${GIT_DIR:-}], [${GIT_WORK_TREE:-}]"
  dbg "tag.sort, log.decorate : [$(raw config --get tag.sort)], [$(raw config --get log.decorate)]"
  dbg "HEAD                 : $(raw rev-parse HEAD)"
  dbg "tags at HEAD         : [$(raw tag --points-at HEAD)]"
  dbg "tags in the repo     : $(grep -c . <<<"$all" || true)"
}
probe() {
  [[ -n ${G_HIST_DEBUG:-} ]] || return 0
  dbg "commit $1"
  dbg "  rev-parse --verify   : [$(raw rev-parse --verify "$1^{commit}")]"
  dbg "  tag --points-at      : [$(raw tag --points-at "$1")]"
  dbg "  log -1 --format=%D   : [$(raw log -1 --format=%D "$1")]"
  dbg "  describe exact-match : [$(raw describe --tags --exact-match "$1")]"
  dbg "  name-rev --tags      : [$(raw name-rev --tags --name-only "$1")]"
}

# Commits touching the file, newest first. --follow tracks renames, so we
# record the path the file had at each commit.
revs=()
paths=()
cur=
while IFS= read -r line; do
  if [[ $line == @* ]]; then
    cur=${line#@}
  elif [[ -n $line ]]; then
    revs+=("$cur")
    paths+=("$line")
  fi
done < <(git_ log --follow --name-only --format='@%H' -- "$rel")
probe_repo
dbg "${#revs[@]} commits touch $rel, newest first:"
for i in "${!revs[@]}"; do dbg "  ${revs[i]}  ${paths[i]}"; done

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
base=$(basename -- "$rel")

# Write file contents at a revision to $3 (empty if it doesn't exist there,
# e.g. before creation or after deletion).
show_at() {
  local rev=$1 path=$2 out=$3
  if git_ cat-file -e "$rev:$path" 2>/dev/null; then
    git_ show "$rev:$path" > "$out"
  else
    : > "$out"
  fi
}

describe() { git_ log -1 --format='%h %ad %cn: %s' --date=short "$1"; }

# Temp file name shown in meld's pane headers: [<tags>-]<date>-<committer>-<filename>
# (the commit's tags, if any, joined by +; else ~<nearest tag it is in>).
# $2 is a subdirectory ("new"/"old") so both files can never collide, even if
# two commits share the same date and committer.
tmpname() {
  local rev=$1 side=$2 who when tag near prefix=
  who=$(git_ log -1 --format='%cn' "$rev")
  who=${who//[^[:alnum:]._-]/_}
  while IFS= read -r tag; do
    [[ -n $tag ]] || continue
    prefix+="${prefix:+"+"}${tag//[^[:alnum:]._-]/_}"
  done < <(git_ tag --points-at "$rev")
  if [[ -z $prefix ]]; then
    # Release tags are usually on a later commit (a merge), not on the ones
    # that changed the file: name the nearest tag the commit is in, marked ~
    # as not exact. name-rev says "undefined" for none.
    near=$(git_ name-rev --tags --name-only "$rev")
    near=${near%%[~^]*}
    [[ -z $near || $near == undefined ]] || prefix="~${near//[^[:alnum:]._-]/_}"
  fi
  [[ -z $prefix ]] || prefix+=-
  probe "$rev"
  dbg "  named $side: prefix [$prefix] -> $base"
  when=$(git_ log -1 --format='%cd' --date=format:%Y-%m-%d "$rev")
  mkdir -p "$tmpdir/$side"
  echo "$tmpdir/$side/${prefix}${when}-${who}-$base"
}

# 1) Uncommitted changes vs HEAD, if any.
if git_ rev-parse --verify -q HEAD >/dev/null \
   && ! git_ diff --quiet HEAD -- "$rel" 2>/dev/null; then
  head_file=$(tmpname HEAD head)   # named like the others: with HEAD's tags
  show_at HEAD "$rel" "$head_file"
  echo "Uncommitted changes: opening working copy vs HEAD"
  meld --label "$(basename -- "$head_file")" --label "working copy" "$head_file" "$abs" || true
  ask "Continue?" "Continue to committed history?" || exit 0
fi

if (( ${#revs[@]} == 0 )); then
  # a path no commit touches: usually a path that is not the file's
  like=$(git_ ls-tree -r --name-only HEAD 2>/dev/null \
    | awk -v b="$base" '$0 == b || substr($0, length($0) - length(b)) == "/" b' \
    | head -8 | paste -sd, - | sed 's/,/, /g' || true)
  [[ -n $like ]] || like="none: no file called $base at HEAD either"
  die "No commit of $root touches $rel; files called $base at HEAD: $like"
fi

if (( ${#revs[@]} < 2 )); then
  die "Need at least 2 committed revisions of $rel (found ${#revs[@]})"
fi

total=$(( ${#revs[@]} - 1 ))
echo "Found ${#revs[@]} revisions; $total comparisons."

for ((i = 0; i < total; i++)); do
  new=${revs[i]};      new_path=${paths[i]}
  old=${revs[i + 1]};  old_path=${paths[i + 1]}
  new_desc=$(describe "$new")
  old_desc=$(describe "$old")

  if (( i > 0 )); then
    ask "Continue?" "Comparison $((i + 1)) of $total

new: $new_desc
old: $old_desc" || { echo "Stopped by user after $i comparison(s)."; exit 0; }
  fi

  nf=$(tmpname "$new" new)
  of=$(tmpname "$old" old)
  show_at "$new" "$new_path" "$nf"
  show_at "$old" "$old_path" "$of"

  [[ $new_path == "$old_path" ]] || echo "  (renamed: $old_path -> $new_path)"
  echo "[$((i + 1))/$total] $new_desc  <-  $old_desc"
  meld "$of" "$nf" || true   # oldest on the left, newest on the right

  rm -f "$nf" "$of"
done

msg_info "Done. Reviewed $total comparison(s)."
