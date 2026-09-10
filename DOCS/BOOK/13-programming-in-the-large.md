# Chapter 13 — Programming in the Large: Modules, Projects, and Builds

Every chapter so far has shown one file. That is how most Adascript programs
start, and `EXAMPLES/` is full of single files that stayed useful at two
hundred lines. Past that, a program wants seams: a types module everything
agrees on, a domain model, an output layer, and one file at the top that is
the program itself.

This chapter is about that scale. It is a **Nim-backend chapter**: `nimport`
is the module mechanism, and the Nim backend is the one that resolves,
transpiles and links a dependency graph. Section 13.10 says exactly what the
Python backend does and does not do with a multi-module program.

The worked example is `EXAMPLES/PROJECT/`, a four-file program you can build
and run:

```bash
ady2nim c -r EXAMPLES/PROJECT/dispatch.ady
```

---

## 13.1 What a module is

A module is a `.ady` file. There is no manifest, no package file, no
`__init__`, and nothing to register — a file becomes a module the moment
another file nimports it:

```python
nimport geometry        # geometry.ady, beside the importing file
```

Two roles, one file format:

| Role | Shape | Top-level code |
|------|-------|----------------|
| **Program** (entry point) | has a `#!/usr/bin/env ady2nim` shebang, is the file you hand to `ady2nim` | this *is* the program |
| **Module** (library) | declarations only: types, procs, classes, constants | runs at import time — see 13.7 |

`EXAMPLES/PROJECT/` has one of the first and three of the second:

```
EXAMPLES/PROJECT/
    dispatch.ady          <- the program
    lib/geometry.ady      <- leaf module: Point_T, distance(), bearing()
    lib/fleet.ady         <- domain model: Vehicle_T, Depot
    lib/report.ady        <- formatting
    test_geometry.ady     <- a second entry point: the module's unit test
```

Nothing marks a module as a module, and nothing marks a declaration as
exported. When ady2nim transpiles a file *as a dependency* it emits every
top-level declaration with Nim's export marker, so `def distance(...)`
becomes `proc distance*(...)`. Exporting is the default, and the unit of
privacy is the module you choose not to import.

---

## 13.2 `nimport`: one keyword, three kinds of module

`nimport` is the same keyword you already met in Chapter 12 for Nim standard
library modules. It resolves three kinds of name, in this order of surprise:

```python
nimport strutils, math      # 1. Nim's own standard library
nimport stdlib, graphs      # 2. Adascript's bundled libraries (TO_NIM/STDLIB/)
nimport geometry            # 3. your own geometry.ady
```

The difference is only whether a `.ady` file with that name is found next to
your source. If one is, ady2nim transpiles it and compiles it into your
program; if not, the name is handed to Nim untouched. That is why
`nimport os` and `nimport lib/fleet` can sit in the same file without
ceremony.

Names arrive **unqualified**. After `nimport geometry`, `distance(a, b)` is
just in scope:

```python
nimport geometry

let km: float = distance(ORIGIN, here)          # no prefix needed
let m2: float = geometry.distance(ORIGIN, here) # also fine — same call
```

The qualified spelling is accepted and compiles to the identical Nim call, so
use it wherever it reads better. What you cannot do is rely on qualification
to keep two `distance` procs apart: see 13.9.

The selective form works too, and imports the whole module anyway (Nim has no
partial import of a module's symbols):

```python
from geometry nimport distance, Point_T   # pulls in geometry, all of it
```

Plain `import geometry` is **rejected** on the Nim backend — `import` is
reserved for Python modules (Chapter 12). The error message says so:

```
Error: 'import geometry' is not allowed. Use 'nimport geometry' for
Nim/stdlib modules or 'pyimport geometry' for Python packages.
```

---

## 13.3 How a module name is resolved

For each name it nimports, ady2nim looks for a `.ady` file in three places, in
order:

1. **the directory of the file doing the importing**
2. **that directory's parent**
3. **the build cache** (where the bundled `TO_NIM/STDLIB/*.ady` libraries are
   installed)

The first hit wins. If none matches, the name is left for Nim — which is what
makes `nimport strutils` work.

A name may carry a path, and the path is written with `/`:

```python
nimport lib/fleet          # <dir>/lib/fleet.ady, or <parent>/lib/fleet.ady
```

Two consequences worth internalising:

- **A sibling is imported by its bare name.** Inside `lib/fleet.ady`,
  `nimport geometry` finds `lib/geometry.ady` by rule 1.
- **The parent rule is what makes `bin/` + `lib/` layouts work.** From
  `bin/tool.ady`, `nimport lib/util` misses `bin/lib/util.ady` and then hits
  `<project>/lib/util.ady` by rule 2. `EXAMPLES/TIMETABLE/timetable_server.ady`
  lives on this rule: its `nimport timetable_engine` and `nimport timetable_sa`
  resolve to `EXAMPLES/timetable_engine.ady` and `EXAMPLES/timetable_sa.ady`,
  one directory up.

There is no `..` syntax: a module name starts with a letter, so
`nimport ../lib/util` is not a name ady2nim will resolve. The parent rule
covers the one level of escape you actually need.

---

## 13.4 Three layouts that work

### Flat

Everything in one directory, one file per concern, several entry points
sharing the modules. This is `EXAMPLES/CFMU/` — seventeen scripts over a
shared `ftps_common.ady`:

```
CFMU/
    ftps_common.ady     # constants, helpers, server lookup
    ftps_get.ady        # nimport ftps_common
    ftps_put.ady        # nimport ftps_common
    ...
```

```python
# ftps_get.ady
nimport ftps_common
import os

if $# < 3:
    print "Usage: ftps_get <dest_dir> <ftps_service> <decompress>"
    sys.exit(RC_ARG_ERROR)          # RC_ARG_ERROR came from ftps_common
```

Flat is right up to about a dozen modules, and it is the layout with the
fewest rules to remember: every name is a bare name.

### Entry point at the root, modules under `lib/`

This is `EXAMPLES/PROJECT/`, and the layout to reach for once the modules
have their own relationships:

```
PROJECT/
    dispatch.ady        # nimport lib/geometry, lib/fleet, lib/report
    lib/
        geometry.ady    # leaf: nimports nothing of its own
        fleet.ady       # nimport geometry   (sibling, bare name)
        report.ady      # nimport geometry   (sibling, bare name)
```

Note the asymmetry, and that it is not an accident: the program addresses
modules by their path from the project root (`lib/geometry`), while modules
address each other as siblings (`geometry`).

### `bin/` + `lib/`

Several programs, one library directory:

```
project/
    bin/
        dispatch.ady    # nimport lib/geometry
        report_only.ady # nimport lib/report
    lib/
        geometry.ady
        report.ady
```

The entry points sit one level below the root and still name modules by their
root-relative path, because rule 2 looks in the parent. Keep entry points at
the root or exactly one level below it and every path in the project is
written the same way.

---

## 13.5 What the build actually does

`ady2nim c -r EXAMPLES/PROJECT/dispatch.ady` prints its own story:

```
# transpiled → ~/.cache/hparsec/cache-DECF844B7E36524E/dispatch.nim
# transpiled dependency → ~/.cache/hparsec/cache-DECF844B7E36524E/lib/geometry.nim
# transpiled dependency → ~/.cache/hparsec/cache-DECF844B7E36524E/lib/fleet.nim
# transpiled dependency → ~/.cache/hparsec/cache-DECF844B7E36524E/lib/report.nim
# nim c --nimcache:… --out:…/.dispatch --path:…/cache-DECF844B7E36524E …/dispatch.nim
```

Step by step:

1. **Pre-pass.** Before anything is written, ady2nim walks the `nimport` graph
   breadth-first and parses each dependency to collect what the *importers*
   need to know about it: class names, constructor signatures, which classes
   are `ref`/virtual, proc return types, and the field order of records and
   named tuples (13.6).
2. **Transpile.** The entry point becomes `<stem>.nim` in a cache directory of
   its own; each dependency becomes `<name>.nim` beside it, with export
   markers, mirroring any subdirectory in its name.
3. **Compile.** One `nim c` invocation over the entry point, with
   `--path:<cache dir>` so `import lib/geometry` resolves inside the cache.
   Nim compiles the module graph — each module once, however many importers
   it has.
4. **Link and run,** and drop a symlink named after the source next to it, so
   `EXAMPLES/PROJECT/dispatch` runs the built binary.

The cache directory is keyed by a SHA-1 of the entry point's absolute path
*and* the backend, so `ady2nim c` and `ady2nim js` never hand each other the
wrong `.nim`, and two programs sharing a `lib/` get one cache each. Nothing is
ever written next to your source but the symlink.

Rebuilds are three mtime tiers, like make: re-transpile only if the `.ady`
(or the transpiler itself) is newer than the `.nim`; recompile only if any
`.nim` in the cache — dependency `.nim` files included, at any depth, the
bundled support files aside — is newer than the binary; otherwise exec the binary directly. Editing
`lib/geometry.ady` therefore rebuilds `dispatch`, and editing nothing costs
one `stat` per file.

`ady2nim -t` runs step 1 and 2 and stops. It is the build's first tier, not a
different translation: use it to read the generated Nim, and expect the same
`.nim` a later `ady2nim c` compiles.

---

## 13.6 What crosses a module boundary

The pre-pass exists because Adascript's output depends on knowledge the
declaring file has and the importing file would otherwise lack. What travels:

**Types.** Records, named tuples, enums, subranges and classes are ordinary
Nim types once exported.

```python
# lib/fleet.ady
type Vehicle_T is record:
    name:     str
    position: Point_T
    fuel:     float
```

**Field order, so positional construction works anywhere.** Adascript rewrites
`Vehicle_T("van-9", (x: 2.0, y: 2.0), 6.0)` into Nim's named form using the
declared order — and that order crosses the boundary with the type:

```python
# dispatch.ady — the type is declared in lib/fleet.ady
let spare: Vehicle_T = Vehicle_T("van-9", (x: 2.0, y: 2.0), 6.0)
```

**Constructors.** A class becomes a Nim `object` plus `newX`/`initX` procs, and
`Depot("Central", base)` in an importer is rewritten to `newDepot("Central",
base)` because the pre-pass saw the signature:

```python
# dispatch.ady
var d: Depot = Depot("Central", base)   # -> newDepot("Central", base)
d.add("truck-1", (x: 12.0, y: 5.0), 4.0)
```

**Inheritance across files.** A base class declared `@virtual` in one module
and subclassed in another still emits `ref object` on both sides, and a
subclass inherits the base's constructor parameters. `EXAMPLES/test_awk.ady`
is exactly this: its class subclasses `AwkBase` from the bundled `awk.ady`.

**Generics.** A generic proc or class instantiates per call site in the
importer, the same as within a file — `graphs.ady` defines `dijkstra[Node_T]`
once and every importer instantiates it for its own node type.

---

## 13.7 Modules run at import time

A module's top-level statements are its initialisation code, and Nim runs
them when the program starts, in dependency order:

```python
# lib/util.ady
print "util module init"        # runs before the program's own first line

def twice(n: int) -> int:
    return n * 2
```

```
$ ady2nim c -r bin/tool.ady
util module init
42
```

That is occasionally what you want — a lookup table computed once, a
connection opened — and it is a trap when it is not. Two habits keep it
boring:

- Modules declare; programs act. Constants and `let` bindings are fine at
  module top level; anything with an effect belongs in a proc the program
  calls.
- Never leave a smoke test at the bottom of a module. It will run in every
  program that imports it. Put it in its own entry point instead (13.11).

---

## 13.8 Keep the graph acyclic

Give the project a leaf: a module that imports nothing of the project and
holds the types everyone agrees on. In `PROJECT/` that is `lib/geometry.ady`,
and both `fleet` and `report` depend on it while neither depends on the other.

Nim tolerates some mutual imports — two modules whose procs call each other
across the cycle will usually compile — but a cycle that types participate in
does not resolve, and the failure surfaces as a Nim error in generated code
rather than as a message about your source. The fix is always the same: pull
the shared types down into a leaf module both sides import. Do it while the
cycle is still hypothetical.

---

## 13.9 Naming rules to respect

The module's **basename becomes a Nim module name**, and its exported symbols
land unqualified in every importer. Three rules follow:

1. **Basenames must be unique across the project.** Dependencies are
   transpiled into one cache directory keyed by the name you nimported them
   by, and each name is resolved once per build. Two different `util.ady`
   files in two directories, both imported as `util`, are one module as far as
   the build is concerned. If you want both, import at least one by path
   (`nimport lib/util`) — the path form keeps its own place in the cache — or,
   better, give them names that say what they are.
2. **Don't use a Nim keyword as a filename.** `mod.ady` fails with
   ``Error: invalid module name: `mod` `` — from Nim, about a file you did not
   write. `type`, `end`, `object`, `proc`, `block`, `ref` and friends are the
   same story.
3. **Exported names share one namespace.** Two modules exporting `format()`
   with the same signature is an ambiguity error at the call site. Nim's
   overloading absorbs a surprising amount of this — same name, different
   parameter types, no problem — but when two procs really do the same thing
   for the same types, rename one.

---

## 13.10 The Python backend has no module system

`nimport` is Nim-only by design: the Python backend comments the line out.

```python
nimport geometry
print dist(ORIGIN, p)
```

```python
# Python output
# nimport geometry
print(dist(ORIGIN, p))          # NameError: dist is not defined
```

And `ady2py` translates exactly one file — it has no dependency resolution, it
writes `<name>_gen.py` next to the source, and type knowledge does not cross
files, so even after transpiling each module by hand a `Point_T` built in one
file and used in another comes out as a bare tuple. `from geometry import *`
is not a way around it either: it survives into the Nim output as invalid
Nim.

So the rule is blunt, and it is the reason this chapter privileges Nim:

> **A program split across modules is a Nim-backend program.** Code that must
> run on both backends stays in one file.

That is less restrictive than it sounds. The single-file programs in
`EXAMPLES/` — `lispy.ady`, `c500.ady`, `tsp.ady` — run on both backends
because they are single files; the multi-module projects (`CFMU/`,
`TIMETABLE/`, `JOINTJS_DEMO/`, `PROJECT/`) are Nim programs, and the Python
backend is where you check a *module's* semantics one file at a time.

---

## 13.11 Testing a project

There is no test runner, and none is needed: a test is an entry point that
imports the module under test and asserts.

```python
#!/usr/bin/env ady2nim
# EXAMPLES/PROJECT/test_geometry.ady
nimport lib/geometry

assert distance(ORIGIN, (x: 3.0, y: 4.0)) == 5.0
assert bearing(ORIGIN, (x: 0.0, y: 1.0)) == 0.0
assert bearing(ORIGIN, (x: 1.0, y: 0.0)) == 90.0
print "all geometry checks passed"
```

`EXAMPLES/PROJECT/dispatch.ady` ends the same way — it asserts on the result
and prints `all PROJECT checks passed`, which is what lets the repository's
`make test` run it as a self-checking example. The repository Makefile is
worth copying for your own project: it lists sources by path relative to a
single examples directory, builds each with `ady2nim c`, then runs the ones
that are self-contained.

```makefile
ADY2NIM := python3 /path/to/TO_NIM/ady2nim.py

TESTS := test_geometry.ady test_fleet.ady

test:
	@for t in $(TESTS); do \
	    printf '  %-30s' "$$t"; \
	    $(ADY2NIM) c -r $$t >/dev/null 2>&1 && echo OK || { echo FAIL; exit 1; }; \
	done
```

Two build knobs matter at this size:

- **`#ady2nim-args`** on the second line of an entry point sets that program's
  compiler options: `#ady2nim-args c -d:release` builds it optimised without a
  flag on every invocation.
- **`make clean`**, or `rm -rf ~/.cache/hparsec`, throws away every cache
  directory. You need it after upgrading Nim, and essentially never
  otherwise — the mtime tiers handle the rest.

---

## 13.12 A checklist

Splitting a program that outgrew one file:

- [ ] One entry point at the project root, or one level below it in `bin/`.
- [ ] A leaf module for the types everyone shares — no `nimport` of your own
      code in it.
- [ ] Modules under `lib/`, importing each other by bare name and imported by
      the program as `lib/<name>`.
- [ ] Unique basenames, none of them Nim keywords.
- [ ] No top-level statements in modules beyond constants and `let`.
- [ ] A `test_<module>.ady` entry point per module, each ending in an assert
      and a line saying it passed.
- [ ] `ady2nim c -r <entry>.ady` builds the whole graph; nothing else to
      configure.

---

*Next: [Chapter 14 — Case Studies: The Big Programs](14-case-studies.md)*
