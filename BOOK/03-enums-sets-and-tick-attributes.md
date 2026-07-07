# Chapter 3 — Enums, Sets, and Tick Attributes

If Adascript has a heart, it is here. The README's manifesto says it
plainly: Pascal set the base minimum for systems languages — an enumerated
type must be usable *wherever an ordinal type is accepted*: as an array
index, as a loop range, as a set element. Adascript restores that minimum on
top of Python syntax.

## 3.1 Declaring enums

```python
type Color   is enum RED, GREEN, BLUE
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9
```

Both `is` and `=` are accepted. Multi-line bodies with per-member comments
work too — `EXAMPLES/lv.ady` documents a workflow state machine this way:

```python
type State = enum:
    ACTIVE        # being worked on
    OPS_BUG       # blocked by an ops/infra bug
    BUSY          # build/test running
    DONE          # work finished, awaiting review
    BLOCKED       # blocked by a dependency
    ON_HOLD       # paused
    IDLE          # no activity
    BACKGROUND    # low-priority background task
    INTEGRATED    # merged into the integration branch
    MERGED        # merged to mainline
    REJECTED      # change rejected
```

The Python backend emits `class State(Enum)` with `auto()` members; the Nim
backend emits a native `enum`. Members are referenced *bare* (`ACTIVE`, not
`State.ACTIVE`) and the transpiler qualifies them where the target needs it.

Calling an enum type with a string parses the string into a member — useful
for reading states from files, as `lv.ady` does:

```python
def parse_state(s: str) -> State:
    try:
        State(s.replace("-", "_"))
    except:
        ACTIVE
```

(In Nim this becomes `parseEnum[State](...)`; note also the implicit return
of the last expression in each branch — Chapter 8.)

## 3.2 Enums as array indexes: `[E]T`

An array indexed by an enum is declared `[E]T` and initialised with the
`[KEY: value, ...]` literal:

```python
type Priority is enum LOW, MED, HIGH
var costs: [Priority]int = [LOW: 1, MED: 5, HIGH: 10]
```

In Nim this is `array[Priority, int]` — a fixed-size, stack-allocated array
with O(1) indexing and *no hashing*. In Python it becomes a dict keyed by
enum members. `EXAMPLES/awk_example.ady` tallies log-line severities in one:

```python
type Severity_T is enum INFO, WARN, ERROR, OTHER
var counts : [Severity_T]Natural = [INFO : 0, WARN : 0, ERROR : 0, OTHER: 0]
...
counts[sev] += 1
```

and `EXAMPLES/phonecode.ady` builds a trie whose children are indexed by a
digit enum — ten slots per node, no dictionary overhead in the Nim build:

```python
type Digit_T is enum D0, D1, D2, D3, D4, D5, D6, D7, D8, D9

class TrieNode:
    var children: [Digit_T]TrieNode
    var words: []str
```

## 3.3 Enums as loop ranges

Iterating over a whole enum requires no ceremony:

```python
for s in Severity_T:          # every member, in declaration order
    print f"  {s:<6} {counts[s]}"
```

or, when you want to be explicit about bounds, the Ada way:

```python
for s in Stage_T'First .. Stage_T'Last:
    ...
```

## 3.4 Ordinal sets: `{}E`

A set whose element type is ordinal (an enum, `bool`, `char`, a small int
range) compiles to Nim's bitset `set[T]` — one machine word, constant-time
membership, and set arithmetic with `-`, `+`, `*`. The canonical
demonstration is `EXAMPLES/monty_hall.ady`, which is worth reading whole:

```python
#!/usr/bin/env py2nim

type Door_T is enum Door1, Door2, Door3
type Choice_T is enum Switch, DontSwitch

def monty_hall_simulation(trials=100_000):
  var stayWins : Natural = 0
  var switchWins : Natural = 0

  for _ in 1..trials:
    let carLocation : Door_T = Door_T'Choice
    let candidateFirstChoice : Door_T = Door_T'Choice
    let availableDoors : {}Door_T = Door_T'Range - {candidateFirstChoice, carLocation}
    let hostChoice : Door_T = availableDoors'Choice
    let switchOptions : {}Door_T = Door_T'Range - {candidateFirstChoice, hostChoice}
    for choice in Choice_T:
      case choice:
        when DontSwitch:
          if candidateFirstChoice == carLocation:
            stayWins += 1
        when Switch:
          let candidateSecondChoice : Door_T = switchOptions'Choice
          if candidateSecondChoice == carLocation:
              switchWins += 1

  print "Trials: ", trials
  print f"Stay:   {stayWins} wins ({stayWins * 100 / trials} %)"
  print f"Switch: {switchWins} wins ({switchWins * 100 / trials} %)"

monty_hall_simulation()
```

The problem's logic *is* set algebra, and the code says so directly:

- `Door_T'Range` — the full set of doors;
- `- {candidateFirstChoice, carLocation}` — set difference with a set
  literal: the doors the host may open;
- `availableDoors'Choice` — a uniformly random element of that set.

Compare this with the bookkeeping any conventional implementation needs
(lists, `random.choice`, membership scans) and the appeal of ordinal types
is obvious.

## 3.5 Tick attributes

The `'` attribute syntax gives first-class access to type and value
metadata. The tokenizer rewrites `Type'Attr` internally before parsing, so
the apostrophe never confuses the Python-shaped grammar.

| Expression | Meaning |
|------------|---------|
| `E'First` | first member of enum `E` |
| `E'Last` | last member |
| `E'Range` | the set (or iteration range) of all members |
| `expr'Next` | successor |
| `expr'Prev` | predecessor |
| `expr'Choice` | uniformly random element of an enum, set, or range |
| `expr'Image` | string representation |
| `s'Length` | length of a string/sequence |

They work on more than enums. `EXAMPLES/floyd.ady` — Floyd's algorithm for
sampling k distinct integers — applies `'Choice` to a *range expression*:

```python
def floyd(n : Positive, k : Positive) -> {}Positive:
    s : {}Positive
    for i in n-k+1..n:
        t = (1..i)'Choice          # random integer in 1..i
        if t in s:
            s.add(i)
        else:
            s.add(t)
    return s

let sample : {}Positive = floyd(100, 10)
print "10 distinct numbers from 1..100: ", sample
```

`prisoners.ady` applies `'Shuffle` to an enum-indexed array and `'Range` to
a subrange type:

```python
def make_boxes() -> [Prisoner_T]Box_T:
    var boxes: [Prisoner_T]Box_T
    for i in Prisoner_T'Range:
        boxes[i] = i
    boxes'Shuffle                      # in-place shuffle; also the implicit return
```

and `average_line.ady` uses `line'Length` on a plain string. Stepping
through an enum uses `'Next` — here from `EXAMPLES/test_shortest_path.ady`,
advancing a knapsack solver to its next stage:

```python
def get_next_state(self, current_state: State_T, decision: Decision_T) -> State_T:
    let (stage, remaining) = current_state
    let used: Natural = decision.quantity * ITEMS[decision.stage].weight
    (decision.stage'Next, remaining - used)
```

**Limitation:** tick attributes attach to bare identifiers and type names
only — `self.num'Image` and `args[0]'Image` do not parse. Bind the value to
a local first, or use `str()`.

## 3.6 Why this matters: a checklist

When you model a domain in Adascript, reach for an enum early, because one
declaration buys all of this at once:

1. a `case`/`when` dispatch subject with exhaustiveness in Nim (Chapter 5);
2. an array index type (`[E]T`) — fixed-size lookup tables, no hashing;
3. a loop range (`for x in E:` / `E'First .. E'Last`);
4. a bitset element type (`{}E`) with `-`, `+`, `in`;
5. random sampling (`E'Choice`) for simulations;
6. ordered navigation (`'Next`, `'Prev`) for stage machines.

The examples keep proving the point: doors (`monty_hall`), digits
(`phonecode`), severities (`awk_example`), workflow states (`lv`), decisions
(`test_shortest_path`: `BUY, SELL, KEEP, TRADE`), compass actions
(`td_learning/qlearning.ady`: `UP, RIGHT, DOWN, LEFT`).

---

*Next: [Chapter 4 — Tuples, Records, and Variant Records](04-tuples-records-and-variants.md)*
