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
