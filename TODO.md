# TODO

Open items only.  The write-ups for everything already fixed — 26 numbered
bugs and the shell-syntax work — were removed once done; they are in the git
history of this file if the reasoning behind one of them is ever wanted.

- [ ] JSON for the browser. The accounting page hands the browser its accounts and
      arrows as tab-separated lines in a hidden `pre` (`TOOLS/ACCOUNTING/shared/layout.ady`,
      `books_text`/`slots_of`), with the fields matched by position and escaped by hand.
      JSON in a `<script type="application/json">` element would follow the record types
      instead. The server can already use it (`from json nimport parseJson, ...`, std/json),
      but the browser build cannot: `browser.ady` has no JSON, and a plain `parseJson` plus
      `JsonNode` indexing did not translate. The fix is a stdlib piece: typed accessors
      over the parsed value in `browser.ady`, tested on both backends. Then the page
      writes the records as JSON and the browser reads them by name.
- [ ] a direct request from the browser. The Dijkstra gestures send their changes by
      filling the hidden form `#gesture` and pressing a button (`Change` in
      `EXAMPLES/DIJKSTRA_HTMX/frontend/dijkstra_js_events.ady`). A call such as
      `htmx.ajax(method, url, values)` would skip the form. The browser build cannot reach
      a JavaScript global like `htmx` yet: `js/jsffi` has no way to fetch one, and Adascript
      has no way to declare an external JavaScript global. Needs a stdlib binding or a
      transpiler feature.
- [ ] a method's parameter is made `var` only for a direct write to it
      (`p.x = 1`, `p.items.add(..)`), where a plain proc's is also for a call of
      a method that mutates its object (`p.scroll()`). So `def draw(self, ed:
      Editor)` calling `ed.scroll()` kept a by-value `ed` and nim refused it. The
      fix is not just to copy the proc rule: a method that overrides must have its
      base's exact signature, and a `var` the subclass alone infers from its body
      makes a *different* method -- the base's is called, silently. Today the way
      out is a reference class (`@virtual`), or a plain record handed over instead,
      as vi's terminals are handed a `Frame_T` and not the `Editor`. What
      is wanted is `var` decided from the declaration (`ed: var Editor`), the same
      in the base and every override, and refused where they differ.
- [ ] three things found porting kilo that are language decisions, not slips
      (the slips were fixed: `+=` on a string field, `+` with a call operand,
      a failure narrowed in a method, `"".join` over a multi-line f-string,
      `{}` as a record field -- `EXAMPLES/test_nim_quirks.ady`).
      (1) A slice past the end of a string or list raises on Nim and is clipped
      on Python; kilo's `clip`/`tail`/`splice` stand in for it. One of the two
      has to give.
      (2) Nim reads names without case or underscores, so enum members `PAGE_UP`
      and `PAGEUP`, or two names differing in the case after the first letter,
      collide on Nim and not on Python. Refuse the pair at transpile time, or
      accept it.
      (3) A `let` class instance is immutable on Nim (a `var`-less object), so
      `let r = Row(..); r.x = 1` fails there where Python allows it; kilo writes
      through `self.rows[i].x`. Refuse the write on both backends, or make `let`
      of a class a reference.
- [ ] decorators beyond `@decorator` wrappers. Wrappers marked `@decorator`
      work on every backend, with arguments, stacked, generic, with state of
      their own (`@cached`), on functions of any arity and on methods
      (EXAMPLES/test_decorators.ady, book 8.7). Still open: one that returns
      a function of another type, and a cache on a method keyed on its
      object too. Nim refuses any other decorator, while Python passes it
      through; `@property`, `@staticmethod`, `@classmethod`, `@functools.*`
      have no Nim counterpart and keep their refusal.
- [ ] whether a class is a `ref object` on Nim is decided twice, and the two
      can disagree. An exact check over the field declarations runs first
      and the constructor follows it (`new(result)` or not); a search of the
      *emitted* field text runs after the body is generated and the type
      follows that. Where the second says ref and the first did not, the
      type is `ref object` and `newX` never allocates, so the first field
      write in `initX` dereferences nil -- a SIGSEGV at run time, not a
      compile error. The known way in was a substring match (`Build` found
      inside `BuildType`), now a whole-word match; nothing else in the repo
      disagrees today. The robust fix is one source of truth: decide once,
      before the body, or have the late check regenerate the constructor.
      `hek_nim_parser.py`, the `needs_ref` line and the `_has_self_ref`
      pre-check above it.
- [ ] a type argument written inline as a list type is not parsed:
      `first_of[[]int](rows)` is a syntax error on both backends, where a
      name (`first_of[Row_T]`, with `type Row_T is []int`) or a tuple
      (`first_of[(int, str)]`) works. Now that a generic call must name its
      types, naming a list type first is the only spelling; accept
      `[]T`, `{K}V` and the like in the brackets, or keep it a deliberate
      rule and say so in the error.
- [ ] a subrange is bounds-checked on Nim only, so the same source behaves
      differently. With `type Quantity_T is 0 .. Max_Allowed_Quantity`, on
      Nim `let q: Quantity_T = 101` does not compile and a computed value
      outside the range (`q -= 2` from 1, `q += 20` from 90) stops at its
      line; on Python the same program runs on with -1 or 110, because a
      range is a plain `int` there. The examples now lean on ranges for
      counts, so the gap matters more than it did. Check on assignment: a
      literal at transpile time, a computed value with a small `_check(x,
      lo, hi)` at each assignment and augmented assignment of a variable of
      the type, as Ada's constraint model does. The tutorial says "Nim only"
      meanwhile.
- [ ] streaming stdin — deliberately not built; the deadlock case is already
      handled, so only the in-memory limit remains (see below)
- [ ] the keyed-comprehension form `[k: v for k in E]` is a parse error on
      both backends. Consistent rather than divergent, and a missing form
      rather than a bug -- less pressing than it was, now that the
      generator can name the domain: `[Color]int = [ord(c)*10 for c in
      Color]` computes each value *from* its own key, which is what the
      keyed form was mostly wanted for. What is still missing is filling
      the slots out of domain order, the way the `[BLUE: 3, RED: 1]`
      literal does.
- [ ] a variable named `b`, `r`, `f` or `u` cannot take a tick: `b'Length`
      lexes as the start of a bytes literal and fails to parse on both
      backends. Consistent, so not a divergence, but the error names the
      wrong thing.
- [ ] Nim identifiers ignore case and underscores, so an Adascript class
      `Container` and a constant `CONTAINER` are one name there and two on
      Python. Worth a transpile-time warning: the Nim error names a
      "redefinition" at a line the author did not write.
- [ ] `Path` in expression position needs a `: Path` annotation somewhere in
      the same file. `let base: str = Path(p).name` on its own does not
      compile on Nim -- "undeclared identifier: 'Path'" -- because the Path
      prelude is injected by `_ensure_path_helper`, and only `type_name` calls
      it. Hooking the identifier instead does fire, and is still too late:
      `nim_top_decls` has been flushed by the time expressions are emitted, so
      the appended helper never reaches the output. The fix is a pre-scan, the
      way `user_top_level_procs` already works in `ady2nim.py`, not another
      emission-time hook. Binding the path to a name is the workaround, and
      reads better anyway when both `.parent` and `.name` are wanted.
- [ ] no spelling for a pattern that is not known until run time. Regex
      literals are syntax, which is the point, but it leaves a program that
      reads a pattern out of a database or builds one from parts with nowhere
      to go: `EXAMPLES/CFMU/cfmu_get_file_type.ady` matches against a pattern
      the query returned and has to say `pyimport re` for that one call, which
      drags CPython into a Nim binary. `re(expr)` appears in a couple of older
      CFMU files as if it existed; it does not. Either a `Regex(s)` value that
      `==` accepts on the right, or interpolation inside a literal.
- [ ] `.lines` on the Python backend now applies only to a receiver it can
      see is a file -- stdin, an `open(...)` call, a string literal, or a
      `File`/`str`/`Path` binding -- because `lines` is also an ordinary field
      name and `trace.lines` was being rewritten into `_lines(trace)`. The
      cases left over are a file reached through an expression the emitter
      cannot type: a `[]File` element, a field holding a handle, a call
      returning one. Those now keep `.lines` as an attribute and raise
      AttributeError, which is at least loud. A receiver-type pass would
      settle it properly.
- [ ] a single-line `when COND: stmt` body glues a following comment onto
      the Nim `of` clause instead of leaving it where it is, when that
      comment is the very next line after the case statement (at the same
      or a shallower indent -- exiting the case, not another `when`).
      Minimal repro:

          case TOOL:
              when GREP: stages = stages + "a"
              when RG:   stages = stages + "b"
          # a comment right after

      compiles to `of RG    # a comment right after:`, which Nim rejects
      ("expected: ':', but got: 'stages'") since the comment lands between
      `of RG` and its colon. Writing the last `when`'s body on its own
      indented line instead of inline avoids it -- confirmed the bug is
      specific to the single-line `stmt_line` form, not the `case`
      statement generally -- which is the workaround `TOOLS/PGREP/Pgrep.ady`
      uses (the `-ppat` stage's `case GREP_TOOL:` in `search_one`). Found
      while adding a `GREP_TOOL` enum there; `_block_inline_header_comment`
      in `HPARSEC/hek_helpers.py`, called from `when_clause.to_nim` in
      `TO_NIM/hek_nim_parser.py`, is where the trailing-comment lookup for
      a compound header lives and is the likely place the wrong comment is
      being picked up.
- [ ] a `char` reached through a *field* is not recognised as one by the
      comparison narrowing, so `r.fill == "."` over a `fill: char` fails on
      Nim ("type mismatch", string against char) and passes on Python. A
      char *variable* is fine, and so is `s[0]`, because
      `_is_nim_char_expr` looks the expression up in the symbol table by
      its whole spelling and a field access is not a name there. The `&`
      case and the `*`/repeat() case both answer this by looking the last
      dotted component up on its own; the same fallback in
      `_is_nim_char_expr` would settle it, with the caveat that a field
      name shared by two classes with different types could then narrow
      the wrong way -- which is why it is written down rather than done
      alongside the char-default fix.
- [ ] distinct types and units, what is left (the feature itself --
      `distinct`, scaling, derived and scaled units -- is done: book 2.7,
      EXAMPLES/test_distinct.ady, test_units.ady, test_money.ady):
      - the Python backend does not check an argument's type (it records
        no parameter types); building for Nim catches it.
      - a literal whose context Nim cannot see (an argument to something
        that is not a known routine) needs `V(x)` written. A table literal
        with a distinct key or value type no longer does, when declared,
        returned or passed as a known routine's argument.
      - a derived unit is float, or int for a product, and a unit cannot be
        raised to a power: `Area_T` is `Length_T * Length_T`, and there is
        no `Length_T ** 2`. Units relate by dimension (book 2.7), but only
        to the units declared: Nim's `unchained` does full dimensional
        analysis; this is deliberately smaller.
      - a conversion between two distinct types no declaration relates,
        `Duration_T(d)` for a `Distance_T` d, is refused on Nim, naming
        both types; `Duration_T(float(d))` is the spelling that says the
        units are meant. ady2py still keeps the number: it records no
        parameter types and knows a value's unit only where a name or
        operator shows it.
      - cents: `type Dollar_T is 100 * Dollar_in_cent_T` over a `distinct
        int` is done on Nim (EXAMPLES/test_cents.ady); ady2py still
        refuses scaled units. Building them there, where the argument's
        unit is known, would lift that for money, km and miles alike. The
        conversion to cents rounds with its own helper, not `round`.
- [ ] **For discussion:** let `m(k)` look up a `{K}V` or `[K]V` as `m[k]`
      does, and let a table be passed where a `(K) -> V` is expected (a
      small adapter on each backend). A pure function is a mapping, and Ada
      writes both the same way, so a computed function could become a
      precomputed table without touching a call site. Every declaration
      would still name one concrete type; only the call syntax is shared.
- [ ] `[E]{}T` cannot infer the element type of an empty set literal in its
      initialiser: `var seen: [Phase_T]{}str = [CLIMB: {}, ...]` gives Nim
      "cannot instantiate: 'A'" from initHashSet. `{}` is ambiguous on its
      own -- empty set or empty table -- and the enum-array literal is not
      passing the annotation down to its elements. `[E][]T` is fine, so it
      is the set literal specifically.
- [ ] `.map()` / `.and_then()` rewriting on `?T` (Feature 2)
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

- [ ] two slips found making EXAMPLES/ROI_JOINTJS run again and writing
      EXAMPLES/ROI_HTMX (the same page, drawn by the server, no JointJS):
      (1) `.extend(...)` on any receiver becomes `.add(...)`
      (`_PY_UNIVERSAL_METHOD_TO_NIM` in hek_nim_expr.py), so JointJS's
      `dia["ElementView"].extend({...})` -- a method of a `JsObject` -- crashed
      the page ("add is not a function") and nothing was drawn. The demo now
      goes round it with `["extend"].call(dia["ElementView"], {...})`; the
      mapping should leave a `JsObject` receiver alone. (2) an `html:` block
      takes `+ text("...")` for bare text but not a bare string
      (`"What % did you invest in "` -> `add(tmp, "...")`, "type mismatch"), so
      text mixed with tags, as in `label: "..." strong: ...`, has no plain
      spelling. Also seen: the CSS in a `style:` block comes out
      HTML-escaped (`"Segoe UI"` -> `&quot;Segoe UI&quot;`), which breaks the
      declaration. Karax's `style=` attribute is a typed `VStyle`, so
      `style="fill:#fff"` is refused; classes and a `<style>` element do.
      An attribute value in an `html:` block ends at a space, so it cannot
      hold one: `x=str(a + b)`, `class=("n" if g else "b")` and
      `viewBox=f"0 0 {w} {h}"` do not parse (a call or a spaceless f-string
      does: `x=f"{x}"`, `data_x=f"{x+w/2.0}"`). Worse, `+` joins silently:
      `marker_end="url(#head"+color[1:]+")"` compiles and writes only
      `marker_end="url(#head"`, the rest dropped without a word; and a format
      spec or a slice inside an attribute f-string (`{w:.0f}`, `{c[1:]}`)
      does not parse. The same escaping hits `>` in a `style:` block (a child
      combinator, `a > b`, comes out `&gt;`). Each should either work or say
      what it refuses.
- [x] Nim: a `T | !F` passed as an *argument* whose value is a plain T or E
      -- `f(3)` where f takes `int | !Failure_T` -- is typed from the
      parameter (EXAMPLES/test_union_args.ady).
- [x] a union of more than six members: stdlib.nim now has OneOf2..OneOf10
      (generated blocks). The Python backend still stops at six
      (`hek_py_declarations.py`).
- [ ] which side a returned value is on is read from its type; a value the
      Nim backend cannot type goes on the value side, and Nim's own type
      check then catches a failure put there by mistake. The message names
      the generated code, not the line.
- [ ] an adapter from exceptions at the boundary: a `T | !F` from a call
      that raises. Needs a decision first: what spells "this call's
      exception is that failure" -- a `try`-expression, a decorator on the
      callee, or a typed `shell:`-like block -- and how the exception's
      message maps onto `F`'s fields.

### Feature 2 — `.map()` and `.and_then()` method rewriting on `?T`

The transpiler does not currently rewrite `opt.map(f)` or `opt.and_then(f)` to
Nim's `opt.map(f)` / `opt.flatMap(f)`. Without this, chained optional
transformations must be broken into walrus steps or `do:` blocks — they cannot
appear in expression position (inside arguments, list comprehensions, etc.).

**Desired syntax:**
```python
# Expression-position pipeline — impossible today
let label: ?str = fetch_user(id)
                  .and_then(fetch_account)
                  .map(format_summary)

# In an argument
print(fetch_user(id).map(format_summary) or "not found")
```

**Implementation sketch:**
- In `hek_nim_expr.py`, detect `expr.map(f)` and `expr.and_then(f)` call
  patterns where `expr` is typed as `Option[T]`.
- Rewrite `.map(f)` → `.map(f)` (Nim options already has this).
- Rewrite `.and_then(f)` → `.flatMap(f)` (Nim's name for monadic bind on Option).
- The rewriting requires knowing that `expr` is Option-typed — check the symbol
  table or the call's receiver type.
- Complexity: ~300–500 lines in `hek_nim_expr.py`.

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

## Substitution as an expression

`target = s/pat/repl/` rewrites a variable in place, which means a name
cannot be derived from another in one step: `EXAMPLES/CFMU/ftps_get.ady`
copies first and substitutes second, four times in a row.

    var no_gz : str = remote_file
    no_gz = s/\.gz$//g

An expression form -- `let no_gz: str = remote_file.sub(/\.gz$/, "")`, or
whatever spelling keeps the sed flavour -- would make the copy unnecessary
and leave the statement form for the in-place case. Needs a `sub` on `str`
in both emitters.

## `{!var}` quoting not supported in shell block form

In single-line `shell:`, `{!var}` quotes the value as a single shell argument
(`quoteShell`). In block form (`shell(join = ";"):` with indented lines),
`{!var}` fails with `undeclared identifier: '!'`. Only `{var}` (unquoted
interpolation) works in block lines.

```adascript
# Works:
let rc: int = shell: sd 'a' 'b' {!out_file}

# Fails:
let rc: int = shell(join = ";"):
    sd 'a' 'b' {!out_file}    # Error: undeclared identifier: '!'

# Workaround — use {var} (safe when the path has no special characters):
let rc: int = shell(join = ";"):
    sd 'a' 'b' {out_file}
```

## Union returns: what is left from rewriting lispy.ady

- An f-string inside a shell interpolation, `{!f"HEAD {short}"}`, breaks the
  emitted Nim ("closing \" expected"); bind it to a `let` first.

Also: a variant record is a value type on Nim, so a variant that holds
itself through a field (a closure holding its body) needs the holder to be a
class marked `@virtual` -- correct, but `@virtual` is documented as being for
cross-module subclasses only.

## `n'Image` on an int or a str emits `.name` in Python

`def f(n: int) -> str: return n'Image` (a `str` likewise) becomes `return (n).name` on the
Python backend, which raises at run time; Nim's `$(n)` is right. The image of
an enum member is `.name`, and the emitter takes any name it cannot type for
one. It went unseen because the shared tests print enums and strings.

## Found writing EXAMPLES/bench_search.ady

- `case $1:` (a command-line argument as the subject) is emitted as
  `if if paramCount() >= 1: paramStr(1) else: "" == "find":`, which Nim does
  not parse; bind it first, `let mode: str = $1`. The `$n` expansion needs
  parentheses wherever it is an operand.
- `f"{x:7.0f}"` prints `5.` on Nim -- its format spec keeps the dot at zero
  precision -- and `5` on Python. `{int(x):7}` is the same on both.
- `for w in f(path): ... int(w)` on Nim leaves `w` untyped, so `int(w)` on a
  `str` is emitted as-is and fails -- in a comprehension too,
  `[int(w) for w in f(path)]`; a typed `let words: []str = f(path)` first
  avoids it, and the routine's declared return type is all the emitter needs.

## A record literal with fewer positional arguments than fields, on Nim

`Press_T(ESCAPE)` for `record: key: Key_T; text: str = ""` works on Python but on
Nim is emitted as the conversion `Press_T(ESCAPE)`: "type mismatch: got 'Key_T'
but expected 'Press_T = object'". `Press_T(CHAR, "x")` and `Press_T(key=ESCAPE)`
are fine; a program built for both backends would meet it.

## Found writing EXAMPLES/VI/vi_curses.ady (Adascript on Nim)

Each is worked around there, and none is needed for Python:

- `xs.insert(i, x)` is Python's order on both backends; on Nim the call is Nim's
  `insert(xs, x, i)`. `xs.insert("b", 1)` works on Nim and fails on Python.
- `Editor(path).run()` on a temporary: Nim wants a `var` receiver.
- `return n` for an `n` narrowed by `if n is Failure_T: return ...` is not
  unwrapped on Nim (a method call on it is): `case n: when int: return n` is.
- `T(fd = 0, events = POLLIN)` on a Nim object type (not an Adascript record) is
  emitted as a call with `=` arguments; fields have to be assigned.

## Modules on the Python backend (ady2py merges what ady2nim links)

`ady2py` replaces `import X` by X.ady's text (see `include_ady_modules`).
Known, and not done:

- `geometry.distance(a, b)` is rewritten to `distance(a, b)` (ady_modules.resolve_imports),
  so it works, but not beside a `distance` of the importing file's own.
- One namespace: a name defined in two modules is the later definition.
- A parse error's line number is a line of the merged text.
- The libraries bundled with ady2nim (`TO_NIM/STDLIB/*.ady`) are not merged.
- `nimport math` then an unqualified `sqrt` is Nim's `math`; on Python it is a
  NameError (EXAMPLES/PROJECT is that program).

## `return n` of a narrowed result, in a method, on Nim

In a plain function `if n is Failure_T: return 1` then `return n` works (it is
emitted `n.value`). In a method it is emitted `is_err(n)` and `return n`,
and Nim refuses the Result. EXAMPLES/VI/vi_editor.ady keeps that code in a function
(`count_of`) for this.

## Found porting EXAMPLES/MOON/moon_sim.ady

Each open one has a workaround in that file.

- [ ] `from MAP_UTILS/map_base import` works from a sibling directory only because the
      parent is searched. (The map_* modules stay Nim-only, by decision.)

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
