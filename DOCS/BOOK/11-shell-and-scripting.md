# Chapter 11 — Shell Integration: Adascript as a Better Bash

Every scripting language eventually shells out; few make it pleasant.
Adascript makes subprocess execution, command-line arguments, environment
variables and file tests part of the *syntax*, so the scripts you would have
written in Bash gain types, data structures and two compilation targets —
without losing Bash's directness. The `EXAMPLES/INTERACTIVE/` directory is
this chapter's home turf.

The surface has grown enough to be worth a map before the tour.

## 11.1 Choosing a form

| You want | Form | Gives back |
|----------|------|------------|
| Output, error output and status | `let r = shell: cmd` | `.output`, `.stderr`, `.code` |
| Output as lines | `let ls: []str = shellLines: cmd` | `[]str` |
| The terminal kept, and the status | `let code: int = shell: cmd` | `int` |
| Nothing — just run it | `shell: cmd` | — |
| Output line by line, as it arrives | `for line in shellIter: cmd` | one `str` per line |
| To start it and carry on | `let j: Job = shellSpawn: cmd` | a `Job` to `wait()` on |
| To *become* the command | `shellExec: cmd` | never returns |
| To run a program with no shell at all | `run(argv)` / `runLines(argv)` | `RunResult` / `[]str` |

The first four are the common ones; the rest exist because a script that
outgrows them otherwise reaches for a temp file or a hand-rolled helper.

Two rules of thumb. Reach for `shell:` when you want a *shell* — pipes,
redirection, globbing, `&&`. Reach for `run` when you just want to run a
program, which is most of the time and is the only form where quoting cannot
go wrong.

## 11.2 `shell:` and `shellLines:`

```python
let result = shell: git status
print(result.output)   # stdout as a string
print(result.stderr)   # stderr as a string
print(result.code)     # exit code as int
```

Destructuring works — take just what you need. The slots are stdout, the
exit code, then stderr:

```python
let (out, code) = shell: some-command
let (out2, code2, err2) = shell: some-command
```

`shellLines:` splits stdout into `[]str`, one element per line. Combined
with implicit return, a shell command becomes a typed function:

```python
def getTestStatusLines() -> []str:
    shellLines: show_tests_status -raw
```

The assignment target accepts type annotations, bare names, or
`let`/`var`/`const`:

```python
let entries: []str = shellLines: ls -1a /tmp
output = shellLines: find . -name "*.ady"
```

With no assignment target, output is simply discarded:

```python
shell: rm -rf /tmp/build
```

An **`int`-typed target** is the form to reach for when a command should keep
the terminal — its output, its colours, its pager — while still reporting
whether it worked:

```python
let code: int = shell: git log --oneline
```

Capturing would have taken the terminal away; discarding would have thrown
the status away. This form does neither, and it is what a wrapper around an
interactive tool almost always wants.

## 11.3 Interpolation, and the quoting that goes with it

`{name}` interpolates anywhere in the command body. Function calls and other
complex expressions work too — the transpiler hoists them to temp variables
in the Nim output:

```python
let branch: str = "main"
let result = shell: git log --oneline {branch}
```

The command is a *string handed to a shell*, so a value that might contain a
space or a metacharacter has to say so. Three sigils, and the difference
matters:

```python
let f: str = "my notes.txt"
shell: ls -l {f}               # ls -l my notes.txt   — two arguments
shell: ls -l {!f}              # ls -l 'my notes.txt' — one argument
```

`{!expr}` quotes the value as a single argument. `{*xs}` does the same for
every element of a list and joins them:

```python
let args: []str = ["commit", "-m", "two words"]
shell: git {*args}             # git commit -m 'two words'
```

Nim emits `quoteShell(expr)` and `mapIt(xs, quoteShell(it)).join(" ")`;
Python `shlex.quote(expr)` and `' '.join(...)`. The rule is short: a value
that is *part of* a command uses `{x}`; a value that is *an argument to* one
uses `{!x}`.

This is one character per site rather than a habit to remember, which is the
point — but it is still a habit. §11.6 shows the form that removes the
question entirely.

## 11.4 Options

Options go in parentheses before the colon:

```python
let r2 = shell(cwd = "/tmp", timeout = 3000): ls -la
```

| Option | Means |
|--------|-------|
| `cwd = dir` | run it somewhere else |
| `timeout = ms` | kill it after `ms`; the status is 124, as `timeout(1)` reports |
| `check = true` | raise instead of returning a non-zero status |
| `stdin = text` | feed the child that string |
| `env = table` | add to the child's environment (`{str}str`) |
| `pipefail = true` | a pipeline reports its first failure, not its last command |
| `join = "…"` | how a block's lines are strung together |

Which form takes which:

| | `cwd` | `env` | `timeout` | `stdin` | `check` | `pipefail` |
|---|---|---|---|---|---|---|
| `shell:` / `shellLines:` | ✓ | ✓ | ✓ | capturing forms | ✓ | ✓ |
| `shellIter` | ✓ | ✓ | | | ✓ (at the end) | ✓ |
| `shellSpawn` | ✓ | ✓ | | ✓ | | ✓ |
| `shellExec` | ✓ | ✓ | | | | ✓ |
| `run` / `runLines` | ✓ | ✓ | ✓ | ✓ | ✓ | n/a — no shell |

An option a form cannot honour is a transpile-time error rather than a
silent no-op, and a misspelled one says what you probably meant:

```
shell: unknown option `timout` -- did you mean `timeout`?
       (supported: check, cwd, env, stdin, timeout)
shellExec(timeout = ...) is not supported: shellExec replaces this process,
       so there is no child to time out. timeout works on shell, shellLines.
```

That matters more than it sounds. An option that is quietly dropped leaves
a script that *reads* as though it has a timeout and does not have one.

### `check = true`

```python
shell(check = true): git commit -m {!msg}

try:
    shell(check = true): exit 9
except:
    print("handled")
```

`OSError` on the Nim backend, `CalledProcessError` on Python, both catchable.

### `env` and `stdin`

`env` **adds** to the environment the child inherits rather than replacing
it, so a child never silently loses `PATH`:

```python
let extra: {str}str = {"GIT_DIR": repo, "LC_ALL": "C"}
let r3 = shell(env = extra): git status
```

`stdin` feeds a string to the child, and applies to the capturing forms,
since those are the ones that give the child a pipe:

```python
let text: str = "gamma\nalpha\nbeta\n"
let sorted_r = shell(stdin = text): sort
```

Writing it is interleaved with reading the child's output, so feeding a
command more than a pipe buffer holds does not deadlock.

### `pipefail`

A pipeline's exit status is its *last* command's — what POSIX says, and
almost never what a script means:

```python
let lax = shell: false | cat
print(lax.code)                        # 0 — the failure vanished
let strict = shell(pipefail = true): false | cat
print(strict.code)                     # non-zero
```

`/bin/sh` is dash on most Linuxes and has no `set -o pipefail`, so both
backends run these through bash — which therefore has to be installed for
this option.

## 11.5 Bash variables, file tests, and `have()`

| Adascript | Meaning | Python | Nim |
|-----------|---------|--------|-----|
| `$0` | script name | `sys.argv[0]` | `getAppFilename()` |
| `$1` … `$9` | positional args | `sys.argv[N]` | `paramStr(N)` |
| `$@` | all args | `sys.argv[1:]` | `commandLineParams()` |
| `$#` | arg count | `len(sys.argv) - 1` | `paramCount()` |
| `$NAME` | env variable | `os.environ.get('NAME','')` | `getEnv("NAME")` |

File tests are expressions: `-e` (exists), `-f` (file), `-d` (dir), `-L`
(symlink), `-r`/`-w`/`-x` (permissions), `-s` (non-empty), and the
comparisons `a -nt b` / `a -ot b` (newer/older than). They negate and
combine normally: `if not -f dict_file:`.

Whether a *program* exists is the same kind of question, and `have` answers
it from `PATH` — `shutil.which` on Python, `findExe` on Nim — so unlike
`command -v` it costs neither a process nor a shell:

```python
if not have("git"):
    print("git is required")
    quit(1)
```

`phonecode.ady`'s argument handling shows the whole kit in six lines:

```python
def main():
    let dict_file: str  = ($1 if $# >= 1 else "test_words.txt")
    let phone_file: str = ($2 if $# >= 2 else "test_phones.txt")

    if not -f dict_file:
        print(f"Error: Dictionary file not found: {dict_file}")
        print("Usage: phonecode [dictionary_file] [phone_numbers_file]")
        quit(1)
```

## 11.6 Leaving the shell out: `run` and `runLines`

Every form so far builds a command line and hands it to `/bin/sh`, so the
shell parses it and quoting is the caller's problem. `{!x}` and `{*xs}` solve
that — but only when remembered, and the default is still wrong.

`run` takes an argument list instead. There is nothing to quote, because
nothing parses the arguments a second time:

```python
let r4: RunResult = run(["git", "commit", "-m", msg])
print(r4.output, r4.code)
let names: []str = runLines(["ls", dir])
```

The difference shows on a value that is also shell syntax:

```python
let nasty: str = "; rm -rf ~"
run(["ls", nasty])        # ls complains about a file with that name
shell: ls {nasty}         # the shell runs it
shell: ls {!nasty}        # safe — if you remembered the !
```

`run` returns the same record as `shell` — `.output`, `.stderr`, `.code` —
spelled `RunResult` where a binding needs an annotation. `runLines` returns
`[]str`. Both take the same options, as keyword arguments:

```python
let r5: RunResult = run(["make", "-j4"], cwd = src, env = e,
                        stdin = text, timeout = 30000, check = true)
```

A program that is not there reports 127 and a timeout 124, exactly as a
shell and `timeout(1)` do, so the two families agree on what failure looks
like.

## 11.7 Reading output as it arrives: `shellIter`

The capturing forms wait for the command to finish. A long-running or
endless one wants to be read while it runs:

```python
for line in shellIter: tail -f build.log
    print(line)
```

Only stdout is streamed. `cwd`, `env` and `pipefail` apply, and `check`
raises when the command ends badly — once the stream is over, since that is
when the status exists:

```python
for line in shellIter(check = true): make -j4
    print(line)
# raises here if make failed
```

`check` applies to a loop that ran to completion. Breaking out early leaves
the command unfinished, and an unfinished command has no status to object
to, so a `break` never raises.

## 11.8 Running commands alongside each other: `shellSpawn`

Every form so far waits, so N commands take the sum of their times.
`shellSpawn` starts one and carries on, handing back a `Job`:

```python
var jobs: []Job = []
for host in hosts:
    let j: Job = shellSpawn: ping -c1 {!host}
    jobs.append(j)

let results: []RunResult = waitAll(jobs)
for r6 in results:
    print(r6.code)
```

Those pings happen at the same time, so the loop takes about as long as the
slowest rather than the sum. A single job is waited on directly, and the
handle answers a few other questions:

```python
let j2: Job = shellSpawn: make -j8
while j2.running():            # never blocks
    print("still building")
let r7: RunResult = j2.wait()  # blocks
let r8 = j2.wait(check = true) # raises if it failed
j2.kill()                      # SIGTERM, reported as 143
```

`wait` is safe to call twice: the result is kept once the child is reaped.

**Use `waitAll` for more than one job.** This is not a convenience wrapper
around a loop of `wait()`. The output goes into a pipe, and a pipe holds only
so much — 64K on Linux. A job that produces more stops when it fills and
resumes when something drains it, so waiting for jobs one at a time quietly
serialises them again, in exactly the case the form exists for. `waitAll`
drains every job as it goes.

## 11.9 Handing the process over: `shellExec`

A wrapper script's last act is usually to run the real command and pass its
exit status on. `shellExec:` replaces the running process instead — it does
not return, and the command's own status becomes the script's:

```python
shellExec: git {*args}          # this script *becomes* git
```

One less process in the tree, the status is right by construction rather
than by copying, and signals reach the real command instead of arriving at a
wrapper that has to decide what to do about them. It is what `exec git "$@"`
is for in Bash, and what most wrapper scripts should end in.

Compare with the capturing form, which does return:

```python
let code2: int = shell: git {*args}
quit(code2)                     # forwarding the status by hand
```

`EXAMPLES/git1.ady` ends in `shellExec:` for exactly this reason; §13.7
walks through the change.

## 11.10 Case study: a five-minute wrapper — `sv.ady`

`EXAMPLES/INTERACTIVE/sv.ady` is fifteen lines of glue around three internal
tools, and it is worth quoting whole because this is the *most common kind of
program in the world* — the workflow wrapper:

```python
#!/usr/bin/env py2nim
# set view TAKES AN OPTIONAL BASELINE AS A PARAMETER !!!
let pattern : str =$1
let baseline : str =$2
let (view,_,_) = shell: choose_view_sorted {pattern}
if view:
  if $USER == $LOGNAME:
    if baseline: # WHAT IF ELD view ????
      shell: Csetup -e G!31.IP.L8 -b TACT.TACT_CONFIG.28.1.0.{baseline} {view}
    else:
      shell: Csetup -e G!31.IP.L8 {view}
  else:
    shell: Ccontext -e G!31.IP.L8 -b TACT.TACT_CONFIG.{view}
else:
  print "No view chosen"
```

Everything Bash would give you is here — `$1`, `$USER`, command capture,
interpolation — but with `let` bindings and a real `if` instead of `[ -n
"$view" ]`.

Written today it would end in `shellExec:` rather than a `shell:` per branch,
since nothing follows the command it chose to run.

## 11.11 Case study: an interactive file browser — `fsel.ady`

`EXAMPLES/INTERACTIVE/fsel.ady` drives `fzf` in a loop to browse and open
files. It composes almost every feature of this chapter:

```python
let editor: str = $EDITOR if $EDITOR else "nano"

if $# > 0:
    setCurrentDir($1)

while True:
    let cwd: str = getCurrentDir()
    let listing = shellLines: find {cwd} -maxdepth 1 -mindepth 1 -printf '%P\n' | sort
    var entries: str = ""
    for item in listing:
        if -d (f"{cwd}/{item}"):
            entries += BOLD_BLUE + item + "/" + RESET + TAB + item + NL
        else:
            entries += item + TAB + item + NL

    writeFile(tmpfile, entries)
    let (selection, sel_code) = shell: fzf --ansi --prompt="{prompt}" < {tmpfile}

    if sel_code != 0 or len(selection) == 0:
        quit(0)
    match sel:
        case "/" | "..":
            setCurrentDir(sel)
        case _ if -d (f"{cwd}/{sel}"):
            setCurrentDir(sel)
        case _ if key == "right" and -x (f"{cwd}/{sel}"):
            shell: {cwd}/{sel}
            quit(0)
        case _:
            shell: {editor} {cwd}/{sel}
            quit(0)
```

Pipes inside the command body (`find ... | sort`), exit-code checks,
environment fallbacks, and pattern matching with file-test guards — compiled
to a native binary by the Nim backend, so the browser starts instantly.

The two `shell:` / `quit(0)` pairs at the end are what `shellExec:` (§11.9)
was added for: the browser has decided what to run and has nothing left to
do, so it can become that command rather than supervise it and forward its
status.

## 11.12 Case study: parsing other tools' output — `lv.ady` and `show_status.ady`

`lv.ady` (§9.3) captures `shellLines: Clsview -u $USER`, splits fields,
reads per-view README files with `-e`/`-f` tests and `shell: head -1
{comment_path}`, then sorts and colour-codes the result. `show_status.ady`
polls a status command every minute and diffs the completed-test set:

```python
completedTests: {}str  ## All completed tests (persistent)

while True:
    time.sleep(60)
    for test in parseCompletedTests(getTestStatusLines()):
        completedTests.add(test)
```

The pattern to internalise: **`shellLines` at the boundary, typed data
structures inside.** Text comes in from the legacy tool, is parsed once into
enums/records/sets, and everything downstream is type-checked.

A tool that is slow to finish but prompt to print wants `shellIter` at that
boundary instead, so the first lines are parsed while the rest are still
arriving.

## 11.13 Multi-line and interactive blocks

`shell:` with an indented block joins plain commands with `&&`, so it stops
at the first failure:

```python
shell:
    echo hello
    echo world
```

`join` picks something else — `"&&"` (the default), `";"`, `"|"` or `"||"`,
as literals, since the lines are joined at transpile time:

```python
shell(join = ";"):                # run them all regardless
    make clean
    rm -rf tmp
    echo done

let top = shell(join = "|"):      # one pipeline
    sort access.log
    uniq -c
    head -1
```

If the block contains `send(...)`/`expect(...)`, the first line is spawned
under a **PTY** and the rest drives it — a built-in `expect(1)`. From
`EXAMPLES/test_shell_block.ady`:

```python
shell:
    bc -q
    send("2 + 2\n")
    expect("4")
    send("10 * 5\n")
    expect("50")
    send("quit\n")
```

For finer control — capturing what matched, multiple concurrent spawns —
use the bundled library directly (`EXAMPLES/test_expect.ady`):

```python
nimport expect

var s: Spawn = spawn("bc")
s.expect("\\$|>|bc")   # wait for the prompt
s.send("2 + 2\n")
s.expect("4")
print("2 + 2 = " & s.match)
s.send("quit\n")
s.close()
```

## 11.14 Translation summary

| Adascript | Python 3 | Nim |
|-----------|----------|-----|
| `let r = shell: cmd` | `subprocess.run(…, capture_output=True, text=True)` | `adascriptRun("cmd")` |
| `let ls = shellLines: cmd` | `…stdout.splitlines()` | `adascriptShellLines(adascriptRun(…).output)` |
| `let code: int = shell: cmd` | `subprocess.call(…)` | `execCmd("cmd")` |
| `shell: cmd` | `subprocess.run("cmd", shell=True)` | `discard execCmd("cmd")` |
| `for l in shellIter: cmd` | generator over `Popen.stdout` | `iterator` over `outputStream.readLine` |
| `let j: Job = shellSpawn: cmd` | `Popen` in a `_Job` wrapper | `AdascriptJob` around `startProcess` |
| `waitAll(jobs)` | a thread per job, each `communicate()` | one non-blocking pass over every job |
| `shellExec: cmd` | `os.execv` / `os.execve` | `execv` / `execve` |
| `run(argv)` | `subprocess.run(list)` — no shell | `startProcess(argv[0], args = …)` |
| `have("x")` | `shutil.which` | `findExe` |
| `{var}` in body | f-string interpolation | `fmt"""…"""` |
| `{!x}` / `{*xs}` | `shlex.quote` / joined | `quoteShell` / `mapIt(…).join(" ")` |
| `pipefail = true` | `executable="/bin/bash"` | `startProcess("/bin/bash", …)` |
| block with `send`/`expect` | PTY driver | bundled `expect` lib (`forkpty` + `select`) |

All required imports (`subprocess`, `osproc`, `strformat`, …) and runtime
helpers are inserted automatically, on first use only.

---

*Next: [Chapter 12 — Living on Two Backends](12-two-backends.md)*
