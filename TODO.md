# TODO

- [x] Restore Python 3.10 match/case syntax alongside Adascript case/when (Adascript should be a superset of Python)
- [x] add expect/send command in shell
- [x] py2py: regex flag constants reference `re` but the prelude imports it as `_re_mod` (see [Bug 1](#bug-1--py2py-emits-reignorecase-while-importing-re-as-_re_mod))
- [ ] py2py: implicit return does not reach into `if`/`else` branches (see [Bug 2](#bug-2--py2py-implicit-return-stops-at-ifelse-branches))
- [ ] py2py: `Natural` / `Positive` are emitted into annotations but never defined (see [Bug 3](#bug-3--py2py-emits-natural--positive-without-defining-them))
- [x] py2py: no `to_py()` for `pyimport` / `from … nimport …`, so those files cannot transpile at all (see [Bug 4](#bug-4--py2py-has-no-to_py-for-pyimport--from--nimport))
- [ ] py2py: declarations without an initialiser bind nothing (see [Bug 5](#bug-5--py2py-drops-declarations-that-have-no-initialiser))
- [x] `quit()` clamps exit codes to 127, so wrappers cannot forward a child's 128/129 (see [quit() clamps exit codes](#quit-clamps-exit-codes-to-127--fixed))
- [ ] py2nim: a quoted receiver inside an f-string interpolation is mangled (see [Bug 6](#bug-6--py2nim-mangles-a-quoted-receiver-inside-an-f-string))
- [ ] py2py: assigning a module-level `var` inside a function creates a local (see [Bug 7](#bug-7--py2py-does-not-emit-global-for-module-level-vars))
- [ ] py2py: `stderr.writeLine` / `stdout.write` are emitted untranslated (see [Bug 8](#bug-8--py2py-does-not-translate-the-nim-stream-objects))

## Shell improvements

### `shell:` with terminal passthrough and exit code

Currently `shell:` has two modes: discard (inherits terminal, no exit code)
and capture (`let r = shell:`, captures stdout, returns `.code`). There is no
way to both inherit the terminal *and* get the exit code — scripts that need
this (e.g. running git with a pager, or interactive editors) must use a
`$? > tmpfile` workaround.

**Desired syntax:**
```python
let code: int = shell: git log --oneline    # inherits terminal, returns exit code
```

When the assignment target is a bare `int` (not a record/tuple), emit
`execCmd()` in Nim which inherits stdio and returns the exit code directly.

**Implementation sketch:**
- In `_parse_shell_stmt`, detect when target type is `int` (or infer from
  `shell:` vs `shellLines:`).
- Emit `execCmd(cmd)` instead of `execCmdEx(cmd)` — Nim's `execCmd` inherits
  the terminal and returns the exit code.
- Python backend: `subprocess.call(cmd, shell=True)`.
- Complexity: ~50 lines in `hek_nim_parser.py` + `hek_py3_parser.py`.

---

### `quit()` clamps exit codes to 127 — FIXED

A program that forwards another command's exit status cannot report anything
above 127: `quit(n)` yields 127 for every n >= 128. Codes 0..127 pass through
untouched.

```
requested: 0  1  2  100 126 127 128 129 200 255
actual:    0  1  2  100 126 127 127 127 127 127
```

This is Nim's behaviour, not the transpiler's — the generated code is a plain
`quit(n)`, and the same clamp appears in a hand-written Nim program, while C's
`exit(128)` returns 128.

It bites any wrapper that forwards a child's status. `EXAMPLES/git1.ady` ends
in `quit(g(args))`, so `git1 <file> <git args...>` reports git's 0 and 1
faithfully but turns git's 128 (bad ref, bad usage) and 129 (usage error)
into 127:

```
                                     git1   raw git
  diff --quiet (dirty tree)            1       1
  rev-parse --verify nosuchbranch    127     128
```

`if git1 f rev-parse --verify b; then` still works, since non-zero stays
non-zero; only a script that distinguishes 128 from 1 is affected.

**Fix (in `TO_NIM/hek_nim_expr.py`):** `quit(x)` and `sys.exit(x)` now emit
C's `exit()` whenever the argument is not a literal in 0..127 — a variable, an
expression, or a literal above 127. A literal 0..127 still emits the idiomatic
`quit(n)` and injects nothing.

```nim
proc c_exit(code: cint) {.importc: "exit", header: "<stdlib.h>", noreturn.}
proc adascriptExit*(code: int) {.noreturn.} =
  c_exit(code.cint)
```

The helper is added to `nim_top_decls` on first use only. `exit()` is used
rather than `posix.exitnow()`: both preserve the full 0..255 range, but
`exitnow` is `_exit` and discards buffered output — a program that prints and
then exits 128 would lose the print. Verified: with `exitnow` the output
vanished; with `exit()` it appears and the status is still 128.

The Python backend needed nothing: `sys.exit(128)` already exits 128.

After the fix, `EXAMPLES/git1.ady` forwards git's status faithfully:

```
                                     git1   raw git
  diff --quiet (dirty tree)            1       1
  rev-parse --verify nosuchbranch    128     128
```

---

### Bug 6 — py2nim mangles a quoted receiver inside an f-string

An interpolation whose receiver is a string literal is rewritten across the
f-string boundary, producing Nim that does not parse.

```python
let others: []str = ["exp1", "exp3"]
print f"Delete the branches ({', '.join(others)})?"
```

emits

```nim
", ")})?""".join(fmt"""Delete the branches ({others)
```

— the `'sep'.join(x)` -> `x.join("sep")` rewrite in
`_translate_stdlib_patterns` runs over the whole emitted expression, and
inside an f-string the quotes it matches on are the f-string's own.  Nim
then fails with `invalid indentation` at that line.

The receiver has to be a literal for this to fire: `sep.join(others)` with
`sep` a variable is fine, as is any `.join` outside an f-string.

**Workaround:** hoist the call into a local.

```python
let names: str = ", ".join(others)
print f"Delete the branches ({names})?"
```

`EXAMPLES/git1.ady` does exactly this in `cmd_adopt`, with a comment
pointing here.

**Fix sketch:** the post-pass should not treat the inside of an f-string as
an ordinary expression.  Either convert interpolations before the pattern
pass and mark them done, or run the `.join` rewrite on the interpolation
text only, not on the whole `fmt"..."` string.

---

### Safe shell interpolation (auto-quoting)

`shell:` interpolation with `{var}` embeds the value as raw text into the
command string — no quoting. A variable containing spaces or shell
metacharacters (`my notes.txt`, `hello; rm -rf /`) breaks or is dangerous.
Scripts must manually wrap every interpolated path in a quoting helper:

```python
def Q(s: str) -> str:
    "'" + s.replace("'", "'\\''") + "'"

shell: git add -- {Q(file)}
```

**Desired syntax** — a distinct sigil (e.g. `${var}` or `{!var}`) that
auto-quotes the interpolated value:

```python
shell: git add -- ${file}           # → git add -- 'my notes.txt'
shell: mv -- ${old} ${new}          # each arg single-quoted automatically
```

Plain `{var}` stays as-is (raw interpolation) for cases where the value is
already a command fragment or intentionally unquoted.

**Implementation sketch:**
- Tokenizer: recognise `${name}` inside shell bodies as a distinct token
  (e.g. `SHELL_SAFE_INTERP`).
- Nim backend: emit the value wrapped in `quoteShell()` (Nim's `osproc`
  provides this) or a single-quote-and-escape helper.
- Python backend: `shlex.quote(var)`.
- Complexity: ~100 lines across tokenizer + both backends.

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

## Python backend (py2py) — known bugs

Found while making `EXAMPLES/test_regex.ady` compile on the Nim backend
(bugs 1 and 2), then one at a time while fixing and regression-testing that
work (bugs 3, 4 and 5). The Nim backend handles all five correctly — every
affected example compiles and runs there — so it is the Python output that is
wrong in each case. Only the first is regex-specific: bug 2 affects any
function whose body ends in `if`/`else`, bug 3 any file using `Natural` or
`Positive`, bug 4 any file using `pyimport` or `from … nimport …`, and bug 5
any declaration written without an initialiser.

Bugs 1 and 4 are fixed. Bugs 3 and 5 are what still stop most of `EXAMPLES/`
from running under `py2py`, and they share a shape: a Python annotation that
binds no value. Bugs 7 and 8 are a different pair, found in `git1.ady`: a
scoping rule Python has and Nim does not, and two Nim stream names the
Python backend never maps.

### Bug 1 — py2py emits `re.IGNORECASE` while importing `re` as `_re_mod`

**Fixed.** `_py_re_flags` now spells the constants with the `_re_mod` alias.
Kept here for the record.

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

**Cause:** the flag table in `_py_re_flags` (`TO_PYTHON/hek_py3_expr.py`)
```python
mapping = {'i': 're.IGNORECASE', 'm': 're.MULTILINE', 's': 're.DOTALL'}
```
The rest of the file already used the alias correctly — e.g. the `/g`
find-all path emits `_re_mod.findall(...)`.

**Fix applied:** the three values now read `_re_mod.IGNORECASE` /
`_re_mod.MULTILINE` / `_re_mod.DOTALL`. A sweep for other bare `re.`
emissions in `TO_PYTHON/` found none — the remaining matches are docstrings.
Verified on all three flags across both the match path (`_pymatch(s, pat,
_re_mod.IGNORECASE)`) and the substitution path (`_re_mod.sub(..., flags=…)`).

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

---

### Bug 3 — py2py emits `Natural` / `Positive` without defining them

The Ada-inherited integer subtypes are passed straight through into the
generated annotations, but nothing defines them, so any file using them dies
at import time. Python evaluates annotations on module-level assignments, so
this is a hard failure rather than a cosmetic one. Nim needs no help here —
`Natural` and `Positive` are built-in there, which is why this shows only in
Python output.

**Reproduction:**
```python
var n: Natural = 0
var p: Positive = 1
n += 1
print n, p
```

**Generated Python — nothing declares the two names:**
```python
n: Natural = 0        # NameError: name 'Natural' is not defined
p: Positive = 1
```

This is why `EXAMPLES/awk_example.ady` (`var NR : Natural = 0`) cannot run on
the Python backend, though it compiles and runs on Nim.

**Implementation sketch:**
- Emit `Natural = int` / `Positive = int` into the generated prelude the first
  time either name is used, in the same manner as `_PYMATCH_HELPER`
  (`TO_PYTHON/hek_py3_expr.py:1507`) is injected via `ParserState.py_top_decls`.
- Emitting plain `int` in the annotation instead would also work, but loses the
  documentation value of the subtype name in the generated source.
- Neither spelling gives Python the range checking Nim gets; that is a separate
  question, and the aliases at least make the output run.
- Complexity: ~20 lines, plus a regression test that runs `awk_example.ady`
  through `py2py -c`.

---

### Bug 4 — py2py has no `to_py()` for `pyimport` / `from … nimport …`

**Fixed.** The three missing `to_py` methods are in place; see the note at the
end of this entry. Kept here for the record.

Three of the four import forms are implemented only in the Nim backend, so a
file using any of them cannot be transpiled to Python at all — the run aborts
before producing output, rather than emitting a wrong line.

| Form | `to_py()` | `to_nim()` |
|---|---|---|
| `nimport X` | yes | yes |
| `from X import Y` | yes (plain Python) | yes |
| `pyimport X` | **missing** | yes |
| `from X nimport Y` (`from_nim_abs`) | **missing** | yes |
| `from X pyimport Y` (`from_pyimport`) | **missing** | yes |

**Reproduction:**
```python
from stdlib nimport PriorityQueue
print "ok"
```
```
TypeError: to_py() takes 1 positional argument but 2 were given
```

**Cause:** the grammar rules `pyimport_stmt`, `from_nim_abs` and
`from_pyimport` (`ADASCRIPT_GRAMMAR/py3stmt.py`, lines ~251–257) have a
`@method(...) to_nim` in `TO_NIM/hek_nim_stmt.py` but no matching `to_py` in
`TO_PYTHON/`. `py2py.py:247` calls `stmt.to_py(0)`, gets a `TypeError` because no
method is attached, falls back to `stmt.to_py()`, and that walks into a bare
`Sequence_Parser` — so the failure surfaces as a confusing arity error rather
than "unimplemented".

**Blocks:** `dijkstra.ady` (`from stdlib nimport PriorityQueue`),
`primes.ady`, `tsp.ady` and `rsync_time_machine.ady` (all `pyimport`). All
four compile and run on the Nim backend.

**Implementation sketch:**
- Add three `to_py` methods in `TO_PYTHON/hek_py3_stmt.py`, next to the
  existing `nimport_stmt` one, which is the model to copy:
  - `pyimport X` → `import X` (Python-only import, so it is emitted in full)
  - `from X pyimport Y` → `from X import Y`
  - `from X nimport Y` → `# from X nimport Y` (Nim-only, comment it out as
    `nimport_stmt` already does)
- Consider making the `except TypeError` fallback in `py2py.py:248` re-raise
  with the rule name when no `to_py` exists; the current arity error hides
  which construct is unimplemented and cost real time to track down twice.
- Complexity: ~30 lines, plus a `py2py -c` run of `dijkstra.ady` as the test.

**Fix applied:** the three methods were added to `TO_PYTHON/hek_py3_stmt.py`,
with the bodies of `import_stmt` and `from_abs` factored into
`_import_as_list_to_py` and `_from_import_parts` so each form renders the
shared parse. `pyimport X` → `import X`, `from X pyimport Y` →
`from X import Y`, `from X nimport Y` → `# from X nimport Y`. Verified over
aliases (`pyimport numpy as np`), multi-module lists (`pyimport os, time`)
and dotted sources (`from a.b.c nimport X, Y`); `dijkstra.ady`, `primes.ady`,
`tsp.ady` and `rsync_time_machine.ady` all transpile now.

Transpiling is not yet running: `primes.ady` then hits bug 3, and
`dijkstra.ady` hits bug 5 below. The suggested `py2py.py` error-reporting
improvement was **not** done and is still worth doing.

---

### Bug 5 — py2py drops declarations that have no initialiser

`var x: T` with no value emits a bare annotation in Python, which binds
nothing, so the first use raises `UnboundLocalError` (or `NameError` at module
level). Nim zero-initialises such a declaration, which is why the same source
works there. Adascript documents the form as valid: "Declarations without an
initial value are valid (Nim zero-initialises)".

**Reproduction:**
```python
def f() -> int:
    var seen: {}str
    seen.add("x")
    return len(seen)
print f()
```

**Generated Python — `seen` is annotated but never bound:**
```python
def f() -> int:
    seen: set[str]
    seen.add("x")          # UnboundLocalError: cannot access local variable 'seen'
    return len(seen)
```

**Generated Nim — zero-initialised, so it works:**
```nim
proc f(): int =
    var seen: HashSet[string]
    seen.incl("x")
    return len(seen)
```

This is what `dijkstra.ady` (`visited : {}Node_T`) hits once bug 4 is out of
the way. It is the same family as bug 3 — a Python annotation that binds no
value — but a different cause and a different fix.

**Implementation sketch:**
- When a `var`/`let`/`const` declaration has no initialiser, emit an
  explicit empty value for the annotated type rather than a bare annotation:
  `set[str]` → `set()`, `list[T]` → `[]`, `dict[K,V]` → `{}`, `str` → `""`,
  `int` → `0`, `float` → `0.0`, `bool` → `False`.
- The type is already known — it is what the annotation is built from — so
  this is a lookup keyed on the same information the annotation printer uses.
- For a class or `?T`, `None` is the honest default.
- Complexity: ~40 lines, next to the annotated-assignment handling in
  `TO_PYTHON/hek_py3_stmt.py`; `dijkstra.ady` under `py2py -c` is the test.

---

### Bug 7 — py2py does not emit `global` for module-level `var`s

A function that assigns a module-level `var` compiles to a plain assignment,
which in Python creates a *local*.  The global keeps its old value, silently.
Nim has no such rule, so the same source is correct there.

**Reproduction:**
```python
var counter: int = 0

def bump():
    counter = 1

bump()
print counter
```

**Generated Python — `bump` writes a local, `counter` stays 0:**
```python
counter: int = 0

def bump():
    counter = 1      # local; the module-level counter is untouched

bump()
print(counter)       # prints 0
```

```
py2py -c  ->  0
py2nim -r ->  1      <- correct
```

No error is raised, which makes this the worst of the py2py bugs to debug:
the program runs and quietly does the wrong thing.

This is what stops `EXAMPLES/git1.ady` running on the Python backend.  It
keeps its state in three module-level `var`s set by `split_target()` --
`G1_DIR`, `G1_BASE`, `G1_GITDIR`, a shape inherited from the bash original --
so on Python they stay `""` and every subcommand fails on an empty path
(`git1: no such directory: `).  `--version`, which touches none of them, is
the only thing that works.

**Implementation sketch:**
- Track which names are bound at module level (they already reach the symbol
  table as globals).
- When emitting a function body, collect the module-level names it assigns to
  -- assignment, augmented assignment, `for` target, `with ... as` -- and emit
  `global a, b, c` as the first statement of the body.
- A name only read, never assigned, needs nothing.
- Nested functions need `nonlocal` for the same reason; the same pass covers
  both if it walks scopes rather than just module/function.
- Complexity: ~40 lines in `hek_py3_stmt.py`, at the funcdef emitter.

---

### Bug 8 — py2py does not translate the Nim stream objects

`stderr.writeLine(...)`, `stdout.write(...)` and `stdout.flushFile()` are
emitted verbatim, so the Python output raises `NameError` on the first call.
They are Nim names; the Python backend has to map them onto `sys.stderr` and
`sys.stdout`.

**Reproduction:**
```python
def warn(msg: str):
    stderr.writeLine(msg)

warn("careful")
stdout.write("prompt: ")
stdout.flushFile()
print "done"
```

**Generated Python — unchanged, and undefined:**
```python
def warn(msg: str):
    stderr.writeLine(msg)    # NameError: name 'stderr' is not defined
```

**Generated Nim — works:**
```
careful
prompt: done
```

Together with bug 7 this is the second thing keeping `EXAMPLES/git1.ady` off
the Python backend: `die()` and `warn()` are the program's error path, and
`confirm()` writes its prompt through `stdout.write` + `stdout.flushFile`.

**Implementation sketch:**
- Map at the call site, the way `_PY_MODULE_FUNC_TO_NIM` does in the other
  direction:
  - `stderr.writeLine(x)` -> `print(x, file=_sys.stderr)`
  - `stdout.writeLine(x)` -> `print(x)`
  - `stderr.write(x)` / `stdout.write(x)` -> `_sys.stderr.write(x)` /
    `_sys.stdout.write(x)`
  - `stdout.flushFile()` / `stderr.flushFile()` -> `.flush()`
- The prelude already imports `sys`, so no new import is needed.
- Complexity: ~25 lines in `hek_py3_expr.py`, plus a test per form.
