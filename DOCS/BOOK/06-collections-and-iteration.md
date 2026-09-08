# Chapter 6 — Collections and Iteration

Chapter 2 introduced the type notation for collections. This chapter is
about *using* them: literals, comprehensions, loops, and the iterator
library — with Norvig's Sudoku solver and spelling corrector as the running
examples, because both are dense with idiomatic collection code.

## 6.1 Sequences

```python
var words:  []str     = ["hello", "world"]
var matrix: [][]float = [[1.0, 2.0], [3.0, 4.0]]

words.append("!")
print(len(words))
```

Python list methods (`append`, slicing, `in`, `not in`, `len`) work
unchanged and map to `seq` operations in Nim. `+` concatenates two
sequences, and the Nim backend rewrites it to that language's `&`.

`EXAMPLES/sudoku.ady` builds its unit list — all nine rows, nine columns
and nine boxes — as three comprehensions joined:

```python
var unitlist: [][]str = (
    [cross(ROWS, c) for c in COLS]
    + [cross(r, COLS) for r in ROWS]
    + [cross(rb, cb) for rb in ["ABC", "DEF", "GHI"] for cb in ["123", "456", "789"]])
```

That is Norvig's own line, transliterated. The two derived tables read the
same way — a dict comprehension whose value is itself a comprehension:

```python
var units: {str}[][]str = {s: [u for u in unitlist if s in u] for s in squares}
var peers: {str}{}str = {s: {s2 for u in units[s] for s2 in u if s2 != s} for s in squares}
```

`units` maps a square to the three units containing it, `peers` to the 20
squares it shares a unit with — and note the second comprehension is a
`{…}` set, so duplicates across the three units collapse without the
algorithm having to think about them.

## 6.2 Hash tables

`{K}V` literals look like Python dicts; iteration uses `.items()`, lookup
supports `.get(key, default)`, and `in` tests keys:

```python
var counts: {str}int = {:}
counts["apple"] += 1

for key, val in counts.items():
    print(f"{key}: {val}")
```

Sudoku's whole board is a `{str}str` — square name to remaining candidate
digits — and the solver threads it functionally through `assign`/`eliminate`,
returning `{:}` to signal contradiction (see §2.3).

The `{…}` in the notation is a promise about order, or rather the absence of
one, and it is worth taking literally when a program has to build on both
backends. Iterating the same `{str}int` yields insertion order on Python and
hash order on Nim — keys inserted `zebra, apple, mango, kiwi, banana` come
back in that order from one and as `zebra, kiwi, apple, mango, banana` from
the other. Sets behave the same way. Nothing is wrong in either case; the
type simply never promised an order. Where output has to match, collect the
keys and sort those, or keep the data in one of the `[…]` forms, which do
iterate in order on both:

```python
var keys: []str = []
for k in counts.keys():
    keys.append(k)
for key in sorted(keys):
    print key, counts[key]
```

Sort the keys rather than the table: `sorted(counts)` works on the Python
backend but has no meaning for a Nim `Table`, and fails to compile there.

Dict comprehensions work, including conditional expressions inside.
`dijkstra.ady` initialises all distances in one line:

```python
distances: {Node_T}Distance_T = {node: (0.0 if node==start else MAX_DIST) for node in graph}
```

Two things are carrying the weight there. The conditional is *inside* the
comprehension, so Dijkstra's initialisation has no second phase where the
start node gets fixed up afterwards — which is where that loop usually goes
wrong. And `for node in graph` iterates a `{K}V`, which yields its keys, so
the clause reads "for each node in the graph". §1.4 shows the whole
program, which is 28 lines for the entire algorithm.

## 6.3 Sets

Beyond the ordinal bitsets of Chapter 3, `{}T` over strings or other
non-ordinal types is a hash set (`HashSet` in Nim). The visited-set idiom
from `dijkstra.ady`:

```python
var visited : {}Node_T
...
if node in visited:
    continue
visited.add(node)
```

`spell.ady` (Norvig's corrector) is set-driven end to end. Set
comprehensions filter candidate corrections against the corpus:

```python
def known_variations(variations: {}str) -> {}str:
    {variation for variation in variations if variation in WORDS}

def edits2(word: str) -> {}str:
    {e2 for e1 in edits1(word) for e2 in edits1(e1)}
```

— note the double generator in `edits2`, and that both functions use
implicit return (Chapter 8). The edit-distance-1 generator shows sets
absorbing duplicates so the algorithm doesn't have to think about them:

```python
def edits1(word: str) -> {}str:
    let letters: str = "abcdefghijklmnopqrstuvwxyz"
    var result: {}str
    var L: str
    var R: str
    for i in word'Range:
        L = word[:i]
        R = word[i:]
        result.add(L + R[1:])                      # delete
        if len(R) > 1:
            result.add(L + R[1] + R[0] + R[2:])    # transpose
        for c in letters:
            result.add(L + c + R[1:])              # replace
            result.add(L + c + R)                  # insert
    for c in letters:
        result.add(word + c)                       # insert at end
    return result
```

Python's slicing (`word[:i]`, `R[2:]`) survives intact on both backends, and
`word'Range` iterates the index range of the string.

## 6.4 List comprehensions

Available wherever expressions are, including method bodies. From
`phonecode.ady`:

```python
def clean_number(num: str) -> []Digit_T:
    return [CHAR_TO_DIGIT[c] for c in num if c in CHAR_TO_DIGIT]
```

and from the knapsack/rod-cutting models in `test_shortest_path.ady`,
filtering feasible decisions:

```python
def get_next_decisions(self, current_state: State_T) -> []Choice_T:
    let (stage, remaining_size) = current_state
    [(size, rev) for size, rev in self.choices if size <= remaining_size]
```

### The loop variable

A comprehension's loop variable is typed from whatever it iterates, the
same as a `for` statement's, so the element expression can operate on it:

```python
[r + c for r in ["A", "B"] for c in ["1", "2"]]   # ["A1","A2","B1","B2"]
[p + q for p in "AB" for q in "12"]               # the same, over strings
```

Both matter on the Nim backend, which has separate operators for arithmetic
and concatenation and so has to know which one is meant. Iterating a string
yields chars there, and the second line relies on `char + char` being a
string — it is `sudoku.ady`'s `cross()`, whole.

The same knowledge lets a char go wherever a string is wanted, so the
`str(c)` conversions that used to litter code like this are gone. Four
places take it: a call argument whose parameter is `str` (`cross(ROWS, c)`
in §6.1), a declaration annotated `str`, `.append` onto a `[]str`, and a
string method given part chars and part strings — Nim overloads `replace`,
`split` and the rest all-char or all-string with nothing mixed, so
`s.replace(c, "\\" + c)` needed a conversion on the first argument alone.
An all-char call is left as it is; that overload is the better one. Each
case is an error on Nim and a no-op on Python, where a char *is* a
one-character string, so converting can only make the two agree.
`sudoku.ady`'s grid parser is the shape that gets shorter:

```python
var chars: []str
for c in grid:
    if c in DIGITS or c == "0" or c == ".":
        chars.append(c)
```

A slice is not a char, and is left alone: `s[i]` indexes, `s[2:10]` cuts.

The binding is scoped to the comprehension, as in Python. The same name can
hold different types in two of them, and an outer name of that spelling is
untouched:

```python
let same: int = 5
[same + "?" for same in ["p"]]      # a string in here
assert same + 1 == 6                # still the outer int out here
```

### Comprehensions that build arrays

A comprehension normally produces a growable sequence. In Adascript the
annotation decides what it produces, and the *same* comprehension will fill
a fixed-size array instead:

```python
var asSeq: []int  = [i*i for i in 0..4]     # a seq / list
var asArr: [5]int = [i*i for i in 0..4]     # a stack array, 5 slots
```

Nothing about the right-hand side changed. That is the part worth noticing:
the length lives in the type, so the expression that fills the container
does not have to know it, and switching between the two is an edit to the
annotation alone.

The Nim backend earns that. Nim will not assign a `collect()` to an
`array[N, T]`, so the transpiler emits the copy:

```nim
var asSeq: seq[int] = toSeq(collect(for i in 0 .. 4: i * i))
var asArr: array[5, int] = (block:
let adasq = collect(for i in 0 .. 4: i * i)
var adaarr: array[5, int]
for adai in 0 ..< 5: adaarr[adai] = adasq[adai]
adaarr)
```

Among statically typed languages this is rarer than it looks, though not
unique: Fortran has had implied-do array constructors since F90
(`[(i*2, i=1,10)]`) and Ada 2022 added iterated component associations
(`(for I in 1 .. 10 => I * 2)`), both filling compile-time-sized arrays.
Haskell gets there through `listArray (0,9) [i*i | i <- [0..9]]`. Rust has
no comprehension at all and reaches the same place with
`std::array::from_fn`; Julia's comprehensions do produce arrays, but Julia
is not statically typed. Nim, the backend this compiles to, cannot do it —
hence the copy above.

What is unusual is not the array case on its own but that *one* comprehension
syntax covers every container, with the annotation choosing:

```python
var asList:  []int    = [i*i for i in 0..4]     # seq / list
var asArray: [5]int   = [i*i for i in 0..4]     # stack array
var asSet:   {}int    = {i*i for i in 0..4}     # set
var asDict:  {int}int = {i: i*i for i in 0..4}  # dict
```

Fortran's implied-do and Ada's iterated aggregate are array constructors and
nothing else — neither language has a set or dict comprehension to be
consistent with. Here the four differ only in the brackets and the
annotation, which is the same scheme §2.2 sets out, used to build rather
than to declare.

Two of them join with `+`, so a list that comes from more than one source
is still one expression — §6.1 builds Sudoku's 27 units that way.

The key type can be any of the ordinals, not just a length, and the values
fill the slots in domain order. When the key is a named type, that type is
what the generator iterates:

```python
type Idx is 0 .. 4
type Off is 2 .. 6                 # a domain that does not start at zero
type Color is enum RED, GREEN, BLUE

var byIdx:  [Idx]int   = [i * 100     for i in Idx]
var byOff:  [Off]int   = [o * 10      for o in Off]     # byOff[2] is 20
var byE:    [Color]int = [ord(c) * 10 for c in Color]   # byE[RED] .. byE[BLUE]
var byBool: [bool]int  = [ord(b)      for b in bool]
```

A type is a domain, so it is something to iterate — `for c in Color` visits
`RED, GREEN, BLUE`, and `for o in Off` visits `2, 3, 4, 5, 6`. That is
worth insisting on, because the alternative is writing `for i in 0..2` and
relying on it being the right *length*: nothing in that line says which key
each value belongs to, and the two drift apart the first time a member is
added to the enum. Written this way the loop variable *is* the key, so the
value beside it is about that key by construction. `ord` gives its position
where a number is wanted (Python's builtin only takes a one-character
string; the emitter supplies the rest of the ordinals).

A length is the one key with no type to name, so `[5]int` still takes a
`0..4`.

`byOff` shows the difference between filling an array and filling a list:
its first value lands at index 2, because that is where its domain starts.
The backends have to work for this — Nim iterates `low(Off) .. high(Off)`
and offsets into the collected seq, and the Python backend zips the
comprehension against `range(2, 7)` so the dict it uses is keyed the same
way.

The same reading of a type as a domain is what makes the trie node in
`phonecode.ady` (Chapter 9) read as it does:

```python
self.children = {d: None for d in Digit_T}
```

— one entry per digit, and no way for that to be the wrong number of them.

One form is missing rather than broken: there is no keyed comprehension,
`[k: v for k in E]`, so the values are positional and cannot name their own
keys. It is a parse error on both backends, and it is in `TODO.md`.

## 6.5 Standard containers from `stdlib`

The bundled `stdlib` shim (imported with `nimport stdlib` / `from stdlib
import ...`) supplies containers Python programmers expect but Nim spells
differently:

- **`PriorityQueue[T]`** — min-heap ordered by the tuple's first element.
  `dijkstra.ady`, `shortest_path.ady` and `state_search.ady` all pivot on it:

  ```python
  from stdlib nimport PriorityQueue

  queue : PriorityQueue[Neighbour_T] = [(0.0, start)]
  while queue:
      current_dist, node = queue.pop()
      ...
      queue.push((new_dist, neighbor))
  ```

  Note `while queue:` — container truthiness ("non-empty") works as in
  Python.

- **`FifoQueue[T]`, `LifoQueue[T]`** — breadth-first vs depth-first fringes
  in `state_search.ady`.

- **`Counter_T`** — a counting dict. `spell.ady` builds its word-frequency
  model in one line and asks for `.total()`:

  ```python
  from stdlib import Counter_T

  let WORDS: Counter_T[str] = Counter_T(words(readFile(corpus_file)))
  let N: Natural = WORDS.total()
  ```

- **`ANY`** — a wildcard sentinel used by `shortest_path.ady` for "no
  explicit end state; use `is_end_state()` instead".

## 6.6 The iterator library: `nimport iters`

`EXAMPLES/test_iters.ady` exercises a bundled itertools-alike, generic over
element type, usable directly in `for` loops. It is a `nimport`, so it is
Nim-only by construction (§12.2): on the Python backend the line becomes a
comment and the names are simply undefined. Reaching for it pins the
program to one backend, which is why `sudoku.ady` writes its own `cross()`
rather than building on `product()`.

```python
nimport iters

for p in pairwise([1, 2, 3, 4]):        # (1,2) (2,3) (3,4)
    ...
for w in sliding_window([1, 2, 3, 4, 5], 3):
    ...
for x in takewhile(less_than_4, [1, 2, 3, 4, 5]):
    ...
for x in chain([1, 2], [3, 4, 5]):
    ...
for x in flatten([[1, 2], [3], [4, 5]]):
    ...
for c in combinations([1, 2, 3, 4], 2):
    ...
for p in product([1, 2], ["x", "y"]):   # mixed element types
    ...
for b in batched([1, 2, 3, 4, 5], 2):   # [1,2] [3,4] [5]
    ...
```

The full menu in the test file: `pairwise`, `sliding_window`,
`enumerate_seq`, `takewhile`, `dropwhile`, `compress`, `chain`, `flatten`,
`accumulate`, `zip_longest`, `combinations`, `permutations`, `repeat_elem`,
`count_from`, `product`, `batched`. Each is tested with both `int` and `str`
instantiations — a reminder that these are true generics in the Nim build.

## 6.7 Iteration odds and ends

- Ranges are first-class: `for i in 0 ..< 10:`, membership `if x in 1 .. 100:`.
- `for key, val in mapping.items():` and `for i, x in enumerate(xs):` work as
  in Python.
- `stdin.lines` iterates standard input (see `average_line.ady`,
  `awk_example.ady`).
- File iteration uses the familiar `with`:

  ```python
  # phonecode.ady
  with open(filename, "r") as f:
      for line in f:
          let word: str = line.strip()
          ...
  ```

- Strings iterate per character, and `str(c)` converts a char back to a
  string where the Nim backend distinguishes them. Concatenating two of
  them needs no conversion: `+` between chars is a string on both sides,
  which is why `sudoku.ady`'s `cross()` is just
  `[a + b for a in xs for b in ys]`.

- Concatenate with `+` — the Nim backend rewrites it to that language's
  `&`. Writing `&` directly is a Nim-only spelling: it is bitwise-and on
  Python and raises there, so prefer `+` in code meant for both.
  `sudoku.ady` used to use `&` throughout and so ran on one backend only;
  it now uses `+` and produces byte-identical output on both.

---

*Next: [Chapter 7 — Regular Expressions as a Language Feature](07-regex.md)*
