# Chapter 13 — Case Studies: The Big Programs

The previous chapters quoted the examples feature by feature. This chapter
reverses the lens: each section takes one substantial program and asks what
the *whole* of it teaches about writing Adascript. Line counts are of the
`.ady` sources.

## 13.1 `tsp.ady` — an algorithm laboratory (~1,300 lines)

The travelling-salesman study, after Norvig's pytudes notebook, implements
**fourteen algorithms** in one file, from `nearest_tsp` (greedy, O(n²))
through 2-opt, Or-opt, Lin-Kernighan, simulated annealing and tabu search,
up to exact Held-Karp DP and brute-force enumeration. The header block is a
model of engineering documentation — it records measured quality rankings at
n=500 and validation against the exact optimum at n=10..15, including the
honest warning that tabu search's O(n²)-per-iteration inner loop makes it
"100–400× slower at n≥100" than annealing.

What it teaches:

- **Benchmark-driven development on two backends.** The same file times all
  algorithms; the Nim build (`-d:release`) is what makes n=500 experiments
  interactive.
- Tuples-as-tours, `[]Point` geometry, and heavy use of the iterator
  patterns from Chapter 6.
- Documentation culture: findings live next to the code that produced them.

## 13.2 `INTERACTIVE/lispy.ady` — a Scheme interpreter (~1,200 lines)

Norvig's `lis.py`, grown to cover `quasiquote`, `cond`, `let`, variadic
lambdas, `apply` and `map`. The language features it stresses:

- the flat **variant record** `Val_T` with a `Val_Kind_T` discriminant
  (§4.3) — the single type through which every interpreter value flows;
- **sequence patterns** to recognise special forms (§5.6) — the eval loop is
  essentially one big `case x.items:`;
- `# nimraw:` **forward declarations** for the mutually recursive
  eval/apply pair (§8.3);
- free functions taking `self: Val_T`, called method-style via UFCS —
  the trick that keeps a Nim-compatible design Pythonic to read.

If you want to internalise Adascript's pattern matching, reimplementing one
special form of lispy is the exercise.

## 13.3 `shortest_path.ady` + `test_shortest_path.ady` — a generic framework and its zoo

The framework file (Chapters 8–9) defines `Minimizer[S, D, C]` and
`Maximizer[S, D, R]` — Dijkstra/A* and best-first longest-path over a
user-supplied state space, both as generator methods with back-link path
reconstruction. The test file then instantiates them **eight ways**: two
textbook graphs, rod cutting, capital budgeting, knapsack, equipment
replacement, the Romania map with an A* heuristic, and more.

The lesson is architectural: the guiding comment at the top —

> ALL DYNAMIC PROGRAMMING PROBLEMS CAN BE TRANSFORMED INTO SHORTEST-PATH
> PROBLEMS UNDER THE CONDITION THAT for each decision there is only ONE next
> state.

— turns into a checklist per problem: choose `State_T` (a tuple), choose
`Decision_T` (an enum or tuple), write `get_next_decisions` (often a single
`case` decision table, §5.3) and `get_next_state` (often one line), and the
framework does the search. Each example is 30–60 lines. That density is the
whole argument for generic classes plus enums plus tuples.

`state_search.ady` and its test file replay the same design for
uninformed/blind search (FIFO/LIFO/priority fringes), if you want a second,
simpler read of the pattern.

## 13.4 `sudoku.ady` — functional style in an imperative language (~220 lines)

Norvig's constraint-propagation solver. Points of interest beyond the
collection idioms of Chapter 6:

- the board is a `{str}str` threaded *by value* through
  `assign`/`eliminate`/`search`, with `{:}` as the contradiction sentinel —
  a functional core with no classes at all;
- the unit/peer tables are built once at module top level, imperative-style;
- MRV search copies the board per branch — the `with own` RAII pattern
  (§12.4) exists precisely to keep those copies from outliving their branch.

## 13.5 `rsync_time_machine.ady` — a faithful port of a real tool (~800 lines)

A translation of basnijholt's `rsync-time-machine.py` (Time-Machine-style
incremental backups over rsync, with SSH support, marker files, lock
handling and expiration strategies). It is the best example of Adascript as
a *systems* language:

- `pyimport os/sys/time/signal` next to `nimport strutils, osproc, posix,
  times` (§12.1) — each backend using its native muscles;
- a named-tuple `SSH` record carrying connection context through every
  function;
- extensive `shell:` use where rsync itself is invoked.

Porting advice embedded in it: keep the original's function structure, type
the data at the boundaries first (`SSH`, backup-folder records), and let
`shell:` interpolation replace string-building.

## 13.6 `lolcate/lolcate.ady` — a small database tool (~400 lines)

A port of lolcate-rs: named file-index databases under
`~/.local/share/lolcate-ady/`, a line-based config format, and subcommands
(`create`, `update`, `query`, `ls`, `info`, `add-dir`, `add-ignore`). Reads
as the reference recipe for CLI tools: a `Config` record, `$@` subcommand
dispatch via `case`, `walkDir`-style scanning through `nimport os`, regex
queries from Chapter 7.

## 13.7 `git1.ady` — a single-file version-control tool (~400 lines)

Every other program in this chapter is an algorithm or a port of one.
`git1.ady` is the workflow tool: the kind of program that is usually written
as a shell script and then regretted. It is the best place in the book to see
what the shell half of Adascript is for.

The tool gives each tracked file its own private git repo,
`.git1/<name>`, grouped under a single `.git1` container in the file's
directory.  `notes.txt` and `diary.txt` can sit side by side, each with
independent history, with no repo at the directory level. (The concept comes
from kotodharma/single-file-git.)

### Structure: one record, not three globals

Every git call needs three things about the file it acts on, and they travel
together:

```python
type Target_T is tuple:
    dir:    str    # the directory holding the file; git runs here
    base:   str    # the file's own name
    gitdir: str    # its private repo, relative to dir

def split_target(target: str) -> Target_T:
    var t: str = target.rstrip("/")
    if t'Length == 0:
        die("empty file name")
    let head: str = os.path.dirname(t)
    let base: str = os.path.basename(t)
    if base'Length == 0:
        die(f"not a file name: '{target}'")
    (dir: "." if head'Length == 0 else head,
     base: base,
     gitdir: CONTAINER + "/" + base)
```

An earlier version of this file kept those three as module-level `var`s that
`split_target` assigned and every helper read. It worked, and it is what a
shell script has to do, having no records — but it meant `g(args)` did not
say which repo it acted on. It acted on whichever file was split last.

The version that returns a value is better in three specific ways, and each
one is worth more than the annotation it costs:

- `g(t, args)` names its target, so a caller that forgets to split cannot
  quietly operate on the previous file. For a version-control tool,
  committing to the wrong repo is the failure worth designing against.
- `cmd_mv` holds two targets at once. With globals it had to copy the old
  values into locals before `split_target(new)` overwrote them; with a record
  it simply has `ot` and `nt`.
- Assigning a module-level `var` inside a function is a local in Python and
  not in Nim, so the pattern needed a `global` declaration on one backend and
  not the other. A returned value has no such asymmetry.

### The `g()` function

Every git invocation goes through one helper:

```python
def g(t: Target_T, args: []str) -> int:
    let env: {str}str = {"GIT_DIR": t.gitdir, "GIT_WORK_TREE": "."}
    let code: int = shell(cwd = t.dir, env = env): git {*args}
    code
```

Three settings make a per-file repo work: run in the file's own directory,
name the private repo as `GIT_DIR` so git stops searching upward for a
`.git`, and declare that directory the work tree. The first is the `cwd`
option; the other two go through `env`, which is where a value crossing into
a child's environment belongs — spelling them as `GIT_DIR={!x}` inside the
command would work, but then the shell is parsing what the language can hand
over directly.

`{*args}` quotes each element and joins them, so
`g(t, ["commit", "-m", "hello world"])` reaches git as three arguments and
not four. The `int`-typed target is the form that keeps the terminal — git's
output, colours and pager reach the user — while still returning the status.

### The last git call is different: `g_exec()`

Most of the program's git calls have work waiting behind them — `cmd_ls`
reads the log it just asked for, `cmd_adopt` checks whether the reset
worked.  Those need `g()`.

One does not.  The last line of `main()` is the passthrough: whatever the
user typed after the file name is handed to git, and git1's only remaining
job is to copy git's exit code into its own.  It used to say so:

```python
quit(g(t, args))
```

That works, and it costs a process.  git1 forks git, blocks until it
finishes, reads a number, and exits with it — a parent standing around
holding a pid for the sole purpose of relaying a status.  `shellExec:`
removes the middle:

```python
def g_exec(t: Target_T, args: []str):
    let env: {str}str = {"GIT_DIR": t.gitdir, "GIT_WORK_TREE": "."}
    shellExec(cwd = t.dir, env = env): git {*args}
```

The statement does not return.  git1 *becomes* git: same pid, same terminal,
same place in whatever launched it.  The exit status is git's by
construction rather than by forwarding, and Ctrl-C reaches git directly
instead of arriving at a wrapper that then has to decide what to do about
it.  This is what bash's `exec git "$@"` is for, and what every wrapper
script written by someone who has been bitten ends in.

The rule for which to reach for is simply whether there is anything left to
do: `g()` when the program continues, `g_exec()` when it does not.

### Subcommand dispatch

`case`/`when`, one inline statement per branch:

```python
case argv[0]:
    when "init":
        if argv'Length < 2: die(f"usage: {PROG} init <file>")
        cmd_init(argv[1])
        return
    when "ls":       cmd_ls(argv[1:]); return
    when "rm":       cmd_rm(argv[1:]); return
    when "help" | "-h" | "--help": cmd_help(); return
    when "--version": print f"{PROG} {VERSION}"; return
    when others: pass
```

### Shell idioms, in Adascript

The shell half of Adascript covers most of what a shell script does:

| Shell | Adascript | Notes |
|------|-----------|-------|
| `$0`, `$1`, `$@`, `$#` | `$0`, `$1`, `$@`, `$#` | Identical syntax |
| `${PAGER:-less}` | `$PAGER if $PAGER else "less"` | Same intent, explicit |
| `[ -f "$f" ]` | `-f f` | File-test operators |
| `[ -d "$d" ]` | `-d d` | |
| `command -v tool` | `have("tool")` | Straight from PATH, no process |
| `$(cmd)` | `let r = shell: cmd` | Capture with `shell:` |
| `cmd \|\| die` | `let code: int = shell: cmd` | Exit code, terminal kept |
| `"$f"` (quoted expansion) | `{!f}` in a shell body | Quoted interpolation |
| `"$@"` | `{*args}` | Each element quoted |
| `exec cmd "$@"` | `shellExec: cmd {*args}` | Replaces the process |
| `for f in *.txt` | `let entries = shellLines: ls -1a ...` | Glob via shell |
| `cat <<EOF ... EOF` | `f"""..."""` | Triple-quoted f-string |

### What the language adds

**Interpolation with expressions.** A function call goes directly inside a
`shell:` body:

```python
shell: mkdir -p -- {!os.path.join(t.dir, CONTAINER)}
shell: rm -rf -- {!os.path.join(t.dir, t.gitdir)}
```

The transpiler hoists complex `{expr}` interpolations to temp variables
automatically — you write `{!os.path.join(...)}` and the generated Nim
pre-binds `let shArg0 = joinPath(...)` before the command.  The `!` asks for
the value to be quoted as one argument, which is what a path assembled at run
time needs; an earlier draft of this file carried a hand-written `Q()` quoter
for the job, which is exactly what the sigil replaced.

**Compiled binary.** A shell script starts a new interpreter on every
invocation; `git1.ady` compiles to a native binary (~100 KB).  For a tool
that runs once per user action this rarely matters, but `git1 each` iterates
over every repo — a compiled loop with compiled string handling.

**Type annotations.** `args: []str`, `-> int`, `-> Target_T` — a reader knows
what flows through each function without tracing it.

### What it costs, honestly

**Quoting.** A shell word-splits `"$@"` correctly by default. Adascript shell
commands are strings, so a value that might contain spaces or metacharacters
has to be quoted where it is interpolated — `{!f}` for one value, `{*args}`
for a list. That is a character of syntax per site rather than a habit to
remember, which is the point. `run(["git", ...])`, which never builds a
command line at all, removes even that.

**Shell plumbing helpers — none, now.**  This section used to describe three
of them, eighteen lines: `sh_status()` existed because `shell:` could not
both keep the terminal and return an exit code, and `Q()` because
interpolation did not quote.  Both gaps are closed in the language, so the
example stopped needing the workarounds rather than documenting them.  That
is the healthier outcome, and the reason to write a tool like this in a new
language at all: what it cannot say comfortably is a bug report about the
language.

**`exec` — the last gap, now closed.**  This section used to say the
passthrough ran git as a child and forwarded the status: same behaviour to
the caller, one extra process for the command's lifetime.  `shellExec:`
closed that too, and `g_exec()` above is where it went, so the passthrough
now costs no process at all and the status is git's by construction rather
than by copying.

The forwarding machinery is still there for the calls that do return —
`quit(n)` compiles to C's `exit()` rather than Nim's `quit()` whenever `n`
is not a literal in 0..127, since Nim's own `quit` clamps at 127, which
would have turned git's 128 for a bad ref into 127.  git1 no longer exercises
it, having stopped forwarding anything; a wrapper that still forwards does.

### The scoreboard

| Metric | `git1.ady` |
|--------|------------|
| Lines | ~400, of which 66 are docstrings |
| Shell plumbing overhead | 0 |
| Type declarations | 1 record (`Target_T`) |
| Runtime | native binary (~100 KB) |
| Subcommands | 9 |

Nearly a quarter of the file is docstrings, and another 80 lines are `adopt`
and the helpers it needed. What is left is the tool.

### Replacing rather than merging

`adopt` is the one place where this tool takes a position of its own.
Branching a single file is cheap and useful — try a bolder draft, keep the
better one — but *merging* one file is a poor fit: a merge combines two
versions, and with no file boundary to separate the changes, two versions of
one file conflict readily. Edits one line apart already do.

So `git1 adopt <file> <branch>` moves the current branch onto the winner
wholesale, with `reset --hard`, and offers to delete the branches that
lost.  Nothing is combined, so nothing can conflict, and the losing
attempts stay reachable through the reflog.  It is a smaller operation
than merge, and for the workflow it serves — several attempts, one
survivor — it is the whole of what is wanted.

---

## 13.8 `dp/jacks.ady`, `td_learning/qlearning.ady`, `td_learning/sarsa.ady` — numeric kernels

Sutton & Barto's Jack's Car Rental (policy iteration) and Cliff Walking
(Q-learning vs SARSA). These show the numeric-modelling style:

- domain-constrained types doing real work — `type Prob_T is float range
  0.0..1.0`, `type Cars_T is 0..20`, `type Row_T is 1..4` — with Ada-style
  assignment checks catching modelling errors early (§2.4);
- memoisation with a tuple-keyed dict:
  `var poisson_cache: {(int, int)}float = {:}`;
- `Coord_T is (row: Row_T, col: Col_T)` as a grid state, action enums
  (`UP, RIGHT, DOWN, LEFT`), and reward tables indexed by them;
- the file headers state the algorithmic point being demonstrated (e.g. why
  Q-learning walks the cliff edge and SARSA stays a row above) — the
  examples are teaching documents, deliberately.

## 13.9 `geo_server.ady` — 1990s prototyping experiment, revisited (~450 lines)

The Yale/NSWC geo-server problem (which zones does each tracked object
occupy?) was a famous language-comparison exercise — Haskell's entry was
celebrated for defining regions as composable predicates. The Adascript
version makes the same move with operator overloading (§9.3): `Region`
subclasses (`Circle`, `Sector`, polygon corridors) plus `&`, `|`, `~` and
`in`, so an engageability annulus is

```python
~Circle(center, inner) & Circle(center, outer)
```

It is the clearest demonstration that the Python surface syntax buys real
expressive power for the compiled target.

## 13.10 The `CFMU/` and `TIMETABLE/` directories — Adascript at work

Finally, two directories of *production-shaped* code: `CFMU/` contains a
family of FTPS transfer tools (`ftps_get`, `ftps_put`, `ftps_list`,
`ftps_rename`, a status monitor, recovery scripts) sharing a common module
`ftps_common.ady`; `TIMETABLE/` mixes `.ady` solvers (`timetable_engine`,
`timetable_backtrack`, `timetable_sa` at the EXAMPLES root) with a Python
web server and a JSX viewer. Neither is polished for teaching — which is
exactly why they are worth skimming: multi-file organisation, `nimport`ed
shared modules, and the boundary between Adascript and the surrounding
Python/JS world.

## 13.11 What the corpus says, in one paragraph

Across all of these, the same shape recurs. **Types first**: a handful of
`type` declarations — enums, subranges, tuples, an alias or two — turn the
problem statement into vocabulary. **Tables as data**: enum-indexed arrays
and dict literals hold the problem instance. **Dispatch as tables**:
`case`/`when` decision logic that reads like the specification. **Small
functions with implicit returns** for the algebra, **a generator or a loop**
for the engine, and **`shell:`/`$1`/`-f`** at the edges where the program
meets the operating system. Learn that shape and you write Adascript the way
its author does.

---

*Next: [Appendix — Syntax Cheat Sheet and Toolchain](14-appendix.md)*
