# TDIFF — What Changed Between Two NM Revisions

## Tdiff

Lists what changed in the NM superproject between two revisions: the lines
(for Tblame), or the commits. Answers "who is responsible for what went in
with the last baseline?".

```
Tdiff [-commits] [-root DIR] [REV1 [REV2]]
```

| Invocation | Compares |
|---|---|
| `Tdiff` | `HEAD^` with the checkout: the previous workspace baseline and what is checked out now |
| `Tdiff REV1` | REV1 with the checkout |
| `Tdiff REV1 REV2` | REV1 with REV2 |

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
Tdiff | Tblame
```

By default Tdiff prints each line the newer revision adds or changes as
`<file>:<line_no>:<text>`, Tblame's input, so Tblame answers with the date,
SC ticket and committer of each. Tblame blames the checkout, so leave REV2
out for this -- Tdiff warns when it is given. Against the checkout, Tdiff
diffs the working tree, as Tblame blames it: uncommitted lines are listed,
and the line numbers are the ones Tblame will look up.

Deleted lines are not listed: they are not in the newer revision to blame.
`-commits` names who deleted them.

### Which commits went in

```
$ Tdiff -commits
6d2e0f1 2024.03.01 SC-4     Bob B   sysA/subA | SC-4 prepend
3b9c7aa 2024.02.01 SC-2(+1) Alice A sysA/subA | SC-2 SC-3 tweak
a41f0c2 2024.03.01 SC-5     Carol C sysB/subC | SC-5 drop l2
```

Newest first within each submodule, merges left out. The ticket column is
Tblame's `sc_hint`: the first SC ticket, and how many more there are.

## How it works

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

`test/run_tests.sh` builds a superproject with four submodules, two
workspace baselines and the NM baselines `30.0.0.1`/`30.0.0.2` as tags in
each submodule -- changes by three people, one submodule not checked out,
one unchanged -- and checks the default, superproject-commit and baseline
forms, `-commits`, uncommitted work, `Tdiff | Tblame`, an unknown baseline
and an unfetched commit.

```bash
python3.12 TO_NIM/ady2nim.py c TOOLS/TDIFF/Tdiff.ady    # builds TOOLS/TDIFF/Tdiff
cd TOOLS/TDIFF/test && sh run_tests.sh ../Tdiff ../../TBLAME/Tblame
```
