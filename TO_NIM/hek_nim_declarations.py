#!/usr/bin/env python3
"""Nim translation methods for ADASCRIPT type declarations.

Adds to_nim() methods to the type declaration parser classes defined in
hek_py_declarations.py. Import this module to enable .to_nim() on type AST nodes.

Usage:
    from hek_nim_declarations import *
    ast = parse_type("[]?int")
    print(ast.to_nim())  # seq[Option[int]]
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))
# (no TO_PYTHON dependency needed)

from hek_parsec import method, ParserState
from ady_declarations import *  # noqa: F403 — need all parser rule names
from ady_declarations import parse_type
from ady_stmt import subrange_array_type  # noqa: F401 — defined after ady_declarations

###############################################################################
# to_nim() methods
###############################################################################

_PY_TO_NIM = {
    "int": "int",
    "str": "string",
    "float": "float",
    "bool": "bool",
    "bytes": "seq[byte]",
    "None": "void",
    "list": "seq",
    "object": "auto",
    # What run() and the shell forms hand back.  The shell forms infer it, so
    # the name is only needed where a binding must be annotated:
    # `let r: RunResult = run(argv)`.
    "RunResult": "tuple[output: string, stderr: string, code: int]",
    # The handle shellSpawn returns, so `let jobs: []Job = @[]` can name it.
    "Job": "AdascriptJob",
    # std/paths already has it, with `/` defined; see _ensure_path_helper for
    # the converter that keeps it usable everywhere a string is.
    "Path": "Path",
}

# Nim ordinal types — eligible for built-in set[T]
_NIM_ORDINALS = {
    "int8", "int16",
    "uint8", "uint16",
    "char", "bool", "byte", "enum",
}


def _is_nim_ordinal(nim_type):
    """Return True if nim_type is an ordinal type (eligible for set[T])."""
    if nim_type in _NIM_ORDINALS:
        return True
    # Check symbol table for user-defined enum types
    info = ParserState.symbol_table.lookup(nim_type)
    return info is not None and info.get("type") == "enum"


@method(primitive_type)
def to_nim(self, prec=None):
    """primitive_type: 'int' | 'str' | 'float' | 'bool' | 'bytes' | 'None' -> Nim: str->string, bytes->seq[byte], None->void"""
    name = self.nodes[0]
    return _PY_TO_NIM.get(name, name)


_PATH_HELPER = """\
proc `/`*(head: Path, tail: string): Path = head / Path(tail)
  ## Joining a Path with a plain string keeps it a Path. Without these two,
  ## overload resolution takes the converter below, finds the string `/`, and
  ## hands back a string -- while the Python backend returns a Path. The two
  ## backends have to agree on the type of `d / "sub"`.
proc `/`*(head: string, tail: Path): Path = Path(head) / tail

converter adascriptPathToString*(p: Path): string = p.string
  ## Path is `distinct string` in std/paths, so without this every use of one
  ## where a string belongs -- readFile, string concatenation, a proc taking
  ## string -- would need an explicit `.string`. The converter is what lets a
  ## Path be passed anywhere a str is, which is what the Python backend gets
  ## for free by making Path a str subclass. The two backends have to agree.

proc parent*(p: Path): Path =
  ## The directory holding p -- "." when there is none.
  ## parentDir already agrees with Python's pathlib on every path that names
  ## a file; it returns "" only for the four navigation-only inputs "/", "",
  ## "." and "..", where pathlib answers "/" for the first and "." for the
  ## rest. That is the whole difference, so that is all this fixes up.
  result = p.parentDir
  if result.string.len == 0:
    result = if p.isAbsolute: Path("/") else: Path(".")

proc name*(p: Path): string =
  ## The last component of p, with no directory part.
  ## lastPathPart matches pathlib everywhere except on "." itself, which it
  ## reports as "." where pathlib reports no name at all.
  result = p.lastPathPart.string
  if result == ".":
    result = ""

proc resolve*(p: Path): Path =
  ## The absolute path, with every symlink along it expanded.
  ## expandFilename does this in one call but raises when the path does not
  ## exist, where Python's realpath expands as much of it as does exist and
  ## keeps the rest. Matching that costs the two fallbacks below and makes
  ## the backends agree on a path that is only about to be created, on a
  ## broken link, and on one reached through a symlinked directory.
  if fileExists(p.string) or dirExists(p.string):
    return Path(expandFilename(p.string))
  if symlinkExists(p.string):
    let target = Path(expandSymlink(p.string))
    return (if target.isAbsolute: target else: p.parent.resolve / target)
  let up = p.parent
  if up.string == p.string:
    return Path(absolutePath(p.string))
  up.resolve / Path(p.name)\
"""


def _ensure_path_helper():
    """Inject std/paths and the converter the first time Path is named."""
    from hek_parsec import ParserState
    # std/paths for the type and its splitting procs, and os for the
    # existence tests and link expansion behind Path.resolve. Both are used
    # by the helper itself, so neither can turn into an unused-import
    # warning. std/dirs is NOT added here: it is only needed for the one
    # createDir that Path.mkdir calls, so it is added lazily, only when a
    # `.mkdir()` call is actually seen (see the attr_trailer handling in
    # hek_nim_expr.py) -- a file that uses Path but never calls .mkdir()
    # should not have to depend on a stdlib module split out of `os` in a
    # comparatively recent Nim release. std/files stays out entirely: the
    # converter below lets os's string-based fileExists, readFile and
    # friends take a Path already.
    ParserState.nim_imports.add("std/paths")
    ParserState.nim_imports.add("os")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("adascriptPathToString" in d for d in decls):
        decls.append(_PATH_HELPER)
        ParserState.nim_top_decls = decls


_PATH_RELATIVE_TO = """\
proc relative_to*(p: Path, base: Path): Result[Path, PathFailure_T] =
  ## p seen from base: `Path("/a/b/c").relative_to(Path("/a"))` is `b/c`, and
  ## a path relative to itself is ".". Not below base is a PathFailure_T, not
  ## an exception -- by pathlib's reading of "below": a leading "/" has to
  ## match, and repeated slashes, "." parts and a trailing slash do not
  ## count. ".." is not resolved, as there.
  proc parts(s: string): seq[string] =
    for c in s.split('/'):
      if c.len > 0 and c != ".": result.add(c)
  let a = parts(p.string)
  let b = parts(base.string)
  if p.isAbsolute != base.isAbsolute or b.len > a.len or a[0 ..< b.len] != b:
    return Result[Path, PathFailure_T].err(PathFailure_T(op: "relative_to", path: p.string, base: base.string))
  Result[Path, PathFailure_T].ok(Path(if a.len == b.len: "." else: a[b.len .. ^1].join("/")))\
"""


_PATH_MKDIR = """\
proc mkdir*(p: Path): Result[void, PathFailure_T] =
  ## Create this directory and any missing parents (mkdir -p). createDir is
  ## already both recursive and idempotent, which is the contract the Python
  ## backend gets from os.makedirs(exist_ok = True). What the system refuses
  ## -- a permission, a file where the directory should be -- is a
  ## PathFailure_T, not an exception.
  try:
    createDir(p)
    Result[void, PathFailure_T].ok()
  except CatchableError as e:   # OSError for one refusal, IOError for another
    Result[void, PathFailure_T].err(PathFailure_T(op: "mkdir", path: p.string, reason: e.msg))\
"""


_PATH_IO = """\
proc read_text*(p: Path): Result[string, PathFailure_T] =
  ## The whole file, as text: what readFile gives, or why it could not.
  try:
    Result[string, PathFailure_T].ok(readFile(p.string))
  except CatchableError as e:
    Result[string, PathFailure_T].err(PathFailure_T(op: "read_text", path: p.string, reason: e.msg))

proc read_lines*(p: Path): Result[seq[string], PathFailure_T] =
  ## The lines of the file, without their newlines -- what `for line in
  ## p.lines:` yields, as a list, or why the file could not be read.
  try:
    var got: seq[string]
    for line in lines(p.string):
      got.add(line)
    Result[seq[string], PathFailure_T].ok(got)
  except CatchableError as e:
    Result[seq[string], PathFailure_T].err(PathFailure_T(op: "read_lines", path: p.string, reason: e.msg))

proc write_text*(p: Path, text: string): Result[void, PathFailure_T] =
  ## Replace the file's contents: what writeFile does, or why it could not.
  try:
    writeFile(p.string, text)
    Result[void, PathFailure_T].ok()
  except CatchableError as e:
    Result[void, PathFailure_T].err(PathFailure_T(op: "write_text", path: p.string, reason: e.msg))\
"""


_PARSE_HELPERS = """\
proc adascriptParseFloat*(s: string): Result[float, ParseFailure_T] =
  ## parse_float. A decimal number: an optional sign, digits with at most one
  ## `.`, an optional exponent -- and nothing else. No spaces, no `_`, no
  ## `inf` or `nan`, no hex: the same on both backends, where Python's
  ## `float()` and Nim's `parseFloat` each take a different set. Not a number
  ## is a ParseFailure_T, not an exception. (Named adascript... because Nim
  ## ignores case and underscores: `parse_float` there IS strutils.parseFloat.)
  var i = 0
  let n = s.len
  if i < n and s[i] in {'+', '-'}: inc i
  var digits = 0
  while i < n and s[i] in {'0'..'9'}:
    inc i
    inc digits
  if i < n and s[i] == '.':
    inc i
    while i < n and s[i] in {'0'..'9'}:
      inc i
      inc digits
  var valid = digits > 0
  if valid and i < n and s[i] in {'e', 'E'}:
    inc i
    if i < n and s[i] in {'+', '-'}: inc i
    var exp_digits = 0
    while i < n and s[i] in {'0'..'9'}:
      inc i
      inc exp_digits
    valid = exp_digits > 0
  if valid and i == n:
    Result[float, ParseFailure_T].ok(strutils.parseFloat(s))
  else:
    Result[float, ParseFailure_T].err(ParseFailure_T(what: "float", text: s))

proc adascriptParseInt*(s: string): Result[int, ParseFailure_T] =
  ## parse_int. A decimal integer: an optional sign and digits, nothing else
  ## (no spaces, no `_`, no `0x`), and one that fits an `int`: the same on
  ## both backends. Not one is a ParseFailure_T, not an exception.
  var i = 0
  let n = s.len
  if i < n and s[i] in {'+', '-'}: inc i
  let start = i
  while i < n and s[i] in {'0'..'9'}: inc i
  if i == n and i > start:
    try:
      return Result[int, ParseFailure_T].ok(strutils.parseInt(s))
    except ValueError:
      discard                       # too big for an int
  Result[int, ParseFailure_T].err(ParseFailure_T(what: "int", text: s))

proc adascriptParseEnum*[T: enum](U: typedesc[T], s: string): Result[T, ParseFailure_T] =
  ## parse_enum. The member of the enum named exactly S -- Nim's `parseEnum` would also
  ## take `a` for `A` and ignore underscores. Not a member is a
  ## ParseFailure_T, not an exception.
  for e in T:
    if $e == s:
      return Result[T, ParseFailure_T].ok(e)
  Result[T, ParseFailure_T].err(ParseFailure_T(what: $U, text: s))\
"""


_INPUT_HELPER = """\
proc adascriptInput*(prompt: string = ""): Result[string, InputFailure_T] =
  ## input. One line from standard input, without its newline; the end of the
  ## input is an InputFailure_T, not an exception. The prompt is shown first
  ## and flushed, as Python's input() does.
  if prompt.len > 0:
    stdout.write(prompt)
    stdout.flushFile()
  var line: string
  if stdin.readLine(line):
    Result[string, InputFailure_T].ok(line)
  else:
    Result[string, InputFailure_T].err(InputFailure_T(reason: "end of input"))\
"""


def _ensure_input_helper():
    """Add input the first time it is called: a proc returning a Result, so
    it needs stdlib.nim."""
    from hek_parsec import ParserState
    ParserState.nim_imports.add("stdlib")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("proc adascriptInput*" in d for d in decls):
        decls.append(_INPUT_HELPER)
        ParserState.nim_top_decls = decls


def _ensure_parse_helpers():
    """Add parse_float, parse_int and parse_enum the first time one is called: procs
    returning a Result, so they need stdlib.nim."""
    from hek_parsec import ParserState
    ParserState.nim_imports.add("stdlib")
    ParserState.nim_imports.add("strutils")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("proc adascriptParseFloat*" in d for d in decls):
        decls.append(_PARSE_HELPERS)
        ParserState.nim_top_decls = decls


def _ensure_path_io():
    """Add Path.read_text / read_lines / write_text the first time one is
    called: procs returning a Result, so they need stdlib.nim."""
    from hek_parsec import ParserState
    _ensure_path_helper()
    ParserState.nim_imports.add("stdlib")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("proc read_text*" in d for d in decls):
        decls.append(_PATH_IO)
        ParserState.nim_top_decls = decls


def _ensure_path_mkdir():
    """Add Path.mkdir the first time it is called: a proc returning a
    Result, so it needs stdlib.nim, and createDir, which is in std/dirs."""
    from hek_parsec import ParserState
    _ensure_path_helper()
    ParserState.nim_imports.add("stdlib")
    ParserState.nim_imports.add("std/dirs")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("proc mkdir*" in d for d in decls):
        decls.append(_PATH_MKDIR)
        ParserState.nim_top_decls = decls


def _ensure_path_relative_to():
    """Add Path.relative_to the first time it is called: a proc returning a
    Result, so it needs stdlib.nim, and strutils to split and join."""
    from hek_parsec import ParserState
    _ensure_path_helper()
    ParserState.nim_imports.add("stdlib")
    ParserState.nim_imports.add("strutils")
    decls = getattr(ParserState, "nim_top_decls", [])
    if not any("proc relative_to*" in d for d in decls):
        decls.append(_PATH_RELATIVE_TO)
        ParserState.nim_top_decls = decls


def _union_alias_nim(name):
    """The Nim union a name declared `type X is A | B` stands for, or None.
    Read as the union itself -- OneOf2[A, B] -- so that everything that
    works on a written-out union works on its name."""
    aliases = getattr(ParserState, "union_aliases", {})
    if name not in aliases:
        return None
    cache = getattr(ParserState, "union_aliases_nim", None)
    if cache is None:
        cache = ParserState.union_aliases_nim = {}
    if name not in cache:
        cache[name] = None            # a union naming itself stops here
        from ady_declarations import parse_type
        _ast = parse_type(aliases[name])
        cache[name] = _ast.to_nim() if _ast is not None else None
    return cache[name]


@method(type_name)
def to_nim(self, prec=None):
    """type_name: IDENTIFIER (type alias or user-defined type) -> Nim: mapped via _PY_TO_NIM if known"""
    # Check if the underlying identifier has a known Nim mapping
    node = self.nodes[0]
    if hasattr(node, 'nodes') and node.nodes and isinstance(node.nodes[0], str):
        mapped = _PY_TO_NIM.get(node.nodes[0])
        if mapped:
            if node.nodes[0] == "Path":
                _ensure_path_helper()
            return mapped
        if node.nodes[0] in ("ShellFailure_T", "PathFailure_T", "ParseFailure_T"):
            ParserState.nim_imports.add("stdlib")   # they live in stdlib.nim
        _alias = _union_alias_nim(node.nodes[0])
        if _alias and len(self.nodes) == 1:
            return _alias
    result = node.to_nim()
    # Append any trailing nodes (e.g. generic params [T] from subscript trailers)
    for extra in self.nodes[1:]:
        # Several_Times nodes don't have a useful to_nim(); iterate their children
        if hasattr(extra, 'nodes'):
            for child in extra.nodes:
                if hasattr(child, 'to_nim'):
                    result += child.to_nim()
        elif hasattr(extra, 'to_nim'):
            result += extra.to_nim()
    return result


@method(seq_type)
def to_nim(self, prec=None):
    """seq_type: '[]' type_annotation -> Nim: seq[T]"""
    return f"seq[{self.nodes[0].to_nim()}]"


@method(array_type)
def to_nim(self, prec=None):
    """array_type: '[' INTEGER ']' type_annotation -> Nim: array[N, T]"""
    size = self.nodes[0].nodes[0]  # the integer string
    elem = self.nodes[1].to_nim()
    return f"array[{size}, {elem}]"


@method(openarray_type)
def to_nim(self, prec=None):
    """openarray_type: '[*]' type_annotation -> Nim: openArray[T]"""
    elem = self.nodes[1].to_nim()
    return f"openArray[{elem}]"


@method(enum_array_type)
def to_nim(self, prec=None):
    """enum_array_type: '[' IDENTIFIER ']' type_annotation (enum-indexed array) -> Nim: array[EnumType, T]"""
    idx = self.nodes[0].to_nim()
    elem = self.nodes[1].to_nim()
    # `[str]float`: a key with no finite domain orders its keys by
    # insertion, which is what OrderedTable is. See ordered_map_key.
    from ady_declarations import ordered_map_key
    if ordered_map_key(self.nodes[0]):
        ParserState.nim_imports.add("tables")
        _ensure_ordered_table_items()
        return f"OrderedTable[{idx}, {elem}]"
    return f"array[{idx}, {elem}]"


# Iteration goes to the half of a mapping that is not known in advance. A
# [Color_T]V's keys are the domain, so it yields values; a [str]V's keys are
# whatever arrived, so it yields those, in the order they arrived -- as a
# {K}V yields its keys. The for-loop rewrite turns `for k in m` into
# `m.keys` when it knows m's type; this is the same thing for when it does
# not.
_ORDERED_TABLE_ITEMS = """\
iterator items[K, V](t: OrderedTable[K, V]): K =
  ## `for k in m` over a `[K]V` with no finite K: its keys, in insertion order.
  for k in t.keys: yield k"""


def _ensure_ordered_table_items():
    """Define `items` on OrderedTable the first time a [K]V map is named:
    a [K]V whose keys are not known in advance iterates them."""
    decls = getattr(ParserState, "nim_top_decls", None)
    if decls is None:
        decls = ParserState.nim_top_decls = []
    if _ORDERED_TABLE_ITEMS not in decls:
        decls.append(_ORDERED_TABLE_ITEMS)


@method(subrange_array_type)
def to_nim(self, prec=None):
    """subrange_array_type: '[' subrange_def ']' type_annotation -> Nim: array[lo..hi, T]"""
    idx = self.nodes[0].to_nim()   # subrange_def -> "range[lo..hi]"
    # Nim array index spec uses lo..hi directly, not range[lo..hi]
    if idx.startswith("range[") and idx.endswith("]"):
        idx = idx[6:-1]
    elem = self.nodes[1].to_nim()  # type_annotation
    return f"array[{idx}, {elem}]"


@method(dict_type)
def to_nim(self, prec=None):
    """dict_type: '{' type_annotation '}' type_annotation -> Nim: Table[K, V] (imports tables)"""
    ParserState.nim_imports.add("tables")
    key = self.nodes[0].to_nim()
    val = self.nodes[1].to_nim()
    return f"Table[{key}, {val}]"


@method(set_type)
def to_nim(self, prec=None):
    """set_type: '{}' type_annotation -> Nim: set[T] for ordinals; HashSet[T] otherwise"""
    elem = self.nodes[0].to_nim()
    if _is_nim_ordinal(elem):
        return f"set[{elem}]"
    ParserState.nim_imports.add("sets")
    return f"HashSet[{elem}]"


@method(callable_type)
def to_nim(self, prec=None):
    """callable_type: params '->' type_annotation -> Nim: proc(a0: T, ...): R"""
    tup = self.nodes[0]
    ret = self.nodes[1].to_nim()
    params = _tuple_elements_nim(tup)
    if params:
        param_str = ", ".join(f"a{i}: {p}" for i, p in enumerate(params))
    else:
        param_str = ""
    if ret == "void":
        return f"proc({param_str})"
    return f"proc({param_str}): {ret}"


@method(single_param_type)
def to_nim(self, prec=None):
    """single_param_type: '(' type_annotation ')' -- the one parameter of a
    function type, `(int) -> int`; rendered by callable_type."""
    return self.nodes[0].to_nim()


@method(no_param_type)
def to_nim(self, prec=None):
    """no_param_type: '(' ')' -- a function type taking nothing, `() -> R`;
    rendered by callable_type."""
    return ""


@method(empty_tuple_type)
def to_nim(self, prec=None):
    """empty_tuple_type: '(' ',' ')' (empty params) -> Nim: '()'"""
    return "()"


@method(singleton_tuple_type)
def to_nim(self, prec=None):
    """singleton_tuple_type: '(' type_annotation ',' ')' -> Nim: '(T,)'"""
    return f"({self.nodes[0].to_nim()},)"


@method(multi_tuple_type)
def to_nim(self, prec=None):
    """multi_tuple_type: '(' type_annotation (',' type_annotation)+ [','] ')' -> Nim: '(T, U, ...)'"""
    elems = _tuple_elements_nim(self)
    return f"({', '.join(elems)})"


def _tuple_elements_nim(tup):
    """Extract Nim type strings from a tuple_type AST node, or from
    the parameters of a function type: `()` and `(T)` are those too."""
    if type(tup).__name__ in ("empty_tuple_type", "no_param_type"):
        return []
    if type(tup).__name__ == "single_param_type":
        return [tup.nodes[0].to_nim()]
    if type(tup).__name__ == "singleton_tuple_type":
        return [tup.nodes[0].to_nim()]
    # multi_tuple_type: first + Several_Times of (COMMA + type_annotation)
    elems = [tup.nodes[0].to_nim()]
    st = tup.nodes[1]  # the Several_Times node
    for seq in st.nodes:
        if hasattr(seq, "nodes") and seq.nodes:
            elems.append(seq.nodes[0].to_nim())
    return elems


@method(optional_type)
def to_nim(self, prec=None):
    """optional_type: '?' type_annotation -> Nim: Option[T] (imports options); ref types stay as-is"""
    inner = self.nodes[0].to_nim()
    # For ref object types, the type is already nullable — no Option needed.
    # Value-type classes (kind="class") need Option[T].
    sym = ParserState.symbol_table.lookup(inner)
    if sym and sym.get("kind") == "ref_class":
        return inner
    ParserState.nim_imports.add("options")
    return f"Option[{inner}]"


def _nim_union_type(values):
    """OneOfN[...] of the Nim spellings of a union's members."""
    if len(values) > 6:
        raise SyntaxError(
            f"a union of {len(values)} members: six at most -- group some "
            f"of them in a record")
    return f"OneOf{len(values)}[{', '.join(values)}]"


@method(union_type)
def to_nim(self, prec=None):
    """union_type: A '|' B ('|' C)* -> Nim. A plain union is stdlib.nim's
    OneOfN[...] -- `int | float` is OneOf2[int, float]. With a failure
    member it is Result[T, F], whichever order the members are written in:
    Result[void, F] when T is None, Result[OneOfN[...], F] for several
    value members. `T | None` is ?T, Option[T]."""
    from ady_stmt import classify_union, check_failure_marks
    members = [self.nodes[0]] + [seq.nodes[0] for seq in self.nodes[1].nodes
                                 if hasattr(seq, "nodes") and seq.nodes]
    parts = [m.to_nim() for m in members]
    marked = [type(m).__name__ == "failure_member" for m in members]
    parts = ["None" if p in ("nil", "void") else p for p in parts]
    u = classify_union(parts, check_failure_marks(
        parts, marked, getattr(ParserState, "failure_types", set())))
    if u["kind"] == "optional":
        ParserState.nim_imports.add("options")
        return f"Option[{u['values'][0]}]"
    ParserState.nim_imports.add("stdlib")
    if u["kind"] == "plain":
        return _nim_union_type(u["values"])
    values = u["values"]
    value = ("void" if values == ["None"] else
             values[0] if len(values) == 1 else _nim_union_type(values))
    return f"Result[{value}, {u['failure']}]"


@method(failure_member)
def to_nim(self, prec=None):
    """failure_member: '!' T -> Nim: T. The mark is read by union_type,
    which makes the member the Result's error."""
    return self.nodes[0].to_nim()


@method(lent_type)
def to_nim(self, prec=None):
    """lent T  ->  T  (Nim ARC handles borrows; 'lent' is a no-op at the type level for params)"""
    inner = self.nodes[0].to_nim()
    return inner


@method(own_param_type)
def to_nim(self, prec=None):
    """own T  ->  sink T  (Nim ownership-transfer annotation; callee takes ownership)"""
    inner = self.nodes[0].to_nim()
    return f"sink {inner}"


###############################################################################
# Tests
###############################################################################

if __name__ == "__main__":
    import hek_nim_expr  # noqa: F401 — registers expr to_nim() for expression fallback
    print()
    print("=" * 60)
    print("ADASCRIPT -> Nim Type Translation Tests")
    print("=" * 60)

    nim_tests = [
        # --- Primitives ---
        ("int", "int"),
        ("str", "string"),
        ("float", "float"),
        ("bool", "bool"),
        ("bytes", "seq[byte]"),
        ("None", "void"),
        # --- User-defined types ---
        ("MyClass", "MyClass"),
        ("SomeType", "SomeType"),
        # --- Sequence ---
        ("[]int", "seq[int]"),
        ("[]str", "seq[string]"),
        ("[][]int", "seq[seq[int]]"),
        # --- Fixed array ---
        ("[5]int", "array[5, int]"),
        ("[*]int", "openArray[int]"),
        ("[3]str", "array[3, string]"),
        # --- Nested containers ---
        ("[3][]int", "array[3, seq[int]]"),
        ("[][5]int", "seq[array[5, int]]"),
        # --- Dict ---
        ("{str}int", "Table[string, int]"),
        ("{int}str", "Table[int, string]"),
        # --- Set ---
        ("{}int", "HashSet[int]"),
        ("{}str", "HashSet[string]"),
        # --- Optional ---
        ("?int", "Option[int]"),
        ("?str", "Option[string]"),
        ("?[]int", "Option[seq[int]]"),
        ("[]?int", "seq[Option[int]]"),
        # --- Tuple ---
        ("(int, str)", "(int, string)"),
        ("(int, str, float)", "(int, string, float)"),
        ("(int,)", "(int,)"),
        # --- Union ---
        ("int | str", "int | string"),
        ("int | str | float", "int | string | float"),
        ("?int | str", "Option[int] | string"),
        # --- Callable ---
        ("(int, str) -> bool", "proc(a0: int, a1: string): bool"),
        ("(int,) -> int", "proc(a0: int): int"),
        ("(int) -> int", "proc(a0: int): int"),
        ("() -> None", "proc()"),
    ]

    passed = failed = 0
    for code, expected in nim_tests:
        try:
            ast = parse_type(code)
            if ast is None:
                print(f"  FAIL: {code!r} -> parse returned None")
                failed += 1
            else:
                output = ast.to_nim()
                if output == expected:
                    print(f"  PASS: {code!r} -> {output!r}")
                    passed += 1
                else:
                    print(f"  MISMATCH: {code!r}")
                    print(f"    expected: {expected!r}")
                    print(f"    got:      {output!r}")
                    failed += 1
        except Exception as e:
            print(f"  ERROR: {code!r} -> {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print()

