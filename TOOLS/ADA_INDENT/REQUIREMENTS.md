# ada_indent — Indentation Requirements

## 1. Indentation unit

The indentation step is **2 spaces** per nesting level. All output uses
spaces only; no tab characters are ever emitted.

---

## 2. Block structure

### 2.1 Basic compound statements

- `if` / `elsif` / `else` / `end if` — each keyword starts at the same
  column; the body is indented one level.
- `for … loop` / `end loop` — body indented one level.
- `case … is` / `when … =>` / `end case` — `when` is indented one level
  inside `case`; the arm body is indented one further level.

### 2.2 Declare block

- `declare` / `begin` / `exception` / `end` all align at the same column.
- Declarations inside `declare` are indented one level.
- Statements inside `begin` are indented one level.
- `when` inside `exception` is indented one level; the handler body one
  further level.
- Named (`Label:`) declare blocks and named loops are supported; the label
  does not affect the indentation of the block body.

### 2.3 Record types

- `type T is record` (inline): field declarations indented one level;
  `end record` at the same level as `type`.
- `type T is` on its own line followed by `record` on the next: `record`
  is indented one level; fields one level further; `end record` aligns
  with `record`.
- Variant records: `case M is` inside the record body is indented one
  level; `when` arms one further level; `end case` closes back to `case`.

### 2.4 Task type / protected type

- `task type T … with` / aspect clause / `is` / entries / `end T`:
  the aspect clause is indented one level; after the standalone `is` the
  entries are at one level; `end` returns to the `task type` column.
- A standalone `is` on its own line (after the aspect clause) snaps back
  to the declaration column — it does **not** stay continuation-indented.
- `select` / `or` / `end select` all align at the same column; each
  guarded alternative body is indented one level.

### 2.5 Expression function

- `function F return T is (expr)` — the parenthesised expression body is
  indented one level relative to `function`.
- The spec (`function F return T is`) does **not** push a block frame; the
  next declaration starts at the enclosing level.
- A `(case … is …)` or `(if … then … else …)` body is treated as a
  paren-continuation, not as a block statement — no block frame is pushed.

### 2.6 Generic instantiation

- `procedure P is new Gen (…)` — when `is new` appears on the next line it
  is continuation-indented (one level).
- `package Q is new Gen (…)` inside a declarative region: `new` on the
  next line is continuation-indented.

### 2.7 Subunit

- `separate (Parent) procedure P … is` is treated as a top-level
  compilation unit; its body is indented at the standard one level.

---

## 3. Declaration continuations

When a declaration's initial value (`:= …`) does not fit on the first
line:

- The `:=` token may stay on the first line or move to the next;
  the value that follows is indented **two levels** relative to the
  declaration (i.e. one extra level beyond a normal continuation).
- An operator (`+`, `-`, `and`, `or`, `or else`, `and then`, `and not`,
  `or not`) that **leads** a continuation line is indented two levels from
  the declaration.
- `and not` and `or not` are treated as single binary operators for
  indentation purposes.
- A `for … =>` quantified expression body is indented one level inside the
  enclosing paren.

---

## 4. Paren continuation

When an open parenthesis is not closed on the same line:

### 4.1 Alignment under first item

Subsequent lines align under the **first non-space character after the
opening `(`**.

### 4.2 Call name on its own line

When a call name (or named-association key `Name =>`) appears on one line
and its argument list `(…)` starts on the next, the `(` is indented one
level deeper than the call name; subsequent arguments align under the first
argument.

### 4.3 Nested parens

Each additional open paren that is not closed on the same line increases
the alignment column by one level. Operators inside an inner paren are
indented one extra level compared to the same operators outside.

An argument-list `(` that opens a continuation line is the call's argument
list, so it nests one level past the **call name**, which sits on the
previous code line. When that previous line is itself an operator/term
continuation (already deeper than the item column), the `(` compounds past
it rather than flattening back to the item column.

### 4.4 If-expression inside paren

- `then` and `else` branches align under `if`.
- A `)` that closes the surrounding paren (lone closing paren) aligns one
  column to the left of the opening `(`.
- After the closing `)` of the if-expression, expression continuation
  resumes at the outer level.

### 4.5 Character literal `)`

A `)` that is the content of a character literal `')'` must not affect
the paren-depth counter.

### 4.6 `..` range continuation

When the upper bound of a `for … in A .. B loop` range appears on the
next line, it is continuation-indented; the standalone `loop` that follows
snaps back to the `for` column.

---

## 5. Multi-line conditions

- An `if` or `elsif` condition that continues across lines: continuation
  operators (`and then`, `or else`) are indented one level relative to
  the `if`/`elsif` keyword.
- A standalone `then` that closes the condition snaps back to the
  `if`/`elsif` column.
- A term continuation (e.g. `>= value`) that is a sub-expression of a
  larger `and then` chain is indented one extra level.
- A call whose argument list starts on the next line inside a condition is
  indented one level relative to the call name.

---

## 6. Case-expression arm continuation

- `when A | B` — a `|` continuation on the next line is indented one
  level relative to `when`.
- `=> value` on the same line as `when`: the arm body continues at that
  column.
- `=>` on its own line: the arm body is indented one level relative to
  `when`.
- An operator continuation inside an arm body is indented one level
  further than the arm body start.

---

## 7. Comments

### 7.1 Continuation transparency

Comment lines appearing **between** continuation lines are treated as
transparent: they do not reset or alter the continuation state. The
following code line is indented as if the comments were not there.

### 7.2 Comment inside paren

A comment that appears inside an open-paren region inherits the current
paren-alignment column, not the stale alignment from an earlier paren on
the same statement.

Trailing comments after the last argument (before the closing `)`) align
at the paren-content column.

Comments between arguments (after a comma-terminated line) align at the
argument column.

### 7.3 Comment between if-expression branches

Comment lines between `then (…)` and `else (…)` inside a parenthesised
if-expression align at the `then`/`else` column.

### 7.4 Comment before `begin` / after deferred header

A comment in the declarative region (before `begin`) is indented at the
declaration level. A comment between the function header and the first
declaration is indented one level inside the subprogram.

---

## 8. Named associations and `=>`

- When a named-association value (`Key => Value`) is split across lines,
  `Value` on the next line is indented one level relative to `Key =>`.
- Operator continuation inside such a value is indented one level further.

---

## 9. Keyword-prefix identifiers

Identifiers whose names **begin with** an Ada reserved word (`Case_Sensitive`,
`If_Valid`, `For_Each`, …) must not be mistaken for keywords. They are
treated as ordinary identifiers for all indentation purposes.

---

## 10. Idempotency

Running `ada_indent` on already-correctly-indented source must produce
output that is byte-for-byte identical to the input. The regression test
file is its own golden file: feeding it to `ada_indent` must reproduce it
exactly.
