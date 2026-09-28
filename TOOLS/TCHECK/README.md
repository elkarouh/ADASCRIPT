# TCHECK — TACT Baseline Build Checker and Troubleshooter

Tools for buildmasters to check, troubleshoot, and compare TACT baseline builds.
Translated from ksh originals (`Tcheck_tact.ksh`, `hek-troubleshoot.sh`) to Adascript,
with new features added during the translation.

## Programs

### Tcheck_tact

Report the status of a baseline build: regression test results, replay status,
Padactl/CRC summary, and build closure.

Its source is split into modules, laid out as `EXAMPLES/PROJECT` is:
`Tcheck_tact.ady` (the options, the report, the main block) nimports, one
module per thing it reads:

| Module                | Holds                                                        |
|-----------------------|--------------------------------------------------------------|
| `LIBS/tcheck_common`  | named types, colored output, settings, the CM tree, build enums |
| `LIBS/tlog`           | a Tlog: its sections, the tests it reports newly failing     |
| `LIBS/replays`        | the replays: their types, their Treplay logs, their dirs     |
| `LIBS/baselines`      | a baseline and its builds, which read their Tlogs            |
| `LIBS/csystem_log`    | a baseline's Csystem_build.log, and comparing two            |
| `LIBS/changes_report` | who changed what, per the CFMUTEST changes report            |

`tcheck_common` is the leaf; `baselines` builds on `tlog` and `replays`,
and `csystem_log` and `changes_report` on `baselines`. Build it as before,
`ady2nim c Tcheck_tact.ady`. A nimport is Nim-only, so Tcheck_tact is a
Nim program.

Each module carries its own tests, under `if __name__ == "__main__"`: built
alone (`ady2nim c LIBS/tlog.ady && LIBS/tlog`) it runs them, and
`make test` does so for all six. They read real files from
`test/samples/`: a Tlog, two replay logs (trimmed to the lines that matter)
and a CFMUTEST changes report.

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
- `-focus changes alice`, or `-user alice`: only alice's changes -- her line
  of the summary, her branches, her files; the newly failed tests stay, the
  whole baseline's. A name nobody committed under says so, and who did.

**Build closure and test programs** (`-focus build_info`, and the full
report) are summed up from the IP build's `check_run_test_programs.log`,
linked above them, rather than printed: the log repeats the messages of
each sub-build that ran a check, and gives a ksh style difference in six
lines. Shown, each once: what `check_run_test_programs_log` says failed;
each ksh style difference with the previous baseline, its component and
check, with the `ediff-files` link that shows it and, when its two files
are there to read, the scripts whose findings are not the previous
baseline's, so as to know whose change it was, each script's path in bold
yellow to stand out from its findings:

```
  COMMON_CONFIG VAR_CHECK  #emacs:(ediff-files "..." "...")
    ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
    ./sources/regression_testing.ksh  new used not defined: CM_HOST PERL_VERSION; gone defined not used: OLD_WORK_DIR
```

The findings (`./<script>:XXX:<name>` under the heading of their kind) are
compared as sets, so a finding that only moved in the file is no change.

Under a script the baseline's CFMUTEST changes report names (the one
`-focus changes` lists), who broke it -- its findings are new -- or fixed
it -- they are gone -- or changed it, both: the report's
`TOOL/COMMON_CONFIG/sources/regression_testing.ksh` is COMMON_CONFIG's
`./sources/regression_testing.ksh`, and the change is credited to a branch
as `-focus changes` credits it. Under a script the report does not name,
nothing: its findings come from elsewhere than this baseline's changes.

```
    ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
      broken by carol.new_ops: 9abc0123 SC-2
    ./sources/make_dom_escinfra_per_file.ksh  gone defined not used: MODE
      fixed by arodrigu.fix_eld_op_reg: 7c4f6d8 SC-133596, reviewed by abernal on 260925.094727
```

Without a changes report, the line under the count of style differences
says why. In the comparison with the previous baseline's summary (below),
a script new there is said who broke it, and one gone from it who fixed
it -- a script gone since was fixed.
Then the other programs' SEVERE messages, how many and the first (`3 SEVERE from
param_shared_cleanup_ftok: dbspy -D ...`); docgen's errors, five of them
(all with `-v`); and the files missing.

Without `-short`, `-focus build_info` then diffs that summary with the
previous baseline's -- `+` a line only this baseline's has, `-` one only
the previous one's had. The ediff links are left out and the baseline
numbers masked, so that only a change in what fails shows; a script line
comes under its style difference, so as to say which one it is. The log
read is a build's newest check_run_test_programs.log: a test's LOGS
directory may hold an older one of its own.

```
Compare the check_run_test_programs.log summary with 30.0.0.134's:
  #emacs:(progn(find-file ".../TACT_CONFIG.30.0.0.134/.../check_run_test_programs.log"))
  + 7 ksh style differences with the previous baseline:
  +   TACT_CONFIG VAR_CHECK
  +     ./sources/find_current_ops.ksh  new used not defined: CFMU_REGRESS_TEST_FTPS_DIR
  +       broken by carol.new_ops: 9abc0123 SC-2
    COMMON_CONFIG VAR_CHECK
  +     ./sources/regression_testing.ksh  new used not defined: CM_HOST
  - 6 ksh style differences with the previous baseline:
    DOM STABLE_CHECKS
  -     ./sources/make_dom_escinfra_per_file.ksh  new defined not used: MODE
  -       fixed by arodrigu.fix_eld_op_reg: 7c4f6d8 SC-133596
  -   1 SEVERE from old_program: something fixed since
```

and prints the command comparing the two baselines' Csystem_build.log,
normalized, in the diff tool (`meld` unless `-tool` names another) rather
than opening it: the two differ in too much for that to be worth doing
every time. It says which Csystem_build.log is missing, if one is.

It reads a build's logs in the build of the type it wants, whichever of
`$CM_ENV_ID`'s it was launched with -- `G!31.IP.L8` or `G!31.OP.L8`: a
replay's are always the OP build's, a Csystem log the IP build's, mono
results IP and assert results OP.

When the build or the Tlog asked for is not there, Tcheck_tact says so and
where it looked: `No OP build in <baseline dir>` with the builds it has and
those it sets aside (the 92, 94, 95, 98 and 30 variants), or `"OP in" build
not ready yet` with the Tlog it looked for -- also for a subtype a build
type is not expected to have, when -focus asks for it. The same for a
replay: `WARNING: no performance replay log in <baseline dir>`, with where
it looked (build_*OP*/saved_logs/Treplay_*.log) and the replays the
baseline has; and, for its details, `no performance replay dir: no
<saved_logs>/replay_dir*TAC_LO3*/work/logging/LOGS, nor in the baselines
before, back to <nr>`.

Each focus shows its overview first, then the details -- the detailed test
comparison, the replay diffs, the build logs side by side, each file's
changes. `-short` leaves the details out: `-focus changes -short` is just
the files per committer by type.

**A failed replay** is shown with what happened in it, counted rather than
listed -- a prequal replay's check_logs report was 6 MB:

- from its Treplay log: what `replay_day` returned, how many of the
  replays finished, a prequal replay's successful and failing runs and what
  `Tprequal_analyzer` said went wrong comparing with the reference;
- from the check_logs report, which fails the replay -- the one the log
  names, where it is now (the replay directory is moved to `saved_logs/`
  once the replay is over), or else the newest in the replay directory's
  logs: the replay script calls TACOT could not evaluate, by call and
  exception, with where the first was; the tests that failed; the error
  reports by severity and message. Each is counted once, though check_logs
  quotes one again from a core's .logs, and TACOT reports a failed call
  twice;
- when the report is not at hand, `replay_day`'s own count of the SEVERE
  error reports, from the log;
- the cores dumped, from the log and the report: which process dumped each,
  and the command that opens gdb on it where it is now -- where it was
  dumped, or in the replay's logs, where tacot moves one it did not expect
  -- as a command and as an `#emacs:` link, the two places the replay's own
  gdb link looks. The cores themselves, one "dumped core file to" line
  each: not `NR_COREDUMPS`, which counts every line about a core ("A core
  dump not created ...", 2699 times in one replay for one core).

Five of each kind, the most frequent; twenty with `-v`. `-focus replay`
without `-short` shows twenty, for this baseline and the one before, and
compares the two summaries.

```
"run_prequal"  replay ==> FAILED
Look for details in:
#emacs:(progn(find-file ".../Treplay_G!31.OP.L8_30.0.0.133_...-run_prequal.NJrqM.log"))
    replay_day returned 1
    prequal runs: 1 successful, 0 failing
    prequal analyzer: No prequal summary found for baseline/reference
    check_logs reported errors:
    #emacs:(progn(find-file ".../replay_dir-run_prequal.JpAfK/work/logging/LOGS/260925.134324.dhdevd28.check_logs.result.svlog"))
    997 replayed calls failed, 2 tests failed, 2 SEVERE and 228 WARNING error reports
       977  IFPS_CORBA_SERVICES.PROCESS_FLIGHT raised BUFFER.MARK_MISMATCH_ERROR : buffer.adb:266, first at 20251129.09.el:50622
        18  IFPS_CORBA_SERVICES.TRANSMIT_FPD raised TACOT.READ_UTILITIES.ARGS_ERROR : ..., first at 20251130.11.el:91904
         2  IFPS_CORBA_SERVICES.TRANSMIT_EFPM raised TACOT.READ_UTILITIES.ARGS_ERROR : ..., first at 20251201.10.el:376795
            tests failed: receive_an1.el ok:9 nok:442, receive_an3.el ok:8 nok:442
         2  SEVERE   TEST failure, locate this error in *error_logs.log ..., first at 25/12/03 00:05:00
       227  WARNING  FPD_Id_From_Access_Keys cannot determine FPD_ID, first at 25/11/30 09:59:53
         1  WARNING  Not all count periods covered, first at 25/12/01 14:20:37
    1 core dumped:
      core.5742.26_09_24-06:46:51.97, by tacot1 (pid 5742)
        lgdb --fullname -analyze_core .../UIF!30.0.0.131/build_G!31.OP.L8/ada/exe/tact_uif_shared_exe .../replay_dir-run_prequal.JpAfK/work/logging/LOGS/core.5742.26_09_24-06:46:51.97
        #emacs:(progn(gud-gdb "lgdb --fullname -analyze_core .../tact_uif_shared_exe .../core.5742.26_09_24-06:46:51.97"))
```

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
```

A change no user branch is credited with -- only integration merges or
baseline syncs above it -- is not counted here; the detailed listing
lists it, under "Files with no branch merged above them".

Then the branches not built yet, if any -- no `build_*` under
`/cm/ot/TACT/TACT_CONFIG.<USER>.<BRANCH>`:

```
NO VIEW BUILD FOUND FOR THESE BRANCHES
  ehristea.flight_list_fix
```

Then the tests newly failing, as the Tlogs report them -- each Tlog's "New
tests failing" and "Crashed Tests", new against that Tlog's own reference
baseline (its "Actual reference baseline" line) -- each once, with the
build type and subtype(s) it fails in:

```
NEWLY FAILED TESTS vs 30.0.0.131
  test_alpha.el  IP in, IP mono
  test_gamma.el  IP in
  test_delta.el  OP assert
```

The previous baseline is not looked at here: comparing with it is for the
detailed views, where the causes are looked for. Treport.ksh shows the same.

Then, unless `-short`, each branch: its view build
(`/cm/ot/TACT/TACT_CONFIG.<USER>.<BRANCH>/build_*`, e.g. `build_default_Linux`),
the previous TACT baseline's build (the one its test reports are named
after: `…30.0.0.131-G!31.IP.L8-<host>-<date>` for
`TACT_CONFIG.30.0.0.131/build_G!31.IP.L8`), and the branch's test reports
(`test_reports/TACT.TACT_CONFIG.<USER>.<BRANCH>-G!31.*`) next to that
baseline's, with the ediff between their failures -- each said to be
missing when it is; for each file, one entry
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

Without a workspace (`$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY` unset), the
links work in a cache instead, `$TCHECK_NM_CACHE` (default
`~/Downloads/.cache/tcheck/NM`): the first click clones the file's
repository from Bitbucket into it, without its files' contents, and every click fetches the
commits and tags compared when the cache lacks them -- it keeps up with
Bitbucket:

```
DIFF        : #emacs:(when (eql 0 (shell-command "Tcheckout -cache /home/me/Downloads/.cache/tcheck/NM -rev c3fb81031 -rev c3fb81031^ TACT/UIF/sources/b.adb")) (vc-version-ediff (list "/home/me/Downloads/.cache/tcheck/NM/TACT/UIF/sources/b.adb") "c3fb81031^" "c3fb81031"))
```

The path's `<system>/<subsystem>` is a submodule of the NM workspace
(`$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY`), where the commits are. Where it
is not checked out -- or is checked out sparsely, without that file -- the
links check the file out first, alone, with `Tcheckout`, and compare only
once that worked:

```
DIFF        : #emacs:(when (eql 0 (shell-command "Tcheckout -root /…/NM TACT/UIF/sources/b.adb")) (vc-version-ediff (list "/…/NM/TACT/UIF/sources/b.adb") "c3fb81031^" "c3fb81031"))
```

A submodule checked out already needs the commits and the baseline tags
fetched (`fetch --tags`); the list says so once, at its top.

A review is shown where the
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
| `-user NAME` | Only committer NAME's changes: the same as `-focus changes NAME` |
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
Treport.ksh [-no-color] [-tool NAME | -meld] [-batch] [-short] [-user NAME] BASELINE
Treport.ksh -tool kompare 30.0.0.132
```

It reads the same environment (`TCHECK_CM_OT`,
`CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY`, `TCHECK_NM_CACHE`) and needs `Psort`
on the PATH.
It runs under ksh93 and under zsh in ksh emulation (a `/bin/ksh` that is
zsh, or plain zsh, which it switches to ksh emulation), and prints its
colours with the original Tcheck_tact.ksh's `cecho`/`cechon`.
`make test` runs Tcheck_tact's changes tests (`test/run_changes_tests.sh`)
against it too, under both shells, so the two cannot drift apart; with the output identical,
a change to one is a change to both.

### Tcheckout

Checks out one file of an NM submodule that is not checked out, and only
that file -- what the list of changes' `DIFF` and `NET DIFF` links run
first, where the file's submodule is not checked out. `Tcheckout.ady` is
built to `Tcheckout`, the name the links run; `Tcheckout.ksh` is the same
program in shell, for where the Adascript build is not at hand -- link it
as `Tcheckout` there. The two take the same options and print the same
messages, and `make test` runs `test/run_checkout_tests.sh` against both
(the Adascript one on both backends):

```
Tcheckout [-root DIR] <system>/<subsystem>/<path>
Tcheckout [-root DIR] -u <system>/<subsystem>/<path>
Tcheckout [-root DIR] -u -all [<system>/<subsystem>]
Tcheckout [-root DIR] -l [<system>/<subsystem>]
Tcheckout TACT/UIF/sources/b.adb
```

The workspace is `-root`, or `$CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY`. The
submodule is registered (`git submodule init`), cloned into the workspace's
`.git/modules/<name>` as `git submodule` would, but without its files'
contents (`--filter=blob:none`: git fetches a version only when a diff reads
it), then checked out at the commit the superproject records, sparsely: this
file alone. A submodule checked out sparsely gets the file added; one checked
out in full is never moved. `git submodule status`, `update` and `deinit`
treat the result as any other submodule. Needs git 2.25 or later.

`-u` takes a file out again. The last file of its submodule takes the
submodule out too (`git submodule deinit`), keeping its clone in
`.git/modules/<name>` for the next checkout (`rm -rf` it to free the space).
It refuses a file with changes of yours, and a submodule checked out in full.
`-u -all` takes out every file checked out -- all the workspace's, or one
submodule's -- but those with changes, which it names.
`-l` lists the files checked out, one `<system>/<subsystem>/<path>` a line --
what `-u` takes: all the workspace's, or one submodule's.

It clones from the submodule's URL. NM's `.gitmodules` gives most of them
relative to the workspace's own (`../tact.uif.git`): they resolve against the
URL the workspace was cloned from (`git -C $CMA_WORKSPACE_NM_REPOSITORY_DIRECTORY
remote get-url origin`) -- a workspace cloned from the mirror,
`https://mirror-cma.bitbucket.cfmu.corp.eurocontrol.int/scm/nm/nm`, clones
them from `.../scm/nm/tact.uif.git` there. The few given in full
(BROKER, NIP) come from `https://bitbucket.eurocontrol.int/scm/nm/`. Nothing
to set; to clone from another server, have git rewrite the URLs, once:

```
git config --global url.<the other server's prefix>.insteadOf https://bitbucket.eurocontrol.int/scm/nm/
```

A server that does not filter gives a full clone (git warns "filtering not
recognized by server"): slower, the same result.

`-cache DIR` is for no workspace at all -- the diff links of a report made
outside one:

```
Tcheckout [-cache DIR] [-rev REV]... <system>/<subsystem>/<path>
Tcheckout [-cache DIR] -u <system>/<subsystem>/<path>
Tcheckout [-cache DIR] -u -all [<system>/<subsystem>]
Tcheckout [-cache DIR] -l [<system>/<subsystem>]
```

The file's repository, `$TCHECK_NM_URL/<system>.<subsystem>.git` in lower
case (`TCHECK_NM_URL` defaults to
`https://mirror-cma.bitbucket.cfmu.corp.eurocontrol.int/scm/nm`), is cloned
alone into `DIR/<system>/<subsystem>`, as above, and the file checked out
at the first `REV` that has it. The `REV`s -- what the diff compares -- are
fetched when the clone lacks them. Without a workspace, `-cache` is the
default: `$TCHECK_NM_CACHE`, or `~/Downloads/.cache/tcheck/NM`.

`-l` and `-u` work on the cache too (`Tcheckout -l` outside a workspace
lists it); `-u` of a repository's last file removes the repository from the
cache. `make test` runs
`test/run_checkout_tests.sh`, against repositories it builds.

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

`make compile` (or `make test`) at the top of the repository builds them,
leaving `Tcheck_tact`, `make_comparable` and `Tcheckout` here; Tcheck_tact
runs `make_comparable` by name, and its diff links `Tcheckout`, so put this
directory on the PATH. By hand:

```bash
cd TOOLS/TCHECK
ady2nim c Tcheck_tact.ady
ady2nim c make_comparable.ady
ady2nim c Tcheckout.ady
```

## Origin

- `Tcheck_tact.ady` — translated from `Tcheck_tact.ksh` (TOOL/COMMON_UTILS)
- `hek-troubleshoot.sh`'s prev-vs-current comparisons are Tcheck_tact's
  `-focus` modes (`-focus IP in`, `-focus replay performance`,
  `-focus build_info`, ...); the separate Ttroubleshoot program is gone.
- `make_comparable.ady` — translated from `make_comparable.ksh`
- `Treport.ksh` — `list_changes` and `list_detailed_changes` of `Tcheck_tact.ady`, translated
  back to ksh
- `Tcheckout.ady` — translated from `Tcheckout.ksh`
