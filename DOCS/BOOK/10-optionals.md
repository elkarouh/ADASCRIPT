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

The first half of this chapter is the type: how to declare it, test it, and
get the value out. The second half (10.8 onward) is what `?T` *is* — the
Maybe monad — and the shapes that fall out of that: bind chains, the `do:`
block, fmap, traverse, and a `Result_T` sibling for when "nothing" is not a
good enough answer.

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
    var _predicate: ?[(Point,)]bool

    def __init__(self, predicate: ?[(Point,)]bool = None) -> None:
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

Calling `.get()` yourself is not wrong, just noise. Prefer the plain name.

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
def bind_int(m: ?int, f: [(int,)]?int) -> ?int:
    if m is not None:
        return f(m)      # f applied to the unwrapped value
    return None          # absence propagated
```

**Fmap** — apply a step that cannot fail (`T -> U`), preserving presence:

```python
def fmap_int(m: ?int, f: [(int,)]int) -> ?int:
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

## 10.12 When "nothing" is not enough: `Result_T`

`?T` records absence but not its reason. When the caller needs the reason —
validation, I/O, anything user-facing — pair the value with a message in a
variant record. This is the Either monad, and Adascript spells it as a
discriminated record (Chapter 4):

```python
type ResultTag_T is enum OK, ERR

type ParseResult_T (tag: ResultTag_T) is record:
    case tag is
        when OK:
            value: int
        when ERR:
            message: str

def ok(value: int) -> ParseResult_T:
    return ParseResult_T(tag=OK, value=value)

def err(msg: str) -> ParseResult_T:
    return ParseResult_T(tag=ERR, message=msg)
```

Bind is a `case` on the tag: apply the next step on success, pass the failure
through untouched.

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
        when others: pass

    let den_r: ParseResult_T = parse_positive(den_s)
    case den_r.tag:
        when ERR: return den_r
        when others: pass

    if den_r.value == 0:
        return err("denominator cannot be zero")
    return ok(num_r.value * 100 // den_r.value)
```

Convert at the boundaries — detail inside, plain absence at the API edge:

```python
def result_to_option(r: ParseResult_T) -> ?int:
    case r.tag:
        when OK:  return r.value
        when ERR: return None
```

| | `?T` (Maybe) | `Result_T` (Either) |
|---|---|---|
| Why it failed | not recorded | carried in the record |
| Transpilation | `Option[T]`, fully automatic | variant object, explicit `case` |
| Walrus, `or`-default, auto-unwrap | yes | no |
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
| `?T` | `T \| None` | `Option[T]` |
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

---

*Next: [Chapter 11 — Shell Integration: Adascript as a Better Bash](11-shell-and-scripting.md)*
