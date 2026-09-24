# TBLAME — Batch WHO/WHEN/WHY Git-Blame Lookups

Translated from the ksh/zsh original (`Tblame.ksh`) to Adascript.

## Tblame

Reads lines shaped `<file>:<line_no>[<info>]` (e.g. piped from `grep -n`)
and answers, per line, WHO (user) last touched it, WHEN (date), and WHY
(the software-change ticket the commit belongs to) — plus the blamed
source text and any trailing `<info>` carried on the input line.

```
Tblame [OPTIONS...] [COLUMN_NAME...] [- FILENAME...]
```

**Options:**
| Option | Description |
|---|---|
| `-filter_unmatched` | Drop input lines that don't match `<file>:<line_no>` instead of passing them through |
| `-alternate <root>` | Use an alternative NM repository root (also `$NM_REPOSITORY_ALTERNATE`) |
| `-since <epoch>` | Drop lines committed before `<epoch>` |
| `-debug` | Verbose tracing to stderr |

**Columns:** `checksum date user sc_first sc_hint sc_all file_original
file_name file_workspace reference reference_blame` — default is `date
sc_hint user file_workspace reference_blame`. `Tblame -help` lists each
one's meaning.

## What changed from the ksh original

**One `git blame` process per distinct (repository, revision, file)**,
not one per input line. Each call requests every needed line in that file
with repeated `-L n,n` flags; results are matched back to requesters by
the line number git itself reports in each porcelain block, not by the
order or count of the `-L` flags sent — git sorts and deduplicates `-L`
ranges internally, so request order/count cannot be relied on. Measured
on a 31-line/1-file test input: 31 `git` invocations collapse to 1.

**All dates are formatted by one `date` process** (`date -f -`), not one
per output row. Measured on a 300-hit input over six commits: 300 `date`
processes and 1.19 s become 1 process and 0.02 s -- formatting dates had
cost far more than the blaming itself.

**`- FILENAME...` reads the named files directly** instead of piping
`grep -n` output back into a fresh copy of the running program. Same
observable output, no dependency on how the program resolves its own path
on a given site.

## Structure

| Class | What it owns |
|---|---|
| `Options` | what was asked for: flags, columns, files, the alternate (with its env fallback and readability check) |
| `Resolver` | what this site's paths mean: the two path shapes, the workspace root, the alternate (registered once), and the revision each baseline resolves to (cached) |
| `BlameBatch` | blaming each (repository, revision, file) once and handing each input line its result |
| `Report` | the rows in input order, pass-through lines, the `-since` filter, column widths and printing |

`Hit` (one input line, resolved), `Blame` (one line's result) and `Target`
(one file at one revision) are the records passed between them. Hits are
known to `BlameBatch` by input index, not by reference, since classes and
records are value types on the Nim backend.

## Bugs found in the ksh original while translating

Testing this translation against a real (if small) git repository — not
just reading the ksh — surfaced three real, pre-existing defects, none of
which trace back to anything this translation introduced:

1. **`sc_hint` name collision.** The ksh script's `sc_hint`/`sc_first`
   column-value logic uses a local scalar named `sc_hint`, which is *also*
   the name of the `sc_hint` output-column array. The collision was
   accidentally harmless in the original because that code ran inside a
   `$(...)` subshell; asking for several columns together (e.g. adding
   `reference`) crashed it with a `bad math expression` error and
   corrupted output. Adascript's lexical scoping has no equivalent
   collision to hit.
2. **An unused `ref` computation** in `revision_of_context_file`: the ksh
   original computes a `workspace/...` ref form from the baseline (lower
   -cased, underscores to dashes) but then calls `git rev-parse` with the
   raw baseline string, never the computed `ref`. Dropped here since it
   had no effect on the result.
3. **A case mismatch in the same function's revision cache**: the cache
   is *populated* under a key built from the baseline's raw case, but
   *looked up* under a key with the baseline lower-cased. Any baseline
   containing uppercase letters (a realistic NM build id, e.g.
   `G!31.IP.L8`) always missed the cache it had just filled and silently
   fell back to blaming HEAD instead of the resolved revision. Fixed by
   lower-casing both sides of the cache key.

## Testing

`test/run_tests.sh` builds a throwaway git repository standing in for an
NM workspace (three commits, a tag, a multi-ticket commit), stubs the
site-specific `Psort` tool, and drives a built `Tblame` binary through:
the default and full column sets, duplicate-line and same-commit-cache
batching, `-filter_unmatched`, `-since`, the `- FILENAME` direct-read
mode, and the `/cm/ot/...` context-path branch via `-alternate` and a git
tag (proving a revision is actually resolved and blamed against, not
just defaulted to HEAD).

```bash
python3.13 TO_NIM/ady2nim.py c TOOLS/TBLAME/Tblame.ady   # builds ../Tblame
cd TOOLS/TBLAME/test && sh run_tests.sh
```

The `/NM/...` workspace-path branch and the `/cm/ot/...` context-path
branch (both the `-alternate` and the `where_workspace`-via-workspace
sub-paths) are exercised this way. `where_workspace` itself is not
stubbed by the test (the `-alternate` path used for context-path coverage
doesn't call it) — like `Psort`, it is site-specific NM tooling ported
structurally from the ksh original.
