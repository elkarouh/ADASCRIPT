# Chapter 7 — Regular Expressions as a Language Feature

Perl and AWK made text processing pleasant by making regexes *syntax*, not a
library. Adascript does the same: `/pattern/flags` is a literal, matching is
an operator, and captures are variables. There is never an `import re`.
`EXAMPLES/test_regex.ady` is the systematic tour; `awk_example.ady` and
`spell.ady` show the idioms in context.

## 7.1 Match tests: `==` and `!=`

A string compared to a regex literal is a match test:

```python
def is_integer(s: str) -> bool:
    s == /^\d+$/

def is_not_blank(s: str) -> bool:
    s != /^\s*$/

def is_yes(s: str) -> bool:
    s == /^yes$/i          # i flag: case-insensitive
```

(All from `test_regex.ady`; all use implicit return.) In Nim this becomes
`nimatch(s, re"...")`, in Python `_pymatch(s, r'...')` — both helpers are
injected automatically into the generated file when needed.

## 7.2 Captures: `$+N` and named groups

After a successful match, `$+0` is the whole match and `$+1`, `$+2`, … are
the capture groups:

```python
def parse_kv(s: str) -> str:
    if s == /(\w+)\s*=\s*(\w+)/:
        f"{$+1} -> {$+2}"
    else:
        "no match"
```

Named groups use PCRE `(?P<name>...)` syntax and are read back either
through `$+{name}` or the `namedCaptures` dict:

```python
def parse_date(s: str) -> str:
    if s == /(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/:
        f"{$+{day}}/{$+{month}}/{$+{year}}"
    else:
        "invalid date"
```

`matches` and `namedCaptures` are globals populated by the most recent
match — copy the values out before running another regex.

## 7.3 Find-all: the `g` flag

With `g`, a match test stops being a boolean and returns every
non-overlapping match as `[]str`:

```python
def all_words(s: str) -> []str:
    s == /\w+/g

def all_tags(s: str) -> []str:
    s == /<[^>]+>/g
```

This one feature makes corpus loading in `spell.ady` a single expression —
tokenise the entire text of `big.txt` into lowercase words:

```python
def words(text: str) -> []str:
    text.lower() == /[a-z]+/g

let WORDS: Counter_T[str] = Counter_T(words(readFile(corpus_file)))
```

`!= /pat/g` is meaningless; test emptiness with `len(s == /pat/g) == 0`.

## 7.4 Substitution: `s/pat/repl/flags`

The Perl substitution form assigns its result back to the left-hand side:

```python
def redact_numbers(s: str) -> str:
    s == s/\d+/[N]/g       # "phone: 555-1234" -> "phone: [N]-[N]"
    s

def normalize_spaces(s: str) -> str:
    s == s/\s+/ /g         # collapse whitespace runs
    s
```

Backreferences in the replacement use `$+1` / `$+{name}`. Under the hood:
Nim `s = s.replace(srx.re(r"pat"), "repl")`, Python `s = re.sub(...)`.

## 7.5 Regexes as patterns

Chapter 5 previewed the classifier from `awk_example.ady`; here is the full
data path from stdin to report, because it is the language's best
advertisement for AWK-style work:

```python
type Severity_T is enum INFO, WARN, ERROR, OTHER

def classify(line: str) -> Severity_T:
    case line:
        when /error/i:      return ERROR
        when /warn/i:       return WARN
        when /info|debug/i: return INFO
        when others:        return OTHER

def process(raw: str):
    let line: str = raw.rstrip()
    NR += 1
    let Fields: []str = (line.split() if FS == " " else line.split(FS))
    NF = Fields'Length
    total_len += line'Length
    total_nf  += NF

    let sev: Severity_T = classify(line)
    counts[sev] += 1
    ...
```

A regex `when` mixes freely with literal `when`s in the same `case`; the
whole block desugars to a match-test chain on both backends.

## 7.6 Flags and translation summary

| Flag | Meaning |
|------|---------|
| `i` | case-insensitive |
| `g` | return all matches as `[]str` (on `==`), global replace (on `s///`) |
| `m` | multiline: `^` / `$` match at line boundaries |
| `s` | dotall: `.` matches newlines |

| Adascript | Nim | Python |
|-----------|-----|--------|
| `s == /pat/` | `nimatch(s, re"pat")` | `_pymatch(s, r'pat')` |
| `s == /pat/i` | `nimatch(s, re"(?i)pat")` | `_pymatch(s, r'pat', re.IGNORECASE)` |
| `s == /pat/g` | `s.findAll(srx.re(r"pat"))` | `re.findall(r'pat', s)` |
| `$+N` | `matches[N]` | `matches[N]` |
| `$+{k}` | `namedCaptures["k"]` | `namedCaptures["k"]` |
| `s == s/pat/repl/g` | `s = s.replace(srx.re(r"pat"), "repl")` | `s = re.sub(r'pat', r'repl', s)` |
| `when /pat/:` | `elif nimatch(subject, re"pat"):` | `elif _pymatch(subject, r'pat'):` |

## 7.7 A worked example: config-file parsing without a parser

`EXAMPLES/lolcate/lolcate.ady` (a port of the lolcate-rs file indexer) keeps
its per-database configuration in a line-based text format — section headers
like `dirs:` and `ignores:` followed by entries. The header comment calls it
"no external parser needed": a `for line in ...` loop, a couple of match
tests and string methods do the whole job. That is the regex chapter's
closing moral: when matching is an operator and captures are variables, the
threshold at which you need a parsing library moves a long way out.

---

*Next: [Chapter 8 — Functions, Closures, and Generators](08-functions-and-generators.md)*
