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

[[ -e $FILE ]] || die "File not found: $FILE"

abs=$(realpath -- "$FILE")

# Ask git from the file's own directory, so this works from any cwd.
root=$(git -C "$(dirname -- "$abs")" rev-parse --show-toplevel 2>/dev/null) \
  || die "$FILE is not inside a git repository"

rel=${abs#"$root"/}
[[ $rel != "$abs" ]] || die "$FILE is not inside the git repo at $root"

echo "Repo root:     $root"
echo "Repo-rel path: $rel"

git_() { git -C "$root" "$@"; }

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

describe() { git_ log -1 --format='%h %ad %an: %s' --date=short "$1"; }

# 1) Uncommitted changes vs HEAD, if any.
if git_ rev-parse --verify -q HEAD >/dev/null \
   && ! git_ diff --quiet HEAD -- "$rel" 2>/dev/null; then
  show_at HEAD "$rel" "$tmpdir/head-$base"
  echo "Uncommitted changes: opening working copy vs HEAD"
  meld --label "working copy" --label "HEAD $(git_ rev-parse --short HEAD)" \
    "$abs" "$tmpdir/head-$base" || true
  ask "Continue?" "Continue to committed history?" || exit 0
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

  nf="$tmpdir/${new:0:8}-$base"
  of="$tmpdir/${old:0:8}-$base"
  show_at "$new" "$new_path" "$nf"
  show_at "$old" "$old_path" "$of"

  [[ $new_path == "$old_path" ]] || echo "  (renamed: $old_path -> $new_path)"
  echo "[$((i + 1))/$total] $new_desc  <-  $old_desc"
  meld --label "$new_desc" --label "$old_desc" "$nf" "$of" || true

  rm -f "$nf" "$of"
done

msg_info "Done. Reviewed $total comparison(s)."
