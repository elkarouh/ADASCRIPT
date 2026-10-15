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

### What Emacs does with it

`ada-indent.el` keeps two buffer-local variables:

| variable                  | meaning                                            |
|---------------------------|----------------------------------------------------|
| `ada-indent--state`       | the last `##STATE:` blob captured, or `nil`        |
| `ada-indent--state-lnum`  | the line number that blob was captured *after*      |

On each call to `ada-indent--column` (the function behind `RET`/`TAB`):

1. **Decide whether the cache is usable.** It is usable when a blob exists and
   the cursor is *below* the cached line (`ada-indent--state-lnum < current
   line`). Editing happens top-to-bottom, so the common case — type a line,
   press `RET`, type the next — always hits the cache.
2. **Pick the slice to send.**
   - *Cache hit:* send only the lines from `ada-indent--state-lnum + 1` through
     the current line, prefixed with `--state <blob>`.
   - *Cache miss* (first indent in the buffer, or cursor jumped upward): send the
     whole prefix `1..N` with no `--state`.
3. **Run `ada_indent … --emit-state`,** split the output into code lines and
   `##STATE:` lines.
4. **Refresh the cache:** store the last blob and set `ada-indent--state-lnum`
   to the current line.
5. **Return** the indent column of the last code line to `indent-line-to`.

### Keeping the cache honest

A checkpoint for line *K* is only valid if lines *1..K* have not changed.
The mode installs `ada-indent--invalidate-cache` on `before-change-functions`.

Any change on or above line *K* clears it -- the condition is `<=`:

```
(<= (line-number-at-pos beg) ada-indent--state-lnum)
```

with one exemption: the package's own reindentation. Computing line *K*'s
column caches the state after *K*, and the very next thing that happens is
`indent-line-to` rewriting line *K*'s indentation -- an edit at the cache point
that must not wipe the cache it just set. Those rewrites go through
`ada-indent--indent-to`, which binds `ada-indent--reindenting` so the
invalidation hook lets them pass. So:

- Our own reindent of line *K*: **cache kept** ✓
- Edit on lines *K+1, K+2, …* -- forward typing: **cache kept** ✓
- Any other edit on lines *1..K* -- typing on line *K* itself, or going back
  to change earlier code: **cache cleared** ✓

Steady-state forward editing keeps the cache alive across every keystroke;
only an edit at or above the cache point pays a one-time full-prefix rescan.

The net effect: steady-state editing costs one short `ada_indent` invocation
over just the handful of lines since your last keystroke, regardless of how large
the file is — while a jump to the top of a big buffer pays a one-time
full-prefix scan and then resumes incremental speed.

(One small subtlety re-stated: a blank current line is probed with a neutral
token `x` before being sent, so the indenter reports the enclosing block's body
indent instead of column 0. The probe is never inserted into the buffer.)
