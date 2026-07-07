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

## 13.7 `dp/jacks.ady`, `td_learning/qlearning.ady`, `td_learning/sarsa.ady` — numeric kernels

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

## 13.8 `geo_server.ady` — 1990s prototyping experiment, revisited (~450 lines)

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

## 13.9 The `CFMU/` and `TIMETABLE/` directories — Adascript at work

Finally, two directories of *production-shaped* code: `CFMU/` contains a
family of FTPS transfer tools (`ftps_get`, `ftps_put`, `ftps_list`,
`ftps_rename`, a status monitor, recovery scripts) sharing a common module
`ftps_common.ady`; `TIMETABLE/` mixes `.ady` solvers (`timetable_engine`,
`timetable_backtrack`, `timetable_sa` at the EXAMPLES root) with a Python
web server and a JSX viewer. Neither is polished for teaching — which is
exactly why they are worth skimming: multi-file organisation, `nimport`ed
shared modules, and the boundary between Adascript and the surrounding
Python/JS world.

## 13.10 What the corpus says, in one paragraph

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
