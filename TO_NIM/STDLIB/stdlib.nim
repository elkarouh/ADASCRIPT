## stdlib.nim -- Nim support types for HPython transpiled code
## Provides: AnyType/ANY sentinel, FifoQueue, LifoQueue, PriorityQueue, Counter,
##           Result, ShellFailure_T, OneOf2..OneOf6

import std/deques
import hashes
import tables

# ---------------------------------------------------------------------------
# Counter[K] — frequency map, like Python's collections.Counter
# ---------------------------------------------------------------------------
type Counter_T*[K] = Table[K, Natural]

proc initCounter*[K](items: openArray[K]): Counter_T[K] =
  for item in items:
    result[item] = result.getOrDefault(item, 0) + 1

proc total*[K](c: Counter_T[K]): Natural =
  for v in c.values: result += v

proc contains*[K](c: Counter_T[K]; key: K): bool = tables.hasKey(c, key)
proc `[]`*[K](c: Counter_T[K]; key: K): Natural = tables.getOrDefault(c, key, 0)
proc len*[K](c: Counter_T[K]): int = tables.len(c)

# ---------------------------------------------------------------------------
# ANY sentinel -- matches every value via ==
# ---------------------------------------------------------------------------
type AnyType* = object

func `==`*(a: AnyType; b: auto): bool = true
func `==`*(a: auto; b: AnyType): bool = true
func `==`*(a: AnyType; b: AnyType): bool = true
func isANY*(a: AnyType): bool = true
func isANY*(a: auto): bool = false
func hash*(a: AnyType): int = hash("ANY")
func `$`*(a: AnyType): string = "ANY"

const ANY* = AnyType()

# ---------------------------------------------------------------------------
# FifoQueue (FIFO)
# ---------------------------------------------------------------------------
type FifoQueue*[T] = object
  data: Deque[T]

proc initFifoQueue*[T](): FifoQueue[T] =
  result.data = initDeque[T]()

proc push*[T](q: var FifoQueue[T]; item: T) = q.data.addLast(item)
proc pop*[T](q: var FifoQueue[T]): T = q.data.popFirst()
proc len*[T](q: FifoQueue[T]): int = q.data.len
proc isEmpty*[T](q: FifoQueue[T]): bool = q.data.len == 0

# ---------------------------------------------------------------------------
# LifoQueue (Stack)
# ---------------------------------------------------------------------------
type LifoQueue*[T] = object
  data: Deque[T]

proc initLifoQueue*[T](): LifoQueue[T] =
  result.data = initDeque[T]()

proc push*[T](q: var LifoQueue[T]; item: T) = q.data.addLast(item)
proc pop*[T](q: var LifoQueue[T]): T = q.data.popLast()
proc len*[T](q: LifoQueue[T]): int = q.data.len
proc isEmpty*[T](q: LifoQueue[T]): bool = q.data.len == 0

# ---------------------------------------------------------------------------
# PriorityQueue (min-heap)
# ---------------------------------------------------------------------------
type PriorityQueue*[T] = object
  data: seq[T]

proc initPriorityQueue*[T](): PriorityQueue[T] =
  result.data = @[]

proc swap[T](q: var PriorityQueue[T]; a, b: int) =
  let tmp = q.data[a]
  q.data[a] = q.data[b]
  q.data[b] = tmp

proc siftUp[T](q: var PriorityQueue[T]; i: int) =
  var i = i
  while i > 0:
    let parent = (i - 1) shr 1
    if q.data[i][0] < q.data[parent][0]:
      q.swap(i, parent)
      i = parent
    else: break

proc siftDown[T](q: var PriorityQueue[T]; i: int) =
  let n = q.data.len
  var i = i
  while true:
    var smallest = i
    let l = 2 * i + 1
    let r = 2 * i + 2
    if l < n and q.data[l][0] < q.data[smallest][0]: smallest = l
    if r < n and q.data[r][0] < q.data[smallest][0]: smallest = r
    if smallest == i: break
    q.swap(i, smallest)
    i = smallest

proc push*[T](q: var PriorityQueue[T]; item: T) =
  q.data.add(item)
  q.siftUp(q.data.high)

proc pop*[T](q: var PriorityQueue[T]): T =
  result = q.data[0]
  q.data[0] = q.data[^1]
  q.data.setLen(q.data.high)
  if q.data.len > 0: q.siftDown(0)

proc len*[T](q: PriorityQueue[T]): int = q.data.len
proc isEmpty*[T](q: PriorityQueue[T]): bool = q.data.len == 0

# Convenience constructors with first element (for type inference)
proc newPriorityQueueWith*[T](first: T): PriorityQueue[T] =
  result.data = @[first]

proc newFifoQueueWith*[T](first: T): FifoQueue[T] =
  result.data = initDeque[T]()
  result.data.addLast(first)

proc newLifoQueueWith*[T](first: T): LifoQueue[T] =
  result.data = initDeque[T]()
  result.data.addLast(first)

# Bool converters for Python-style truthiness
converter toBool*[T](q: PriorityQueue[T]): bool = q.data.len > 0
converter toBool*[T](q: FifoQueue[T]): bool = q.data.len > 0
converter toBool*[T](q: LifoQueue[T]): bool = q.data.len > 0

# ---------------------------------------------------------------------------
# Result[T, E] -- Adascript's `T | E`: a T, or the E that says why there is
# none. Ok is the zero value, so a `None | E` proc (Result[void, E]) that
# falls off its end has succeeded, as a plain proc does. The transpiler
# writes the constructors with their type: `Result[int, string].ok(v)`,
# and reads a narrowed name as its .value or .error.
# ---------------------------------------------------------------------------
type Result*[T, E] = object
  case adaIsErr: bool
  of false: adaVal: T
  of true: adaErr: E

proc ok*[T, E](R: typedesc[Result[T, E]]; v: T): Result[T, E] =
  Result[T, E](adaIsErr: false, adaVal: v)
proc ok*[E](R: typedesc[Result[void, E]]): Result[void, E] =
  Result[void, E](adaIsErr: false)
proc err*[T, E](R: typedesc[Result[T, E]]; e: E): Result[T, E] =
  Result[T, E](adaIsErr: true, adaErr: e)

proc is_ok*[T, E](r: Result[T, E]): bool = not r.adaIsErr
proc is_err*[T, E](r: Result[T, E]): bool = r.adaIsErr

proc value*[T, E](r: Result[T, E]): T =
  ## The value of an Ok. Asking an Err for one is a bug, not a failure to
  ## handle, so it raises the way Python's backend does.
  if r.adaIsErr:
    when compiles($r.adaErr):
      raise newException(ValueError, "value of an Err: " & $r.adaErr)
    else:
      raise newException(ValueError, "value of an Err")
  r.adaVal

proc error*[T, E](r: Result[T, E]): E =
  if not r.adaIsErr:
    raise newException(ValueError, "error of an Ok")
  r.adaErr

proc value_or*[T, E](r: Result[T, E]; default: T): T =
  if r.adaIsErr: default else: r.adaVal

proc `==`*[T, E](a, b: Result[T, E]): bool =
  ## Nim derives no == for a variant object; this is Python's __eq__.
  if a.adaIsErr != b.adaIsErr: return false
  if a.adaIsErr: return a.adaErr == b.adaErr
  when T is void: true
  else: a.adaVal == b.adaVal

proc `$`*[T, E](r: Result[T, E]): string =
  ## What it holds, as Python prints the same value: a `T | E` there is
  ## just the T or the E, unboxed. Ok of nothing is None.
  if r.adaIsErr:
    when compiles($r.adaErr): $r.adaErr else: "Err"
  else:
    when T is void: "None"
    else:
      when compiles($r.adaVal): $r.adaVal else: "Ok"

# ---------------------------------------------------------------------------
# ShellFailure_T -- the built-in failure of a shell command: what ran, the
# status it ended with, and what it said on stderr. `let out: str |
# ShellFailure_T = shell: cmd` holds the output, or this.
# ---------------------------------------------------------------------------
type ShellFailure_T* = object
  command*: string
  code*: int
  stderr*: string

# ---------------------------------------------------------------------------
# PathFailure_T -- the built-in failure of a Path operation that can fail:
# `p.relative_to(base)` is a `Path | !PathFailure_T` and `p.mkdir()` a
# `None | !PathFailure_T`. It says which operation (`op`), on which path, with
# which base (`relative_to` only, else ""), and why (`reason`: the system's
# words for a mkdir, "" for relative_to, whose reason is the base).
# ---------------------------------------------------------------------------
type PathFailure_T* = object
  op*: string
  path*: string
  base*: string
  reason*: string

# ---------------------------------------------------------------------------
# ParseFailure_T -- the built-in failure of a conversion from text:
# `parse_float(s)` is a `float | !ParseFailure_T`, `parse_int(s)` an
# `int | !ParseFailure_T` and `parse_enum(E, s)` an `E | !ParseFailure_T`. It
# says what was being read (`what`: "float", "int", or the enum's name) and the text that was not one (`text`).
# ---------------------------------------------------------------------------
type ParseFailure_T* = object
  what*: string
  text*: string

# ---------------------------------------------------------------------------
# OneOf2..OneOf6 -- Adascript's plain union, `int | float | str`: one of its
# members, which member told by `which`. The transpiler writes the
# constructors with their type -- `OneOf2[int, float].of1(2.5)` -- tests a
# member with `is_m1` and reads it with `m1` once a test has narrowed it.
# Member 0 is the zero value, as a plain variable's is. A union with a
# failure member is a Result whose value is one of these: `is_v1` / `v1`.
# (Generated, one block per arity.)
# ---------------------------------------------------------------------------

type OneOf2*[T0, T1] = object
  case adaWhich: range[0..1]
  of 0: adaM0: T0
  of 1: adaM1: T1
proc of0*[T0, T1](U: typedesc[OneOf2[T0, T1]]; v: T0): OneOf2[T0, T1] = OneOf2[T0, T1](adaWhich: 0, adaM0: v)
proc is_m0*[T0, T1](u: OneOf2[T0, T1]): bool = u.adaWhich == 0
proc m0*[T0, T1](u: OneOf2[T0, T1]): T0 =
  if u.adaWhich != 0: raise newException(ValueError, "member 0 of a union holding member " & $u.adaWhich)
  u.adaM0
proc is_v0*[T0, T1, Err](r: Result[OneOf2[T0, T1], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 0
proc v0*[T0, T1, Err](r: Result[OneOf2[T0, T1], Err]): T0 = r.value.m0
proc of1*[T0, T1](U: typedesc[OneOf2[T0, T1]]; v: T1): OneOf2[T0, T1] = OneOf2[T0, T1](adaWhich: 1, adaM1: v)
proc is_m1*[T0, T1](u: OneOf2[T0, T1]): bool = u.adaWhich == 1
proc m1*[T0, T1](u: OneOf2[T0, T1]): T1 =
  if u.adaWhich != 1: raise newException(ValueError, "member 1 of a union holding member " & $u.adaWhich)
  u.adaM1
proc is_v1*[T0, T1, Err](r: Result[OneOf2[T0, T1], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 1
proc v1*[T0, T1, Err](r: Result[OneOf2[T0, T1], Err]): T1 = r.value.m1
proc `$`*[T0, T1](u: OneOf2[T0, T1]): string =
  case u.adaWhich
  of 0: (when compiles($u.adaM0): $u.adaM0 else: "member 0")
  of 1: (when compiles($u.adaM1): $u.adaM1 else: "member 1")
proc `==`*[T0, T1](a, b: OneOf2[T0, T1]): bool =
  if a.adaWhich != b.adaWhich: return false
  case a.adaWhich
  of 0: a.adaM0 == b.adaM0
  of 1: a.adaM1 == b.adaM1

type OneOf3*[T0, T1, T2] = object
  case adaWhich: range[0..2]
  of 0: adaM0: T0
  of 1: adaM1: T1
  of 2: adaM2: T2
proc of0*[T0, T1, T2](U: typedesc[OneOf3[T0, T1, T2]]; v: T0): OneOf3[T0, T1, T2] = OneOf3[T0, T1, T2](adaWhich: 0, adaM0: v)
proc is_m0*[T0, T1, T2](u: OneOf3[T0, T1, T2]): bool = u.adaWhich == 0
proc m0*[T0, T1, T2](u: OneOf3[T0, T1, T2]): T0 =
  if u.adaWhich != 0: raise newException(ValueError, "member 0 of a union holding member " & $u.adaWhich)
  u.adaM0
proc is_v0*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 0
proc v0*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): T0 = r.value.m0
proc of1*[T0, T1, T2](U: typedesc[OneOf3[T0, T1, T2]]; v: T1): OneOf3[T0, T1, T2] = OneOf3[T0, T1, T2](adaWhich: 1, adaM1: v)
proc is_m1*[T0, T1, T2](u: OneOf3[T0, T1, T2]): bool = u.adaWhich == 1
proc m1*[T0, T1, T2](u: OneOf3[T0, T1, T2]): T1 =
  if u.adaWhich != 1: raise newException(ValueError, "member 1 of a union holding member " & $u.adaWhich)
  u.adaM1
proc is_v1*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 1
proc v1*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): T1 = r.value.m1
proc of2*[T0, T1, T2](U: typedesc[OneOf3[T0, T1, T2]]; v: T2): OneOf3[T0, T1, T2] = OneOf3[T0, T1, T2](adaWhich: 2, adaM2: v)
proc is_m2*[T0, T1, T2](u: OneOf3[T0, T1, T2]): bool = u.adaWhich == 2
proc m2*[T0, T1, T2](u: OneOf3[T0, T1, T2]): T2 =
  if u.adaWhich != 2: raise newException(ValueError, "member 2 of a union holding member " & $u.adaWhich)
  u.adaM2
proc is_v2*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 2
proc v2*[T0, T1, T2, Err](r: Result[OneOf3[T0, T1, T2], Err]): T2 = r.value.m2
proc `$`*[T0, T1, T2](u: OneOf3[T0, T1, T2]): string =
  case u.adaWhich
  of 0: (when compiles($u.adaM0): $u.adaM0 else: "member 0")
  of 1: (when compiles($u.adaM1): $u.adaM1 else: "member 1")
  of 2: (when compiles($u.adaM2): $u.adaM2 else: "member 2")
proc `==`*[T0, T1, T2](a, b: OneOf3[T0, T1, T2]): bool =
  if a.adaWhich != b.adaWhich: return false
  case a.adaWhich
  of 0: a.adaM0 == b.adaM0
  of 1: a.adaM1 == b.adaM1
  of 2: a.adaM2 == b.adaM2

type OneOf4*[T0, T1, T2, T3] = object
  case adaWhich: range[0..3]
  of 0: adaM0: T0
  of 1: adaM1: T1
  of 2: adaM2: T2
  of 3: adaM3: T3
proc of0*[T0, T1, T2, T3](U: typedesc[OneOf4[T0, T1, T2, T3]]; v: T0): OneOf4[T0, T1, T2, T3] = OneOf4[T0, T1, T2, T3](adaWhich: 0, adaM0: v)
proc is_m0*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): bool = u.adaWhich == 0
proc m0*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): T0 =
  if u.adaWhich != 0: raise newException(ValueError, "member 0 of a union holding member " & $u.adaWhich)
  u.adaM0
proc is_v0*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 0
proc v0*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): T0 = r.value.m0
proc of1*[T0, T1, T2, T3](U: typedesc[OneOf4[T0, T1, T2, T3]]; v: T1): OneOf4[T0, T1, T2, T3] = OneOf4[T0, T1, T2, T3](adaWhich: 1, adaM1: v)
proc is_m1*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): bool = u.adaWhich == 1
proc m1*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): T1 =
  if u.adaWhich != 1: raise newException(ValueError, "member 1 of a union holding member " & $u.adaWhich)
  u.adaM1
proc is_v1*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 1
proc v1*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): T1 = r.value.m1
proc of2*[T0, T1, T2, T3](U: typedesc[OneOf4[T0, T1, T2, T3]]; v: T2): OneOf4[T0, T1, T2, T3] = OneOf4[T0, T1, T2, T3](adaWhich: 2, adaM2: v)
proc is_m2*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): bool = u.adaWhich == 2
proc m2*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): T2 =
  if u.adaWhich != 2: raise newException(ValueError, "member 2 of a union holding member " & $u.adaWhich)
  u.adaM2
proc is_v2*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 2
proc v2*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): T2 = r.value.m2
proc of3*[T0, T1, T2, T3](U: typedesc[OneOf4[T0, T1, T2, T3]]; v: T3): OneOf4[T0, T1, T2, T3] = OneOf4[T0, T1, T2, T3](adaWhich: 3, adaM3: v)
proc is_m3*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): bool = u.adaWhich == 3
proc m3*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): T3 =
  if u.adaWhich != 3: raise newException(ValueError, "member 3 of a union holding member " & $u.adaWhich)
  u.adaM3
proc is_v3*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 3
proc v3*[T0, T1, T2, T3, Err](r: Result[OneOf4[T0, T1, T2, T3], Err]): T3 = r.value.m3
proc `$`*[T0, T1, T2, T3](u: OneOf4[T0, T1, T2, T3]): string =
  case u.adaWhich
  of 0: (when compiles($u.adaM0): $u.adaM0 else: "member 0")
  of 1: (when compiles($u.adaM1): $u.adaM1 else: "member 1")
  of 2: (when compiles($u.adaM2): $u.adaM2 else: "member 2")
  of 3: (when compiles($u.adaM3): $u.adaM3 else: "member 3")
proc `==`*[T0, T1, T2, T3](a, b: OneOf4[T0, T1, T2, T3]): bool =
  if a.adaWhich != b.adaWhich: return false
  case a.adaWhich
  of 0: a.adaM0 == b.adaM0
  of 1: a.adaM1 == b.adaM1
  of 2: a.adaM2 == b.adaM2
  of 3: a.adaM3 == b.adaM3

type OneOf5*[T0, T1, T2, T3, T4] = object
  case adaWhich: range[0..4]
  of 0: adaM0: T0
  of 1: adaM1: T1
  of 2: adaM2: T2
  of 3: adaM3: T3
  of 4: adaM4: T4
proc of0*[T0, T1, T2, T3, T4](U: typedesc[OneOf5[T0, T1, T2, T3, T4]]; v: T0): OneOf5[T0, T1, T2, T3, T4] = OneOf5[T0, T1, T2, T3, T4](adaWhich: 0, adaM0: v)
proc is_m0*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): bool = u.adaWhich == 0
proc m0*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): T0 =
  if u.adaWhich != 0: raise newException(ValueError, "member 0 of a union holding member " & $u.adaWhich)
  u.adaM0
proc is_v0*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 0
proc v0*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): T0 = r.value.m0
proc of1*[T0, T1, T2, T3, T4](U: typedesc[OneOf5[T0, T1, T2, T3, T4]]; v: T1): OneOf5[T0, T1, T2, T3, T4] = OneOf5[T0, T1, T2, T3, T4](adaWhich: 1, adaM1: v)
proc is_m1*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): bool = u.adaWhich == 1
proc m1*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): T1 =
  if u.adaWhich != 1: raise newException(ValueError, "member 1 of a union holding member " & $u.adaWhich)
  u.adaM1
proc is_v1*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 1
proc v1*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): T1 = r.value.m1
proc of2*[T0, T1, T2, T3, T4](U: typedesc[OneOf5[T0, T1, T2, T3, T4]]; v: T2): OneOf5[T0, T1, T2, T3, T4] = OneOf5[T0, T1, T2, T3, T4](adaWhich: 2, adaM2: v)
proc is_m2*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): bool = u.adaWhich == 2
proc m2*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): T2 =
  if u.adaWhich != 2: raise newException(ValueError, "member 2 of a union holding member " & $u.adaWhich)
  u.adaM2
proc is_v2*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 2
proc v2*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): T2 = r.value.m2
proc of3*[T0, T1, T2, T3, T4](U: typedesc[OneOf5[T0, T1, T2, T3, T4]]; v: T3): OneOf5[T0, T1, T2, T3, T4] = OneOf5[T0, T1, T2, T3, T4](adaWhich: 3, adaM3: v)
proc is_m3*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): bool = u.adaWhich == 3
proc m3*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): T3 =
  if u.adaWhich != 3: raise newException(ValueError, "member 3 of a union holding member " & $u.adaWhich)
  u.adaM3
proc is_v3*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 3
proc v3*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): T3 = r.value.m3
proc of4*[T0, T1, T2, T3, T4](U: typedesc[OneOf5[T0, T1, T2, T3, T4]]; v: T4): OneOf5[T0, T1, T2, T3, T4] = OneOf5[T0, T1, T2, T3, T4](adaWhich: 4, adaM4: v)
proc is_m4*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): bool = u.adaWhich == 4
proc m4*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): T4 =
  if u.adaWhich != 4: raise newException(ValueError, "member 4 of a union holding member " & $u.adaWhich)
  u.adaM4
proc is_v4*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 4
proc v4*[T0, T1, T2, T3, T4, Err](r: Result[OneOf5[T0, T1, T2, T3, T4], Err]): T4 = r.value.m4
proc `$`*[T0, T1, T2, T3, T4](u: OneOf5[T0, T1, T2, T3, T4]): string =
  case u.adaWhich
  of 0: (when compiles($u.adaM0): $u.adaM0 else: "member 0")
  of 1: (when compiles($u.adaM1): $u.adaM1 else: "member 1")
  of 2: (when compiles($u.adaM2): $u.adaM2 else: "member 2")
  of 3: (when compiles($u.adaM3): $u.adaM3 else: "member 3")
  of 4: (when compiles($u.adaM4): $u.adaM4 else: "member 4")
proc `==`*[T0, T1, T2, T3, T4](a, b: OneOf5[T0, T1, T2, T3, T4]): bool =
  if a.adaWhich != b.adaWhich: return false
  case a.adaWhich
  of 0: a.adaM0 == b.adaM0
  of 1: a.adaM1 == b.adaM1
  of 2: a.adaM2 == b.adaM2
  of 3: a.adaM3 == b.adaM3
  of 4: a.adaM4 == b.adaM4

type OneOf6*[T0, T1, T2, T3, T4, T5] = object
  case adaWhich: range[0..5]
  of 0: adaM0: T0
  of 1: adaM1: T1
  of 2: adaM2: T2
  of 3: adaM3: T3
  of 4: adaM4: T4
  of 5: adaM5: T5
proc of0*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T0): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 0, adaM0: v)
proc is_m0*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 0
proc m0*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T0 =
  if u.adaWhich != 0: raise newException(ValueError, "member 0 of a union holding member " & $u.adaWhich)
  u.adaM0
proc is_v0*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 0
proc v0*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T0 = r.value.m0
proc of1*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T1): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 1, adaM1: v)
proc is_m1*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 1
proc m1*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T1 =
  if u.adaWhich != 1: raise newException(ValueError, "member 1 of a union holding member " & $u.adaWhich)
  u.adaM1
proc is_v1*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 1
proc v1*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T1 = r.value.m1
proc of2*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T2): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 2, adaM2: v)
proc is_m2*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 2
proc m2*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T2 =
  if u.adaWhich != 2: raise newException(ValueError, "member 2 of a union holding member " & $u.adaWhich)
  u.adaM2
proc is_v2*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 2
proc v2*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T2 = r.value.m2
proc of3*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T3): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 3, adaM3: v)
proc is_m3*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 3
proc m3*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T3 =
  if u.adaWhich != 3: raise newException(ValueError, "member 3 of a union holding member " & $u.adaWhich)
  u.adaM3
proc is_v3*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 3
proc v3*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T3 = r.value.m3
proc of4*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T4): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 4, adaM4: v)
proc is_m4*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 4
proc m4*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T4 =
  if u.adaWhich != 4: raise newException(ValueError, "member 4 of a union holding member " & $u.adaWhich)
  u.adaM4
proc is_v4*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 4
proc v4*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T4 = r.value.m4
proc of5*[T0, T1, T2, T3, T4, T5](U: typedesc[OneOf6[T0, T1, T2, T3, T4, T5]]; v: T5): OneOf6[T0, T1, T2, T3, T4, T5] = OneOf6[T0, T1, T2, T3, T4, T5](adaWhich: 5, adaM5: v)
proc is_m5*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): bool = u.adaWhich == 5
proc m5*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): T5 =
  if u.adaWhich != 5: raise newException(ValueError, "member 5 of a union holding member " & $u.adaWhich)
  u.adaM5
proc is_v5*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): bool = not r.adaIsErr and r.adaVal.adaWhich == 5
proc v5*[T0, T1, T2, T3, T4, T5, Err](r: Result[OneOf6[T0, T1, T2, T3, T4, T5], Err]): T5 = r.value.m5
proc `$`*[T0, T1, T2, T3, T4, T5](u: OneOf6[T0, T1, T2, T3, T4, T5]): string =
  case u.adaWhich
  of 0: (when compiles($u.adaM0): $u.adaM0 else: "member 0")
  of 1: (when compiles($u.adaM1): $u.adaM1 else: "member 1")
  of 2: (when compiles($u.adaM2): $u.adaM2 else: "member 2")
  of 3: (when compiles($u.adaM3): $u.adaM3 else: "member 3")
  of 4: (when compiles($u.adaM4): $u.adaM4 else: "member 4")
  of 5: (when compiles($u.adaM5): $u.adaM5 else: "member 5")
proc `==`*[T0, T1, T2, T3, T4, T5](a, b: OneOf6[T0, T1, T2, T3, T4, T5]): bool =
  if a.adaWhich != b.adaWhich: return false
  case a.adaWhich
  of 0: a.adaM0 == b.adaM0
  of 1: a.adaM1 == b.adaM1
  of 2: a.adaM2 == b.adaM2
  of 3: a.adaM3 == b.adaM3
  of 4: a.adaM4 == b.adaM4
  of 5: a.adaM5 == b.adaM5
