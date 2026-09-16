# git1 — version control for one file at a time

`git1.ady` gives every tracked file its own private git repository, named
after the file and kept in a `.git1` container beside it. Many tracked files
can share a directory without seeing each other, and none of them needs the
directory to be a repository.

It is written in **Adascript** and transpiles to Python and Nim like any
other `.ady` file. It is also the worked example behind
[DOCS/ADASCRIPT_FOR_SHELL.md](../DOCS/ADASCRIPT_FOR_SHELL.md) and §13.7 of
[the book](../DOCS/BOOK/15-case-studies.md): `cwd`, `env`, `shellExec:`,
`Path`, file tests and `shellLines:` all doing a real job rather than
demonstrating themselves.

## Contents

| | |
|---|---|
| [`git1.ady`](git1.ady) | the tool |
| [`git1.el`](git1.el) | Emacs VC integration, so `C-x v ...` works on a tracked file |
| [`vscode-git1/`](vscode-git1) | VS Code integration, the same idea as `git1.el` |

## Building

```bash
ady2nim GIT1/git1.ady              # transpile + compile (cached)
ady2nim GIT1/git1.ady -r -- ls     # compile if stale, then run
```

The shebang already carries `-d:release --opt:size`. Put the resulting
binary on your PATH as `git1`; the program reads its own name, so a copy
called something else prints that name in its messages and usage.

## Using it

```
git1 init <file>            start tracking <file>
git1 <file> [git args...]   run git in that file's repo (default: status)
git1 ls [dir]               list tracked files in a directory
git1 mv <old> <new>         rename a tracked file and its repo
git1 rm [-f] <file>         delete a file's history (keeps the file)
git1 adopt <file> <branch>  make <branch> the current branch, wholesale
git1 each <git args...>     run one git command in every repo here
git1 help                   the full usage text
```

```bash
git1 init notes.txt
git1 notes.txt commit -am "reworked the intro"
git1 notes.txt log --oneline
git1 each log -1 --oneline
```

Anything after the file name goes to git untouched, so the whole command set
is available -- log, diff, stash, tag, blame, rebase. Paths in those
arguments are read relative to the tracked file's directory, which is the
work tree.

## The layout on disk

```
notes.txt
config.yml
.git1/
    notes.txt/      a git repository, tracking notes.txt alone
    config.yml/     another, tracking config.yml alone
```

A repository is a directory named after the file it tracks. That is worth
knowing before you point a tool at the tree: `.git1/notes.txt` is a
directory whose name ends in the same extension as the file, and a sweep
that assumes otherwise will try to read it. `DOCS/check_quotes.py` learned
that the hard way.

## `adopt`, and why there is no merge

Merging a single file is a poor fit. A merge combines two versions, and with
no file boundary to separate the changes, two versions of one file conflict
readily -- edits one line apart already do. `git1 adopt <file> <branch>`
moves the current branch onto the winner wholesale instead, and offers to
delete the branches that lost: nothing is combined, so nothing can conflict.
What the branch held before stays reachable through `git1 <file> reflog`.

## `git1.el` — `C-x v ...` on a git1-tracked file in Emacs

`git1.ady` gives each tracked file its own private repository under
`.git1/`, reached through `GIT_DIR` and `GIT_WORK_TREE`. Emacs locates
repositories by filename instead — `vc-git-root` is literally
`(vc-find-root file ".git")` — so a git1 file looks unversioned to VC and
`C-x v ...` does nothing useful with it.

It can also do something actively wrong: a directory that sits inside an
ordinary git repo makes Emacs find *that* repo, which knows nothing about
the file, so `C-x v b c` would create the branch in the enclosing project.

`git1.el` fixes both, per file rather than per directory. It advises
`vc-git` so that a tracked file's own directory counts as a VC root, and
splices `--git-dir=` and `--work-tree=` into the git calls that follow.
Nothing is written to disk, and several tracked files in one directory work
at the same time — each buffer talks to its own repository.

```elisp
(use-package git1
  :load-path "/path/to/ADASCRIPT/GIT1"
  :demand t
  :hook (find-file . git1-maybe-enable)
  :config
  (git1-global-mode 1))
```

`git1-global-mode` installs the advice; `git1-maybe-enable` on `find-file`
turns on the buffer-local `git1-mode` for files that are tracked, which
lights the mode line and binds `C-c g`. Plain `(require 'git1)` and a call
to `git1-global-mode` work just as well.

What then works in a git1 buffer:

| Key | Command | Acts on |
|---|---|---|
| `C-x v b c` | `vc-create-branch` | the file's git1 repo |
| `C-x v b s` | `vc-switch-branch` | the file's git1 repo, branch names completed |
| `C-x v b l` | `vc-print-branch-log` | the file's git1 repo |
| `C-x v b a` | `git1-adopt` | replace the current branch with another, wholesale |
| `C-x v b d` | `git1-delete-branch` | delete a branch of that repo |
| `C-x v m` | `vc-merge` | the file's git1 repo (see below) |
| `C-x v v` `C-x v =` `C-x v l` | commit, diff, log | the file's git1 repo |
| `C-c g c` | `git1-commit` | save, then commit this file |
| `C-c g d` `C-c g l` `C-c g b` | diff, log, annotate | the file's git1 repo |
| `C-c g a` | `git1-adopt` | same command as `C-x v b a` |
| `C-c g s` | `git1-magit-status` | Magit on that repo, if Magit is installed |

Emacs itself binds only three commands under `C-x v b` — create, switch and
branch log. In a git1 buffer that map gains `a` and `d`; it *inherits* from
the stock one rather than replacing it, so the three keep working and
anything Emacs adds later appears too. Outside a git1 buffer nothing
changes: `C-x v b a` stays unbound.

`M-x git1-init` starts tracking the file in the current buffer.

`git1-adopt` is the one command here without a VC equivalent, and it exists
because merging a single file is a poor fit: a merge combines two versions,
and with no file boundary to separate the changes, two versions of one file
conflict readily — edits one line apart already do. `git1-adopt` moves the
current branch onto the winner wholesale instead and offers to delete the
branches that lost, so nothing is combined and nothing can conflict. It
runs `git1 adopt`, so the command line and the key do the same thing. What
the branch held before is reachable through `git1 <file> reflog`.

Branch commands name a directory rather than a file, since a branch belongs
to a repository. When several tracked files share a directory, the one
meant is the file whose buffer the command was invoked from.

Two things to know:

- `vc-dir` is not supported. It is inherently a per-directory view, and a
  directory holding several git1 files has no single repository to show.
  Use `git1 each status -s` from a shell instead.
- A repository is named after its file — `notes.txt` is tracked in
  `.git1/notes.txt` — and is confirmed by its `HEAD`. `git1-container`
  renames `.git1` itself if you changed it in `git1.ady`, and
  `git1-program` names the executable used by `git1-init`.

`git1.el` is independent of `adascript-mode` — it needs neither `nim-mode`
nor the language server.
