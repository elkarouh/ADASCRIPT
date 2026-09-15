# ada-indent for VS Code

Ada indentation driven by the `ada_indent` binary — the same one behind
[`ada-indent.el`](../emacs/ada-indent.el) and
[`ada-indent.vim`](../vim/ada-indent.vim),
and wired up the same way: **the extension calls the binary directly.** No
language server, no Python, no npm dependencies. (`ADA_INDENT/LSP/` exists for
editors that would rather speak LSP; VS Code does not need to.)

## What you get

| | |
|---|---|
| **Format Document** (`⇧⌥F` / `Ctrl+Shift+I`) | reindent the whole file |
| **Format Selection** (`Ctrl+K Ctrl+F`) | reindent the selected lines |
| **Enter** | indents the new line to its block |
| typing a bare dedenting keyword | `end`, `else`, `when`, `record`, … snaps left on its final character, no extra keypress |
| **Ada Indent: Reindent Whole Buffer** | the same as Format Document, as a command you can bind a key to |

Format on save works too — it goes through Format Document:

```jsonc
"[ada]": { "editor.formatOnSave": true }
```

## Install

**1. Build the binary and put it on `PATH`.**

```bash
ady2nim ADA_INDENT/ada_indent.ady               # compiles into ~/.cache/adascript/
ln -s ~/.cache/adascript/cache-*/.ada_indent ~/.local/bin/ada_indent
```

or let `ady2nim` place it directly:

```bash
ady2nim c -o:~/.local/bin/ada_indent ADA_INDENT/ada_indent.ady
```

**2. Install the extension.** For everyday use, symlink this directory into
your extensions folder and restart VS Code:

```bash
ln -s "$PWD" ~/.vscode/extensions/ada-indent
```

To hack on it instead, open this directory in VS Code and press `F5` — that
launches an Extension Development Host with it loaded.

There is nothing to `npm install`: the extension uses only the `vscode` API and
Node's own `child_process`.

## Settings

| Setting | Default | |
|---|---|---|
| `adaIndent.program` | `ada_indent` | name or full path of the binary; a bare name is looked up on `PATH` |
| `adaIndent.enableStateCache` | `true` | see below — turn off only to diagnose a suspected stale cache |

The extension also sets, for Ada buffers only, `editor.insertSpaces`,
`editor.tabSize: 2` (what `ada_indent` emits) and `editor.formatOnType: true`
(without which VS Code never asks for the on-type dedent snap). Override any of
them in your own `"[ada]"` block.

## How it works, and why it is fast

`ada_indent` is **stateful**: it carries a stack of open blocks, so it cannot
indent a line in isolation — naively it has to replay every line above the one
you are editing, which is O(file size) per keypress.

The binary therefore speaks an incremental protocol:

- `--emit-state` interleaves a `##STATE:…` line after each output line,
  encoding the full indenter state at that point;
- `--state S` starts from a captured state instead of from line 1.

The extension keeps that state per document, along with the line it was
captured after. The next format starts from there and sends only the lines
since, which is O(distance). The cache is dropped as soon as the document is
edited *above* the cache point.

Strictly above: the state captured after line N is derived from lines 1..N and
is unaffected by re-whitespacing line N itself, because `ada_indent` strips
leading whitespace before looking at a line. Using "at or above" instead would
wipe the cache on the very edit that formatting makes, leaving it useless. This
is the same rule, for the same reason, as in the Emacs and Vim versions.

Two more details worth knowing:

- **Edits replace leading whitespace only,** and only on lines whose
  indentation actually changed. An already-correct file yields no edits at all,
  and the ones it does yield leave the cursor and selection alone.
- **On-type formatting asks the binary as little as possible.** The trigger
  characters are Enter plus the final letter of each dedenting keyword
  (`defnspot`), and even then the extension checks that the line has become
  exactly one of those keywords before running anything.

## Tests

```bash
node test/test_extension.js        # or: npm test
```

`make test` runs it too, and SKIPs when node is missing. The Emacs and Vim
halves have their own suites checking the same properties; see
[`../README.md`](../README.md).

Ten checks against the **real binary** — `ada_indent` has to be on `PATH`. The
editor API is stubbed (`test/vscode-stub.js`), but the code under test is the
shipped `extension.js`, so what passes here is what the extension does. Among
them: Format Document agrees with piping the file through `ada_indent`
directly; a canonical file produces zero edits; formatting is a fixpoint; a
selection ending at column 0 does not pull that line in; **and a warm state
cache gives byte-identical edits to a cold run**, which is the property the
whole cache design rests on.
