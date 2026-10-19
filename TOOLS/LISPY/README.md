# lispy — four versions of a Scheme interpreter

All four are Peter Norvig's [lis.py](https://norvig.com/lispy.html) in one form
or another. They differ in how much Scheme they do and in how a Scheme value is
typed.

| File | What it is | Lines (code only) | Scheme value is |
|---|---|---|---|
| `lispy.py` | Norvig's original, unchanged | 144 (117) | a plain Python `str`, `list` or number |
| `lispy_short.ady` | Adascript, lis.py's features and no more | 241 (202) | a **union** of records |
| `lispy.ady` | Adascript, the full interpreter | 899 (782) | a **variant record** |
| `lispy_union.ady` | Adascript, the full interpreter | 894 (770) | a **union** of records |

"Code only" leaves out blank lines and comment lines. `lispy_short.ady` carries
about 45 lines of self-test and REPL that `lispy.py` has no equivalent of; the
interpreter itself is about 160.

## Which to read

- **`lispy.py`** — the baseline, and the smallest. It has no types: a number is
  a number, a symbol is a `str`, a list is a `list`.
- **`lispy_short.ady`** — read this to compare Adascript with Python line for
  line. Same features as `lispy.py`, with the value declared.
- **`lispy.ady` and `lispy_union.ady`** — the same interpreter written twice,
  to compare the two ways Adascript has of saying "a value is one of several
  shapes". Read them side by side.

## Features

`lispy.py` and `lispy_short.ady`: numbers, symbols, lists; `quote`, `if`,
`define`, `set!`, `lambda` and procedure calls; `+ - * / > < >= <= =`, `abs`,
`append`, `apply`, `begin`, `car`, `cdr`, `cons`, `eq?`, `equal?`, `length`,
`list`, `list?`, `map`, `max`, `min`, `not`, `null?`, `number?`, `procedure?`,
`round`, `symbol?`, and a few of `math` (`sqrt`, `sin`, `cos`, `pi`).

`lispy.ady` and `lispy_union.ady` add strings, `cond`, `let`, `let*`, `letrec`,
named `let`, `do`, `when`, `unless`, `and`, `or`, `quasiquote`, `for-each`,
variadic lambdas (`(lambda args ...)`, `(a . rest)`), tail-call optimisation
(a tail-recursive loop of any depth does not overflow the stack), variadic
arithmetic, about 80 built-ins, a reader that returns a failure instead of
raising, and Scheme errors that stop with a message.

## Variant record or union

`lispy.ady`:

```python
type Val_Kind_T is enum:
    VNum
    VSym
    ...

type Val_T (kind: Val_Kind_T) is record:
    case kind is
        when VNum:
            num: float
        when VSym:
            sym: str
        ...
```

One record with a tag. A value is built and matched by its kind alone,
`VNum(3.0)`, `[VSym("if"), test, *rest]`.

`lispy_union.ady` and `lispy_short.ady`:

```python
type Num_T is record:
    num: float
type Sym_T is record:
    sym: str
...
type Val_T is Num_T | Sym_T | Str_T | Bool_T | Nil_T | List_T | Lambda | Builtin_T
```

One record per kind, and the union is the type. There is no tag to name: the
type says which it is. A value is built and matched by its type,
`Num_T(3.0)`, `[Sym_T("if"), test, *rest]`; `x is Sym_T` asks which, and
`x.num` reads the field of the one member that has it (and stops the program
if `x` holds another).

What the union version asks of the code, and what it saves:

- The kind enum goes; seven small record declarations take its place, so the
  two are about the same length. The interpreter proper is the same.
- Each kind of value must be a type of its own. `Sym_T` and `Str_T` both hold a
  string, and a union of `str | str` would not say which, so each is a record.
- A user-defined procedure (`Lambda`, a class) is a member of the union as it
  is; the variant record needed a `lam:` field to hold it.
- On Nim a union is `OneOf8[...]` from `stdlib.nim`, a variant object much like
  the first; the difference is in the source, not in the speed.
- A record that holds itself (`List_T` holds a list of `Val_T`) is a reference
  on Nim, and the transpiler gives it a field-by-field `==`, so
  `(equal? (list 1 2) (list 1 2))` is true as it is on Python.

## Running

```
ady2nim c -r TOOLS/LISPY/lispy_union.ady             # self-test, then a prompt
ady2nim c -r TOOLS/LISPY/lispy_union.ady -- prog.scm # run a file
make test-part-28                                    # the self-tests of the Adascript ones
```

`lispy.py` is the original and is not run by the tests: its REPL uses
`raw_input`, which is Python 2.

The Adascript versions run their self-test first (`lispy: all tests passed`)
and then offer a `lispy>` prompt; `:q` leaves it. The Nim backend is the one
these are written for.
