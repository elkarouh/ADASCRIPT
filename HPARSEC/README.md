# hparsec — Python Parser Combinator Framework

A lightweight, operator-based parser combinator library for building recursive
descent parsers in Python. Inspired by
[David Beazley's three-problems post](https://github.com/dabeaz/blog/blob/main/2023/three-problems.md).

Parsers are composed using Python operators, producing typed AST nodes that
can be given output methods via the `@method` decorator.

---

## Files

| File | Purpose |
|------|---------|
| `hek_parsec.py` | Core combinators: `Parser`, `ParserState`, `SymbolTable`, `forward`, `method`, `filt`, `fmap`, `ignore`, `expect`, `literal`, … |
| `hek_tokenize.py` | `Tokenizer` — wraps Python's `tokenize` module; handles tick-attributes, range operators, bash-isms, f-string interpolation, `RichNL` comment bundling |
| `hek_helpers.py` | Shared helpers: indentation (`_ind`), `RichNL` extraction, block statement utilities |

---

## Operators

| Expression | Meaning |
|-----------|---------|
| `A + B` | Sequence — match A then B |
| `A \| B` | Choice — match A or B (first match wins) |
| `A[:]` | Zero or more repetitions |
| `A[1:]` | One or more repetitions |
| `A[n:m]` | Between n and m repetitions |
| `A * n` | Exactly n repetitions |
| `~A` | Negative lookahead — succeed only if A fails, consuming nothing |
| `fw("X")` | Lazy forward reference, for a recursive grammar |

---

## Quick start

```python
from hek_parsec import (
    Input, ParserState, method, forward,
    IDENTIFIER, EQUAL, NUMBER, SEMICOLON,
)

# Grammar
keyvalue  = IDENTIFIER + EQUAL + NUMBER + SEMICOLON
keyvalues = keyvalue[1:]

# Output method
@method(keyvalue)
def to_py(self):
    name  = self.nodes[0].to_py()
    value = self.nodes[1].to_py()
    return f"{name} = {value}"

# Parse
ParserState.reset()
stream = Input("x=42; y=7;")
result = keyvalues.parse(stream)
for node in result[0].nodes:
    print(node.to_py())
# x = 42
# y = 7
```

---

## Key concepts

### `method(parser_class)`
Decorator that attaches an output method to a parser class after the grammar
has been defined. Used to add `to_py()`, `to_nim()`, or any backend-specific
rendering without modifying the grammar definition:

```python
@method(if_stmt)
def to_py(self, indent=0):
    ...
```

### `forward(name)`
Creates a lazy forward reference for mutually recursive grammar rules.
The name is resolved in the calling module's namespace at parse time:

```python
expr     = forward("expr")
paren    = LPAREN + expr + RPAREN
expr     = NUMBER | paren | ...
```

### `filt(predicate, parser)`
Wraps a parser so it only succeeds when the matched token satisfies a
predicate. Used for context-sensitive matching:

```python
keyword = filt(lambda tok: tok.string in KEYWORDS, IDENTIFIER)
```

### `fmap(func, parser)`
Transforms the matched result through a function before returning it:

```python
integer = fmap(int, NUMBER)
```

### `ignore(parser)`
Matches the parser but discards the result from the AST (useful for
punctuation that does not need to appear in the tree):

```python
COMMA = ignore(expect(tkn.OP, ","))
```

### `SymbolTable`
A scoped symbol table for tracking declared variables and types during
parsing. Supports `push()`/`pop()` for nested scopes and `resolve_type()`
to follow type aliases transitively.

### `ParserState`
Global parse-time state. Holds `DEBUG`, `memos`, and `symbol_table`.
Backend-specific state (imports, type maps, pragmas, etc.) should be
initialised by the backend after calling `ParserState.reset()` — not stored
here.

**The state is process-global and mutable.** All grammar rules and output
methods read and write it through the class, so only one translation unit
can be "live" at a time. Historically this made nested translations —
transpiling an imported dependency in the middle of transpiling the main
file — silently corrupt the outer unit's state: whatever `reset()` and field
writes the inner unit performed were still in effect when control returned
to the outer unit. Callers worked around it with careful call ordering and
module-level stash variables, which is fragile and easy to get wrong.

`snapshot()` / `restore()` / `scoped()` exist to make nested use safe:

```python
with ParserState.scoped():        # save every data field
    ParserState.reset()
    translate(dependency_source)  # inner unit mutates freely
# outer unit's state is restored here, even on exception
```

- `snapshot()` captures **all** data attributes on the class — core fields
  and any backend fields added since — copying dicts/sets/lists one level
  deep so in-place mutations inside the scope don't leak out.
- `restore(snap)` puts the captured values back and deletes fields that
  were added after the snapshot.
- `scoped()` is the context-manager form of the pair and is exception-safe.

Any code that triggers a translation while another translation is in
progress **must** wrap the inner one in `scoped()`.

Remaining limitations (accepted by design for a single-threaded CLI):
the state is still a global, so translations cannot run concurrently, and
two units cannot be interleaved except through `scoped()` nesting. Making
the state an explicit object passed through every rule and output method
would lift that, at the cost of touching every call site in the grammar
and both backends.

### `RichNL` (in `hek_tokenize`)
A newline token enriched with any preceding inline comments. Allows comments
to travel naturally with the parse tree so backends can reproduce them in
generated output.

---

## Extra token types

`Tokenizer` does not rewrite the source. It wraps Python's `tokenize` and
emits token types Python has no notion of, so the Adascript syntax that
Python's lexer would otherwise mis-read arrives at the grammar intact:

| Token | Matches | Why Python's lexer needs help |
|-------|---------|-------------------------------|
| `TICK_TOKEN` | the `'` of `x'Image` | it would open a string literal |
| `DOLLAR_TOKEN` | the `$` of `$HOME`, `$1`, `$@`, `$#` | `$` is not a Python token at all |
| `BASH_TEST_TOKEN` | the `-` of `-e path` | it would be unary minus |
| `BASH_CMP_TOKEN` | `-nt`, `-ot` | as above |
| `RANGE_TOKEN` | `..` | `0..10` would lex as two floats |
| `RANGE_EXCL_TOKEN` | `..<` | as above |
| `REGEX_TOKEN` | `/pattern/flags` | it would be division |
| `CAPTURE_TOKEN` | `$+1` | — |
| `NAMED_CAPTURE_TOKEN` | `$+{name}` | — |
| `SUBST_TOKEN` | `s/pattern/replacement/flags` | — |
| `ENVDEF_TOKEN` | the `${NAME:-` of `${NAME:-default}` | as `DOLLAR_TOKEN` |
| `ENVOPT_TOKEN` | `$?NAME`, `${?NAME}` | as `DOLLAR_TOKEN` |

The grammar consumes these like any other token — `tick_trailer = TICK +
IDENTIFIER`, `dollar_var = DOLLAR + _DOLLAR_SUFFIX` — and the backends
resolve them from the parse tree.

Several are context-sensitive rather than lexical: `-e` is a
`BASH_TEST_TOKEN` in `if -e path:` but stays an ordinary minus in
`func(-e, y)`, and a `'` only opens a tick when a name precedes it, so
`'hello'` is still one string token.

---

## Design notes

- **No dependencies** beyond the Python standard library.
- **Backend-agnostic**: the library knows nothing about Nim, Python output,
  or any target language. Backends attach output methods via `@method`.
- **Memoization**: `apply_parsing_context` wraps each `parse()` call with
  packrat-style caching keyed by `(parser_id, position)`, giving linear-time
  parsing for unambiguous grammars.
- **Error reporting**: the tokenizer tracks the farthest position reached
  and the set of expected tokens at that point, producing useful parse-error
  messages even on complex failures.
