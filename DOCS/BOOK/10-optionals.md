# Chapter 10 — Optional Types and the Maybe Monad

`?T` means "a `T`, or nothing". The absent value is written `None`, exactly
as in Python — and the transpiler maps the whole vocabulary (`None`,
`is None`, `is not None`, truthiness, `or`-defaults) onto Nim's `Option[T]`
machinery. You never write `some()`, `none()`, `.get()`, `.isSome` or
`.isNone` by hand.

```
?T   ──▶  Python:  T | None
     ──▶  Nim:     Option[T]
```

`?T` is shorthand for `T | None` — "a `T`, or nothing", said the way Python
says it. The two spellings are one type, and `None | T` is the same type
again: everything in this chapter holds for all three.
`EXAMPLES/test_optional_spelling.ady` runs them side by side:

```python
def half(n: int) -> int | None:
    if n % 2 == 1:
        return None
    return n // 2

let b: ?int = half(7)
```

`?T` is the short one, and the one this book uses. The long one shows what
the type *is*: the same `|` that, with a failure type in place of `None`,
means a value or a failure (10.12).

The first half of this chapter is the type: how to declare it, test it, and
get the value out. The second half (10.8 onward) is what `?T` *is* — the
Maybe monad — and the shapes that fall out of that: bind chains, the `do:`
block, fmap, traverse, and `T | !F` — a value or a *failure* — the sibling
for when "nothing" is not a good enough answer.

## 10.1 Declaring optionals

The `?` prefix goes in front of any type:

```python
var name:    ?str        # optional string
var count:   ?int  = None
var weights: ?[]float    # optional list of floats
var lookup:  ?{str}int   # optional dict
```

| Adascript | Python | Nim |
|---|---|---|
| `?int` | `int \| None` | `Option[int]` |
| `?str` | `str \| None` | `Option[string]` |
| `?[]str` | `list[str] \| None` | `Option[seq[string]]` |
| `[]?str` | `list[str \| None]` | `seq[Option[string]]` |
| `?{str}int` | `dict[str, int] \| None` | `Option[Table[string, int]]` |
| `?Token_T` (record) | `Token_T \| None` | `Option[Token_T]` |
| `?Node` (ref class) | `Node \| None` | `Node` — nil-able, no wrapper |

Assignment needs no ceremony in either direction:

```python
var result: ?int = None    # absent
result = 42                # present — some(42) on the Nim side
result = None              # absent again
```

One optional comes from the language rather than from an annotation: `$?NAME`
reads an environment variable as a `?str`, `None` when the variable is not in
the environment at all. `$NAME` stays a plain `str` and reads an unset
variable as `""`, so the two spellings answer different questions:

```python
if $?EDITOR:                   # is it set? "" counts as set
    print "EDITOR is set"
let editor: str = $?EDITOR or "vi"
```

## 10.2 Parameters, returns, and fields

An optional **parameter** with a `= None` default is an argument the caller
may omit:

```python
def greet(name: str, suffix: ?str = None) -> str:
    if suffix is not None:
        return f"Hello, {name} {suffix}!"
    return f"Hello, {name}!"
```

```nim
proc greet(name: string, suffix: Option[string] = none(string)): string =
    if suffix.isSome:
        return fmt"Hello, {name} {suffix.get()}!"
    return fmt"Hello, {name}!"
```

`rsync_time_machine.ady` threads a whole remote/local distinction through its
helpers this way — `ssh: ?SSH = None` means "run locally unless a connection
is passed":

```python
def run_cmd(cmd: str, ssh: ?SSH = None) -> CmdResult:
    let full_cmd: str = f"{ssh.cmd} '{cmd}'" if ssh is not None else cmd
    ...

def mkdir_p(path: str, ssh: ?SSH = None) -> None:
    run_cmd(f"mkdir -p -- '{path}'", ssh)

mkdir_p("/tmp/work")            # local
mkdir_p("/backup", ssh=conn)    # remote
```

An optional **return type** is the bread-and-butter case: the function either
produces a value or says it found none, without sentinels or exceptions.
Searching a trie in `phonecode.ady`:

```python
def find_exact_word(self, digits: []Digit_T) -> ?str:
    var node: TrieNode = self
    for digit in digits:
        if node.children[digit] is None:
            return None
        node = node.children[digit]
    if len(node.words) > 0:
        return node.words[0]
    return None
```

`graph.ady`'s path finder returns `?[]Node_T` — an optional list — and threads
the "not found" case up the recursion:

```python
def find_path(graph: Graph_T, start_node: Node_T, end_node: Node_T,
              path:[]Node_T=[]) -> ?[]Node_T:
    path = path + [start_node]
    if start_node == end_node:
        return path
    if start_node not in graph:
        return None
    for node in graph[start_node]:
        if node not in path:
            newpath : ?[]Node_T = find_path(graph, node, end_node, path)
            if newpath is not None:
              return newpath
    return None
```

**Fields** take `?T` too. `geo_server.ady` stores an optional predicate —
`None` in subclasses that override `__contains__` directly, present in
composed regions:

```python
class Region:
    var _predicate: ?(Point) -> bool

    def __init__(self, predicate: ?(Point) -> bool = None) -> None:
        self._predicate = predicate

    def __contains__(self, point: Point) -> bool:
        if self._predicate is None:
            raise NotImplementedError("Region subclass must implement __contains__")
        return self._predicate(point)
```

`c500.ady`'s lexer keeps one token of look-ahead the same way
(`var lookahead: ?Token_T`), and a record field is no different:

```python
type Config_T is record:
    host:     str
    port:     int
    id_rsa:   ?str       # SSH key path — may not be needed
    log_file: ?str       # optional logging destination
```

## 10.3 Testing, and the auto-unwrap that follows

Write `is None` / `is not None` exactly as in Python; `== None` and `!= None`
mean the same thing. They become `.isNone` / `.isSome` in Nim — or `== nil`
for a ref type (10.7).

The part worth internalising is what happens *after* the test. Inside an
`is not None` guard the optional is used **directly**: the transpiler inserts
the `.get()`.

```python
let exact_match: ?str = trie.find_exact_word(test_digits)
if exact_match is not None:
    print(f"Exact match for digits 3,5: {exact_match}")
else:
    print("No exact match for digits 3,5")
```

Field access unwraps in the right place too, and nested guards each add to
the set:

```python
var tok: ?Token_T = lexer.try_next(TK_IDENT)

if tok is not None:
    let name: str = tok.content     # tok.get().content in Nim
    let line: int = tok.line        # tok.get().line in Nim
    register(name, line)
```

An **early-return guard** establishes the same thing for everything that
follows it, which is what makes the flat style of 10.9 work:

```python
def bump(raw: str) -> ?int:
    let v: ?int = parse_int(raw)
    if v is None:
        return None
    return v + 1            # v is a plain int from here on
```

```nim
proc bump(raw: string): Option[int] =
    let v: Option[int] = parse_int(raw)
    if v.isNone:
        return none(int)
    return some(v.get() + 1)
```

Any exit works — `return`, `break`, `continue`, `raise`, `quit` — as long as
the guard body leaves the block and has no `else`.

The guard may be written as a statement modifier, which is the same thing on
one line and reads best in a loop:

```python
for name in listing:
    let bt: ?BuildType = build_type_from(name)
    continue if bt is None
    builds.append((name: name, btype: bt))   # bt is a plain BuildType here
```

What the guard establishes holds everywhere after it, not only in the
positions that look like tests: a `let`, a tuple constructor, a subscript and
a tick attribute all take the plain name.

Do **not** write `.get()` yourself after a guard. The name already *is* the
value there, so the call lands on the unwrapped value rather than on the
optional, and Adascript reads `.get()` on a non-optional as a table lookup —
`bt.get()` becomes `bt.get().getOrDefault()` in Nim, which does not compile:

```python
continue if bt is None
builds.append((name: name, btype: bt.get()))   # wrong: a second unwrap
```

Outside a guard `.get()` is still the explicit unwrap, and still means what
it says.

## 10.4 Defaults, truthiness, and the walrus

`x or default` reads "the value if present, otherwise this":

```python
def connect(host: str, port: ?int = None) -> None:
    let p: int = port or 5432
```

```nim
proc connect(host: string, port: Option[int] = none(int)): void =
    let p: int = port.get(5432)
```

Note what this is *not*: Python's `or` asks about the wrapped value, so a
`?str` holding `""` would fall through to the default. Adascript emits the
presence test instead (`port if port is not None else 5432` on the Python
backend), keeping `""` — and the default stays lazy, so a default that calls
something is evaluated only when the optional is absent. Fallbacks chain:

```python
let colour: str = env_colour or config_colour or "white"
```

An optional used as a **condition** is tested for presence, not for the
truthiness of what it holds — including a bare call to a `?T`-returning
function:

```python
var result: ?str = find_result()

if result:                             # if result.isSome
    use(result)

if find_backup_marker(folder, ssh):    # returns ?str -> .isSome
    check_dest_is_backup_folder(...)
```

The **walrus** combines the call, the test and the binding. In an `if`, that
is one fallible step; in a `while`, it is "loop until absent":

```python
if n := parse_int(text):
    print "parsed:", n              # n is a plain int here

while token := lexer.try_next(TK_IDENT):
    register(token.content, token.line)
```

```nim
var n = parse_int(text)
if n.isSome:
    echo("parsed:", " ", n.get())

while true:
    let token = lexer.try_next(TK_IDENT)
    if token.isNone: break
    register(token.get().content, token.get().line)
```

## 10.5 Wrapping is automatic

You never write `some(x)` or `none(T)`. The transpiler inserts them from the
type context — on assignment to a `?T` variable, on `return` from a `-> ?T`
function, and at a call site whose parameter is `?T`:

```python
var best: ?str = None
for candidate in candidates:
    if score(candidate) > threshold:
        best = candidate            # best = some(candidate)
        break

def lookup(key: str) -> ?int:
    if key in table:
        return table[key]           # return some(table[key])
    return None                     # return none(int)

log_cmd("backup started", my_ssh)   # my_ssh: SSH  -> some(my_ssh)
log_cmd("done")                     # no ssh       -> none(SSH)
```

An argument that is *already* optional — a variable of type `?T`, or a call
to a function declared `-> ?T` — is passed through untouched rather than
wrapped a second time.

One asymmetry to know about: printing an optional directly shows Python's
`42` and Nim's `some(42)`. Print the unwrapped value (inside a guard, or via
`or`) when the output matters on both backends.

## 10.6 Optionals in patterns

`None` is a legal pattern, and on an optional subject it is a presence test:

```python
def show(v: ?int) -> str:
    case v:
        when None:
            return "nothing"
        when others:
            return "something"
```

```nim
proc show(v: Option[int]): string =
    if v.isNone:
        return "nothing"
    else:
        return "something"
```

## 10.7 Ref types are already nullable

A class that is `@virtual`, or that inherits from another class, is a **ref
type** in Nim: heap-allocated and nil-able on its own. `?RefClass` therefore
stays `RefClass` with no `Option` wrapper, and `is None` becomes `== nil`:

```python
@virtual
class Node:
    var value: int
    var next:  ?Node     # recursive nullable ref — no Option in Nim
```

```nim
type Node = ref object of RootObj
    value: int
    next:  Node          # ref, already nullable
```

This is why `phonecode.ady`'s trie children can be `None` without any
`Option` appearing in the generated code. The rule:

> Value types (records, named tuples, primitives) → `Option[T]`.
> Ref types (`@virtual` classes and their subclasses) → nil-able already.

Adding `?` to a ref class is harmless but pointless; `??T` is not a type at
all.

---

The rest of this chapter is about composing optionals. `?T` is the Maybe
monad, and its three operations already have Adascript spellings.

## 10.8 Unit, bind, fmap

**Unit** — lift a plain value into the optional context. This is the
automatic wrapping of 10.5: `return x` inside a `-> ?T` function *is* unit.

**Bind** — apply a step that may itself fail (`T -> ?U`) to an optional,
propagating absence without running the step. The guard forms of 10.3 are
bind written out:

```python
def bind_int(m: ?int, f: (int) -> ?int) -> ?int:
    if m is not None:
        return f(m)      # f applied to the unwrapped value
    return None          # absence propagated
```

**Fmap** — apply a step that cannot fail (`T -> U`), preserving presence:

```python
def fmap_int(m: ?int, f: (int) -> int) -> ?int:
    if m is not None:
        return f(m)
    return None

let doubled: ?int = fmap_int(parse_int(text), lambda v: v * 2)
```

```nim
proc fmap_int(m: Option[int], f: proc(a0: int): int): Option[int] =
    if m.isSome:
        return some(f(m.get()))
    return none(int)
```

For a one-off transform, the conditional expression says the same thing
without a helper:

```python
let score: ?int = int(raw_score) if raw_score is not None else None
```

The monad laws hold — left identity, right identity, associativity — which
in practice means bind chains can be regrouped or factored into helpers
without changing behaviour.

## 10.9 Bind chains: the railroad

A chain of fallible steps wants the happy path to read straight down the
page, with the first failure diverting everything after it. Nesting one `if`
per step does not do that:

```python
def load_config(path: str) -> ?Config_T:
    let text: ?str = read_file_safe(path)
    if text is not None:
        let raw: ?{str}str = parse_json(text)
        if raw is not None:
            let host: ?str = raw.get("host")
            if host is not None:
                ...
    return None
```

The **flat guard** style is the same monad without the pyramid. Each
`if x is None: return None` is one bind step, and the auto-unwrap of 10.3
means the following lines use plain values:

```python
def load_config(path: str) -> ?Config_T:
    let text: ?str = read_file_safe(path)
    if text is None: return None

    let raw: ?{str}str = parse_json(text)
    if raw is None: return None

    let host: ?str = raw.get("host")
    if host is None: return None

    let port: ?int = parse_int(raw.get("port") or "")
    if port is None: return None

    return Config_T(host, port)
```

The flat style is also where you annotate *which* step failed, since each
guard has a body of its own:

```python
    let raw: ?{str}str = parse_json(text)
    if raw is None:
        log(f"invalid JSON in: {path}")
        return None
```

## 10.10 The `do:` block

When there is nothing to say about the individual failures, the `do:` block
is do-notation: `x <- expr` unwraps an optional, or **short-circuits the
whole enclosing function to `None`**. `EXAMPLES/test_do_block.ady` is the
spec:

```python
def try_parse_int(s: str) -> ?int:
    if len(s) == 0: return None
    for c in s:
        if not (c >= '0' and c <= '9'): return None
    return int(s)

def safe_div(a: int, b: int) -> ?int:
    if b == 0: return None
    return a // b

def clamp_positive(n: int) -> ?int:
    if n <= 0: return None
    return n

def compute(raw_a: str, raw_b: str) -> ?int:
    """Parse two strings and return their quotient, or None on any failure."""
    do:
        a <- try_parse_int(raw_a)
        b <- try_parse_int(raw_b)
        q <- safe_div(a, b)
        r <- clamp_positive(q)
    return r
```

After each `<-`, the bound name is a plain (non-optional) value — `a` and `b`
go straight into `safe_div` — and every binding stays in scope after the
block, which is how `return r` works. The test file walks each failure mode:

```python
let r1: ?int = compute("20", "4")    # 5
let r2: ?int = compute("abc", "4")   # None — first step fails
let r3: ?int = compute("20", "0")    # None — middle step fails
let r4: ?int = compute("0", "4")     # None — last step fails
```

The rules are short:

- every expression to the right of `<-` must return `?T`;
- the enclosing function must return `?R`, since that is what a failing step
  returns;
- bindings are plain `let`s of type `T`, in scope for the rest of the
  function.

The same block chains `T | !F` steps, F a failure type, in a function
that returns one; 10.12 has the details. A line without `x <-` is a *bare step*: it
is checked like any other and binds nothing.

Three spellings of one pattern, then:

| Style | Best for |
|-------|----------|
| Walrus `if x := f():` | one or two steps |
| Flat guard `if x is None: return None` | any length, and when each failure needs its own message |
| `do:` block | three or more steps with nothing to say about individual failures |

## 10.11 Sequence and traverse

**Sequence** turns a list of optionals into an optional list: if any element
is absent, the whole thing is. **Traverse** does the same while applying a
fallible function, in one pass:

```python
def traverse_parse(tokens: []str) -> ?[]int:
    var acc: []int = []
    for tok in tokens:
        let v: ?int = parse_int(tok)
        if v is None:
            return None          # bad token → fail the whole parse
        acc.append(v)
    return acc

let good: ?[]int = traverse_parse(["1", "42", "7"])   # [1, 42, 7]
let bad:  ?[]int = traverse_parse(["1", "??", "7"])   # None
```

All-or-nothing is a choice, not a default. When you want the successes and
nothing else, filter instead — that is not a monadic operation and should not
look like one:

```python
var loose: []int = []
for t in tokens:
    let v: ?int = parse_int(t)
    if v is not None:
        loose.append(v)
```

## 10.12 When "nothing" is not enough: failures

`?T` records absence but not its reason. When the caller needs the reason —
validation, I/O, a shell command that failed, anything a user will read —
the function returns **either** its value **or** a failure that says why
there is none:

```python
def read_number(s: str) -> int | !Failure_T:
```

This is railway-oriented programming. Every step runs on the value track,
and the first failure switches to the failure track and rides it, unchanged,
to the one place that decides what to tell the user. Code in this style has
five parts, in this order.

```
int | !Failure_T   ──▶  Python:  int | Failure_T    (the int or the Failure_T itself)
                  ──▶  Nim:     Result[int, Failure_T]   (stdlib.nim's variant object)
```

### 1. Declare what a failure looks like

A failure is an ordinary record. An enum says *which* failure; the
fields say what the report needs. One failure type is usually enough for a
whole program. `EXAMPLES/test_result.ady`:

```python
type ErrKind_T is enum BAD_NUMBER, DIVIDE_BY_ZERO, NOT_POSITIVE

type Failure_T is record:
    kind:   ErrKind_T    # which failure
    detail: str          # what it needs to say so

def fail(kind: ErrKind_T, detail: str) -> Failure_T:
    return Failure_T(kind=kind, detail=detail)
```

`int | !Failure_T` is a *union* (4.4) — a value that is one of its members —
and the `!` is what makes it a value-or-failure: it marks the member a
`do:` block passes on, where the reader sees it. `int | !Failure_T` and
`!Failure_T | int` are the same type: the mark, not the position, says
which member is the failure. A type marked `!` in one union is marked in
every union it is in — unmarked, it is refused, since it would read as a
value. A union has at most one failure; any
number of value members may go with it — `int | str | !Failure_T`. (`T | None`
is `?T` written out — `?T` is its shorthand — so `None` there means absence,
not a failure.) Only a record can be a failure: it has to say what went wrong, and on
the Python backend it has to be a class of its own, since that is all that
tells it from the value.

### Forgetting the `!`

The `!` is the only thing that makes a record a failure, so leaving it out
changes what the type means. What happens depends on where it is missing.

**Marked somewhere else, missing here.** Once `Failure_T` is marked `!` in
one union, the transpiler knows it is a failure, and refuses every union
that mentions it without the mark:

```text
'int | Failure_T': Failure_T is a failure type -- mark it `!Failure_T`,
which shows the member a do: block passes on
```

This is the common case, and the harmless one: the program does not
build until the mark is there.

**Missing everywhere.** If no union in the program marks `Failure_T`,
nothing says it is a failure, and `int | Failure_T` is a *plain union*
(4.4): an int or a Failure_T, two values of equal standing. It still
builds, and `return Failure_T(...)` still returns one — but the protection
is gone:

- a `do:` step on it is refused, since there is nothing to pass on —
  the message ends *if one member is, mark it `!`*;
- a call whose result nobody takes is **not** refused: the failure is
  dropped without a word;
- a caller that uses the result without testing it gets an error that
  says nothing about failures — a type mismatch from Nim, a `TypeError`
  from Python *when it runs*.

**Missing from `None | Failure_T`.** This is the one to watch. `None |
Failure_T` without the mark is not a failure at all: `None` with one other
type is `?T` (10.1), so it reads as `?Failure_T` — *maybe* a Failure_T.
A function declared that way returns its failure as an optional value,
and optional values may be ignored:

```python
def check(n: int) -> None | Failure_T:      # meant: None | !Failure_T
    return Failure_T(message="negative") if n < 0

check(-1)             # accepted: the failure is dropped
print "went on"       # and the program goes on
```

Nothing refuses it, on either backend, unless `Failure_T` is marked `!`
somewhere else in the program — which is one more reason to give a
program a single failure type (step 1), used, and marked, everywhere.

### 2. Return the value, or return a failure

Declare the function `-> T | !Failure_T` and return whichever applies. There
is nothing to wrap: a value whose type is the failure type is the failure,
anything else is the value.

```python
def read_number(s: str) -> int | !Failure_T:
    if len(s) == 0:
        return fail(BAD_NUMBER, "empty")
    for c in s:
        if not (c >= '0' and c <= '9'):
            return fail(BAD_NUMBER, f"'{s}' is not a number")
    return int(s)

def divide(a: int, b: int) -> int | !Failure_T:
    if b == 0:
        return fail(DIVIDE_BY_ZERO, f"{a} / 0")
    return a // b
```

`fail`, from step 1, is an ordinary function that builds the record: a
failure is returned like any other value.

A step that changes something and has nothing to give back returns
`None | !Failure_T`. A bare `return`, and falling off the end, are success.
From `TOOLS/RSYNC_TIME_MACHINE/rsync_time_machine.ady`, where a local `mkdir` reports its own
exit status and a remote one goes through `run_checked`:

```python
def mkdir_p(path: Path, ssh: ?SSH = None) -> None | !Failure_T:
    if ssh is None:
        let r = shell: mkdir -p -- {!path}
        return checked(r, f"mkdir -p -- '{path}'")
    do:
        run_checked(f"mkdir -p -- '{path}'", ssh)
```

Returning a call of another function with the same `T | !Failure_T` passes
its result on as it is — the `return checked(...)` above. What a call to
such a function may not do is stand alone as a statement: `mkdir_p(dest)`
on a line of its own would throw its failure away, and it does not compile.
Its result has to be taken — by a `do:` step (4 below), a `let` and a test
(3), or a `return`. The one exception is a call standing last in a function
that returns the same `T | !Failure_T`: that call *is* the function's value. Declarations and
assignments work the same way: `var r: str | !Failure_T = "seven"` holds a
str, and `r = fail(BAD_NUMBER, "gone")` then holds the failure.

### 3. Test before you use

The value cannot be used straight away, because it might be the failure.
Ask with `is`. The test *narrows* the name, exactly as `x is None` narrows a
`?T` (10.3): inside the test it is the failure, and past a guard that leaves
— or in the `else` — it is the value, with nothing to unwrap.

```python
def describe(r: int | !Failure_T) -> str:
    if r is Failure_T:
        case r.kind:
            when BAD_NUMBER:     return f"bad number: {r.detail}"
            when DIVIDE_BY_ZERO: return f"divide by zero: {r.detail}"
            when NOT_POSITIVE:   return f"not positive: {r.detail}"
    return f"ok {r}"                        # r is the int from here on
```

`r is not Failure_T` asks the other way round, `r is int` names the value
side, and for a `None | !Failure_T`, `r is None` means it succeeded. Using the
value with no test at all is a compile error on Nim, as it is for `?T`.

When both sides need code of their own, a `case` says it more directly: a
`when` names a member, the name is that member inside the branch, and the
case must cover every member — or say `when others:` — so a forgotten one
does not compile:

```python
def sign_of(raw: str) -> str:
    let n: int | !Failure_T = read_number(raw)
    case n:
        when Failure_T:
            return f"no sign: {n.detail}"   # n is the failure here
        when int:
            return "zero" if n == 0 else "positive"   # and the int here
```

The subject is a name — bind a call with `let` first — and a branch cannot
carry a guard: test inside it instead.

### 4. Pass failures on with `do:`

Most functions that call fallible ones should not handle the failure — only
pass it up. That is the `do:` block of 10.10: `x <- step` binds the step's
value, or returns its failure from the whole function, as it is. A line
without `x <-` is a step with no value, checked and nothing else:

```python
def ratio(raw_a: str, raw_b: str) -> int | !Failure_T:
    do:
        a <- read_number(raw_a)
        b <- read_number(raw_b)
        q <- divide(a, b)
        check_positive(q)
    return q
```

The function containing a `do:` must itself return `... | !Failure_T` —
that is where a failure goes. A `T | !Failure_T` step in a function returning
`?T`, or nothing, is refused.

A step that fails some other way — a `?T` that may be absent, a function
with a different failure type, a shell command — ends in `else`, followed by
the failure to return in its place. Inside the `else`, the step's name is
the step's own failure, just as a test narrows it. From `test_result.ady`:

```python
def shout(words: {str}str, key: str) -> str | !Failure_T:
    do:
        w <- find_word(words, key) else fail(BAD_NUMBER, f"no word for {key}")
        out <- shell: echo {w} | tr a-z A-Z else cmd_failed(out)
        shell: test -n "{w}" else fail(NOT_POSITIVE, "an empty word")
    return out.strip()
```

The first step is a `?str`: absence alone is no failure, so without the
`else` the step is refused. The second and third are shell commands, which
fail with the built-in `ShellFailure_T` (see *Shell commands* below): the
`else` turns that into this program's `Failure_T` — `cmd_failed(out)`
reads the failed command's details off `out`. A step whose failure type is
the function's own needs no `else`; any other is refused without one. In a
`do:` step a shell command ends at `else`: a command that needs the word
quotes it. A chain of steps that must all succeed, in order, is
one `do:` block; `rsync_time_machine.ady` ends a backup with one, so that its
lock file is removed only once the `latest` link is in place:

```python
    do:
        rm_file(dest_f / "latest", dest_is_ssh(ssh))
        ln_s(Path(dest.name), dest_f / "latest", dest_is_ssh(ssh))
        rm_file(inprogress_file, ssh)
```

### 5. Report once, at the top

Low-level functions only *return* failures. One place at the top of the
program decides what to print and which exit status to give. A `case` over
the failure's kind is exhaustive, so a new kind of failure that nobody
reports is a compile error rather than a silent gap:

```python
def report(f: Failure_T) -> None:
    """What went wrong, said once, here, for every step that can fail."""
    case f.kind:
        when CMD_FAILED:
            log(f"Command failed: {f.detail}", ERROR)
            if f.stderr:
                log(f.stderr, ERROR)
        ...

def main() -> None:
    ...
    let outcome: None | !Failure_T = backup(...)
    if outcome is Failure_T:
        report(outcome)
        quit(1)
```

### Shell commands

A shell command fails too — with the built-in failure record
`ShellFailure_T`, whose fields are the `command` that ran, the exit `code`
and its `stderr`. Declare the target's type and a `shell:` statement gives
you the output or the failure, instead of a result you have to remember to
check:

```python
let hi: str | !ShellFailure_T = shell: echo hi
if hi is str:
    print f"said {hi.strip()}"
let oops: str | !ShellFailure_T = shell: echo oops >&2; exit 3
if oops is ShellFailure_T:
    print f"exit {oops.code}, stderr {oops.stderr.strip()}"
let quiet: None | !ShellFailure_T = shell: true
```

`str` is the output, `[]str` its lines (`shellLines:`), `None` nothing — a
command run only for what it does. Every `shell:` option still applies. In
a `do:` block, `out <- shell: cmd` binds the output and a bare `shell: cmd`
is a step; in a function whose own failure type is `ShellFailure_T` they
need no `else`. A program with its own failure type converts once, in one
small function, and names it in each step's `else` —
`rsync_time_machine.ady`:

```python
def cmd_failed(f: ShellFailure_T) -> Failure_T:
    """A local command's failure -- the built-in ShellFailure_T a shell:
    step fails with -- as this program's: the `else` of the steps below."""
    return failure(CMD_FAILED, f.command, f.stderr.strip())

def mkdir_p(path: Path, ssh: ?SSH = None) -> None | !Failure_T:
    if ssh is None:
        do:
            r <- shell: mkdir -p -- {!path} else cmd_failed(r)
        return
```

### Every failure, not the first

A `do:` block stops at the first failure — right for a pipeline, wrong for
validation, where the user wants every bad field at once. That is not a
bind chain and should not look like one: collect the failures in a loop, as
10.11 collects successes, and return them together in a failure of their
own:

```python
type Problems_T is record:
    bad: []str

def parse_all(tokens: []str) -> []int | !Problems_T:
    """Validation that reports every bad token, not only the first one."""
    var good: []int = []
    var bad: []str = []
    for t in tokens:
        let p: int | !Failure_T = read_number(t)
        if p is Failure_T:
            bad.append(p.detail)
        else:
            good.append(p)
    if len(bad) > 0:
        return Problems_T(bad=bad)
    return good
```

### Rules of thumb

| Situation | Write |
|---|---|
| Something may be absent, and nobody needs to know why | `?T`, tested with `is None` |
| The caller needs to know *why* it failed | `T \| !Failure_T` |
| A step that only changes something | `None \| !Failure_T` |
| Passing a failure upward | a `do:` block, `x <- f()` |
| Deciding what the user sees, and the exit status | once, at the top: `case` over the kind |
| A bug that should never happen | `raise` or `die` — not a failure |
| A query command — `find`, `test -e`, `ps \| grep` | not a failure: its exit status is its answer |

The transpiler refuses:

- a failure dropped: a call returning `T | !Failure_T` standing alone as a
  statement, its result taken by nobody;
- a `do:` step that fails some other way — a `?T`, another failure type, a
  shell command in a function that is not `... | !ShellFailure_T` — without
  an `else` saying what failure it becomes;
- a `case` over a union that leaves a member out and has no `when others:`;
- a union with two failure members (`!A_T | !B_T`), or with members nothing
  can tell apart at run time (`[]int | []str`, 4.4);
- `!` on anything but a record (`int | !str`);
- a failure type left unmarked in a union (`int | Failure_T`, where
  Failure_T is marked `!` elsewhere) — it would read as a value;
- a `T | !Failure_T` step in the `do:` block of a function that cannot return
  the failure;
- a `do:` step on a plain union (`int | Failure_T` with the `!` forgotten
  everywhere): nothing in it is a failure to pass on.

**Which to use.**

| | `?T` (Maybe) | `T \| !F` (Either) |
|---|---|---|
| Why it failed | not recorded | the failure value |
| Returning | the value, or `None` | the value, or the failure |
| Asking | `x is None` | `r is F` |
| Narrowing after a guard | yes | yes |
| `do:` chains | yes | yes |
| `or`-default, walrus | yes | no |
| Ideal for | lookup, find, parse | validation, I/O, anything reported to a user |

## 10.13 When *not* to use `?T`

The examples are as instructive about the negative space:

- **Container "not found"** — `dijkstra.ady` initialises unreached nodes to
  `Inf` rather than typing them `?Distance_T`, because arithmetic on
  distances must stay unconditional inside the hot loop. An infinity compares
  and adds like any other float; an optional would have to be unwrapped at
  every comparison. (A *magic* sentinel like `1e6` would be the bad version
  of this: it is a ceiling a large graph can exceed, where `Inf` cannot.)
- **Contradiction in a solver** — `sudoku.ady` returns the empty dict `{:}`
  rather than `?{str}str`, because the empty dict is already falsy and the
  algorithm tests `if not values:` a dozen times.
- **A default is available** — use `.get(key, default)` (see
  `self.G.get(curr, [])` in the optimiser subclasses) instead of an optional
  lookup followed by a branch.
- **A ref type** — it is nil-able already (10.7).

And the positive rule, unchanged since the start of the chapter: reach for
`?T` when *absence is meaningful at the interface* — search results, parse
results, configuration that may be missing — and prefer it over a sentinel
value every time. `-1` for "not found" is a convention the caller has to
know; `?int` is one the compiler enforces.

## 10.14 Reference

| Adascript | Python | Nim |
|---|---|---|
| `?T` (shorthand for `T \| None`) | `T \| None` | `Option[T]` |
| `var x: ?T = None` | `x: T \| None = None` | `var x: Option[T] = none(T)` |
| `x = value` (x is `?T`) | `x = value` | `x = some(value)` |
| `return value` (in `-> ?T`) | `return value` | `return some(value)` |
| `return None` (in `-> ?T`) | `return None` | `return none(T)` |
| `x is None` / `x == None` | unchanged | `x.isNone` |
| `x is not None` / `x != None` | unchanged | `x.isSome` |
| `if x is not None: use(x)` | unchanged | `if x.isSome: use(x.get())` |
| `if x is None: return` then `use(x)` | unchanged | `if x.isNone: return` then `use(x.get())` |
| `x or default` | `x if x is not None else default` | `x.get(default)` |
| `if x:` (x is `?T`) | unchanged | `if x.isSome:` |
| `if m := f():` (f returns `?T`) | unchanged | `var m = f()` + `if m.isSome:` |
| `while m := f():` | unchanged | `while true: let m = f(); if m.isNone: break` |
| `f(plain_value)` (param is `?T`) | unchanged | `f(some(plain_value))` |
| `when None:` on a `?T` | `case None:` | `if subject.isNone:` |
| `$?NAME` | `os.environ.get("NAME")` | `adascriptEnvOpt("NAME")` — an `Option[string]` |
| `?RefClass` | `RefClass \| None` | `RefClass` (nil-able) |
| `do: x <- f()` | guard chain | `if …isNone: return none(R)` per step |
| `type F is record:` (a failure where marked `!F`) | a dataclass | an object |
| `T \| !F` (F a failure) | `T \| F` | `Result[T, F]` (stdlib.nim), either order |
| `None \| !F` | `None \| F` | `Result[void, F]` |
| `return v` (in `-> T \| !F`) | unchanged | `return Result[T, F].ok(v)`, or `.err(v)` when v is an F |
| `r is F` / `r is not F` | `_is_a(r, F)` (an isinstance) | `r.is_err` / `r.is_ok` |
| `r` after `if r is F: return` | unchanged | `r.value` |
| `case r:` / `when F:` / `when T:` | `if _is_a(r, F):` / `elif not _is_a(r, F):` | `if r.is_err:` / `elif r.is_ok:` |
| `let o: str \| !ShellFailure_T = shell: cmd` | the output, or `ShellFailure_T(command, code, stderr)` | `Result[string, ShellFailure_T]` |
| `do: x <- step else e` | `if _is_a(x, F2): return e` | `if t.is_err: (let x = t.error) return R.err(e)` |
| `do: x <- f()` (in `-> T \| !F`) | `if _is_a(x, F): return x` per step | `if t.is_err: return R.err(t.error)` per step |

---

*Next: [Chapter 11 — Shell Integration: Adascript as a Better Bash](11-shell-and-scripting.md)*
