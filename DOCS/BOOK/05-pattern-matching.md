# Chapter 5 — Pattern Matching

A pattern-matching block is `case subject:` with one `when pattern:` branch
per alternative, and `when others:` last for everything not named:

```python
case tok:
    when "+" | "-":
        apply_additive(tok)
    when others:
        die(f"unexpected {tok}")
```

`when` is the same word a variant record uses for its arms (§4.4), so one
keyword means "arm of a discriminated choice" everywhere in the language.

Adascript used to offer Python's `match`/`case` alongside this. It no longer
does. The two were one construct with two spellings — the same patterns, the
same guards, the same generated code — and keeping both meant `case` headed
the block in one and a branch in the other, so a reader had to look at the
enclosing line to know which. Convert a `match` block by writing `case` for
`match`, `when` for `case`, and `when others` for `case _`.

## What is checked, and what is not

The reason to write this rather than an `if`/`elif` chain is that the Nim
backend can be made to prove you have covered everything. That guarantee is
narrower than it looks, and it is worth knowing exactly where it holds.

| subject | branches | checked? |
|---|---|---|
| enum | all constants | **yes** — a missing member is a compile error |
| ordinal (int, char) | all constants | **yes** — so a catch-all is in practice required |
| str | all constants | **no** — Nim lets a string `case` fall through |
| any | one or more guarded | **no** — a guard forces the `if`/`elif` lowering |

Where Nim stops checking, Adascript asks for the catch-all instead: a block
with a guarded branch, or with a string subject, is refused unless it has an
unguarded `when others:`. So the safety is continuous even though its source
changes:

```python
case sev:              # enum, no guards: Nim proves the branches are total,
    when LOW:  ...     # and a `when others:` here would only hide a mistake
    when MID:  ...
    when HIGH: ...

case sev:              # a guard, so no proof is possible --
    when LOW if n > 0: ...
    when others: ...   # ... and this is now required
```

`when others` may not itself carry a guard. `others` is everything that is
left, so a condition on it is a contradiction: a guarded catch-all that fails
leaves the block with nothing to do.

Nothing is lost by that, because a condition on the last branch can always be
written inside it — and writing it there is the improvement, since the `else`
becomes impossible to leave out:

```python
case sev:
    when LOW:
        note("low")
    when others:                # everything left, unconditionally
        if n > threshold:       # the condition moves inside, where the
            escalate(sev)       # other outcome has to be written down
        else:
            note("ignored")
```

The other tool is `when _ if cond:`, and it is not the same thing. It is an
ordinary pattern that *declines* when the condition is false, letting a later
branch take the subject, and it does not count as the catch-all. It also
matches whatever the value is, so its position decides what it shadows:

```python
case sev:
    when _ if n > threshold:    # first, so it wins over `when LOW` too
        escalate(sev)
    when LOW:
        note("low")
    when others:                # still required: the wildcard may decline
        note("ignored")
```

Use the first when the last branch has two outcomes; use the second when a
condition should pre-empt the patterns below it.

**None of this is enforced on the Python backend.** Exhaustiveness is a
property of the Nim build, so a block `ady2py` accepts and runs can still be
refused by `ady2nim`. Build with both before believing a block is complete.

## How a block is lowered

On the Python backend a block becomes a `match`/`case` statement, except when
it uses a pattern Python has no syntax for (a regex, a range), in which case
the whole block is lowered to an `if`/`elif` chain. On the Nim backend, a
simple ordinal or string subject becomes a native `case` statement — which is
where the exhaustiveness check above comes from — and anything structural
(tuples, sequences, record patterns, regexes, guards) desugars into
`if`/`elif`/`else`.

## 5.1 Literals and alternatives

Integers, floats, strings, `True`, `False` and `None` all match as literals.
`|` separates alternatives, and every alternative must bind the same names (or
none):

```python
case http_status:
    when 200:
        print("OK")
    when 400 | 401 | 403:
        print("client error")
    when 500 | 502:
        print("server error")
    when others:
        print("unknown")
```

**Nim output** — a native `case`, no runtime overhead beyond the switch:

```nim
case http_status:
    of 200:
        echo("OK")
    of 400, 401, 403:
        echo("client error")
    of 500, 502:
        echo("server error")
    else:
        echo("unknown")
```

Like `if`/`while`, a branch accepts an inline single-statement body, which
makes dispatch tables read like tables. `EXAMPLES/argparse.ady`:

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

Inline and indented branches mix freely in the same block.

## 5.2 Enum patterns

Enum members appear **bare** in patterns. The transpiler qualifies them for
the Python target, because Python's `match` reads a bare name as a capture
that always succeeds — `case Red:` would match everything and shadow `Red`
locally, while `case Colour_T.Red:` is the value test you meant:

| Pattern as written | Python output | Meaning |
|---|---|---|
| `when Red:` | `case Colour_T.Red:` | value test |
| `when x:` (not an enum member) | `case x:` | capture |

Nim needs no such help: it reads a capitalised name in a branch as an enum
value already. From `monty_hall.ady`:

```python
for choice in Choice_T:
    case choice:
        when DontSwitch:
            if candidateFirstChoice == carLocation:
                stayWins += 1
        when Switch:
            let candidateSecondChoice : Door_T = switchOptions'choose
            if candidateSecondChoice == carLocation:
                switchWins += 1
```

On the Nim side this is a genuine `case` over an enum, so the compiler
**checks exhaustiveness**: cover every member and no `others` branch is
needed, and forgetting one is a compile error rather than a silent fall-through.
`awk_example.ady` dispatches output formatting on a severity enum the same
way:

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

## 5.3 Range patterns

`lo .. hi` matches an inclusive range. Ranges are an Adascript extension —
Python's `match` has no range pattern — and they work on integers, characters
and any other ordinal type:

```python
def tier(age: int) -> str:
    case age:
        when 0 .. 12:
            return "child"
        when 13 .. 17:
            return "teen"
        when 18 .. 64:
            return "adult"
        when others:
            return "senior"
```

**Nim output** — one range test per branch inside the native `case`:

```nim
proc tier(age: int): string =
    case age:
        of 0 .. 12:
            return "child"
        of 13 .. 17:
            return "teen"
        of 18 .. 64:
            return "adult"
        else:
            return "senior"
```

**Python output** — no range pattern exists, so the block becomes a chain
that compares against the subject:

```python
def tier(age: int) -> str:
    if 0 <= age <= 12:
        return "child"
    elif 13 <= age <= 17:
        return "teen"
    elif 18 <= age <= 64:
        return "adult"
    else:
        return "senior"
```

Character ranges classify without a single library call:

```python
def kind(ch: char) -> str:
    case ch:
        when 'a' .. 'z':
            return "lower"
        when '0' .. '9':
            return "digit"
        when others:
            return "other"
```

A bound may be a named constant, but on the Nim backend it has to be a
`const`: Nim evaluates `case` ranges at compile time, and a `let` bound is
rejected with *cannot evaluate at compile time*.

```python
const MAX_AGE: int = 120

case age:
    when 65 .. MAX_AGE:
        return "senior"
    when others:
        return "other"
```

A block containing a range lowers to an `if`/`elif` chain on both backends,
since Python has no range pattern for the target to use.

## 5.4 Captures and `as` bindings

A bare lowercase name is a capture: it always matches and binds the subject
to that name for the branch body. In structural positions, captures are how
you take a value apart:

```python
case response:
    when [first, *rest]:
        print(f"first: {first}, {len(rest)} more")
    when []:
        print("empty")
```

**Nim output** — the bindings become `let`s at the top of the branch:

```nim
if len(response) >= 1:
    let first = response[0]
    let rest = response[1..response.high]
    echo(fmt"first: {first}, {len(rest)} more")
elif len(response) == 0:
    echo("empty")
```

`as` names the whole matched value while the inner pattern still decomposes
it:

```python
case items:
    when [first, *_] as whole:
        return str(first) + "/" + str(len(whole))
    when []:
        return "empty"
```

```nim
if len(items) >= 1:
    let whole = items
    let first = items[0]
    return $first & "/" & $len(whole)
elif len(items) == 0:
    return "empty"
```

`as` attaches to a single pattern. `case 400 | 401 as code:` — an `as` over an
alternation — is not accepted; bind in the body instead, or give each
alternative its own branch.

## 5.5 Sequence patterns

Sequence patterns match a list by length and element structure. `*name`
captures the tail, `*_` discards it, and `[]` matches only the empty list:

```python
case parts:
    when [host, port]:
        connect(host, int(port))
    when [host]:
        connect(host, 80)
    when []:
        raise ValueError("empty address")
    when others:
        raise ValueError("too many components")
```

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

Literals may sit inside a sequence pattern, which is how you recognise a
prefix — a keyword, a magic number, a byte-order mark:

```python
case tokens:
    when ["if", cond, "then", *body]:
        parse_if(cond, body)
    when ["while", cond, "do", *body]:
        parse_while(cond, body)
    when [keyword, *_]:
        raise SyntaxError(f"unexpected keyword: {keyword}")
```

This is the interpreter's workhorse. `lispy.ady` recognises Scheme special
forms with one `when` per grammar rule:

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

## 5.6 Class and record patterns

`TypeName(field=pattern, ...)` matches an object by its fields. Only the
keyword form is supported — positional class patterns (`Point(0, y)`) are
not, because field order is not knowable at the pattern site. Fields you do
not mention are ignored, so a pattern can be as partial as you like.

The capitalisation of the right-hand side decides the meaning:

- `field=VSym` (uppercase) → **equality check** against an enum or constant;
- `field=name` (lowercase) → **capture binding** (`let name = subject.field`).

```python
type Token_T is record:
    kind:  str
    lexem: str

def compile_token(tok: Token_T) -> str:
    case tok:
        when Token_T(kind="INT", lexem=v):
            return "int " + v
        when Token_T(kind="OP", lexem="+"):
            return "plus"
        when Token_T(kind=k, lexem=v):
            return k + " " + v
```

**Nim output** — field access conditions, and a `let` per capture:

```nim
proc compile_token(tok: Token_T): string =
    if tok.kind == "INT":
        let v = tok.lexem
        return "int " & v
    elif tok.kind == "OP" and tok.lexem == "+":
        return "plus"
    elif true:
        let k = tok.kind
        let v = tok.lexem
        return k & " " & v
```

Variant records — records with a discriminant — are matched the same way, on
the discriminant field plus whichever payload fields the branch needs:

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

## 5.7 Tuple subjects — multi-dimensional dispatch

When the subject is a tuple expression, each branch lists one value per
element, with `_` as a wildcard. A two-variable decision table becomes code
that *looks like* the table. A state machine in four lines:

```python
def step(state: State_T, event: Event_T) -> State_T:
    case (state, event):
        when (Idle, Start):
            return Running
        when (Running, Stop):
            return Done
        when others:
            return state
```

```nim
proc step(state: State_T, event: Event_T): State_T =
    if state == Idle and event == Start:
        return Running
    elif state == Running and event == Stop:
        return Done
    else:
        return state
```

Every non-`_` element of a tuple pattern is a **value test**, not a capture —
including lowercase names, which are compared against whatever they hold. To
take a tuple apart, destructure it first and then match on the parts.

The equipment-replacement model in `EXAMPLES/test_shortest_path.ady`
(example 6) decides what to do with a machine given the year and the
machine's age:

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

**The one rule to remember:** the subject must be written as a *structural
expression* — `(year, age)`, `x.kind` — not a plain variable that happens to
hold a tuple. `case state:` with tuple patterns emits a native Nim `case`,
which rejects a runtime tuple and fails to compile. Destructure first
(`let (year, age) = state`), then match on `(year, age)`.

## 5.8 Guards

An `if` after a pattern adds a runtime condition that structure cannot
express — a membership test, a prefix check, a comparison between two
captures. Both spellings take one (`when pat if cond:` as well as
`case pat if cond:`); the guard is evaluated only once the pattern itself has
matched, and a guarded block always lowers to an `if`/`elif` chain, since
Nim's `case` takes no guard.

```python
def pairs(items: []int) -> str:
    case items:
        when [a, b] if a > b:
            return "descending"
        when [a, b] if a == b:
            return "equal"
        when [a, b]:
            return "ascending"
        when others:
            return "not a pair"
```

**Nim output** — the captures the guard talks about are substituted into the
condition, since Nim has no bindings in scope before the branch is entered:

```nim
proc pairs(items: seq[int]): string =
    if len(items) == 2 and (items[0]) > (items[1]):
        let a = items[0]
        let b = items[1]
        return "descending"
    elif len(items) == 2 and (items[0]) == (items[1]):
        let a = items[0]
        let b = items[1]
        return "equal"
    elif len(items) == 2:
        ...
```

Classifying command-line tokens in `argparse.ady`:

```python
def get_kind(arg: str) -> Kind_T:
    case arg:
        when "--":
            return cmdEnd
        when _ if arg.startswith("--"):
            return cmdOption
        when _ if arg.startswith("-") and len(arg) > 1:
            return cmdOption
        when others:
            return cmdArgument
```

`EXAMPLES/INTERACTIVE/fsel.ady` — an fzf-based file browser — mixes literal
alternatives, a directory test, and an executability test in one block:

```python
case sel:
    when "/" | "..":
        setCurrentDir(sel)
    when _ if -d (f"{cwd}/{sel}"):
        setCurrentDir(sel)
    when _ if key == "right" and -x (f"{cwd}/{sel}"):
        if "/" in sel:
            shell: {sel}
        else:
            shell: {cwd}/{sel}
        quit(0)
    when others:
        shell: {editor} {cwd}/{sel}
        quit(0)
```

(Those `-d` / `-x` operands are Bash-style file tests — Chapter 11.)

Guards are also where you put the checks that have no pattern syntax at all:

```python
case token:
    when s if s.startswith("0x"):
        return int(s, 16)
    when s if s.isdigit():
        return int(s)
    when s:
        raise ValueError(f"not a number: {s}")
```

## 5.9 Regex patterns

A regex literal is a legal pattern; the block then desugars to a chain of
case tests on both backends. The line classifier in `awk_example.ady`:

```python
def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER
```

Four lines, no `import re`, identical behaviour on both backends. Regex
literals get their own chapter (Chapter 7).

## 5.10 Nested patterns

Patterns compose: any position inside a pattern is itself a pattern, so
sequences of records, records containing sequences, and literals inside
either all work:

```python
case events:
    when [MouseClick(x=x, y=y), *_]:
        handle_first_click(x, y)
    when [KeyPress(key="Escape"), *_]:
        cancel()
    when []:
        idle()
```

`argparse.ady` takes this further and nests whole blocks: a token-kind `case`
whose branches contain a parser-state `case` whose branches contain an
option-name `case` — a complete argument parser as three nested decision
tables, with `quit(1)` on the error paths. It is worth reading the full 85
lines of `EXAMPLES/argparse.ady` once; it compresses what argparse-the-library
does with reflection into plain visible control flow.

## 5.11 Pattern reference

| Pattern | Written | Nim output |
|---------|---------|------------|
| Literal | `when 42:` | `of 42:` |
| String | `when "ok":` | `of "ok":` |
| Bool | `when True:` | `of true:` |
| `None` | `when None:` | presence test (Chapter 10) |
| Wildcard | `when others:` | `else:` |
| Capture | `when x:` | `let x = subject` |
| Alternatives | `when 1 \| 2:` | `case 1 \| 2:` | `of 1, 2:` |
| Enum value | `when Red:` | `of Red:` |
| Range | `when 1 .. 10:` | `of 1 .. 10:` |
| Fixed sequence | `when [a, b]:` | `if len == 2: let ...` |
| Sequence + tail | `when [a, *xs]:` | `if len >= 1: let ...` |
| Empty sequence | `when []:` | `if len == 0:` |
| Record / class | `when P(x=0, y=y):` | `if subj.x == 0: let y = subj.y` |
| Tuple subject | `when (a, _):` | `if s0 == a:` |
| `as` binding | `when pat as n:` | `let n = subject` |
| Guard | `when pat if cond:` | `if ... and cond:` |
| Regex | `when /err/i:` | `nimatch(subject, re"(?i)err")` |

## 5.12 What is not supported

Four Python pattern features are deliberately absent, each because it has no
clean compilation path on the Nim side. Each has a one-line rewrite.

**Mapping (dict) patterns.** Nim has no structural dict matching:

```python
# not supported
case config:
    when {"host": h, "port": p}:
        connect(h, p)

# instead — test membership, then read
if "host" in config and "port" in config:
    connect(config["host"], config["port"])
```

**Positional class patterns.** Field order is not knowable at the pattern
site, so name the fields:

```python
case point:
    when Point_T(0, y): ...      # not supported
    when Point_T(x=0, y=y): ...  # supported
```

**Structural patterns inside an alternation.** Alternatives must be simple
values; split them into separate branches:

```python
case x:
    when Point_T(x=0) | Circle_T(radius=0): ...   # not supported

    when Point_T(x=0):
        handle_zero()
    when Circle_T(radius=0):
        handle_zero()
```

**`as` over an alternation** — `case 400 | 401 as code:` — is not accepted
either; bind in the body (`let code = status`) or give each alternative its
own branch.

## 5.13 Choosing a syntax

Both spellings compile to the same code, so the choice is about who reads the
file.

Reach for a `case` block over an `if`/`elif` chain when the subject is an
enum and the branches are constants: that is the one shape where Nim proves
the dispatch is total, and the proof is the whole reason the construct earns
its keep.

```python
# Adascript style for the enum dispatch
case score:
    when 90 .. 100: grade = "A"
    when 80 ..  89: grade = "B"
    when others:    grade = "C or below"

# Python style for the structural match
case result:
    when Ok_T(value=v):
        process(v)
    when Err_T(msg=m):
        log(m)
```

---

*Next: [Chapter 6 — Collections and Iteration](06-collections-and-iteration.md)*
