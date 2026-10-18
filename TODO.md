# TODO

Open items only. What was fixed is in the git history of this file, if the
reasoning behind one of them is ever wanted.

## Open

### `T | !F` (value or failure) -- what is left

`T | !F`, F an ordinary record marked `!` in the union, is built in
(book 10.12, `EXAMPLES/test_result.ady`, `rsync_time_machine.ady`): a
routine returns either a T or an F, in either order; `r is F` asks which
and narrows, as does `case r:` with a `when` per side; `None | !F`;
`do:` over them with bare steps, shell steps and `else`; the built-in
`ShellFailure_T` of a typed `shell:`; a dropped failure is refused. Plain
unions (`int | float`, book 4.4, `EXAMPLES/test_union.ady`) share all of
it but do:. Not yet:

- [ ] an adapter from exceptions at the boundary: a `T | !F` from a call
      that raises. Needs a decision first: what spells "this call's
      exception is that failure" -- a `try`-expression, a decorator on the
      callee, or a typed `shell:`-like block -- and how the exception's
      message maps onto `F`'s fields.

### The Python backend

`ady2py` replaces `import X` by X.ady's text (see `include_ady_modules`). The
libraries bundled with ady2nim build with it too; `db.ady` through its Python
version, TO_PYTHON/STDLIB/db.ady (sqlite3). TOOLS/ACCOUNTING's tests pass on
it, all but test_htmx, whose `html:` block is refused as Nim only.

- [ ] EXAMPLES/timetable_sa and timetable_backtrack stop at Nim's json
      (`parseJson`) and a `proc` type.

### Under `ady2nim js`

- [ ] regular expressions: refused for now ("does not translate yet"). Nim's
      `std/jsre` has JavaScript's RegExp, which reads most patterns as PCRE
      does; the regex helpers would need a JS version. test_vi_*,
      test_small_fixes and the vi editor wait on it (they use files too).

### Found simplifying TOOLS/ACCOUNTING

- [ ] a parameter `amount: float` of a routine in an imported module
      (importers/plain_books.ady) made `posting.amount == 10500` in
      tests/test_ledger.ady, a `Cents_T` field, lose its literal conversion
      on Nim ("type mismatch: Cents_T, int literal"). The field's type is
      taken from the bare name where the parameter's is found first. The
      helper's parameter is named `x` meanwhile.

## For discussion

- [ ] let `m(k)` look up a `{K}V` or `[K]V` as `m[k]` does, and let a table
      be passed where a `(K) -> V` is expected (a small adapter on each
      backend). A pure function is a mapping, and Ada writes both the same
      way, so a computed function could become a precomputed table without
      touching a call site. Every declaration would still name one concrete
      type; only the call syntax is shared.
- [ ] **Not to implement yet:** a statement modifier on more than the
      guards. Today only `return`, `break`, `continue`, `die(...)` and
      `quit(...)` may carry a trailing `if` (README, "Statement Modifier",
      says why). Writing `Tcheckout.ady` asked for it three times --
      `warn(msg) if msg != ""`, `x = y if c`, a call run only when needed --
      each now a two-line `if` block. The case against: an assignment with a
      trailing `if` reads like the conditional expression `x = y if c else z`
      until the end of the line; any call could hide its condition off to the
      right; and the rule "a modifier means the block is left" would be gone.
      The goal is readability, not terseness, so the default answer is no --
      unless a narrower rule (a `warn`, say, as the guard's non-leaving
      sibling) turns out to read as well as the guards do.
- [ ] `len`, indexing, slicing and `for c in s` of text beyond ASCII count
      bytes on Nim and characters on Python (TUTORIAL §2, "Text beyond
      ASCII"). To make them agree, either Nim works in runes (`std/unicode`:
      `runeLen`, `runeAt`, O(n) indexing) or Python works in bytes
      (`s.encode()`, and a `str` no longer Python's). Neither can be told
      apart at transpile time, so neither is refused.

## Deliberately not done

### Distinct types and units: known limits

The feature is done (book 2.7, EXAMPLES/test_distinct.ady, test_units.ady,
test_money.ady). What it leaves, on purpose or because it cannot see more:

- A literal passed to a method of an object that is not the program's own
  needs `V(x)` written: the transpiler cannot see that method's parameter
  types. A known routine's argument, a function value's, `xs.append(5.0)` to
  a []Speed_T, a table literal and an argument to a hand-written Nim module
  beside the program (EXAMPLES/test_nim_module.ady) are converted.
- Units relate by dimension only through the units declared (book 2.7). A
  derived unit is float, or int for a product; `x ** n` is the unit of that
  dimension when one is declared. Nim's `unchained` does full dimensional
  analysis; this is deliberately smaller.
- A conversion between two distinct types no declaration relates,
  `Duration_T(d)` for a `Distance_T` d, is refused on both backends, naming
  both types; `Duration_T(float(d))` says the units are meant.

### Enums whose values skip numbers

`for x in E` visits the members. Still refused, since their meaning is open:
`[E]T` (a slot per member or per value?) and 'Next/'Prev (the next member or
the next value?) -- DOCS/BOOK §3.1a.

### Nim only, by nature or by decision

- `html:` blocks (karax), and the `browser`, `svg_drag` and `jointjs`
  libraries, which are for `ady2nim js`.
- The EXAMPLES/MAP_UTILS map_* modules.

### Streaming stdin

The case for it was that `stdin = expr` takes one whole string, so a large
input has to be built before the command starts. Measured before building
anything: 200 000 bytes fed to `head -c 3` -- a command that reads three
bytes and exits -- completes on both backends, no deadlock, no stall.

That is the interesting half of the problem, and it is already solved. Nim's
runner writes the input non-blockingly *inside* the same loop that drains
stdout and stderr, so a child that writes while we write cannot block us,
and Python's `communicate` does the equivalent with selectors. The child
consumes while we are still writing.

What is left is only that the input must fit in memory. Closing that would
mean a producer the runtime can pull from -- a closure iterator stored in
the job -- threaded through the most delicate loop in the project, the one
that took the most care to get right and whose failure mode is a hang.
Narrow benefit, real risk, and no reproduction that motivates it.

Worth revisiting if a program ever wants to feed a command more than it can
hold. A cheaper middle step, if that day comes: let `stdin` accept `[]str`
and write it element by element without ever joining it.
