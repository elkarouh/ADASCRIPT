# Adascript for Shell Programmers

Shell got one thing profoundly right: the command *is* the syntax. `grep pat
file | sort | uniq -c` is the shortest way anyone has found to say that, and
no library API has ever improved on it. That is why the script you wrote in
five minutes is still in production.

What it costs is everything else. There is one type, and it is "string, split
on spaces unless you remembered the quotes". `$?` is checked or it is not.
A pipeline's status is its last command's, which is almost never what you
meant. Every array is a string with a separator you hope nobody used. Every
enumeration is a bare word that four different `if` statements compare
against, and a typo in one of them is a branch that silently never runs.

Adascript keeps the command as syntax and puts a type system behind it. This
document is for someone who already writes shell and wants to know exactly
what changes.

Every example here is compiled and run on **both** backends — `ady2nim` and
`ady2py` — before being quoted. `EXAMPLES/sh_janitor.ady` is the worked
example at the end; `make test` runs it, and its output is byte-identical on
the two backends.

---

## 1. The command is still the syntax

`shell:` takes a command line, not a string. What differs is the target you
give it, and the target is what decides how the command is run.

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
shell: true                                   # run it; nothing captured

let r = shell: echo captured                  # .output, .stderr, .code
assert r.output.strip() == "captured"

let (text, rc) = shell: echo tuple            # the two halves, by name
assert text.strip() == "tuple" and rc == 0

let names: []str = shellLines: printf 'a\nb\nc\n'
assert names == ["a", "b", "c"]

let status: int = shell: true                 # inherits the terminal
assert status == 0
```

That last one is worth dwelling on. An `int`-typed target does **not**
capture: stdin, stdout and stderr are inherited, so colours, progress bars
and the pager reach the user exactly as they would from a script, and you
still get the status. `TOOLS/GIT1/git1.ady` uses the two forms deliberately —
one for the commands the user is meant to watch, one for the commands whose
answer is their output:

<!-- from: TOOLS/GIT1/git1.ady -->
```python
let code: int = shell(cwd = self.dir, env = self.env): git {*args}
...
let lines = shellLines(cwd = self.dir, env = self.env): git {*args}
```

And when the last thing your script does is run a program, `shellExec`
replaces this process with it — the status is the child's by construction and
Ctrl-C reaches it directly:

<!-- from: TOOLS/GIT1/git1.ady -->
```python
shellExec(cwd = self.dir, env = self.env): git {*args}
```

---

## 2. Quoting, which is where shell scripts actually break

`{x}` interpolates the value **as written**, which is what a command fragment
needs. `{!x}` quotes it. `{*xs}` quotes every element of a list and joins
them. The difference is the single most common bug in shell:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let f: str = "my notes.txt"
let split_up = shell: printf '[%s]' {f}
let one_arg  = shell: printf '[%s]' {!f}
assert split_up.output == "[my][notes.txt]"      # two arguments
assert one_arg.output  == "[my notes.txt]"       # one

let argv: []str = ["-m", "two words"]
let starred = shell: printf '[%s]' {*argv}
assert starred.output == "[-m][two words]"
```

`{*args}` is `"$@"` done right, and unlike `"$@"` it is not one character
away from being wrong.

But the real answer is not to quote better — it is to stop handing a string
to a parser. `run` takes an argument list, and nothing parses it a second
time:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let nasty: str = "; echo pwned"
let safe: RunResult = run(["printf", "[%s]", nasty])
assert safe.output == "[; echo pwned]"

let listing: []str = runLines(["printf", "a\nb\n"])
```

Reach for `shell:` when you actually want a shell — pipes, redirection,
globbing, `&&`. Reach for `run` when you just want to run a program, which is
most of the time.

---

## 3. Errors, instead of `set -e` and `$?`

`set -euo pipefail` is three separate patches over three separate defaults,
and every one of them has exceptions you have to remember. Adascript makes
the choice per command.

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
try:
    shell(check = true): exit 9
except:
    print "handled"
```

`check = true` raises on a non-zero status — `OSError` on Nim,
`CalledProcessError` on Python, both catchable — and works with every form.
Leave it off and the status is yours to inspect; there is no global mode to
forget to set.

A pipeline's status is the POSIX one unless you ask otherwise:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let loose  = shell: false | cat
let strict = shell(pipefail = true): false | cat
assert loose.code == 0            # the failure vanished, as POSIX says
assert strict.code != 0
```

An indented block joins its lines with `&&`, so it stops at the first
failure — the `set -e` behaviour, scoped to the block that wanted it:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let built = shell:
    echo one
    echo two
assert built.output == "one\ntwo\n"
```

`join = ";"` runs them all regardless, `join = "|"` makes one pipeline:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let anyway = shell(join = ";"):
    false
    echo still here
assert anyway.output.strip() == "still here"
```

---

## 4. Reading output, instead of `while read`

`$(cmd)` in a `for` loop splits on `$IFS`, which means a filename with a
space becomes two filenames. `while read -r line; do ... done < <(cmd)` fixes
it and is three constructs deep. `shellLines:` is the whole thing:

<!-- from: TOOLS/GIT1/git1.ady -->
```python
let entries = shellLines: ls -1a {!self.path}
```

That is `git1.ady`, and yes — it is parsing `ls`, which it can do safely
because `-1a` puts one name on each line and `shellLines` splits on newlines
only. When the output is long or slow, `shellIter` yields each line as it
arrives, so nothing is held in memory:

<!-- illustrative: `tail -f` never ends, so there is nothing for `make test` to run -->
```python
for line in shellIter: tail -f build.log
    print line
```

`check = true` on a `shellIter` raises once the stream is over, since that is
when the status exists — and a `break` never raises, because an unfinished
command has no status to object to.

---

## 5. Doing several things at once, without `&` and `wait`

Backgrounding in shell gives you `$!`, a `wait` that returns one status, and
no way to say which job produced what. `shellSpawn` hands back a `Job`:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
var jobs: []Job = []
for n in ["1", "2", "3"]:
    let j: Job = shellSpawn: echo {!n}
    jobs.append(j)

let results: []RunResult = waitAll(jobs)
for res in results:
    assert res.code == 0
```

`results[i]` is job `i`'s: its own output, its own stderr, its own status.

**Use `waitAll` rather than a `wait` per job.** Output goes into a pipe, a
pipe holds 64K, and a job that fills it stops until something drains it — so
waiting on jobs one at a time quietly serialises what you just started in
parallel. `waitAll` drains all of them as it goes.

A single job answers a few questions directly: `j.running()` never blocks,
`j.wait()` does, `j.wait(check = true)` raises, `j.kill()` is safe twice, and
`j.pid` is what you expect.

---

## 6. The child's environment, not `VAR=x cmd`

`env` takes a `{str}str` and **adds** to what the child inherits — `PATH` and
everything else is still there:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let extra: {str}str = {"ADY_DOC_VAR": "set-by-parent"}
let seen_env = shell(env = extra): printf '%s' "$ADY_DOC_VAR"
assert seen_env.output == "set-by-parent"
```

`git1.ady` uses it for the reason that matters — the value crosses into the
child without the shell parsing it on the way:

<!-- from: TOOLS/GIT1/git1.ady -->
```python
let one_env: {str}str = {"GIT_DIR": str(gitdir)}
let r = shell(env = one_env): git log -1 --format='%cr'
```

`stdin = expr` feeds the child, so a here-document becomes an expression:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let sorted_out = shell(stdin = "gamma\nalpha\nbeta\n"): sort
assert sorted_out.output == "alpha\nbeta\ngamma\n"
```

`cwd = dir` is `( cd dir && ... )` without the subshell, and `timeout = ms`
is `timeout(1)` without the dependency.

---

## 7. Paths join with an operator

String concatenation with `/` between the parts is how a shell script ends up
with `//` in the middle of a path and an empty variable turning `$dir/$name`
into `/etc/passwd`. `Path` makes joining an operation:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
let root: Path = Path("/tmp")
let log:  Path = root / "ady_shell_doc" / "app.log"
assert str(log) == "/tmp/ady_shell_doc/app.log"
assert log.name == "app.log"
assert str(log.parent) == "/tmp/ady_shell_doc"
log.parent.mkdir()                  # mkdir -p: parents made, existing is fine
```

`Path` is a string that also joins, so it goes wherever a `str` goes — a file
test, `readFile`, shell interpolation, a dict key. The other direction is
deliberate: `Path(s)` to make one, `str(p)` to go back, and a bare `p = s` is
an error on both backends.

The shell's file tests come across unchanged, and mean what they mean:

<!-- illustrative: a checklist of the file tests, with the bodies elided -->
```python
if -f path:  ...      # and -d -e -L -r -w -x -s
if a -nt b:  ...
if which("git") is not None: ...   # is it even installed?
```

`which` is `command -v foo` with the redirection already thought about, and
the answer kept: a `?Path` rather than an exit status. (`have("git")` is the
older spelling that only ever said yes or no; it is deprecated and warns.)

---

## 8. Arguments and the environment

Positional parameters, the count, and the whole list are spelled as you would
expect:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
assert $# >= 0
let first: str = $1
for arg in $@[1:]:
    ...
```

The environment has three readings, and the difference between them is one
shell can only fake:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
assert $HOME != ""
assert $NO_SUCH_VAR_HERE == ""                  # unset reads as empty, as in sh
assert ${NO_SUCH_VAR_HERE:-"fallback"} == "fallback"
assert $?NO_SUCH_VAR_HERE == None               # ...unless you ask this way
```

`$NAME` is a `str` and reads unset as `""`, exactly as the shell does.
`${NAME:-default}` is the shell's fallback, including the `:` — it fires on
unset *or* empty. `$?NAME` is a `?str`, which is the one shell cannot
express: it tells "not set" from "set to nothing".

All three read. There is no `export`: `$PATH = "/opt/bin:" + $PATH` is
refused, and the message says what to write instead. A shell exports so that
the commands it runs will see the value, and §6 above hands those commands
the value directly — `shellExec(env = extra): cmd` is `export` and `exec` in
one line, with nothing left behind in a process that is about to be replaced
anyway. Argument variables refuse assignment for the same reason.

---

## 9. Text, without the pipeline

The sed/grep/awk pipeline exists because shell has no way to look at a
string. Adascript has regex literals, so matching is an operator and captures
are variables:

<!-- illustrative: a fragment -- `line` comes from a loop that is not shown -->
```python
if line == /^(\w+)=(\d+)$/:
    let key:   str = $+1
    let value: int = int($+2)
```

`s == /pat/g` is every match as a `[]str`; `s = s/pat/repl/g` is `sed
's/pat/repl/g'` assigning back to the variable. `DOCS/ADASCRIPT_FOR_AWK.md`
covers the whole family, along with `case`/`when` over regex patterns — which
is what a chain of `case "$x" in ... esac` wanted to be.

---

## 10. The part shell has no word for

Everything above is ergonomics. This is the part that changes what you can
write.

**An enum instead of a bare word.** In shell, `action="compress"` and the
four places that test it are four independent chances to typo. Here it is a
type, and a `case` over it is checked for completeness by the Nim backend —
miss a member and the program does not compile:

<!-- illustrative: a case over Action_T with the branch bodies elided -->
```python
type Action_T is enum COMPRESS, DELETE, KEEP, SKIP

case e.action:
    when COMPRESS: ...
    when DELETE:   ...
    when others:   pass
```

Add a fifth member and every `case` over the type becomes a compile error
listing the places you have to think about. Iterate the type itself to get
every member in declaration order — useful for a report that must not forget
a category:

<!-- from: EXAMPLES/sh_janitor.ady -->
```python
for a in Action_T:
    print f"  {a'Image:<8} {counts[a]:>2} file(s), {bytes[a]:>4} bytes"
```

**A record instead of parallel arrays.** Shell's answer to a table is
`name_1`, `size_1`, `name_2`, `size_2`, or an array per column and an index
you carry by hand:

<!-- from: EXAMPLES/sh_janitor.ady -->
```python
type Entry_T is record:
    """One file, decided once."""
    path:   Path
    size:   Natural = 0
    action: Action_T = KEEP
```

**`Natural` instead of a counter that can go negative**, checked at run time
on the Nim backend, including under `-d:release`. **`?T` instead of `""`
meaning absent.** And arithmetic that is arithmetic — no `$(( ))`, no `expr`,
no surprise when a value has a leading zero.

---

## 11. What you do not need a Python import for

Adascript can reach into Python with `pyimport`, and the temptation, coming
from Python, is to reach for it the moment you want the time or the process
id. Don't. **`pyimport` is for libraries with no shell equivalent** —
`numpy`, `requests`, `pandas`, a vendor's SDK. Everything a shell script
already knows how to ask for, ask for the same way here.

It is not a style preference. On the Nim backend a `pyimport` is a real
dependency: the build needs [nimpy](https://github.com/yglukhov/nimpy) on
the Nim path, the binary links against libpython, and it has to find a
matching interpreter at run time. A program that imports `datetime` to
format a timestamp has bought all of that for one line of `date`.

**Two of them are not even the shell's job.** `os` and `time` are mapped
natively: written `nimport os` and `nimport time` rather than `pyimport`,
they become Nim's own `getCurrentProcessId()` and `epochTime()` on one
backend and Python's `os` and `time` on the other. A `nimport` costs the
build nothing, so it beats starting a process. Only what has *no* mapping
goes to the shell.

| you might reach for | ask the language, or the shell |
|---|---|
| `pyimport os` → `os.getpid()` | **`nimport os`** → `os.getpid()` |
| `pyimport time` → `time.time()` | **`nimport time`** → `time.time()` |
| `pyimport datetime` → `now().strftime(...)` | `shell: date +%Y-%m-%d-%H%M%S` |
| `pyimport sys` → `sys.platform` | `shell: uname -s` |
| `pyimport sys` → `sys.exit(1)` | `quit(1)` |
| `pyimport getpass` → `getuser()` | `shell: id -un` |
| `pyimport socket` → `gethostname()` | `shell: hostname` |
| `pyimport tempfile` → `mkdtemp()` | `shell: mktemp -d` |
| `pyimport os` → `os.environ["HOME"]` | `$HOME`, `$?HOME`, `${HOME:-"/root"}` |
| `pyimport os.path` → `join`, `dirname`, `exists` | `Path`, `/`, `.parent`, `-f`, `-d` |
| `pyimport shutil` → `copy`, `move` | `shell: cp -a {!src} {!dst}` |
| `pyimport glob` → `glob("*.log")` | `shellLines: ls -1 {!dir}` |
| `pyimport subprocess` | `shell:`, `run()` — the whole of §1–§7 |
| `pyimport re` → `re.match(...)` | a regex literal: `s == /pat/`, `$+1`, `s = s/a/b/g` |

The two native ones read as ordinary calls, and start nothing:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
    assert os.getpid() > 0
    let t0: float = time.time()
```

The rest are one line each, and the capture forms of §2 are how the answer
gets back:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
    let (stamp, rc_stamp) = shell: date +%Y-%m-%d-%H%M%S
    assert stamp.strip()'Length == 17
```

**`$PPID` is the trap worth knowing.** `$NAME` in Adascript reads the
*environment*, and `PPID` is a shell variable that no shell exports — so a
bare `$PPID` is the empty string, every time, on both backends. Inside a
`shell:` it does work, because there a shell is running and the shell it
starts is your child, so its `$PPID` is you. That is a real fact and
occasionally the only way to reach the number from inside a pipeline that
is already running. It is not how you ask for your own process id:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
    let from_env: str = $PPID
    assert from_env == ""
    let (pid, rc_pid) = shell: echo $PPID
    assert int(pid.strip()) == os.getpid()
```

**Prefer the command that answers where the environment is thin.** `$USER`
is unset in most containers; `id -un` answers anyway:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
    let (who, rc_who) = shell: id -un
```

### When a date needs arithmetic rather than formatting

`time.time()` gives you now and `date` formats, but turning *a stamp you
already have* into an epoch is where the shell answer stops being portable:
`date -d` is GNU, and `date -j -f` is BSD. If a program has to do that —
comparing backup directories by age, say — the arithmetic is a dozen lines
and runs anywhere. `EXAMPLES/rsync_time_machine.ady` has it as
`days_from_civil`, and dropping its five `pyimport`s for that plus the table
above is what let it into `make test`: the Nim build no longer needs nimpy
at all.

### When the pattern is data

`re` is the one row in that table where the replacement is not the shell but
the language: matching is an operator and captures are variables, so
`pyimport re` is never the way to match against a pattern you can *write*.
Chapter 7 of the book has the whole family.

The exception is a pattern you cannot write, because it is not known until
the program runs -- a rule read out of a configuration file or a database
column. A regex literal is a literal, so there is nothing to put in it, and
this is where the reflex to reach for `re` is strongest. The shell has
matched a string against a pattern handed to it at runtime since v7, and
`grep`'s exit status is the whole answer:

<!-- from: EXAMPLES/CFMU/cfmu_get_file_type.ady -->
```python
def matches(text: str, pattern: str) -> bool:
  let (_, rc) = shell(stdin = text + "\n"): grep -qE -- {!pattern}
  return rc == 0
```

`-E` is POSIX ERE; `-q` answers without printing; `--` keeps a pattern that
starts with a dash from being read as an option; and feeding the subject
through `stdin =` rather than the command line keeps it out of the quoting
entirely. `EXAMPLES/CFMU/cfmu_get_file_type.ady` is the live use -- its
patterns are rows of an `ftps_cleanup` table -- and dropping its `pyimport
re` for those three lines is what let it compile at all: it was the last
file under `EXAMPLES/CFMU/` still asking the Nim build for nimpy.

### What is left for `pyimport`

A library, not a fact about the machine. `pyimport numpy`, `pyimport
requests`, `pyimport yaml` — things with no `/usr/bin` equivalent and no
answer in `$VAR`. There the bridge earns its cost, and
`DOCS/BOOK/12-two-backends.md` §12.2 covers how it works.

`EXAMPLES/pyimport_similar.ady` is what that looks like: the file whose
whole subject is the bridge, and the only one `make test` actually runs
across it. (`EXAMPLES/tsp.ady` keeps a `pyimport` too — `matplotlib`, to
draw its tours — but that one needs an install, so it is compiled and not
run.) It asks `difflib`
which of a tool's subcommands a typo most resembles. `grep` answers
*whether* a pattern matched, and the question here is *how close* and which
candidate is closest — a ranking, which no standard tool computes. It is a
standard-library module rather than `numpy` so that `make test` can run it
without an install first; the bridge is the same one either way, and so is
what it costs: nimpy on the Nim path, a libpython link, an interpreter at
run time, and a `Testing libpython: ...` line on stdout ahead of the
program's own output.

---

## 12. A worked example

`EXAMPLES/sh_janitor.ady` is the log-rotation script every site has written
in Bash. It builds its own fixture under `/tmp` so the run is self-contained,
and **the filenames contain spaces on purpose**: that is the bug the Bash
version has.

That Bash version is in the repository too, as `EXAMPLES/sh_janitor.sh`, so
the claim can be run rather than believed. It is not sabotaged: same
decisions, same fixture, same report, written the way these are written.

The decision is made once, over a closed set of outcomes:

<!-- from: EXAMPLES/sh_janitor.ady -->
```python
def decide(p: Path, size: Natural) -> Action_T: # a pure function is also a mapping.
    let BIG_ENOUGH : Natural = 64      # bytes; a real one would say 10 MB
    case p.name:
        when /\.gz$/: SKIP       # already done
        when /^\./: SKIP        # dotfile
        when /\.(log|out|err)$/: COMPRESS if size >= BIG_ENOUGH else KEEP
        when /\.tmp$|~$/: DELETE
        when others: KEEP
```

The listing does not parse `ls` through `$IFS` — `runLines` skips the shell
entirely, so each name stays one name however many spaces it holds:

<!-- from: EXAMPLES/sh_janitor.ady -->
```python
for name in sorted(runLines(["ls", "-A", str(dir)])):
    let p: Path = dir / name
    if not -f p:
        continue
```

The work runs in parallel, with a status per job rather than one for the lot,
and every interpolated path is quoted:

<!-- from: EXAMPLES/sh_janitor.ady -->
```python
var jobs   : []Job     = []
var zipped : []Entry_T = []
for e in entries:
    case e.action:
        when COMPRESS:
            let j: Job = shellSpawn: gzip -f -- {!e.path}
            jobs.append(j)
            zipped.append(e)
        when DELETE:
            shell(check = true): rm -f -- {!e.path}
        when others:
            pass

let results: []RunResult = waitAll(jobs)
```

Run it:

```
$ EXAMPLES/sh_janitor
--- sh_janitor /tmp/ady_janitor ---
  COMPRESS  3 file(s),  628 bytes
  DELETE    2 file(s),   20 bytes
  KEEP      2 file(s),   23 bytes
  SKIP      2 file(s),   40 bytes
  0 failure(s)

$ ls -1 /tmp/ady_janitor
app.conf
app.log.gz
build.out.gz
old.log.gz
quiet service.log.gz
tiny.log
```

`quiet service.log.gz` is the whole point. Here is the Bash version of the
same run, on its own copy of the same fixture:

```
$ EXAMPLES/sh_janitor.sh
--- sh_janitor /tmp/sh_janitor_sh ---
  COMPRESS  2 file(s),  328 bytes
  DELETE    1 file(s),   10 bytes
  KEEP      2 file(s),   23 bytes
  SKIP      2 file(s),   40 bytes
  0 failure(s)
$ echo $?
0
```

Two files are missing from the report, and the report does not say so. The
line responsible is the one everybody writes:

```bash
for f in $(ls -A "$DIR"); do
```

`ls` writes one name per line; the shell splits that on whitespace; `quiet
service.log` becomes `quiet` and `service.log`; neither exists, so `[ -f
"$path" ] || continue` drops both. The file is never compressed, `editor
backup~` is never deleted, nine files go in and seven are accounted for, and
the exit status is 0. Nothing in that output is an error message, which is
what makes it worth a section: the failure mode of shell quoting is not a
crash, it is a report that is quietly wrong.

`make test` asserts that this is still what happens — if `sh_janitor.sh`
ever agrees with `sh_janitor`, this section is stale and the check fails.

The quoting itself is fixable, and it is worth being clear that it is:
`find "$DIR" -maxdepth 1 -print0 | while IFS= read -r -d '' path` and quotes
on every expansion after it. What the fix does not touch is everything else
this section is about — `ACTION` is still a string that nothing checks
against the four places that test it, `wait` still reports the last job
rather than each of them, and the totals are still four pairs of variables
that have to be updated in step by hand.

---

## 13. Translation table

| Shell | Adascript |
|-------|-----------|
| `cmd` | `shell: cmd` |
| `out=$(cmd)` | `let r = shell: cmd` → `r.output`, or `let (text, rc) = shell: cmd` |
| `cmd; rc=$?` | `let (text, rc) = shell: cmd` — the status is a value, not `$?` |
| `readarray -t a < <(cmd)` | `let a: []str = shellLines: cmd` |
| `cmd` with the terminal (pager, colours) | `let code: int = shell: cmd` |
| `exec cmd` | `shellExec: cmd` |
| `"$var"` in a command | `{!var}` |
| `$var` unquoted, on purpose | `{var}` |
| `"$@"` | `{*args}` |
| `cmd "$a" "$b"` with no shell at all | `run(["cmd", a, b])` |
| `set -e` | `shell(check = true): cmd` |
| `set -o pipefail` | `shell(pipefail = true): a \| b` |
| `a && b && c` | an indented `shell:` block |
| `a; b; c` | `shell(join = ";"):` block |
| `while read -r l; do …; done < <(cmd)` | `for l in shellIter: cmd` |
| `cmd & … wait` | `let j: Job = shellSpawn: cmd` … `waitAll(jobs)` |
| `$!` | `j.pid` |
| `kill $!` | `j.kill()` |
| `VAR=x cmd` | `shell(env = {"VAR": x}): cmd` |
| `( cd d && cmd )` | `shell(cwd = d): cmd` |
| `timeout 30 cmd` | `run(argv, timeout = 30000)` |
| `cmd <<EOF … EOF` | `shell(stdin = text): cmd` |
| `"$dir/$name"` | `dir / name`, with `dir: Path` |
| `mkdir -p "$d"` | `d.mkdir()` |
| `dirname`, `basename` | `p.parent`, `p.name` |
| `[ -f "$p" ]`, `[ -d "$p" ]` | `-f p`, `-d p` — unchanged |
| `command -v foo >/dev/null` | `which("foo") is not None` |
| `p=$(command -v foo)` | `which("foo")`, a `?Path` |
| `$1`, `$#`, `$@` | `$1`, `$#`, `$@` |
| `$HOME` | `$HOME` |
| `${VAR:-default}` | `${VAR:-default}` |
| unset vs. empty | `$?NAME` → `?str`; `None` vs `""` |
| `case "$x" in p) … esac` | `case x:` with `when /p/:` |
| `echo "$s" \| sed 's/a/b/g'` | `s = s/a/b/g` |
| `grep -q pat <<< "$s"` | `s == /pat/` |
| `[[ $s =~ re ]]; ${BASH_REMATCH[1]}` | `if s == /re/:` … `$+1` |
| `$(( a + b ))` | `a + b` |
| `action="compress"` | `type Action_T is enum COMPRESS, …` |
| `name_1`, `size_1`, `name_2`, … | a `record` |

### The dollars that do not mean what they mean in the shell

Most of them carry over unchanged, which is the point — `$1`, `$#`, `$@`,
`$HOME` and `${VAR:-default}` are all themselves. Three are not:

| | means | the shell's version |
|---|---|---|
| `$NAME` | an **environment** variable, only ever that | `$NAME`, which may also be a local |
| `$?NAME` | **is it set at all** — a `?str`, `None` when it is not | `${NAME+set}`, or `[ -v NAME ]` in bash |
| `$+1` | a **capture group** of the regex that just matched | `${BASH_REMATCH[1]}`, after `[[ =~ ]]` |

And one that is simply absent: **there is no `$?`**. A command's status is a
value the shell form hands back, so it is named where it is used and cannot
be read after the wrong command:

<!-- from: EXAMPLES/DOC/shell_snippets.ady -->
```python
    let (text, rc) = shell: git rev-parse --git-dir
```

`$?NAME` is not `$?` with a name after it — the `?` belongs to the `?str`
the whole thing produces, and `$?` on its own does not parse. The other
collision is quieter: `$name` in Adascript always means the environment,
never a local. A local is an ordinary identifier, and inside a command it
goes in braces — `{!name}` quoted, `{name}` deliberately not. So the shell's
habit of writing `$x` for a variable you set two lines earlier reads, here,
as "the environment variable `x`", and finds nothing.

---

## 14. Where to go next

- `EXAMPLES/sh_janitor.ady` — the worked example above
- `EXAMPLES/sh_janitor.sh` — the Bash version of it, to run side by side
- `TOOLS/GIT1/git1.ady` — a real tool: `cwd`, `env`, `shellExec`, `Path`, file tests
- `EXAMPLES/CFMU/` — a directory of ksh scripts translated line by line
- `EXAMPLES/test_shell_block.ady` — every block and join form
- `DOCS/ADASCRIPT_FOR_AWK.md` — the text-processing half of the same argument
- `DOCS/BOOK/11-shell-and-scripting.md` — the shell forms in full
- `README.md`, *Shell Statements* — the complete reference for the options
