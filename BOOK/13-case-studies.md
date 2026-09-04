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

## 13.7 `git1.ady` — Adascript vs. bash, side by side (~300 vs. ~250 lines)

Every other program in this chapter was written as Adascript from the start.
`git1.ady` is the opposite exercise: a translation of a **bash script**
(`git1.sh`, after kotodharma/single-file-git), which makes it the best place
to see what Adascript adds to shell scripting — and what it costs.

The tool gives each tracked file its own private git repo,
`.git1/.g1_<name>`, grouped under a single `.git1` container in the file's
directory.  `notes.txt` and `diary.txt` can sit side by side, each with
independent history, with no repo at the directory level.

### Structure: bash globals translate directly

The bash version uses three globals set by `split_target`:

```bash
G1_DIR= G1_BASE= G1_GITDIR=
split_target() {
    local t=${1%/}
    [ -n "$t" ] || die "empty file name"
    case $t in
        */*) G1_DIR=${t%/*}; G1_BASE=${t##*/} ;;
        *)   G1_DIR=.;       G1_BASE=$t ;;
    esac
    [ -n "$G1_BASE" ] || die "not a file name: '$1'"
    G1_GITDIR=$CONTAINER/$PREFIX$G1_BASE
}
```

The Adascript version mirrors this exactly — mutable globals, same names:

```python
var G1_DIR:    str = ""
var G1_BASE:   str = ""
var G1_GITDIR: str = ""

def split_target(target: str):
    var t: str = target.rstrip("/")
    if t'Length == 0:
        die("empty file name")
    let head: str = os.path.dirname(t)
    G1_BASE = os.path.basename(t)
    if G1_BASE'Length == 0:
        die(f"not a file name: '{target}'")
    G1_DIR = "." if head'Length == 0 else head
    G1_GITDIR = CONTAINER + "/" + PREFIX + G1_BASE
```

The type annotations on the globals and the `os.path` calls replace bash
parameter expansion (`${t%/*}`, `${t##*/}`).  The logic is the same.

### The `g()` function: bash's one-liner becomes Adascript's

In bash, running git against a file's repo is one function:

```bash
g() {
    ( cd -- "$G1_DIR" && GIT_DIR=$G1_GITDIR GIT_WORK_TREE=. git "$@" )
}
```

The Adascript version is the same idea — build a command string and run it
through the shell:

```python
def g(args: []str) -> int:
    var parts: []str = []
    for a in args:
        parts.append(Q(a))
    let cmd: str = " ".join(parts)
    sh_status(f"cd {Q(G1_DIR)} && GIT_DIR={Q(G1_GITDIR)} GIT_WORK_TREE=. git {cmd}")
```

The extra lines are quoting — bash's `"$@"` word-splits correctly by default;
Adascript must quote explicitly via `Q()` since arguments cross a shell
boundary.

### Subcommand dispatch

Bash dispatches with a `case` in `main()`:

```bash
case $first in
    init)          shift; cmd_init "$@"; return ;;
    ls)            shift; cmd_ls "$@"; return ;;
    rm)            shift; cmd_rm "$@"; return ;;
    help|-h|--help) cmd_help; return ;;
    --version)     printf '%s %s\n' "$PROG" "$VERSION"; return ;;
esac
```

Adascript uses `case/when` with identical structure — one inline statement
per branch:

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

### What maps 1:1

The shell half of Adascript covers most of what a bash script does:

| bash | Adascript | Notes |
|------|-----------|-------|
| `$0`, `$1`, `$@`, `$#` | `$0`, `$1`, `$@`, `$#` | Identical syntax |
| `${PAGER:-less}` | `$PAGER if $PAGER else "less"` | Same intent, explicit |
| `[ -f "$f" ]` | `-f f` | File-test operators |
| `[ -d "$d" ]` | `-d d` | |
| `$(cmd)` | `let r = shell: cmd` | Capture with `shell:` |
| `cmd \|\| die` | `shell: cmd` (exit code via `sh_status`) | |
| `for f in *.txt` | `let entries = shellLines: ls -1a ...` | Glob via shell |
| `cat <<EOF ... EOF` | `f"""..."""` | Triple-quoted f-string |

### What Adascript adds

**Shell interpolation with expressions.** Bash requires `"$G1_DIR/$G1_GITDIR"`;
Adascript allows function calls directly inside `shell:` interpolation:

```python
shell: mkdir -p -- {Q(os.path.join(G1_DIR, CONTAINER))}
shell: rm -rf -- {Q(os.path.join(G1_DIR, G1_GITDIR))}
```

The transpiler hoists complex `{expr}` interpolations to temp variables
automatically — so you write `{Q(os.path.join(...))}` and the generated Nim
pre-binds `let shArg0 = joinPath(...)` before the command.

**Compiled binary.** `git1.sh` starts a new bash process on every invocation;
`git1.ady` compiles to a native binary (~100 KB).  For a tool that runs
once per user action this rarely matters, but `git1 each` iterates over every
repo — a compiled loop with compiled string handling.

**Type annotations.** `args: []str`, `-> int`, `-> ?str` — a reader
knows what flows through each function without tracing the bash.

### What it costs, honestly

**Quoting.** Bash word-splits `"$@"` correctly by default.  Adascript shell
commands are strings, so every argument that might contain spaces or shell
metacharacters must go through `Q()`.  The `g()` function exists largely to
quote its arguments — `g(["commit", "-m", "hello world"])` must produce
`git 'commit' '-m' 'hello world'`, not `git commit -m hello world`.

**Shell plumbing helpers.** `sh()`, `sh_status()`, and `Q()` are 18 lines
that bash gives you for free.  Every Adascript shell script will need
something like them.

**No `exec`.** The bash version's pass-through path replaces its own process
with git (`exec` semantics via the final `g "$@"` in a subshell).  The
Adascript version runs git as a child and forwards the exit status — same
behaviour to the caller, one extra process for the lifetime of the command.
The forwarding is exact across the whole 0..255 range, including git's 128
for a bad ref: `quit(n)` compiles to C's `exit()` rather than Nim's `quit()`
whenever `n` is not a literal in 0..127, since Nim's own `quit` clamps at 127.

### The scoreboard

| Metric | `git1.sh` | `git1.ady` |
|--------|-----------|------------|
| Lines | 246 | 299 |
| Shell plumbing overhead | 0 | ~18 lines (`sh`, `sh_status`, `Q`) |
| Type declarations | 0 | 0 (globals, no records) |
| Runtime | bash interpreter | native binary (~100 KB) |
| Subcommands | 8 | 8 (+ `migrate`) |

The 53-line gap is mostly quoting helpers, type annotations, and the fact
that `os.path.join(a, b)` is more characters than `$a/$b`.  The structure
is otherwise 1:1 — someone who reads the bash can read the Adascript,
and vice versa.

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
