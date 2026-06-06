# Simplified Ada Indentation Grammar

`ada_indent.ady` re-indents Ada source code. It is written in **Adascript** and
transpiles to Python and Nim like any other `.ady` file.

It is **not** a full Ada parser. Indentation does not require understanding
expressions, types, or semantics — only the keywords that **open**, **close**,
or **split** an indented block. This document specifies that simplified grammar
and how it drives the indenter.

## Running

Compile once (the shebang already encodes `-d:release --opt:speed`), then run
the resulting binary directly:

```bash
py2nim ADA_INDENT/ada_indent.ady            # transpile + compile (cached)
py2nim ADA_INDENT/ada_indent.ady -r -- file.adb   # compile if stale, then run
cat file.adb | py2nim ADA_INDENT/ada_indent.ady -r  # reindent from stdin
```

`py2nim` stores the binary in `~/.cache/hparsec/` and skips recompilation when
neither the source nor the generated `.nim` have changed.

## Tests

The self-tests live in `test_ada_indent.ady`, which imports the indenter as a
library (`nimport ada_indent` auto-transpiles the sibling `.ady`) and runs it
against a table of messy-input → canonical-output cases:

```bash
py2nim ADA_INDENT/test_ada_indent.ady -r    # compile if stale, run all cases
```

The core (the `Indenter` class plus the lexical helpers) is pure Adascript and
transpiles to both Python and Nim.

## Emacs integration (format-all)

[`format-all`](https://github.com/lassik/emacs-format-all-the-code) can run
`ada_indent` as a buffer formatter. The tool reads Ada source on stdin and
writes re-indented source to stdout, which is exactly the interface
`format-all` expects.

**Step 1 — install the binary.**  Compile once and symlink the cached binary
onto your `PATH`:

```bash
py2nim ADA_INDENT/ada_indent.ady          # compile; binary lands in ~/.cache/hparsec/
ln -s ~/.cache/hparsec/cache-*/ada_indent ~/.local/bin/ada-indent
```

Or let `py2nim` install it for you with an explicit output path:

```bash
py2nim c -o:~/.local/bin/ada-indent ADA_INDENT/ada_indent.ady
```

**Step 2 — register the formatter in Emacs.**  Add to your `init.el` (or the
relevant `use-package` block):

```elisp
(define-format-all-formatter ada-indent
  (:executable "ada-indent")
  (:install "Compile ADA_INDENT/ada_indent.ady with py2nim, then put ada-indent on PATH")
  (:languages "Ada")
  (:features)
  (:format (format-all--buffer-easy executable)))

(add-hook 'ada-mode-hook 'format-all-mode)
(add-hook 'ada-ts-mode-hook 'format-all-mode)
```

`format-all--buffer-easy` pipes the buffer through the command and replaces
the buffer with its stdout, which is the standard pattern for formatters that
read stdin and write stdout.

**Step 3 — use it.**  Open any `.adb` / `.ads` file and run `M-x
format-all-buffer`, or enable `format-all-mode` to reformat on save
automatically.

### Indent as you type (electric)

`format-all` reformats the *whole buffer* on demand (or on save). For
indentation that happens **while you type**, wire `ada_indent` up as Emacs'
`indent-line-function` and bind `RET` to a custom newline-and-indent command.

The one thing to know: `ada_indent` is **stateful** — it carries a stack of
open blocks, so it cannot indent a line in isolation. Naively it must see every
line above the current one. For large files this is slow.

`ada_indent` therefore supports two incremental flags:

- `--emit-state` — after each output line, also emits a `##STATE:…` line
  encoding the full indenter state.
- `--state STATE` — start from a previously captured state instead of the
  beginning of the file.

The Emacs integration below caches the state per buffer. On the first indent of
line N it pipes *all* lines 1..N through `ada_indent --emit-state` and saves the
returned state. On every subsequent indent it starts from that cached state and
pipes only the lines between the cache point and the current line — O(distance)
instead of O(N). The cache is invalidated automatically whenever the buffer is
edited before the cache point.

(Blank lines are probed with a neutral token so they pick up the enclosing
block's indent instead of snapping to the left margin.)

Two things matter for the key binding to actually take effect:

1. **Use a minor-mode keymap, not `local-set-key`.** Minor-mode keymaps
   outrank the major-mode map, so they reliably own `RET` even when the major
   mode (or `electric-indent-mode`) also binds it.
2. **Hook both `ada-mode` and `ada-ts-mode`.** If you have the tree-sitter
   Ada grammar installed, your files open in `ada-ts-mode`, and a hook on
   `ada-mode-hook` alone never runs.

```elisp
(require 'subr-x)   ; string-blank-p, string-trim-left (built in on Emacs 27+)

;;; Per-buffer state cache — avoids reprocessing the whole file every keypress.
(defvar-local ada-indent--state nil
  "Serialized Indenter state after line `ada-indent--state-lnum', or nil.")
(defvar-local ada-indent--state-lnum 0
  "Line number for which `ada-indent--state' was last captured.")

(defun ada-indent--invalidate-cache (beg _end)
  "Clear the state cache when a change falls strictly before the cache point."
  (when ada-indent--state
    (when (< (line-number-at-pos beg) ada-indent--state-lnum)
      (setq-local ada-indent--state nil ada-indent--state-lnum 0))))

(defun ada-indent--column ()
  "Column `ada_indent' assigns to the current line in its buffer context."
  (let* ((bol   (line-beginning-position))
         (cur   (buffer-substring-no-properties bol (line-end-position)))
         ;; Blank line: probe with a neutral token to get the block-body indent.
         (probe (if (string-blank-p cur) "x" cur))
         (lnum  (line-number-at-pos bol))
         ;; Start from cached state when it was captured before this line.
         (use-cache (and ada-indent--state (< ada-indent--state-lnum lnum)))
         (input-start (if use-cache
                          (save-excursion
                            (goto-char (point-min))
                            (forward-line ada-indent--state-lnum)
                            (point))
                        (point-min)))
         (input    (concat (buffer-substring-no-properties input-start bol) probe))
         (cmd-args (if use-cache
                       (list "--state" ada-indent--state "--emit-state")
                     (list "--emit-state")))
         (out      (with-temp-buffer
                     (insert input)
                     (apply #'call-process-region (point-min) (point-max)
                            "ada_indent" t t nil cmd-args)
                     (buffer-string)))
         (all-lines   (split-string out "\n" t))
         (state-lines (seq-filter (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (code-lines  (seq-remove (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (last-state  (car (last state-lines)))
         (last        (car (last code-lines))))
    ;; Save state so the next call can skip everything up to this line.
    (when last-state
      (setq-local ada-indent--state      (substring last-state 8)
                  ada-indent--state-lnum lnum))
    (if last (- (length last) (length (string-trim-left last))) 0)))

(defun ada-indent-line ()
  "Indent the current line with `ada_indent'."
  (interactive)
  (indent-line-to (ada-indent--column)))

(defun ada-newline-and-indent ()
  "Reindent the current line, insert a newline, then indent the new line."
  (interactive)
  ;; `indent-line-to' runs `back-to-indentation', which moves point to the
  ;; start of the line's text.  Wrap it in `save-excursion' so point stays
  ;; where RET was pressed; otherwise `newline' splits at the line start and
  ;; the blank line ends up *above* the current line.
  (save-excursion
    (indent-line-to (ada-indent--column)))  ; fix the line we are leaving
  (newline)
  (indent-line-to (ada-indent--column)))    ; indent the fresh line

(defun ada-indent--post-insert ()
  "Snap line left as soon as it becomes a bare dedenting keyword."
  ;; Only reindent when the whole trimmed line is exactly one of the
  ;; keywords that step left relative to their enclosing block.  Fired via
  ;; post-self-insert-hook so the snap happens on the final character of the
  ;; keyword, with no extra keypress needed.
  (let ((content (string-trim
                  (buffer-substring-no-properties
                   (line-beginning-position) (line-end-position)))))
    (when (member content
                  '("end" "else" "elsif" "when" "exception"
                    "begin" "is" "then" "private" "limited"
                    "record" "loop" "do" "select"))
      (save-excursion
        (indent-line-to (ada-indent--column))))))

(defvar ada-indent-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "RET")      #'ada-newline-and-indent)
    (define-key map (kbd "<return>") #'ada-newline-and-indent)
    (define-key map (kbd "C-m")      #'ada-newline-and-indent)
    (define-key map (kbd "TAB")      #'ada-indent-line)
    map)
  "Keymap for `ada-indent-mode' — minor-mode maps outrank the major map.")

(define-minor-mode ada-indent-mode
  "Use the external `ada_indent' program for indentation."
  :lighter " AdaInd"
  :keymap ada-indent-mode-map
  (if ada-indent-mode
      (progn
        (setq-local indent-line-function #'ada-indent-line)
        ;; Disable electric-indent entirely: it reindents the line you just left
        ;; and moves point back, fighting our RET handler.
        (electric-indent-local-mode -1)
        ;; Snap dedenting keywords left as each one is completed.
        (add-hook 'post-self-insert-hook  #'ada-indent--post-insert      nil t)
        ;; Invalidate the state cache whenever the buffer is edited before it.
        (add-hook 'before-change-functions #'ada-indent--invalidate-cache nil t))
    (remove-hook 'post-self-insert-hook   #'ada-indent--post-insert          t)
    (remove-hook 'before-change-functions #'ada-indent--invalidate-cache     t)))

;; Cover BOTH classic and tree-sitter Ada modes.
(add-hook 'ada-mode-hook    #'ada-indent-mode)
(add-hook 'ada-ts-mode-hook #'ada-indent-mode)

;; Retroactively enable in Ada buffers opened before this config loaded.
(dolist (buf (buffer-list))
  (with-current-buffer buf
    (when (derived-mode-p 'ada-mode 'ada-ts-mode)
      (ada-indent-mode 1))))
```

Now `RET` reindents the current line, inserts a newline, and places point at
the correct indentation on the new line. `TAB` reindents the current line.
Typing a bare dedenting keyword (`end`, `else`, `elsif`, `when`, `exception`,
`begin`, `is`, `then`, …) snaps the line left on the final keystroke of the
keyword — no extra `TAB` needed.


For *continuous* reformatting as you edit anywhere in the line — not just on
newline — add [`aggressive-indent-mode`](https://github.com/Malabarba/aggressive-indent-mode)
(`(add-hook 'ada-mode-hook #'aggressive-indent-mode)`). Be aware of the
trade-off: each reindent spawns one `ada-indent` process over the buffer prefix,
so `aggressive-indent` (which reindents whole regions on every change) is fine
for small files but gets sluggish on large ones. For large files prefer
electric indent on newline plus `format-all` on save.

> **Ready-made package.** The whole snippet above is also shipped as
> [`ada-indent.el`](./ada-indent.el) in this directory. Put the directory on
> your `load-path` and `(require 'ada-indent)` — no need to paste the elisp into
> your init file. It adds a `defcustom ada-indent-program` (the binary path) and
> only activates when that binary is found on `PATH`.

## How incremental mode works

`ada_indent` is a **stack machine**: the indent of line *N* depends on every
opener/closer above it (see "The model" below). A naive editor integration must
therefore feed lines *1..N* to the indenter on every keystroke — O(N) work per
keypress, which crawls on a 5,000-line file.

The `--state` / `--emit-state` flags turn that O(N)-per-keypress cost into
O(*distance moved since the last edit*). The idea is a **resumable checkpoint**:
the indenter's entire working memory can be dumped to a string after any line and
restored before processing the next, so you never reprocess a prefix you have
already seen.

### The wire protocol

The indenter's state is the `Indenter` object's 14 fields (the block stack, the
paren stack, the continuation flags, the condition tracker — see `dump_state` in
`ada_indent.ady`). Two flags expose it on the normal stdin → stdout pipe:

- **`--emit-state`** — after each reindented line, print one extra line
  `##STATE:<blob>`, where `<blob>` is the serialized state *as of that line*.
  The blob is an opaque, single-line, `|`-delimited `key=value` string:

  ```
  package Foo is
  ##STATE:stack=PKG|pd=0|ps=F|pi=F|cs=0|cb=0|cvb=0|ic=F|vb=0|psk=|pc=F|al=0|pnl=0|pnld=-1
     procedure Bar;
  ##STATE:stack=PKG|pd=0|ps=F|pi=F|cs=0|cb=0|cvb=0|ic=F|vb=1|psk=|pc=F|al=0|pnl=0|pnld=-1
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

The condition is **strict `<`**, not `<=`:

```
(< (line-number-at-pos beg) ada-indent--state-lnum)
```

The state after line *K* is computed from the *logical content* of lines
*1..K* — the indenter strips leading whitespace before analysis. So rewriting
line *K*'s indentation (which is exactly what `indent-line-to` does on the
very line we just cached) does **not** invalidate the state. Using `<=` would
cause every `indent-line-to` call to clear the cache the instant it was set,
making it useless. With `<`:

- Edit on line *K* (the cached line) — indentation fix or continued typing: **cache kept** ✓
- Edit on lines *K+1, K+2, …* — forward typing: **cache kept** ✓
- Edit on lines *1..K−1* — going back and changing earlier code: **cache cleared** ✓

The net effect: steady-state forward editing (the common case in both normal
and `aggressive-indent` modes) keeps the cache alive across every keystroke.
Only a backwards jump that edits above the cache point pays the one-time
full-prefix rescan.

The net effect: steady-state editing costs one short `ada_indent` invocation
over just the handful of lines since your last keystroke, regardless of how large
the file is — while a jump to the top of a big buffer pays a one-time
full-prefix scan and then resumes incremental speed.

(One small subtlety re-stated: a blank current line is probed with a neutral
token `x` before being sent, so the indenter reports the enclosing block's body
indent instead of column 0. The probe is never inserted into the buffer.)

## The model: a block stack

Indentation in Ada is a function of how many blocks are currently open. The
indenter keeps a **stack of frames**, one per open construct. For each physical
line:

1. The line is classified by its **leading keyword** and its **final token**
   (after stripping `--` comments and a trailing `;`).
2. The **display indent** is the stack depth — adjusted down by one for keywords
   that align with their opener rather than the block body.
3. The stack is then updated (push / pop) for the lines that follow.

Indent width defaults to **2 spaces**, set by `INDENT_WIDTH` (change it there
for the GNAT-conventional 3, or any other width).

## Formal grammar (EBNF)

This is the indentation-relevant subset of Ada the indenter recognises, in
EBNF. Each production is annotated with its **stack action** — what the
indenter pushes (`▶`) or pops (`◀`). Only the keywords shown here affect
indentation; any other line is an `ordinary_line` and inherits the current
depth.

```ebnf
source          ::= { line }

line            ::= opener | closer | splitter | ordinary_line | blank

(* ---- openers: push a frame, body indents one level deeper ---- *)

opener          ::= spec_is | function_is | declare_open | if_open | loop_open
                  | case_open | record_open | select_open | do_open
                  | when_open

spec_is         ::= ( "package" | "procedure" | "task"
                    | "protected" | "type" | … ) … "is"            (* ▶ PKG     *)
function_is     ::= "function" … "is"                              (* deferred: *)
   (* next line begins with "("  → expression function, indent +1, no push     *)
   (* otherwise                  → real body, ▶ PKG retroactively              *)
declare_open    ::= [ label ":" ] "declare"                        (* ▶ DECLARE *)
if_open         ::= "if" … "then"                                  (* ▶ IF      *)
loop_open       ::= [ label ":" ] [ iteration_scheme ] "loop"      (* ▶ LOOP    *)
case_open       ::= "case" … "is"                                  (* ▶ CASE    *)
record_open     ::= "type" … "is" [ "tagged" ] "record"           (* ▶ RECORD  *)
select_open     ::= "select"                                       (* ▶ SELECT  *)
do_open         ::= ( "accept" … | "return" … ) "do"              (* ▶ DO      *)
when_open       ::= "when" choices "=>"                            (* ◀ WHEN? ▶ WHEN *)

(* ---- closer: align with the opener's header ---- *)

closer          ::= "end" [ "if" | "loop" | "case" | "record"
                          | "select" | name ] ";"                  (* ◀ WHEN* then ◀ 1 *)

(* ---- splitters: align with opener, frame stays open ---- *)

splitter        ::= "elsif" … "then"      (* part of IF; does NOT push a 2nd IF *)
                  | "else"                (* part of IF or SELECT               *)
                  | "exception"           (* part of BLOCK                      *)
                  | "or"                  (* part of SELECT                     *)
                  | "private"             (* part of package spec              *)

(* ---- begin: context-sensitive ---- *)

begin_line      ::= "begin"
   (* if top frame is PKG or DECLARE  → splitter, convert that frame to BLOCK *)
   (* otherwise                       → opener,   ▶ BLOCK (nested block stmt) *)

(* ---- everything else ---- *)

ordinary_line   ::= ? any line whose lead/last tokens match none of the above ?
blank           ::= ? whitespace only ?  (* emitted verbatim, stack unchanged *)
```

Notes on the annotations:

- `when_open` first pops a preceding `WHEN` (closing the previous `case`
  alternative or exception handler) and then pushes its own — that is what lets
  consecutive `when` lines sit at the same column.
- `closer` pops **all** trailing `WHEN` frames before popping the one enclosing
  construct, so `end case;` dedents past both the final `when` and the `case` in
  a single step.
- Recognition is purely lexical: the **lead** token and the **last** token of a
  line (after stripping a `--` comment and a trailing `;`). No expression or
  type parsing is performed.

The tables below restate the same rules keyword-by-keyword, with examples.

## The simplified grammar

Keywords are grouped by their effect on indentation. `LAST` is the final token
of the line; `LEAD` is the first.

### Openers — push a frame (the body below indents one level deeper)

| Trigger | Frame | Example |
|---|---|---|
| `LAST = is` (and `LEAD ≠ case`) | `PKG` | `package P is`, `procedure Q is`, `function F return T is`, `task body T is` |
| `LEAD = case` and `LAST = is` | `CASE` | `case X is` |
| `LAST = then` (and `LEAD ≠ elsif`) | `IF` | `if C then` |
| `LAST = loop` | `LOOP` | `while C loop`, `for I in 1 .. N loop`, `Outer : loop` |
| `LAST = record` (and `LEAD ≠ null`) | `RECORD` | `type R is record` |
| `LAST = select` | `SELECT` | `select` |
| `LAST = do` | `DO` | `accept E do`, `return R : T do` |
| `LEAD = declare` | `DECLARE` | `declare`, `Blk : declare` |
| `LEAD = when` | `WHEN` | `when A =>`, `when others =>` |

A `function … is` header is **deferred**, not pushed immediately: a function may
open a real body *or* be an **expression function** (`function F return T is`
followed by a parenthesised expression). The decision is made on the next
non-blank line — if it begins with `(`, the line is an expression body that
indents one level and pushes **no** frame; otherwise the `PKG` frame is pushed
retroactively and the body indents normally. This keeps the declarations after
an expression function from drifting one level to the right:

```ada
function Image return String is
  (Compute (A, B'Image));   -- indented one level, no frame opened
procedure P is              -- back at the outer level
begin
  null;
end P;
```

### Multi-line conditions

When an `if` or `elsif` condition spans more than one line (no closing `then`
on the opener line), continuation lines are indented one level deeper than the
`if`/`elsif`. The `then` keyword, whenever it appears (on its own line or as
the last token of a continuation line), snaps back to align with the opener and
pushes the `IF` frame as usual:

```ada
if FTFX.The_Flight_Status = Cancelled
    and then Action_Info.Event = IFPS_New_Flight   -- +1 level
    and then Chained_TACT_Id (...) = None          -- +1 level
  then                                              -- aligns with 'if'
    Reset;                                          -- +1 from 'then' depth
  elsif Other_Condition
    and then Extra_Guard                            -- +1 level
  then
    Handle;
  end if;
```

The `and` / `or` / `xor` connectives join condition terms and sit at this base
continuation level. A **term continuation** (a line starting with a different
operator such as `>=`, `&`, `+`, or opening an argument list with `(`) continues
the *previous* term across the break, so it nests one level deeper:

```ada
if A
    and then Take_Off_Time (X)                      -- +1 (connective)
      >= Take_Off_Time (Y)                          -- +2 (continues the term)
    and then Curtain_Index_May_Differ               -- +1 (connective)
      (Left (Normal) (FTFM),                        -- +2: '(' opens the call's args
       Right (FTFM))                                -- arguments align under the first
  then
```

If a condition opens a **parenthesis** that spans lines, the lines inside it are
aligned to that parenthesis (with the operator-extra rule below) rather than
flattened to the condition level, so nested boolean groups show their depth:

```ada
if Event_Category (Action_Info.Event) = External_Reset
    and then Departure.Ready_To_Depart (FTFX.Departure_Info)
    and then (Ready_Time_Deterioration
                or else (SAM_Status.Is_Sent (FTFX.SAM_Data)
                           and then SAM_Status.Get_CTOT (FTFX.SAM_Data)
                           - Departure.Taxi_Time (FTFX.Departure_Info) < Time.Clock))
  then
```

### Statement continuation

A logical statement or declaration split across several physical lines has its
continuation lines indented one level deeper. A line is treated as **continued**
when it is non-empty, does not end in `;`, does not end in `=>`, does not end in
`:` (a block/loop label such as `Find_Model :` or `Log_Changes:` is a complete
prefix, so the labelled construct on the next line stays at the label's level),
is not a lone splitter/opener keyword (`begin`, `declare`, `else`, `exception`,
`or`, `private`, `select`) or compilation-unit prefix (`separate (Parent)`,
`[not] overriding`), and does not end in a block-opening keyword
(`is`, `then`, `loop`, `record`, `select`, `do`). The continuation persists
until a line completes the statement (typically by ending in `;`):

```ada
Curtains : constant Alternatives_Profiles_T
  := Whatever_But_Very_Long;     -- +1 level, until the ';'
Other : Integer := 0;            -- back at the base level
```

A **term continuation** — a line that continues a value (sub-)expression across
a break by starting with a value operator (`-`, `+`, `&`, `>=`, `=`, `..`, `mod`,
`rem`, …) or by opening an argument list with `(` — nests one level past *where
that value expression began*. The expression begins on the statement head, or on
a `:=` line when the initializer is wrapped onto its own line. So a `(args)` or
`& …` under a continued `:= F` gets a second level, while the same under a
statement's first line gets just `+1`; a chain of such continuations all align at
that one level rather than escalating. The binding operators `:=` / `=>` and the
boolean connectives `and` / `or` / `xor` are **not** term continuations — they
keep the plain continuation level (so an `and …` aligns with comments that
document it):

```ada
Curtain_Index_May_Differ         -- statement start (expression begins here)
  (Left  => A,                   -- +1: the call's argument list
   Right => B);                  -- arguments align under the first

Set_Info : constant T
  := Get                         -- +1 level (the ':=' line; value begins here)
    (Query  => Q,                -- +2: '(' continues the value on the ':=' line
     Object => O);               -- arguments align under the first one

Delta_X : constant Duration_T
  := Take_Off_Time (RTFM)        -- +1 (':=' line)
    - Take_Off_Time (FTFM);      -- +2: '-' continues the value
```

This is distinct from **parenthesis continuation** (an unclosed `(`, see below),
which aligns by column instead. Parenthesis state takes priority: while inside
an open `(` the statement-continuation rule does not also apply.

**Comment-only lines are transparent.** A line whose code is empty once the
`--` comment is stripped does not alter any parser state — it neither starts,
extends, nor ends a statement continuation. It is indented to the current
continuation context and the next real line is positioned exactly as if the
comment were not there. So comments may freely interrupt a multi-line
condition, an open parenthesis, or a statement continuation without disturbing
the surrounding indentation:

```ada
return New_OBT > Old_OBT
  -- a comment here does not break the continuation
  and (Departure.Earliest_TTOT = None     -- +1 continuation, aligned with the comments
         or else New_OBT > X);            -- 'or else': +1 operator extra (inside the paren)
```

### Expressions inside parentheses (if-/case-expressions)

While the running parenthesis depth is `> 0`, every line is treated as part of
an expression and **no statement-keyword handling applies**. This matters for
conditional and case *expressions*, where `then`, `else`, `elsif` and `when`
are part of the expression, not statement structure — without this rule a
leading `else` would dedent as if it closed an `if` statement.

For an **if-expression** the indenter additionally aligns to the `if`: the
column of the `if` token (in the re-indented opening line) is remembered, and
each continuation line is positioned by absolute column — `then`, `else` and
`elsif` under the `if`, and the condition continuation one indent level past
the `if` (i.e. one level in from the `then`/`else`):

```ada
Reroutings := (if Cycle_Of (Normal_Flight.IOBT)
                 /= Cycle_Of (Message.IOBT)       -- one level past the 'if'
               then Empty_List                    -- under the 'if'
               else Normal_Flight.Reroutings);    -- under the 'if'
```

A **case-expression** is aligned to its `case` the same way, except the
`when` clauses are indented one **level** in from the `case` (rather than lined
up under it), and a clause body indents one further level. A clause body is
itself an expression, so a continuation line that starts with an operator
(`or else`, `and then`, `&`, …) takes one more level past the body — except a
leading `=>`, which is the result arrow for choices that spilled onto an
earlier line and stays at the body level:

```ada
function F return T is
  (case X is
     when A | B            -- one level in from 'case'
       => R1,              -- clause body ('=>' arrow), one level deeper
     when others =>
       X                   -- clause body
         or else Y);       -- operator continuation, one further level
```

These keyword offsets are just the if-/case-specific cases of the same
column-alignment used for every open parenthesis (see **Parenthesis
continuation** below): each entry on the paren stack records the alignment
column and whether the `(` is plain, `(if`, or `(case`, and a line aligns to
the innermost open one. Entries are dropped when their `)` closes. (The
`(if`/`(case` scan runs over the emitted text, so a keyword appearing inside a
string literal in the expression could be mis-detected — rare in practice.)

### Closers — pop, and align with the opener's header

`LEAD = end` (covers `end;`, `end if;`, `end loop;`, `end case;`, `end record;`,
`end select;`, `end Name;`):

1. Pop **all** trailing `WHEN` frames (close the open `case`/exception
   alternatives).
2. Pop **one** more frame (the enclosing construct).
3. Display at the resulting depth.

This is why a single `end case;` correctly dedents past both the last `when` and
the `case`.

### Splitters — align with the opener, but keep the frame open

These display one level shallower than the body; the body below them re-indents
because the enclosing frame stays on the stack:

| `LEAD` | Belongs to |
|---|---|
| `elsif`, `else` | `if` (note: `elsif … then` does **not** push a second `IF`) |
| `when` | `case` / exception handler (pops a previous `WHEN`, then pushes its own) |
| `exception` | `begin … end` block |
| `or`, `else` | `select` |
| `private` | package spec |

### `begin` — context-sensitive

- If the top frame is `PKG` or `DECLARE` (a declarative region not yet started),
  this is the **declarative-part `begin`**: it aligns with the subprogram /
  `declare` header and converts that frame to `BLOCK` (no push).
- Otherwise it is a **nested block statement**: it pushes a fresh `BLOCK`.

When a `when` choice list is split across lines before its `=>`, the `|`
continuation aligns at the **arm-body level** — the `WHEN` frame already
supplies the indent, so the continuation is not pushed a further level:

```ada
when Action_1 | Action_15
  | Action_16 | Action_43 =>   -- '|' continuation, at the arm-body level
  Do_It;                        -- arm body, same level
```

### Parenthesis continuation

While the running parenthesis depth is `> 0` (an unclosed `(` from an aggregate,
parameter list, or call), continuation lines are **aligned by column** under the
first item after the innermost open `(`:

```ada
procedure Perform (Flights           : in out Flight.Options.T;
                   Flight_Query_Set  :        Env_Query.Set.T;
                   Action_Result     :    out Result.T) is   -- ') is' still opens the body
   X : Integer;
begin
```

The alignment column is the position of the first non-blank character after the
`(` (or one indent level in if the `(` ends the line), measured from where the
opening line actually lands. Every open parenthesis is tracked on a stack keyed
by depth, so a line uses the **innermost** one — a nested aggregate aligns under
its own `(` while the enclosing expression keeps its alignment. A line that
closes all the parentheses and ends in a block opener (a parameter list ending
in `) is`, `) return T is`, `) loop`, …) is aligned like the other
continuations *and* opens that block. if-/case-expressions are the same
mechanism with keyword-aware offsets (see above).

A continuation line that **starts with an operator** takes one extra indent
level so the operator stands out from the operand it continues — but **only
inside parentheses**. The qualifying operators are any symbol (`:=`, `=>`, `&`,
`+`, `-`, `*`, `/`, `=`, `<`, `>`, `|`, `..`) or a word operator (`and`, `or`,
`xor`, `mod`, `rem`, covering `and then` / `or else`).

**Outside parentheses** a statement or declaration continuation always takes a
plain single level, regardless of any leading operator. So an `and`/`or` line
continuing a `return`, or a `:=` continuing a declaration, sits at the same
+1 level as a comment that documents it — it does *not* get the operator extra.

```ada
return New_OBT > Old_OBT
  and (Departure.Earliest_TTOT (FTFX.Departure_Info) = Time.None_Time   -- 'and': plain +1 (outside '(')
         or else New_OBT > Departure.Off_Block);                        -- 'or else': +1 extra (inside '(')

First_Time_In_TACT : constant Count_Option.Set.T
  := (if Action_Info.Event = External_Create                            -- ':=': plain +1 (outside '(')
      then (others => True)
      else (Count_Option.Normal
              => Flight_Updates (Count_Option.Normal).Old_Fixed_Info.Status = Not_Existing,  -- '=>': +1 (in parens)
            Count_Option.Proposal
              => Flight_Updates (Count_Option.Proposal).Old_Fixed_Info.Status = Not_Existing));
```

(The if-/case-expression keyword offsets already build in this extra step for
their own `=>`/conditions, so it is not applied twice there.)

## What it deliberately ignores

Keeping the grammar simple means a few things are out of scope:

- **Non-parenthesised continuations are a single level.** A wrapped statement
  (no enclosing `(`) and a multi-line `if`/`elsif` condition each add exactly
  one indent level rather than aligning under a specific column such as the
  `:=`. Continuations **inside** parentheses, by contrast, *are* column-aligned
  (under the first item, or the `if`/`case` keyword) — see above.
- **Parenthesis counting** skips both string literals and character literals,
  so a `'('` or `')'` does not throw off the depth. The `--` comment scanner,
  however, only tracks double-quoted strings: a character literal containing a
  `"` and **doubled-quote escapes** (`"a""b"`) are not modelled there.
- **Generic formal parts** (`generic … package …`) are left flat.
- Alignment *within* a line (e.g. lining up `:=` or `=>`) is not attempted —
  only leading indentation is changed.

## Behaviour on syntactically incorrect code

The indenter never validates Ada — it only inspects the leading and trailing
token of each line. It degrades gracefully on most errors:

- **Misspelled or unknown keywords** are treated as ordinary lines; no stack
  change occurs.
- **Extra `end`** — every pop is guarded by `if len(stack) > 0`, so an
  unmatched `end` is silently ignored.
- **Missing `end`** — the stack stays open; subsequent lines receive deeper
  indentation for the rest of the file.
- **Mismatched closers** (e.g. `end loop;` closing an `if`) — the top frame
  is popped regardless of its kind; the indenter does not check for agreement.

One error can cascade badly: an **unclosed `(`** with no matching `)` leaves
`paren_depth > 0` permanently and gives every following line an extra indent
level for the rest of the file.

## Ada 2022 compatibility

Most Ada 2022 code uses the same block-forming keywords as earlier standards
and indents correctly. Three specific additions are not fully supported:

| Feature | Effect |
|---|---|
| `[…]` array / container aggregates | Only `(` / `)` are tracked for continuation depth. A multi-line `[…]` aggregate receives no extra continuation indent. |
| `parallel do … and do … end do` | The `and do` arm is not a recognised splitter; its body is indented as an ordinary line rather than aligning with the first `do` arm. |
| `declare` expressions `(declare X := …; begin …)` | `declare` and `begin` as trailing/leading tokens inside an expression can push spurious stack frames. The effect is partially masked when the expression is already inside `()`. |

The most common issue in practice is `[…]` aggregates, since Ada 2022
encourages that syntax for all composite literals. Fixing it would require
tracking `[` / `]` depth alongside `(` / `)` in `paren_delta`.

## Worked example

Input (all flush-left):

```ada
procedure Hello is
X : Integer := 0;
begin
if X = 0 then
Put_Line ("zero");
elsif X > 0 then
Put_Line ("pos");
else
Put_Line ("neg");
end if;
end Hello;
```

Output:

```ada
procedure Hello is
  X : Integer := 0;
begin
  if X = 0 then
    Put_Line ("zero");
  elsif X > 0 then
    Put_Line ("pos");
  else
    Put_Line ("neg");
  end if;
end Hello;
```

See `sample.adb` for a longer example and `test_ada_indent.ady`'s `run_tests()`
for the full set of cases (subprograms, records, exception handlers, paren
continuations).
