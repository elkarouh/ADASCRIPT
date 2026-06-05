# Optional Types in Adascript

Adascript optional types express "a value of type `T`, or nothing." The
prefix `?` annotates any type to make it optional. The absent state is
written `None` — exactly as in Python — and the transpiler maps every
`None`-related construct to Nim's `Option[T]` machinery automatically.
You never write `some()`, `.get()`, `.isSome`, or `.isNone` by hand.

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
