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

Every example here is compiled and run on **both** backends — `ady2nim` and
`ady2py` — before being quoted. `EXAMPLES/awk_logscan.ady` is the worked
example at the end, and `make test` runs it.

---

## 1. The shape of a program

AWK's implicit loop has two spellings in Adascript, and the choice is about
how much state you carry.

### The flat form

For a filter, iterate `stdin.lines` and be done. `EXAMPLES/awk_example.ady`
is this shape:

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

---

## 2. Patterns: `case` instead of a pattern list

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

## 3. Regex is syntax

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

## 4. Enums: the thing AWK has no word for

This is the centre of the argument. In AWK a severity is a string, a parser
state is an integer, and a status class is a key you hope you spelled the
same way in both places. In Adascript each is a type.

```python
type Severity_T is enum DEBUG, INFO, WARN, ERROR
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

## 5. Numbers that cannot be wrong

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

## 6. Records instead of parallel arrays

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

---

## 7. Missing is not the empty string

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

---

## 8. The shell, without `system()`

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

## 9. A worked example

`EXAMPLES/awk_logscan.ady` scans an application log where most lines are
timestamped events and the lines after a failure are a stack trace. That is
the case AWK makes awkward: what a line *means* depends on the state the
scanner is in.

Three types carry the program:

```python
type Severity_T    is enum DEBUG, INFO, WARN, ERROR
type Scan_State_T  is enum OUTSIDE, IN_TRACE
type Status_T      is enum SUCCESS, REDIRECT, CLIENT_ERROR, SERVER_ERROR, ODD
```

The state machine is a `case` over `Scan_State_T`, not a flag:

```python
case self.state:
    when IN_TRACE:
        if self.line != /^\d{4}-\d{2}-\d{2} /:
            self.traced += 1
            return
        self.state = OUTSIDE
    when others:
        pass
```

One regex takes the record apart, and the groups go straight into a record:

```python
if self.line == /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (\w+) +(\w+) (\S+) (\d{3}) (\d+)ms$/:
    let req: Request_T = Request_T(at=$+1 + " " + $+2, verb=$+4, path=$+5,
                                   status=int($+6), ms=int($+7))
    let sev: Severity_T = Severity_T($+3.upper())
```

That last line is worth a second look. The log writes `INFO`, `WARN`,
`ERROR` as text; `Severity_T($+3.upper())` turns the text into a value of the
type, and a log line carrying a severity nobody declared fails there, at the
line that read it, rather than becoming a silent extra bucket in the report.

The status class is a `case` over ranges — AWK's if/else chain, said once:

```python
def _status_class(self, status: Natural) -> Status_T:
    case status:
        when 200 .. 299: return SUCCESS
        when 300 .. 399: return REDIRECT
        when 400 .. 499: return CLIENT_ERROR
        when 500 .. 599: return SERVER_ERROR
        when others:     return ODD
```

And the report loops over the types themselves, so a new enum member appears
in the output without anyone remembering to add it:

```python
for s in Severity_T:
    print f"  {s'Image:<5} {self.counts[s]}"
for k in Status_T:
    print f"  {k'Image:<13} {self.by_status[k]}"
```

Iterate the *type*, not `Enum_T'Range`: `'Range` is the set of members, and a
set has no order to promise — on the Python backend it comes out shuffled,
differently on each run.

Run it:

```
$ EXAMPLES/awk_logscan < EXAMPLES/awk_logscan_sample.txt
--- awk_logscan ---
records : 12
traces  : 4 line(s), the last one under POST /api/order

  DEBUG 1
  INFO  4
  WARN  2
  ERROR 1

  SUCCESS       4
  REDIRECT      1
  CLIENT_ERROR  2
  SERVER_ERROR  1
  ODD           0

slowest : 2317 ms  GET /reports/full at 2026-09-11 08:00:04
```

---

## 10. Translation table

| AWK | Adascript |
|-----|-----------|
| `BEGIN { }` | `def start(self):` — or just code before the loop |
| `END { }` | `def finish(self):` |
| `{ action }` | `def process_record(self):` |
| `$0` | `self.line`, or `Fields[0]` |
| `$1`, `$NF` | `Fields[1]`, `Fields[self.NF]` |
| `NR`, `NF`, `FS`, `OFS`, `RS` | `self.NR`, `self.NF`, `self.FS`, `self.OFS`, `self.RS` |
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
| `""` meaning "not set" | `?T` and `None` |

---

## 11. Where to go next

- `EXAMPLES/awk_example.ady` — the flat form, runs on both backends
- `EXAMPLES/test_awk.ady` — the same program as an `AwkBase` subclass
- `EXAMPLES/awk_logscan.ady` — the worked example above
- `EXAMPLES/CFMU/Tstatus_monitor.ady` — a real AWK script, translated
- `DOCS/BOOK/05-pattern-matching.md` — `case`/`when` in full
- `DOCS/BOOK/07-regex.md` — every regex form
- `DOCS/BOOK/03-enums-sets-and-tick-attributes.md` — enums and tick attributes
- `DOCS/BOOK/11-shell-and-scripting.md` — the shell forms
