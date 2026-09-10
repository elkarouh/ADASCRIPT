#!/usr/bin/env python3
"""ADASCRIPT-style type annotation parser using hek_parsec combinator framework.

Defines the ``type_annotation`` parser used throughout the Python 3 grammar
(annotated assignments, function parameter/return annotations, type aliases).

ADASCRIPT uses a left-to-right type notation inspired by Go and Odin, where
container prefixes read naturally ("sequence of int" = ``[]int``).  The parser
translates this notation into standard Python annotation strings via to_py().

Syntax reference
================

Primitives
----------
    int  str  float  bool  bytes  None

User-defined types
------------------
    Any identifier that is not a primitive keyword:
        MyClass   SomeType   TreeNode

Sequences (dynamic)
--------------------
    []<type>                        list[<type>]

    []int                           list[int]
    [][]int                         list[list[int]]
    []MyClass                       list[MyClass]

Fixed-size arrays
-----------------
    [<N>]<type>                     tuple[<type>, ...]

    [5]int                          tuple[int, ...]
    [3][]int                        tuple[list[int], ...]

Dictionaries
------------
    {<key_type>}<value_type>        dict[<key_type>, <value_type>]

    {str}int                        dict[str, int]
    {int}[]str                      dict[int, list[str]]

Sets
----
    {}<type>                        set[<type>]

    {}int                           set[int]
    {}str                           set[str]

Optional (nullable)
-------------------
    ?<type>                         <type> | None

    ?int                            int | None
    ?[]int                          list[int] | None
    []?int                          list[int | None]

Tuples
------
    (<type>, <type>, ...)           tuple[<type>, <type>, ...]
    (<type>,)                       tuple[<type>]

    (int, str)                      tuple[int, str]
    (int, str, float)               tuple[int, str, float]

Union types
-----------
    <type> | <type> | ...           <type> | <type> | ...

    int | str                       int | str
    ?int | str                      int | None | str

Callable (function signature)
-----------------------------
    [(<param_types>)]<return_type>  Callable[[<param_types>], <return_type>]

    [(int, str)]bool                Callable[[int, str], bool]
    [(int,)]int                     Callable[[int], int]

Grammar
=======
::

    type_annotation      = union_type | maybe_optional | expression
    union_type           = maybe_optional ('|' maybe_optional)+
    maybe_optional       = optional_type | basic_type
    optional_type        = '?' basic_type
    basic_type           = seq_type | callable_type | array_type
                         | dict_type | set_type | tuple_type
                         | primitive_type | type_name
    seq_type             = '[]' type_annotation
    array_type           = '[' INTEGER ']' type_annotation
    dict_type            = '{' type_annotation '}' type_annotation
    set_type             = '{}' type_annotation
    callable_type        = '[' tuple_type ']' type_annotation
    tuple_type           = empty_tuple_type | singleton_tuple_type | multi_tuple_type
    multi_tuple_type     = '(' type_annotation (',' type_annotation)+ [','] ')'
    singleton_tuple_type = '(' type_annotation ',' ')'
    empty_tuple_type     = '(' ',' ')'
    primitive_type       = 'int' | 'str' | 'float' | 'bool' | 'bytes' | 'None'
    type_name            = IDENTIFIER  (excluding primitives)

The ``expression`` fallback allows standard Python annotation syntax
(e.g. ``list[int]``) to pass through when used inside the full grammar.

Nim Translation
===============

Nim code generation is in ``hek_nim_declarations.py`` (``to_nim()`` methods)::

    Primitives:  str -> string, bytes -> seq[byte], None -> void
    Sequences:   []int -> seq[int]
    Arrays:      [5]int -> array[5, int]
    Dicts:       {str}int -> Table[string, int]
    Sets:        {}int -> HashSet[int]
    Optionals:   ?int -> Option[int]
    Tuples:      (int, str) -> (int, string)
    Callables:   [(int, str)]bool -> proc(a0: int, a1: string): bool

Usage
=====
::

    from hek_py_declarations import type_annotation, parse_type
    from hek_parsec import Input

    # Standalone parsing
    ast = parse_type("[]?int")
    print(ast.to_py())          # list[int | None]
    # from hek_nim_declarations import *  # to enable to_nim()
    # print(ast.to_nim())         # seq[Option[int]]

    # As part of a larger grammar
    ann_assign = IDENTIFIER + COLON + type_annotation
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))

from ady_declarations import *
import hek_py_expr  # noqa: F401 — registers expr to_py() methods
from hek_parsec import method
from ady_stmt import subrange_array_type  # noqa: F401 — defined after ady_declarations

# to_py() methods
###############################################################################


@method(primitive_type)
def to_py(self, prec=None):
    """primitive_type: 'int' | 'str' | 'float' | 'bool' | 'bytes' | 'None' -> Nim: str->string, bytes->seq[byte], None->void"""
    name = self.nodes[0]
    if name == "char":
        return "str"
    return name


# Adascript's predefined subtypes have no Python spelling.  Nim range-checks
# them; Python cannot, so they are defined as int and kept in the annotation
# for what the name tells the reader.
_SUBTYPE_ALIASES = """\
# Adascript's predefined subtypes.  Nim range-checks these (Natural is 0..,
# Positive is 1..); Python does not, so here they are plain ints.
Natural = int
Positive = int\
"""


def _ensure_subtype_aliases():
    """Define Natural/Positive the first time an annotation names one."""
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("Natural = int" in d for d in decls):
        decls.append(_SUBTYPE_ALIASES)
        ParserState.py_top_decls = decls


# A path that is still a string.
#
# `pathlib.Path` was the obvious choice and is the wrong one here: Nim's
# `std/paths.Path` is a `distinct string`, and with the converter the Nim
# backend injects, `p & "!"` and `p.toUpperAscii` both work there.  On
# pathlib those are a TypeError and an AttributeError, so the same source
# would behave differently per backend -- the one thing this project cannot
# afford.  A str subclass with `/` gives both backends "a string that also
# joins", which is what Nim has.
_PATH_ALIAS = """\
class Path(str):
    \"\"\"A filesystem path: a str that also joins with `/`.

    Everything that takes a str takes one of these -- open(), os.path.*,
    subprocess, f-strings, .upper() -- which mirrors Nim, where Path is a
    distinct string with a converter back to string.
    \"\"\"
    __slots__ = ()

    def __truediv__(self, other):
        return Path(os.path.join(self, str(other)))

    def __rtruediv__(self, other):
        return Path(os.path.join(str(other), self))

    @property
    def parent(self):
        \"\"\"The directory holding this path -- "." when there is none.\"\"\"
        return Path(_pathlib.PurePath(self).parent)

    @property
    def name(self):
        \"\"\"The last component, with no directory part.\"\"\"
        return _pathlib.PurePath(self).name

    def mkdir(self):
        \"\"\"Create this directory and any missing parents (mkdir -p).\"\"\"
        os.makedirs(self, exist_ok=True)

    def resolve(self):
        \"\"\"The absolute path, with every symlink along it expanded.\"\"\"
        return Path(os.path.realpath(self))\
"""
# `parent` and `name` go through PurePath rather than os.path.dirname /
# os.path.basename because those two disagree with Nim on a trailing slash:
# os.path says "a/b/" has no basename and "a/b" as its dirname, while both
# pathlib and Nim's lastPathPart/parentDir say "b" and "a".  Nim is the one
# that cannot be changed, so Python follows pathlib's splitting rules --
# without becoming a pathlib.Path, which is what the note above rules out.


def _ensure_path_alias():
    """Define Path the first time an annotation names it."""
    from hek_parsec import ParserState
    ParserState.nim_imports.add("import os")
    ParserState.nim_imports.add("import pathlib as _pathlib")
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("class Path(str)" in d for d in decls):
        decls.append(_PATH_ALIAS)
        ParserState.py_top_decls = decls


# What `shell:` and `run()` hand back.  The shell forms infer it, so it only
# needs a spelling where a binding must be annotated -- `let r: RunResult =
# run(argv)`.  Python has no record type here, only the SimpleNamespace the
# helpers build, so the name is an alias to that.
_RUN_RESULT_ALIAS = """\
# What run() and the shell forms return: output, stderr and code.
RunResult = _types.SimpleNamespace\
"""


def _ensure_run_result_alias():
    """Define RunResult the first time an annotation names it."""
    from hek_parsec import ParserState
    ParserState.nim_imports.add("import types as _types")
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("RunResult = " in d for d in decls):
        decls.append(_RUN_RESULT_ALIAS)
        ParserState.py_top_decls = decls


@method(type_name)
def to_py(self, prec=None):
    """type_name: IDENTIFIER (type alias or user-defined type) -> Nim: mapped via _PY_TO_NIM if known"""
    name = self.nodes[0].to_py()  # delegate to primary expression node
    if name in ("Natural", "Positive"):
        _ensure_subtype_aliases()
    elif name == "RunResult":
        _ensure_run_result_alias()
    elif name == "Path":
        _ensure_path_alias()
    elif name == "File":
        # Nim's File is what open() returns and what stdin/stdout/stderr are,
        # so one variable can hold either -- `(open(p) if p else stdin)` is
        # how a program reads a named file or its input without writing the
        # loop twice. typing.TextIO is the annotation that covers both here;
        # the name itself is not defined in Python and reached the output
        # verbatim, so any program that wrote it raised NameError.
        from hek_parsec import ParserState as _PS_file
        _PS_file.nim_imports.add("from typing import TextIO")
        return "TextIO"
    elif name == "Job":
        # `let jobs: []Job = []` has to name the handle shellSpawn returns,
        # so the class the helper defines answers to that name too.
        from hek_py_parser import _ensure_spawn_helper
        _ensure_spawn_helper()
        return "_Job"
    return name


@method(seq_type)
def to_py(self, prec=None):
    """seq_type: '[]' type_annotation -> Nim: seq[T]"""
    return f"list[{self.nodes[0].to_py()}]"


@method(array_type)
def to_py(self, prec=None):
    """array_type: '[' INTEGER ']' type_annotation -> Nim: array[N, T]"""
    return f"tuple[{self.nodes[1].to_py()}, ...]"


@method(openarray_type)
def to_py(self, prec=None):
    """openarray_type: '[*]' type_annotation -> Nim: openArray[T]"""
    return f"Sequence[{self.nodes[1].to_py()}]"


_ENUM_ARRAY_ALIAS = '''\
class _EnumArray(dict):
    """[O]T where the domain is an enum: an array indexed by its members.

    A dict, so `score[RED]` is the natural lookup, but it iterates its
    values, in the order of the domain. Every other member of the [O]T
    family -- [3]int, [0..2]int, a named subrange -- is a list here and
    yields values in index order, and the Nim backend does the same for all
    four because they are all `array[O, T]` there. A plain dict would make
    this one alone yield its keys, in whatever order the literal was written.

    `{E}V` is unaffected: that is a real dict and iterating it gives keys,
    which is what both Python and Nim's Table do.
    """
    __slots__ = ()

    def __iter__(self):
        def _ordinal(kv):
            k = kv[0]
            return getattr(k, "value", k)
        return iter(v for _, v in sorted(self.items(), key=_ordinal))\
'''


def _ensure_enum_array_alias():
    """Define _EnumArray the first time an [E]T is named or built."""
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("class _EnumArray(dict)" in d for d in decls):
        decls.append(_ENUM_ARRAY_ALIAS)
        ParserState.py_top_decls = decls


@method(enum_array_type)
def to_py(self, prec=None):
    """enum_array_type: '[' IDENTIFIER ']' type_annotation (enum-indexed array) -> Nim: array[EnumType, T]"""
    from hek_parsec import ParserState
    idx = self.nodes[0].to_py()
    elem = self.nodes[1].to_py()
    # `[E]T` and `[N]T` are the same shape once N is a named constant --
    # both are '[' IDENTIFIER ']' T -- so the grammar cannot separate them
    # and the identifier has to be looked up. An enum (or char/bool, the
    # other ordinals that arrive by name) indexes a mapping; an integer
    # constant just gives the length, and that is the fixed array of
    # array_type above.
    # tick_types holds the named ordinal *types* -- enums by their members,
    # subranges by their bounds -- and not plain constants, which is exactly
    # the line to draw. `[Prisoner_T]Box_T` over `1 .. 100` is a mapping and
    # cannot be a list: its domain does not start at 0.
    _info = getattr(ParserState, "tick_types", {}).get(idx)
    _is_ordinal_domain = _info is not None or idx in ("str", "bool")
    if not _is_ordinal_domain:
        return f"tuple[{elem}, ...]"
    # Named rather than `dict[...]` so the annotation still says which of the
    # two it is: `[E]T` and `{E}T` both rendered as dict[E, T], and the zero
    # value below has nothing else to go on.
    _ensure_enum_array_alias()
    return f"_EnumArray[{idx}, {elem}]"


@method(subrange_array_type)
def to_py(self, prec=None):
    """subrange_array_type: '[' subrange_def ']' type_annotation -> Python: list[T]"""
    elem = self.nodes[1].to_py()
    return f"list[{elem}]"


@method(dict_type)
def to_py(self, prec=None):
    """dict_type: '{' type_annotation '}' type_annotation -> Nim: Table[K, V] (imports tables)"""
    key = self.nodes[0].to_py()
    val = self.nodes[1].to_py()
    return f"dict[{key}, {val}]"


@method(set_type)
def to_py(self, prec=None):
    """set_type: '{}' type_annotation -> Nim: set[T] for ordinals; HashSet[T] otherwise"""
    return f"set[{self.nodes[0].to_py()}]"


@method(callable_type)
def to_py(self, prec=None):
    """callable_type: '[' tuple_type ']' type_annotation -> Nim: proc(a0: T, ...): R"""
    # nodes[0] is the tuple_type (params), nodes[1] is the return type
    tup = self.nodes[0]
    ret = self.nodes[1].to_py()
    # Extract individual param types from the tuple
    params = _tuple_elements(tup)
    param_str = ", ".join(params)
    # The name has to come from somewhere: an annotation is evaluated at
    # class-body and module level, so an unimported Callable is a NameError
    # at import time rather than a quiet typing-only omission.
    from hek_parsec import ParserState
    ParserState.nim_imports.add("from typing import Callable")
    return f"Callable[[{param_str}], {ret}]"


@method(empty_tuple_type)
def to_py(self, prec=None):
    """empty_tuple_type: '(' ',' ')' (empty params) -> Nim: '()'"""
    return "tuple[()]"


@method(singleton_tuple_type)
def to_py(self, prec=None):
    """singleton_tuple_type: '(' type_annotation ',' ')' -> Nim: '(T,)'"""
    return f"tuple[{self.nodes[0].to_py()}]"


@method(multi_tuple_type)
def to_py(self, prec=None):
    """multi_tuple_type: '(' type_annotation (',' type_annotation)+ [','] ')' -> Nim: '(T, U, ...)'"""
    elems = _tuple_elements(self)
    return f"tuple[{', '.join(elems)}]"


def _tuple_elements(tup):
    """Extract type strings from a tuple_type AST node."""
    if type(tup).__name__ == "empty_tuple_type":
        return []
    if type(tup).__name__ == "singleton_tuple_type":
        return [tup.nodes[0].to_py()]
    # multi_tuple_type: first + Several_Times of (COMMA + type_annotation)
    elems = [tup.nodes[0].to_py()]
    st = tup.nodes[1]  # the Several_Times node
    for seq in st.nodes:
        if hasattr(seq, "nodes") and seq.nodes:
            elems.append(seq.nodes[0].to_py())
    return elems


@method(optional_type)
def to_py(self, prec=None):
    """optional_type: '?' type_annotation -> Nim: Option[T] (imports options); ref types stay as-is"""
    return f"{self.nodes[0].to_py()} | None"


@method(union_type)
def to_py(self, prec=None):
    """union_type: maybe_optional ('|' maybe_optional)+ -> Nim: best-effort 'T | U' (Nim uses object variants instead)"""
    # nodes[0] is first maybe_optional, nodes[1] is Several_Times of (VBAR + maybe_optional)
    parts = [self.nodes[0].to_py()]
    st = self.nodes[1]
    for seq in st.nodes:
        if hasattr(seq, "nodes") and seq.nodes:
            parts.append(seq.nodes[0].to_py())
    return " | ".join(parts)


@method(lent_type)
def to_py(self, prec=None):
    """lent T  ->  T  (ownership annotation stripped for Python; GC handles it)"""
    return self.nodes[0].to_py()


@method(own_param_type)
def to_py(self, prec=None):
    """own T  ->  T  (ownership annotation stripped for Python; GC handles it)"""
    return self.nodes[0].to_py()

@method(lent_type)
def to_py(self, prec=None):
    """lent T  ->  T  (lent annotation stripped for Python; GC handles references)"""
    return self.nodes[0].to_py()


@method(own_param_type)
def to_py(self, prec=None):
    """own T  ->  T  (own annotation stripped for Python; GC handles ownership)"""
    return self.nodes[0].to_py()


###############################################################################
# Parse helper
###############################################################################


###############################################################################
# Tests
###############################################################################

if __name__ == "__main__":
    print("=" * 60)
    print("ADASCRIPT-style Type Annotation Parser Tests")
    print("=" * 60)

    tests = [
        # --- Primitives ---
        ("int", "int"),
        ("str", "str"),
        ("float", "float"),
        ("bool", "bool"),
        ("bytes", "bytes"),
        ("None", "None"),
        # --- User-defined types ---
        ("MyClass", "MyClass"),
        ("SomeType", "SomeType"),
        # --- Sequence ---
        ("[]int", "list[int]"),
        ("[]str", "list[str]"),
        ("[][]int", "list[list[int]]"),
        # --- Fixed array ---
        ("[5]int", "tuple[int, ...]"),
        ("[*]int", "Sequence[int]"),
        ("[3]str", "tuple[str, ...]"),
        # --- Nested containers ---
        ("[3][]int", "tuple[list[int], ...]"),
        ("[][5]int", "list[tuple[int, ...]]"),
        # --- Dict ---
        ("{str}int", "dict[str, int]"),
        ("{int}str", "dict[int, str]"),
        # --- Set ---
        ("{}int", "set[int]"),
        ("{}str", "set[str]"),
        # --- Optional ---
        ("?int", "int | None"),
        ("?str", "str | None"),
        ("?[]int", "list[int] | None"),
        ("[]?int", "list[int | None]"),
        # --- Tuple ---
        ("(int, str)", "tuple[int, str]"),
        ("(int, str, float)", "tuple[int, str, float]"),
        ("(int,)", "tuple[int]"),
        # --- Union ---
        ("int | str", "int | str"),
        ("int | str | float", "int | str | float"),
        ("?int | str", "int | None | str"),
        # --- Callable ---
        ("[(int, str)]bool", "Callable[[int, str], bool]"),
        ("[(int,)]int", "Callable[[int], int]"),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            ast = parse_type(code)
            if ast is None:
                print(f"  FAIL: {code!r} -> parse returned None")
                failed += 1
            else:
                output = ast.to_py()
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

