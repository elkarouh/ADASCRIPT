# TODO

- [x] Restore Python 3.10 match/case syntax alongside Adascript case/when (Adascript should be a superset of Python)
- [x] add expect/send command in shell
- [ ] py2py: regex flag constants reference `re` but the prelude imports it as `_re_mod` (see [Bug 1](#bug-1--py2py-emits-reignorecase-while-importing-re-as-_re_mod))
- [ ] py2py: implicit return does not reach into `if`/`else` branches (see [Bug 2](#bug-2--py2py-implicit-return-stops-at-ifelse-branches))

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

## Python backend (py2py) — known bugs

Both were found while making `EXAMPLES/test_regex.ady` compile on the Nim
backend. The Nim backend handles both correctly, so `test_regex.ady` runs
there; it is the Python output that is wrong. Neither is specific to regex
code — the second affects any function whose body ends in `if`/`else`.

### Bug 1 — py2py emits `re.IGNORECASE` while importing `re` as `_re_mod`

A regex literal carrying a flag (`/pat/i`, `/pat/m`, `/pat/s`) generates a
reference to the bare module name `re`, but the injected prelude imports the
module under an alias, so the generated file raises `NameError` on the first
call.

**Reproduction:**
```python
def is_yes(s: str) -> bool:
    s == /^yes$/i
print is_yes("YES")
```

**Generated Python (abridged) — note the two spellings:**
```python
import re as _re_mod                                  # prelude
...
    return _pymatch(s, r'^yes$', re.IGNORECASE)       # NameError: name 're' is not defined
```

**Cause:** `TO_PYTHON/hek_py3_expr.py:1548`
```python
mapping = {'i': 're.IGNORECASE', 'm': 're.MULTILINE', 's': 're.DOTALL'}
```
The rest of the file already uses the alias correctly — e.g. the `/g`
find-all path emits `_re_mod.findall(...)` at `hek_py3_expr.py:899`.

**Implementation sketch:**
- Change the three values to `_re_mod.IGNORECASE` / `_re_mod.MULTILINE` /
  `_re_mod.DOTALL`.
- Grep for other bare `re.` emissions in `TO_PYTHON/` before closing this out.
- Complexity: one line, plus a regression test with a flagged literal.

---

### Bug 2 — py2py implicit return stops at `if`/`else` branches

Implicit return works when the last statement of a function is a bare
expression, but not when it is an `if`/`else` whose branches end in bare
expressions. Each branch is emitted as an expression statement, so the
function falls off the end and returns `None`.

**Reproduction:**
```python
def first_word(s: str) -> str:
    if s == /(\w+)/:
        $+1
    else:
        ""
print first_word("hello world")          # prints None; expected "hello"
```

**Generated Python — the branch values are discarded:**
```python
def first_word(s: str) -> str:
    if _pymatch(s, r'(\w+)'):
        matches[1]
    else:
        ""
```

Working case for contrast — a bare last expression is promoted correctly:
```python
def add(a: int, b: int) -> int:
    a + b                                 # -> return a + b, prints 5
```

**Implementation sketch:**
- The promotion lives in `TO_PYTHON/hek_py3_parser.py` (see the
  "Implicit return: if last statement is a bare expression" comments at
  lines 1095 and 1178). It inspects only the final statement.
- Make it recursive: when the final statement is an `if`/`elif`/`else` chain,
  a `case`/`when`, or a `match`/`case`, promote the last bare expression of
  every branch instead of the statement as a whole. Leave a branch alone if
  it already ends in `return`, `raise`, `break` or `continue`.
- The Nim backend needs no such pass — Nim takes the last expression of each
  branch as the block's value — which is why this only shows up in Python
  output. `EXAMPLES/test_regex.ady` (`first_word`, `parse_kv`, `parse_date`,
  `first_number`) is the natural test case.
- Complexity: ~50–100 lines in `hek_py3_parser.py`.
