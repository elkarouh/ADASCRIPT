# Chapter 5 — Pattern Matching

Adascript supports two pattern-matching syntaxes side by side:

| Syntax | Style | Best for |
|--------|-------|----------|
| `case x:` / `when pat:` | Ada / Nim | enum dispatch, ranges, tuples, structural patterns |
| `match x:` / `case pat:` | Python 3.10+ | branches that need `if` guards |

Both produce Python `match`/`case` on the Python backend. On the Nim
backend, simple ordinal/string subjects become a native `case` statement;
anything structural (tuples, regexes, class patterns, guards) desugars into
an `if`/`elif`/`else` chain.

## 5.1 Literals, alternatives, ranges

```python
case code:
    when 200:
        print("OK")
    when 400 | 401 | 403:
        print("client error")
    when 500 .. 599:
        print("server error")
    when others:
        print("unknown")
```

`|` separates alternatives, `..` matches a range, and `others` is the
catch-all (you may also see `_`).

Like `if`/`while`, a `when` branch accepts an inline single-statement body,
which makes dispatch tables read like tables. `EXAMPLES/argparse.ady`:

```python
case arg:
    when "--help" | "-h": usage(0)
    when "--verbose" | "-v":
        res.verbose = True
        state = expecting_option_or_argument
    when "-n" | "-o" | "--count" | "--output": # these options expect an argument
        current_option = arg
        state = processing_option
    when others:
        print "Unknown option: -", arg
        quit(1)
```

Inline and indented branches mix freely in the same `case`.

## 5.2 Enum dispatch

Enum members appear bare in patterns; the transpiler qualifies them so
Python treats them as value patterns rather than capture names. From
`monty_hall.ady`:

```python
for choice in Choice_T:
    case choice:
        when DontSwitch:
            if candidateFirstChoice == carLocation:
                stayWins += 1
        when Switch:
            let candidateSecondChoice : Door_T = switchOptions'Choice
            if candidateSecondChoice == carLocation:
                switchWins += 1
```

On the Nim side this is a genuine `case` over an enum — meaning the compiler
checks exhaustiveness. `awk_example.ady` dispatches output formatting on a
severity enum the same way:

```python
case sev:
    when ERROR: print f"!! {NR:>3}: {line}"
    when WARN:  print f" ! {NR:>3}: {line}"
    when INFO:
        if NF >= 1:
            let first: str = Fields[0]
            let last:  str = Fields[NF-1]
            print f"[info] NR={NR} NF={NF} first={first}{OFS}last={last}"
        else:
            print f"[info] NR={NR} (empty)"
    when others:
        let joined: str = OFS.join(Fields)
        print f"   {NR:>3}: {joined}"
```

## 5.3 Tuple patterns — multi-dimensional dispatch

When the subject is a tuple expression, each `when` lists one value per
element, with `_` as a wildcard. This turns a two-variable decision table
into code that *looks like* the table. The equipment-replacement model from
`EXAMPLES/test_shortest_path.ady` (example 6) decides what to do with a
machine given the year and the machine's age:

```python
def get_next_decisions(self, current_state: State_T) -> [](Decision_T, Cost_T):
    let (year, age) = current_state
    case (year, age):
        when (6, _):
            []
        when (0, _):
            [(BUY, self.maintenance_cost[0] + self.market_value[0])]
        when (5, _):
            [(SELL, -self.market_value[age])]
        when (_, 3):
            [(TRADE, -self.market_value[age] + self.market_value[0] + self.maintenance_cost[0])]
        when others:
            [
                (KEEP, self.maintenance_cost[age]),
                (TRADE, -self.market_value[age] + self.market_value[0] + self.maintenance_cost[0]),
            ]
```

Nim's `case` cannot take tuple selectors, so the transpiler desugars this to
an `if year == 6: ... elif year == 0: ...` chain; wildcards contribute no
condition.

**The one rule to remember:** the subject must be written as a *structural
expression* — `(year, age)`, `x.kind` — not a plain variable that happens to
hold a tuple. `case state:` with tuple patterns emits a native Nim `case`
and fails to compile. Destructure first (`let (year, age) = state`), then
match on `(year, age)`.

## 5.4 Guards: `match` / `case`

Guards on arbitrary expressions are the reason the Python syntax exists in
Adascript. Classifying command-line tokens in `argparse.ady`:

```python
def get_kind(arg: str) -> Kind_T:
    match arg:
        case "--":
            return cmdEnd
        case _ if arg.startswith("--"):
            return cmdOption
        case _ if arg.startswith("-") and len(arg) > 1:
            return cmdOption
        case _:
            return cmdArgument
```

`EXAMPLES/INTERACTIVE/fsel.ady` — an fzf-based file browser — mixes literal
alternatives, a directory test, and an executability test in one `match`:

```python
match sel:
    case "/" | "..":
        setCurrentDir(sel)
    case _ if -d (f"{cwd}/{sel}"):
        setCurrentDir(sel)
    case _ if key == "right" and -x (f"{cwd}/{sel}"):
        if "/" in sel:
            shell: {sel}
        else:
            shell: {cwd}/{sel}
        quit(0)
    case _:
        shell: {editor} {cwd}/{sel}
        quit(0)
```

(Those `-d` / `-x` operands are Bash-style file tests — Chapter 11.)

## 5.5 Structural patterns — matching variant records

Patterns of the form `TypeName(field=Value, ...)` match against records with
a discriminant. The capitalisation of the right-hand side decides the
meaning:

- `field=VSym` (uppercase) → **equality check** against an enum/constant;
- `field=name` (lowercase) → **capture binding** (`let name = x.field`).

```python
def describe(x: Val_T) -> str:
    case x:
        when Val_T(kind=VSym, sym="if"):   # field equality check
            return "keyword: if"
        when Val_T(kind=VSym, sym=name):   # field capture binding
            return "symbol: " + name
        when Val_T(kind=VNum, num=n):
            return "number"
        when others:
            return "other"
```

## 5.6 Sequence patterns — the interpreter's workhorse

Sequence patterns match a list by length and element structure; `*name`
captures the tail. This is how `lispy.ady` recognises Scheme special forms —
each `when` is a grammar rule:

```python
case x.items:
    when [Val_T(kind=VSym, sym="if"), test, consequence, alternative]:
        ...                                   # (if test conseq alt)
    when [Val_T(kind=VSym, sym="define"), Val_T(kind=VSym, sym=name), expr]:
        ...                                   # (define name expr)
    when [Val_T(kind=VSym, sym=op), *args]:
        ...                                   # (op arg...)
    when others:
        ...
```

The generated Nim is exactly what you would write by hand — length checks,
field comparisons, and `let` bindings for the captures:

```nim
if len(x.items) == 4 and x.items[0].kind == VSym and x.items[0].sym == "if":
    let test = x.items[1]
    let consequence = x.items[2]
    let alternative = x.items[3]
    ...
```

Pattern rules in one box:

- `TypeName(field=Value)` — uppercase → equality check
- `TypeName(field=name)` — lowercase → binding
- `[p0, p1, ..., pN]` — fixed length (`len == N+1`)
- `[p0, *rest]` — at least one element; `rest` gets the tail
- `[]` — empty sequence
- `_` / `others` — catch-all

## 5.7 Regex patterns

A regex literal is a legal `when` pattern; the whole `case` then desugars to
a chain of match tests. The line classifier in `awk_example.ady`:

```python
def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER
```

Four lines, no `import re`, works identically on both backends. Regex
literals get their own chapter (Chapter 7).

## 5.8 Nested state machines

Pattern matching composes: `argparse.ady` runs a token-kind `case` whose
branches contain a parser-state `case` whose branches contain an
option-name `case` — a complete argument parser as three nested decision
tables, with `quit(1)` on the error paths. It is worth reading the full 85
lines of `EXAMPLES/argparse.ady` once; it compresses what argparse-the-library
does with reflection into plain visible control flow.

---

*Next: [Chapter 6 — Collections and Iteration](06-collections-and-iteration.md)*
