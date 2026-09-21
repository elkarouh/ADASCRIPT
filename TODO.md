# TODO

Open items only.  The write-ups for everything already fixed — 26 numbered
bugs and the shell-syntax work — were removed once done; they are in the git
history of this file if the reasoning behind one of them is ever wanted.

- [ ] streaming stdin — deliberately not built; the deadlock case is already
      handled, so only the in-memory limit remains (see below)
- [ ] `EXAMPLES/JOINTJS_DEMO/roi_glue.ady` crashes ady2py on `jsvar`, which the
      grammar marks JS-backend-only. The file targets neither Python nor the
      Nim C backend (it does not compile there either), so this is a bad
      diagnostic rather than a missing feature: ady2py should say the construct
      is not for this backend instead of raising AttributeError.
- [ ] containers holding enum values stringify differently. `print xs` where
      `xs: []Node_T` gives `@[A, B, C, D]` on Nim and
      `[<Node_T.A: 0>, <Node_T.B: 1>, ...]` on Python -- Nim's seq syntax and
      bare enum names against Python's list syntax and Enum *repr*. It is
      what stops most examples from producing byte-identical output on the
      two backends. A bare enum agrees now (the generated class gets a
      `__str__` returning the member name, so `'Image`, `str()`, `print` and
      f-strings all give `A`); it is a container's elements that do not,
      because a container formats its elements with `repr`. Giving the class
      a `__repr__` as well would leave only the `@` prefix -- and the set
      ordering, which `{}T` never promised anyway.
- [ ] the keyed-comprehension form `[k: v for k in E]` is a parse error on
      both backends. Consistent rather than divergent, and a missing form
      rather than a bug -- less pressing than it was, now that the
      generator can name the domain: `[Color]int = [ord(c)*10 for c in
      Color]` computes each value *from* its own key, which is what the
      keyed form was mostly wanted for. What is still missing is filling
      the slots out of domain order, the way the `[BLUE: 3, RED: 1]`
      literal does.
- [ ] `.keys()` and `.items()` on an `[E]T` work on Python and do not exist
      on Nim, where the type is an `array[E, T]`: `score.keys()` fails with
      "type mismatch ... expected Table". Iteration and indexing agree now;
      these two do not. Nim's `pairs`/`keys` iterators over an array are the
      shape to map onto.
- [ ] ady2py generates annotations whose names are not in scope at import
      time. `Callable` is fixed (the emitter now adds the typing import),
      but a class that names itself -- `def __and__(self, other: Region)`
      inside `class Region` -- is still a NameError, because Python
      evaluates annotations eagerly while Adascript writes them the way Nim
      does, as compile-time types. `from __future__ import annotations` is
      the right answer and is a one-line change, but every expected output
      in `ady2py --test` and `test_ady2py.py` is a literal string that would
      gain the import line: 43 and 122 cases respectively fail on it. Worth
      doing together with a pass over those fixtures.
- [ ] `&` as string concatenation is Nim-only: `a & b` over two strings
      works there (Nim spells concat `&`) and raises `unsupported operand
      type(s) for &: 'str' and 'str'` on Python, where `&` is bitwise-and.
      `+` is the portable spelling -- the Nim emitter rewrites it to `&`
      when it can tell an operand is a string -- so this is a matter of
      examples not reaching for `&`, which the book now says. What made it
      look unavoidable was a gap in that rewrite, fixed: `str(x) + str(y)`
      renders as `$x + $y` and a leading `$` was not counted as evidence
      of a string, so `+` failed on Nim in exactly the position where
      `sudoku.ady` had reached for `&`. Worth a transpile-time warning on
      `&` between strings rather than a Python run-time error.
- [ ] `T'Last` on an alias of a non-ordinal type emits nonsense on Python.
      With `type Distance_T is float`, `Distance_T'Last` is `Distance_T.high`
      on Nim -- which is `inf`, and right -- and `(len(Distance_T) - 1)` on
      Python, which raises `TypeError: object of type 'type' has no len()`.
      The tick means the largest value of the type; the Python emitter is
      reaching for the ordinal-domain reading without checking that the
      type has one. `Inf` is the portable spelling meanwhile, and is what
      `dijkstra.ady` uses.
- [ ] `int == int / int` compiles on Python and is rejected by Nim, whose
      `/` yields a float and whose `==` has no int/float overload. Python
      says `4 == 8 / 2` is True. Either the emitter converts, or the
      limitation is documented.
- [ ] a variable named `b`, `r`, `f` or `u` cannot take a tick: `b'Length`
      lexes as the start of a bytes literal and fails to parse on both
      backends. Consistent, so not a divergence, but the error names the
      wrong thing.
- [ ] `Path` joins diverge on a `.` segment once three terms are chained:
      `Path(".") / ".git1" / "x.txt"` is `./.git1/x.txt` on Python and
      `.git1/x.txt` on Nim. Two terms agree (`Path(".") / ".git1"` is
      `./.git1` on both), and so does `Path(".") / Path(".git1/x.txt")` --
      only the chained form differs, because Nim's `joinPath` normalizes a
      head that already holds a separator and `os.path.join` never
      normalizes anything. Same expression, two different strings: it
      changes printed output, dict keys and `==`, even though both still
      name the same file. Fixing it means one `/` doing the same thing on
      both sides; the lexical `os.path.join` rule is the easier one to
      match, but it means shadowing the `/` that std/paths exports.
      `git1.ady` sidesteps it by joining in two steps.
- [ ] ady2nim: a value-returning call used as a statement gets `discard` inside
      a plain `def` but not inside a *method body* or at module level, so the
      same source compiles on Python and fails on Nim with "expression ... has
      to be used (or discarded)". The richer logic in `hek_nim_stmt.py` is the
      disabled fallback; the active `stmt_line.to_nim` in `hek_nim_parser.py`
      only discards `pop` and nimpy calls.
- [ ] Nim identifiers ignore case and underscores, so an Adascript class
      `Container` and a constant `CONTAINER` are one name there and two on
      Python. Worth a transpile-time warning: the Nim error names a
      "redefinition" at a line the author did not write.
- [ ] a `[]?T` parameter does not accept a plain list. `def sequence[T](items:
      []?T)` -- the combinator Feature 2 below is really about -- is written
      and compiled, but no call reaches it: `sequence([1, 2, 3])` wraps the
      whole literal as `some(@[1,2,3])` and `let xs: []?int = [1,2,3]` fails
      to build at all, "got 'seq[int]' ... expected 'seq[Option[int]]'". The
      elements need lifting, not the container. Generic syntax is no longer
      what blocks these; this is.
- [ ] `.isdigit()` is ASCII-only on Nim and Unicode-aware on Python:
      a string of Arabic-Indic digits answers false there and true here. It is what every
      strutils predicate does -- `TO_NIM/STDLIB/strscan.ady` says so in its
      header -- and it became *reachable* rather than new when the string
      overload landed, since before that a string receiver did not compile at
      all. The same gap is waiting behind `.isalpha()`, `.isalnum()`,
      `.isspace()`, `.islower()` and `.isupper()`, none of which have a string
      overload yet. Either the Python backend narrows to ASCII, or unicode's
      predicates go behind the Nim ones, or it is documented per method.
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
- [ ] a bare file test as an `assert` condition is dropped on Nim. `assert -s
      path` emits just the path -- "expression ... has to be used (or
      discarded)" -- losing both the assert and the operator, while `assert
      not -s path` and `assert (-s path)` are both fine. So it is the
      unnegated, unparenthesised form that the assert emitter does not route
      through the file-test rule.
- [ ] no spelling for a pattern that is not known until run time. Regex
      literals are syntax, which is the point, but it leaves a program that
      reads a pattern out of a database or builds one from parts with nowhere
      to go: `EXAMPLES/CFMU/cfmu_get_file_type.ady` matches against a pattern
      the query returned and has to say `pyimport re` for that one call, which
      drags CPython into a Nim binary. `re(expr)` appears in a couple of older
      CFMU files as if it existed; it does not. Either a `Regex(s)` value that
      `==` accepts on the right, or interpolation inside a literal.
- [ ] `s.split(None, maxsplit)` emits `split(s, nil, 1)`, which is not valid
      Nim. Python's "split on runs of whitespace, at most n times" has no
      single Nim call -- `splitWhitespace` takes no maxsplit -- so it wants a
      helper. It is the last thing keeping `cfmu_get_file_type.ady` from
      compiling.
- [ ] an escaped delimiter in the *replacement* half of `s///` keeps its
      backslash. `s = s/(\d{4})-(\d{2})-(\d{2})/$+3\/$+2\/$+1/g` gives Nim
      `"$3\/$2\/$1"`, which is not a valid character escape and does not
      compile, and Python `r'\3\/\2\/\1'`, which leaves a stray backslash in
      the result. The pattern half is fine -- `s/^[.\/]+//g` works on both --
      so it is only the replacement scanner that keeps the backslash instead
      of dropping it.
- [ ] a Nim keyword used as a tuple-unpacking target is not escaped. `let out:
      str = "x"` emits `` let `out` `` and is fine; `let (out, rc) = shell: echo
      hi` emits a bare `out` and fails with "identifier expected, but got
      'keyword out'". The plain-declaration path calls `_nim_user_ident` and
      the unpacking path does not.
- [ ] `for x in Enum_T'Range:` iterates in a different order on each backend,
      and on Python in a different order on each *run*. `'Range` is the set of
      members, which the Nim backend renders as a `set[Enum_T]` -- ordinal
      order -- and the Python backend as `set(Enum_T)`, whose order is hash
      order. A report built that way comes out shuffled and differently
      shuffled every time. `for x in Enum_T:` and `for x in Enum_T'First ..
      Enum_T'Last:` both give declaration order on both backends and are what
      the examples use; the divergence is in the set form. Either Python emits
      something ordered for `'Range` in a for-loop, or `'Range` is documented
      as unordered and the examples keep away from it.
- [ ] `sorted(d.keys())` over a `{K}V` does not compile on Nim: "undeclared
      field: 'sorted'", because `keys` is an iterator there and wants
      `toSeq`. Same family as the `[E]T` `.keys()` entry above. An example
      that needs a stable report order has to carry its own list of keys.
- [ ] `.lines` on the Python backend now applies only to a receiver it can
      see is a file -- stdin, an `open(...)` call, a string literal, or a
      `File`/`str`/`Path` binding -- because `lines` is also an ordinary field
      name and `trace.lines` was being rewritten into `_lines(trace)`. The
      cases left over are a file reached through an expression the emitter
      cannot type: a `[]File` element, a field holding a handle, a call
      returning one. Those now keep `.lines` as an attribute and raise
      AttributeError, which is at least loud. A receiver-type pass would
      settle it properly.
- [ ] a comment between `case X:` and its first `when` is a parse error on
      both backends: "got RichNL, expected one of: ... regex_lit". A comment
      above the `case`, or between two `when` clauses, is fine -- it is only
      the position before the first clause, where a reader naturally puts the
      note explaining what the block dispatches on.
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
- [ ] a user-defined scalar type is an alias, not a distinct type, so
      `type Velocity_T is float` documents a unit without enforcing it:
      `let d: Distance_T = v` over two float aliases compiles on both
      backends. `Path` proves the machinery is there -- it is a distinct
      string on Nim and a str subclass on Python, and `p = s` is refused on
      both -- so the shape of the feature is `type Velocity_T is distinct
      float`, with an explicit `Velocity_T(x)` to get in and `float(v)` to
      get out. DOCS/WHY_ADASCRIPT.md rests its central argument on the name
      alone and says so; this is what would let it rest on the compiler.
- [ ] `[E]{}T` cannot infer the element type of an empty set literal in its
      initialiser: `var seen: [Phase_T]{}str = [CLIMB: {}, ...]` gives Nim
      "cannot instantiate: 'A'" from initHashSet. `{}` is ambiguous on its
      own -- empty set or empty table -- and the enum-array literal is not
      passing the annotation down to its elements. `[E][]T` is fine, so it
      is the set literal specifically.
- [ ] `.map()` / `.and_then()` rewriting on `?T` (Feature 2)

---

## Monad support improvements (high ROI)

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

## The one cross-backend difference the catalogue named

`"".splitlines()` is `[]` on Python and `@[""]` on Nim -- one blank line
rather than none. It is a standard-library difference rather than a
transpiler bug, and it cannot be fixed in one without picking a side, so
filter the empty lines after splitting input that might be empty.
Everything else the outside session catalogued now compiles and runs the
same on both backends; the probes are in the session log.
## Nim keyword as a tuple-unpacking target

## Auto-unwrap incomplete after `continue if is None`

After `continue if x is None`, the transpiler auto-unwraps `x` for tick
attributes (`x'Image` → `$(x.get())`) but **not** inside tuple constructors
or `let` assignments:

```adascript
let bt: ?BuildType = build_type_from(name)
continue if bt is None
# These work — auto-unwrap applied:
type_to_file[bt'Image] = filepath       # ok: $(bt.get())
print bt'Image                           # ok

# These fail — auto-unwrap NOT applied:
builds.append((name: name, btype: bt))   # error: got Option[BuildType], expected BuildType
let btype: BuildType = bt                # error: same
