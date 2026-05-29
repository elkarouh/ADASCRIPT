# Simplified Ada Indentation Grammar

`ada_indent.ady` re-indents Ada source code. It is written in **Adascript** and
transpiles to Python and Nim like any other `.ady` file.

It is **not** a full Ada parser. Indentation does not require understanding
expressions, types, or semantics — only the keywords that **open**, **close**,
or **split** an indented block. This document specifies that simplified grammar
and how it drives the indenter.

## Running

```bash
# Via the Python target (the tested path):
python3.13 TO_PYTHON/py2py.py -c ADA_INDENT/ada_indent.ady file.adb     # reindent a file
python3.13 TO_PYTHON/py2py.py -c ADA_INDENT/ada_indent.ady --test       # run self-tests

# Or transpile once, then run the generated Python directly:
python3.13 TO_PYTHON/py2py.py ADA_INDENT/ada_indent.ady > ada_indent.py
python3.13 ada_indent.py file.adb
```

The core (`reindent` plus the lexical helpers) is pure Adascript and transpiles
to both Python and Nim. Execution is verified on the **Python target**; the Nim
CLI wrapper is transpiled but not exercised in CI.

## The model: a block stack

Indentation in Ada is a function of how many blocks are currently open. The
indenter keeps a **stack of frames**, one per open construct. For each physical
line:

1. The line is classified by its **leading keyword** and its **final token**
   (after stripping `--` comments and a trailing `;`).
2. The **display indent** is the stack depth — adjusted down by one for keywords
   that align with their opener rather than the block body.
3. The stack is then updated (push / pop) for the lines that follow.

Indent width defaults to **3 spaces** (the GNAT convention), set by
`INDENT_WIDTH`.

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

opener          ::= spec_is | declare_open | if_open | loop_open
                  | case_open | record_open | select_open | do_open
                  | when_open

spec_is         ::= ( "package" | "procedure" | "function"
                    | "task" | "protected" | "type" | … ) … "is"   (* ▶ PKG     *)
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

### Parenthesis continuation

While the running parenthesis depth is `> 0` (an unclosed `(` from an aggregate,
parameter list, or call), continuation lines get **one extra** indent level.

## What it deliberately ignores

Keeping the grammar simple means a few things are out of scope:

- **Expression continuations** not wrapped in parentheses (e.g. a statement
  split across lines on a binary operator) are indented as ordinary lines.
- **Character literals** containing a `"` and **doubled-quote escapes**
  (`"a""b"`) are not modelled by the string scanner.
- **Generic formal parts** (`generic … package …`) are left flat.
- Alignment *within* a line (e.g. lining up `:=` or `=>`) is not attempted —
  only leading indentation is changed.

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

See `sample.adb` for a longer example and `ada_indent.ady`'s `run_tests()` for
the full set of cases (subprograms, records, exception handlers, paren
continuations).
