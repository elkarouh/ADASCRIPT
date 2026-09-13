# Adascript for AWK Programmers

AWK got one thing profoundly right: a program is a set of *patterns* and
*actions*, the input is split into records and fields for you, and the
plumbing — open, read, loop, close — is not your problem. Thirty years on,
that is still the fastest way to write a report over a log file.

What AWK gets wrong is everything past the first hundred lines. There is one
scalar type, and it is "string that is sometimes a number". Every state
machine is an integer flag. Every enumeration is a string constant nobody
checks. Every record is a set of parallel arrays with a shared index. `$3`
means nothing to the next reader, and nothing at all to the compiler.

Adascript keeps AWK's shape and replaces its type system. This document is
for someone who already thinks in records and fields and wants to know what
that buys them.

Every example quoted here is a real, runnable file under `EXAMPLES/`, and
`make test` runs it. Most run on **both** backends — `ady2nim` and `ady2py`;
the one exception is `awk_logscan.ady`, whose `AwkBase` form is Nim-only
(§2). §10 works through three of them, built up in stages: no state, then
one record shape or another, then a state machine deciding which shape a
record even is.

---

## 1. The problem

Before any syntax, the shape of the job. It is the same job every time, and
naming its five parts is what makes the rest of this document a list of
answers rather than a list of features.

**There is a file, and it holds records.** Not rows of one table — records.
A log, a dump, a report, a protocol trace, a configuration.

**A record is usually a line, and sometimes it is not.** One line per record
is the common case and the default everywhere. But a record can span several
lines and be closed by a blank line, or by a marker of its own, or by nothing
at all except the next record starting. Anything that assumes "record ==
line" has to be rewritten from scratch the first time that stops being true.
`RS` is AWK's answer and Adascript keeps it (§2.1).

**The records are not all of the same kind.** A file of build output holds
user lines, host lines, config lines and result lines; an application log
holds events and stack traces. They have different fields, they mean
different things, and a program that treats them as one shape ends up with a
row of mostly-empty columns and a comment explaining which ones apply.

**Which kind a record is may depend on the records before it.** This is the
part that turns a filter into a program. A stack trace carries no timestamp,
so nothing *in* the line says whom it belongs to — only the fact that the
line before it was a failure. AWK spells this with an integer flag and a
condition repeated on every pattern. It is a **state machine**, and saying so
out loud is most of the work: the state decides which kind of record you are
looking at, and reaching a new kind is what changes the state.

**What comes out is one or more lists of similar records, which are then
post-processed — and some of the work happens on the way past.** A running
total needs no second pass and should not wait for one. A median, a ranking,
a join between two of the lists, "which requests have no trace" — those
cannot be answered until every record is in hand. Both kinds of work belong
in the same program, and the difference between them is worth being
deliberate about.

Everything below is one of those five points answered. The worked example in
§10.3 is all five at once.

---

## 2. The shape of a program

AWK's implicit loop has two spellings in Adascript, and the choice is about
how much state you carry.

### The flat form

For a filter, iterate `stdin.lines` and be done. `EXAMPLES/awk_example.ady`
is this shape (quoted in full in §10.1):

```python
def main():
    for raw in stdin.lines:
        process(raw)
```

`stdin` has type `File`, and so does `open(path)` — the same variable holds
either, so the loop is written once:

```python
let f: File = (open(file_arg) if file_arg != "" else stdin)
for line in f.lines:
    print indent_line(line)
```

`.lines` strips the newline, which is what `$0` does and what you wanted.

### The AwkBase form

When the program is a state machine — when what a record *means* depends on
the records before it — subclass `AwkBase` from the bundled library
(`TO_NIM/STDLIB/awk.ady`) and override three methods:

```python
nimport awk

class LogScan(AwkBase):
    def start(self):           # awk's BEGIN
        ...
    def process_record(self):  # the pattern/action body
        ...
    def finish(self):          # awk's END
        ...

LogScan().run()
```

`AwkBase` gives you the AWK variables under their own names: `self.line` is
`$0`, `self.Fields[1] .. self.Fields[NF]` are `$1 .. $NF` (`Fields[0]` is the
whole record, exactly as in AWK), and `self.NR`, `self.NF`, `self.FS`,
`self.OFS`, `self.RS`, `self.ORS` are what you expect. `run_file(path)` is
the same loop over a named file.

One caveat: `nimport` means "a module the Nim backend provides", so the
`AwkBase` form is Nim-only. The flat form runs on both backends.

### 2.1 When a record is not a line

`RS` is the record separator, and setting it is the whole of the answer to
§1's second point. Pass it at construction and the loop changes shape
underneath you — `AwkBase` reads the input whole and splits on `RS` instead
of iterating lines:

```python
class Para(AwkBase):
    def process_record(self):
        print f"record {self.NR}: NF={self.NF} [{self.line}]"

def main():
    var p: Para = Para(rs = "\n\n")      # a blank line ends a record
    p.run()
```

Fed a file of blank-line-separated stanzas:

```
User: alice
Host: build01

User: bob
Host: build02

User: carol
Host: build03
```

it prints:

```
record 1: NF=4 [User: alice
Host: build01]
record 2: NF=4 [User: bob
Host: build02]
record 3: NF=4 [User: carol
Host: build03]
```

`self.line` is the whole multi-line record and the fields run across the
newlines, which is what AWK's paragraph mode does. Any other separator works
the same way — `rs = "%%\n"` for a marker, `rs = "\x1e"` for a record
separator byte. Nothing else in the program changes: `process_record` still
gets one record at a time and still does not know how the input was cut up.

The cost is the one AWK has too — a non-newline `RS` reads the input whole
rather than streaming it, so it is for files that fit in memory. The default
`rs = "\n"` streams.

---

## 3. Patterns: `case` instead of a pattern list

An AWK program is a list of `pattern { action }` pairs, tried in order.
Adascript writes the same thing as a `case` over the record, and a `when`
takes a regex literal:

```python
def classify(s: str) -> Severity_T:
    case s:
        when /error|fatal/i: return ERROR
        when /warn/i:        return WARN
        when /info|debug/i:  return INFO
        when others:         return DEBUG
```

The `i` is a flag on the literal, not an argument to a function. Literal
strings, regexes and ranges mix freely in one `case`:

```python
case F[1]:
    when "Showing" if self.NF >= 12:              # a literal, plus a guard
        self._showing(F)
    when "User:" if self.NF >= 2:
        self._open_build()
        self.current_build.user = F[2]
    when "Host:" if self.NF >= 2:
        self.current_build.host      = F[2]
        self.current_build.test_mode = "REGRESS"
        self.newhost = True
    when /TACT\.TACT_CONFIG|IFPS\.FPL_CONFIG/:    # a regex
        self._config(F)
    when others:
        pass
```

That is from `EXAMPLES/CFMU/Tstatus_monitor.ady`, a translation of a real
AWK script. The guard — `if self.NF >= 12` — is the `pattern && condition`
you would have written in AWK, except that it sits with the pattern instead
of at the top of the action.

**The rule worth knowing:** when a `case` has a guard, or the subject is a
string, the Nim backend requires an unguarded `when others:`. A guard can
decline, and a string has no finite domain, so without a catch-all some
input would fall through the whole block silently. The compiler will not let
you write that. Over an enum subject, no catch-all is needed — and then the
compiler checks that you covered every member, which is the check AWK could
never give you.

---

## 4. Regex is syntax

There is never an `import re`. A pattern is a literal, matching is an
operator, captures are variables.

```python
let line: str = "2026-09-11 ERROR disk full on /var/log"

assert line == /ERROR|FATAL/
assert line != /^#/
```

Captures come back as `$+1`, `$+2`, … with `$+0` the whole match:

```python
if line == /^(\d{4})-(\d{2})-(\d{2}) (\w+)/:
    assert $+1 == "2026"
    assert $+4 == "ERROR"
```

Named groups use `(?P<name>...)` and read back as `$+{name}`.

The `g` flag turns the match test into a list of every match — this is AWK's
`split` with a regex, and rather more:

```python
let nums: []str = "a1 b22 c333" == /\d+/g
assert nums == ["1", "22", "333"]
```

Substitution is Perl's, and assigns back to the left-hand side, so the
target is a `var`:

```python
var path: str = "/var/log/app.log.gz"
path == s/\.gz$//g
assert path == "/var/log/app.log"

var stamp: str = "2026-09-11"
stamp == s/(\d{4})-(\d{2})-(\d{2})/$+3.$+2.$+1/g
assert stamp == "11.09.2026"
```

`sub` and `gsub` in one form: without `g` it replaces the first match, with
`g` all of them.

---

## 5. Enums: the thing AWK has no word for

This is the centre of the argument. In AWK a severity is a string, a parser
state is an integer, and a status class is a key you hope you spelled the
same way in both places. In Adascript each is a type.

```python
type Severity_T   is enum DEBUG, INFO, WARN, ERROR
type Scan_State_T is enum OUTSIDE, IN_TRACE
type Status_T     is enum SUCCESS, REDIRECT, CLIENT_ERROR, SERVER_ERROR, ODD

type Request_T is record:
    """One served request, taken apart by a single regex."""
    at:      str     = ""
    verb:    str     = ""
    path:    str     = ""
    status:  Natural = 0
    ms:      Natural = 0

type Trace_T is record:
    """One stack trace: several lines, belonging to the request before it."""
    under:   str     = ""      # the request it followed
    lines:   Natural = 0
    failure: str     = ""      # the exception line that ends it
```

A `case` over that type is checked for completeness — leave out `WARN` and
the Nim backend refuses the program. No `when others:` is needed, and adding
a fifth member turns every `case` over the type into a compile error listing
the places you have to think about. That is the refactoring AWK cannot help
you with at all.

Guards work here too, and are what makes a catch-all necessary again:

```python
def prefix(sev: Severity_T, nr: Natural) -> str:
    case sev:
        when ERROR:            return "!!"
        when WARN if nr < 10:  return " !"   # only shout early
        when others:           return "  "
```

The type answers questions about itself, through tick attributes borrowed
from Ada:

```python
assert ERROR'Image      == "ERROR"    # the name, for printing
assert Severity_T'First == DEBUG
assert Severity_T'Last  == ERROR
assert Severity_T("WARN") == WARN     # and back from a string
```

And it can index an array, which is AWK's associative array with the typos
removed and the iteration order fixed:

```python
var counts: [Severity_T]Natural = [DEBUG: 0, INFO: 0, WARN: 0, ERROR: 0]
counts[classify("warn: hot")] += 1
assert counts[WARN] == 1

for s in Severity_T:                  # every member, in declaration order
    print f"  {s'Image:<5} {counts[s]}"
```

`counts["WANR"]` is not a subtle bug that shows up as a zero in a report six
months later. The Nim backend rejects it at compile time — "type mismatch",
at that line — and the Python backend raises a `KeyError` there rather than
quietly creating a fifth bucket, which is what AWK would have done.

---

## 6. Numbers that cannot be wrong

`Natural` is an integer that cannot go below zero; `Positive` is one that
cannot reach it. They are range-checked at run time on the Nim backend —
including under `-d:release`.

```python
var NR        : Natural = 0
var total_len : Natural = 0
```

This is documentation that the compiler enforces. A counter that goes
negative is a bug you find at the moment it happens, with the line number,
instead of as a nonsense average at the end of the report.

---

## 7. Records instead of parallel arrays

The AWK idiom is `user[i]`, `host[i]`, `build[i]` and an `i` you increment by
hand. A record names the row:

```python
type Request_T is record:
    """One served request, taken apart by a single regex."""
    at:     str = ""
    verb:   str = ""
    path:   str = ""
    status: Natural = 0
    ms:     Natural = 0
```

Fields have defaults, so `Request_T()` is a complete zero row, and a
construction names what it sets:

```python
let req: Request_T = Request_T(at=$+1, verb=$+4, path=$+5, status=int($+6), ms=int($+7))
```

Pulling the fields out of a record beats pulling them out of `$1 $2 $3`
mostly because of what it does six months later: `req.ms > self.slowest.ms`
survives a change to the log format, `$7 > slowest[7]` does not.

### 7.1 One of several shapes: the variant record

A plain record gives every row the same fields. When the rows are genuinely
*different* — a schema in which a number has bounds and a choice has a word
list — Ada's answer is a record whose field set depends on an enum
discriminant, and Adascript adopts the syntax:

```python
type Kind_T is enum FLAG, NUMBER, CHOICE, PATHNAME

type Spec_T (kind: Kind_T) is record:
    case kind is
        when FLAG:
            on_by_default: bool
        when NUMBER:
            lo: int
            hi: int
        when CHOICE:
            allowed: []str
        when PATHNAME:
            must_exist: bool
```

Reading `s.lo` where `s.kind` is `CHOICE` is not a mistake to be careful
about. On the Nim backend the field is not there to read at all. And a `case`
over the discriminant needs no `when others:` — the enum has four members, so
the compiler checks that all four are handled:

```python
def describe(s: Spec_T) -> str:
    case s.kind:
        when FLAG:     return "a flag"
        when NUMBER:   return f"a whole number in {s.lo} .. {s.hi}"
        when CHOICE:   return "one of " + ", ".join(s.allowed)
        when PATHNAME: return "a path that must exist" if s.must_exist else "a path"
```

In AWK this is `kind[i]`, `lo[i]`, `hi[i]`, `allowed[i]` and a convention
about which of them are meaningful for a given `i` — written down in a
comment if you were lucky. `EXAMPLES/config_check.ady` is a configuration
checker whose whole schema is one variant record; §10.2 walks through it.

---

## 8. Missing is not the empty string

AWK's uninitialised variable is `""` and also `0`, and a field that is
genuinely empty is indistinguishable from one that is not there. `?T` is the
type that can tell:

```python
def field(fs: []str, i: Natural) -> ?str:
    if i >= fs'Length:
        return None
    return fs[i]

assert (field(F, 1) or "-") == "ERROR"
assert field(F, 99) == None
```

`or` supplies a default on absence only — a present-but-empty value survives
it. The same distinction reaches the environment: `$NAME` is a `str` that
reads unset as `""`, `$?NAME` is a `?str` that can tell unset from empty, and
`${NAME:-default}` is the shell's fallback.

### 8.1 Getting a value in and out of a `?T`

You never write `some()` or `none()`. A plain value put where a `?T` is
expected is **lifted** for you, and `None` becomes the empty one:

```python
type Finding_T is record:
    line: ?Natural = None
    text: str      = ""

let n: Natural = 12
let maybe: ?Natural = n                              # a declaration lifts
let one:   Finding_T = Finding_T(line=n, text="on a line")     # so does a field
let none_: Finding_T = Finding_T(text="about the file")        # left out: None
```

Getting the value back out is the half worth reading carefully, because a
`?T` and a `T` are different types and the Nim backend says so — `maybe == 12`
does not compile. Two ways out:

```python
assert (maybe or 0) == 12          # `or` supplies a default
assert none_.line == None          # comparing against None is always fine
```

...and, for the case where you have already established it is there, an
**early-return guard**, which narrows the name below it to a plain `Natural`:

```python
def where(f: Finding_T) -> str:
    let ln: ?Natural = f.line      # bind it to a name first
    if ln is None:
        return ""
    return "line " + str(ln)       # a plain Natural from here on
```

That first line is not ceremony. The guard narrows a **name**, and `f.line`
is a field access rather than a name, so `if f.line is None: return` leaves
the field an `Option` below it — on Nim `str(f.line)` then prints `some(12)`
where Python prints `12`. Binding it first is what makes the two backends
agree. (It is a wart, and it is in `TODO.md`.)

The point of all this is what it replaces. AWK's `line[i]` is `""` when the
finding has no line, `""` when the line number was never filled in, and `0`
if you compare it to a number — three different situations wearing the same
face. `?Natural` distinguishes "no line" from "line 0", and nothing reads the
value without first saying which case it is in.

---

## 9. The shell, without `system()`

AWK shells out through `system()` and `"cmd" | getline`, with quoting left
to you. In Adascript a command is a statement:

```python
let (greeting, rc) = shell: echo hello world
assert rc == 0
assert greeting.strip() == "hello world"
```

A value goes in braces. `{x}` puts it in as written, which is what a command
fragment wants; `{!x}` quotes it, so a path holding spaces arrives as one
argument instead of two:

```python
let dir: str = "/tmp"
let (count_out, _) = shell: ls -1d {!dir}
```

`run(["ls", dir])` skips the shell altogether, and then there is nothing to
quote because nothing parses the arguments twice.

A pipeline can report the first failure rather than the last, and a long
output can be streamed instead of held:

```python
let (_, pipe_rc) = shell(pipefail = true): false | cat
assert pipe_rc != 0

var seen: Natural = 0
for l in shellIter: printf 'a\nb\nc\n'
    seen += 1
assert seen == 3
```

Arguments, the environment and the shell's file tests come across as they
are:

```python
assert $HOME != ""
assert $NO_SUCH_VAR_HERE == ""
assert ${NO_SUCH_VAR_HERE:-"fallback"} == "fallback"
assert $?NO_SUCH_VAR_HERE == None

if -f path:    ...    # and -d -e -L -r -w -x -s, plus a -nt b
if have("git"): ...   # is it even installed?
```

---

## 10. Worked examples

The rest of this document is vocabulary. These three files put it to work,
in the order complexity actually arrives in practice: no state, then one
record shape or another, then a state machine deciding which shape a record
even is. Each is a complete, runnable program — `make test` runs all three —
and each is quoted here as it actually stands in `EXAMPLES/`, not as a
simplified stand-in for it.

### 10.1 No state: `awk_example.ady`

The plainest case first: one kind of record, no memory of the records
before it. This is §2's flat form, in full — every line is classified and
printed on its own, and nothing about line *N* depends on line *N-1*:

```python
#!/usr/bin/env ady2nim
"""
awk-style line processor.

Usage:
    ./awk_example < FILE                   # FS = whitespace
    cat FILE | ./awk_example ,             # FS = comma
    cat FILE | ./awk_example '\t'          # FS = tab
"""
type Severity_T is enum INFO, WARN, ERROR, OTHER


var FS        : str = " "
var OFS       : str = " "
var NR        : Natural = 0
var NF        : Natural = 0
var total_len : Natural = 0
var total_nf  : Natural = 0
var counts    : [Severity_T]Natural = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]

if $# > 0:
    FS = $1

def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER


def process(raw: str):
    let line: str = raw.rstrip()
    NR += 1
    let Fields: []str = (line.split() if FS == " " else line.split(FS))
    NF = Fields'Length
    total_len += line'Length
    total_nf  += NF

    let sev: Severity_T = classify(line)
    counts[sev] += 1

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


def main():
    print "--- awk report ---"
    print f"FS = {repr(FS)}"

    for raw in stdin.lines:
        process(raw)

    print ""
    print "--- summary ---"
    print f"records : {NR}"
    if NR > 0:
        let avg_len: float = total_len / NR
        let avg_nf:  float = total_nf  / NR
        print f"avg len : {avg_len:.2f}"
        print f"avg NF  : {avg_nf:.2f}"
    for s in Severity_T:
        print f"  {s:<6} {counts[s]}"


main()
```

Nothing here needs `AwkBase` at all — module-level `var`s stand in for `NR`
and the running totals, and `for raw in stdin.lines: process(raw)` is the
whole loop. `Severity_T` is doing real work even in the simplest case: a
severity is a type from the first line of the program, not a string
convention `classify` and every caller have to agree on separately.

### 10.2 One shape or another: `config_check.ady`

Still no state carried between records — but now the records are not all
the same shape. `config_check.ady` checks a config file against a schema
where a setting is a flag, a bounded number, a word from a list, or a path,
and a variant record gives each shape only the fields that shape has (§7.1):

```python
type Kind_T is enum FLAG, NUMBER, CHOICE, PATHNAME

type Spec_T (kind: Kind_T) is record:
    case kind is
        when FLAG:
            on_by_default: bool
        when NUMBER:
            lo: int
            hi: int
        when CHOICE:
            allowed: []str
        when PATHNAME:
            must_exist: bool
```

Checking a value is a `case` over the same discriminant, and each branch
reads only the fields its own shape declares — `s.lo` inside the `CHOICE`
branch is not a mistake to be careful about; on the Nim backend the field is
not there to read. (`TRUE_WORDS` and `FALSE_WORDS` are two module-level word
lists defined earlier in the file.)

```python
def check_value(s: Spec_T, value: str) -> str:
    """Empty means the value is fine; otherwise the complaint."""
    case s.kind:
        when FLAG:
            if value.lower() in TRUE_WORDS or value.lower() in FALSE_WORDS:
                return ""
            return f"'{value}' is not a yes/no word"
        when NUMBER:
            if value != /^-?\d+$/:
                return f"'{value}' is not a whole number"
            let n: int = int(value)
            if n < s.lo or n > s.hi:
                return f"{n} is outside {s.lo} .. {s.hi}"
            return ""
        when CHOICE:
            if value in s.allowed:
                return ""
            return f"'{value}' is not one of " + ", ".join(s.allowed)
        when PATHNAME:
            if s.must_exist and not -d Path(value):
                return f"'{value}' is not an existing directory"
            return ""
```

The schema itself is a plain dict from setting name to `Spec_T`, which is
where AWK's associative array is doing fine — the shape that needs the
variant record is the *value*, not the lookup:

```python
let SCHEMA: {str}Spec_T = {
    "verbose":  Spec_T(kind=FLAG,     on_by_default=False),
    "workers":  Spec_T(kind=NUMBER,   lo=1, hi=64),
    "mode":     Spec_T(kind=CHOICE,   allowed=["fast", "safe", "paranoid"]),
    "log_dir":  Spec_T(kind=PATHNAME, must_exist=True),
    "cache_dir":Spec_T(kind=PATHNAME, must_exist=False),
}
```

`check()` reads the file line by line, matches `key = value` with a regex,
looks the key up in `SCHEMA`, and calls `check_value` — no state carried
from one line to the next, only a `seen` set so a key set twice is a warning
rather than silently keeping the last one. The full file, with the report
loop and the self-contained fixture `main()` writes under `/tmp`, is in
`EXAMPLES/config_check.ady`.

### 10.3 A state machine: `awk_logscan.ady`

`EXAMPLES/awk_logscan.ady` is §1's five points in one file. An application
log holds **two kinds of record**: timestamped events, and the stack traces
that follow a failure. A trace carries no timestamp, so nothing in the line
says whom it belongs to — only **the state the scanner is in**. Each kind is
gathered into **its own list**, some work is done **on the way past** and the
rest **once both lists are complete**.

Three enums and two record types carry it:

```python
type Severity_T   is enum DEBUG, INFO, WARN, ERROR
type Scan_State_T is enum OUTSIDE, IN_TRACE
type Status_T     is enum SUCCESS, REDIRECT, CLIENT_ERROR, SERVER_ERROR, ODD

type Request_T is record:      # a timestamped event
    at:      str     = ""
    verb:    str     = ""
    path:    str     = ""
    status:  Natural = 0
    ms:      Natural = 0

type Trace_T is record:        # the lines after a failure
    under:   str     = ""      # the request it followed
    lines:   Natural = 0
    failure: str     = ""      # the exception line that ends it
```

**The two lists, and the totals kept on the way past:**

```python
class LogScan(AwkBase):
    var state    : Scan_State_T          = OUTSIDE

    # One list per kind of record. Both are complete by finish().
    var requests : []Request_T           = []
    var traces   : []Trace_T             = []

    # Counted on the way past, because a total needs no second pass.
    var counts   : [Severity_T]Natural   = [DEBUG: 0, INFO: 0, WARN: 0, ERROR: 0]
    var by_status: [Status_T]Natural     = [SUCCESS: 0, REDIRECT: 0, CLIENT_ERROR: 0,
                                            SERVER_ERROR: 0, ODD: 0]

    var open_trace: Trace_T              = Trace_T()
```

**The state machine decides which kind of record this is**, and the `case`
over the state is the *whole* dispatch — one branch per state, and nothing
outside it:

```python
def process_record(self):
    case self.state:
        when OUTSIDE:  self._outside()
        when IN_TRACE: self._in_trace()
```

That shape is worth copying, and it is not the obvious one. The tempting
version tests for the state you care about, falls through, and handles the
other state in the code *below* the `case` — at which point the `case` is a
pre-check rather than a dispatch, one state's handling sits nowhere near the
other's, and the block needs a `when others:` to paper over the state that
appears to do nothing.

With one branch per state there is no `when others:`, and that is what buys
the check. Delete a branch and the Nim backend refuses the program:

```
Error: not all cases are covered; missing: {IN_TRACE}
```

Add a third state later and every `case` over the type names itself as a
place you have to think about. In AWK this is an integer flag and a condition
repeated on the front of every pattern, and nothing tells you when you miss
one.

**Each branch is a handler for the records valid in that state.** Between
traces, a record is an event, the start of a trace, or noise. One regex takes
an event apart, and the groups go straight into a record:

```python
def _outside(self) -> None:
    """Between traces: a record is an event, the start of one, or noise."""
    # One regex takes the record apart; $+1 .. $+7 are its groups.
    case self.line:
        when /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+) +(\w+) (\S+) (\d{3}) (\d+)ms$/:
            let req: Request_T = Request_T(at=$+1 + " " + $+2, verb=$+4, path=$+5,
                                           status=int($+6), ms=int($+7))
            let sev: Severity_T = Severity_T($+3.upper())
            self.requests.append(req)
            self._event(sev, req)
        when /^Traceback |^[A-Z]\w+(Error|Exception): /:
            self.state = IN_TRACE
            self._in_trace()
        when others:
            pass                      # a line belonging to neither kind
```

`Severity_T($+3.upper())` is worth a second look. The log writes `INFO`,
`WARN`, `ERROR` as text; that turns the text into a value of the type, and a
log line carrying a severity nobody declared fails there, at the line that
read it, rather than becoming a silent extra bucket in the report.

The second branch is deliberately thin: recognising the line that *starts* a
trace is not the same job as setting one up, so `_outside()` only flips the
state and hands the very same record straight to `_in_trace()` — the state
it just entered. Inside a trace, every record is part of it until one is not:

```python
def _in_trace(self) -> None:
    """Inside a trace: every record is part of it until one is not."""
    case self.line:
        when /^Traceback /:
            # Only the literal header can mean "a new trace starts here";
            # unlike _outside()'s regex, this one must NOT also match an
            # exception-summary line (below), or that line -- which ends
            # the trace -- would be misread as starting another one.
            self.open_trace = Trace_T(lines=1)
            if self.requests'Length > 0:
                let prev: Request_T = self.requests[self.requests'Length - 1]
                self.open_trace.under = prev.verb + " " + prev.path
        when /^\d{4}-\d{2}-\d{2} /:
            # A timestamped line is not part of the trace: close it, leave
            # the state, and hand this same record to the state just
            # entered -- it is an event, and is counted as one.
            self.traces.append(self.open_trace)
            self.state = OUTSIDE
            self._outside()
        when /^([A-Z]\w+(Error|Exception)): /:
            self.open_trace.lines  += 1
            self.open_trace.failure = $+1
        when others:
            self.open_trace.lines += 1
```

The hand-off is symmetric, and worth seeing as one pattern rather than two.
Neither transition ever handles the boundary record itself: each recognises
that the record belongs to the *other* state and re-dispatches it there,
rather than special-casing it in place. Going in, `_outside()` does no setup
at all — it flips the flag and calls `self._in_trace()`, and the first branch
above, now looking at the same line a second time, is what actually opens
`open_trace`. Coming out, `_in_trace()` does the opposite: it finishes its
own bookkeeping first — the completed trace goes on the list — *then* flips
the flag and calls `self._outside()`, so the timestamped line that closed the
trace is itself counted as the event it is, by the ordinary event branch,
rather than by any special case for "the line after a trace." One recursion
each way, and no record is ever dropped or double-handled.

Look closely and the two regexes for "a trace is starting" are not quite the
same, and that difference is load-bearing. `_outside()` watches for either
the literal `Traceback ` header or a bare one-line `SomeError: ...` summary,
because either can open a trace. `_in_trace()`'s own first branch only
watches for the header. It has to: once inside a trace, a line that matches
`SomeError: ...` is the trace's *closing* summary (the third branch below),
not the start of a second, nested one — and a regex that could not tell
those apart would reset `open_trace` on the very line meant to finish it,
losing every line counted so far and the failure text with it.

Both handlers are a `case` over the record: the dispatch on *state* picks the
handler, and a dispatch on the *record* picks the branch. The catch-all is
needed here because the subject is a string — §3 — and it is where a line
belonging to neither kind goes.

The status class is the third `case`, over ranges this time, and it is not a
method: nothing about it concerns one scanner, so it is a plain function of
the code.

```python
def status_class(status: Natural) -> Status_T:
    """A case over ranges, which awk has to spell as an if/else chain.

    Nothing here is about one scanner: a status code means the same thing
    whoever read it, so it is a function of the code and lives outside the
    class.
    """
    case status:
        when 200 .. 299: return SUCCESS
        when 300 .. 399: return REDIRECT
        when 400 .. 499: return CLIENT_ERROR
        when 500 .. 599: return SERVER_ERROR
        when others:     return ODD
```

**And the post-processing**, which is `finish()`. First the housekeeping the
streaming form cannot do: a trace that runs to the end of the file has no
following record to close it, so this is where the last one is filed.

```python
if self.state == IN_TRACE:
    self.traces.append(self.open_trace)
```

Then the questions no running total can answer, because they need every
record in hand before any of them has one — a percentile has to sort, and a
maximum has to have seen the last record:

```python
var times: []Natural = []
for r in self.requests:
    times.append(r.ms)
times = sorted(times)

var slowest: Request_T = Request_T()
for r in self.requests:
    if r.ms > slowest.ms:
        slowest = r
```

...next to the totals that were already answered on the way past, and a walk
over the *other* list:

```python
for s in Severity_T:
    print f"  {s'Image:<5} {self.counts[s]}"
for t in self.traces:
    print f"  trace   {t.lines} line(s) under {t.under} -- {t.failure}"
```

Run it:

```
$ EXAMPLES/awk_logscan < EXAMPLES/awk_logscan_sample.txt
--- awk_logscan ---
records : 17
requests: 9    traces: 2

  DEBUG 1
  INFO  4
  WARN  2
  ERROR 2

  SUCCESS       4
  REDIRECT      1
  CLIENT_ERROR  2
  SERVER_ERROR  2
  ODD           0

p50     : 45 ms
slowest : 2317 ms  GET /reports/full at 2026-09-11 08:00:04

  trace   4 line(s) under POST /api/order -- ValueError
  trace   4 line(s) under GET /api/report -- TimeoutException
```

17 records in, two lists out: nine `Request_T` and two `Trace_T`, each trace
carrying the request it belongs to. The second one runs to the end of the
file, which is why `finish()` has to file it.

---

## 11. Translation table

| AWK | Adascript |
|-----|-----------|
| `BEGIN { }` | `def start(self):` — or just code before the loop |
| `END { }` | `def finish(self):` |
| `{ action }` | `def process_record(self):` |
| `$0` | `self.line`, or `Fields[0]` |
| `$1`, `$NF` | `Fields[1]`, `Fields[self.NF]` |
| `NR`, `NF`, `FS`, `OFS`, `RS` | `self.NR`, `self.NF`, `self.FS`, `self.OFS`, `self.RS` |
| `RS=""` (paragraph mode) | `AwkBase(rs = "\\n\\n")` |
| `RS="%%\\n"` (a marker) | `AwkBase(rs = "%%\\n")` |
| `/re/ { a }` | `when /re/:` in a `case` over the record |
| `/re/ && cond { a }` | `when /re/ if cond:` |
| `$0 ~ /re/` | `line == /re/` |
| `$0 !~ /re/` | `line != /re/` |
| `match($0, re); substr($0, RSTART, RLENGTH)` | `if line == /re/: … $+0` |
| capture groups | `$+1`, `$+2`, `$+{name}` |
| `sub(/re/, "x")` | `s == s/re/x/` |
| `gsub(/re/, "x")` | `s == s/re/x/g` |
| `split(s, a, sep)` | `let a: []str = s.split(sep)` |
| `split(s, a)` | `let a: []str = s.split()` |
| — (no equivalent; `gsub` counting is the hack) | `let all: []str = s == /re/g` |
| `a[k] += 1` over strings | `counts[member] += 1` over `[Enum_T]Natural` |
| `for (k in a)` | `for k in Enum_T:` — in declaration order |
| `printf "%-8s"` | `f"{value:<8}"` |
| `system("cmd")` | `shell: cmd` |
| `"cmd" \| getline line` | `let (out, rc) = shell: cmd` |
| `close(cmd)` | — nothing to close |
| `ARGV[1]`, `ARGC` | `$1`, `$#` |
| `ENVIRON["HOME"]` | `$HOME`, or `$?HOME` for a `?str` |
| an integer state flag | an `enum`, checked for completeness |
| parallel arrays sharing an index | a `record` |
| `kind[i]` plus a comment about which columns apply | a variant record |
| `""` meaning "not set" | `?T` and `None` |

---

## 12. Where to go next

- `EXAMPLES/awk_example.ady` — the flat form, in full in §10.1, runs on both backends
- `EXAMPLES/test_awk.ady` — the same program as an `AwkBase` subclass
- `EXAMPLES/config_check.ady` — the variant-record schema, walked through in §10.2
- `EXAMPLES/awk_logscan.ady` — the state-machine example, in full in §10.3, all of §1 at once
- `EXAMPLES/CFMU/Tstatus_monitor.ady` — a real AWK script, translated
- `DOCS/BOOK/05-pattern-matching.md` — `case`/`when` in full
- `DOCS/BOOK/07-regex.md` — every regex form
- `DOCS/BOOK/03-enums-sets-and-tick-attributes.md` — enums and tick attributes
- `DOCS/BOOK/11-shell-and-scripting.md` — the shell forms
