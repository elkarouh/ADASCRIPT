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
still get the status. `EXAMPLES/git1.ady` uses the two forms deliberately —
one for the commands the user is meant to watch, one for the commands whose
answer is their output:

```python
let code: int = shell(cwd = self.dir, env = self.env): git {*args}
...
let lines = shellLines(cwd = self.dir, env = self.env): git {*args}
```

And when the last thing your script does is run a program, `shellExec`
replaces this process with it — the status is the child's by construction and
Ctrl-C reaches it directly:

```python
shellExec(cwd = self.dir, env = self.env): git {*args}
```

---

## 2. Quoting, which is where shell scripts actually break

`{x}` interpolates the value **as written**, which is what a command fragment
needs. `{!x}` quotes it. `{*xs}` quotes every element of a list and joins
them. The difference is the single most common bug in shell:

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

```python
let loose  = shell: false | cat
let strict = shell(pipefail = true): false | cat
assert loose.code == 0            # the failure vanished, as POSIX says
assert strict.code != 0
```

An indented block joins its lines with `&&`, so it stops at the first
failure — the `set -e` behaviour, scoped to the block that wanted it:

```python
let built = shell:
    echo one
    echo two
assert built.output == "one\ntwo\n"
```

`join = ";"` runs them all regardless, `join = "|"` makes one pipeline:

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

```python
let entries = shellLines: ls -1a {!self.path}
```

That is `git1.ady`, and yes — it is parsing `ls`, which it can do safely
because `-1a` puts one name on each line and `shellLines` splits on newlines
only. When the output is long or slow, `shellIter` yields each line as it
arrives, so nothing is held in memory:

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

```python
let extra: {str}str = {"ADY_DOC_VAR": "set-by-parent"}
let seen_env = shell(env = extra): printf '%s' "$ADY_DOC_VAR"
assert seen_env.output == "set-by-parent"
```

`git1.ady` uses it for the reason that matters — the value crosses into the
child without the shell parsing it on the way:

```python
let one_env: {str}str = {"GIT_DIR": str(gitdir)}
let r = shell(env = one_env): git log -1 --format='%cr'
```

`stdin = expr` feeds the child, so a here-document becomes an expression:

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

```python
if -f path:  ...      # and -d -e -L -r -w -x -s
if a -nt b:  ...
if have("git"): ...   # is it even installed?
```

`have` is `command -v foo >/dev/null 2>&1` with the redirection already
thought about.

---

## 8. Arguments and the environment

Positional parameters, the count, and the whole list are spelled as you would
expect:

```python
assert $# >= 0
let first: str = $1
for arg in $@[1:]:
    ...
```

The environment has three readings, and the difference between them is one
shell can only fake:

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

---

## 9. Text, without the pipeline

The sed/grep/awk pipeline exists because shell has no way to look at a
string. Adascript has regex literals, so matching is an operator and captures
are variables:

```python
if line == /^(\w+)=(\d+)$/:
    let key:   str = $+1
    let value: int = int($+2)
```

`s == /pat/g` is every match as a `[]str`; `s == s/pat/repl/g` is `sed
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

```python
for a in Action_T:
    print f"  {a'Image:<8} {counts[a]:>2} file(s)"
```

**A record instead of parallel arrays.** Shell's answer to a table is
`name_1`, `size_1`, `name_2`, `size_2`, or an array per column and an index
you carry by hand:

```python
type Entry_T is record:
    path:   Path    = Path("")
    size:   Natural = 0
    action: Action_T = KEEP
```

**`Natural` instead of a counter that can go negative**, checked at run time
on the Nim backend, including under `-d:release`. **`?T` instead of `""`
meaning absent.** And arithmetic that is arithmetic — no `$(( ))`, no `expr`,
no surprise when a value has a leading zero.

---

## 11. A worked example

`EXAMPLES/sh_janitor.ady` is the log-rotation script every site has written
in Bash. It builds its own fixture under `/tmp` so the run is self-contained,
and **the filenames contain spaces on purpose**: that is the bug the Bash
version has.

The decision is made once, over a closed set of outcomes:

```python
def decide(p: Path, size: Natural) -> Action_T:
    """One decision per file, in one place, over a closed set of outcomes."""
    let name: str = p.name
    case name:
        when /\.gz$/:            return SKIP        # already done
        when /^\./:              return SKIP        # dotfile
        when /\.(log|out|err)$/:
            if size >= BIG_ENOUGH:
                return COMPRESS
            return KEEP
        when /\.tmp$|~$/:        return DELETE
        when others:
            return KEEP
```

The listing does not parse `ls` through `$IFS` — `runLines` skips the shell
entirely, so each name stays one name however many spaces it holds:

```python
for name in sorted(runLines(["ls", "-A", str(dir)])):
    let p: Path = dir / name
    if not -f p:
        continue
```

The work runs in parallel, with a status per job rather than one for the lot,
and every interpolated path is quoted:

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

`quiet service.log.gz` is the whole point. The Bash version compressed a file
called `quiet` and a file called `service.log`, or said `gzip: quiet: No such
file or directory` and carried on with status 0 because nobody checked.

---

## 12. Translation table

| Shell | Adascript |
|-------|-----------|
| `cmd` | `shell: cmd` |
| `out=$(cmd)` | `let r = shell: cmd` → `r.output`, or `let (out, rc) = shell: cmd` |
| `cmd; rc=$?` | `let (out, rc) = shell: cmd` |
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
| `command -v foo >/dev/null` | `have("foo")` |
| `$1`, `$#`, `$@` | `$1`, `$#`, `$@` |
| `$HOME` | `$HOME` |
| `${VAR:-default}` | `${VAR:-default}` |
| unset vs. empty | `$?NAME` → `?str`; `None` vs `""` |
| `case "$x" in p) … esac` | `case x:` with `when /p/:` |
| `echo "$s" \| sed 's/a/b/g'` | `s == s/a/b/g` |
| `grep -q pat <<< "$s"` | `s == /pat/` |
| `$(( a + b ))` | `a + b` |
| `action="compress"` | `type Action_T is enum COMPRESS, …` |
| `name_1`, `size_1`, `name_2`, … | a `record` |

---

## 13. Where to go next

- `EXAMPLES/sh_janitor.ady` — the worked example above
- `EXAMPLES/git1.ady` — a real tool: `cwd`, `env`, `shellExec`, `Path`, file tests
- `EXAMPLES/CFMU/` — a directory of ksh scripts translated line by line
- `EXAMPLES/test_shell_block.ady` — every block and join form
- `DOCS/ADASCRIPT_FOR_AWK.md` — the text-processing half of the same argument
- `DOCS/BOOK/11-shell-and-scripting.md` — the shell forms in full
- `README.md`, *Shell Statements* — the complete reference for the options
