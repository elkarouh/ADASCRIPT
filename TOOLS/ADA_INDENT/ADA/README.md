# ada_indent in Ada

A translation of [`../ada_indent.ady`](../ada_indent.ady) -- the Ada
re-indenter -- into an Ada 2012 application. It behaves the same as the
Adascript build: same options (`-h`, `-q`, `--emit-state`, `--state`), same
indenting, same diagnostics on stderr, same `##STATE:` snapshots. The grammar
and the comment rules are documented in [`../README.md`](../README.md).

## Build and run

Needs GNAT and `gprbuild`, run through the `g` wrapper (`g gprbuild`, `g gprclean`);
without it, `make GPRBUILD=gprbuild GPRCLEAN=gprclean`.

```bash
make                                  # or: g gprbuild -P ada_indent.gpr
bin/ada_indent file.adb               # re-indent a file
cat file.adb | bin/ada_indent         # ...or stdin
g gprbuild -P ada_indent.gpr -XMODE=debug   # assertions, overflow and stack checks
```

## Layout

| Ada file | Adascript source it mirrors |
|---|---|
| `src/strscan.ads/.adb` | `TO_NIM/STDLIB/strscan.ady`, plus the Python/Nim string idioms the indenter uses (`strip`, `split`, slices) |
| `src/ada_scan.ads/.adb` | the "Lexical helpers" and "Construct names" sections of `ada_indent.ady` (`last_word`, `code_words`, `stmt_incomplete`, `scan_parens`, `declared_name`, ...) |
| `src/indenter.ads/.adb` | `class Indenter` (frame stack, `indent_raw`, `indent_lines`, `dump_state`/`load_state`) |
| `src/ada_indent.adb` | `usage` and `main` |

Names follow the Adascript source (`Last_Word` for `last_word`, `Indenter_T`
fields in the same order). Two conventions carry the translation:

* Indices are **0-based** in `Strscan` and everything built on it (`Ch (S, I)`,
  `Slice (S, Lo, Hi)` = `s[lo:hi]`), so each line of logic reads against the
  original line by line. Strings returned from `Strscan` always have bounds `1 .. N`.
* Enum literals carry a prefix (`B_PKG`, `P_PLAIN`) because `RECORD`, `SELECT`,
  `CASE`, `LOOP`, ... are reserved words in Ada. The saved state still spells
  them `PKG`, `PLAIN`, ... so snapshots are interchangeable with the Adascript build.

## Tests

```bash
make test      # the golden sample and regress/valid_*.adb come back unchanged,
               # as they are and with all leading whitespace stripped;
               # then ../metamorphic_check.py drives bin/ada_indent
make compare   # byte-for-byte against the Adascript build (REF=../ada_indent):
               # stdout, stderr and --emit-state over the sample and regress/ files
```

When the translation was written it was also compared with the Adascript
program (transpiled to Python) on the GNAT run-time library sources and on
mangled copies of the fixtures (deleted, duplicated and truncated lines,
stray keywords and parentheses): stdout, stderr and `--emit-state` identical.
