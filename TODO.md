# TODO

Open items only. What was fixed is in the git history of this file, if the
reasoning behind one of them is ever wanted.

## Open

### `T | !F` (value or failure) -- what is left

`T | !F`, F an ordinary record marked `!` in the union, is built in
(book 10.12, `TESTS/test_result.ady`, `rsync_time_machine.ady`): a
routine returns either a T or an F, in either order; `r is F` asks which
and narrows, as does `case r:` with a `when` per side; `None | !F`;
`do:` over them with bare steps, shell steps and `else`; the built-in
`ShellFailure_T` of a typed `shell:`; a dropped failure is refused. Plain
unions (`int | float`, book 4.4, `TESTS/test_union.ady`) share all of
it but do:. Not yet:

- [ ] an adapter from exceptions at the boundary: a `T | !F` from a call
      that raises. Needs a decision first: what spells "this call's
      exception is that failure" -- a `try`-expression, a decorator on the
      callee, or a typed `shell:`-like block -- and how the exception's
      message maps onto `F`'s fields.

### Classes are values in Nim, references in Python

- [ ] a class that is not inherited is a Nim `object`, a value: an
      assignment, a field or a closure holds a copy. In Python it is a
      reference. So `self.selection = selection` in another object, or a
      closure made in `__init__` (`listen("click", self.clicked)`), sees
      a copy whose state drifts from the original. A class that passes its
      own method as a value is a `ref object` already
      (`_method_value_classes`, ady2nim.py); for the rest `@virtual` is the
      workaround today.

### A module's cached Nim outlives a change to what it imports

- [ ] the cache keeps each imported module's .nim and makes it again only
      when that module's own source changes. When a stdlib module it imports
      changes a signature (blackboard's `publish` stopped returning an int),
      the cached .nim still has `discard x.publish(...)`, and Nim refuses
      it until the cache entry is removed. The key should take in the
      sources of what the module imports.

### A method of a generic class from another module, as a value

- [ ] `listen_to_server("/events", changes_channel.publish)`, the channel a
      `PublishChannel[Page_Channel_T, str]` under an alias, comes out as the
      field `changes_channel.publish` ("undeclared field"): `_bare_method_ref`
      knows the methods of this module's classes only, and would have to put
      the alias's type arguments into `publish`'s generic parameter types.
      DIJKSTRA_HTMX's liaison has a method `news` for it meanwhile.

### Table literals the record or the return gives the type of

- [ ] `Command(READ, DIAGRAM, {:})`: an empty `{:}` as a record's field in
      its constructor comes out as `initTable()` with no types, and Nim
      cannot instantiate it. The field's type, `{str}str`, says which.
- [ ] `return {"a": x}` from a `-> {str}str` routine compiled with
      `ady2nim js` comes out as `js{...}`, a JsObject, not a Table (C is
      right). SVG_NODE_EDITOR's node_editor_commands.ady puts both through
      a typed `let` meanwhile.

### Narrowing an optional

- [ ] a leaving guard whose `or` mixes other tests with `x is None`:
      `if not flag or now is None: return` proves `now` below it in
      Python, but Nim still reads it as an `Option` (`shift(el, at, now)`
      is a type mismatch). A guard made only of `is None` tests, `if a is
      None or now is None: return`, already proves each of them
      (note_option_guard in hek_nim_parser.py). Any `or` that leaves the
      block proves each `x is None` in it false, whatever the other tests
      are.

### The Python backend

`ady2py` replaces `import X` by X.ady's text (see `include_ady_modules`). The
libraries bundled with ady2nim build with it too; `db.ady` through its Python
version, TO_PYTHON/STDLIB/db.ady (sqlite3). BROWSER_EXAMPLES/ACCOUNTING's tests pass on
it, all but test_htmx, whose `html:` block is refused as Nim only.

- [ ] EXAMPLES/TIMETABLE/timetable_sa and timetable_backtrack stop at Nim's json
      (`parseJson`) and a `proc` type.

### Under `ady2nim js`

- [ ] regular expressions: refused for now ("does not translate yet"). Nim's
      `std/jsre` has JavaScript's RegExp, which reads most patterns as PCRE
      does; the regex helpers would need a JS version. test_vi_*,
      test_small_fixes and the vi editor wait on it (they use files too).

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
      bytes on Nim and characters on Python (README, "Text beyond
      ASCII"). To make them agree, either Nim works in runes (`std/unicode`:
      `runeLen`, `runeAt`, O(n) indexing) or Python works in bytes
      (`s.encode()`, and a `str` no longer Python's). Neither can be told
      apart at transpile time, so neither is refused.
- [ ] a field read on a union that is not narrowed (`grip.node` where
      `grip` is `Idle_T | Held_T | Ended_T`) is checked at run time, by Nim,
      and not at compile time (DOCS/UNION_TYPES.md, Caveats). Kept so: a
      compile-time refusal broke lispy_short.ady and lispy_union.ady, which
      read fields that way. A checked accessor, `if x.is_mN: x.mN.f else:
      raise ...`, does not compile as an operand of `+` (Nim rejects a raise
      inside an if-expression there). `if x is A or x is B:` now narrows to
      the two members named, and refuses a field one of them lacks; `and`
      mixed with `or`, and an `or` of tests on different names, narrow
      nothing.

## Deliberately not done

### Distinct types and units: known limits

The feature is done (book 2.7, TESTS/test_distinct.ady, test_units.ady,
test_money.ady). What it leaves, on purpose or because it cannot see more:

- A literal passed to a method of an object that is not the program's own
  needs `V(x)` written: the transpiler cannot see that method's parameter
  types. A known routine's argument, a function value's, `xs.append(5.0)` to
  a []Speed_T, a table literal and an argument to a hand-written Nim module
  beside the program (TESTS/test_nim_module.ady) are converted.
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
