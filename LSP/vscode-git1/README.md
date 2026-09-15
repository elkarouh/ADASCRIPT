# vscode-git1 — Single-File Version Control for VS Code

VS Code integration for [git1](../../EXAMPLES/git1.ady): each tracked file
gets its own private git repo under `.git1/.g1_<name>`, independent of any
directory-level repository.

## Features

- **Status bar** — shows branch name and dirty state for git1-tracked files
- **git1: Start Tracking** — `git1 init` the current file
- **git1: Commit** — stage + commit with a message prompt
- **git1: Show Diff** — open the diff in a new tab
- **git1: Show Log** — last 30 commits in a new tab
- **git1: Status** — quick status in an info message
- **git1: Stop Tracking** — `git1 rm -f` with confirmation dialog

All commands are available from the Command Palette (`Ctrl+Shift+P`) when a
git1-tracked file is open.

## Prerequisites

- **`git1`** binary on your PATH (compile from `EXAMPLES/git1.ady` or install
  `~/bin/git1.sh`)
- **`git`** (standard git — git1 uses it under the hood)

## Install

From the extension directory:

```bash
cd LSP/vscode-git1
npm install
```

Then in VS Code: `Ctrl+Shift+P` → "Developer: Install Extension from
Location..." → select the `vscode-git1` folder.

Or package as a `.vsix`:

```bash
npx vsce package                              # vscode-git1-<version>.vsix
code --install-extension vscode-git1-*.vsix
```

The version in the filename is the one in `package.json`, so the glob saves
keeping this line in step with it.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `git1.program` | `git1` | Path to the git1 binary |
| `git1.container` | `.git1` | Container directory name |

## How it works

The extension detects git1-tracked files by checking for
`.git1/.g1_<filename>/HEAD` next to the open file.  When found, all git
commands are run with `--git-dir` and `--work-tree` pointed at that file's
private repo — the same approach as `git1.el` for Emacs.

Unlike the Emacs version, which hooks into `vc-git` at a low level to make
the built-in VC commands work transparently, the VS Code extension provides
its own command set (`git1.commit`, `git1.diff`, etc.) since VS Code's
built-in Git extension doesn't have an equivalent hook point.

## Comparison with git1.el

| | git1.el (Emacs) | vscode-git1 |
|---|---|---|
| Integration depth | Hooks into `vc-git` — all VC commands work | Own command set via Command Palette |
| Status display | Mode line (` git1`) | Status bar with branch + dirty |
| Commit | `C-c g c` / `C-x v v` | Command Palette → git1: Commit |
| Diff | `C-c g d` / `C-x v =` | Command Palette → git1: Show Diff |
| Log | `C-c g l` / `C-x v l` | Command Palette → git1: Show Log |
| Magit | `C-c g s` | Not applicable |
| Branch operations | Full (create, switch, adopt, delete) | Not yet — use `git1` CLI |
