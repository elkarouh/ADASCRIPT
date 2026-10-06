# TDIFF — What Changed, Between Two Baselines, Workspaces or Revisions

Two programs, for two different jobs:

- **Tdiff** — the full tool: baselines by shorthand (`LATEST`, a bare
  integer, `X.Y.Z.N`), workspaces by name, and a browsable directory-tree
  diff (or just the changed file names/statuses/revisions).
- **Tdiff_lines** — the lean one: two explicit revisions of the NM
  superproject, the changed lines or commits, for `Tblame`.

## Tdiff

A port of `TOOL/COMMON_UTILS`'s `Tdiff.ksh` (in fact zsh, despite the
shebang). Differences between baselines, workspaces and release branches,
as a browsable directory-tree diff -- or just the changed names, statuses,
or revisions.

```
Tdiff [<option>...] [<descriptor>] [<descriptor>]
```

| Invocation | Compares |
|---|---|
| `Tdiff` | in a workspace: it against its release branch; in a build context: that baseline against the one before |
| `Tdiff <descriptor>` | a baseline against the one before it; a workspace against its release branch |
| `Tdiff <descriptor> <descriptor>` | the two descriptors' closures directly |

A `<descriptor>` is a **baseline** (`X` -> `CFMUTEST.CFMUTEST_CONFIG.30.0.0.X`;
`LATEST`/`LATEST_GOOD`, resolved; `29.0.0.X`; or a full
`SYSTEM.SUBSYSTEM.VERSION`) or a **workspace** (a bare name, taken as
`$USER.name`, or `user.name` directly).

**Options:**
| Option | Description |
|---|---|
| `-alternate DIR` | an NM repository alternate to clone from; else `$NM_REPOSITORY_ALTERNATE`. Required for anything but diffing your own workspace -- without it, every other case is far too slow against a shallow-cloned workspace |
| `-debug` | a readable summary of what was resolved, on stderr |
| `-directory DIR` / `-d DIR` | where the generated file trees go (default `/tmp`) |
| `-extcmd CMD` / `-x CMD` | run as `CMD <left> <right>`; default opens an Emacs directory ediff. `-x ''` prints the two directories instead, and leaves them on disk |
| `-head` / `-H` | only the diff of your own uncommitted changes (no descriptor, inside a workspace) |
| `-name` / `-n` | just the changed files, prefixed `SYSTEM.SUBSYSTEM/`; no file trees made |
| `-status` / `-s` | `-name`, with a status column (`M`/`D`/`A`/`R`/`C`/`?`) |
| `-revision` / `-r` | just the two revisions that would be compared, per submodule |
| `-help` | this |

### How it works

1. **Resolve each descriptor to a per-submodule revision.** A baseline,
   through `Psort`/`list_subsystems`: the tag each submodule in its closure
   has for that version. A workspace, as the *left* side: the merge-base of
   its own branch and the release branch it belongs to (so only its own
   commits show) -- preferring the `testadm` integration branch's
   merge-base when it is more recent. As the *right* side: the tip of
   `origin/workspace/<name, dashed, lower-cased>`.
2. **Which submodules changed**, and what: `git diff --name-status` (plus,
   diffing a workspace's own uncommitted changes, `git ls-files --others`).
   `-name`/`-status` stop here.
3. **Each side's changed files, sparse-checked-out alone**, into a scratch
   directory -- cloned `--shared` from the alternate (so this is a local,
   not a network, clone) and checked out `--detach`; the workspace's own
   uncommitted side instead symlinks the files in from the real checkout.
   The two trees are handed to `-extcmd`, or printed with `-extcmd ''`.

### Differences from `Tdiff.ksh`

- `Log`/`Abort` are zsh functions from a sourced library this program does
  not have; `warn`/`die` stand in. `Clsworkspace`, `Psort`,
  `list_subsystems`, `Cget_viewspace_name`, `list_cfmutest_subsystems` are
  real external programs either way, shelled out to exactly as `Tdiff.ksh`
  does (as `where_workspace` already is, in `Tblame.ady`).
- the zsh glob patterns that classify a baseline shorthand are approximated
  by regexes for realistic inputs, not matched byte-for-byte the same way.
- concurrency is flattened: every submodule's every side runs as one batch
  of jobs, `MAX_JOBS` at a time, rather than one job per submodule each
  backgrounding its own pair.
- `-debug` prints a readable summary, not a raw shell variable dump.
- `-source` is accepted and does nothing (there is nothing to source in a
  compiled program).

### Verified against the real thing

`-name`, `-status` and the sparse-checked-out tree content were compared,
byte-for-byte, against a real `Tdiff.ksh` run on a real NM alternate, over
a real baseline-to-baseline diff of 77 changed files across ~30
submodules: identical. Workspace-descriptor resolution (the merge-base and
integration-branch logic) could not be fixture-tested the same way -- no
stand-in for `Clsworkspace`'s exact output exists here -- but was read
line-for-line against `Tdiff.ksh`.

## Tdiff_lines

Lists what changed in the NM superproject between two revisions: the lines
(for Tblame), or the commits. Answers "who is responsible for what went in
with the last baseline?". No baseline-name or workspace-name resolution,
no directory-tree view -- just two explicit revisions, and the git-only
parts of the job above.

```
Tdiff_lines [-commits] [-root DIR] [REV1 [REV2]]
```

| Invocation | Compares |
|---|---|
| `Tdiff_lines` | `HEAD^` with the checkout: the previous workspace baseline and what is checked out now |
| `Tdiff_lines REV1` | REV1 with the checkout |
| `Tdiff_lines REV1 REV2` | REV1 with REV2 |

A revision is either a **superproject commit** (`HEAD^`, `HEAD~5`, a SHA),
where every commit is a workspace baseline (`Baseline workspace '...'`), or
an **NM baseline** such as `30.0.0.124`, which is a tag inside each
submodule rather than in the superproject.

**Options:**
| Option | Description |
|---|---|
| `-commits` | List commits instead of lines: hash, date, SC ticket, committer, submodule, summary |
| `-root DIR` | The superproject; defaults to `$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY` |

### Who wrote each changed line

```
Tdiff_lines | Tblame
```

By default Tdiff_lines prints each line the newer revision adds or changes
as `<file>:<line_no>:<text>`, Tblame's input, so Tblame answers with the
date, SC ticket and committer of each. Tblame blames the checkout, so
leave REV2 out for this -- Tdiff_lines warns when it is given. Against the
checkout, Tdiff_lines diffs the working tree, as Tblame blames it:
uncommitted lines are listed, and the line numbers are the ones Tblame
will look up.

Deleted lines are not listed: they are not in the newer revision to blame.
`-commits` names who deleted them.

### Which commits went in

```
$ Tdiff_lines -commits
6d2e0f1 2024.03.01 SC-4     Bob B   sysA/subA | SC-4 prepend
3b9c7aa 2024.02.01 SC-2(+1) Alice A sysA/subA | SC-2 SC-3 tweak
a41f0c2 2024.03.01 SC-5     Carol C sysB/subC | SC-5 drop l2
```

Newest first within each submodule, merges left out. The ticket column is
Tblame's `sc_hint`: the first SC ticket, and how many more there are.

### How it works

1. **Which commit a revision means in each submodule.** A superproject
   commit: one `git ls-tree`. The checkout, or an NM baseline: one
   `git rev-parse` per checked-out submodule, run in parallel.
2. **Which submodules changed.** Those whose commit differs. Only checked-out
   submodules can be looked into; a changed one that is not is named once
   on stderr.
3. **What changed in each.** One `git diff -U0` (or `git log`) per changed
   submodule, 16 at a time. The new line numbers come straight from the
   hunk headers.

On a workspace of 161 submodules, one workspace baseline typically changes
one or two, so a default run looks into one or two repositories.

**When something is missing, it says so and says what to try:** an NM
baseline no checked-out submodule has a tag for (`fetch --tags`), a
submodule commit that was never fetched (`fetch`).

## Testing

`TOOLS/TDIFF/test/run_tests.sh` builds an alternate with two submodules,
tagged `30.0.0.1`/`30.0.0.2` (one of them renaming a file between the
two), and stubs `Psort`/`list_subsystems`/`list_cfmutest_subsystems`/
`readlink` on PATH, so Tdiff's baseline resolution, `-name`/`-status`/
`-revision` and the sparse-checkout directory diff (including the rename)
run without the real NM site tools:

```bash
python3.12 TO_NIM/ady2nim.py c TOOLS/TDIFF/Tdiff.ady       # builds TOOLS/TDIFF/Tdiff
cd TOOLS/TDIFF/test && sh run_tests.sh ../Tdiff
```

`TOOLS/TDIFF/test/run_lines_tests.sh` builds a superproject with four
submodules, two workspace baselines and the NM baselines
`30.0.0.1`/`30.0.0.2` as tags in each submodule -- changes by three
people, one submodule not checked out, one unchanged -- and checks the
default, superproject-commit and baseline forms, `-commits`, uncommitted
work, `Tdiff_lines | Tblame`, an unknown baseline and an unfetched commit:

```bash
python3.12 TO_NIM/ady2nim.py c TOOLS/TDIFF/Tdiff_lines.ady  # builds TOOLS/TDIFF/Tdiff_lines
cd TOOLS/TDIFF/test && sh run_lines_tests.sh ../Tdiff_lines ../../TBLAME/Tblame
```
