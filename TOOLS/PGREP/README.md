# Pgrep — grep the sources of a build closure

`Pgrep.ady` searches the source files of a CM build: either the closure of a
system, a baseline ID or a project baseline ID, or the LATEST (or
LATEST_GOOD) build of every subsystem. Each subsystem is searched in a
process of its own and the results are printed in subsystem order, so the
wall time is the slowest subsystem's rather than the sum of all of them.

It is a translation of a ~480-line ksh script, and it is here as the worked
example of what that translation looks like: the option loop is a `case`
over the argument, and each subsystem's `find | sort | grep -Ei | xargs
grep` becomes one `shellSpawn`, with `waitAll` collecting them.

The pipeline is the shell's rather than this program's on purpose. Reading
the file list in to sort and filter it here reads better and costs twice
the wall time: nothing can grep until every `find` has finished, and a
`-ppat` compared in the program is a process per file rather than one
`grep` for the list.

Each pipeline writes to a file of its own, and the program waits for one
subsystem at a time, in order, printing each as it lands -- so results
start appearing while the rest are still being searched. The others carry
on meanwhile: they need nothing from this process until their turn, which
is what a file buys over a pipe that has to be drained while it is written.

Choosing the subsystems is two commands rather than two per subsystem: one
`readlink` resolves the whole list and one `perl` says which baselines
match, the line numbers giving the answer for each. The shell version runs
a `readlink` and a `perl` for every directory, which at a few hundred
subsystems is most of a second before the first file is looked at.

`-verbose` says where the time went, on stderr: how long it took to start
the searches, when each subsystem finished, and the total.

## Building

```bash
ady2nim c TOOLS/PGREP/Pgrep.ady        # transpile + compile (cached)
```

The shebang already carries `-d:release`. Put the resulting binary on your
PATH as `Pgrep`; the program reads its own name, so a copy called something
else prints that name in its messages and its usage.

## Using it

```
Pgrep -? | -help | -html
Pgrep [options] [--] <GREP_PARAMS | -no-grep>
```

| | |
|---|---|
| `-closure <SYSTEM \| BASELINE_ID \| PROJECT_BASELINE_ID>` | search the closure of that system or baseline |
| `-subsys <PATTERN>` | search the subsystems whose build directory matches |
| `-all` | include project branch builds (they are skipped by default) |
| `-latest_good` | the LATEST_GOOD builds rather than the LATEST ones |
| `-ada` | Ada files only (`*.ad?`) |
| `-fpat <PATTERN>` / `-ppat <PATTERN>` | filter by file name / by path |
| `-sort` | sort the files within each subsystem |
| `-basenames` | print `file:line:` rather than the whole path |
| `-no_colors` | no colour, whatever stdout is |
| `-verbose` | the subsystem header lines, and what the options resolved to |
| `-no-grep` | list the files instead of searching them |

Everything after the options — or after `--` — goes to grep untouched, so
`-w`, `-E`, `-c` and the rest are available:

```bash
Pgrep -closure IFPS -latest_good -ada remote
Pgrep -closure IFPS -fpat "*.ksh" -ppat "*queue*" length
Pgrep -closure IFPS -no-grep | wc -l
Pgrep -subsys eld -- -w queue
```

### What reaches grep, and what does not

Everything Pgrep does not recognise itself is passed on untouched, so `-w`,
`-c`, `-l`, `-i`, `-h`, `-E` and the rest all work. Five things to know:

* **Pgrep's options come first.** The first argument Pgrep does not
  recognise ends its own parsing: that one and everything after it is
  grep's. A Pgrep option written after the search pattern goes to grep.
* **The sixteen names Pgrep claims never reach grep** — `-?`, `-help`,
  `-ht`, `-html`, `-ada`, `-all`, `-latest_good`, `-no-grep`, `-basenames`,
  `-verbose`, `-no_colors`, `-sort`, `-closure`, `-fpat`, `-ppat`,
  `-subsys` and `--`. None of them is a grep option, which spells its long
  options with two dashes; `--help` does reach grep and prints grep's.
* **`--` is consumed rather than forwarded.** A pattern that starts with a
  dash goes through `-e`: `Pgrep -e -v`. Files cannot be passed at all —
  the list comes from `find` through `xargs`, and Pgrep ends the grep
  arguments with its own `--`.
* **`--color=never` loses.** On a terminal Pgrep appends `--color=always`
  after your arguments, and grep takes the last one. Use `-no_colors`.
* **grep's own complaints go to stderr**, one per subsystem, so a mistyped
  grep argument says so rather than searching nothing quietly. The exit
  status is grep's neither here nor in the ksh original: Pgrep exits 0
  whether or not anything matched.

## The test

`test/run_tests.sh` builds a CM tree of its own -- builds that live
elsewhere and are reached through `/cm/ot` names, a project branch beside
each ordinary build, a `cc_pattern` that answers with a perl regexp -- and
runs the built binary against it. `$PGREP_CM_OT` is what lets it: the
program lists its subsystems from there rather than from `/cm/ot`, so the
path that picks the subsystems and filters them can be exercised on a
machine that has no CM at all. `make test` runs it.

It is here because three bugs hid in that path in a row, and every one of
them came out as "no match", which is indistinguishable from a site with
nothing to search.

## The CM helpers are ksh functions

`cc_pattern`, `get_topmost_subsystems` and `Psort` are not programs. They
are ksh functions defined by `Caux_functions`, which the original
dot-sources at the top of the file -- `cc_pattern` in particular is written
in ksh, with an associative array and a `for ((;;)){ }` loop, and answers
with a perl regexp built from `Regexp::Common`, `(?^:…)` and all.

So Pgrep asks them where they live:

```sh
ksh -c '. Caux_functions; cc_pattern PROJECT_BASELINE_ID'
```

Run as plain commands they simply do not exist, and a command that does not
exist prints nothing -- which is exactly what a helper answering with an
empty string looks like. `cc_pattern` came back empty, every baseline was
tested against `^$`, and nothing matched. That was read once as "every
subsystem is a project branch" (so all 200 were searched) and once as "none
of them is an ordinary build" (so none were). It now says so instead: a
helper that answers nothing is named on stderr, and an empty pattern stops
the run rather than guessing.

Where the helpers really are programs, and there is no ksh, the direct call
is still the fallback.

## What it needs around it

The CM environment: `$CM_ROOT`, `$CM_ENV_ID`, `$CONTEXT_CM_BASELINE`, the
builds under `/cm/ot` (or `$PGREP_CM_OT`), and the helpers `Psort`,
`cc_pattern` and `get_topmost_subsystems` on the PATH, plus `perl` for the
baseline pattern. Without them it prints its usage and its diagnostics but
finds nothing.

## Where it differs from the ksh original

* The project-branch filter is the shell's, not the documentation's. A
  directory is kept when its baseline matches `cc_pattern
  PROJECT_BASELINE_ID`, which is what the perl line does; the name says
  project and what it selects is the opposite, and that is what the
  `#?? This is bizarre` comment beside it is about. Reading it as its name
  suggests searches every project branch as well — on one site, 200
  subsystems against the shell version's 165.
* That match is made by **perl**, as it is there. cc_pattern's patterns are
  perl regexps, `(?:…)` and `\d` and all, and `grep -E` is a different
  language: given one it warns and matches nothing, which reads as "every
  subsystem is a project branch" — a search of everything or of nothing,
  depending which way the answer is taken. With no perl on the PATH, Pgrep
  says so and searches them all, as `-all` does.
* `. trace`, `. cm_audit_logger` and `. Caux_functions` are gone. None is
  ever called by name; what they install is a ksh environment, and none of
  it has a meaning in a compiled program.
* The per-subsystem results go through the `Job` each search returns rather
  than through a `mktemp -d` directory and a `cat *.out`, so there is no
  temporary directory to trap and clean up, and the order is the
  subsystems' rather than the shell glob's.
