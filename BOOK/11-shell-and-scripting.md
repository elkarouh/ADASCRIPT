# Chapter 11 — Shell Integration: Adascript as a Better Bash

Every scripting language eventually shells out; few make it pleasant.
Adascript makes subprocess execution, command-line arguments, environment
variables and file tests part of the *syntax*, so the scripts you would have
written in Bash gain types, data structures and two compilation targets —
without losing Bash's directness. The `EXAMPLES/INTERACTIVE/` directory is
this chapter's home turf.

## 11.1 `shell:` and `shellLines:`

```python
let result = shell: git status
print(result.output)   # stdout as a string
print(result.stderr)   # stderr as a string
print(result.code)     # exit code as int
```

Destructuring works — take just what you need:

```python
let (out, code) = shell: some-command
```

The slots are stdout, the exit code, then stderr:

```python
let (out, code, err) = shell: some-command
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

**Interpolation** uses `{name}` anywhere in the command body. Function calls
and other complex expressions also work inside `{}` — the transpiler
automatically hoists them to temp variables in the Nim output:

```python
let branch = "main"
let result = shell: git log --oneline {branch}

def Q(s: str) -> str:
    "'" + s.replace("'", "'\\''") + "'"

shell: mkdir -p -- {Q(os.path.join(d, "subdir"))}
```

Options control working directory and timeout:

```python
let r2 = shell(cwd = "/tmp", timeout = 3000): ls -la
```

## 11.2 Bash variables and file tests

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

## 11.3 Case study: a five-minute wrapper — `sv.ady`

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

## 11.4 Case study: an interactive file browser — `fsel.ady`

`EXAMPLES/INTERACTIVE/fsel.ady` drives `fzf` in a loop to browse and open
files. It composes almost every feature of this chapter:

```python
let editor: str = $EDITOR if $EDITOR else "nano"

if $# > 0:
    setCurrentDir($1)

while True:
    let cwd: str = getCurrentDir()
    let listing = shellLines: find {cwd} -maxdepth 1 -mindepth 1 -printf '%P\n' | sort
    var entries: str = ...
    for item in listing:
        if -d (f"{cwd}/{item}"):
            entries += BOLD_BLUE + item + "/" + RESET + TAB + item + NL
        else:
            entries += item + TAB + item + NL

    writeFile(tmpfile, entries)
    let (selection, sel_code) = shell: fzf --ansi ... --prompt="{prompt}" ... < {tmpfile}

    if sel_code != 0 or len(selection) == 0:
        quit(0)
    ...
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

## 11.5 Case study: parsing other tools' output — `lv.ady` and `show_status.ady`

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

## 11.6 Multi-line and interactive blocks

`shell:` with an indented block joins plain commands with `&&`:

```python
shell:
    echo hello
    echo world
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

## 11.7 Translation summary

| Adascript | Python 3 | Nim |
|-----------|----------|-----|
| `let r = shell: cmd` | `subprocess.run(…, capture_output=True, text=True)` | `execCmdEx("cmd")` |
| `let ls = shellLines: cmd` | `…stdout.splitlines()` | `execCmdEx(…)[0].splitLines()` |
| `let ls: []str = shellLines: cmd` | same (annotation stripped) | same (Nim infers type) |
| `ls = shellLines: cmd` | same (bare assignment) | same |
| `shell: cmd` | `subprocess.run("cmd", shell=True)` | `discard execCmd("cmd")` |
| `{var}` in body | f-string interpolation | `fmt"""…"""` |
| `{f(x)}` in body | f-string interpolation | hoisted to `let tmp = f(x)` |
| block with `send`/`expect` | PTY driver | bundled `expect` lib (`forkpty` + `select`) |

All required imports (`subprocess`, `osproc`, `strformat`, …) are inserted
automatically.

---

*Next: [Chapter 12 — Living on Two Backends](12-two-backends.md)*
