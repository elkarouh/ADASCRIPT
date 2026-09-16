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
ady2nim c TOOLS/ADA_INDENT/ada_indent.ady     # builds, and drops a symlink next to the source
ln -sf "$PWD/ADA_INDENT/ada_indent" ~/.local/bin/ada_indent
```

`ady2nim c` refreshes that symlink on every rebuild, so a link pointing at it
keeps working; one pointing straight into `~/.cache/adascript/` goes stale as
soon as the source changes and the hash with it.

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

Each has one, and all three need `ada_indent` on `PATH`:

```bash
cd vs_code && node test/test_extension.js
emacs -Q --batch -L emacs -l emacs/test-ada-indent.el -f ert-run-tests-batch-and-exit
cd vim && vim -es -N -u NONE -S test-ada-indent.vim
```

`make test` runs all three, and SKIPs rather than fails when node, emacs or vim
is absent — none of them is otherwise a dependency of this repo.

Every suite drives the **shipped** integration against the **real binary**: the
editor half is the file you would install (the VS Code one stubs only the
`vscode` API), and the indenter is the actual `ada_indent`. Expectations come
from the binary's own output wherever they could otherwise drift from it — how
wide an indent is, is the indenter's business, not the tests'.

They check the same short list of properties, which is the point of having
three: reindenting the whole buffer agrees with piping the file through the
binary; an already-indented buffer is a fixpoint; a region reindent leaves the
lines outside it alone; a line opened inside a block lands at the body indent
(the neutral-token probe); a line that becomes a bare `else` snaps left while a
word merely ending in `e` does not; and **a warm state cache produces the same
result as a cold run**, which is the property the whole cache design rests on.
The Emacs suite additionally pins the invalidation rule from both sides —
re-whitespacing the cache line keeps the cache, editing above it drops it —
because that is the one place the strict `<` could be "corrected" into a bug.

Each suite was mutation-checked when written, which is the only evidence that a
green test is testing anything: breaking the blank-line probe, emptying the
dedent-keyword list, or relaxing the cache's "strictly above" guard each makes
the relevant tests fail. Four of the ten VS Code checks failed on first run —
all four wrong expectations of mine rather than bugs, which is what the
"take the expectation from the binary" rule above is for.
