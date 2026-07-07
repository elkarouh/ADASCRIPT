# Chapter 10 — Optional Types and the Maybe Monad

`?T` means "a `T`, or nothing". The absent value is written `None`, exactly
as in Python — and the transpiler maps the whole vocabulary (`None`,
`is None`, `is not None`, truthiness) to Nim's `Option[T]` machinery. You
never write `some()`, `.get()`, or `.isSome` by hand. The full reference is
`OPTIONAL_TYPES.md` at the repository root; this chapter covers what the
examples actually use.

## 10.1 Basic use

```python
var name:    ?str        # optional string
var count:   ?int  = None
count = 42               # wrapped automatically on the Nim side
```

Optional **return types** are the bread-and-butter case. Searching a trie in
`phonecode.ady` either finds a word or doesn't:

```python
def find_exact_word(self, digits: []Digit_T) -> ?str:
    var node: TrieNode = self
    for digit in digits:
        if node.children[digit] is None:
            return None
        node = node.children[digit]
    if len(node.words) > 0:
        return node.words[0]
    return None
```

and the caller tests with plain Python idiom:

```python
let exact_match: ?str = trie.find_exact_word(test_digits)
if exact_match is not None:
    print(f"Exact match for digits 3,5: {exact_match}")
else:
    print("No exact match for digits 3,5")
```

Note the auto-unwrap: inside the `is not None` guard, `exact_match` is used
directly in the f-string — on the Nim side the transpiler inserts the
`.get()` for you.

## 10.2 Optionals in recursion

`graph.ady`'s path finder returns `?[]Node_T` — an optional list — and
threads the "not found" case up the recursion without exceptions or
sentinel values:

```python
def find_path(graph: Graph_T, start_node: Node_T, end_node: Node_T,
              path:[]Node_T=[]) -> ?[]Node_T:
    path = path + [start_node]
    if start_node == end_node:
        return path
    if start_node not in graph:
        return None
    for node in graph[start_node]:
        if node not in path:
            newpath : ?[]Node_T = find_path(graph, node, end_node, path)
            if newpath is not None:
              return newpath
    return None

let path_AD: ?[]Node_T = find_path(graph, A, D)
assert path_AD is not None
print path_AD
```

The type honestly describes the function: it may fail, and the compiler (on
the Nim target) makes you acknowledge that at every call site.

## 10.3 Optional fields

`?T` works on fields too. `geo_server.ady` stores an optional predicate —
`None` in subclasses that override `__contains__` directly, present in
composed regions:

```python
class Region:
    var _predicate: ?[(Point,)]bool

    def __init__(self, predicate: ?[(Point,)]bool = None) -> None:
        self._predicate = predicate

    def __contains__(self, point: Point) -> bool:
        if self._predicate is None:
            raise NotImplementedError("Region subclass must implement __contains__")
        return self._predicate(point)
```

(`phonecode.ady`'s trie children are `None`-able for a different reason:
class instances are `ref` types on the Nim side, which can be nil natively —
no `Option` wrapper needed. The transpiler knows the difference.)

## 10.4 The `do:` block — monadic bind chains

A pipeline of maybe-failing steps normally forces either nested `if`s or an
early-return ladder. Adascript borrows Haskell's do-notation:
inside a `do:` block, `x <- expr` unwraps an optional or **short-circuits
the whole block to `None`**. `EXAMPLES/test_do_block.ady` is the spec:

```python
def try_parse_int(s: str) -> ?int:
    if len(s) == 0: return None
    for c in s:
        if not (c >= '0' and c <= '9'): return None
    return int(s)

def safe_div(a: int, b: int) -> ?int:
    if b == 0: return None
    return a // b

def clamp_positive(n: int) -> ?int:
    if n <= 0: return None
    return n

def compute(raw_a: str, raw_b: str) -> ?int:
    """Parse two strings and return their quotient, or None on any failure."""
    do:
        a <- try_parse_int(raw_a)
        b <- try_parse_int(raw_b)
        q <- safe_div(a, b)
        r <- clamp_positive(q)
    return r
```

After each `<-`, the bound name is a plain (non-optional) value — `a` and
`b` go straight into `safe_div`. The test file walks every failure mode:

```python
let r1: ?int = compute("20", "4")    # Some(5)
let r2: ?int = compute("abc", "4")   # None — first step fails
let r3: ?int = compute("20", "0")    # None — middle step fails
let r4: ?int = compute("0", "4")     # None — last step fails
```

This is the Maybe monad's "railroad" pattern: the happy path reads straight
down the page, and failure at any step diverts to the `None` track without
another line of code. `OPTIONAL_TYPES.md` §16–22 develops the theme further
(fmap, sequence/traverse, and a `Result_T` Either-analogue for carrying
error messages).

## 10.5 When *not* to use `?T`

The examples are equally instructive about the negative space:

- **Container "not found"** — `dijkstra.ady` uses `MAX_DIST` as an infinity
  sentinel rather than `?Distance_T`, because arithmetic on distances must
  stay unconditional inside the hot loop.
- **Contradiction in a solver** — `sudoku.ady` returns the empty dict `{:}`
  rather than `?{str}str`, because the empty dict is already falsy and the
  algorithm tests `if not values:` a dozen times.
- **A default is available** — use `.get(key, default)` (see
  `self.G.get(curr, [])` in the optimiser subclasses) instead of an optional
  lookup followed by a branch.

`?T` shines when *absence is meaningful at the interface* — search results,
parse results, configuration that may be missing — and the `do:` block keeps
chains of such interfaces readable.

---

*Next: [Chapter 11 — Shell Integration: Adascript as a Better Bash](11-shell-and-scripting.md)*
