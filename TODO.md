# TODO

Open items only.  The write-ups for everything already fixed — 26 numbered
bugs and the shell-syntax work — were removed once done; they are in the git
history of this file if the reasoning behind one of them is ever wanted.

- [ ] distinct types and units, what is left (the feature itself --
      `distinct`, scaling, derived and scaled units -- is done: book 2.7,
      EXAMPLES/test_distinct.ady, test_units.ady, test_money.ady):
      - a literal whose context Nim cannot see needs `V(x)` written: an
        argument to a routine of a Nim module, or a method of an object
        that is not the program's own. A known routine's argument, a function
        value's (`let f: (Speed_T) -> float`), `xs.append(5.0)` to a
        []Speed_T and a table literal no longer do.
      - a derived unit is float, or int for a product. `x ** n` (n a whole
        number written out) is the unit of that dimension, when one is
        declared. Units relate by dimension (book 2.7), but only to the
        units declared: Nim's `unchained` does full dimensional analysis;
        this is deliberately smaller.
      - a conversion between two distinct types no declaration relates,
        `Duration_T(d)` for a `Distance_T` d, is refused on Nim, naming
        both types; `Duration_T(float(d))` is the spelling that says the
        units are meant. ady2py refuses it the same way.
- [ ] **For discussion:** let `m(k)` look up a `{K}V` or `[K]V` as `m[k]`
      does, and let a table be passed where a `(K) -> V` is expected (a
      small adapter on each backend). A pure function is a mapping, and Ada
      writes both the same way, so a computed function could become a
      precomputed table without touching a call site. Every declaration
      would still name one concrete type; only the call syntax is shared.
- [ ] **For discussion, not to implement yet:** a statement modifier on more
      than the guards. Today only `return`, `break`, `continue`, `die(...)`
      and `quit(...)` may carry a trailing `if` (README, "Statement
      Modifier", says why). Writing `Tcheckout.ady` asked for it three
      times -- `warn(msg) if msg != ""`, `x = y if c`, a call run only when
      needed -- each now a two-line `if` block. The case against: an
      assignment with a trailing `if` reads like the conditional expression
      `x = y if c else z` until the end of the line; any call could hide its
      condition off to the right; and the rule "a modifier means the block
      is left" would be gone. The goal is readability, not terseness, so
      the default answer is no -- unless a narrower rule (a `warn`, say, as
      the guard's non-leaving sibling) turns out to read as well as the
      guards do.

---

## Monad support improvements (high ROI)

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

---

## Deliberately not done

### Streaming stdin — NOT DONE, and here is why

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

## Union returns: what is left from rewriting lispy.ady

A variant record is a value type on Nim, so a variant that holds
itself through a field (a closure holding its body) needs the holder to be a
class marked `@virtual` -- correct, but `@virtual` is documented as being for
cross-module subclasses only.

## Modules on the Python backend (ady2py merges what ady2nim links)

`ady2py` replaces `import X` by X.ady's text (see `include_ady_modules`).
Known, and not done:

- The libraries bundled with ady2nim build with ady2py too; `db.ady` through its Python
  version, TO_PYTHON/STDLIB/db.ady (sqlite3). `browser`, `svg_drag` and `jointjs` are for
  `ady2nim js`, by nature.
- [ ] Found trying db's users on Python: TOOLS/ACCOUNTING/tests/test_gnucash.ady stops at
  `Cents_T((int(net) * rate.ord + 50) // 100)` (the unit of an int expression with an
  enum's ordinal "cannot be told"), and EXAMPLES/timetable_engine.ady at a record field
  whose default is another record (a dataclass's mutable default).

## Found porting EXAMPLES/MOON/moon_sim.ady

Each open one has a workaround in that file.

- `from MAP_UTILS/map_base import` from a sibling directory is the parent rule (tutorial
  21.2), on both backends. (The map_* modules stay Nim-only, by decision.)

### Met on the way and since fixed

The units items below were fixed in the transpiler (`EXAMPLES/test_units_fields.ady`); the rest have a workaround in the source, marked where it is.

* **`(a, b) = f()` inside a block, onto variables declared outside it, made new variables on
  Nim** (`var (a, b) = ...`) and left the outer ones as they were. Silent: guidance flew to a
  target of zeros and the lander hit the Moon at 300 m/s. Fixed in the transpiler; the source still
  returns a record and assigns (`Guidance.compute`'s `aim`).
* **`(self.r, self.v) = f()` was not seen as a write to `self`**: the method got a plain `self` and
  Nim refused to compile it. Fixed in the transpiler; `Navigation.propagate` still assigns one at a time.
* **Methods in a `record` body were dropped without a word**, on both backends; both now refuse
  them and say to write a function or use a class. The first version's vector had to be a class.
* **Classes are values on Nim, references on Python** (chapter 13): `Rng` and `Spacecraft` are shared,
  so they are `@virtual`.
* **Units**: `SquareMeters_T * metre_T` has no unit (a chain is two-at-a-time), so a cube is taken
  through `float`. Three others were fixed here: a literal beside `>` on a distinct type in a
  conditional expression or on a tuple-unpacked name came out as `0.0 < force`; a bare `0.0` in a
  returned tuple `(int, Force_T)` was not converted; and the Python unit check did not know a record
  field's type (`st.isp * G0`).
* **`{x:,.0f}` and `{x:+.0f}` in an f-string**: Nim had no `,` flag, and `+.0f` left a stray `.`
  (`-456396.`). Fixed in the transpiler, with a width and alignment too (`{x:15,.1f}`); the source
  writes them as Python does. `\n` in an f-string was fixed some time before.
* **A call on a `PyObject` variable standing alone (`ax.plot(...)`) was "has to be used" on Nim**
  (only a call on a pyimported module was discarded). Fixed in the transpiler; the plots are written
  as plain calls.
* **`Record(a, b, None)` with a positional `None` for a `?T` field emitted `nil` on Nim, and
  `opt == value` / `opt != value` on a `?Enum` did not compile.** Fixed in the transpiler (the field is
  lifted to `none(T)` or `some(v)`, positional or by name; the value beside `==` is lifted to
  `some(v)`).
* **`a + b` on two `[]T` fields reached through `self.x.y`** was not seen as a list concatenation on
  Nim (`&`). Fixed in the transpiler.
* **`min(a, b, c)` with three arguments, and `raise NotImplementedError()` without a message,
  did not compile on Nim.** Fixed in the transpiler (nested two-argument calls; the exception's name
  as its message, and `except NotImplementedError` catches it).
* **`math.atan`, `atan2`, `asin`, `acos` and one-argument `math.log`** are Python's names, not Nim's
  (`arctan`, `arctan2`, `arcsin`, `arccos`, `ln`). They are now refused with what Nim calls them, and
  `math.arctan` and the others run on the Python backend too.
* **map_base and map_flat cannot be imported from a sibling directory by name**; `from MAP_UTILS/map_base import`
  works because the parent of this directory is searched.

## Found porting EXAMPLES/accounting.ady


## Found writing TOOLS/ACCOUNTING/ledger.ady

- [x] a local `let x: str` made a field of the same name on another value
      a string too: in accounting_gui.ady's box_html, with `let x: str =
      px(...)` in scope, `px(p.x + shape.half_w - 8.0)` came out as
      `p.x & shape.half_w - 8.0` (string concatenation). Fixed: `+` and `*`
      read a field's type from its object's declaration when the object's
      type is known, the field's bare name only otherwise
      (test_local_named_like_field).
- [x] an enum whose member values skip numbers (`type VatRate_T is enum
      NO_VAT = 0, REDUCED = 6, INTERMEDIATE = 12, STANDARD = 21`) could not be
      iterated (`for rate in VatRate_T`), so listing its members meant writing
      them out again by hand. Fixed: `for x in E` visits the members, each once
      and in order, never a value no member has (Nim: std/enumutils' items;
      Python: Enum iteration). Still refused, a gap leaving their meaning open:
      `[E]T` (a slot per member or per value?) and 'Next/'Prev (the next member
      or the next value?) -- DOCS/BOOK §3.1a.
