# Adascript Language Reference for LLMs

## What is Adascript?

Adascript (`.ady` files) is a statically-typed superset of Python 3. Every valid Python 3 file is valid Adascript. It transpiles to both **Python 3** and **Nim**. Features are purely additive — you write one source file and target either ecosystem.

```
source.ady  ──▶  python3 TO_PYTHON/py2py.py source.ady  ──▶  Python 3
            ──▶  python3 TO_NIM/py2nim.py   source.ady  ──▶  Nim
```

Key design goals: Ada-style type safety, Python ergonomics, Nim performance.

---

## Running Adascript

```bash
# Transpile to Python 3 and run
python3 TO_PYTHON/py2py.py -c source.ady

# Transpile to Nim and compile+run (default)
python3 TO_NIM/py2nim.py source.ady

# Transpile only (write .nim file)
python3 TO_NIM/py2nim.py -t source.ady

# Optimised Nim build
python3 TO_NIM/py2nim.py c -d:release source.ady
```

Shebang + per-file Nim options (first two lines only):
```adascript
#!/usr/bin/env py2nim
#ady2nim-args c -d:release
```

Build artifacts go into `~/.cache/hparsec/cache-<HASH>/` — source directories stay clean. Builds are incremental.

---

## Type Annotations (Left-to-Right)

Adascript uses prefix notation for containers. `[]int` = "list of int".

| Adascript | Python | Nim |
|-----------|--------|-----|
| `[]T` | `list[T]` | `seq[T]` |
| `[N]T` | `tuple[T, ...]` (fixed-size) | `array[N, T]` |
| `[*]T` | `Sequence[T]` | `openArray[T]` |
| `[E]T` | `dict[E, T]` | `array[E, T]` (enum-indexed) |
| `{K}V` | `dict[K, V]` | `Table[K, V]` |
| `{}T` | `set[T]` | `HashSet[T]` or `set[T]` (ordinal) |
| `?T` | `T \| None` | `Option[T]` |
| `(T, U)` | `tuple[T, U]` | `(T, U)` |
| `[(T, U)]R` | `Callable[[T,U], R]` | `proc(a0: T, a1: U): R` |

Types compose: `{Node_T}[]Node_T` = dict mapping node to list of nodes.

**Empty literals** — resolves Python's `{}` ambiguity:
```adascript
var counts:  {str}int = {:}    # empty dict  → Python: {}   Nim: initTable()
var visited: {}str    = {}     # empty set   → Python: set() Nim: initHashSet()
```

**Open arrays** (`[*]T`) are only valid in parameter/return annotations, not variable declarations. They accept both `[]T` (seq) and `[N]T` (fixed array) at call sites.

---

## Variable Declarations

```adascript
var   counter: int   = 0        # mutable
let   name:    str   = "Alice"  # immutable
const MAX:     int   = 1_000    # compile-time constant

var result: []int               # declaration without init (zero-initialised in Nim)
```

**Tuple unpacking:**
```adascript
let (x, y) = point              # explicit let destructuring
var (a, b) = (1, 2)             # explicit var destructuring
a, b = some_func()              # implicit let tuple unpack (bare comma = implicit let)
```

---

## Enums

```adascript
type Door_T  is enum Door1, Door2, Door3
type Priority is enum LOW, MED, HIGH
type Digit_T  is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are valid assignment keywords.

**Python output:** `class Door_T(Enum): Door1 = auto(); ...`
**Nim output:** `type Door_T = enum Door1, Door2, Door3`

Calling an enum type with a string argument emits `parseEnum` in Nim:
```adascript
def parse_state(s: str) -> State:
    try:
        State(s.replace("-", "_"))
    except:
        ACTIVE
```

---

## Named Tuples

```adascript
type Point is tuple:
    x: float
    y: float

p = Point(x: 1.0, y: 2.5)       # construct with (field: value) syntax
```

**Python output:** `Point(x=1.0, y=2.5)` via `NamedTuple`
**Nim output:** `(x: 1.0, y: 2.5)` structural tuple literal

Named tuple literals work inside collections and as function arguments:
```adascript
fringe.push((stage: STAGE1, budget: float(CAPITAL)))
```

---

## Records and Variant Records

**Record** (dataclass):
```adascript
type Person is record:
    name: str
    age:  int
```

**Python output:** `@dataclass class Person: ...`
**Nim output:** `type Person = object`

**Discriminated (variant) record** — fields depend on a tag:
```adascript
type Shape_Kind is enum Circle, Rectangle

type Shape (Kind : Shape_Kind) is record:
    case Kind is
        when Circle:
            Radius : float
        when Rectangle:
            Width  : float
            Height : float
```

**Nim output:** native variant object with `case Kind: Shape_Kind`
**Python output:** flattened `@dataclass` with `None` defaults for unused fields

---

## Subranges

```adascript
type SmallInt is 0 .. 255     # inclusive, both ends
type Index    is 0 ..< 10     # exclusive upper bound (0–9)
type Age      is int range 0..100    # synonym form

type Probability is float range 0.0 .. 1.0   # float subrange
```

**Python output:** `int` or `float` (type alias)
**Nim output:** native range type with compile-time bounds checking. Float subranges emit `assert` after every assignment.

Tick attributes `T'First` and `T'Last` give the bounds of a subrange.

---

## Tick Attributes

Ada-style `'` attributes. Tokeniser converts `Type'Attr` → `Type__tick__Attr` before parsing, so Python's lexer is unaffected.

| Expression | Meaning |
|------------|---------|
| `E'First` | First member of enum `E` |
| `E'Last` | Last member of enum `E` |
| `E'Range` | Full ordinal set of enum `E` |
| `expr'Next` | Successor |
| `expr'Prev` | Predecessor |
| `expr'Choice` | Random element from enum, set, or range |
| `expr'Image` | String representation |

> **Limitation:** tick attributes only work on bare identifiers and type names — not on field accesses (`self.x'Image`) or subscripts. Use `str()` in those cases.

```adascript
# Iterating over full enum range
for s in Stage_T'First .. Stage_T'Last:
    print(f"processing stage {s}")

# Set arithmetic with 'Range
let available: {}Door_T = Door_T'Range - {candidateFirstChoice, carLocation}
let hostChoice: Door_T  = available'Choice   # random door from the set

# Random selection from a range
t = (1..i)'Choice    # random int in 1..i
```

---

## Range Expressions

`..` is inclusive. `..<` excludes the upper bound.

```adascript
for i in 0 .. 10:       # 0, 1, …, 10
    pass

for i in 0 ..< 10:      # 0, 1, …, 9
    pass

if x in 1 .. 100:
    print("in range")
```

**Python output:** `range(lo, hi+1)` for `..`; `range(lo, hi)` for `..<`
**Nim output:** native `lo .. hi` / `lo ..< hi`

---

## Control Flow

### if / elif / else
Standard Python. Also supports single-statement inline form:
```adascript
if x < 5: print("x<5")
elif x < 10: print("5<=x<10")
else: print("x>=10")
```

### while
```adascript
while queue:
    item = queue.pop()

while n > 0: n -= 1    # inline form
```

### case / when
Pattern matching. Ada-style alternative to Python 3.10+ `match/case` (both syntaxes work).

**Literal and range patterns:**
```adascript
case code:
    when 200:              print("OK")
    when 400 | 401 | 403:  print("client error")
    when 500 .. 599:       print("server error")
    when others:           print("unknown")
```

**Enum patterns:**
```adascript
case choice:
    when DontSwitch:
        if candidateFirstChoice == carLocation:
            stayWins += 1
    when Switch:
        if candidateSecondChoice == carLocation:
            switchWins += 1
```

**Tuple patterns (multi-dimensional dispatch):**
```adascript
let (year, age) = current_state
case (year, age):            # subject must be a tuple EXPRESSION, not a plain variable
    when (6, _):
        []
    when (0, _):
        [(BUY, maintenance_cost[0] + market_value[0])]
    when (_, 3):
        [(TRADE, -market_value[age] + market_value[0])]
    when others:
        [(KEEP, maintenance_cost[age])]
```

**Python output:** `match/case` with tuple pattern
**Nim output:** `if/elif/else` chain (Nim doesn't support tuple case selectors)

> **Critical:** The tuple desugar path fires only when `case` subject is a compound expression `(x, y)` or field access `x.kind`. A plain variable holding a tuple emits Nim's `case`, which rejects it. Always destructure with `let` first.

**Structural patterns (record matching):**
```adascript
case x:
    when Val_T(kind=VSym, sym="if"):    # uppercase → equality check
        return "keyword: if"
    when Val_T(kind=VSym, sym=name):    # lowercase → let binding
        return "symbol: " + name
    when Val_T(kind=VNum, num=n):
        return "number"
    when others:
        return "other"
```

**Sequence patterns:**
```adascript
case x.items:
    when [Val_T(kind=VSym, sym="if"), test, consequence, alternative]:
        return "if-expr"
    when [Val_T(kind=VSym, sym=op), *args]:    # *name captures tail
        return "call: " + op
    when []:                                    # empty list
        return "empty"
    when others:
        return "other"
```

Rules: `TypeName(field=Value)` with uppercase → equality check; lowercase → `let` binding. `*rest` captures tail. `[]` matches empty. `_` or `others` → catch-all.

---

## Functions

```adascript
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str = "world") -> str:
    return f"Hello, {name}!"
```

**Implicit return:** if a function has a return-type annotation and its last statement is a bare expression (not `return`), it's promoted to a return. Excludes `-> None`.
```adascript
def clamp(x: int, lo: int, hi: int) -> int:
    max(lo, min(x, hi))    # implicitly returned
```

**Generator functions:** `yield` transpiles to Python generators and Nim iterators.
```adascript
def shortest_path(self, start_state: S, end_state: S):
    while fringe:
        ...
        if current_state == end_state:
            yield self.real_cost(cost), path
```

---

## Classes and Inheritance

Use `var`, `let`, `const` inside class body to declare fields.

```adascript
class TrieNode:
    var children: [Digit_T]TrieNode
    var words:    []str

    def __init__(self):
        self.children = {d: None for d in Digit_T}
        self.words = []
```

**Inline field defaults** are injected into the constructor automatically:
```adascript
class AwkProcessor(AwkBase):
    var NR     : int = 0
    var counts : [Severity_T]int = [INFO: 0, WARN: 0, ERROR: 0, OTHER: 0]

    def __init__(self, fs: str = " "):
        self.FS = fs    # only caller-supplied fields need explicit init
```

**Mutable self** — the transpiler auto-detects if a method mutates `self` (field assignment, `+=`, `.add()`, or any `self.method()` call) and emits `self: var ClassName` in Nim. No annotation needed.

**Parameter mutation** — parameters follow Python's rules. Rebinding the name (`s = s + "!"`) is local: Nim shadows it with `var s = s`. Mutating in place (`xs.append(...)`, `xs[i] = ...`, `+=`) is visible to the caller: Nim emits `xs: var seq[int]`. No annotation needed either way.

**Forwarding constructors** — when a subclass has no `__init__`, the transpiler generates one mirroring the parent's parameters.

**`@virtual`** — only needed when subclasses live in a different file (module). Makes Nim emit `ref object of RootObj` for cross-module dynamic dispatch.

**Inheritance:**
```adascript
class Circle(Shape):
    var radius: float

    def __init__(self, r: float):
        self.radius = r

    def area(self) -> float:
        return 3.14159 * self.radius ** 2
```

**ALL_CAPS for shared state** — when a class is defined inside a function, local variables of the outer function aren't visible in Nim's hoisted methods. Declare shared variables with ALL_CAPS names; the transpiler hoists them to global scope.

---

## Generic Classes

```adascript
class Optimizer[S, D, C]:
    var offset: float

    def get_next_decisions(self, current_state: S) -> [](D, C):
        raise NotImplementedError()

    def shortest_path(self, start: S, end: S):
        ...
        yield cost, path
```

Subclass by instantiating parameters:
```adascript
class BookMap(Optimizer[State_T, State_T, Cost_T]):
    def get_next_decisions(self, curr: State_T) -> [](State_T, Cost_T):
        return self.G.get(curr, [])
```

Methods defined outside a generic class avoid Nim 2.x generic-method restrictions and can be called via UFCS:
```adascript
def longest_path(self: Optimizer[S, D, C], start: S, end: S) -> (float, []D):
    ...
```

---

## Shell Integration

Shell commands are first-class expressions.

```adascript
let result = shell: git status
print(result.output)    # stdout as string
print(result.stderr)    # stderr as string
print(result.code)      # exit code as int

# Lines capture — type annotations and bare names both work
let lines: []str = shellLines: ls -la
entries = shellLines: find . -name "*.ady"
for line in lines:
    print(line)

# Variable interpolation — simple names and function calls
let branch = "main"
let r = shell: git log --oneline {branch}
shell: mkdir -p -- {Q(os.path.join(d, "subdir"))}

# Options
let r = shell(cwd = "/tmp"): pwd
let r = shell(timeout = 5000): slow-command

# Discard output
shell: rm -rf /tmp/build

# Block form — multiple commands joined with &&
shell:
    echo hello
    echo world

# Interactive block (PTY expect/send)
shell:
    bc -q
    send("2 + 2\n")
    expect("4")
    send("quit\n")
```

| Adascript | Python 3 | Nim |
|-----------|----------|-----|
| `let r = shell: cmd` | `subprocess.run(…, capture_output=True)` | `execCmdEx("cmd")` |
| `let ls = shellLines: cmd` | `…stdout.splitlines()` | `execCmdEx(…)[0].splitLines()` |
| `let ls: []str = shellLines: cmd` | same (annotation stripped) | same (Nim infers type) |
| `ls = shellLines: cmd` | same (bare assignment) | same |
| `shell: cmd` | `subprocess.run("cmd", shell=True)` | `discard execCmd("cmd")` |
| `{var}` in body | f-string | `fmt"""…"""` |
| `{f(x)}` in body | f-string | hoisted to `let tmp = f(x)` |

Required imports (`subprocess`, `osproc`, `strformat`) are inserted automatically.

---

## Bash Variables and File Tests

```adascript
if $# < 2:
    print(f"Usage: {$0} <input> <output>")
    quit(1)

let dict_file:  str = $1
let phone_file: str = $2
for arg in $@:
    print(arg)

home   = $HOME
editor = $EDITOR
```

| Adascript | Python | Nim |
|-----------|--------|-----|
| `$0` | `sys.argv[0]` | `getAppFilename()` |
| `$1`…`$9` | `sys.argv[1]`… | `paramStr(1)`… |
| `$@` | `sys.argv[1:]` | `commandLineParams()` |
| `$#` | `len(sys.argv) - 1` | `paramCount()` |
| `$NAME` | `os.environ.get('NAME','')` | `getEnv("NAME")` |

**File-test operators:**
```adascript
if -e path:      # exists
if -f path:      # regular file
if -d path:      # directory
if -L path:      # symlink
if -r path:      # readable
if -w path:      # writable
if -x path:      # executable
if -s path:      # non-empty
if a -nt b:      # a newer than b
if a -ot b:      # a older than b

if not -f dict_file:
    print("Error: file not found")
    quit(1)
```

---

## Nim-Only Features

**`nimport`** — imports that appear only in Nim output, stripped from Python:
```adascript
nimport strutils, sequtils, algorithm
nimport stdlib          # PriorityQueue, FifoQueue, LifoQueue, ANY
nimport awk             # AwkBase record-processor base class
nimport shortest_path   # another .ady file as a library (auto-transpiled)
```

**`# nimraw: <code>`** — raw Nim line verbatim, stripped from Python. Mainly for forward declarations of mutually recursive functions:
```adascript
# nimraw: proc b(x: int): int
def a(x: int) -> int:
    return b(x - 1)
def b(x: int) -> int:
    if x <= 0: return 0
    return a(x - 1)
```

---

## Python Interoperability

Adascript knows which Python imports have direct Nim equivalents and which need the `nimpy` bridge.

**Natively mapped modules** (no runtime overhead):

| Python import | Nim module |
|---------------|------------|
| `import os` | `import os` |
| `import math` | `import math` |
| `import time` | `import times` |
| `import re` | `import re` |
| `import random` | `import random` |
| `import json` | `import std/json` |
| `import itertools` | `import sequtils` |
| `import asyncio` | `import asyncdispatch` |

Call translation examples:
```adascript
import math, time, re, random
x      = math.sqrt(4.0)      # → sqrt(4.0)
t      = time.time()          # → epochTime()
result = re.sub(r'\s+', ' ', text)   # → replace(text, re("\\s+"), " ")
n      = random.randint(1, 100)      # → rand(1..100)
```

**Non-native libraries** go through `nimpy` automatically:
```adascript
import requests
r = requests.get('https://example.com')
```
Nim output:
```nim
import nimpy
let requests = pyImport("requests")
var r = requests.get("https://example.com")
```

**Automatic `.to(T)` coercion** — when a variable has a primitive type annotation and its right-hand side is from a `PyObject` call chain:
```adascript
count: int   = r.json()['total']    # → r.json()["total"].to(int)
score: float = r.json()['score']    # → r.json()["score"].to(float)
```

---

## Print Statement

Python-2-style `print` without parentheses is supported (call form also works):
```adascript
print "hello"
print f"result: {value}"
print "x =", x
print("also valid")
```

Nim output: `echo(...)`. Python output: `print(...)`.

---

## Enum-Indexed Arrays

```adascript
type Priority is enum LOW, MED, HIGH
var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
print(costs[HIGH])    # 10

# Nested 2-D lookup table
var transition: [Hidden_State_T][Hidden_State_T]float = [
    HEALTHY: [HEALTHY: 0.7, FEVER: 0.3],
    FEVER:   [HEALTHY: 0.4, FEVER: 0.6],
]
```

**Python output:** nested dict
**Nim output:** `array[Hidden_State_T, array[Hidden_State_T, float]]` — stack-allocated, O(1) lookup.

---

## Callable Objects and Pipe Operator

Classes with `__call__` become callable; Nim uses `{.experimental: "callOperator".}` (inserted automatically). `__ror__` flips argument order for pipe syntax:

```adascript
class Style:
    var on: str
    var off: str
    def __init__(self, code: int):
        self.on = f"\x1b[{code}m"
        self.off = "\x1b[0m"
    def __call__(self, *args: str) -> str:
        return "".join([f"{self.on}{arg}" for arg in args]) + self.off
    def __ror__(self, other: str) -> str:
        return self(other)

let bold: Style = Style(1)
print("hello" | bold)     # via __ror__
print(bold("hello"))      # via __call__
```

The `|` operator is context-sensitive: when operands involve custom types, emits Nim `|`; otherwise emits `or`.

---

## Collections — Key Patterns

**Sequences:**
```adascript
var words: []str = ["hello", "world"]
words.append("!")
print(len(words))
```

**Hash tables:**
```adascript
var counts: {str}int = {:}
counts["apple"] += 1
for key, val in counts.items():
    print(f"{key}: {val}")
```

**Sets:**
```adascript
var visited: {}str    = {}    # HashSet[string]
var seen:    {}Door_T = {}    # set[Door_T] (bitset — ordinal type)
visited.add("node_A")
if "node_A" in visited:
    print("seen")
```

The Nim backend uses bitset (`set[T]`) for ordinal types (bool, char, byte, small int, enum) and `HashSet` otherwise.

---

## Python 3.10+ `match/case`

Adascript is a superset of Python, so standard `match/case` is supported alongside Adascript's own `case/when`. Both compile to the same Nim output.

```adascript
def get_kind(arg: str) -> Kind_T:
    match arg:
        case "--":
            return cmdEnd
        case _ if arg.startswith("--"):
            return cmdOption
        case _:
            return cmdArgument
```

All Python 3.10 pattern forms work: literals, guards (`if`), wildcards (`_`), capture variables, class patterns, sequence patterns, OR patterns (`|`).

---

## Walrus Operator `:=`

The walrus operator assigns and tests in one expression. The primary use-case is optional-type bind chains — it provides Haskell-do-notation ergonomics without dedicated syntax.

```adascript
# Optional bind: if the result is present, unwrap and use it
def load_config(path: str) -> ?Config:
    if text := read_file_safe(path):
        if raw := parse_json(text):
            if port := parse_int(raw.get("port") or ""):
                return Config(host=raw.get("host") or "localhost", port=port)
    return None

# While loop consuming an iterator
while token := lexer.try_next(TK_STRCONST):
    emit(token)
```

**Nim output** — the transpiler hoists the binding out of the condition:

```nim
let text = read_file_safe(path)
if text.isSome:
    let raw = parse_json(text.get())
    if raw.isSome:
        ...
```

Inside a `while` condition, `:=` becomes a `let` before the loop with the test inlined.

---

## `do:` Block — Monadic Bind

The `do:` block is first-class do-notation for `?T` chains. Each `x <- expr` step evaluates `expr` (which must return `?T`), short-circuits to `return none(R)` if absent, and binds the unwrapped value to `x` as a plain variable.

```adascript
def compute(raw_a: str, raw_b: str) -> ?int:
    do:
        a <- parse_int(raw_a)
        b <- parse_int(raw_b)
        q <- safe_div(a, b)
        r <- clamp_positive(q)
    return r
```

After the block, `a`, `b`, `q`, `r` are plain `int` (not `?int`) and in scope for the rest of the function body.

**Nim output:**

```nim
proc compute(raw_a: string, raw_b: string): Option[int] =
    let adadoA = parse_int(raw_a)
    if adadoA.isNone: return none(int)
    let a = adadoA.get()
    ...
    return some(r)
```

Rules:
- Every `expr` after `<-` must return `?T`.
- The enclosing function must also return `?R`.
- All bindings are plain (non-optional) `let` variables in scope after the block.
- Use `do:` for chains of 3+ steps; walrus `:=` for 1–2 steps.

---

## Perl-Style Regex Literals

Adascript supports inline regex literals. No `import re` needed.

```adascript
# Match / non-match test — returns bool
if s == /^\d+$/:
    print("integer")

if s != /^\s*$/:
    print("non-blank")

# Flags: i (case-insensitive), g (findall)
if s == /^yes$/i:
    print("affirmative")

# Positional captures — $+1, $+2, ... after a successful match
if s == /(\w+)\s*=\s*(\w+)/:
    print(f"{$+1} → {$+2}")

# Named captures — $+{name}
if s == /(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/:
    print(f"{$+{day}}/{$+{month}}/{$+{year}}")

# Whole-match capture
if s == /\d+/:
    print($+0)

# Findall — /pat/g returns []str
let words: []str = s == /\w+/g

# Substitution — s/pat/repl/flags
s == s/\d+/[N]/g    # replace all digits with [N]
```

**Python output:** uses `re` module.
**Nim output:** uses `std/re`.

---

## Block-Form Enum Declarations

In addition to the inline `type E is enum A, B, C` form, enums can be declared with one member per line — useful for long enums or when per-member comments are needed:

```adascript
type Expr_Kind is enum:
    EK_IntLit      # integer literal  42
    EK_RealLit     # float literal    3.14
    EK_Sym         # symbol           foo
    EK_List        # list             (...)
    EK_Builtin     # built-in op      +, -, car, cdr
```

Both forms are identical at the type level and produce the same Python/Nim output.

---

## `@contextmanager` → Nim Template

Python's `@contextmanager` decorator transpiles to a Nim `template` with a trailing block argument. The `yield` in the body becomes the injection point for the caller's block.

```adascript
@contextmanager
def emit_block(self, start: str, close: str):
    self(start)
    self.indent_level += 2
    yield
    self.indent_level -= 2
    self(close)

# Call site — caller's block is injected at yield
with emit.emit_block("{", "}"):
    emit("int x = 42;")
```

**Nim output:**

```nim
template emit_block(self: var Emitter, start: string, close: string, body: untyped) =
    self(start)
    self.indent_level += 2
    body
    self.indent_level -= 2
    self(close)

emit.emit_block("{", "}"):
    emit("int x = 42;")
```

---

## Ownership (`own` / `lent` / `move` / `drop`)

Adascript exposes Nim's ARC (automatic reference counting) memory model through optional ownership annotations. These are purely additive — unowned code is valid and identical in behaviour.

```adascript
# own: declare a uniquely-owned value (freed at end of scope by ARC)
own a: Msg_T = make_msg("hello", 3)

# lent: borrow without taking ownership (read-only in Nim)
def summarise(msg: lent Msg_T) -> str:
    f"{msg.text} x{msg.count}"

print(summarise(a))    # borrows a

# with own: RAII scoped block — a is freed when the block exits
with own tmp = make_msg("scoped", 1):
    print(summarise(tmp))
# tmp freed here

# move: explicit ownership transfer (a is invalid after this)
own b: Msg_T = move(a)

# drop: explicit early release
own c: Msg_T = make_msg("temp", 5)
drop(c)
```

**Python output:** ownership annotations are stripped; code runs identically under GC.
**Nim output:** `own` → `var`, `lent` → `lent`, `move` → `move()`, `drop` → `=destroy()`.

---

## Complete Quick Example

```adascript
type Stage_T is enum STAGE1, STAGE2, STAGE3

type Choice_T is tuple:
    weight: int
    benefit: int

var items: [Stage_T]Choice_T = [
    STAGE1: (weight: 2, benefit: 65),
    STAGE2: (weight: 3, benefit: 80),
    STAGE3: (weight: 1, benefit: 30),
]

for s in Stage_T'First .. Stage_T'Last:
    let choice: Choice_T = items[s]
    print(f"Stage {s}: weight={choice.weight}, benefit={choice.benefit}")
```

**Python output:** uses `Enum`, `NamedTuple`, `dict`, `range()`.
**Nim output:** uses native `enum`, `tuple`, `array[Stage_T, Choice_T]`, `lo .. hi`.

---

## Full Syntax Reference

| Feature | Adascript syntax |
|---------|-----------------|
| Mutable variable | `var x: int = 0` |
| Immutable binding | `let name: str = "hello"` |
| Compile-time constant | `const MAX: int = 1000` |
| Enum declaration | `type E is enum A, B, C` |
| Named tuple | `type P is tuple: x: float; y: float` |
| Record | `type P is record: name: str; age: int` |
| Variant record | `type S (Kind: K) is record: case ...` |
| Subrange | `type T is lo .. hi` |
| List annotation | `[]T` |
| Fixed array annotation | `[N]T` |
| Open array (param only) | `[*]T` |
| Dict annotation | `{K}V` |
| Set annotation | `{}T` |
| Enum-indexed array | `[E]T` |
| Optional | `?T` |
| Inclusive range | `lo .. hi` |
| Exclusive range | `lo ..< hi` |
| Enum first/last | `E'First`, `E'Last` |
| Full enum set | `E'Range` |
| Successor/predecessor | `expr'Next`, `expr'Prev` |
| Random selection | `expr'Choice` |
| Empty dict literal | `{:}` |
| Named tuple literal | `(field: value, ...)` |
| Enum-indexed array literal | `[KEY: value, ...]` |
| Pattern matching | `case x: when P: ... when others: ...` |
| Inline suite | `if x>0: f()`, `while c: g()`, `when P: h()` |
| Generator function | `def f(): ... yield value` |
| Field with default | `var x: int = 0` inside class body |
| Mutable self (auto) | any `self.field =` / `self.method()` |
| Cross-module base class | `@virtual class C: ...` |
| Generic class | `class C[S, D, C]: ...` |
| Nim-only import | `nimport module` |
| Raw Nim injection | `# nimraw: <code>` |
| Shell capture | `let r = shell: cmd` |
| Shell exit code, terminal kept | `let code: int = shell: cmd` |
| Shell interpolation, quoted | `shell: cmd {!path}` |
| Shell interpolation, list | `shell: cmd {*args}` |
| Shell, fail on non-zero | `shell(check = true): cmd` |
| Shell lines capture | `let ls = shellLines: cmd` |
| Shell lines (typed) | `let ls: []str = shellLines: cmd` |
| Shell (bare assign) | `ls = shellLines: cmd` |
| Shell expr interpolation | `shell: cmd {f(x)}` (auto-hoisted) |
| Discard shell output | `shell: cmd` |
| Shell block | `shell:` then indented commands |
| Interactive PTY block | `shell:` then `cmd` / `send(...)` / `expect(...)` |
| CLI argument | `$1`, `$@`, `$#` |
| Environment variable | `$HOME`, `$PATH` |
| File-test | `-e path`, `-f path`, `-d path` |
| File comparison | `a -nt b`, `a -ot b` |
| Python 2-style print | `print "text"` or `print expr, expr` |
| Python 3.10 match/case | `match x: case P: ...` (full pattern syntax) |
| Walrus bind | `if r := f():` / `while r := f():` |
| Monadic do block | `do:` / `x <- expr` |
| Regex literal | `s == /pat/`, `s != /pat/`, `s == /pat/g` |
| Regex capture | `$+1`, `$+{name}`, `$+0` |
| Substitution | `s == s/pat/repl/g` |
| Block-form enum | `type E is enum:` / one member per indented line |
| Context manager | `@contextmanager def f(): ... yield ...` |
| Owned value | `own x: T = expr` |
| Borrow parameter | `param: lent T` |
| Ownership transfer | `move(x)` |
| Explicit release | `drop(x)` |
| RAII scope | `with own x = expr:` |

---

## Known Limitations

- **Blank lines and inline comments** — `py2py.py` collapses blank lines between statements and drops inline comments (`x = 1  # note`). Infrastructure is in place but not yet wired through all compound-statement backends.
- **Tick attributes on field accesses** — `self.x'Image` does not work; use `str(self.x)` instead.
- **Case subject must be structural** — `case state:` where `state` is a tuple variable emits Nim's native `case`, which rejects non-ordinal selectors. Destructure with `let (a, b) = state` first, then `case (a, b):`.
- **Global parser state** — `ParserState` is a class-level singleton; call `ParserState.reset()` between independent parse runs. Thread-unsafe for concurrent parses.
- **`nimport` stdlib coverage** — some Python builtins (`PriorityQueue`, `FifoQueue`, `ANY`) live in a local `stdlib.nim` shim (`nimport stdlib`).
- **`$name` is always a shell variable** — `$HOME`, `$1`, etc. are tokenised as environment/CLI lookups even outside `shell:` blocks. Use explicit `getEnv("NAME")` in Nim-only contexts if needed.
