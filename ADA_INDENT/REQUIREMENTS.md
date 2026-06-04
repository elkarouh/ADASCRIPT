# ada_indent — Indentation Requirements

Each requirement is traced to its test case(s) in `ada_indent_sample_test.adb`.

---

## 1. Indentation unit

The indentation step is **2 spaces** per nesting level. All output uses
spaces only; no tab characters are ever emitted.

---

## 2. Block structure

### 2.1 Basic compound statements [T1]

- `if` / `elsif` / `else` / `end if` — each keyword starts at the same
  column; the body is indented one level.
- `for … loop` / `end loop` — body indented one level.
- `case … is` / `when … =>` / `end case` — `when` is indented one level
  inside `case`; the arm body is indented one further level.

### 2.2 Declare block [T3]

- `declare` / `begin` / `exception` / `end` all align at the same column.
- Declarations inside `declare` are indented one level.
- Statements inside `begin` are indented one level.
- `when` inside `exception` is indented one level; the handler body one
  further level.

### 2.3 Record types [T2, T45]

- `type T is record` (inline): field declarations indented one level;
  `end record` at the same level as `type`.
- `type T is` on its own line followed by `record` on the next: `record`
  is indented one level; fields one level further; `end record` aligns
  with `record`.
- Variant records: `case M is` inside the record body is indented one
  level; `when` arms one further level; `end case` closes back to `case`.

### 2.4 Task type / protected type [T46, T47, T49]

- `task type T … with` / aspect clause / `is` / entries / `end T`:
  the aspect clause is indented one level; after the standalone `is` the
  entries are at one level; `end` returns to the `task type` column.
- A standalone `is` on its own line (after the aspect clause) snaps back
  to the declaration column — it does **not** stay continuation-indented.
  [T46, T49]
- `select` / `or` / `end select` all align at the same column; each
  guarded alternative body is indented one level. [T47]

### 2.5 Expression function [T7, T10, T15, T16]

- `function F return T is (expr)` — the parenthesised expression body is
  indented one level relative to `function`.
- The spec (`function F return T is`) does **not** push a block frame; the
  next declaration starts at the enclosing level. [T7]
- A `(case … is …)` or `(if … then … else …)` body is treated as a
  paren-continuation, not as a block statement — no block frame is pushed.
  [T10, T15, T16]

### 2.6 Generic instantiation [T49, T51]

- `procedure P is new Gen (…)` — when `is new` appears on the next line it
  is continuation-indented (one level). [T49]
- `package Q is new Gen (…)` inside a declarative region: `new` on the
  next line is continuation-indented. [T51]

### 2.7 Subunit [T9]

- `separate (Parent) procedure P … is` is treated as a top-level
  compilation unit; its body is indented at the standard one level.

---

## 3. Declaration continuations [T5, T17, T22, T25, T28, T29, T30, T31]

When a declaration's initial value (`:= …`) does not fit on the first
line:

- The `:=` token may stay on the first line or move to the next;
  the value that follows is indented **two levels** relative to the
  declaration (i.e. one extra level beyond a normal continuation). [T5]
- An operator (`+`, `-`, `and`, `or`, `or else`, `and then`, `and not`,
  `or not`) that **leads** a continuation line is indented two levels from
  the declaration. [T5, T22, T25, T28, T29]
- `and not` and `or not` are treated as single binary operators for
  indentation purposes. [T25]
- A `for … =>` quantified expression body is indented one level inside the
  enclosing paren. [T31]

---

## 4. Paren continuation [T4, T8, T11, T12, T13, T17, T17b, T20, T23, T23b, T24, T27, T32, T34, T50]

When an open parenthesis is not closed on the same line:

### 4.1 Alignment under first item [T4]

Subsequent lines align under the **first non-space character after the
opening `(`**.

### 4.2 Call name on its own line [T17b, T50]

When a call name (or named-association key `Name =>`) appears on one line
and its argument list `(…)` starts on the next, the `(` is indented one
level deeper than the call name; subsequent arguments align under the first
argument. [T17b, T50]

### 4.3 Nested parens [T12, T13, T23, T32, T39, T40]

Each additional open paren that is not closed on the same line increases
the alignment column by one level. Operators inside an inner paren are
indented one extra level compared to the same operators outside. [T12]

### 4.4 If-expression inside paren [T8, T11, T20, T27, T34]

- `then` and `else` branches align under `if`. [T8, T11, T27]
- A `)` that closes the surrounding paren (lone closing paren) aligns one
  column to the left of the opening `(`. [T34]
- After the closing `)` of the if-expression, expression continuation
  resumes at the outer level. [T20]

### 4.5 Character literal `)` [T24]

A `)` that is the content of a character literal `')'` must not affect
the paren-depth counter.

### 4.6 `..` range continuation [T48]

When the upper bound of a `for … in A .. B loop` range appears on the
next line, it is continuation-indented; the standalone `loop` that follows
snaps back to the `for` column.

---

## 5. Multi-line conditions [T6, T19, T23, T23b, T38]

- An `if` or `elsif` condition that continues across lines: continuation
  operators (`and then`, `or else`) are indented one level relative to
  the `if`/`elsif` keyword. [T6]
- A standalone `then` that closes the condition snaps back to the
  `if`/`elsif` column. [T6]
- A term continuation (e.g. `>= value`) that is a sub-expression of a
  larger `and then` chain is indented one extra level. [T19]
- A call whose argument list starts on the next line inside a condition is
  indented one level relative to the call name. [T23, T23b]

---

## 6. Case-expression arm continuation [T10, T16, T21, T41]

- `when A | B` — a `|` continuation on the next line is indented one
  level relative to `when`. [T21]
- `=> value` on the same line as `when`: the arm body continues at that
  column. [T10]
- `=>` on its own line: the arm body is indented one level relative to
  `when`. [T16]
- An operator continuation inside an arm body is indented one level
  further than the arm body start. [T16, T41]

---

## 7. Comments [T14, T30, T33, T35, T37, T38, T39, T40, T41, T42, T43]

### 7.1 Continuation transparency [T14, T30, T38]

Comment lines appearing **between** continuation lines are treated as
transparent: they do not reset or alter the continuation state. The
following code line is indented as if the comments were not there.

### 7.2 Comment inside paren [T39, T40, T42, T43]

A comment that appears inside an open-paren region inherits the current
paren-alignment column, not the stale alignment from an earlier paren on
the same statement. [T40]

Trailing comments after the last argument (before the closing `)`) align
at the paren-content column. [T42]

Comments between arguments (after a comma-terminated line) align at the
argument column. [T43]

### 7.3 Comment between if-expression branches [T37]

Comment lines between `then (…)` and `else (…)` inside a parenthesised
if-expression align at the `then`/`else` column.

### 7.4 Comment before `begin` / after deferred header [T35]

A comment in the declarative region (before `begin`) is indented at the
declaration level. A comment between the function header and the first
declaration is indented one level inside the subprogram.

---

## 8. Named associations and `=>` [T33, T50]

- When a named-association value (`Key => Value`) is split across lines,
  `Value` on the next line is indented one level relative to `Key =>`.
  [T33, T50]
- Operator continuation inside such a value is indented one level further.
  [T33]

---

## 9. Keyword-prefix identifiers [T44]

Identifiers whose names **begin with** an Ada reserved word (`Case_Sensitive`,
`If_Valid`, `For_Each`, …) must not be mistaken for keywords. They are
treated as ordinary identifiers for all indentation purposes.

---

## 10. Idempotency

Running `ada_indent` on already-correctly-indented source must produce
output that is byte-for-byte identical to the input. The regression test
file is its own golden file: feeding it to `ada_indent` must reproduce it
exactly.
