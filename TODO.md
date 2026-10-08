# TODO

Open items only.  The write-ups for everything already fixed — 26 numbered
bugs and the shell-syntax work — were removed once done; they are in the git
history of this file if the reasoning behind one of them is ever wanted.

- [ ] an imported function named like a builtin is read as the builtin. A
      same-file `def run` overrides the builtin `run([...])` (the tutorial says
      so), but `from loop import run` does not: the call is the builtin's, and the
      importer is given the process runtime (`adascriptRun` and the rest) and its
      imports -- `osproc`, `posix`, `streams`, `strtabs`, `times` -- which can
      clash with the importer's own: illwill's `Key` against posix's, "ambiguous
      identifier", in a file that never mentions a process. Found moving the vi
      loop into a module of its own, where it is called `edit` to stay clear of it. The
      builtins (`run`, `die`, `warn`, ...) should give way to an imported name as
      they do to a local one.
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
- [ ] general function decorators on Nim. Today the Nim backend knows five
      annotations (`@contextmanager`, `@virtual`, `@proc`, `@export`,
      `@used`) and refuses any other decorator, while Python passes every
      one through. `@d` on `def f` means `f = d(f)`, which Nim can express:
      emit the proc under a hidden name and bind `let f = d(fHidden)` -- a
      closure, so `d` must take and return a proc type (`(int) -> int`).
      That covers wrappers written in Adascript (`@twice`, timing,
      memoizing). Not covered, having no Nim counterpart: `@property`,
      `@staticmethod`, `@classmethod`, `@functools.*` -- those stay
      Python-only, and keep their refusal. Open questions: a decorator on a
      method (self), one taking arguments (`@retry(3)`), and several
      stacked. Test on both backends, as test_union does.
- [ ] stateless decorators, by rewrite -- the narrow, closure-free way to the
      entry above, and enough for `TOOLS/LV/lv.py`, whose `@align(64)` puts a
      column's width next to the function that produces it (`lv.ady` has
      to pad at the call site instead: `colored_viewname(v).alignLeft(64)`).
      A wrapper is an ordinary function handed the function it wraps:

          @decorator
          def aligned(width: Positive, f: (str) -> str, s: str) -> str:
              return f(s).alignLeft(width)

          @aligned(64)
          def colored_viewname(view_name: str) -> str: ...

      Before the parse, in both backends (as `expand_variant_literals`
      does, in `ady_stmt.py`), the decorated `def` becomes the original under
      a hidden name, `colored_viewname__body`, plus a forwarding `def` that
      returns `aligned(64, colored_viewname__body, view_name)`. Stacked
      decorators apply bottom-up; a recursive call inside the body goes
      through the decorated name, as in Python. Checked at transpile time,
      each a one-line `SyntaxError`: the wrapper's `f` parameter has the
      decorated function's type; the parameters after `f` are the decorated
      function's, in order; the leading ones are the decorator's arguments;
      a decorator not marked `@decorator` keeps today's refusal. No
      closures, so nothing waits on `def` returning a `lambda`.
      Limits, by design: no per-function state (`@cached`, a call counter
      need a class or a global), one signature per wrapper (a wrapper for
      any signature needs generics, which are explicit), top-level `def`s
      only to begin with. Line numbers in errors shift by the added lines,
      as with variant literals. About a day, mostly tests: one file compared
      between the backends, three or four refusals, docs. Worth building
      when a second wrapper is reused across several functions; `lv.py`
      alone is one use, and the call-site form is as short.
- [ ] `+` of two calls returning lists does not build on Nim. `evens(4) +
      odds(4)`, each `-> []int`, is emitted as it is, and nim has no `+`
      for seqs ("type mismatch ... seq[int]"); the same on two typed
      locals, `a + b`, becomes `a & b` and builds. Python takes both. The
      list concatenation is recognised from a name's declared type but not
      from a call's result type. Worked around in
      TOOLS/TCHECK/LIBS/baselines.ady (`diff_summaries`) with two typed
      locals.
- [ ] `s.split()` of a string with leading whitespace differs between the
      backends. `"    ./c.ksh  gone".split()[0]` is `"./c.ksh"` on Python,
      which drops the empty fields, and `""` on Nim, whose strutils `split`
      keeps an empty field for each leading separator. Map a bare `split()`
      to `splitWhitespace()`. Worked around in
      TOOLS/TCHECK/LIBS/baselines.ady (`script_of`, `marked`) with
      `.strip().split(" ")[0]`.
- [ ] a class named after a Nim keyword does not build on Nim: `class Out:`
      emits `proc new`Out`*()`, the constructor's name pasted onto the
      backticked type name, which nim rejects ("invalid indentation"). The
      constructor has to be named from the bare name -- `newOut` -- wherever
      it is declared and called.

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
- [ ] a generic method does not build on Nim. `def echo[T](self, x: T) ->
      T` inside a class is emitted without `T` among the proc's generic
      parameters ("undeclared identifier: 'T'"); Python takes it (PEP 695).
      Generic functions and generic classes are fine. It also means the rule
      that a generic call names its types is checked for module-level
      functions only: a generic method called as `h.echo(5)` is not, since
      no such call can build on Nim anyway. Emit the method's own `[T]`, and
      extend `check_generic_calls` to `obj.method(...)` once it does.
- [ ] directly constructing a generic class does not build on Nim.
      `class Box[T]` with `let a: Box[int] = Box[int](3)` is emitted as
      `Box[int](3)` -- a conversion of the literal -- instead of the
      constructor call `newBox[int](3)`; Python takes it. Generic classes are
      used by subclassing with named arguments (`class X(Maximizer[S, D,
      R])`), which works, so nothing in the repo constructs one.
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
- [ ] a subrange with a negative bound does not declare on either backend.
      `type Off_T is range -2 .. 1` emits `Off_T = range(<Filter object>,
      1 + 1)` on Python -- a parser node reaches the output -- and a type
      mismatch on Nim. The unary minus is not being folded into the literal
      where the bounds are read, so both `tick_types` and the rendered alias
      get it wrong. Loud on both sides rather than divergent, and a
      non-negative subrange is unaffected.
- [ ] `p / ".."` is not the same path on the two backends. Nim's `joinPath`
      collapses the `..` as it joins, so `Path("/a/b") / ".." / "c"` is
      `/a/c`; pathlib keeps it, giving `/a/b/../c`. Both name the same
      directory, so `-d` and `readFile` agree and only *printed* paths
      differ -- which makes it easy to miss until a log or a diff report
      shows two spellings. `.parent` agrees on both and is the spelling to
      use (`saved_logs_dir` in `Tcheck_tact.ady` says so in its docstring).
      Either normalise in the Python backend's `/` or reject a `".."`
      component at transpile time with a pointer to `.parent`.
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
- [ ] implicit return does not work under a `?T` return type, so every
      branch of an optional-returning function needs an explicit `return`.
      Two different failures, depending on the branch. A value as the tail
      expression is wrapped one level too deep -- `def f(s: str) -> ?BT`
      ending in `when others: OP` gives "got 'Option[BT]' for 'some(OP)'
      but expected 'BT'", because the case itself is typed `BT` and the
      `some()` lands inside it. A bare `None` as the tail reaches Nim as
      `nil`, where `isNil` is ambiguous between its `ptr T` and `ref T`
      overloads. The `if/else` form fails the same way as the `case` one,
      so it is the implicit return rather than the construct around it.
      `TOOLS/TCHECK/Tcheck_tact.ady`'s `build_type_from` says so where it
      spells out the returns it would otherwise leave implicit.
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
        no `Length_T ** 2`. Nim's `unchained` does full dimensional
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
- [ ] `round(x)` differs between the backends. Python's returns an int and
      rounds half to even (`round(2.5)` is 2); Nim's `round` is in `math`,
      which Adascript does not import for it ("undeclared identifier"),
      returns a float, and rounds half away from zero. Give it one
      meaning -- an int, and say which way halves go -- and emit the import.
- [ ] a `?T` compared with a plain value compiles on Python and not on Nim.
      `let x: ?int = f(...)` then `x == 7` is True on Python; Nim has no
      `==` between `Option[int]` and an int ("type mismatch"). The same
      through a function-typed variable, `p("7") == 7` for `p: (str) ->
      ?int`. `x is not None and x == 7` is the spelling that works on both,
      or the emitter could unwrap for the comparison.
- [ ] a `def` returning a `lambda` does not build on Nim. `def twice(f: (int)
      -> int) -> (int) -> int: return lambda x: f(f(x))` is emitted as a
      nested `proc(x: auto): auto`, which Nim rejects ("a nested proc can
      have generic parameters only when it is used as an operand"). The
      lambda's parameter and result types are known from the declared
      return type and should be written out; Python takes it. The same
      goes for a lambda in a `{str}(float) -> float` table literal
      (`{"sqrt": lambda x: sqrt(x)}`): the declared type of the table
      gives the lambda's types, and they are not written out. It stopped
      lispy's built-ins from being a table of one-line procedures.
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

- [x] Nim: a `T | !F` passed as an *argument* whose value is a plain T or E
      -- `f(3)` where f takes `int | !Failure_T` -- is typed from the
      parameter (EXAMPLES/test_union_args.ady).
- [x] a union of more than six members: stdlib.nim now has OneOf2..OneOf10
      (generated blocks). The Python backend still stops at six
      (`hek_py_declarations.py`).
- [ ] an optional union written out, `int | float | None`, stays refused on
      purpose: `None` goes with one other type, and `type Num_T is int |
      float` with `?Num_T` says the same thing with a name. Revisit only if
      the name proves a burden.
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

## The one cross-backend difference the catalogue named

`"".splitlines()` is `[]` on Python and `@[""]` on Nim -- one blank line
rather than none. It is a standard-library difference rather than a
transpiler bug, and it cannot be fixed in one without picking a side, so
filter the empty lines after splitting input that might be empty.
Everything else the outside session catalogued now compiles and runs the
same on both backends; the probes are in the session log.
## Nim keyword as a tuple-unpacking target

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

## Union returns: four Nim-side slips found rewriting lispy.ady

`T | !F` works in free functions and most methods, but on Nim:

- A string holding a `)` inside a call's argument list --
  `return reject("missing )")` -- makes the analysis of what is returned lose
  its place: the failure is wrapped as `.ok(...)` instead of `.err(...)` and
  Nim refuses it. Naming the string first (`let MISSING: str = "missing )"`)
  avoids it. The same for `return Failure_T(message="missing )")`.
- `if r is F: return r` narrows `r` for the rest of a *free function*, but
  not at the top level of a *class method* (deeper blocks are fine): a later
  `use(r)` still sees the Result. `case r: when F: ... when T: ...` narrows
  in both.
- The return type of a method is looked up by its bare name, so a method
  `run` returning `str | !F` is taken for the free function `run` returning
  `str` when the two share a file.
- A method named `get` is taken for a dict's `get`, and `bind` is a Nim
  keyword: a Nim-reserved or stdlib-shadowing method name fails late, inside
  Nim, rather than with a message from Adascript.
  `out` is the same as a parameter name (`def f(out: Path)` gives "typedesc[var]"
  in the generated `quoteShell(out)`).
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

## A dropped `T | !F` is only refused after a name

`p.relative_to(base)` as a statement is refused ("drops a failure"), but
`Path("/a/b").relative_to(base)` -- the receiver a call -- is not, on either
backend: the check reads `name.name(...)` and gives up on anything before the
last dot that is not a bare name. The same is true of any routine returning a
`T | !F`, `f(x).g(y)` included. On Nim the unused Result then fails to
compile; on Python the failure is dropped silently.

## `case r:` over a built-in failure and `str`

`case r: when ShellFailure_T: ... when str: ...` (r a `str | !ShellFailure_T`)
emits `case ShellFailure_T:` on Python, a capture pattern that makes the next
one unreachable: a SyntaxError. A user's own record type works. Use
`if r is ShellFailure_T: ... else: ...` for now.

## `x.strip().replace(...)` on a `T | !F` that a test narrowed

After `if r is ShellFailure_T: return ...`, `r.strip()` is unwrapped on Nim but
`r.strip().replace(...)` is not (`strip(r)` mismatch), nor is `let text: str = r`.
Split the chain into a `let` of the first call.

## A record literal with fewer positional arguments than fields, on Nim

`Press_T(ESCAPE)` for `record: key: Key_T; text: str = ""` works on Python but on
Nim is emitted as the conversion `Press_T(ESCAPE)`: "type mismatch: got 'Key_T'
but expected 'Press_T = object'". `Press_T(CHAR, "x")` and `Press_T(key=ESCAPE)`
are fine; a program built for both backends would meet it.

## Found writing EXAMPLES/VI/vi_curses.ady (Adascript on Nim)

Each is worked around there, and none is needed for Python:

- `a[:i] + b[j:]` over two list slices, `line[:i] + tail(...)` over string slices
  and `self.lines[i] + self.lines[j]` are emitted with Nim's `+` (a set or number
  operator), not `&`: the operand types are not inferred from a slice or an index
  of a field. With a typed `let` for each operand it is `&`.
- `self.count += press.text` on a `str` field is emitted `+=`, not `&=`.
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

- [ ] units: `SquareMeters_T * Meters_T` has no unit (a chain is two-at-a-time).
- [ ] `from MAP_UTILS/map_base import` works from a sibling directory only because the
      parent is searched. (The map_* modules stay Nim-only, by decision.)
- [ ] units: `sqrt` of a unit. `Speed_T(sqrt(float(mu) / float(radius)))`, `half_period`, the Moon's
      mean motion and `sqrt(float(dt))` in the IMU all go through floats; `sqrt(SpeedSq_T)` is a
      `Speed_T`, and `sqrt(Duration_T)` has no unit at all.
- [ ] units: a unit with two derivations. `Force_T` is `Mass_T * Accel_T`, but the mass flow wants
      `Force_T / Speed_T` and `MassFlow_T * Duration_T`; `v^2 - mu/r` (`Mu_T / Meters_T`) and the
      products `AngMom_T * AngMom_T` have no unit either. `Propulsion.thrust` and `orbital_elements`
      keep a float block.
- [ ] units: an angle times a length. A radian is dimensionless, so `radius * angle` is a length;
      `arc` (the one place that takes `float(Radians_T(angle))`) says so.
- [ ] `max(unit, 1e-9)` and `min`/`max` with a literal beside a unit do not compile on Nim (the literal is
      not typed); `max(a, Meters_T(1e-9))` does.
- [ ] a literal on the LEFT of `-` takes the wrong unit: `180.0 - n * t` (n: `AngularRate_T`, t:
      `Duration_T`) came out as `Duration_T(180.0) - ...` and did not compile. Workaround: a `const`.
- [ ] a literal in an explicit generic call is not typed: `clip[Speed_T](x, -2.0, 2.0)` fails
      (constants `SIDE_MAX` and friends instead), and a `const` initialised by `5.0 * 86400.0` stays a float.
- [ ] an `int` beside a float (`0.9 * i`) is refused on Nim; the example has `fraction(i, n)`. A cast the
      language could take over, as Python does.
- [ ] a unit-typed constructor argument is spelled out where a class has two constructors
      (`Velocity(Speed_T(0.0), Speed_T(0.0))`): a literal to an overloaded name is refused on Nim.

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
* **Units**: `SquareMeters_T * Meters_T` has no unit (a chain is two-at-a-time), so a cube is taken
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

- [ ] A literal beside `==` (and the other comparisons) on a tuple subscript of a call, on
      Nim: `assert books.profit_and_loss()[2] == 130_000` (the tuple's third field is a
      `Cents_T`, a `distinct int`) emits a bare `130000` and Nim reports a type mismatch.
      The literal takes the declared type next to a name or a field, but not next to
      `f(...)[i]`. Workaround in the example: unpack with `let (revenue, expenses, profit) = ...`.

## Found writing TOOLS/ACCOUNTING/ledger.ady

- [ ] a parameter is made `var` when its name, followed by ` = `, appears
      inside a string literal: `self.db.value("SELECT number FROM accounts
      WHERE name = ?", [name])` made `name` a `var string`, and every caller
      passing a `let` or a field was refused ("expression is immutable, not
      var"). The mutation scan should skip string contents. The ledger writes
      `WHERE name IS ?` to stay clear of it.
- [ ] a stale transpile is kept when a dependency failed to parse: compiling
      test_accounting_model.ady while accounting_model.ady had a parse error
      cached the test's Nim without the model's types (`g.total() == 0` lost
      its `Cents_T(0)`), and fixing the model did not refresh it -- the test
      kept failing until `~/.cache/adascript/cache-<hash>` was removed. A
      failed dependency should leave nothing cached, or the cache key should
      cover the dependencies' contents.
- [ ] `assert r is not F` does not narrow `r` for the lines after it (an `if
      r is F: die(...)` does not either, without `else:`), so a test takes a
      value that must not fail through a helper with `case r:`.
- [ ] a `let` that shadows an outer one of the same name narrows as the
      outer: in ledger.ady's main, `let read: Books | !BookFailure_T` inside
      the `else:` of an outer `let read: Config | !BookFailure_T` gave
      "undeclared field: 'detail' for type Books" on `read.detail`. The
      inner one is named `loaded` instead.
- [ ] a module-level function used before its `def` in another function's
      body (`setTimeout(pick_shown, 50)` with `pick_shown` defined below) is
      "undeclared identifier" in the Nim, though calling one before its def
      works elsewhere: forward declarations miss a function passed as a value.
