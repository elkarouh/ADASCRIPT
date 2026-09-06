# Appendix — Syntax Cheat Sheet and Toolchain

## A.1 Adascript-only syntax at a glance

| Feature | Syntax |
|---------|--------|
| Mutable variable | `var x: int = 0` |
| Immutable binding | `let name: str = "hello"` |
| Compile-time constant | `const MAX: int = 1000` |
| Enum | `type E is enum A, B, C` |
| Named tuple | `type P is tuple:` + fields |
| Record | `type P is record:` + fields |
| Variant record | `type S (Kind: K) is record: case Kind is when ...` |
| Subrange | `type T is lo .. hi` / `type T is int range lo..hi` |
| Float subrange | `type T is float range lo .. hi` |
| List / fixed array / open array | `[]T` / `[N]T` / `[*]T` (params only) |
| Dict / set / enum-indexed array | `{K}V` / `{}T` / `[E]T` |
| Optional | `?T` |
| Function type | `[(T, U)]R` |
| Empty dict / empty set | `{:}` / `{}` |
| Inclusive / exclusive range | `lo .. hi` / `lo ..< hi` |
| Enum bounds / full set | `E'First`, `E'Last` / `E'Range` |
| Successor / predecessor | `x'Next` / `x'Prev` |
| Random element | `x'Choice` (enum, set, or range) |
| String repr / length | `x'Image` / `s'Length` |
| Named tuple literal | `(field: value, ...)` |
| Enum array literal | `[KEY: value, ...]` |
| Pattern matching (Ada style) | `case x:` / `when pat:` / `when others:` |
| Pattern matching (Python style) | `match x:` / `case pat if guard:` |
| Inline suite | `if c: stmt`, `when p: stmt`, `while c: stmt` |
| Implicit return | last bare expression of a `-> T` function |
| Nim result variable | `result` inside a `-> T` function |
| Class field | `var x: T = default` in class body |
| Cross-module base class | `@virtual class C:` |
| Generic class | `class C[S, D, C]:` |
| Nim-only / Python-only import | `nimport m` / `pyimport m` |
| Raw Nim line | `# nimraw: <code>` |
| Per-file Nim flags | `#ady2nim-args c -d:release` (line 2) |
| Shell capture | `let r = shell: cmd` → `.output`, `.stderr`, `.code` |
| Shell exit code, terminal kept | `let code: int = shell: cmd` |
| Shell lines | `let ls = shellLines: cmd` |
| Shell lines (typed/bare) | `let ls: []str = shellLines: cmd` / `ls = shellLines: cmd` |
| Shell expr interpolation | `{f(x)}` in body — auto-hoisted to temp variable |
| Shell interpolation, quoted | `{!path}` — one argument whatever it holds |
| Shell interpolation, list | `{*args}` — each element quoted, space-joined |
| Shell, fail on non-zero | `shell(check = true): cmd` |
| Shell, feed stdin | `shell(stdin = text): cmd` (capturing forms) |
| Shell, child environment | `shell(env = {"K": v}): cmd` — added, not replaced |
| Shell, streamed lines | `for line in shellIter: cmd` + body |
| Shell options | `shell(cwd = "...", timeout = ms): cmd` |
| Shell block / PTY automation | `shell:` + lines / + `send()`/`expect()` |
| CLI args | `$0`, `$1`…`$9`, `$@`, `$#` |
| Environment variable | `$HOME`, `$EDITOR`, … |
| File tests | `-e -f -d -L -r -w -x -s path`; `a -nt b`; `a -ot b` |
| Regex match / find-all | `s == /pat/flags` / `s == /pat/g` → `[]str` |
| Regex captures | `$+0`, `$+1`, …, `$+{name}`, `namedCaptures` |
| Regex substitution | `s == s/pat/repl/g` |
| Regex pattern in case | `when /pat/:` |
| Print statement | `print "x =", x` (parens optional) |
| Ownership | `own x: T`, `lent T`, `own T` (param), `move(x)`, `drop(x)`, `with own x = e:` |
| Maybe-monad block | `do:` + `x <- optional_expr` lines |

Flags on regex literals: `i` (ignore case), `g` (all matches / global
substitution), `m` (multiline), `s` (dotall).

Predefined subtypes: `Natural` (0..), `Positive` (1..).

## A.2 Toolchain reference

```bash
# Python backend
python3 TO_PYTHON/py2py.py source.ady          # emit Python to stdout
python3 TO_PYTHON/py2py.py -c source.ady       # transpile and run
echo "var x: int = 42" | python3 TO_PYTHON/py2py.py    # from stdin

# Nim backend
python3 TO_NIM/py2nim.py source.ady            # transpile + compile + run
python3 TO_NIM/py2nim.py -t source.ady         # transpile only → source.nim
python3 TO_NIM/py2nim.py c source.ady          # nim c
python3 TO_NIM/py2nim.py c -r source.ady       # nim c -r
python3 TO_NIM/py2nim.py c -d:release source.ady  # optimised; unknown flags → nim
python3 TO_NIM/py2nim.py --test                # transpiler self-tests
```

Executable scripts:

```python
#!/usr/bin/env py2nim
#ady2nim-args c -d:release
```

then `chmod +x script.ady && ./script.ady`. Artifacts live in
`~/.cache/hparsec/cache-<HASH>/`; a symlink to the binary is placed next to
the source. Builds are incremental (transpile / compile / run each skipped
when up to date); editing any transpiler `.py` file invalidates the caches.

### Building the whole corpus

The `Makefile` at the repository root drives every example:

```bash
make install    # put py2nim and py2py on PATH (PREFIX=... to relocate)
make compile    # transpile + compile every example, no run
make test       # compile, then run the suite (36 examples, 67 checks)
make clean      # remove ~/.cache/hparsec/ and the binary symlinks
make uninstall  # remove the launchers again
```

`make install` is what makes the `#!/usr/bin/env py2nim` shebang at the top
of every example resolve, so a `.ady` file becomes directly executable from
any directory. It also fetches the `HPARSEC` submodule if the clone omitted
it, and verifies itself by transpiling and running a small program.

`make clean` is the one to reach for when a build looks stale in a way the
incremental check did not catch — it is also what you want before timing
anything, since an up-to-date binary is simply re-run rather than rebuilt.

Nim dependencies, when used: `nimble install nimpy` (for `pyimport`-bridged
libraries), `nimble install db_connector` (for `nimport db`).

A file may pin its C compiler on the `#ady2nim-args` line
(`--cc:clang --clang.exe:zigcc`). That is a preference: when the named
binary is not installed, `py2nim` drops the pin, says so on stderr, and lets
Nim use its default C compiler — so no example needs a particular toolchain
in order to build.

## A.3 Bundled Adascript/Nim libraries

| Import | Provides | Exercised by |
|--------|----------|--------------|
| `nimport stdlib` | `PriorityQueue`, `FifoQueue`, `LifoQueue`, `Counter_T`, `ANY` | `dijkstra.ady`, `shortest_path.ady`, `state_search.ady`, `spell.ady` |
| `nimport awk` | `AwkBase` record-processor base class | `test_awk.ady` |
| `nimport iters` | itertools analogues (`pairwise`, `chain`, `combinations`, …) | `test_iters.ady` |
| `nimport expect` | `Spawn`, `send`, `expect` PTY automation | `test_expect.ady` |
| `nimport <file>` | any other `.ady` compiled as a library | `test_shortest_path.ady` |

## A.4 Known limitations (as of this writing)

- `py2py.py` collapses blank lines and drops inline comments in output.
- `case` subjects must be structural expressions (`(a, b)`, `x.field`) for
  tuple/record patterns — a plain variable falls through to Nim's ordinal
  `case` and fails to compile (§5.3).
- Tick attributes don't attach to field accesses or subscripts
  (`self.x'Image` — bind to a local first).
- `[*]T` is parameter/return-only.
- No borrow checker; `move()` misuse surfaces at runtime, not compile time.
- Generic methods on `@virtual` classes hit Nim 2.x restrictions — define
  them as free functions taking `self` and rely on UFCS (§9.5).
- `ParserState` is a global singleton: call `ParserState.reset()` between
  sequential runs in one process, or `with ParserState.scoped():` around a
  nested one. Concurrent parses in separate threads are still unsupported.

The authoritative, up-to-date lists live in `README.md` ("Known
Limitations") and `TODO.md`.

## A.5 Further reading in this repository

- `README.md` — feature reference with translation tables.
- `TUTORIAL.md` — the long-form tutorial this book complements (20 sections,
  including the full memory-ownership chapter).
- `TUTORIAL_FOR_LLM.md` — a condensed variant tuned for language models.
- `OPTIONAL_TYPES.md` — optionals and monadic patterns, 22 sections.
- `PATTERN_MATCHING.md` — the complete pattern-matching reference.
- `ADASCRIPT_GRAMMAR/`, `HPARSEC/` — the grammar and the parser-combinator
  engine, if you want to extend the language itself.

---

*[Back to the table of contents](README.md)*
