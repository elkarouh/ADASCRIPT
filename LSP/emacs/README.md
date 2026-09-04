# Adascript — Emacs Major Mode

`adascript-mode` is an Emacs major mode for [Adascript](https://github.com/elkarouh/adascript) (`.ady` files).

## Features

- **Syntax highlighting** — type declarations, tick attributes (`Color'First`), Ada/Adascript keywords, plus Python and Nim syntax via `nim-mode`
- **Indentation** — offside rule, inherited from `nim-mode`
- **Diagnostics, hover, completion** — via the Adascript language server (`adascript_ls.py`) through either **eglot** (built-in, Emacs 29+) or **lsp-mode** (third-party)
- **Bracket matching and auto-close** — inherited from `nim-mode`

## Requirements

| Requirement | Version |
|---|---|
| Emacs | ≥ 28.1 |
| `nim-mode` | ≥ 0.4.1 — `M-x package-install RET nim-mode` (MELPA) |
| Python | 3.13+ |
| pygls | ≥ 2.1.1 (`python3.13 -m pip install pygls`) |

`nim-mode` is not optional: `adascript-mode` derives from it, so without it
`(require 'adascript-mode)` fails with "Cannot open load file: nim-mode".

## Installation

### Manual

```elisp
(add-to-list 'load-path "/path/to/ADASCRIPT/LSP/emacs")
(require 'adascript-mode)
```

### use-package

```elisp
(use-package adascript-mode
  :load-path "/path/to/ADASCRIPT/LSP/emacs")
```

`.ady` files are associated with `adascript-mode` automatically via `auto-mode-alist`.

## LSP Setup

### eglot (Emacs 29+, built-in — recommended)

eglot is registered automatically when `adascript-mode` loads. To start it:

```elisp
;; Manually: open a .ady file, then M-x eglot

;; Or auto-start on every .ady file:
(add-hook 'adascript-mode-hook #'eglot-ensure)
```

### lsp-mode (third-party)

`lsp-mode` is registered automatically when both packages are loaded. To auto-start:

```elisp
;; Option A — via the customization variable:
(setq adascript-lsp-mode-auto-enable t)

;; Option B — manually add the hook:
(add-hook 'adascript-mode-hook #'lsp-deferred)
```

## Customization

| Variable | Default | Description |
|---|---|---|
| `adascript-python-command` | `"python3.13"` | Python interpreter used to start the server |
| `adascript-server-path` | `../adascript_ls.py` | Absolute path to `adascript_ls.py` |
| `adascript-lsp-mode-auto-enable` | `nil` | Auto-start lsp-mode in adascript buffers |

```elisp
(setq adascript-python-command "python3.13"
      adascript-server-path    "/absolute/path/to/ADASCRIPT/LSP/adascript_ls.py")
```

The default `adascript-server-path` resolves to the `adascript_ls.py` sitting one directory above this file (`LSP/adascript_ls.py`), which works when the repository is used as-is.

## Faces

Five custom faces can be themed independently:

| Face | Default | Applied to |
|---|---|---|
| `adascript-type-name-face` | `font-lock-type-face` | The `NAME` in `type NAME is …` |
| `adascript-tick-type-face` | `font-lock-type-face` | The type part of `Color'First` |
| `adascript-tick-attr-face` | `font-lock-builtin-face` | The attribute part of `Color'First` |
| `adascript-shell-face` | `font-lock-preprocessor-face` | The `shell:` / `shellLines:` keywords |
| `adascript-range-op-face` | `font-lock-operator-face`, or `font-lock-builtin-face` before Emacs 30 | The range operators `..` and `..<` |

## `git1.el` — `C-x v ...` on a git1-tracked file

`EXAMPLES/git1.ady` gives each tracked file its own private repository under
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
  :load-path "/path/to/ADASCRIPT/LSP/emacs"
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
| `C-x v v` `C-x v =` `C-x v l` | commit, diff, log | the file's git1 repo |
| `C-c g c` | `git1-commit` | save, then commit this file |
| `C-c g d` `C-c g l` `C-c g b` | diff, log, annotate | the file's git1 repo |
| `C-c g s` | `git1-magit-status` | Magit on that repo, if Magit is installed |

`M-x git1-init` starts tracking the file in the current buffer.

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

## Notes

- `'` is punctuation in the syntax table, so `Color'First` is not mis-lexed as the start of a string and an apostrophe in prose — `the command's output` inside a docstring — cannot open one either. `syntax-propertize` then promotes just the pairs that really delimit a string, so `'hello'` is still highlighted as one.
- Escaped quotes inside a prefixed string (`f"... \"x\" ..."`) are repaired after `nim-mode` runs: Nim reads `ident"..."` as a raw string literal where a backslash is not an escape, which would otherwise end the string early and invert the highlighting of the rest of the buffer.
- The mode derives from `nim-mode`, so its navigation commands work in `.ady` files.
