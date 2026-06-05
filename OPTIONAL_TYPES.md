# Optional Types and Monadic Patterns in Adascript

Adascript optional types express "a value of type `T`, or nothing." The
prefix `?` annotates any type to make it optional. The absent state is
written `None` — exactly as in Python — and the transpiler maps every
`None`-related construct to Nim's `Option[T]` machinery automatically.
You never write `some()`, `.get()`, `.isSome`, or `.isNone` by hand.

`?T` is also the **Maybe monad** — a design pattern for composing sequences
of computations that may each fail, without nested `if` chains or exceptions.
The second half of this document (sections 16–22) covers monadic composition
directly.

```
source.ady  ──▶  python3 TO_PYTHON/py2py.py source.ady  ──▶  Python 3  (x | None)
            ──▶  python3 TO_NIM/py2nim.py   source.ady  ──▶  Nim       (Option[T])
```

---

## Table of Contents

1. [Basic syntax](#1-basic-syntax)
2. [Optional function parameters](#2-optional-function-parameters)
3. [Optional return types](#3-optional-return-types)
4. [Optional fields in records and classes](#4-optional-fields-in-records-and-classes)
5. [Checking for None](#5-checking-for-none)
6. [Auto-unwrap inside None-guards](#6-auto-unwrap-inside-none-guards)
7. [Default values with `or`](#7-default-values-with-or)
8. [Assignment and return — automatic wrapping](#8-assignment-and-return--automatic-wrapping)
9. [Optional in conditions (truthiness)](#9-optional-in-conditions-truthiness)
10. [Walrus operator `while m := expr:`](#10-walrus-operator-while-m--expr)
11. [Ref types — no Option wrapping](#11-ref-types--no-option-wrapping)
12. [Composing optional types](#12-composing-optional-types)
13. [What not to do](#13-what-not-to-do)
14. [Reference table](#14-reference-table)
15. [Real-world examples](#15-real-world-examples)

**Monadic patterns:**

16. [?T as the Maybe monad — unit, bind, fmap](#16-t-as-the-maybe-monad--unit-bind-fmap)
17. [Bind chains — the railroad pattern](#17-bind-chains--the-railroad-pattern)
18. [Do-notation analogue — walrus as bind](#18-do-notation-analogue--walrus-as-bind)
19. [Fmap — lifting a pure function over ?T](#19-fmap--lifting-a-pure-function-over-t)
20. [Sequence and traverse — []?T to ?[]T](#20-sequence-and-traverse--t-to-t)
21. [Result type — the Either monad](#21-result-type--the-either-monad)
22. [Choosing between ?T and Result_T](#22-choosing-between-t-and-result_t)

---

## 1. Basic syntax

`?T` means "T or None". The `?` prefix works in front of any type:

```python
var name:     ?str        # optional string
var count:    ?int        # optional integer
var weights:  ?[]float    # optional list of floats
var lookup:   ?{str}int   # optional dict
```

**Python output:**

```python
name:    str | None
count:   int | None
weights: list[float] | None
lookup:  dict[str, int] | None
```

**Nim output:**

```nim
var name:    Option[string]
var count:   Option[int]
var weights: Option[seq[float]]
var lookup:  Option[Table[string, int]]
```

The absent state is always written `None` in Adascript source regardless
of target:

```python
var result: ?int = None    # initially absent
result = 42                # present
result = None              # absent again
```

---

## 2. Optional function parameters

`?T` on a parameter annotates an argument that may be omitted. Pair it
with `= None` as the default to make the argument truly optional at the
call site:

```python
def greet(name: str, suffix: ?str = None) -> str:
    if suffix is not None:
        return f"Hello, {name} {suffix}!"
    return f"Hello, {name}!"
```

**Python output:**

```python
def greet(name: str, suffix: str | None = None) -> str:
    if suffix is not None:
        return f"Hello, {name} {suffix}!"
    return f"Hello, {name}!"
```

**Nim output:**

```nim
proc greet(name: string, suffix: Option[string] = none(string)): string =
    if suffix.isSome:
        return fmt"Hello, {name} {suffix.get()}!"
    return fmt"Hello, {name}!"
```

### Multiple optional parameters

```python
def connect(
    host:     str,
    port:     ?int    = None,
    timeout:  ?float  = None,
    user:     ?str    = None,
) -> Connection:
    let p: int   = port    or 5432
    let t: float = timeout or 30.0
    ...
```

---

## 3. Optional return types

A function returning `?T` either produces a value or signals absence.
Use this instead of sentinel values (`-1`, `""`) or raising exceptions
for expected-absent cases:

```python
def find_first(items: []str, prefix: str) -> ?str:
    for item in items:
        if item.startswith(prefix):
            return item
    return None
```

**Python output:**

```python
def find_first(items: list[str], prefix: str) -> str | None:
    for item in items:
        if item.startswith(prefix):
            return item
    return None
```

**Nim output:**

```nim
proc find_first(items: seq[string], prefix: string): Option[string] =
    for item in items:
        if item.startsWith(prefix):
            return some(item)
    return none(string)
```

The `return item` line gets `some(...)` inserted automatically; `return None`
becomes `none(string)`.

### Chaining optional-returning functions

```python
def parse_int(s: str) -> ?int:
    try:
        return int(s)
    except:
        return None

def first_int(tokens: []str) -> ?int:
    for t in tokens:
        let v: ?int = parse_int(t)
        if v is not None:
            return v
    return None
```

---

## 4. Optional fields in records and classes

Use `?T` inside a `record` or class body to express that a field may
be absent. This is cleaner than a sentinel default and makes the
"maybe missing" intent explicit in the type:

```python
type Config is record:
    host:     str
    port:     int
    id_rsa:   ?str       # SSH key path — may not be needed
    log_file: ?str       # optional logging destination
```

**Nim output:**

```nim
type Config = object
    host:     string
    port:     int
    id_rsa:   Option[string]
    log_file: Option[string]
```

Inside a class:

```python
class Parser:
    var source:     str
    var lookahead:  ?Token   # one token of look-ahead, may be absent

    def __init__(self, source: str):
        self.source    = source
        self.lookahead = None

    def peek(self) -> ?Token:
        if self.lookahead is None:
            self.lookahead = self._lex_next()
        return self.lookahead
```

---

## 5. Checking for None

Write `is None` and `is not None` exactly as in Python.
The transpiler rewrites them to `.isNone` / `.isSome` in Nim output:

```python
var value: ?int = get_value()

if value is None:
    print("nothing")

if value is not None:
    print("got something")
```

**Python output** (unchanged):

```python
if value is None:
    print("nothing")

if value is not None:
    print("got something")
```

**Nim output:**

```nim
if value.isNone:
    echo("nothing")

if value.isSome:
    echo("got something")
```

### Using `==` and `!=`

`== None` and `!= None` are equivalent to `is None` and `is not None`:

```python
if result == None:
    fallback()

if result != None:
    process(result)
```

Both produce `.isNone` / `.isSome` in Nim.

---

## 6. Auto-unwrap inside None-guards

Inside an `if x is not None:` block, every use of `x` is automatically
unwrapped — you access the value directly without calling `.get()`:

```python
var path: ?str = find_config_file()

if path is not None:
    let content: str = read_file(path)    # path used directly — no unwrap needed
    process(content)
```

**Nim output:**

```nim
var path: Option[string] = find_config_file()

if path.isSome:
    let content: string = readFile(path.get())   # .get() inserted automatically
    process(content)
```

### Field access through an optional

Field access on an auto-unwrapped optional also gets `.get()` inserted
in the right place:

```python
var tok: ?Token = try_next(TK_IDENT)

if tok is not None:
    let name: str = tok.content     # tok.get().content in Nim
    let line: int = tok.line        # tok.get().line in Nim
    register(name, line)
```

**Nim output:**

```nim
var tok: Option[Token] = try_next(TK_IDENT)

if tok.isSome:
    let name: string = tok.get().content
    let line: int    = tok.get().line
    register(name, line)
```

### Nested guards

Each `if x is not None:` scope tracks its own unwrap set. A nested
guard on a different variable adds to the set:

```python
var ssh:  ?SSH  = parse_ssh(config)
var dest: ?str  = find_backup(folder)

if ssh is not None:
    if dest is not None:
        run_rsync(ssh.cmd, dest)   # both unwrapped: ssh.get().cmd, dest.get()
    else:
        run_local(ssh.cmd)         # only ssh unwrapped
```

---

## 7. Default values with `or`

`x or default` where `x` is `?T` extracts the value if present,
otherwise falls back to `default`. This is the idiomatic "optional
with fallback" pattern — no `if` needed:

```python
def connect(host: str, port: ?int = None) -> None:
    let p: int = port or 5432    # use 5432 when port is absent
    ...
```

**Python output:**

```python
def connect(host: str, port: int | None = None) -> None:
    p: int = port or 5432
    ...
```

**Nim output:**

```nim
proc connect(host: string, port: Option[int] = none(int)): void =
    let p: int = port.get(5432)   # .get(default) inserted automatically
    ...
```

### Chaining fallbacks

```python
let color: str = env_color or config_color or "white"
```

When `env_color` and `config_color` are both `?str`, this chains
`.get(...)` calls in Nim:

```nim
let color: string = env_color.get(config_color.get("white"))
```

---

## 8. Assignment and return — automatic wrapping

You never write `some(x)` or `none(T)` in Adascript source. The
transpiler inserts them automatically based on type context.

### Assignment

When the left-hand side is a known `?T` variable and the right-hand
side is a plain value, `some(...)` is inserted:

```python
var best: ?str = None

for candidate in candidates:
    if score(candidate) > threshold:
        best = candidate       # becomes some(candidate) in Nim
        break
```

**Nim output:**

```nim
var best: Option[string] = none(string)

for candidate in candidates:
    if score(candidate) > threshold:
        best = some(candidate)
        break
```

### Return

`return value` in a function declared `-> ?T` wraps with `some()`;
`return None` emits `none(T)`:

```python
def lookup(key: str) -> ?int:
    if key in table:
        return table[key]     # return some(table[key]) in Nim
    return None               # return none(int) in Nim
```

**Nim output:**

```nim
proc lookup(key: string): Option[int] =
    if key in table:
        return some(table[key])
    return none(int)
```

### Call-site coercion

When a function expects `?T` and you pass a plain `T`, the argument
is wrapped in `some()` automatically:

```python
def log_cmd(message: str, ssh: ?SSH = None) -> None:
    ...

log_cmd("backup started", my_ssh)   # my_ssh: SSH → some(my_ssh) in Nim
log_cmd("done")                     # no ssh → none(SSH) in Nim
```

---

## 9. Optional in conditions (truthiness)

A `?T` variable used as a condition is automatically tested for
presence, not for the truthiness of the wrapped value:

```python
var result: ?str = find_result()

if result:                      # means "if result is present"
    use(result)
```

**Nim output:**

```nim
var result: Option[string] = find_result()

if result.isSome:
    use(result.get())
```

A function call whose return type is `?T` used as a bare condition also
gets `.isSome` appended:

```python
if find_backup_marker(folder, ssh):    # returns ?str
    check_dest_is_backup_folder(...)
```

**Nim output:**

```nim
if find_backup_marker(folder, ssh).isSome:
    check_dest_is_backup_folder(...)
```

---

## 10. Walrus operator `while m := expr:`

When `expr` returns `?T`, the walrus pattern loops until absent:

```python
while token := lexer.try_next(TK_IDENT):
    register(token.content, token.line)
```

**Python output:**

```python
while token := lexer.try_next(TK_IDENT):
    register(token.content, token.line)
```

**Nim output:**

```nim
while true:
    let token = lexer.try_next(TK_IDENT)
    if token.isNone: break
    register(token.get().content, token.get().line)
```

Inside the loop body, `token` is auto-unwrapped — `token.content` and
`token.line` become `token.get().content` / `token.get().line`.

### Walrus in `if` (single check)

```python
if m := re_match(pattern, line):
    process(m.group(1))
```

**Nim output:**

```nim
let m = re_match(pattern, line)
if m.isSome:
    process(m.get().group(1))
```

---

## 11. Ref types — no Option wrapping

Class instances declared with `@virtual` or that inherit from a base
class are heap-allocated **ref types** in Nim. They are already nullable
via `nil`, so `?RefClass` stays as `RefClass` with no `Option` wrapper —
the transpiler detects this automatically:

```python
@virtual
class Node:
    var value: int
    var next:  ?Node     # recursive nullable ref — no Option in Nim

var head: ?Node = None   # nil in Nim, not Option[Node]
```

**Nim output:**

```nim
type Node = ref object of RootObj
    value: int
    next:  Node          # ref, already nullable

var head: Node = nil     # nil, not none(Node)
```

`is None` on a ref type becomes `== nil` in Nim (not `.isNone`):

```python
if head is None:
    print("empty list")
```

**Nim output:**

```nim
if head == nil:
    echo("empty list")
```

> **Rule**: value types (`record`, named tuples, primitives) → `Option[T]`.
> Ref types (class with `@virtual`, or subclass) → already nullable, no wrapping.

---

## 12. Composing optional types

`?T` composes with every other type constructor:

| Adascript | Nim |
|---|---|
| `?int` | `Option[int]` |
| `?str` | `Option[string]` |
| `?[]str` | `Option[seq[string]]` |
| `[]?str` | `seq[Option[string]]` |
| `?{str}int` | `Option[Table[string, int]]` |
| `?Token_T` (record) | `Option[Token_T]` |
| `?Node` (ref class) | `Node` (nil-able, no Option) |

### List of optionals — `[]?T`

Useful when a collection may have holes (elements that are genuinely
absent vs. zero/empty):

```python
type Row_T is record:
    cells: []?str     # each cell may be absent (sparse table)

def get_cell(row: Row_T, col: int) -> ?str:
    if col < len(row.cells):
        return row.cells[col]
    return None
```

### Optional of a compound type

```python
def parse_ssh_pattern(folder: str) -> ?{str}str:
    if folder == /^(?P<user>\w+)@(?P<host>[\w.]+):(?P<path>.+)$/:
        return namedCaptures    # dict — wrapped in some() automatically
    return None
```

**Nim output:**

```nim
proc parse_ssh_pattern(folder: string): Option[Table[string, string]] =
    ...
    return some(namedCaptures)
    ...
    return none(Table[string, string])
```

---

## 13. What not to do

### Don't use sentinel values

Prefer `?T` over magic sentinel values like `-1`, `""`, or `0`:

```python
# Avoid:
def find_index(items: []str, target: str) -> int:
    for i, item in enumerate(items):
        if item == target:
            return i
    return -1    # caller must know -1 means "not found"

# Prefer:
def find_index(items: []str, target: str) -> ?int:
    for i, item in enumerate(items):
        if item == target:
            return i
    return None  # explicit, type-checked absence
```

### Don't use `?T` on ref types

Applying `?` to a class that is already a ref type adds an unnecessary
`Option` layer (unless you deliberately want `Option[RefType]`):

```python
# Probably wrong — Node is a ref class:
var maybe_node: ?Node = None    # Node already nullable via nil

# Correct — just declare without ?:
var maybe_node: Node = None     # nil in Nim
```

### Don't nest `?` redundantly

`??T` is a type-annotation error — there is no "optional optional":

```python
# Wrong:
var x: ??int = None

# Correct:
var x: ?int = None
```

### Don't call `.get()` manually

The transpiler inserts `.get()` in the right places inside None-guards
and on auto-unwrapped walrus bindings. Calling `.get()` yourself is not
wrong, but it is unnecessary and adds noise:

```python
# Unnecessary:
if path is not None:
    open(path.get())    # .get() is redundant — transpiler handles it

# Clean:
if path is not None:
    open(path)
```

---

## 14. Reference table

| Adascript source | Python output | Nim output |
|---|---|---|
| `?T` | `T \| None` | `Option[T]` |
| `var x: ?T = None` | `x: T \| None = None` | `var x: Option[T] = none(T)` |
| `x = value` *(LHS is `?T`)* | `x = value` | `x = some(value)` |
| `return value` *(in `-> ?T` fn)* | `return value` | `return some(value)` |
| `return None` *(in `-> ?T` fn)* | `return None` | `return none(T)` |
| `x is None` | `x is None` | `x.isNone` |
| `x is not None` | `x is not None` | `x.isSome` |
| `x == None` | `x == None` | `x.isNone` |
| `x != None` | `x != None` | `x.isSome` |
| `if x is not None: use(x)` | unchanged | `if x.isSome: use(x.get())` |
| `x or default` *(x is `?T`)* | `x or default` | `x.get(default)` |
| `if x:` *(x is `?T`)* | unchanged | `if x.isSome:` |
| `while m := f():` *(f returns `?T`)* | unchanged | `while true: let m=f(); if m.isNone: break` |
| `?RefClass` | `RefClass \| None` | `RefClass` (nil-able) |
| `f(plain_val)` *(param is `?T`)* | unchanged | `f(some(plain_val))` |

---

## 15. Real-world examples

### "find" pattern — function that may find nothing

From `rsync_time_machine.ady`:

```python
def find_backup_marker(folder: str, ssh: ?SSH = None) -> ?str:
    let marker: str = backup_marker_path(folder)
    let output: str = find_cmd(marker, dest_is_ssh(ssh))
    if output.strip():
        return output.strip()
    return None
```

The caller can safely test and use:

```python
if find_backup_marker(dest_folder, ssh) is None:
    let marker: str = backup_marker_path(dest_folder)
    log(f"creating backup marker: {marker}")
    run_cmd(f"touch '{marker}'", ssh)
```

---

### Optional SSH connection — threading context through helpers

Many helpers in `rsync_time_machine.ady` accept `ssh: ?SSH = None`.
When `ssh` is present, the command runs remotely; otherwise it runs
locally:

```python
def run_cmd(cmd: str, ssh: ?SSH = None) -> CmdResult:
    let full_cmd: str = f"{ssh.cmd} '{cmd}'" if ssh is not None else cmd
    ...

def mkdir_p(path: str, ssh: ?SSH = None) -> None:
    run_cmd(f"mkdir -p -- '{path}'", ssh)

def rm_file(path: str, ssh: ?SSH = None) -> None:
    run_cmd(f"rm -f -- '{path}'", ssh)
```

The `?SSH = None` default means local-only callers never mention `ssh`:

```python
mkdir_p("/tmp/work")            # local
mkdir_p("/backup", ssh=conn)    # remote
```

---

### Lexer lookahead — optional token buffer

From `c500.ady`:

```python
class Lexer:
    var src:          str
    var loc:          int
    var lookahead_ref: ?Lexer    # clone used for one-token look-ahead

    def try_next(self, kind: TokKind_T) -> ?Token_T:
        if self.peek().kind == kind:
            return self.next()
        return None
```

Callers use the walrus pattern:

```python
while param := lexer.try_next(TK_IDENT):
    params.append(param.content)
    if not lexer.try_next(TK_COMMA):
        break
```

**Nim output:**

```nim
while true:
    let param = lexer.try_next(TK_IDENT)
    if param.isNone: break
    params.add(param.get().content)
    if not lexer.try_next(TK_COMMA).isSome:
        break
```

---

### Optional geometry predicate

From `geo_server.ady`:

```python
class Region:
    """A geographic region with an optional predicate function."""
    var _predicate: ?[(Point,)]bool

    def __init__(self, predicate: ?[(Point,)]bool = None) -> None:
        self._predicate = predicate

    def contains(self, p: Point) -> bool:
        if self._predicate is not None:
            return self._predicate(p)     # callable unwrapped automatically
        return self._default_contains(p)
```

The `?[(Point,)]bool` type is an optional callable — a function that
takes a `Point` and returns `bool`, or nothing (use the default).

---

### Pattern matching over optionals

Optionals integrate naturally with `case/when`:

```python
def safe_divide(a: float, b: float) -> ?float:
    if b == 0.0:
        return None
    return a / b

def format_result(r: ?float) -> str:
    case r:
        when None:
            return "undefined (division by zero)"
        when others:
            if r is not None:
                return f"{r:.4f}"
```

Or with the walrus pattern for a chain of fallible steps:

```python
def process_line(line: str) -> ?Result:
    if m := parse_header(line):
        return handle_header(m)
    if m := parse_data(line):
        return handle_data(m)
    if m := parse_footer(line):
        return handle_footer(m)
    return None
```

Each `parse_*` returns `?Match`. The walrus checks for presence and
auto-unwraps `m` inside the `if` body.

---

---

## 16. `?T` as the Maybe monad — unit, bind, fmap

A monad is a pattern for composing computations in a context — here the
context is *possible absence*. The Maybe monad has three core operations.
In Adascript all three are expressed without ceremony; the transpiler
inserts the Nim plumbing automatically.

### Unit (return) — wrap a plain value

Lift a value into the optional context. In Adascript this happens
automatically wherever the compiler knows the target type is `?T`:

```python
def safe_sqrt(x: float) -> ?float:
    if x < 0.0:
        return None        # none(float) in Nim
    return x ** 0.5        # some(x ** 0.5) in Nim — unit applied implicitly
```

### Bind (>>=) — chain a fallible step

Apply a function `f: T → ?U` to the value inside `?T`; if the input is
absent, propagate absence without calling `f`.

In Adascript, bind is expressed with an `if x is not None:` guard or
the walrus `if r := f(x):` form. Both desugar identically in Nim:

```python
# Explicit guard form — bind(m, f)
def bind_int(m: ?int, f: [(int,)]?int) -> ?int:
    if m is not None:
        return f(m)      # f applied to the unwrapped value
    return None          # absence propagated

# Usage
let x: ?int = some_optional_int()
let y: ?int = bind_int(x, lambda n: n * 2 if n > 0 else None)
```

**Nim output of bind_int:**

```nim
proc bind_int(m: Option[int], f: proc(a0: int): Option[int]): Option[int] =
    if m.isSome:
        return f(m.get())
    return none(int)
```

### Fmap — apply a pure function

Apply a function `f: T → U` to the value inside `?T`, producing `?U`.
Unlike bind, `f` itself cannot fail — it always produces a result.

```python
def fmap_int(m: ?int, f: [(int,)]int) -> ?int:
    if m is not None:
        return f(m)
    return None

# Usage — double the value if present, propagate None otherwise
let doubled: ?int = fmap_int(parse_int(text), lambda n: n * 2)
```

**Nim output:**

```nim
proc fmap_int(m: Option[int], f: proc(a0: int): int): Option[int] =
    if m.isSome:
        return some(f(m.get()))
    return none(int)
```

### Monad laws

`?T` satisfies the three monad laws. You don't need to prove them — just
note that the laws hold, so composed bind chains behave predictably:

| Law | Statement | In Adascript |
|-----|-----------|--------------|
| **Left identity** | `unit(a) >>= f ≡ f(a)` | `return a` in `-> ?T` fn, then bind is just `f(a)` |
| **Right identity** | `m >>= unit ≡ m` | binding with `return x` leaves `m` unchanged |
| **Associativity** | `(m >>= f) >>= g ≡ m >>= (λx. f(x) >>= g)` | chained `if` guards associate freely |

---

## 17. Bind chains — the railroad pattern

A bind chain is a sequence of fallible steps where *the first failure
short-circuits the rest*. This is sometimes called the "railroad" because
the happy path is one track and the failure path is another — once you
fall off, you stay off.

### Without monads (nested ifs)

```python
def load_user_config(path: str) -> ?Config:
    let text: ?str = read_file_safe(path)
    if text is not None:
        let raw: ?dict = parse_json(text)
        if raw is not None:
            let host: ?str = raw.get("host")
            if host is not None:
                let port_s: ?str = raw.get("port")
                if port_s is not None:
                    let port: ?int = parse_int(port_s)
                    if port is not None:
                        return Config(host=host, port=port)
    return None
```

This works but pyramids badly. Every step adds one level of indentation.

### With the guard-and-return pattern (flat bind chain)

Return `None` eagerly when a step fails — this is exactly bind written
out explicitly:

```python
def load_user_config(path: str) -> ?Config:
    let text: ?str = read_file_safe(path)
    if text is None: return None          # bind: propagate failure

    let raw: ?dict = parse_json(text)
    if raw is None: return None

    let host: ?str = raw.get("host")
    if host is None: return None

    let port_s: ?str = raw.get("port")
    if port_s is None: return None

    let port: ?int = parse_int(port_s)
    if port is None: return None

    return Config(host=host, port=port)   # unit: wrap the result
```

**Nim output:**

```nim
proc load_user_config(path: string): Option[Config] =
    let text: Option[string] = read_file_safe(path)
    if text.isNone: return none(Config)

    let raw: Option[Table[string, string]] = parse_json(text.get())
    if raw.isNone: return none(Config)

    let host: Option[string] = raw.get().getOrDefault("host", "")  # simplified
    if host.isNone: return none(Config)

    ...

    return some(Config(host: host.get(), port: port.get()))
```

The flat style is idiomatic Adascript for long bind chains. Each `if x
is None: return None` is a monadic bind step.

### Carrying the error through — annotated failure

When you need to know *which* step failed, attach a reason before each
short-circuit:

```python
def load_user_config(path: str) -> ?Config:
    let text: ?str = read_file_safe(path)
    if text is None:
        log(f"cannot read config: {path}")
        return None

    let raw: ?dict = parse_json(text)
    if raw is None:
        log(f"invalid JSON in: {path}")
        return None

    let port: ?int = parse_int(raw.get("port") or "")
    if port is None:
        log("port is not a valid integer")
        return None

    return Config(host=raw.get("host") or "localhost", port=port)
```

---

## 18. Do-notation analogue — walrus as bind

Haskell's `do` notation desugars `<-` binding into `>>=` calls. The
walrus `if r := f(x):` pattern in Adascript is the same idea —
syntactic sugar over bind, keeping the happy path at a flat indentation
level.

**Haskell do-notation:**

```haskell
loadConfig :: FilePath -> Maybe Config
loadConfig path = do
    text <- readFileSafe path
    raw  <- parseJson text
    host <- Map.lookup "host" raw
    portS <- Map.lookup "port" raw
    port <- parseInt portS
    return Config { host = host, port = port }
```

**Adascript walrus-as-do:**

```python
def load_config(path: str) -> ?Config:
    if text := read_file_safe(path):
        if raw := parse_json(text):
            if host := raw.get("host"):
                if port_s := raw.get("port"):
                    if port := parse_int(port_s):
                        return Config(host=host, port=port)
    return None
```

Each `if x := f(...):`  line is one `<-` binding:
- it calls `f`, checks for presence (`.isSome`)  
- on success, auto-unwraps `x` inside the body
- on failure, falls through to `return None`

**Nim output:**

```nim
proc load_config(path: string): Option[Config] =
    let text = read_file_safe(path)
    if text.isSome:
        let raw = parse_json(text.get())
        if raw.isSome:
            let host = raw.get().getOrDefault("host", "")
            if host.len > 0:
                let port_s = raw.get().getOrDefault("port", "")
                if port_s.len > 0:
                    let port = parse_int(port_s)
                    if port.isSome:
                        return some(Config(host: host, port: port.get()))
    return none(Config)
```

### Choosing walrus vs. flat guard

| Style | Best for |
|-------|----------|
| Walrus `if r := f():` | Short chains (≤4 steps), where the nesting is readable |
| Flat `if x is None: return None` | Long chains, or when you need to log/annotate each failure |
| `do:` block | Any length chain; no nesting, no boilerplate — closest to Haskell do-notation |

Both walrus and flat guard are semantically identical — monadic bind either way. The `do:` block is a dedicated syntax for the same pattern with less ceremony.

---

## 18b. `do:` block — native monadic bind syntax

The `do:` block is Adascript's first-class do-notation. Each `x <- expr`
line binds the unwrapped value of `expr` (which must return `?T`) to `x`,
or short-circuits the enclosing function with `return none(R)` if the
result is `None`.

**Syntax:**

```python
def load_config(path: str) -> ?Config:
    do:
        text   <- read_file_safe(path)
        raw    <- parse_json(text)
        host   <- raw.get("host")
        port_s <- raw.get("port")
        port   <- parse_int(port_s)
    return Config(host=host, port=port)
```

After the `do:` block all bound names (`text`, `raw`, `host`, `port_s`,
`port`) are plain, non-optional variables in scope — no `.get()` or guard
needed.

**Nim output:**

```nim
proc load_config(path: string): Option[Config] =
    let adadoText = read_file_safe(path)
    if adadoText.isNone: return none(Config)
    let text = adadoText.get()
    let adadoRaw = parse_json(text)
    if adadoRaw.isNone: return none(Config)
    let raw = adadoRaw.get()
    let adadoHost = raw.getOrDefault("host", "")
    if adadoHost.isNone: return none(Config)
    let host = adadoHost.get()
    let adadoPortS = raw.getOrDefault("port", "")
    if adadoPortS.isNone: return none(Config)
    let port_s = adadoPortS.get()
    let adadoPort = parse_int(port_s)
    if adadoPort.isNone: return none(Config)
    let port = adadoPort.get()
    return some(Config(host: host, port: port))
```

### Comparison: walrus vs. flat guard vs. `do:`

```python
# walrus — readable for short chains, nesting grows with depth
def compute(a: str, b: str) -> ?int:
    if x := parse_int(a):
        if y := parse_int(b):
            if q := safe_div(x, y):
                return q
    return None

# flat guard — no nesting, but repetitive
def compute(a: str, b: str) -> ?int:
    let x: ?int = parse_int(a)
    if x is None: return None
    let y: ?int = parse_int(b)
    if y is None: return None
    let q: ?int = safe_div(x, y)
    if q is None: return None
    return q

# do: block — no nesting, no boilerplate
def compute(a: str, b: str) -> ?int:
    do:
        x <- parse_int(a)
        y <- parse_int(b)
        q <- safe_div(x, y)
    return q
```

All three compile to equivalent Nim. The `do:` block is preferred for
chains of three or more steps.

### Rules

- Every `expr` on the right of `<-` must return `?T` for some `T`.
- The enclosing function must also return `?R` — the block short-circuits
  via `return none(R)`.
- Bound names are plain `let` bindings (type `T`, not `?T`) and are in
  scope after the block.
- The `do:` block does not introduce its own scope; all bindings are
  visible in the rest of the function body.

---

## 19. Fmap — lifting a pure function over `?T`

Fmap applies a *pure* (always-succeeding) function to the value inside
an optional. The optional context is preserved: present maps to present,
absent maps to absent.

### Inline fmap

For one-off transformations, write the check inline:

```python
let raw_score: ?str  = get_raw_score(data)
let score:     ?int  = int(raw_score) if raw_score is not None else None
let grade:     ?str  = letter_grade(score) if score is not None else None
```

**Nim output** (auto-unwrap inside the `if` guard):

```nim
let raw_score: Option[string] = get_raw_score(data)
let score: Option[int] = if raw_score.isSome: some(int(raw_score.get())) else: none(int)
let grade: Option[string] = if score.isSome: some(letter_grade(score.get())) else: none(string)
```

### Reusable fmap helpers

For types you fmap over frequently, write a typed helper:

```python
def fmap_str(m: ?str, f: [(str,)]str) -> ?str:
    if m is not None: return f(m)
    return None

def fmap_int(m: ?int, f: [(int,)]int) -> ?int:
    if m is not None: return f(m)
    return None

# Usage
let upper: ?str = fmap_str(get_name(record), lambda s: s.upper())
let double: ?int = fmap_int(get_count(record), lambda n: n * 2)
```

### Fmap through a pipeline

Fmap composes: apply a series of pure transforms without breaking out of
the optional context:

```python
def normalise_email(raw: ?str) -> ?str:
    let stripped: ?str = fmap_str(raw,    lambda s: s.strip())
    let lowered:  ?str = fmap_str(stripped, lambda s: s.lower())
    let valid:    ?str = fmap_str(lowered,  lambda s: s if "@" in s else None)
    return valid
```

Wait — the last step uses `None` as a signal, which makes it a *bind*
step (T → ?T), not a fmap step (T → T). Rewrite the final check as bind:

```python
def normalise_email(raw: ?str) -> ?str:
    let stripped: ?str = fmap_str(raw,      lambda s: s.strip())
    let lowered:  ?str = fmap_str(stripped, lambda s: s.lower())
    if lowered is None: return None
    if "@" not in lowered: return None    # bind: validate and short-circuit
    return lowered
```

---

## 20. Sequence and traverse — `[]?T` to `?[]T`

**Sequence** turns a list of optionals into an optional list.
If *any* element is absent, the whole result is absent.

```python
def sequence_ints(items: []?int) -> ?[]int:
    var result: []int = []
    for item in items:
        if item is None:
            return None          # one failure → whole sequence fails
        result.append(item)
    return result
```

**Nim output:**

```nim
proc sequence_ints(items: seq[Option[int]]): Option[seq[int]] =
    var result: seq[int] = @[]
    for item in items:
        if item.isNone:
            return none(seq[int])
        result.add(item.get())
    return some(result)
```

### Traverse — map then sequence in one pass

Traverse applies a fallible function to each element and collects the
results, failing fast on the first absence:

```python
def traverse_parse(tokens: []str) -> ?[]int:
    var result: []int = []
    for tok in tokens:
        let n: ?int = parse_int(tok)
        if n is None:
            return None          # bad token → fail the whole parse
        result.append(n)
    return result

# Usage
let values: ?[]int = traverse_parse(["1", "42", "7"])   # some([1, 42, 7])
let bad:    ?[]int = traverse_parse(["1", "??", "7"])   # None
```

### Traverse with a walrus

```python
def traverse_parse(tokens: []str) -> ?[]int:
    var result: []int = []
    for tok in tokens:
        if n := parse_int(tok):
            result.append(n)
        else:
            return None
    return result
```

### Collecting all results (ignoring failures)

When you want successes only — not the "all or nothing" semantics —
use a list comprehension with a filter instead:

```python
# Monadic traverse — all or nothing
let strict: ?[]int = traverse_parse(tokens)

# Non-monadic filter — keep whatever succeeds
let loose: []int = [parse_int(t) for t in tokens if parse_int(t) is not None]
```

---

## 21. Result type — the Either monad

`?T` models absence but carries no information about *why* something is
absent. The **Either / Result monad** pairs a success value with a
failure message. In Adascript, express it with a variant record:

```python
type ResultTag_T is enum OK, ERR

type ParseResult_T (tag: ResultTag_T) is record:
    case tag is:
        when OK:
            value: int
        when ERR:
            message: str
```

**Python output:**

```python
class ResultTag_T(Enum): OK = auto(); ERR = auto()

@dataclass
class ParseResult_T:
    tag:     ResultTag_T
    value:   int  = 0
    message: str  = ""
```

**Nim output:**

```nim
type ResultTag_T = enum OK, ERR

type ParseResult_T = object
    case tag: ResultTag_T
    of OK:  value:   int
    of ERR: message: string
```

### Unit — wrap a success or failure

```python
def ok(value: int) -> ParseResult_T:
    return ParseResult_T(tag=OK, value=value)

def err(msg: str) -> ParseResult_T:
    return ParseResult_T(tag=ERR, message=msg)
```

### Bind — propagate failure automatically

```python
def bind_result(r: ParseResult_T,
                f: [(int,)]ParseResult_T) -> ParseResult_T:
    case r.tag:
        when OK:  return f(r.value)
        when ERR: return r              # failure is propagated unchanged
```

### A complete Result-based parse pipeline

```python
def parse_positive(s: str) -> ParseResult_T:
    let n: ?int = parse_int(s)
    if n is None:
        return err(f"'{s}' is not an integer")
    if n < 0:
        return err(f"expected positive, got {n}")
    return ok(n)

def parse_ratio(num_s: str, den_s: str) -> ParseResult_T:
    let num_r: ParseResult_T = parse_positive(num_s)
    case num_r.tag:
        when ERR: return num_r          # propagate

    let den_r: ParseResult_T = parse_positive(den_s)
    case den_r.tag:
        when ERR: return den_r          # propagate

    if den_r.value == 0:
        return err("denominator cannot be zero")

    return ok(num_r.value * 100 // den_r.value)

# Usage
let ratio: ParseResult_T = parse_ratio("3", "4")
case ratio.tag:
    when OK:  print f"ratio: {ratio.value}%"
    when ERR: print f"error: {ratio.message}"
```

### Bind helper makes the chain cleaner

```python
def parse_ratio(num_s: str, den_s: str) -> ParseResult_T:
    let num_r: ParseResult_T = parse_positive(num_s)
    let den_r: ParseResult_T = bind_result(num_r, lambda _: parse_positive(den_s))
    return bind_result(den_r, lambda d:
        err("denominator cannot be zero") if d == 0
        else ok(num_r.value * 100 // d)
    )
```

### Conversion between `?T` and `Result_T`

`?T` and `Result_T` address different needs; convert at boundaries:

```python
def result_to_option(r: ParseResult_T) -> ?int:
    case r.tag:
        when OK:  return r.value
        when ERR: return None

def option_to_result(m: ?int, err_msg: str) -> ParseResult_T:
    if m is not None: return ok(m)
    return err(err_msg)
```

---

## 22. Choosing between `?T` and `Result_T`

| Criterion | `?T` (Maybe) | `Result_T` (Either) |
|-----------|-------------|---------------------|
| Why something is absent | Not recorded | Carried in `message` field |
| Caller must handle failure reason | No | Yes |
| Transpilation | `Option[T]` with full automation | Variant object, manual `case` |
| Compose with walrus | Yes | No (need explicit bind) |
| Auto-unwrap in `if` guard | Yes | No |
| Ideal for | Lookup, find, parse (expected absence) | Validation, I/O, pipelines that must report errors |

### Layered design — `?T` at the boundary, `Result_T` inside

A common pattern: use `?T` at the outer API (callers who just want
success-or-nothing) and `Result_T` internally (where error detail
matters for logging or user feedback):

```python
def parse_config_detailed(text: str) -> ParseResult_T:
    let raw: ?dict = parse_json(text)
    if raw is None:
        return err("config is not valid JSON")
    let host: ?str = raw.get("host")
    if host is None:
        return err("missing required key: host")
    let port: ?int = parse_int(raw.get("port") or "")
    if port is None:
        return err("port must be an integer")
    return ok_config(Config(host=host, port=port))

def parse_config(text: str) -> ?Config:
    let r: ParseResult_T = parse_config_detailed(text)
    case r.tag:
        when OK:  return r.config
        when ERR:
            log(f"config parse failed: {r.message}")
            return None
```

The detailed version carries error messages for diagnostics; the simple
version exposes a clean `?Config` interface to the rest of the program.
