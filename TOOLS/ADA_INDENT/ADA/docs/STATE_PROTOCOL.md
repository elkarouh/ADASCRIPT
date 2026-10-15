# Incremental mode and the state protocol

Editors that re-indent one line at a time can drive `ada_indent` incrementally.

## How incremental mode works

`ada_indent` is a **stack machine**: the indent of line *N* depends on every
opener/closer above it (see "The model" in [INDENTATION.md](INDENTATION.md)). A naive editor integration must
therefore feed lines *1..N* to the indenter on every keystroke — O(N) work per
keypress, which crawls on a 5,000-line file.

The `--state` / `--emit-state` flags turn that O(N)-per-keypress cost into
O(*distance moved since the last edit*). The idea is a **resumable checkpoint**:
the indenter's entire working memory can be dumped to a string after any line and
restored before processing the next, so you never reprocess a prefix you have
already seen.

### The wire protocol

The indenter's state is the `Indenter` object's 21 fields (the block stack, the
paren stack, the continuation flags, the condition tracker — see `Dump_State` in
`src/indenter.adb`). Two flags expose it on the normal stdin → stdout pipe:

- **`--emit-state`** — after each reindented line, print one extra line
  `##STATE:<blob>`, where `<blob>` is the serialized state *as of that line*.
  The blob is an opaque, single-line, `|`-delimited `key=value` string:

  ```
  package Foo is
  ##STATE:stack=PKG:Foo|pd=0|ps=F|cf=F|pl=|fn=Foo|sn=|ln=1|pi=F|cs=0|cb=0|cvb=0|ic=F|vb=0|psk=|pc=F|al=0|pnl=0|pnld=-1|ppl=0
     procedure Bar;
  ##STATE:stack=PKG:Foo|pd=0|ps=F|cf=F|pl=|fn=Bar|sn=|ln=2|pi=F|cs=0|cb=0|cvb=0|ic=F|vb=1|psk=|pc=F|al=0|pnl=0|pnld=-1|ppl=0
  ```

- **`--state <blob>`** — initialise the indenter from a `<blob>` instead of from
  an empty stack, then process stdin as usual. Output is identical to what you
  would get had those earlier lines actually been piped in.

The two are exact inverses: feeding line *K+1* with `--state <blob-for-K>`
produces byte-for-byte the same result (and the same next blob) as piping
lines *1..K+1* from scratch. That equivalence is what makes the cache safe.

### What a client does with it

`lsp/ada_indent_proxy.py` is the reference client. Per open document it keeps
the last blob and the number of lines that blob covers, and on each request:

1. **Decides whether the cache is usable.** It is usable when the request
   starts at or below the first line not covered by the blob. Editing happens
   top-to-bottom, so the common case -- type a line, press Enter, type the next
   -- hits the cache.
2. **Picks the slice to send.** On a hit, the lines after the covered ones
   through the requested line, with `--state <blob>`; on a miss, everything
   from line 1, with no `--state`.
3. **Runs `ada_indent --emit-state`.** Every input line comes back as its
   indented text followed by its `##STATE:` line, so the output is read two
   lines at a time.
4. **Refreshes the cache** with the blob *before* the last line fed. That line
   is the one the editor is about to re-indent; an edit to it must not discard
   what was read above it.

### Keeping the cache honest

A blob covering lines *1..K* is only valid while those lines are unchanged. Any
edit that starts on a line above *K+1* (that is, on a covered line) drops it;
edits further down keep it. A full-text `didChange` drops it too.
