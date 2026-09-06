# TODO

- [x] Restore Python 3.10 match/case syntax alongside Adascript case/when (Adascript should be a superset of Python)
- [x] add expect/send command in shell
- [x] py2py: regex flag constants reference `re` but the prelude imports it as `_re_mod` (see [Bug 1](#bug-1--py2py-emits-reignorecase-while-importing-re-as-_re_mod))
- [x] py2py: implicit return does not reach into `if`/`else` branches (see [Bug 2](#bug-2--py2py-implicit-return-stops-at-ifelse-branches))
- [x] py2py: `Natural` / `Positive` are emitted into annotations but never defined (see [Bug 3](#bug-3--py2py-emits-natural--positive-without-defining-them))
- [x] py2py: no `to_py()` for `pyimport` / `from … nimport …`, so those files cannot transpile at all (see [Bug 4](#bug-4--py2py-has-no-to_py-for-pyimport--from--nimport))
- [x] py2py: declarations without an initialiser bind nothing (see [Bug 5](#bug-5--py2py-drops-declarations-that-have-no-initialiser))
- [x] `quit()` clamps exit codes to 127, so wrappers cannot forward a child's 128/129 (see [quit() clamps exit codes](#quit-clamps-exit-codes-to-127--fixed))
- [x] py2nim: a quoted receiver inside an f-string interpolation is mangled (see [Bug 6](#bug-6--py2nim-mangles-a-quoted-receiver-inside-an-f-string))
- [x] py2py: assigning a module-level `var` inside a function creates a local (see [Bug 7](#bug-7--py2py-does-not-emit-global-for-module-level-vars))
- [x] py2py: `stderr.writeLine` / `stdout.write` are emitted untranslated (see [Bug 8](#bug-8--py2py-does-not-translate-the-nim-stream-objects))
- [x] py2py: `os.makedirs` / `os.mkdir` raise where Nim's `createDir` does not (see [Bug 9](#bug-9--py2py-emits-directory-creation-that-is-not-idempotent))
- [x] py2py: `readFile` / `writeFile` are emitted verbatim and undefined (see [Bug 10](#bug-10--py2py-does-not-translate-readfile--writefile))
- [x] py2py: implicit return of a multi-line string writes `return` inside the literal (see [Bug 11](#bug-11--py2py-implicit-return-breaks-a-multi-line-string))
- [x] both backends re-indent the inside of a multi-line string, changing its value (see [Bug 12](#bug-12--a-multi-line-string-is-re-indented-changing-its-value))
- [x] `shell:` could not both inherit the terminal and return an exit code (see [shell: with terminal passthrough](#shell-with-terminal-passthrough-and-exit-code--done))
- [x] `shell:` interpolation did not quote, so every path needed a helper (see [Safe shell interpolation](#safe-shell-interpolation-auto-quoting--done))
- [x] shell tuple capture: the slots mean different things on each backend (see [Bug 13](#bug-13--shell-tuple-capture-slots-disagree-between-backends))
- [x] `r.stderr` is documented, works on Python, and does not exist on Nim (see [Bug 14](#bug-14--rstderr-does-not-exist-on-the-nim-backend))
- [x] `shellLines` yields one more element on Nim than on Python (see [Bug 15](#bug-15--shelllines-differs-by-a-trailing-empty-element))
- [x] `shell(timeout = ms)` is silently ignored on Nim (see [Bug 16](#bug-16--shelltimeout--ms-is-ignored-on-nim))
- [x] `shell:` had no way to interpolate an argument *list* (see [Splat interpolation](#splat-interpolation-args--done))
- [x] `shell:` had no way to fail on a non-zero status (see [Checked form](#checked-form-check--true--done))
- [x] `shell:` had no way to feed a command's stdin (see [stdin feeding](#stdin-feeding-stdin--expr--done))
- [x] `shell:` had no way to set a child's environment (see [env mapping](#env-mapping-env--expr--done))
- [x] `shell:` buffered every command to completion (see [Streaming form](#streaming-form-shelliter--done))
- [x] py2nim: `shell(cwd = expr)` splices the variable's name (see [Bug 18](#bug-18--py2nim-splices-a-non-literal-cwd-as-text))
- [x] py2py: a shell body ending in `"` collides with the `"""` wrapper (see [Bug 17](#bug-17--py2py-mis-quotes-a-shell-body-ending-in-a-double-quote))
- [x] py2nim: the cache did not watch TO_PYTHON, so a stale `.nim` was reused (see [Bug 19](#bug-19--py2nims-cache-does-not-watch-to_python))
- [x] `shell:` had no way to hand the process over (see [Exec form](#exec-form-shellexec--done))
- [x] an unknown or inapplicable shell option was silently ignored (see [Bug 20](#bug-20--an-unknown-or-inapplicable-shell-option-is-silently-ignored))
- [x] `shellIter` accepted options and discarded all of them (see [Bug 21](#bug-21--shelliter-accepted-options-and-discarded-all-of-them))
- [x] py2py: a call spanning lines skips every name-anchored rewrite (see [Bug 22](#bug-22--a-call-spanning-lines-skips-every-name-anchored-rewrite-python-backend))
- [ ] py2py: tick attributes are dropped in a call spanning lines — same root cause as Bug 22, still open
- [x] every command went through `/bin/sh`, so quoting was always the caller's problem (see [Argv form](#argv-form-run--runlines--done))
- [x] every shell form waited, so N commands took the sum of their times (see [Concurrency form](#concurrency-form-shellspawn--done))
- [x] a pipeline's failure vanished, a block could only join with `&&`, and asking whether a program exists cost a process (see [pipefail, join and have()](#pipefail-block-join-and-have--done))
- [x] `shellIter` had no exit status, so a stream that died looked like one that ended (see [shellIter check](#shelliterchecktrue--done))
- [ ] streaming stdin — deliberately not built; the deadlock case is already handled (see [Streaming stdin](#streaming-stdin--not-done-and-here-is-why))

## Shell improvements

### `shell:` with terminal passthrough and exit code — DONE

`shell:` had two modes: discard (inherits the terminal, no exit code) and
capture (`let r = shell:`, captures stdout, returns `.code`). There was no
way to both inherit the terminal *and* get the exit code, so scripts that
needed it wrote the status to a temp file and read it back.

**Syntax:** an `int`-typed target.

```python
let code: int = shell: git log --oneline    # inherits terminal, returns exit code
```

`_parse_shell_stmt()` now reports the target's primitive annotation, and the
backends act on `int`:

| Backend | Emitted |
|---|---|
| Nim | `let code = execCmd(cmd)` — inherits stdin/stdout/stderr |
| Python | `code = subprocess.call(cmd, shell=True)` — no capture kwargs |

Anything else is unchanged: `let r = shell:` still captures into
`(output, code)`, `shellLines:` still splits stdout, and a bare `shell:`
still discards.

`EXAMPLES/git1.ady` was the motivating case and loses its whole workaround —
`sh_status()` and the `/tmp/.git1-status` constant, 13 lines — and with them
a bug nobody had hit yet: that path was fixed, so two git1 processes running
at once could read each other's exit status. `g()` now ends

```python
    let code: int = shell: cd {!G1_DIR} && GIT_DIR={!G1_GITDIR} GIT_WORK_TREE=. git {*args}
    code
```

and `cmd_help` asks `let is_tty: int = shell: test -t 1` directly.

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

An f-string containing `'sep'.join(x)`, **passed as an argument to a call**,
is rewritten across the f-string boundary and produces Nim that does not
parse.

```python
let others: []str = ["exp1", "exp3"]
print ask(f"Delete ({', '.join(others)})?")
```

emits

```nim
", ")})?""".join(ask(fmt"""Delete ({others)
```

and Nim fails with `invalid indentation` at that line.

The `'sep'.join(x)` -> `x.join("sep")` rewrite in
`_translate_stdlib_patterns` matches `^(.+)\.join\((.+)\)$` against the
whole enclosing expression.  With the f-string inside a call there is a
`.join(` to the right of the call's opening paren, so the greedy receiver
swallows `ask(fmt"""Delete ({', '` and the rewrite reassembles the pieces in
the wrong order.

**It fires only in that shape.**  Verified:

| Form | Result |
|---|---|
| `print f"... ({', '.join(x)}) ..."` | correct -- `others.join(", ")` |
| `let s: str = f"... ({', '.join(x)}) ..."` | correct |
| `print ask(f"... ({', '.join(x)}) ...")` | **mangled** |
| `v = ask(f"... ({', '.join(x)}) ...")` | **mangled** |

A receiver that is a variable (`sep.join(x)`) is fine in every form, since
the rule needs the quotes.

**Fixed.** `_is_join_receiver()` gates the rule: it rewrites only when the
receiver is a quoted literal holding no quote of its own, or a bare
identifier (dotted names included).  `ask(fmt"""Delete ({', '` is neither,
so the rule declines and the interpolation is converted on its own, as it
already was when the f-string stood outside a call.

`EXAMPLES/git1.ady` no longer hoists the join out of the prompt in
`cmd_adopt`.

---

### Safe shell interpolation (auto-quoting) — DONE

`shell:` interpolation with `{var}` embeds the value as raw text — no
quoting — so a value holding spaces or shell metacharacters
(`my notes.txt`, `a; rm -rf /`) broke the command or ran part of it. Every
script had to wrap each interpolated path in a helper of its own.

**Syntax:** `{!expr}` interpolates quoted; `{expr}` still interpolates raw.

```python
let f: str = "my notes.txt"
shell: ls -l {!f}              # ls -l 'my notes.txt'
shell: ls -l {f}               # ls -l my notes.txt   -- two arguments
```

`_apply_shell_quoting()` rewrites `{!expr}` into `{quoteShell(expr)}` for
Nim and `{_shlex.quote(expr)}` for Python before either backend builds the
command, so the existing interpolation and hoisting machinery handles it
from there. Escaped braces (`{{`, `}}`) are left alone, and the scan matches
nested braces, so `{!os.path.join(a, b)}` works.

**Not `${var}`**, which the original sketch proposed: `$` reaches the shell
untouched inside a `shell:` body, so `${PATH}` is shell parameter expansion
and `${file}` would have been indistinguishable from it — to a reader and to
the tokenizer both. `{` is already the interpolation sigil, and `!` carries
no meaning after it.

`EXAMPLES/git1.ady` converted 26 interpolations and no longer needs `Q()`
anywhere a shell body appears. It keeps `Q` for one job the sigil cannot do:
`g()` and `g_lines()` join a *list* of arguments into one command fragment,
and a fragment has to be interpolated raw — `{!cmd}` would quote the whole
line into a single word.

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
print first_word("hello world")          # printed None; expected "hello"
```

**Fixed**, together with bug 11, by marking instead of rewriting.
`_mark_implicit_returns()` records the statements that carry the function's
value -- for an `if` in tail position, each branch's own last statement, and
recursively for nested branches and `elif` chains -- and `stmt_line.to_py()`
renders those with the keyword in front.

Verified across nested `if`, an `elif` chain, a function that already
returns explicitly, one with no return annotation, and a `-> None` one; the
values match the Nim build.

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

**Fixed.** The `type_name` emitter calls `_ensure_subtype_aliases()` when an
annotation names either subtype, injecting into `ParserState.py_top_decls`:

```python
Natural = int
Positive = int
```

The annotation keeps the subtype name, for what it tells the reader. A file
that names neither gets nothing. Python still has no range checking --
`Natural` accepts -1 there while Nim rejects it -- which is a separate
question; the alias is what makes the output run at all.

`EXAMPLES/awk_example.ady` (`var NR : Natural = 0`) now runs under
`py2py -c`, which was the test named here.

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

It is the same family as bug 3 — a Python annotation that binds no value —
but a different cause and a different fix.

**Fixed** for the declaration form. `_zero_value()` gives a
`var`/`let`/`const` without an initialiser the empty value of its type:
`int` → `0`, `float` → `0.0`, `bool` → `False`, `str` → `""`, `list[T]` →
`[]`, `dict[K,V]` → `{}`, `set[T]` → `set()`, and `None` for a class or an
optional, where there is no honest zero.

Two deliberate exceptions:

- **The bare `x : T` form is left alone.** It is also ordinary Python, which
  py2py round-trips unchanged — `test_py2py.py` has a case ("annotated no
  value") that pins `x: int` → `x: int`. Write `var x: T` to mean an
  Adascript declaration.
- **A class-level field gets no *mutable* zero.** At class scope that object
  would be shared by every instance, which is worse than the
  `AttributeError` it replaces; scalars, which cannot be mutated in place,
  still get theirs. `CLASS_BODY_DEPTH` tracks this, set by `class_def` and
  cleared by `func_def`, since a method body is an ordinary scope.

`dijkstra.ady` is **not** the test for this after all: it uses the bare form
(`visited : {}Node_T`), and even spelled as a declaration it cannot run
under `py2py` because `PriorityQueue` from `nimport stdlib` has no Python
implementation — `queue.push(...)` finds a plain list.

---

### Bug 7 — py2py does not emit `global` for module-level `var`s

**Fixed.** Kept here for the record.

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

**Fix:** `register_module_globals()` runs over the top-level statements in
`translate()` before anything is emitted -- a function may assign a name
declared below it -- and records what the module binds. The `func_def`
emitter then walks its own body for assignments (plain, augmented, and `for`
targets), subtracts what the body declares local (`var`/`let`/`const`, an
annotated assignment, `own`) and what the parameters bind, and emits
`global a, b, c` for what is left. It goes after a docstring, not before,
so the docstring stays one.

A nested def is not descended into: it is emitted in turn and gets its own
declaration, which is what Python wants -- `global` in the outer function
does not reach it.

`nonlocal` is not handled: a nested function assigning an enclosing
function's local still binds a local of its own. Same shape, one scope in.

---

### Bug 8 — py2py does not translate the Nim stream objects

**Fixed.** Kept here for the record.

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

**Fix:** `_translate_stream_call()` in `hek_py3_expr.py`, applied at the end
of the `primary` emitter when the atom is one of the three stream names:

| Adascript | Python |
|---|---|
| `stderr.writeLine(x)` | `print(x, file=sys.stderr)` |
| `stdout.writeLine(x)` | `print(x)` |
| `stderr.write(x)` / `stdout.write(x)` | `sys.stderr.write(x)` / `sys.stdout.write(x)` |
| `stderr.flushFile()` / `stdout.flushFile()` | `sys.stderr.flush()` / `sys.stdout.flush()` |
| `stdin.readLine()` | `input()` |

`import sys` is requested only when one of these fires, so a file that uses
no stream is unchanged. The rewrite is anchored on the whole emitted
expression and gated on the atom, so `obj.stdout.write(...)` is left alone.

---

### Bug 9 — py2py emits directory creation that is not idempotent

Adascript's `os.makedirs(d)` and `os.mkdir(d)` both map to Nim's `createDir`,
which creates the whole path and, in Nim's own words, "does **not** fail if
the directory already exists because for most usages this does not indicate
an error".  Python's raise `FileExistsError`, and `os.mkdir` does not create
intermediate directories either.  The same source therefore behaves
differently on the two backends.

**Reproduction:**
```python
nimport os

os.makedirs("/tmp/demo/deep/nested")
os.makedirs("/tmp/demo/deep/nested")
os.mkdir("/tmp/demo/second")
os.mkdir("/tmp/demo/second")
print "created twice, no error"
```

```
py2nim -r ->  created twice, no error
py2py  -c ->  FileExistsError: [Errno 17] File exists: '/tmp/demo/deep/nested'
```

This is what `EXAMPLES/git1.ady` hits in `write_exclude()` once bugs 7 and 8
are out of the way.

**Fix:** `_translate_dir_call()` in `hek_py3_expr.py`, applied at the end of
the `primary` emitter when the atom is `os`, rewrites both spellings to
`os.makedirs(..., exist_ok=True)` -- recursive and idempotent, matching
`createDir`.  A call that already passes `exist_ok` is left alone, and the
rewrite requests `import os`, since the emitted call needs the module even
where the source said `nimport os` and meant it for the Nim side only.

---

### Bug 10 — py2py does not translate `readFile` / `writeFile`

The two whole-file builtins are Nim names, emitted verbatim, so the generated
Python raises `NameError` on the first call.  Five examples use them:
`git1.ady`, `spell.ady`, `lispy.ady`, `fsel.ady` and `timetable_server.ady`.

**Reproduction:**
```python
writeFile("/tmp/demo.txt", "alpha\nbeta\n")
print readFile("/tmp/demo.txt").strip()
```

```
py2nim -r ->  beta
py2py  -c ->  NameError: name 'writeFile' is not defined
```

**Fix:** `_file_helper_call()` in `hek_py3_expr.py` rewrites them onto a pair
of helpers injected into `py_top_decls` on first use:

```python
def _read_file(_path):
    with open(_path, encoding="utf-8", errors="surrogateescape") as _f:
        return _f.read()

def _write_file(_path, _text):
    with open(_path, "w", encoding="utf-8", errors="surrogateescape") as _f:
        _f.write(_text)
```

`surrogateescape` because Nim strings hold bytes: it lets the Python side
read and rewrite a file it cannot decode, rather than raising where Nim
would not.  The rewrite happens as the call trailer is consumed rather than
on the finished expression, so `readFile(p).strip()` -- which `git1.ady`
uses -- is rewritten too.

### Bug 11 — py2py implicit return breaks a multi-line string

The implicit-return pass prepended `return ` to the last *line* of the
emitted body rather than to the last statement.  When the trailing
expression was a multi-line string literal, the keyword landed inside the
literal and the function returned None.

**Reproduction:**
```python
def usage() -> str:
    """first line
second line"""

print usage()                 # printed None
```

**Fixed.** The pass now marks statement nodes before the body is rendered,
and `stmt_line.to_py()` puts `return ` in front of the whole statement, so a
multi-line literal stays intact:

```python
def usage() -> str:
    return """first line
    second line"""
```

That also settles the second half of the problem: a body that is only a
string literal would otherwise be read by Python as a docstring, and the
function would return None with nothing to give back.  `git1 help` prints
its text on the Python backend now.

The marks are held by `id()` in `RETURN_NODES` and cleared per module by
`_py_reset()`, since the allocator reuses an id once a parse tree is
collected.

See bug 12 for the re-indentation this exposed.

---

### Bug 12 — a multi-line string is re-indented, changing its value

Both backends pushed the continuation lines of a multi-line string literal
out to the statement's indent, so the string a program produced was not the
string its source contained.

**Reproduction:**
```python
def f():
    s = """line one
line two"""
    return s
```

Every line after the first came back indented to match the statement, and
on the Nim side `lstrip()`ped first, so relative indentation inside the
literal was flattened too.  `git1 help` showed it: every line of the help
text was indented four spaces on the Nim build and, once bug 11 was fixed,
not on the Python one.

**Fixed on both sides**, in the two places that indent a rendered statement:

- `TO_PYTHON/hek_py3_parser.py` (the `block` emitter and `_suite_to_py`)
  indented every line of a multi-line statement.  It now indents the first
  line and leaves the rest, which is what the single-line path already did
  by concatenation.
- `TO_NIM/hek_nim_parser.py` (the `statement` emitter) re-applied the indent
  to every continuation line, which generated code does need -- a `##`
  docstring is one comment per line, and a subrange range-check is emitted
  as a following statement.  It now tracks whether a line falls inside a
  triple-quoted literal and leaves those alone.

The narrower rule matters: excluding *every* non-comment block instead broke
`test_shortest_path.ady`, whose generated `assert` guards are continuation
lines that must be indented.

`git1 help` is now byte-identical on the two backends, and matches the
layout written in `usage()`.

---

### Bug 13 — shell tuple capture slots disagree between backends

The same tuple means different things depending on the backend, with no
error either way.

**Reproduction:**
```python
let (o, c) = shell: sh -c 'echo hi; exit 7'
print "second slot:", c
```

```
Nim    ->  7          (the exit code)
Python ->             (stderr, empty)
```

Nim fills the slots `(stdout, code, "")`; Python fills them
`(stdout, stderr, returncode)`.  With three variables it is worse — on Nim
the code lands in the second name and the third is a bare `""` — and it only
shows up at all if the third variable is used somewhere that type-checks.

`README.md` documents Nim's order: `let (out, code) = shell: cmd`.

**Fixed.** Both backends fill the slots `(stdout, code, stderr)`. Slot 1 is
the exit code — the order README documents and Nim always used — and slot 2
became real stderr once bug 14 gave Nim a separate stream.

Python was the outlier, not the documentation: every tuple capture in
`EXAMPLES/` reads as `(out, code)` — `(env_out, env_rc)`,
`(selection, sel_code)`, `(comment_line, _)` — so the corpus expected the
Nim order too, and those on the Python backend were quietly getting stderr
where they asked for a status.

Verified: both backends now give `7` for the second slot of
`let (o, c) = shell: sh -c 'echo hi; exit 7'`, agree on the three-slot form,
and still skip `_` slots.

---

### Bug 14 — `r.stderr` does not exist on the Nim backend

The record form is documented as carrying `.output`, `.stderr` and `.code`,
and does on Python.  On Nim the field is simply absent:

```python
let r = shell: sh -c 'echo out; echo err >&2'
print r.stderr        # Nim: Error: undeclared field: 'stderr'
```

The Nim emitter builds `(output: tmp[0], code: tmp[1])` — two fields — and
`execCmdEx` merges the child's stderr into its stdout anyway, so there was
never a separate stream to expose.

**Fixed**, and properly rather than with an empty placeholder.
`adascriptRun()`, injected on first use, replaces `execCmdEx` for every
capture form: `startProcess` with both pipes set non-blocking, drained in a
loop as the child runs, so a child that fills one buffer cannot block the
other. Confirmed against 1.3 MB of stderr alongside stdout.

`r.stderr` now returns the same text on both backends, and two more things
follow from real separation:

- `shellLines:` no longer carries stderr lines. `execCmdEx` merged them, so
  `shellLines: sh -c 'echo good; echo noise >&2'` gave two lines on Nim and
  one on Python.
- The tuple's third slot means something: `(out, code, err)` (bug 13).

---

### Bug 15 — `shellLines` differs by a trailing empty element

```python
let ls = shellLines: printf 'a\nb\n'
print ls'Length          # Nim: 3    Python: 2
```

Nim's `splitLines` keeps the empty string after a trailing newline; Python's
`splitlines` drops it.  Command output almost always ends in a newline, so
almost every `shellLines` result is one longer on Nim, and any `'Length`,
index or loop over it disagrees between the backends.

**Fixed.** `adascriptShellLines()`, injected into `nim_top_decls` on first
use, splits and then drops a single trailing empty element — matching both
Python and what the caller means by "the lines this command printed".

Verified against the edges too: no output gives 0 lines on both backends,
output with no trailing newline gives 1, and a blank line *in the middle* is
kept.

---

### Bug 16 — `shell(timeout = ms)` is ignored on Nim

```python
let r = shell(timeout = 500): sleep 3; echo finished
```

Python raises `TimeoutExpired` after half a second.  Nim runs the command to
completion — the emitter appends `# timeout: 500ms (execCmdEx has no
timeout)` and carries on, so the option reads as supported and does nothing.

**Fixed**, together with bug 14 as expected. `adascriptRun()` takes the
timeout and kills the child when the deadline passes; `adascriptExec()` does
the same for the forms that keep the terminal (a bare `shell:` and an
`int`-typed target), since those cannot go through the capturing runner.

A killed command reports **124**, as `timeout(1)` does. Python raised
`TimeoutExpired`, which Nim has no equivalent for and Adascript cannot
catch, so `_run_shell()` there returns 124 as well. Verified:
`shell(timeout = 400): sleep 3` gives code 124 and empty output on both
backends, for the capture form and the int-typed one.

---

### Splat interpolation `{*args}` — DONE

`{!x}` quotes one value, but an argument *list* had no spelling: a script
had to loop, quote each element itself and join them, then interpolate the
result raw.  `EXAMPLES/git1.ady` carried exactly that — a `Q()` helper and a
four-line loop in each of `g()` and `g_lines()`.

**Syntax:** `{*xs}` quotes each element and joins them with spaces.

```python
let args: []str = ["commit", "-m", "two words; and a semicolon"]
shell: git {*args}          # git commit -m 'two words; and a semicolon'
```

| Backend | Emitted |
|---|---|
| Nim | `mapIt(xs, quoteShell(it)).join(" ")` |
| Python | `' '.join(_shlex.quote(_a) for _a in xs)` |

`_apply_shell_quoting()` handles both sigils in one scan.  An empty list
interpolates to nothing, which is what an absent argument vector should do.

`git1.ady` now has **no shell plumbing at all** — `Q()` and both loops are
gone, and `g()` is two lines:

```python
    let code: int = shell: cd {!G1_DIR} && GIT_DIR={!G1_GITDIR} GIT_WORK_TREE=. git {*args}
    code
```

---

### Bug 17 — py2py mis-quotes a shell body ending in a double quote

A `shell:` body is wrapped in `"""..."""`, so a body whose last character is
`"` produces four quotes in a row and the generated Python does not parse.

**Reproduction:**
```python
shell: echo "end"
```

```python
_subprocess.run("""echo "end"""", shell=True)
#                                ^ SyntaxError: unterminated string literal
```

Predates the quoting sigils — it reproduces with them stashed — and the Nim
backend already guards against it: `_quote()` there switches to an escaped
single-quoted form when the body would collide with its delimiter.

**Fixed.** `_py_shell_literal()` gives the Python emitter the same guard:
when the body ends with `"` or contains `"""`, it emits a `"`-delimited
literal with backslashes and quotes escaped, keeping the `f` prefix where
interpolation is needed.

```python
_subprocess.run("echo \"end\"", shell=True)
```

Checked across every shell form — bare, capture, `shellLines:`, and with
interpolation — and against a body that is genuinely malformed
(`shell: echo {!x}"`), where both backends now emit valid code and the shell
reports the same unterminated-quote error, which is the right outcome.

**An aside worth knowing:** the two delimiters treat backslashes
differently. Nim's `"""` is raw, so `shell: printf 'a\nb\n'` passes `\n`
through for printf to interpret; Python's `"""` is not, so the same body
reaches the shell with a real newline. Both happen to print the same thing
here, but the two are not the same command. The escaped fallback this fix
adds is the raw-faithful one.

---

### Checked form `check = true` — DONE

Every script that cared about a command failing wrote the same three lines:
run it, look at the code, complain.  `check = true` says it once.

```python
shell(check = true): git commit -m {!msg}
```

A non-zero status raises — `OSError` on Nim naming the status and the
command, `CalledProcessError` on Python — and both are catchable, so the
form composes with `try`/`except` rather than only killing the program:

```python
try:
    shell(check = true): exit 9
except:
    print "handled"
```

It is an option rather than a new keyword (`shell!:` was the alternative),
which needed no grammar change: `shell_opts` already parses `name = value`,
and it reads alongside `cwd` and `timeout` as one more thing to say about
how the command should run.

Works with every form — bare, capture, tuple, `shellLines:` and an
`int`-typed target.  The command string is bound to a temp first, since it is
needed twice, to run and to name in the error, and may be an f-string with
side effects.

**Not used in `EXAMPLES/git1.ady` on purpose.** Its failures are reported
with `die()`, which prints `git1: could not create <repo>` and exits 1 — for
a CLI that is better than an uncaught exception's traceback. The checked form
suits a script whose failures should stop it outright.
`EXAMPLES/test_shell_block.ady` covers it, along with `{!x}` and `{*xs}`, so
the suite exercises all three.

---

### stdin feeding `stdin = expr` — DONE

There was no way to send a command its input: a script had to write a temp
file, or build an `echo ... |` prefix and quote it by hand.

```python
let text: str = "gamma\nalpha\nbeta\n"
let r = shell(stdin = text): sort          # r.output is alpha,beta,gamma
```

Works with the three capturing forms — record, tuple and `shellLines:`. On
Python it becomes `input=`; on Nim `adascriptRun` writes the text to the
child's pipe **inside the drain loop**, so a child that writes while we write
cannot deadlock us. Checked with 204 KB of input, well past the 64 KB pipe
buffer.

**It is refused on a bare `shell:` or an `int`-typed target**, with a
transpile-time error naming the forms that work. Feeding stdin needs a pipe,
and those two forms hand the child the terminal; silently ignoring the option
was the alternative, and that is the class of bug this session spent its time
removing.

**It also fixed a hang.** A capture gives the child a pipe for stdin, which
nobody wrote to and nobody closed, so a command that reads stdin waited for
input that never came — `let r = shell: cat` sat there until the timeout
(code 124), or forever without one. The pipe is now closed immediately when
there is nothing to send, so the child sees EOF; Python matches with
`stdin=DEVNULL`. Both return 0 at once.

---

### env mapping `env = expr` — DONE

Setting a variable for one command meant splicing `NAME=value` into the
command text, which is the one place a value crosses into the shell's own
namespace and so cannot be quoted by `{!x}`.  `EXAMPLES/git1.ady` does it
three times with `GIT_DIR=` and `GIT_WORK_TREE=`.

```python
let extra: {str}str = {"GIT_DIR": repo, "LC_ALL": "C"}
let r = shell(env = extra): git status
```

**It adds to the environment rather than replacing it.**  `startProcess` and
`subprocess` both take the child's *whole* environment, so the parent's is
copied in first and the given names layered over — a child that loses `PATH`
is nobody's intent.  Overriding an inherited name works: `HOME` set to
`/overridden` is what the child sees, while `PATH` survives.

It applies to **every** form, unlike `stdin`: setting a variable needs no
pipe, only a different environment for the child, so a bare `shell:` and an
`int`-typed target take it too — those route through `adascriptExec`, which
inherits the terminal and accepts an environment.

The Nim side needed `strtabs`: `startProcess` takes a `StringTableRef`, so
the helper builds one from `envPairs()` and applies the `Table[string, string]`
the dict literal already compiles to.  Python gets
`env={**os.environ, **(...)}`.

---

### Streaming form `shellIter` — DONE

Every capture waited for the child to finish, so a long-running or endless
command showed nothing until it exited — `tail -f` was unusable, and a slow
build's output arrived all at once at the end.

```python
for line in shellIter: tail -f build.log
    print line
```

Lines are yielded as they arrive.  Measured on both backends against
`echo first; sleep 1; echo second; sleep 1; echo third`: the three lines
arrive at 0s, 1s and 2s, not together at the end.

This one needed grammar work, unlike the other options — a `for` loop's
iterable is expression grammar and a shell body is not an expression.
`for_shell_stmt` is a production of its own:

```
for_shell_stmt = "for" for_target "in" "shellIter" shell_opts* ":"
                 shell_body_token+ block
```

The command body stops at the NEWLINE, which `block` then consumes with the
INDENT, so the loop body parses as an ordinary suite.  Both backends get a
helper — a Nim `iterator` over `p.outputStream.readLine`, a Python generator
over `Popen.stdout` — and the quoting sigils work inside the command as
usual.

**One thing to know:** only stdout is streamed, and there is no exit code.
A command whose status matters wants a capturing form; this one is for
watching output as it happens.

**A subtle bug caught while writing the test:** the loop variable has to be
registered in the symbol table *before* the body is rendered, or a body
containing `int(line)` does not know `line` is a string and emits a Nim type
conversion instead of `parseInt`. It compiled in a file where an earlier
loop had already registered the name, which is exactly the kind of thing
that hides until someone reorders their code.

---

### Bug 18 — py2nim splices a non-literal `cwd` as text

`cwd` is implemented on the Nim side by prefixing the command with
`cd <dir> &&`, and the option's value was spliced in as raw text.  A quoted
literal survives that; an expression does not — the *name* of the variable
lands in the command.

**Reproduction:**
```python
let d: str = "/tmp"
let r = shell(cwd = d): pwd
print r.output.strip()
```

```
Nim    ->              (emitted `cd d && pwd`; cd fails, pwd never runs)
Python ->  /tmp        (subprocess takes a real cwd= argument)
```

Nothing reports the failure: `cd` writes to stderr, `&&` swallows the rest,
and the capture comes back empty.  A command that was meant to run somewhere
else quietly does not run at all.

**Fixed.** A quoted literal is still spliced as text; anything else is
interpolated and quoted — `cd {quoteShell(d)} && …` — which also handles a
directory whose name contains a space.

Found while converting `EXAMPLES/git1.ady` to the `env` option, which is why
that file still spells the directory change itself.

---

### Exec form `shellExec` — DONE

Every other form forks a child and waits.  A wrapper script — `git1` being
the case in point — spends its whole life doing that: it forks the real
command, sits there holding a pid, then forwards the child's exit status by
hand and hopes signals land in the right place.

```python
shellExec: git {*args}          # this script *becomes* git
print "never reached"
```

`shellExec:` replaces the running process.  It does not return, the
command's own exit status becomes the script's, and the command inherits the
pid, the terminal and the parent's place in whatever launched it.

Compare with what it replaces:

```python
let code: int = shell: git {*args}
quit(code)
```

Both backends exec `/bin/sh -c`: Nim through `execv` / `execve`, Python
through `os.execv` / `os.execve`.  `cwd` and `env` apply; `timeout`, `stdin`
and `check` do not, because there is no child to wait for or feed.
Interpolation works as usual, `{!x}` and `{*xs}` included.

`cwd` nearly became a backend divergence.  Nim implements it by prefixing
the command with `cd <dir> &&`, which the exec path inherited for free;
Python passes a real `cwd=` argument to `subprocess`, and `os.execv` has no
such argument, so the option was silently dropped.  The same source ran in
two different directories.  The Python helper now takes `_cwd` and calls
`os.chdir` before the exec.

Verified on both backends: `shellExec: exit 42` gives the script exit
status 42, nothing written after the statement runs, and `env` reaches the
command.

**A false alarm worth recording.** The splat looked broken at first —
`shellExec(env = e): sh -c 'echo $MSG; printf "[%s]\n" {*args}'` printed
`[hello]` and `[two]` rather than `[hello]` and `[two words]`.  The splat
was fine; the test was not.  The inner `sh -c '…'` consumed a level of
quoting, so `'two words'` arrived at the inner shell already unwrapped.
Dropping the nested shell — `shellExec: printf '[%s]\n' {*args}` — prints
the two arguments correctly on both backends.  A quoting test that itself
nests shells cannot tell you which layer ate the quotes.

---

### Bug 19 — py2nim's cache does not watch TO_PYTHON

The Nim shell emitter borrows the grammar-neutral halves of the Python
backend — `_parse_shell_stmt`, `_apply_shell_quoting` — but py2nim's
staleness check only hashed `HPARSEC` and `ADASCRIPT_GRAMMAR` alongside
`TO_NIM`.  Editing one of those shared helpers therefore left the cached
`.nim` in place, and the run used the *old* translation.

This is the worst shape a caching bug can take: the edit is correct, the
test fails, and nothing points at the cache.  It cost a debugging session on
`shellExec` — the fix that made the statement stop emitting `execCmd` was
already applied and appeared to do nothing.

**Fixed.** `TO_PYTHON` joined the watched directories:

```python
# TO_PYTHON is in here because the Nim shell emitter borrows its
# grammar-neutral helpers (_parse_shell_stmt, _apply_shell_quoting);
# without it, editing those leaves a stale .nim behind.
for _extra_dir in ("HPARSEC", "ADASCRIPT_GRAMMAR", "TO_PYTHON"):
```

---

### Bug 20 — an unknown or inapplicable shell option is silently ignored

Every option is looked up by name from a dict; nothing ever checked the key
set.  A misspelling therefore compiled and did nothing:

```python
shell(timout = 5000): sleep 3600      # waits forever
shellExec(check = true, timeout = 5000): echo hi   # both dropped
```

Confirmed on both backends.  Only `stdin` on a non-capturing form was
diagnosed, and that check lived in the Python emitter, so the Nim backend
did not give it.

This is the same shape as bugs 16 and 18: the source says one thing, the
program does another, and nothing is printed.  The cost is worse here
because the option *looks* right -- someone reading the line sees a timeout
that is not there.

**Fixed.** `_validate_shell_opts` in `_parse_shell_stmt`, which both
backends decompose through, so one diagnostic serves both:

```
shell: unknown option `timout` -- did you mean `timeout`?
       (supported: check, cwd, env, stdin, timeout)
shellExec(timeout = ...) is not supported: shellExec replaces this process,
       so there is no child to time out. timeout works on shell, shellLines.
```

An option that exists but not on this form says why, and names the forms
that do take it; a misspelling gets a suggestion via `difflib`.  The
per-keyword sets are the table in the README.

---

### Bug 21 — `shellIter` accepted options and discarded all of them

The grammar allows `shell_opts` on the streaming form, but
`_parse_for_shell_stmt` never extracted them:

```python
for line in shellIter(cwd = "/tmp"): pwd
    print line          # printed the *current* directory, both backends
```

Worse than a typo being ignored: `cwd` here is spelled exactly as the
documentation spells it and still did nothing.

**Fixed**, by implementing the options rather than rejecting them, since
the grammar plainly intends to allow them.  `cwd` and `env` now work on
`shellIter`: Python passes them to `Popen`, Nim prefixes `cd <dir> &&`
(with the quoting bug 18 established) and builds a `StringTableRef` the way
the other forms do.  `timeout`, `stdin` and `check` are rejected by bug
20's validator with a reason -- a stream has no exit code to check and no
end to time out.

---

### Bug 22 — a call spanning lines skips every name-anchored rewrite (Python backend)

`call_trailer.to_py` returns the *raw source text* for a call whose
parentheses span lines (`get_multiline_brackets()`), which skips the
expression tree -- and with it every rewrite keyed on a name plus its call
trailer.

**Reproduction:**
```python
print("a:", readFile("/etc/hostname").strip())      # fine
print("b:",
      readFile("/etc/hostname").strip())            # not fine
```

```
Nim    ->  vm / vm          (translates finished expression strings)
Python ->  NameError: name 'readFile' is not defined
```

The same source works on one backend and dies on the other, and it dies at
*runtime*, in whichever branch happens to reach that line.

Expression-level rewrites that match a whole finished expression survive
this path -- `os.makedirs(...)` spanning lines still gets `exist_ok=True`.
Only the name-anchored ones are affected: `readFile`, `writeFile`, and the
`run` / `runLines` added in this pass.

**Fixed** for those, by rewriting the raw text before returning it
(`_rewrite_builtins_in_raw`), tracking string literals so a name inside a
quoted string is left alone, and tick attributes so `xs'Length` is not
mistaken for one.

**Still open, same root cause:** tick attributes themselves are dropped on
this path -- `print("x:",\n      xs'Length)` emits `xs'Length` into Python.
That predates this work and wants the real fix, which is not to bypass the
tree at all; translating ticks textually here would be duplicating the
translator that already exists.

---

### Argv form `run` / `runLines` — DONE

Every `shell:` form builds a command line and hands it to `/bin/sh`, so the
shell parses it and quoting is the caller's problem.  `{!x}` and `{*xs}`
solve that -- but only when remembered, and the default is still wrong.

```python
let r: RunResult = run(["git", "commit", "-m", msg])
let names: []str = runLines(["ls", dir])
```

The list *is* the argument vector.  Nothing parses the arguments a second
time, so there is nothing to quote:

```python
let nasty: str = "; touch canary"
run(["ls", nasty])        # ls: cannot access '; touch canary'
shell: ls {nasty}         # creates canary
shell: ls {!nasty}        # safe -- if you remember the !
```

Both were run: the argv form leaves the canary absent, the unquoted
interpolation creates it, identically on both backends.

`run` returns the same record as `shell` -- `.output`, `.stderr`, `.code` --
spelled `RunResult` where a binding needs an annotation (Python aliases it
to `SimpleNamespace`, Nim to the tuple).  `runLines` returns `[]str`.  Both
take `cwd`, `env`, `stdin`, `timeout` and `check` as keyword arguments; a
missing program reports 127 and a timeout 124, so the two families agree on
what failure looks like.

**Implementation note.** The Nim side reuses `adascriptRun` rather than
duplicating it: two new parameters, `argv` and `workDir`, pick
`startProcess(argv[0], args = argv[1..^1], options = {poUsePath})` over
`startProcess(cmd, options = {poEvalCommand})`.  All the drain, timeout and
stdin logic -- the part that took the care -- is therefore shared, which is
also the only way the two paths are guaranteed to behave the same.

**Two things the naming forced.** The Nim proc's parameters are spelled the
way the options are spelled in Adascript (`cwd`, `env`, `stdin`, `timeout`,
`check`), so the argument list passes through as written on both backends
with no keyword translation.  The one casualty is `stdin`, which the Python
backend had already rewritten to `sys.stdin` by the time the call site sees
it -- not a name a keyword argument may have -- so it is put back, and only
where it is a keyword.

---

### Concurrency form `shellSpawn` — DONE

Every other form waits.  The statement does not finish until the command
does, so N commands take the sum of their times, and a script that fetches
ten things fetched them one at a time.  There was no way to say "start this
and carry on".

```python
var jobs: []Job = []
for host in hosts:
    let j: Job = shellSpawn: ping -c1 {!host}
    jobs.append(j)

let results: []RunResult = waitAll(jobs)
```

Measured: three commands that each `sleep 1` finish in about a second on
both backends, not three.

`shellSpawn` hands back a `Job`.  `j.wait()` blocks and gives the same
`RunResult` the other forms do; `j.wait(check = true)` raises on failure;
`j.running()` answers without blocking; `j.kill()` sends SIGTERM and reaps;
`j.pid` is the child's.  `wait` is safe to call twice -- the result is kept
once the child is reaped, so the second call returns instead of hanging on
a child nobody can collect again.

`cwd`, `env` and `stdin` apply at the spawn.  `timeout` and `check` are
refused by bug 20's validator with a reason: there is nothing to time or
check yet, and both belong on the wait.  A spawn without a target is also
an error -- nothing would be left to reap the command.

**Why `waitAll` exists, and why it is not a loop over `wait`.** The output
goes into a pipe, and a pipe holds 64K on Linux.  A job producing more than
that stops when it fills and resumes when something drains it -- so waiting
for jobs one at a time quietly serialises them again, and the concurrency
the form was added for evaporates in exactly the case where it matters.
`waitAll` drains every job as it goes.

The two backends get there differently, and both were verified against two
jobs producing 200 000 bytes each:

- Nim: `adascriptJobStep` is one non-blocking pass over a job's three
  pipes, and both `wait` and `waitAll` are that called in a loop -- one job
  and many jobs are driven by exactly the same code, which is the only way
  they stay consistent.
- Python: a thread per job, each running that job's own `communicate()`.

**A divergence caught by the tests.** `kill()` originally called
`communicate()` on Python after SIGTERM, which hung: killing `/bin/sh -c
'sleep 30'` reaps the shell but leaves `sleep` holding the write end of the
pipe, so waiting for EOF waits for the full 30 seconds.  Nim did not hang,
because its `kill` never drained.  Both now terminate, reap and report 143
-- what a shell reports for a SIGTERMed command -- and discard whatever
output had accumulated, which is the same answer on both sides.

**Not a bug, but worth knowing:** a `\0` written in a shell body becomes a
real NUL byte in the emitted string literal, not the two characters the
shell would see.  `tr '\0' a` therefore receives an empty argument and
hangs.  Found while writing this test; the test uses `yes` instead.

---

### `pipefail`, block `join`, and `have()` — DONE

Three smaller gaps, closed together.

**`pipefail = true`.** A pipeline's exit status is its last command's, so
`shell: false | cat` reported 0 and the failure vanished. That is what POSIX
says and almost never what a script means.

```python
let r = shell(pipefail = true): grep -q pat file | sort | uniq
```

The catch is that `set -o pipefail` is a bash builtin and `/bin/sh` is dash
on most Linuxes -- prefixing the command alone would have made it *fail*
(dash exits 2 on `set -o pipefail`) rather than work, which is worse than
not having the option. Both backends therefore run these through bash:
Python passes `executable="/bin/bash"` to `subprocess`, and Nim gained a
`shellPath` parameter that switches `startProcess` from `poEvalCommand` to
`bash -c`. It applies to every form that runs a command through a shell.

Verified on both: `false | cat` gives 0 without the option and 1 with it,
and `true | cat` still gives 0.

**`join`.** An indented block joined its lines with `&&` and there was no
way to ask for anything else -- so "run these three regardless" and "these
three are a pipeline" both had to be written as one long line.

```python
let top = shell(join = "|"):
    sort access.log
    uniq -c
    head -1
```

`"&&"` (the default), `";"`, `"|"` and `"||"`, as literals: the lines are
joined at transpile time, so a variable could not work, and passing one
says so rather than being ignored.

**`have()`.** Asking whether a program is installed meant
`shell: command -v tool` and knowing that 127 is the answer -- a process and
a shell to ask a question PATH already answers.

```python
if not have("git"):
    die("git is required")
```

`shutil.which` on Python, `findExe` on Nim. It was tempting to spell this as
a file test, in the family of `-f` and `-x`, but the tokenizer matches those
as single letters from a nearly exhausted set (`-c` is already the character
-device test), and that tokenizer lives in HPARSEC rather than here. A
function costs no new syntax and reads at least as well.

---

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

---

### `shellIter(check = true)` — DONE

The streaming form had no exit status at all: the loop ended and nothing
said whether the command finished or died. A `tail -f` that the kernel
killed and one that ran out of input looked identical.

```python
for line in shellIter(check = true): make -j4
    print line
# raises here if make failed
```

Both helpers already reap the child, so the code was in hand at the end of
iteration; the raise goes there.

**The design point that needed settling: what a `break` means.** Leaving the
loop early leaves the command unfinished, and an unfinished command has no
status to object to -- raising then would be reporting a failure that has
not happened. So `check` applies only to a loop that ran to completion, and
both backends get that for free from how their iteration ends:

- Python: `break` throws `GeneratorExit` in at the `yield`, so the `finally`
  runs and the raise after it is never reached.
- Nim: this is an inline iterator, so `break` leaves the whole construct and
  never reaches the code after the yield loop.

Verified on both, four cases each: a stream that ends well does not raise,
one that ends badly raises after the last line, a `break` does not raise,
and without `check` a bad status is still ignored. It composes with `cwd`,
`env` and `pipefail`.

**An honest note on how this got here.** It was proposed as part of the
shell-syntax review, and then the first implementation pass did the opposite
-- listed `check` among the options `shellIter` refuses, with a rationale
("yields lines and never sees an exit code") written as though that had been
the intent. It reads like a decision but was a reversal that never got
surfaced. The rationale was also wrong: the iterator does see the exit code,
it just discarded it.

**A second bug fell out of testing this.** `pipefail` was never applied on
the Nim `shellIter` path -- the emitter edit that added it had been part of
a batch that aborted before writing, and nothing caught it because until now
no test combined the two. `shellIter(pipefail = true)` silently ran without
pipefail on Nim while working on Python. Fixed, and placed after the cwd
prefix so both backends emit `set -o pipefail; cd x && ...` in the same
order.
