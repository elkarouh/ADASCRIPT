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
the exceptions are `awk_logscan.ady` and `html_body.ady`, whose `AwkBase`
form is Nim-only (§2). §10 works through four of them, built up in stages:
no state, then one record shape or another, then a state machine deciding
which shape a record even is, and one deciding whether a record is wanted at
all.

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

<!-- from: EXAMPLES/awk_example.ady -->
```python
def main():
    for raw in stdin.lines:
        process(raw)
```

`stdin` has type `File`, and so does `open(path)` — the same variable holds
either, so the loop is written once:

<!-- from: TOOLS/ADA_INDENT/ada_indent.ady -->
```python
let f: File = (open(file_arg) if file_arg != "" else stdin)
for line in f.lines:
    print ind.indent_line(line)
    if do_emit_state:
        print "##STATE:" + ind.dump_state()
```

`.lines` strips the newline, which is what `$0` does and what you wanted.

### The AwkBase form

When the program is a state machine — when what a record *means* depends on
the records before it — subclass `AwkBase` from the bundled library
(`TO_NIM/STDLIB/awk.ady`) and override three methods:

<!-- illustrative: the shape of an AwkBase program, with every method body elided -->
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

<!-- from: EXAMPLES/DOC/awk_paragraph.ady -->
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

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
def classify(s: str) -> Severity_T:
    case s:
        when /error|fatal/i: ERROR
        when /warn/i:        WARN
        when /info|debug/i:  INFO
        when others:         DEBUG
```

The `i` is a flag on the literal, not an argument to a function. Literal
strings, regexes and ranges mix freely in one `case`:

<!-- from: EXAMPLES/CFMU/Tstatus_monitor.ady -->
```python
case F[1]:
    when "Showing" if self.NF >= 12:
        self._showing(F)
    when "User:" if self.NF >= 2:
        self._open_build()
        self.current_build.user = F[2]
    when "Host:" if self.NF >= 2:
        self.current_build.host      = F[2]
        self.current_build.test_mode = "REGRESS"
        self.newhost = True
    when /TACT\.TACT_CONFIG|IFPS\.FPL_CONFIG/:
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

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
let line: str = "2026-09-11 ERROR disk full on /var/log"

assert line == /ERROR|FATAL/
assert line != /^#/
```

Captures come back as `$+1`, `$+2`, … with `$+0` the whole match:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
if line == /^(\d{4})-(\d{2})-(\d{2}) (\w+)/:
    assert $+1 == "2026"
    assert $+4 == "ERROR"
```

Named groups use `(?P<name>...)` and read back as `$+{name}`.

The `g` flag turns the match test into a list of every match — this is AWK's
`split` with a regex, and rather more:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
let nums: []str = "a1 b22 c333" == /\d+/g
assert nums == ["1", "22", "333"]
```

Substitution is Perl's, and assigns back to the left-hand side, so the
target is a `var` — and the operator is `=`, not the `==` of a match. The
two are different kinds of thing and are spelled differently: a match is a
test and yields a bool, a substitution rewrites its target and yields
nothing, which is what an assignment does.

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
var path: str = "/var/log/app.log.gz"
path = s/\.gz$//g
assert path == "/var/log/app.log"

var stamp: str = "2026-09-11"
stamp = s/(\d{4})-(\d{2})-(\d{2})/$+3.$+2.$+1/g
assert stamp == "11.09.2026"
```

`sub` and `gsub` in one form: without `g` it replaces the first match, with
`g` all of them.

---

## 5. Enums: the thing AWK has no word for

This is the centre of the argument. In AWK a severity is a string, a parser
state is an integer, and a status class is a key you hope you spelled the
same way in both places. In Adascript each is a type.

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
type Severity_T   is enum DEBUG, INFO, WARN, ERROR
type Scan_State_T is enum OUTSIDE, IN_TRACE
type Status_T is enum SUCCESS, REDIRECT, CLIENT_ERROR, SERVER_ERROR, ODD

type Request_T is record:      # a timestamped event
    """One served request, taken apart by a single regex."""
    at:      str     = ""
    verb:    str     = ""
    path:    str     = ""
    status:  Natural = 0
    ms:      Natural = 0

type Trace_T is record:        # the lines after a failure
    """One stack trace: several lines, belonging to the request before it."""
    under:   str     = ""      # the request it followed
    lines:   Natural = 0
    failure: str     = ""      # the exception line that ends it

def status_class(status: Natural) -> Status_T:
    """A case over ranges, which awk has to spell as an if/else chain.

    Nothing here is about one scanner: a status code means the same thing
    whoever read it, so it is a function of the code and lives outside the
    class.
    """
    case status:
        when 200 .. 299: SUCCESS
        when 300 .. 399: REDIRECT
        when 400 .. 499: CLIENT_ERROR
        when 500 .. 599: SERVER_ERROR
        when others:     ODD
```

A `case` over that type is checked for completeness — leave out `WARN` and
the Nim backend refuses the program. No `when others:` is needed, and adding
a fifth member turns every `case` over the type into a compile error listing
the places you have to think about. That is the refactoring AWK cannot help
you with at all.

Guards work here too, and are what makes a catch-all necessary again:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
def prefix(sev: Severity_T, nr: Natural) -> str:
    case sev:
        when ERROR:            "!!"
        when WARN if nr < 10:  " !"   # only shout early
        when others:           "  "
```

The type answers questions about itself, through tick attributes borrowed
from Ada:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
assert ERROR'Image      == "ERROR"    # the name, for printing
assert Severity_T'First == DEBUG
assert Severity_T'Last  == ERROR
assert Severity_T("WARN") == WARN     # and back from a string
```

And it can index an array, which is AWK's associative array with the typos
removed and the iteration order fixed:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
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

<!-- from: EXAMPLES/awk_example.ady -->
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

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
type Request_T is record:      # a timestamped event
    """One served request, taken apart by a single regex."""
    at:      str     = ""
    verb:    str     = ""
    path:    str     = ""
    status:  Natural = 0
    ms:      Natural = 0
```

Fields have defaults, so `Request_T()` is a complete zero row, and a
construction names what it sets:

<!-- illustrative: one line of awk_logscan.ady's match, shown without the `when` that binds $+1 .. $+7 -->
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

<!-- from: EXAMPLES/config_check.ady -->
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

<!-- from: EXAMPLES/config_check.ady -->
```python
def describe(s: Spec_T) -> str:
    """One line per shape. No `when others:` -- the enum has four members and
    the compiler has checked that all four are here."""
    case s.kind:
        when FLAG: "a flag (" + ", ".join(TRUE_WORDS) + " / " + ", ".join(FALSE_WORDS) + ")"
        when NUMBER: f"a whole number in {s.lo} .. {s.hi}"
        when CHOICE: "one of " + ", ".join(s.allowed)
        when PATHNAME: "a path that must exist" if s.must_exist else "a path"
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

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
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

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
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

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
```python
assert (maybe or 0) == 12          # `or` supplies a default
assert none_.line == None          # comparing against None is always fine
```

...and, for the case where you have already established it is there, an
**early-return guard**, which narrows what it tested to a plain `Natural`
below it:

<!-- from: EXAMPLES/config_check.ady -->
```python
def where(f: Finding_T) -> str:
    if f.line is None:
        return ""
    return "line " + str(f.line)   # a plain Natural from here on
```

Narrowing follows the test wherever it is written: the body of an
`if x is not None:`, the `else` of an `if x is None:`, everything to the
right of an `and`, both halves of a ternary, and — as here — a record field
rather than a bare name.

The point of all this is what it replaces. AWK's `line[i]` is `""` when the
finding has no line, `""` when the line number was never filled in, and `0`
if you compare it to a number — three different situations wearing the same
face. `?Natural` distinguishes "no line" from "line 0", and nothing reads the
value without first saying which case it is in.

---

## 9. The shell, without `system()`

AWK shells out through `system()` and `"cmd" | getline`, with quoting left
to you. In Adascript a command is a statement:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let (greeting, rc) = shell: echo hello world
assert rc == 0
assert greeting.strip() == "hello world"
```

A value goes in braces. `{x}` puts it in as written, which is what a command
fragment wants; `{!x}` quotes it, so a path holding spaces arrives as one
argument instead of two:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let dir: str = "/tmp"
let (count_out, _) = shell: ls -1d {!dir}
```

`run(["ls", dir])` skips the shell altogether, and then there is nothing to
quote because nothing parses the arguments twice.

A pipeline can report the first failure rather than the last, and a long
output can be streamed instead of held:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
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

<!-- illustrative: a checklist of the environment forms, ending in two elided bodies -->
```python
assert $HOME != ""
assert $NO_SUCH_VAR_HERE == ""
assert ${NO_SUCH_VAR_HERE:-"fallback"} == "fallback"
assert $?NO_SUCH_VAR_HERE == None

if -f path:    ...    # and -d -e -L -r -w -x -s, plus a -nt b
if which("git") is not None: ...   # is it even installed?
```

---

## 10. Worked examples

The rest of this document is vocabulary. These four files put it to work,
in the order complexity actually arrives in practice: no state, then one
record shape or another, then a state machine deciding which shape a record
even is, and finally one deciding whether a record is wanted at all. Each is
a complete, runnable program — `make test` runs all four — and each is quoted
here as it actually stands in `EXAMPLES/`, not as a simplified stand-in for
it.

### 10.1 No state: `awk_example.ady`

The plainest case first: one kind of record, no memory of the records
before it. This is §2's flat form, in full — every line is classified and
printed on its own, and nothing about line *N* depends on line *N-1*:

<!-- from: EXAMPLES/awk_example.ady -->
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
        when /error/i:      ERROR
        when /warn/i:       WARN
        when /info|debug/i: INFO
        when others:        OTHER


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

<!-- from: EXAMPLES/config_check.ady -->
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

The awk is next to it, as `EXAMPLES/config_check.awk`: same schema, same
findings, same bytes, and `make test` runs `cmp` on the two. Here is its
schema, which is the whole argument for the variant record:

```awk
function spec(key, kind, a, b, c) {
    spec_kind[key] = kind
    keys[nkeys++] = key
    if (kind == "FLAG")     spec_default[key] = a          # on_by_default
    if (kind == "NUMBER")   { spec_lo[key] = a; spec_hi[key] = b }
    if (kind == "CHOICE")   spec_allowed[key] = a          # a blank-separated list
    if (kind == "PATHNAME") spec_must_exist[key] = a
}
```

One constructor for four shapes, so it takes the union of their fields, and
what `a` and `b` mean depends on `kind` — which only the comment says.
Afterwards every setting has every field: `spec_lo["mode"]` exists, is empty,
and can be read. Nothing stops `check_value` from consulting it and
reporting that 5 is outside `0 .. 0`. The `describe` function needs a
`return "???"` at the end for a `kind` that cannot happen, because nothing
has told awk that there are four of them.

Checking a value is a `case` over the same discriminant, and each branch
reads only the fields its own shape declares — `s.lo` inside the `CHOICE`
branch is not a mistake to be careful about; on the Nim backend the field is
not there to read. (`TRUE_WORDS` and `FALSE_WORDS` are two module-level word
lists defined earlier in the file.)

<!-- from: EXAMPLES/config_check.ady -->
```python
def check_value(s: Spec_T, value: str) -> str:
    """Empty means the value is fine; otherwise the complaint.

    Each branch reads only the fields its own shape declares. `s.lo` inside
    the CHOICE branch is not a mistake to be careful about -- on the Nim
    backend the field is not there to read.
    """
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

<!-- from: EXAMPLES/config_check.ady -->
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

The same report, written in awk, is next to it as
`EXAMPLES/awk_logscan.awk` — POSIX awk, no GNU extensions, and not a straw
man: it is what this program looks like with awk's tools and only those.
The two agree byte for byte on the sample, and `make test` runs `cmp` on
their output, so the comparisons below can be checked rather than believed.

Three enums and two record types carry it:

<!-- from: EXAMPLES/DOC/awk_snippets.ady -->
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

<!-- from: EXAMPLES/awk_logscan.ady -->
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

<!-- from: EXAMPLES/awk_logscan.ady -->
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

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
def _outside(self) -> None:
    """Between traces: a record is an event, the start of one, or noise."""
    # One regex takes the record apart; $+1 .. $+7 are its groups.
    case self.line:
        when /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+) +(\w+) (\S+) (\d{3}) (\d+)ms$/:
            let req: Request_T = Request_T(at=$+1 + " " + $+2, verb=$+4, path=$+5, status=int($+6), ms=int($+7))
            let sev: Severity_T = Severity_T($+3.upper())
            self.requests.append(req)
            self._event(sev, req)
        when /^Traceback |^[A-Z]\w+(Error|Exception): /:
            # Opening the trace belongs here, with the record that starts
            # it: this is the branch that knows a trace is beginning, and
            # it knows which request it belongs to -- the last one in the
            # other list. Then hand the same record on, so the line that
            # started the trace is also counted by it.
            self.open_trace = Trace_T()
            if self.requests'Length > 0:
                let prev: Request_T = self.requests[self.requests'Length - 1]
                self.open_trace.under = prev.verb + " " + prev.path
            self.state = IN_TRACE
            self._in_trace()
        when others:
            pass                      # a line belonging to neither kind
```

`Severity_T($+3.upper())` is worth a second look. The log writes `INFO`,
`WARN`, `ERROR` as text; that turns the text into a value of the type, and a
log line carrying a severity nobody declared fails there, at the line that
read it, rather than becoming a silent extra bucket in the report.

The second branch does three things in order: it opens the trace, it flips
the state, and it hands the very same record straight to `_in_trace()` — the
state it has just entered — so the line that started the trace is also
counted by it. Inside a trace, every record is part of it until one is not:

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
def _in_trace(self) -> None:
    """Inside a trace: every record is part of it until one is not."""
    case self.line:
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

Where the opening lives is worth dwelling on, because it is the whole lesson
of the section in miniature. A bare `SomeError: ...` line can *start* a trace
— not every failure has a `Traceback ` header — and it can also *end* one, as
the summary of a trace already running. Same text, two meanings. No regex can
tell them apart, because the difference is not in the line: it is in which
state you are in when you read it.

So the opening belongs in `_outside()`, where the state has already answered
that question. `_in_trace()` never opens a trace at all; it only counts and
closes. The alternative — matching "a trace is starting" in both handlers and
narrowing the second regex so it cannot fire on a closing line — was tried,
and it works only for traces that have a header: one that starts with a bare
`SomeError: ...` is entered but never opened, so it loses the request it
belongs to and its line count leaks into the next one. The regexes are not
the state machine. That is what the state machine is for.

Both handlers are a `case` over the record: the dispatch on *state* picks the
handler, and a dispatch on the *record* picks the branch. The catch-all is
needed here because the subject is a string — §3 — and it is where a line
belonging to neither kind goes.

The status class is the third `case`, over ranges this time, and it is not a
method: nothing about it concerns one scanner, so it is a plain function of
the code.

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
def status_class(status: Natural) -> Status_T:
    """A case over ranges, which awk has to spell as an if/else chain.

    Nothing here is about one scanner: a status code means the same thing
    whoever read it, so it is a function of the code and lives outside the
    class.
    """
    case status:
        when 200 .. 299: SUCCESS
        when 300 .. 399: REDIRECT
        when 400 .. 499: CLIENT_ERROR
        when 500 .. 599: SERVER_ERROR
        when others:     ODD
```

**And the post-processing**, which is `finish()`. First the housekeeping the
streaming form cannot do: a trace that runs to the end of the file has no
following record to close it, so this is where the last one is filed.

<!-- from: EXAMPLES/awk_logscan.ady -->
```python
if self.state == IN_TRACE:
    self.traces.append(self.open_trace)
```

Then the questions no running total can answer, because they need every
record in hand before any of them has one — a percentile has to sort, and a
maximum has to have seen the last record:

<!-- from: EXAMPLES/awk_logscan.ady -->
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

<!-- from: EXAMPLES/awk_logscan.ady -->
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

**What the awk version has to spell out.** Read the two side by side and the
differences are not stylistic:

| in `awk_logscan.ady` | in `awk_logscan.awk` |
|---|---|
| `type Request_T is record:` with five named fields | five parallel arrays, `req_at[i]`, `req_verb[i]`, … , sharing an index by convention |
| `type Severity_T is enum DEBUG, INFO, WARN, ERROR` | `split("DEBUG INFO WARN ERROR", sev_name, " ")` — the members as a string, and their order written out a second time so the report can loop over it |
| `case status: when 200 .. 299: SUCCESS` | an `if`/`else` chain returning string constants that nothing checks against the ones counted in `BEGIN` |
| `self.state`, a `Scan_State_T` | `in_trace`, an integer flag tested on the front of two rules |
| `times = sorted(times)` | an insertion sort, written out, to answer one median |
| `var counts: [Severity_T]Natural` — indexed *by the type* | `sev_count[$3]` — indexed by whatever string was in field 3 |

That last row is the one that bites. `sev_count[$3]` creates a new entry for
any severity the log invents, silently, and the report loops over the list in
`BEGIN`, so the new one is counted into a row nobody prints. In the
Adascript, `self.counts[sev]` takes a `Severity_T`, and `Severity_T($+3.upper())`
is where an unknown word is rejected — at the edge, once, rather than as a
missing row in a report three weeks later.

Writing the awk companion also found a bug in the Adascript one, which is
the sort of thing that happens when a claim is checked: on a log with no
requests in it at all, `times[times'Length // 2]` indexed an empty list and
the program died. Both now print `n/a`, and `make test` compares them on
that input too.

### 10.4 State that decides what to keep: `html_body.ady`

`EXAMPLES/html_body.ady` is a translation of a real awk script — one that
lifts the `<body>` out of an HTML page so it can be included in another one.
The original is in the repository as `EXAMPLES/process_html.awk`, 48 lines,
so every claim below can be checked against it.
It is the state machine again, turned a quarter turn: in §10.3 the state
decided *which kind* of record had arrived, here it decides whether the
record is wanted at all, and what has to be rewritten before it is let
through.

The point of the file is one line of HTML:

```
</div>
```

That record means two entirely different things — the end of the footer that
is being dropped, or an ordinary line to print — and nothing about it says
which. Only the state does. The original spells that with `in_body` and
`in_footer`, tested on the front of every pattern; nothing checks the four
combinations against each other, and every reader has to reconstruct what
`&& in_footer` is guarding against.

Four states, and the case over them is the whole dispatch:

<!-- from: EXAMPLES/html_body.ady -->
```python
type Scan_State_T is enum HEAD, BODY, FOOTER, DONE
```

<!-- from: EXAMPLES/html_body.ady -->
```python
    def process_record(self):
        case self.state:
            when HEAD:   self._head()
            when BODY:   self._body()
            when FOOTER: self._footer()
            when DONE:   pass          # awk's `exit`, spelled as a state
```

`DONE` is worth a second look. The awk says `exit` when it reaches
`</body>`, which leaves the program; `AwkBase` has no early exit, so the
translation needs a state for "everything from here on is not wanted" — and
that turns out to be the better answer. `exit` says *stop*; `DONE` says
*why*, and it is a member of the same type as the other three, so the
compiler counts it when it checks that the `case` is complete.

Each state is a `case` over the record, with the regexes that matter in that
state and no others:

<!-- from: EXAMPLES/html_body.ady -->
```python
    def _body(self) -> None:
        """Inside the body: rewrite, print, and watch for the two exits."""
        case self.line:
            when /<\/body>/:             self.state = DONE
            when /<div title="footer">/: self.state = FOOTER
            when others:
                self._rewrite()
                print self.line

    def _footer(self) -> None:
        """Inside the footer: dropped, up to the </div> that closes it."""
        case self.line:
            when /<\/body>/: self.state = DONE
            when /<\/div>/:  self.state = BODY
            when others:     pass
```

`</div>` appears exactly once in the program, in the one state where it
means something. That is the whole argument for naming the state: the awk
version writes the same test as `/<\/div>/ && in_footer`, and every reader
after the first has to work out what the `&&` is guarding against.

### What a state is, and what it is not

There is a third boolean in the awk, `div_processed`, and it survives the
translation:

<!-- from: EXAMPLES/html_body.ady -->
```python
    var div_done: bool         = false
```

That is deliberate, and it is worth being precise about why, because "turn
the flags into states" is the kind of rule that is right until it is not.
`in_body` and `in_footer` answer *where are we*, and where-we-are is one
question with four answers — a type. `div_done` answers something else:
*has this already happened?* It is a **latch** — set once, never cleared,
read in exactly one place. Folding it into `Scan_State_T` is possible, and
it doubles the type: `BODY`/`BODY_TAGGED`, `FOOTER`/`FOOTER_TAGGED`, six
states for the same program. It also loses something. A latch survives a
return into a state; a state has to remember which state to return to, so
the single footer becomes two, or one that is told where to come back from.

Six states with nothing to check between them are not safer than four states
and a monotonic flag. The test is not "is it a boolean" but "does it
multiply with the others" — `in_body` × `in_footer` × `div_processed` is
eight combinations and the awk tests them independently; `state` ×
`div_done` is a type the compiler checks, times a latch that only ever goes
one way.

**Where the awk actually goes wrong** is not that it keeps the flag; it is
*where the flag is read*. Put a `<div>` inside the footer, on a line of its
own:

```
<div title="footer">
  <div class="legal">
  dropped
  </div>
</div>
```

The tagging rule tests `in_body`, and the footer is inside the body — so the
id lands on that inner `<div>`, `div_processed` latches, and the line is then
not printed. The page comes out with **no id at all**. That page is
`EXAMPLES/html_body_wasted_id.html` in the repository, and the original is
`EXAMPLES/process_html.awk`, so this is checkable rather than asserted
(with gawk — `gensub` is a GNU extension):

```
$ cd EXAMPLES
$ gawk -f process_html.awk html_body_wasted_id.html | head -2
</div>
<div class="content">

$ ./html_body html_body_wasted_id.html | head -2
</div>
<div class="content" id="html_body_wasted_id">
```

The translation cannot do this, because `_rewrite` is called from one place
— the branch of `BODY` that prints — so a record that is dropped is never
rewritten. The states did that, not the flag: in awk every rule sees every
record and has to re-derive whether it should act, and that re-derivation is
what goes wrong. (Both keep the awk's other quirk faithfully, by the way:
the stray `</div>`, because the first `</div>` ends the footer whether or not
it was the footer's own.)

**Rewriting on the way past.** Two of §1's five points apply here and two do
not: there is a state machine and there is processing on the fly, but there
are no lists at the end — the output *is* the stream, one record at a time.

What gets rewritten, and why, is worth a sentence, because the two edits are
really one. A file is a *name* and a *place*, and the fragment this program
produces has neither: it is about to be pasted into a bigger page.

- The place is gone. `href="test_x.html"` and `<img src="plot.png">` meant
  "next to me"; in the combined page they mean "next to whoever swallowed
  me", which is somewhere else. Making them absolute is what keeps them
  pointing where they pointed.
- The name is gone. Nothing addresses the block any more — it used to be
  `results.html`, and now it is some markup in the middle of another
  document. Putting the file's own name on the first `<div>` as an id is
  what gives it a name again: the body of `results.html` is `#results`
  wherever it lands, so a link, a stylesheet rule or a script can still
  find it. It goes on the *first* `<div>` because that is the block the
  whole page was, and only on the first, because a page has one name.

That is what `div_done` is for, and why it is a latch rather than a state:

<!-- from: EXAMPLES/html_body.ady -->
```python
        if not self.div_done:
            case self.line:
                when /(<div[^>]+)>/:
                    # $+1 is the open tag without its `>`: put the id
                    # inside the tag it came from, wherever on the line
                    # that tag is.
                    let open: str = $+1
                    self.line = self.line.replace(open + ">",
                                                  open + " id=\"" + self.at.stem + "\">")
                    self.div_done = true
                when others: pass
```

**The part awk cannot do at all.** The rewriting needs to know where the
page lives: the directory, to make the links absolute, and the file's name
without its extension, to use as the id. awk has no way to ask, so the
original shells out three times — `realpath`, then `dirname`, then
`basename -s .html`, each through a `cmd | getline` helper. Three processes,
three chances to get the quoting wrong on a path with a space in it, and
three strings that are all just strings afterwards:

<!-- from: EXAMPLES/html_body.ady -->
```python
def anchor(arg: str) -> Anchor_T:
    let full: Path = Path(arg).resolve()
    var stem: str  = full.name
    stem = s/\.html$//g
    Anchor_T(dir=full.parent, stem=stem)
```

One process, no quoting, and the two results are no longer both strings:
`dir` is a `Path` and `stem` is a `str`, which is the difference between a
typo and a compile error. The `s/\.html$//g` is §4's substitution doing what
`basename -s .html` was there for, and the last line is the value the
function returns — a trailing expression is the result, the way the `case`
branches in §3 are.

Run it:

```
$ cp EXAMPLES/html_body_sample.html /tmp/ady_html_body/results.html
$ EXAMPLES/html_body /tmp/ady_html_body/results.html
<div class="content" data-kind="page" id="results">
<h1>Results</h1>
<p>See <a href="/tmp/ady_html_body/test_alpha.html">alpha</a> and <a href="/tmp/ady_html_body/test_beta.html">beta</a>.</p>
<p><img src="/tmp/ady_html_body/plot.png" alt="a plot"></p>
<p>An <a href="https://example.com/">external link</a> is left alone.</p>
<p>After the footer, still inside the body.</p>
</div>
```

The `<head>` is gone, the `<body>` tag with it, the footer and its link are
gone, the first div carries the page's own name, the relative links point at
the directory the page came from, and the external link was not touched.
Byte for byte, that is what the awk original prints — with the one
exception above, where it prints something worse. Two footnotes: the
original needs *gawk*, because `gensub` is a GNU extension, and will not run
under the `mawk` that is `/usr/bin/awk` on a lot of machines; and the two
were diffed on this sample to check the claim, which is what `make test`
keeps checking.

---

## 11. Translation table

| AWK | Adascript |
|-----|-----------|
| `BEGIN { }` | `def start(self):` — or just code before the loop |
| `END { }` | `def finish(self):` |
| `{ action }` | `def process_record(self):` |
| `$0` (the record) | `self.line`, or `Fields[0]` |
| `$1`, `$NF` (a field) | `Fields[1]`, `Fields[self.NF]` |
| `NR`, `NF`, `FS`, `OFS`, `RS` | `self.NR`, `self.NF`, `self.FS`, `self.OFS`, `self.RS` |
| `RS=""` (paragraph mode) | `AwkBase(rs = "\\n\\n")` |
| `RS="%%\\n"` (a marker) | `AwkBase(rs = "%%\\n")` |
| `/re/ { a }` | `when /re/:` in a `case` over the record |
| `/re/ && cond { a }` | `when /re/ if cond:` |
| `$0 ~ /re/` | `line == /re/` |
| `$0 !~ /re/` | `line != /re/` |
| `match($0, re); substr($0, RSTART, RLENGTH)` | `if line == /re/: … $+0` (the whole match) |
| gawk `match($0, re, m); m[1]`, or `gensub`'s `\\1` | `$+1`, `$+2` (a capture group) |
| — (no equivalent at all) | `$+{name}` for a named group |
| `sub(/re/, "x")` | `s = s/re/x/` |
| `gsub(/re/, "x")` | `s = s/re/x/g` |
| `split(s, a, sep)` | `let a: []str = s.split(sep)` |
| `split(s, a)` | `let a: []str = s.split()` |
| — (no equivalent; `gsub` counting is the hack) | `let all: []str = s == /re/g` |
| `a[k] += 1` over strings | `counts[member] += 1` over `[Enum_T]Natural` |
| `for (k in a)` | `for k in Enum_T:` — in declaration order |
| `printf "%-8s"` | `f"{value:<8}"` |
| `system("cmd")` | `shell: cmd` |
| `"cmd" \| getline line` | `let (text, rc) = shell: cmd` |
| `close(cmd)` | — nothing to close |
| `ARGV[1]`, `ARGC` | `$1`, `$#` (a command-line argument) |
| `ENVIRON["HOME"]` | `$HOME`, or `$?HOME` for a `?str` |
| an integer state flag | an `enum`, checked for completeness |
| parallel arrays sharing an index | a `record` |
| `kind[i]` plus a comment about which columns apply | a variant record |
| `""` meaning "not set" | `?T` and `None` |

### Three things spelled with a dollar

Worth separating, because two of them collide with what `$` means in AWK:

| | means | AWK's spelling |
|---|---|---|
| `Fields[1]` | **a field** of the record | `$1` |
| `$+1` | **a capture group** of the regex that just matched | gawk's `match(s, re, m); m[1]` |
| `$1` | **a command-line argument** | `ARGV[1]` |

So AWK's `$1` is `Fields[1]`, and Adascript's `$1` is AWK's `ARGV[1]`: the
same three characters, and not the same thing. The `+` is the reminder that
a capture belongs to a match rather than to the record — `$+0` is the whole
match, `$+1` the first group, `$+{name}` a named one, and all of them are
only meaningful inside the branch whose pattern produced them.

Fields are positional and always there; captures exist only where a regex
matched. That is why `$+1` is what §10.3's scanner uses to take a request
apart, even though the record does have fields: the regex is what says the
record *is* a request, and the groups it hands back are the parts of one.

---

## 12. Where to go next

- `EXAMPLES/awk_example.ady` — the flat form, in full in §10.1, runs on both backends
- `EXAMPLES/test_awk.ady` — the same program as an `AwkBase` subclass
- `EXAMPLES/config_check.ady` — the variant-record schema, walked through in §10.2
- `EXAMPLES/config_check.awk` — the same checker in POSIX awk, to read against it
- `EXAMPLES/awk_logscan.ady` — the state-machine example, in full in §10.3, all of §1 at once
- `EXAMPLES/awk_logscan.awk` — the same report in POSIX awk, to read against it
- `EXAMPLES/html_body.ady` — a real AWK script translated, in full in §10.4: state that decides what to keep
- `EXAMPLES/process_html.awk` — that script, as it was, to read against the translation
- `EXAMPLES/CFMU/Tstatus_monitor.ady` — a real AWK script, translated
- `DOCS/BOOK/05-pattern-matching.md` — `case`/`when` in full
- `DOCS/BOOK/07-regex.md` — every regex form
- `DOCS/BOOK/03-enums-sets-and-tick-attributes.md` — enums and tick attributes
- `DOCS/BOOK/11-shell-and-scripting.md` — the shell forms
