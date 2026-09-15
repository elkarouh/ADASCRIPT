# Editor support for `ada_indent`

One directory per editor. All three drive the **same `ada_indent` binary**
over the same incremental protocol, and none of them reimplements the
indenter — they are the wiring, not the logic.

| | |
|---|---|
| [`emacs/`](./emacs) | `ada-indent.el` — a minor mode on `RET` and `TAB`, `indent-region-function`, and a `post-self-insert-hook` for the dedent snap |
| [`vim/`](./vim) | `ada-indent.vim` — sets `'indentexpr'`, so `==`, `gg=G`, `=ip`, `o`/`O` and `'indentkeys'` all route through the binary |
| [`vs_code/`](./vs_code) | a small extension — Format Document, Format Selection, and on-type formatting, calling the binary directly |

## Before any of them

Build the binary once and put it on `PATH`:

```bash
ady2nim c -o:~/.local/bin/ada_indent ADA_INDENT/ada_indent.ady
```

Each directory's header comment or README says how to load that editor's half.

## The one idea they share

`ada_indent` is **stateful** — it carries a stack of open blocks, so it cannot
indent a line in isolation. Replaying the file from the top on every keypress
is O(file size); instead the binary offers

- `--emit-state`, which interleaves a `##STATE:…` line after each output line,
- `--state S`, which resumes from one,

and each integration caches the last state per buffer, sends only the lines
since, and drops the cache when the buffer is edited **strictly above** the
cache point. Strictly, because the state captured after line N does not depend
on line N's own leading whitespace — `ada_indent` strips that before looking at
the line — so "at or above" would wipe the cache on the very edit that
indenting makes. That reasoning is written out in all three, because it is the
one place the three implementations could silently drift apart.

## Not here

[`../LSP/`](../LSP) is the fourth way in: a Python server speaking LSP, for
editors where that is the shortest path (Helix, Neovim's LSP client, an Emacs
running eglot). The three integrations here deliberately do not use it — each
talks to the binary itself, so an editor needs no Python and no server process.

## Tests

Only the VS Code extension has a runnable harness so far:

```bash
cd vs_code && node test/test_extension.js     # needs ada_indent on PATH
```

It drives the shipped `extension.js` against the real binary with a stubbed
editor API. The Emacs and Vim halves are exercised by hand.
