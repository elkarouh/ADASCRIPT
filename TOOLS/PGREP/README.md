# Pgrep — grep the sources of a build closure

`Pgrep.ady` searches the source files of a CM build: either the closure of a
system, a baseline ID or a project baseline ID, or the LATEST (or
LATEST_GOOD) build of every subsystem. Each subsystem is searched in a
process of its own and the results are printed in subsystem order, so the
wall time is the slowest subsystem's rather than the sum of all of them.

It is a translation of a ~480-line ksh script, and it is here as the worked
example of what that translation looks like: the option loop is a `case`
over the argument, the background `find`/`grep` per subsystem is
`shellSpawn` + `waitAll`, and the file list reaches `xargs` through
`stdin =` rather than a command line that a large subsystem would overflow.

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

## What it needs around it

The CM environment: `$CM_ROOT`, `$CM_ENV_ID`, `$CONTEXT_CM_BASELINE`, the
builds under `/cm/ot`, and the helpers `Psort`, `cc_pattern` and
`get_topmost_subsystems` on the PATH. Without them it prints its usage and
its diagnostics but finds nothing, which is why `make test` only checks that
it builds and that a no-argument run prints the usage.

## Where it differs from the ksh original

* The default filter skips project branch builds, which is what `-all` and
  the usage text describe. The shell version's perl filter *keeps* only the
  directories whose baseline matches `cc_pattern PROJECT_BASELINE_ID` — the
  line its own `#?? This is bizarre` comment is about.
* `. trace`, `. cm_audit_logger` and `. Caux_functions` are gone. None is
  ever called by name; what they install is a ksh environment, and none of
  it has a meaning in a compiled program.
* The per-subsystem results go through the `Job` each search returns rather
  than through a `mktemp -d` directory and a `cat *.out`, so there is no
  temporary directory to trap and clean up, and the order is the
  subsystems' rather than the shell glob's.
