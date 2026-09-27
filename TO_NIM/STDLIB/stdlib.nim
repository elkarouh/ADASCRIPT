## stdlib.nim -- Nim support types for HPython transpiled code
## Provides: AnyType/ANY sentinel, FifoQueue, LifoQueue, PriorityQueue, Counter,
##           Result, ShellFailure_T

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
