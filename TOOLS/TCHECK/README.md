# TCHECK — TACT Baseline Build Checker and Troubleshooter

Tools for buildmasters to check, troubleshoot, and compare TACT baseline builds.
Translated from ksh originals (`Tcheck_tact.ksh`, `hek-troubleshoot.sh`) to Adascript,
with new features added during the translation.

## Programs

### Tcheck_tact

Report the status of a baseline build: regression test results, replay status,
Padactl/CRC summary, and build closure.

```
Tcheck_tact [-no-color] [-s] [-f] [-v] [-l] [-batch] [-only-new] [-exit-code]
            [-focus <domain> [<detail>]] <BASELINE>
```

**Modes:**
- No focus: full report (summary + tests + build info + replays + the
  files per committer by type)
- `-focus IP in`: only IP integration tests
- `-focus OP assert`: only OP assert tests
- `-focus replay run_prequal`: only the run_prequal replay
- `-focus build_info`: only Padactl and check_run_test_programs
- `-focus changes`: only the list of changes, by committer (below)

Each focus shows its overview first, then the details -- the detailed test
comparison, the replay diffs, the build logs side by side, each file's
changes. `-short` leaves the details out: `-focus changes -short` is just
the files per committer by type.

**The list of changes.** The CFMUTEST baseline built on the TACT baseline
(the `CFMUTEST_CONFIG!<nr>` line among the builds `Psort -b` lists) has a changes
report, `/cm/ot/CFMUTEST/baseline_reports/CFMUTEST.CFMUTEST_CONFIG.<nr>.changes_report`:
per component, the merges since the previous baseline and the files their
commits changed, added or removed.

```
===== Differences between TACT.UIF.30.0.0.129 and TACT.UIF.30.0.0.130
      Merge from <- 6627849d2 testadm.integration_30 RELATED_CHANGES="SC-133991 SC-134249 "
      Merge from <- a2721a86a acicek.transmit_esb RELATED_CHANGES="SC-133991 SC-134249 "
      changed 13e00da4a:TACT/UIF/sources/mono_process_display.adb RELATED_CHANGES="SC-134249 "
```

It is regrouped by committer. First, how many files each committed, the
most first, and how many of each type -- a file changed or re-added twice
is one file; the type is what follows the last dot of its name:

```
CHANGES BY COMMITTER
acicek       50 files: 23 adb, 21 ads, 2 idl, 1 el, 1 out, 1 ssm, 1 unfiltered
ehristea     27 files: 13 adb, 11 ads, 3 idl
bss           1 file : 1 (no extension)
(no branch)   1 file : 1 out
```

Then the tests newly failing -- new or crashed in one of the baseline's
builds, and not failing in the previous baseline's -- each once, with the
build type and subtype(s) it fails in:

```
NEWLY FAILED TESTS vs 30.0.0.131
  test_alpha  IP in, IP mono
  test_gamma  IP in
  test_delta  OP assert
```

Then, unless `-short`, each branch: its view build
(`TACT.TACT_CONFIG.<USER>.<BRANCH>-G!31.*`) next to the previous TACT
baseline's, with the ediff between their failures; for each file, one entry
with every commit that touched it, their SC tickets, their reviews, and
`#emacs:` links to its diffs, clickable in an Emacs buffer like the report's
other links:

```
FILE CHANGED: TACT/UIF/sources/query_mgr_task-direct_control_functions.adb
COMMITS     : c3fb81031
REVIEWED BY : dpt, gru, wao on 260922.151702
DIFF        : #emacs:(vc-version-ediff (list "/…/NM/TACT/UIF/sources/query_mgr_task-direct_control_functions.adb") "c3fb81031^" "c3fb81031")
```

`DIFF` is one link per commit, the file before and after it, side by side
in ediff. With more than one commit there is also `NET DIFF`, what the
component's baseline did to the file as a whole, between the tags of its
section's "Differences between" line -- everybody's commits, not only this
branch's:

```
NET DIFF    : #emacs:(vc-version-ediff (list "/…/NM/IFPS/CUA_IDL/sources/fpl-utilities.ads") "30.0.0.122" "30.0.0.123")
```

With `-tool NAME` (and not `-batch`) the same links open that diff tool
instead -- `meld`, `kompare`, `kdiff3`, anything `git difftool -t` knows --
started in the background so Emacs does not wait on it. `-tool kompare`:

```
DIFF        : #emacs:(call-process-shell-command "git -C /…/NM/IFPS/CUA_IDL difftool -y -t kompare 1bd19222^ 1bd19222 -- sources/fpl-utilities.ads" nil 0)
NET DIFF    : #emacs:(call-process-shell-command "git -C /…/NM/IFPS/CUA_IDL difftool -y -t kompare 30.0.0.122 30.0.0.123 -- sources/fpl-utilities.ads" nil 0)
```

With `$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY` unset, the links name the
variable instead, for Emacs to expand (`substitute-in-file-name`, or the
shell for the diff tool).

The path's `<system>/<subsystem>` is a submodule of the NM workspace
(`$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY`), where the commits are -- checked
out and fetched there, the links work. The list says so once, at
its top, with the commands: `submodule update --init` and `fetch --tags`. A review is shown where the
report records one: on the change's own line, or on the merge of the
change's own commit.
- A change is credited to a `<user>.<branch>` merged above it in its
  section; integration merges (`testadm`, any `...adm`) and baseline syncs
  (`CFMUTEST.CFMUTEST_CONFIG.<nr>`) are nobody's branch. Each branch's
  merge lists its tickets: the change goes to the one branch whose tickets
  cover all of the change's, else to the one that shares any, else -- none
  or several, `RELATED_CHANGES=" "` among them -- to the nearest branch.
  The report says no more than that about who made a change.
- Changes with only an integration merge above them are listed apart.

`TCHECK_CM_OT` stands in for `/cm/ot`, to run against a copy of the tree --
which is what `test/run_changes_tests.sh` does.

**Options:**
| Option | Description |
|---|---|
| `-no-color` | Plain output, without ANSI colours; colour is the default (`-c` is still accepted) |
| `-s` | Compute replay dir sizes (disk usage report) |
| `-f` | Fast mode: skip slow check_run_test_programs_log |
| `-v` | Verbose output |
| `-l` | List available builds and replays, then exit |
| `-batch` | Non-interactive: no diff tool and no emacs; the list of changes keeps its ediff links whatever `-tool` says |
| `-tool NAME` | The visual diff tool: `meld`, `kompare`, `kdiff3`, ... The list of changes' DIFF and NET DIFF links open it (`git difftool -y -t NAME`) rather than ediff, and troubleshoot mode compares with it -- `meld` when no `-tool` is given |
| `-meld` | Same as `-tool meld`; kept for older scripts |
| `-only-new` | Show only new failures and regressions |
| `-short` | With `-focus`, only the overview: no details (for changes, the files per committer by type) |
| `-exit-code` | Exit with non-zero status if new failures found |

**Examples:**
```bash
Tcheck_tact 30.0.0.128             # full report, coloured
Tcheck_tact -f -batch 30.0.0.128   # fast, non-interactive
Tcheck_tact -exit-code 30.0.0.128  # CI mode: exit 1 on new failures
Tcheck_tact -only-new 30.0.0.128   # show only regressions
Tcheck_tact -s                     # disk usage of replay dirs
Tcheck_tact -l 30.0.0.128          # list builds and replays
```

### Treport.ksh

Tcheck_tact's list of changes (`-focus changes [-short]`) as a standalone ksh93
script, for where the Adascript build is not at hand. Same output, same
attribution, same links, same options for it:

```
Treport.ksh [-no-color] [-tool NAME | -meld] [-batch] [-short] BASELINE
Treport.ksh -tool kompare 30.0.0.132
```

It reads the same environment (`TCHECK_CM_OT`,
`CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY`) and needs `Psort` on the PATH.
It runs under ksh93 and under zsh in ksh emulation (a `/bin/ksh` that is
zsh, or plain zsh, which it switches to ksh emulation), and prints its
colours with the original Tcheck_tact.ksh's `cecho`/`cechon`.
`make test` runs Tcheck_tact's changes tests (`test/run_changes_tests.sh`)
against it too, under both shells, so the two cannot drift apart; with the output identical,
a change to one is a change to both.

### make_comparable

Normalize a log file for side-by-side diffing. Replaces timestamps, PIDs,
hex addresses, baselines, machine names, and other volatile content with
fixed placeholders. Single-pass: reads once, applies ~35 regex substitutions
per line, writes once.

```
make_comparable <logfile> [<baseline>]
```

Replaces the original `make_comparable.ksh` which ran ~30 separate `sd`/`pysd`
commands (30 full file rewrites).

## Shared Types

All three programs share these Adascript types, designed for an eventual merge:

| Type | Description |
|---|---|
| `BuildSubtype` | `in_test, mono, assert_test, lo, hi, memcheck, with_secondary` |
| `BuildType` | `IP, OP, SIP` |
| `BuildPass` | `normal, mrun` |
| `ReplayType` | `run_prequal, performance, simca, full_simca, oldest_date, all_autolink` |
| `Build` | Named tuple: `(name: str, btype: BuildType)` |
| `Replay` | Named tuple: `(rtype: ReplayType, file: Path)` |
| `FocusDomain` | `no_focus, focus_IP, focus_OP, focus_SIP, focus_replay, focus_build_info, focus_changes` |
| `TlogResult` | Record with parsed test result lists (crashed, new_failing, still_fail, etc.) |

## Output Features

- **Summary dashboard**: one-screen overview of baseline health
- **New failures diff**: highlights tests that regressed vs previous baseline
- **History file**: appends one-line summaries to `~/.tcheck_history`
- **ANSI coloring**: spec strings like `sWr` (bold white on red) matching the ksh original
- **Emacs integration**: `#emacs:` links for opening test logs directly

## Dependencies

- `Psort` — CM tool for ordering build closures
- `make_executable_output_comparable` — normalizes log output for comparison
- `rg` (ripgrep) — fast version of grep, written in rust
- `sd` — fast version of sed, written in rust
- `pyrg` — Python regex wrapper for ripgrep patterns
- a visual diff tool (interactive mode only) — `meld` unless `-tool` names another


## Building

`make compile` (or `make test`) at the top of the repository builds both,
leaving `Tcheck_tact` and `make_comparable` here; Tcheck_tact runs
`make_comparable` by name, so put this directory on the PATH. By hand:

```bash
cd TOOLS/TCHECK
ady2nim c Tcheck_tact.ady
ady2nim c make_comparable.ady
```

## Origin

- `Tcheck_tact.ady` — translated from `Tcheck_tact.ksh` (TOOL/COMMON_UTILS)
- `hek-troubleshoot.sh`'s prev-vs-current comparisons are Tcheck_tact's
  `-focus` modes (`-focus IP in`, `-focus replay performance`,
  `-focus build_info`, ...); the separate Ttroubleshoot program is gone.
- `make_comparable.ady` — translated from `make_comparable.ksh`
- `Treport.ksh` — `list_changes` and `list_detailed_changes` of `Tcheck_tact.ady`, translated
  back to ksh
