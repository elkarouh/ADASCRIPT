# TODO

Open items only.  The write-ups for everything already fixed — 26 numbered
bugs and the shell-syntax work — were removed once done; they are in the git
history of this file if the reasoning behind one of them is ever wanted.

- [ ] streaming stdin — deliberately not built; the deadlock case is already
      handled, so only the in-memory limit remains (see below)
- [ ] `EXAMPLES/JOINTJS_DEMO/roi_glue.ady` crashes py2py on `jsvar`, which the
      grammar marks JS-backend-only. The file targets neither Python nor the
      Nim C backend (it does not compile there either), so this is a bad
      diagnostic rather than a missing feature: py2py should say the construct
      is not for this backend instead of raising AttributeError.
- [ ] py2py: `nimport os` + `os.path.join(...)` emits `os.` without importing it,
      so the program dies at run time with `NameError: name 'os' is not
      defined`. Three lines reproduce it: `nimport os` / `let b: str =
      os.path.basename("/a/b.txt")` / `print b`. Add an `os.makedirs(...)`
      call anywhere and it starts working, because that one *is* rewritten
      into an import. Either honour a Python-available module named by
      `nimport` when it is actually used, or say so at transpile time instead
      of at run time. (`git1.ady` used to depend on that accident; it now
      names no `os.` at all, so it is no longer a witness.)
- [ ] `print x, y` puts a space between the arguments on Python and none on
      Nim: `print "n=", 1` gives `n= 1` there and `n=1` here. Same source,
      different output, which is the one thing the two backends must not do.
- [ ] `[char]T` indexed by a quoted literal compiles on Python and fails on
      Nim. `var freq: [char]int` / `freq['a'] = 3` works on Python (the
      array becomes a `dict[str, int]`) but emits `freq["a"]` for Nim, where
      the type really is `array[char, int]` and a string cannot index it.
      Adascript inherits Python's lack of a char literal, so `'a'` is a
      one-character string. `freq[chr(97)]` works on both and is the
      documented spelling; either the emitter should turn a one-character
      string index into a Nim char literal when the domain is `char`, or the
      mismatch should be reported at transpile time.
- [ ] iterating an `[E]T` means two different things. `for x in score:`
      where `score: [Color]int` yields the *values* on Nim (it is an
      `array[E, T]`) and the *keys* on Python (it is a `dict`), and the
      Python order is the literal's, not the enum's. Indexing agrees, so
      `for c in Color: score[c]` is portable and is what the README now
      recommends; direct iteration should either agree or be rejected.
- [ ] py2nim zero-initialises a *bare* annotated declaration where Python
      binds nothing. `s: {}int` inside a function is ordinary Python, and
      ordinary Python raises `UnboundLocalError` on the next `s.add(1)`;
      py2py round-trips it unchanged and so does raise, but the Nim backend
      treats it as a declaration and prints `{1}`. py2py is the correct side
      here — `var s: {}int` is the Adascript spelling for a declaration, and
      it works on both — so the fix belongs in py2nim, which should either
      match Python or reject the bare form. Found via `floyd.ady`, which was
      written with the bare form and only worked on Nim.
- [ ] py2py generates annotations whose names are not in scope at import
      time. `Callable` is fixed (the emitter now adds the typing import),
      but a class that names itself -- `def __and__(self, other: Region)`
      inside `class Region` -- is still a NameError, because Python
      evaluates annotations eagerly while Adascript writes them the way Nim
      does, as compile-time types. `from __future__ import annotations` is
      the right answer and is a one-line change, but every expected output
      in `py2py --test` and `test_py2py.py` is a literal string that would
      gain the import line: 43 and 122 cases respectively fail on it. Worth
      doing together with a pass over those fixtures.
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
- [ ] py2nim: `any(xs)` and `all(xs)` over a `[]bool` do not translate. `any`
      hits Nim's deprecated `any` *type* ("illegal type conversion to 'any'")
      and `all` is simply undeclared; both work on the Python backend, so the
      same source gives a working program on one and a compile error on the
      other. `sequtils` has `anyIt`/`allIt` to map onto.
- [ ] py2nim: a value-returning call used as a statement gets `discard` inside
      a plain `def` but not inside a *method body* or at module level, so the
      same source compiles on Python and fails on Nim with "expression ... has
      to be used (or discarded)". The richer logic in `hek_nim_stmt.py` is the
      disabled fallback; the active `stmt_line.to_nim` in `hek_nim_parser.py`
      only discards `pop` and nimpy calls.
- [ ] Nim identifiers ignore case and underscores, so an Adascript class
      `Container` and a constant `CONTAINER` are one name there and two on
      Python. Worth a transpile-time warning: the Nim error names a
      "redefinition" at a line the author did not write.
- [ ] generic function syntax `def foo[T]` (Feature 1)
- [ ] `.map()` / `.and_then()` rewriting on `?T` (Feature 2)

---

## Monad support improvements (high ROI)

### Feature 1 — Generic function syntax `def foo[T]`

Currently there is no way to write type-parametric functions. Implicit generics
(undeclared type names used as parameters) work for simple cases, but callers
cannot write explicit type applications and reusable combinators like `fmap`,
`sequence`, and `traverse` must be duplicated for every concrete type.

**Desired syntax:**
```python
def fmap[T, U](opt: ?T, f: proc(T): U) -> ?U:
    if opt is None: return None
    return f(opt)

def sequence[T](items: []?T) -> ?[]T:
    var out: []T = []
    for x in items:
        if x is None: return None
        out.append(x)
    return out
```

**Implementation sketch:**
- Grammar: extend `func_def` to accept `[TypeParam, ...]` after the name.
- Transpiler: emit `proc foo[T, U](...)` in Nim; add type params to the symbol
  table as unresolved type names for the duration of the function scope.
- Complexity: ~200–300 lines in grammar + `hek_nim_parser.py`.

---

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
