# TCHECK — TACT Baseline Build Checker and Troubleshooter

Tools for buildmasters to check, troubleshoot, and compare TACT baseline builds.
Translated from ksh originals (`Tcheck_tact.ksh`, `hek-troubleshoot.sh`) to Adascript,
with new features added during the translation.

## Programs

### Tcheck_tact

Report the status of a baseline build: regression test results, replay status,
Padactl/CRC summary, and build closure.

```
Tcheck_tact [-c] [-s] [-f] [-v] [-l] [-batch] [-only-new] [-exit-code]
            [-focus <domain> [<detail>]] <BASELINE>
```

**Modes:**
- No focus: full report (summary + tests + build info + replays)
- `-focus IP in`: only IP integration tests
- `-focus OP assert`: only OP assert tests
- `-focus replay run_prequal`: only the run_prequal replay
- `-focus build_info`: only Padactl and check_run_test_programs

**Options:**
| Option | Description |
|---|---|
| `-c` | Colored output |
| `-s` | Compute replay dir sizes (disk usage report) |
| `-f` | Fast mode: skip slow check_run_test_programs_log |
| `-v` | Verbose output |
| `-l` | List available builds and replays, then exit |
| `-batch` | Non-interactive: skip meld and emacs |
| `-only-new` | Show only new failures and regressions |
| `-exit-code` | Exit with non-zero status if new failures found |

**Examples:**
```bash
Tcheck_tact -c 30.0.0.128          # full colored report
Tcheck_tact -f -batch 30.0.0.128   # fast, non-interactive
Tcheck_tact -exit-code 30.0.0.128  # CI mode: exit 1 on new failures
Tcheck_tact -only-new 30.0.0.128   # show only regressions
Tcheck_tact -s                     # disk usage of replay dirs
Tcheck_tact -l 30.0.0.128          # list builds and replays
```

### Ttroubleshoot

Compare a baseline against its predecessor — scan regression test logs,
replay logs, and build closure logs side by side.

```
Ttroubleshoot <mode> [options] [<BASELINE>]
```

**Modes:**
| Mode | Description |
|---|---|
| `build_info` | Compare Csystem_build.log and check build closure |
| `ip <subtype>` | Troubleshoot IP regression tests (in, mono) |
| `op <subtype>` | Troubleshoot OP regression tests (in, assert) |
| `replay <type>` | Troubleshoot replays (prequal, performance, simca, full_simca) |

If `BASELINE` is omitted, it's derived from `$CONTEXT_CM_BASELINE`.

**Examples:**
```bash
Ttroubleshoot build_info 30.0.0.128
Ttroubleshoot ip in 30.0.0.128
Ttroubleshoot replay performance 30.0.0.128
```

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
| `FocusDomain` | `no_focus, focus_IP, focus_OP, focus_SIP, focus_replay, focus_build_info` |
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
- `rg` (ripgrep) — fast log searching
- `pyrg` — Python regex wrapper for ripgrep patterns
- `meld` — visual diff tool (interactive mode only)
- `fdcore` — finds core dump files
- `hcmp` — compare and normalize log files (replaced by `make_comparable` + `meld`)

## Building

```bash
cd TOOLS/TCHECK
ady2nim c -d:release Tcheck_tact.ady -o Tcheck_tact
ady2nim c -d:release Ttroubleshoot.ady -o Ttroubleshoot
ady2nim c -d:release make_comparable.ady -o make_comparable
```

## Origin

- `Tcheck_tact.ady` — translated from `Tcheck_tact.ksh` (TOOL/COMMON_UTILS)
- `Ttroubleshoot.ady` — translated from `hek-troubleshoot.sh`
- `make_comparable.ady` — translated from `make_comparable.ksh`
