# Bug: `__init__` cannot call other methods of the same class

## Summary

When a class `__init__` calls another method of the same class via `self.method()`,
the transpiler emits the called method's Nim proc **after** the generated `initX` /
`newX` procs. Nim is single-pass, so the call is unresolved at the point it appears.
If a stdlib proc with the same name exists it is picked up instead (giving a confusing
type-mismatch error); if no same-named proc exists the error is "undeclared routine".

This is valid Python and should transpile correctly.

## Minimal reproducer

```adascript
nimport os          # brings proc resolve*(p: Path): Path into scope

class Config:
    path : Path = Path(".")

    def __init__(self, p: str):
        self.path = Path(p)
        self.resolve()          # calls the method below

    def resolve(self):
        self.path = self.path / "extra"

let c: Config = Config("/tmp")
print str(c.path)
```

Save as `bug.ady` and run:

```
ady2nim c bug.ady -o bug
```

## Actual error

```
bug.nim(62, 9) Error: type mismatch
Expression: resolve(self)
  [1] self: Config

Expected one of (first mismatch at [position]):
[1] proc resolve(p: Path): Path
```

## Generated Nim (annotated)

```nim
proc resolve*(p: Path): Path =   # line 40 — from nimport os
  ...

proc initConfig(self: var Config, p: string) =   # line 59 — __init__ body
    self.path = Path(".")
    self.path = Path(p)
    self.resolve()               # line 62 — Config.resolve not visible yet;
                                 # Nim picks up Path.resolve instead → type mismatch

proc newConfig*(p: string): Config =   # line 64
    initConfig(result, p)

proc resolve(self: var Config) =   # line 66 — defined TOO LATE
    self.path = self.path / "extra"
```

## Root cause

The transpiler emits `initX` / `newX` (from `__init__`) before any other methods of
the class. Methods called via `self.xxx()` inside `__init__` therefore appear in the
Nim output after their call site.

Two failure modes:

| Situation | Nim error |
|-----------|-----------|
| A stdlib proc with the same name is in scope | `type mismatch` (wrong proc selected) |
| No other proc with that name exists | `attempting to call undeclared routine` |

## Workaround

Inline the called method's body directly inside `__init__` to eliminate the
forward-reference. This was required in `Pgrep.ady` to make `Options.__init__` work.

## Expected fix

When the transpiler generates `initX` / `newX` for a class, it should scan the
`__init__` body for `self.method()` calls, collect those method procs, and emit
them **before** `initX` in the Nim output — or emit a Nim forward declaration:

```nim
proc resolve(self: var Config)   # forward declaration — before initConfig
```

This mirrors how Python resolves method names at call time rather than at
definition time.
