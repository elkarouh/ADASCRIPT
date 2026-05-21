# Pattern Matching in Adascript

Adascript supports structural pattern matching in two syntaxes that produce
identical output. You can use whichever reads more naturally for your context:

| Syntax | Keyword at subject | Keyword at branch | Origin |
|--------|--------------------|-------------------|--------|
| `case / when` | `case` | `when` | Adascript / Ada / Nim |
| `match / case` | `match` | `case` | Python 3.10+ |

Both transpile to Python 3.10+ `match/case` and to Nim `case/of` (or
`if/elif` chains for structural patterns). All examples in this tutorial
show both outputs so you can see exactly what each backend receives.

```
source.ady  ──▶  python3 TO_PYTHON/py2py.py   ──▶  Python 3.10+ match/case
            ──▶  python3 TO_NIM/py2nim.py      ──▶  Nim case/of or if/elif
```

---

## Table of Contents

1. [Quick syntax comparison](#1-quick-syntax-comparison)
2. [Literal patterns](#2-literal-patterns)
3. [Wildcard and default branch](#3-wildcard-and-default-branch)
4. [Capture patterns](#4-capture-patterns)
5. [OR patterns](#5-or-patterns)
6. [Value and enum patterns](#6-value-and-enum-patterns)
7. [Range patterns](#7-range-patterns)
8. [Sequence patterns](#8-sequence-patterns)
9. [Class and record patterns](#9-class-and-record-patterns)
10. [AS bindings](#10-as-bindings)
11. [Guard clauses](#11-guard-clauses)
12. [Tuple subjects](#12-tuple-subjects)
13. [Nested patterns](#13-nested-patterns)
14. [Pattern reference table](#14-pattern-reference-table)
15. [What is not supported](#15-what-is-not-supported)
16. [Real-world examples](#16-real-world-examples)

---

## 1. Quick syntax comparison

The two syntaxes are entirely interchangeable. Pick one and stay consistent
within a file.

**Adascript style (`case / when`):**

```python
case command:
    when "quit":
        sys.exit(0)
    when "help":
        print_help()
    when others:
        print("unknown command")
```

**Python style (`match / case`):**

```python
match command:
    case "quit":
        sys.exit(0)
    case "help":
        print_help()
    case _:
        print("unknown command")
```

**Python 3.10+ output** (identical for both):

```python
match command:
    case "quit":
        sys.exit(0)
    case "help":
        print_help()
    case _:
        print("unknown command")
```

**Nim output** (identical for both):

```nim
case command:
    of "quit":
        quit(0)
    of "help":
        printHelp()
    else:
        echo("unknown command")
```

> **`others` vs `_`**: In `case/when` syntax the catch-all branch uses
> `others`; in `match/case` syntax it uses `_`. Both compile to `else:` in
> Nim and `case _:` in Python.

---

## 2. Literal patterns

Match exact integer, float, string, `True`, `False`, or `None` values.
Nim maps these to native `case/of` when every branch is a literal —
no runtime overhead beyond the integer switch.

```python
case http_status:
    when 200:
        print("OK")
    when 404:
        print("Not Found")
    when 500:
        print("Internal Server Error")
    when others:
        print("other status")
```

**Python output:**

```python
match http_status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case 500:
        print("Internal Server Error")
    case _:
        print("other status")
```

**Nim output:**

```nim
case http_status:
    of 200:
        echo("OK")
    of 404:
        echo("Not Found")
    of 500:
        echo("Internal Server Error")
    else:
        echo("other status")
```

### Boolean literals

```python
case flag:
    when True:
        enable()
    when False:
        disable()
```

### None / nil

```python
case maybe_value:
    when None:
        print("nothing here")
    when others:
        print("got a value")
```

---

## 3. Wildcard and default branch

`_` (Python style) and `others` (Adascript style) both mean "match
anything, bind nothing". They must be the last branch.

```python
match direction:
    case "north" | "south":
        move_vertical()
    case "east" | "west":
        move_horizontal()
    case _:
        raise ValueError(f"bad direction: {direction}")
```

**Nim output:**

```nim
case direction:
    of "north", "south":
        moveVertical()
    of "east", "west":
        moveHorizontal()
    else:
        raise newException(ValueError, fmt"bad direction: {direction}")
```

---

## 4. Capture patterns

A bare lowercase name in a pattern binds the matched value to that name for
use inside the branch body. Unlike a wildcard, a capture always succeeds and
always binds.

```python
match token:
    case int(n):
        print(f"integer: {n}")
    case str(s):
        print(f"string: {s}")
    case _:
        print("other")
```

More practically, captures appear in structural positions:

```python
match response:
    case [first, *rest]:
        print(f"first element: {first}, {len(rest)} more")
    case []:
        print("empty")
```

**Python output:**

```python
match response:
    case [first, *rest]:
        print(f"first element: {first}, {len(rest)} more")
    case []:
        print("empty")
```

**Nim output:**

```nim
if len(response) >= 1:
    let first = response[0]
    let rest = response[1..response.high]
    echo(fmt"first element: {first}, {len(rest)} more")
elif len(response) == 0:
    echo("empty")
```

> **Name convention**: Adascript follows Nim's rule that names beginning
> with an uppercase letter are constants or enum values (equality-checked),
> while lowercase names are captures (bound). A name like `RED` in a pattern
> is an equality check; `red` is a capture.

---

## 5. OR patterns

Separate alternatives with `|`. All alternatives must bind the same names
(or none). OR patterns inside a single `when`/`case` branch collapse into
one `of` clause in Nim.

```python
case exit_code:
    when 0 | 1:
        print("success or minor issue")
    when 2 | 3 | 4:
        print("usage or environment error")
    when others:
        print("failure")
```

**Nim output (native case/of — zero overhead):**

```nim
case exit_code:
    of 0, 1:
        echo("success or minor issue")
    of 2, 3, 4:
        echo("usage or environment error")
    else:
        echo("failure")
```

### OR patterns with strings

```python
match verb:
    case "GET" | "HEAD":
        handle_read()
    case "POST" | "PUT" | "PATCH":
        handle_write()
    case "DELETE":
        handle_delete()
    case _:
        raise ValueError("unsupported method")
```

---

## 6. Value and enum patterns

Dotted names like `Color.RED` or `Status.OK` are **value patterns** —
they perform an equality check against the named constant. Define the enum
in the same file with the `type ... = enum` declaration.

```python
type Direction = enum North, South, East, West

def describe(d: Direction) -> str:
    case d:
        when Direction.North:
            return "heading north"
        when Direction.South:
            return "heading south"
        when Direction.East | Direction.West:
            return "heading sideways"
```

**Python output:**

```python
class Direction(Enum):
    North = 0
    South = 1
    East = 2
    West = 3
North = Direction.North
South = Direction.South
East = Direction.East
West = Direction.West

def describe(d: Direction) -> str:
    match d:
        case Direction.North:
            return "heading north"
        case Direction.South:
            return "heading south"
        case Direction.East | Direction.West:
            return "heading sideways"
```

**Nim output:**

```nim
type Direction = enum North, South, East, West

proc describe(d: Direction): string =
    case d:
        of Direction.North:
            return "heading north"
        of Direction.South:
            return "heading south"
        of Direction.East, Direction.West:
            return "heading sideways"
```

### Enum exhaustiveness in Nim

When every enum value is covered, Nim's compiler verifies exhaustiveness at
compile time and elides bounds checking — making enum dispatch essentially
free.

```python
type Color = enum Red, Green, Blue

case pixel:
    when Color.Red:   r += 1
    when Color.Green: g += 1
    when Color.Blue:  b += 1
```

No `others` / `_` needed — Nim knows these three cases are complete.

---

## 7. Range patterns

Adascript extends Python's pattern syntax with Ada/Nim-style range patterns
using `..`. Ranges work on integers, characters, and enum values. They
compile directly to Nim's `lo .. hi` range syntax in `of` branches —
a single efficient comparison.

```python
case age:
    when 0..12:
        tier = "child"
    when 13..17:
        tier = "teen"
    when 18..64:
        tier = "adult"
    when 65..MAX_AGE:
        tier = "senior"
    when others:
        tier = "invalid"
```

**Nim output:**

```nim
case age:
    of 0 .. 12:
        tier = "child"
    of 13 .. 17:
        tier = "teen"
    of 18 .. 64:
        tier = "adult"
    of 65 .. MAX_AGE:
        tier = "senior"
    else:
        tier = "invalid"
```

> **Range patterns are Adascript-only**: Python 3.10+ `match/case` has no
> range syntax. The `case/when` form is required for range patterns.

### Character ranges

```python
case ch:
    when 'a'..'z':
        kind = "lower"
    when 'A'..'Z':
        kind = "upper"
    when '0'..'9':
        kind = "digit"
    when others:
        kind = "other"
```

### Combining ranges with OR

```python
case score:
    when 90..100:
        grade = "A"
    when 80..89:
        grade = "B"
    when 70..79:
        grade = "C"
    when 60..69:
        grade = "D"
    when 0..59:
        grade = "F"
```

---

## 8. Sequence patterns

Match lists by shape: exact length, partial prefix, suffix, or interior.
A `*name` element captures all remaining items; `*_` discards them.

### Fixed-length match

```python
match parts:
    case [host, port]:
        connect(host, int(port))
    case [host]:
        connect(host, 80)
    case []:
        raise ValueError("empty address")
    case _:
        raise ValueError("too many components")
```

**Nim output:**

```nim
if len(parts) == 2:
    let host = parts[0]
    let port = parts[1]
    connect(host, parseInt(port))
elif len(parts) == 1:
    let host = parts[0]
    connect(host, 80)
elif len(parts) == 0:
    raise newException(ValueError, "empty address")
else:
    raise newException(ValueError, "too many components")
```

### Variable-length match with `*rest`

```python
match argv:
    case [cmd, *args] if cmd == "run":
        run(args)
    case [cmd, *_]:
        print(f"unknown command: {cmd}")
    case []:
        print("no arguments")
```

**Nim output:**

```nim
if len(argv) >= 1 and argv[0] == "run":
    let cmd = argv[0]
    let args = argv[1..argv.high]
    run(args)
elif len(argv) >= 1:
    let cmd = argv[0]
    echo(fmt"unknown command: {cmd}")
elif len(argv) == 0:
    echo("no arguments")
```

### Matching a prefix

```python
match tokens:
    case ["if", cond, "then", *body]:
        parse_if(cond, body)
    case ["while", cond, "do", *body]:
        parse_while(cond, body)
    case [keyword, *_]:
        raise SyntaxError(f"unexpected keyword: {keyword}")
```

### Matching literals inside sequences

```python
match packet:
    case [0xFF, 0xFE, *data]:
        decode_utf16_le(data)
    case [0xFE, 0xFF, *data]:
        decode_utf16_be(data)
    case [0xEF, 0xBB, 0xBF, *data]:
        decode_utf8_bom(data)
    case [*data]:
        decode_utf8(data)
```

---

## 9. Class and record patterns

Match an object by its field values. Only **keyword-argument style** is
supported (`FieldName=pattern`). Positional matching is not supported (see
[§15](#15-what-is-not-supported)).

### Matching a dataclass or record

```python
type Point = record:
    x: float
    y: float

def classify(p: Point) -> str:
    match p:
        case Point(x=0.0, y=0.0):
            return "origin"
        case Point(x=0.0, y=y):
            return f"on y-axis at {y}"
        case Point(x=x, y=0.0):
            return f"on x-axis at {x}"
        case Point(x=x, y=y):
            return f"general point ({x}, {y})"
```

**Python output:**

```python
match p:
    case Point(x=0.0, y=0.0):
        return "origin"
    case Point(x=0.0, y=y):
        return f"on y-axis at {y}"
    case Point(x=x, y=0.0):
        return f"on x-axis at {x}"
    case Point(x=x, y=y):
        return f"general point ({x}, {y})"
```

**Nim output** (desugared to field-access conditions):

```nim
if p.x == 0.0 and p.y == 0.0:
    return "origin"
elif p.x == 0.0:
    let y = p.y
    return fmt"on y-axis at {y}"
elif p.y == 0.0:
    let x = p.x
    return fmt"on x-axis at {x}"
else:
    let x = p.x
    let y = p.y
    return fmt"general point ({x}, {y})"
```

### Matching with mixed literals and captures

```python
type Token = record:
    kind: str
    value: str

match tok:
    case Token(kind="INT", value=v):
        emit_int(int(v))
    case Token(kind="STR", value=v):
        emit_str(v)
    case Token(kind="OP", value="+"):
        emit_add()
    case Token(kind="OP", value=op):
        emit_op(op)
    case _:
        raise SyntaxError(f"unexpected token: {tok}")
```

### Partial matching

You don't have to name every field — unmentioned fields are ignored:

```python
match event:
    case Click(button="left"):
        handle_left_click()
    case Click(button="right"):
        handle_right_click()
    case KeyPress(key=k):
        handle_key(k)
    case _:
        pass
```

---

## 10. AS bindings

Attach a name to an entire pattern with `as`. The name is bound to the
matched value regardless of how the inner pattern decomposes it.

```python
match data:
    case [first, *_] as full_list:
        print(f"non-empty: {full_list}")
        process(first)
    case [] as empty:
        log(f"received empty list: {empty}")
```

**Nim output:**

```nim
if len(data) >= 1:
    let full_list = data
    let first = data[0]
    echo(fmt"non-empty: {full_list}")
    process(first)
elif len(data) == 0:
    let empty = data
    log(fmt"received empty list: {empty}")
```

### AS with OR patterns

```python
match status:
    case 400 | 401 | 403 as code:
        log_client_error(code)
    case 500 | 502 | 503 as code:
        log_server_error(code)
```

**Python output:**

```python
match status:
    case 400 | 401 | 403 as code:
        log_client_error(code)
    case 500 | 502 | 503 as code:
        log_server_error(code)
```

### AS with class patterns

```python
match message:
    case ErrorResponse(code=c, body=b) as msg:
        metrics.record(msg)
        raise AppError(c, b)
```

---

## 11. Guard clauses

Add an `if condition` after the pattern for additional runtime checks that
cannot be expressed structurally. The guard is only evaluated when the
pattern already matched.

```python
match value:
    case n if n < 0:
        print("negative")
    case n if n == 0:
        print("zero")
    case n if n > 0:
        print("positive")
```

**Nim output:**

```nim
case value:
    of n if n < 0:
        echo("negative")
    of n if n == 0:
        echo("zero")
    of n if n > 0:
        echo("positive")
```

### Guards on structural patterns

```python
match items:
    case [a, b] if a > b:
        print("descending pair")
    case [a, b] if a == b:
        print("equal pair")
    case [a, b]:
        print("ascending pair")
    case _:
        print("not a pair")
```

**Nim output:**

```nim
if len(items) == 2 and items[0] > items[1]:
    let a = items[0]
    let b = items[1]
    echo("descending pair")
elif len(items) == 2 and items[0] == items[1]:
    let a = items[0]
    let b = items[1]
    echo("equal pair")
elif len(items) == 2:
    let a = items[0]
    let b = items[1]
    echo("ascending pair")
else:
    echo("not a pair")
```

### Guards replacing absent pattern features

Use guards for checks that have no pattern syntax — membership tests,
string prefix checks, range conditions on captures:

```python
match token:
    case str(s) if s.startswith("0x"):
        return int(s, 16)
    case str(s) if s.isdigit():
        return int(s)
    case str(s):
        raise ValueError(f"not a number: {s}")
```

---

## 12. Tuple subjects

When the match subject is a tuple `(a, b, ...)`, Adascript desugars every
branch to `if/elif` conditions over the individual components. This is
necessary because Nim's `case` statement cannot match on tuples directly.

```python
case (operation, operand):
    when ("push", value):
        stack.append(value)
    when ("pop", _):
        return stack.pop()
    when ("peek", _):
        return stack[-1]
    when others:
        raise ValueError("unknown operation")
```

**Nim output:**

```nim
if operation == "push" and operand == value:
    stack.add(value)
elif operation == "pop":
    return stack.pop()
elif operation == "peek":
    return stack[stack.high]
else:
    raise newException(ValueError, "unknown operation")
```

> **Tuple subjects use value semantics**: every non-`_` element in a tuple
> pattern is treated as a value for equality checking, not as a capture.
> To bind tuple components, use sequence patterns or structured unpacking
> before the match.

### Two-dimensional dispatch

```python
case (token_type, token_value):
    when ("NUM", _):
        return float(token_value)
    when ("STR", _):
        return token_value
    when ("OP", "+") | ("OP", "-"):
        return handle_arithmetic(token_value)
    when others:
        raise SyntaxError()
```

---

## 13. Nested patterns

Patterns compose recursively — any pattern position can itself be a pattern.

### Sequences of records

```python
match events:
    case [MouseClick(x=x, y=y), *_]:
        handle_first_click(x, y)
    case [KeyPress(key="Escape"), *_]:
        cancel()
    case []:
        idle()
```

**Nim output:**

```nim
if len(events) >= 1 and events[0].x == x and events[0].y == y:
    let x = events[0].x
    let y = events[0].y
    handleFirstClick(x, y)
elif len(events) >= 1 and events[0].key == "Escape":
    cancel()
elif len(events) == 0:
    idle()
```

### Sequence elements with literal constraints

```python
match matrix_row:
    case [1, *rest]:
        print(f"starts with 1, rest: {rest}")
    case [0, 0, *_]:
        print("starts with two zeros")
    case [a, b] if a + b == 10:
        print(f"pair summing to 10: {a}, {b}")
```

### AS binding on an inner pattern

```python
match tree:
    case Node(left=Leaf(val=v) as lf, right=r):
        # lf is the whole left Leaf, v is its value
        process(lf, v, r)
```

---

## 14. Pattern reference table

| Pattern | `case/when` example | `match/case` example | Nim output |
|---------|--------------------|--------------------|------------|
| **Literal** | `when 42:` | `case 42:` | `of 42:` |
| **String literal** | `when "ok":` | `case "ok":` | `of "ok":` |
| **Bool literal** | `when True:` | `case True:` | `of true:` |
| **Wildcard** | `when others:` | `case _:` | `else:` |
| **Capture** | `when x:` | `case x:` | `of x:` or let-binding |
| **OR** | `when 1 \| 2:` | `case 1 \| 2:` | `of 1, 2:` |
| **Enum value** | `when Color.Red:` | `case Color.Red:` | `of Color.Red:` |
| **Range** *(Adascript only)* | `when 1..10:` | — | `of 1 .. 10:` |
| **Sequence fixed** | `when [a, b]:` | `case [a, b]:` | `if len == 2: let...` |
| **Sequence + rest** | `when [a, *xs]:` | `case [a, *xs]:` | `if len >= 1: let...` |
| **Empty sequence** | `when []:` | `case []:` | `if len == 0:` |
| **Class / record** | `when P(x=0, y=y):` | `case P(x=0, y=y):` | `if subj.x == 0: let y = subj.y` |
| **AS binding** | `when pat as n:` | `case pat as n:` | `let n = subj; ...` |
| **Guard** | `when pat if cond:` | `case pat if cond:` | `if ... and cond:` |

---

## 15. What is not supported

The following Python 3.10+ pattern features are deliberately excluded because
they have no clean Nim compilation path.

### Mapping (dict) patterns

```python
# NOT supported
match config:
    case {"host": h, "port": p}:
        connect(h, p)
```

Reason: Nim has no structural dict matching primitive. Use guards instead:

```python
match config:
    case dict() if "host" in config and "port" in config:
        connect(config["host"], config["port"])
```

Or unpack before the match:

```python
if "host" in config and "port" in config:
    connect(config["host"], config["port"])
```

### Positional class patterns

```python
# NOT supported
match point:
    case Point(0, y):     # positional — field order unknown at codegen time
        ...
```

Use keyword patterns instead:

```python
match point:
    case Point(x=0, y=y):   # supported
        ...
```

### Deeply nested OR patterns on structural types

```python
# Unsupported — structural pattern inside OR
match x:
    case Point(x=0) | Circle(radius=0):
        ...
```

Rewrite as separate branches:

```python
match x:
    case Point(x=0):
        handle_zero()
    case Circle(radius=0):
        handle_zero()
```

---

## 16. Real-world examples

### Command-line argument dispatch

```python
match argv[1:]:
    case ["--help" | "-h"]:
        print_usage()
    case ["--version" | "-v"]:
        print_version()
    case ["--output", path, *rest]:
        run(output=path, args=rest)
    case [flag, *_] if flag.startswith("-"):
        raise SystemExit(f"unknown flag: {flag}")
    case files:
        run(output=None, args=files)
```

**Nim output:**

```nim
let argv1 = argv[1..argv.high]
if len(argv1) == 1 and (argv1[0] == "--help" or argv1[0] == "-h"):
    printUsage()
elif len(argv1) == 1 and (argv1[0] == "--version" or argv1[0] == "-v"):
    printVersion()
elif len(argv1) >= 2 and argv1[0] == "--output":
    let path = argv1[1]
    let rest = argv1[2..argv1.high]
    run(output=path, args=rest)
elif len(argv1) >= 1 and argv1[0].startsWith("-"):
    let flag = argv1[0]
    quit(fmt"unknown flag: {flag}")
else:
    let files = argv1
    run(output=nil, args=files)
```

---

### Expression evaluator

```python
type Expr = record:
    case kind is:
        when "Num":
            value: float
        when "Add" | "Mul" | "Sub" | "Div":
            left:  Expr
            right: Expr
        when "Neg":
            operand: Expr

def eval(e: Expr) -> float:
    case e.kind:
        when "Num":
            return e.value
        when "Add":
            return eval(e.left) + eval(e.right)
        when "Sub":
            return eval(e.left) - eval(e.right)
        when "Mul":
            return eval(e.left) * eval(e.right)
        when "Div":
            if eval(e.right) == 0.0:
                raise ZeroDivisionError("division by zero")
            return eval(e.left) / eval(e.right)
        when "Neg":
            return -eval(e.operand)
```

---

### HTTP router

```python
type Method = enum GET, POST, PUT, DELETE, PATCH

def route(method: Method, path: []str) -> str:
    match (method, path):
        case (Method.GET, ["users"]):
            return list_users()
        case (Method.GET, ["users", uid]):
            return get_user(uid)
        case (Method.POST, ["users"]):
            return create_user()
        case (Method.PUT, ["users", uid]):
            return update_user(uid)
        case (Method.DELETE, ["users", uid]):
            return delete_user(uid)
        case (Method.GET, ["health"]):
            return "ok"
        case _:
            return "404 Not Found"
```

---

### Tokeniser

```python
type TokenKind = enum TInt, TFloat, TIdent, TOp, TEOF

type Token = record:
    kind:  TokenKind
    lexem: str

def compile_token(tok: Token) -> []int:
    case tok:
        when Token(kind=TokenKind.TInt, lexem=s):
            return [OP_PUSH_INT, int(s)]
        when Token(kind=TokenKind.TFloat, lexem=s):
            return [OP_PUSH_FLOAT, encode_float(float(s))]
        when Token(kind=TokenKind.TIdent, lexem=name):
            idx: int = intern(name)
            return [OP_LOAD, idx]
        when Token(kind=TokenKind.TOp, lexem="+"):
            return [OP_ADD]
        when Token(kind=TokenKind.TOp, lexem="-"):
            return [OP_SUB]
        when Token(kind=TokenKind.TOp, lexem="*"):
            return [OP_MUL]
        when Token(kind=TokenKind.TOp, lexem="/"):
            return [OP_DIV]
        when Token(kind=TokenKind.TEOF, lexem=_):
            return [OP_HALT]
        when others:
            raise SyntaxError(f"unexpected token: {tok.lexem}")
```

**Nim output (structural → if/elif):**

```nim
if tok.kind == TokenKind.TInt:
    let s = tok.lexem
    return @[OP_PUSH_INT, parseInt(s)]
elif tok.kind == TokenKind.TFloat:
    let s = tok.lexem
    return @[OP_PUSH_FLOAT, encodeFloat(parseFloat(s))]
elif tok.kind == TokenKind.TIdent:
    let name = tok.lexem
    var idx: int = intern(name)
    return @[OP_LOAD, idx]
elif tok.kind == TokenKind.TOp and tok.lexem == "+":
    return @[OP_ADD]
elif tok.kind == TokenKind.TOp and tok.lexem == "-":
    return @[OP_SUB]
elif tok.kind == TokenKind.TOp and tok.lexem == "*":
    return @[OP_MUL]
elif tok.kind == TokenKind.TOp and tok.lexem == "/":
    return @[OP_DIV]
elif tok.kind == TokenKind.TEOF:
    return @[OP_HALT]
else:
    raise newException(SyntaxError, fmt"unexpected token: {tok.lexem}")
```

---

### State machine

```python
type State = enum Idle, Running, Paused, Done

type Event = enum Start, Pause, Resume, Stop, Reset

def transition(state: State, event: Event) -> State:
    case (state, event):
        when (State.Idle,    Event.Start):  return State.Running
        when (State.Running, Event.Pause):  return State.Paused
        when (State.Running, Event.Stop):   return State.Done
        when (State.Paused,  Event.Resume): return State.Running
        when (State.Paused,  Event.Stop):   return State.Done
        when (State.Done,    Event.Reset):  return State.Idle
        when others:
            raise ValueError(f"invalid transition: {state} + {event}")
```

---

### Binary protocol parser

```python
def parse_tlv(buf: []int) -> (str, []int, []int):
    match buf:
        case [0x01, length, *rest] if len(rest) >= length:
            value = rest[:length]
            remaining = rest[length:]
            return ("string", value, remaining)
        case [0x02, length, *rest] if len(rest) >= length:
            value = rest[:length]
            remaining = rest[length:]
            return ("bytes", value, remaining)
        case [0xFF, *_]:
            return ("end-of-stream", [], [])
        case [tag, *_]:
            raise ValueError(f"unknown tag: 0x{tag:02X}")
        case []:
            raise ValueError("truncated buffer")
```

---

### Pattern matching over results (Option style)

```python
def safe_divide(a: float, b: float) -> ?float:
    if b == 0.0:
        return None
    return a / b

def format_result(r: ?float) -> str:
    match r:
        case None:
            return "division by zero"
        case float(v) if v == int(v):
            return str(int(v))
        case float(v):
            return f"{v:.4f}"
```

---

## Choosing between `case/when` and `match/case`

Both syntaxes are fully supported. Some guidelines:

**Use `case/when` when:**
- You need range patterns (`when 1..10:`) — they are Adascript-only
- The file is otherwise heavy with Adascript extensions (enums, records, `var`/`let`)
- You prefer Ada or Nim aesthetics

**Use `match/case` when:**
- The file is mostly plain Python being migrated incrementally
- The patterns are Python-idiomatic (`case [a, *rest]:`, `case Point(x=0):`)
- Readers unfamiliar with Adascript will read the code

**Never mix in one `case/when` or `match/case` block**: each block uses one
syntax. You may freely alternate between blocks in the same file.

```python
# Adascript style for the enum dispatch (range patterns available)
case score:
    when 90..100: grade = "A"
    when 80..89:  grade = "B"
    when others:  grade = "C or below"

# Python style for the structural match (familiar to Python readers)
match result:
    case Ok(value=v):
        process(v)
    case Err(msg=m):
        log(m)
```
