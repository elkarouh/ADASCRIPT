# Simplified Ada Indentation Grammar and Rules

`ada_indent` re-indents Ada source code.

It is **not** a full Ada parser. Indentation does not require understanding
expressions, types, or semantics — only the keywords that **open**, **close**,
or **split** an indented block. This document specifies that simplified grammar
and how it drives the indenter.

## Recovering from a mis-parse

The block stack is inferred, so a construct parsed as opening a block when it
opens none would otherwise shift every following line to the end of the file.
`end` lines are used as anchors against that. Ada states the structure outright
there — `end Foo;`, `end loop Outer;` — and the indenter matches that name
against the frame it is about to close:

- **It matches** (the overwhelmingly common case): close one frame, as before.
- **It names a frame further down the stack**: the frames above that one were
  never really open, so they are dropped and the stack is re-grounded on the
  source. The damage stops at this `end` instead of running to EOF.
- **It names a frame that an earlier nameless `end;` already closed**: that
  `end;` was stray. The stack returns to the depth it left, and nothing more is
  closed.
- **It names a header that never opened its frame** (a mangled
  `procedure P (...) is (`): nothing is closed, since the frame on top belongs
  to an enclosing construct.
- **It matches nothing else, and the frame being closed has a name**: most
  likely a misspelt name. One frame is closed, as before, and the mismatch is
  reported.

`end if;`, `end loop;`, `end case;`, `end record;`, `end select;` and
`end return;` name a construct *kind*. They close the nearest open frame of
that kind within the current body, dropping any unclosed frames above it. When
there is none, the closer is stray and closes nothing. A bare `end;` carries no
name and closes one frame.

Other resynchronisation points:

- A line starting with a word that cannot occur inside an expression (`begin`,
  `end`, `procedure`, `function`, `package`, `pragma`, `type`, `declare`, ...)
  ends an unclosed `(` or an `if` condition still waiting for `then`. A
  condition line ending in `;` also ends the condition.
- A `when` opens an alternative only inside a `case`, a `select` or an exception
  handler. Anywhere else it opens nothing, so it cannot leave a frame that is
  never closed.

With these rules, a single invalid edit (a deleted, duplicated or truncated
line, a stray `begin`/`end if`/`if`, an unclosed or extra parenthesis) changes
the indentation of about 9% of the lines after it on average, against 48%
without them. `tests/fixtures/invalid_recovery.adb` is the regression fixture.

Diagnostics go to **stderr**, never stdout, so a formatter pipe stays clean;
`-q` / `--quiet` silences them. Silencing changes nothing about the indenting:
the same resynchronisation happens either way.

This bounds a mis-parse to the innermost enclosing *named* construct. It is not
a full recovery: a stray `end;` that closes a package body, or a bad frame in a package body's declarative part is only
re-grounded at that package's own `end`, which may be the last line of the
file. Containing it more tightly than that would mean trusting the input's
existing indentation, which this tool deliberately ignores — see the fixpoint
requirement in `tests/run_tests.py`.

## How comments are indented

A comment-only line has no syntax of its own, so its column cannot be derived
from the grammar the way a code line's is. It has to come from the code it is
about, and the indenter decides which code that is from the layout the author
chose. Trailing comments (after code on the same line) are never moved relative
to their code: only a line's leading whitespace ever changes. The rules below,
specified in `REQUIREMENTS.md` §7, are for comment-only lines.

**1. A comment belongs to the line before it.** It is indented as a line
following that one would be: inside the block the line opens, at the item
column inside a parenthesised list, at the continuation column between the
lines of a split statement.

```ada
   begin
      -- initialise the counters          (inside the block 'begin' opens)
      Count := 0;
```

*Why:* comments are usually written in place, next to the code they explain.
Placing a comment where the next line would start also keeps a comment between
two continuation lines from breaking the statement visually. The indenter treats
such comments as transparent, so the lines around them are indented as if the
comments were not there.

**2. After a blank line, a comment belongs to the line after it,** and takes
that line's column. It makes a difference only where that line steps out of the
block, as in `when`, `elsif`, `else` or `exception`:

```ada
            return X;
         end if;

         -- Below: nothing specific for the origin unit.     (not at 'end if' level)
      when For_FPL_Origin_Unit =>
```

*Why:* a blank line ends a paragraph, and a comment that opens the next one
introduces what follows. The blank line is the author's own statement of which
way the comment faces, so the indenter follows it. It is also easy to control:
to keep a comment with the code above, leave out the blank line.

**3. Except before `end ...`, `begin` or a lone `)`**: there the comment stays
with the block it ends.

```ada
      return Equal_Data (Left_Ref, Right_Ref);

      -- return (Left_Ref.Baseline = Right_Ref.Baseline ...  (commented-out code
      --    or else Equal_Data (Left_Ref, Right_Ref);         stays in the body)
   end Equal_Data;
```

*Why:* those lines carry no meaning a comment could be about. A comment before
them is a note on, or code commented out of, the body or the declarations they
close.

**4. A deliberately placed comment keeps its place.** A comment indented more
than one level deeper than rule 1 would put it (and deeper than the code line
above it) keeps its offset from that code line. When that line is re-indented,
the comment moves with it.

```ada
         Variant => Count.Create_Variant (Option => Options (Set),
                                          Include_Temporary_Proposals => False),
                    -- PQI does not take invisible flights into account.
         Input_Flows => Selection_Flows,
```

*Why:* a note written *under* what it documents, like a value in an argument
list, is an alignment the author chose, and the rules above cannot reconstruct
it. The "more than one level deeper" threshold keeps this from getting in the
way of re-indenting. A file whose indentation has been stripped, or one written
with a different indent width, is still re-indented in full.

**5. Inside a parenthesised list**, a comment after the last item (no comma
follows it) or after a complete `X => Y` association sits at the item column,
like the `)` that closes the list. Only after a line that ends in an operator
(`&`, `+`, `and then`, ...) does it take the deeper continuation column,
because only there is the expression certain to go on.

**Editors.** Rule 2 needs the line after the comment, so it applies when whole
input is indented: the command line, `format-all`, a region re-indent. When an
editor indents one line at a time, the comment is placed before that line
exists. The Emacs integration catches up: once the code line is indented, it
re-indents the paragraph above it together with it. Other editors place such a
comment by rule 1 until the region is re-indented.

## The model: a block stack

Indentation in Ada is a function of how many blocks are currently open. The
indenter keeps a **stack of frames**, one per open construct. For each physical
line:

1. The line is classified by its **leading keyword** and its **final token**
   (after stripping `--` comments and a trailing `;`).
2. The **display indent** is the stack depth — adjusted down by one for keywords
   that align with their opener rather than the block body.
3. The stack is then updated (push / pop) for the lines that follow.

Indent width defaults to **2 spaces**, set by `Indent_Width` in `src/ada_scan.ads` (change it there
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

See `examples/sample.adb` for a longer example and `tests/cases/` (described in
`tests/CASES.md`) for the full set of cases (subprograms, records, exception handlers, paren
continuations).
