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

Open arrays (read-only, accepts seq or array)
---------------------------------------------
    [*]<type>                       Sequence[<type>]

    [*]int                          Sequence[int]
    [*]float                        Sequence[float]

    Use [*]T for function parameters that only read (iterate or index into)
    their argument and must accept both []T (seq) and [N]T (fixed array)
    at the call site.  Not valid as a variable type — only in parameter
    and return annotations.

Ordered mappings
----------------
    [<K>]<type>                     K a finite ordinal (enum, subrange,
                                    bool, char): an array indexed by K.
                                    Any other K (str, int, a class, an
                                    alias of one...): keyed in insertion
                                    order -- OrderedTable on Nim, a dict
                                    on Python. See ordered_map_key().

    [Color_T]int                    array[Color_T, int]
    [str]float                      OrderedTable[string, float]
    [(int, int)]float               OrderedTable[(int, int), float]

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

Function types
--------------
    (<param_types>) -> <return_type>  Callable[[<param_types>], <return_type>]

    (int, str) -> bool              Callable[[int, str], bool]
    (int) -> int                    Callable[[int], int]
    () -> None                      Callable[[], None]

Grammar
=======
::

    type_annotation      = union_type | maybe_optional | expression
    union_type           = maybe_optional ('|' maybe_optional)+
    maybe_optional       = optional_type | basic_type
    optional_type        = '?' basic_type
    basic_type           = seq_type | openarray_type
                         | array_type | enum_array_type
                         | dict_type | set_type | callable_type | tuple_type
                         | primitive_type | type_name
    seq_type             = '[]' type_annotation
    array_type           = '[' INTEGER ']' type_annotation
    openarray_type       = '[*]' type_annotation
    dict_type            = '{' type_annotation '}' type_annotation
    set_type             = '{}' type_annotation
    callable_type        = params '->' type_annotation
    params               = '(' ')' | '(' ',' ')' | '(' type_annotation ')'
                         | tuple_type
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

    Primitives:   str -> string, bytes -> seq[byte], None -> void
    Sequences:    []int -> seq[int]
    Arrays:       [5]int -> array[5, int]
    Open arrays:  [*]int -> openArray[int]
    Dicts:        {str}int -> Table[string, int]
    Sets:         {}int -> HashSet[int]
    Optionals:    ?int -> Option[int]
    Tuples:       (int, str) -> (int, string)
    Functions:    (int, str) -> bool -> proc(a0: int, a1: string): bool

Initialisation via comprehension
================================

Sequences, fixed-size arrays, dicts, and sets can all be initialised from
a comprehension on the right-hand side of an annotated assignment. The
transpiler reads the target type annotation and shapes the generated code
accordingly — you never have to write an explicit fill loop.

Sequences (``[]T``)
-------------------
The comprehension becomes a direct Nim ``collect()``::

    var squares: []int = [i*i for i in 0..<10]
    # Nim: var squares: seq[int] = collect(for i in 0 ..< 10: i * i)

Fixed-size arrays (``[N]T``)
----------------------------
The array dimension can be an INTEGER literal OR a compile-time ``const``
identifier. The ``const`` itself may be any expression Nim can fold at
compile time — an integer literal, arithmetic on other ``const``s, etc.
Nim resolves the size during its own compilation pass::

    const N_LESSONS: int = 22                # literal
    const SIZE_A:    int = 2 + 2 + 2 + 1     # arithmetic
    const SIZE_B:    int = SIZE_A + 7 + 8    # composes with other consts
    type State_T is [N_LESSONS]int
    type Matrix_T is [SIZE_B][SIZE_B]float

Because Nim's ``collect`` always produces a ``seq``, the transpiler wraps
a comprehension assigned into an array-typed destination in a ``block:``
that copies the collected seq into a fixed-size array — so the assignment
just works without any extra syntax::

    # Constant fill — every cell set to -1
    var INITIAL_STATE: State_T = [-1 for i in 0..<N_LESSONS]

    # Element expression may depend on the loop variable
    var PATTERN: State_T = [(-1 if i%2 != 0 else 10) for i in 0..<N_LESSONS]

Note: conditional positions need explicit booleans — ``i%2 != 0`` rather
than bare ``i%2``.

Dictionaries (``{K}V``)
-----------------------
Dict comprehensions translate into ``collect(initTable, ...)``::

    var sq_lookup: {int}int = {i: i*i for i in 1..<10}

Sets (``{}T``)
--------------
Set comprehensions translate into ``toHashSet(collect(...))``::

    var evens: {}int = {i for i in 0..<20 if i%2 == 0}

Open arrays (``[*]T``) — parameter annotation only
---------------------------------------------------
``[*]T`` is Nim's ``openArray[T]``: a read-only view that accepts both
``seq[T]`` (``[]T``) and ``array[N, T]`` (``[N]T``) at the call site.
It may **only** appear in function parameter annotations, not in variable
declarations. Useful when a function only iterates or indexes into its
argument and you want the caller to pass either kind without copying::

    def sum_values(xs: [*]int) -> int:
        var total: int = 0
        for x in xs:
            total = total + x
        return total

    # caller can pass a seq:
    var a: []int = [1, 2, 3, 4]
    print(sum_values(a))

    # or a fixed-size array:
    var b: [4]int = [1, 2, 3, 4]
    print(sum_values(b))

Candidates in the examples (functions whose array/seq parameters are
read-only and could be widened to ``[*]T``):

* ``timetable_backtrack.ady``:
    ``is_consistent(state: State_T, ...)``  — state only indexed
    ``count_options(self, state: State_T, ...)``  — state only indexed

* ``timetable_sa.ady``:
    ``energy(state: State_T)``  — state only indexed
    ``delta_energy(state: State_T, ...)``  — state only indexed
    ``entry_for(..., state: State_T)``  — state only indexed

* ``state_search.ady``:
    ``_reconstruct(self, parents: []int, steps: []Step_T[S,A], ...)``
    ``print_solution(self, solution: []Step_T[S,A], ...)``

* ``tsp.ady``:
    ``tour_length(tour: Tour_T)``
    ``preorder(children: [][]int, ..., tour: Tour_T, cities: Tour_T)``

Note: ``State_T`` is a type alias for ``[N_LESSONS]int`` in the timetable
files — passing it as ``[*]int`` would work, but since the type alias is
already consistent, the main benefit is for utility functions that should
accept both ``[]int`` and ``[N]int`` interchangeably.

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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "HPARSEC"))

import tokenize as tkn

from hek_parsec import (
    COMMA,
    IDENTIFIER,
    INTEGER,
    LBRACE,
    LBRACKET,
    LPAREN,
    RBRACE,
    RBRACKET,
    SSTAR,
    RPAREN,
    VBAR,
    Input,
    expect,
    filt,
    fw,
    ignore,
    literal,
    method,
)
from ady_expr import expression, ikw

###############################################################################
# Tokens
###############################################################################

QUESTION = ignore(expect(tkn.OP, "?"))
EXCLAIM = ignore(expect(tkn.OP, "!"))
ARROW = ignore(expect(tkn.OP, "->"))

###############################################################################
# Forward declarations
###############################################################################

type_annotation = fw("type_annotation")
union_type = fw("union_type")
maybe_optional = fw("maybe_optional")
optional_type = fw("optional_type")
basic_type = fw("basic_type")
seq_type = fw("seq_type")
array_type = fw("array_type")
openarray_type = fw("openarray_type")
enum_array_type = fw("enum_array_type")
dict_type = fw("dict_type")
set_type = fw("set_type")
callable_type = fw("callable_type")
single_param_type = fw("single_param_type")
no_param_type = fw("no_param_type")
tuple_type = fw("tuple_type")
multi_tuple_type = fw("multi_tuple_type")
singleton_tuple_type = fw("singleton_tuple_type")
empty_tuple_type = fw("empty_tuple_type")
primitive_type = fw("primitive_type")
type_name = fw("type_name")
elem_type = fw("elem_type")
lent_type = fw("lent_type")
own_param_type = fw("own_param_type")

###############################################################################
# Grammar rules
###############################################################################

# --- Primitives: int, str, float, bool, bytes, None ---
_PRIMITIVES = {"int", "str", "float", "bool", "bytes", "char", "None"}
primitive_type = filt(lambda s: s in _PRIMITIVES, IDENTIFIER)

# --- User-defined type name: any non-primitive identifier, including subscripts
# e.g. MyClass, List[int], Optional[str], Dict[str, int]
# We use the full Python primary expression so subscript trailers are consumed.
from ady_expr import primary as _primary
type_name = filt(
    lambda node: (
        # Accept primary expressions that start with a non-primitive identifier.
        # filt() passes m[0].node (first child of _primary result),
        # which is a Filter with .nodes[0] being the identifier string.
        hasattr(node, 'nodes') and node.nodes
        and isinstance(node.nodes[0], str)
        and node.nodes[0] not in _PRIMITIVES
    ),
    _primary
)

# --- Tuple types ---
# (int, str, float)  -> tuple[int, str, float]
# (int,)             -> tuple[int]
# (,)                -> tuple[()]
multi_tuple_type = (
    LPAREN + type_annotation + (COMMA + type_annotation)[1:] + COMMA[:] + RPAREN
)
singleton_tuple_type = LPAREN + type_annotation + COMMA + RPAREN
empty_tuple_type = LPAREN + COMMA + RPAREN

tuple_type = empty_tuple_type | singleton_tuple_type | multi_tuple_type

# --- Container types ---
# []int             -> list[int]
seq_type = LBRACKET + RBRACKET + elem_type

# [5]int            -> tuple[int, ...]
array_type = LBRACKET + INTEGER + RBRACKET + elem_type

# [*]int            -> Sequence[int]  (unconstrained/open array)
openarray_type = LBRACKET + SSTAR + RBRACKET + elem_type

# [EnumType]int      -> array[EnumType, int]  (enum-indexed array)
# [(int, int)]float  -> an insertion-ordered mapping keyed by the tuple
# Also accepts primitive ordinal types like char as array index.
# [str]float         -> OrderedTable[string, float] / an insertion-ordered dict:
# `[...]` is an ordered mapping whatever the key; only a finite ordinal key
# fixes the keys and their order at compile time. See ordered_map_key().
enum_array_type = LBRACKET + (tuple_type | type_name | primitive_type) + RBRACKET + elem_type

# {str}int          -> dict[str, int]
dict_type = LBRACE + type_annotation + RBRACE + elem_type

# {}int             -> set[int]
set_type = LBRACE + RBRACE + elem_type

# (int, str) -> bool -> Callable[[int, str], bool]
# (int) -> int, (int,) -> int, () -> None, (,) -> None
# The function type is written the way a `def` writes its signature. The
# return type is a whole type_annotation, as after a def's `->`, so
# `(str) -> int | None` returns an optional int; the arrow reaches as far
# right as it can, and a union *of* functions needs a name.
single_param_type = LPAREN + type_annotation + RPAREN
no_param_type = LPAREN + RPAREN
callable_type = ((empty_tuple_type | no_param_type | single_param_type
                  | singleton_tuple_type | multi_tuple_type)
                 + ARROW + type_annotation)

# --- Ownership type modifiers ---
# lent T  — borrow annotation (caller keeps ownership); maps to Nim's 'lent T'
# own T   — ownership transfer annotation; maps to Nim's 'sink T'
# These must appear BEFORE basic_type so they take priority when 'lent'/'own'
# are used as type prefixes in function parameter or return annotations.
lent_type = ikw("lent") + elem_type
own_param_type = ikw("own") + elem_type

# --- basic_type: a non-union, non-optional type ---
# Order matters: try container/callable before primitive/name (both start differently)
# callable_type before tuple_type: both start with '(', and only the arrow
# after the parameters tells a function type from a tuple.
# lent_type and own_param_type first so 'lent T' / 'own T' are never confused with
# the standalone identifiers 'lent' or 'own'.
basic_type = (
    lent_type
    | own_param_type
    | seq_type
    | openarray_type
    | array_type
    | enum_array_type
    | dict_type
    | set_type
    | callable_type
    | tuple_type
    | primitive_type
    | type_name
)

# --- Optional: ?int -> int | None ---
optional_type = QUESTION + basic_type
maybe_optional = optional_type | basic_type

# --- a union: int | float, and int | !Failure_T -------------------------
# `!` marks the failure member: `int | !Failure_T` is an int, or the reason
# there is none, which a do: block passes on. At most one, anywhere in the
# union; `None | !F` is a step that can only fail, and `T | None` keeps
# Python's meaning, ?T. A type marked `!` in one union is a failure in
# every union it is in, and is marked in each (ady_stmt.check_failure_marks).
failure_member = EXCLAIM + basic_type
union_member = failure_member | maybe_optional
union_type = union_member + (VBAR + union_member)[1:]

# --- type_annotation: union or single type, with expression fallback ---
type_annotation = union_type | maybe_optional | expression

# --- elem_type: a type in an element position, `[]T`, `{K}V`, `[N]T`... ---
# Never a union: `[]int | []str` is a Result of two lists, not a list of
# Results. Parenthesise nothing; a list of Results has to be named.
elem_type = maybe_optional | expression

###############################################################################
def parse_type(source_code):
    """Parse a type annotation string."""
    inp = Input(source_code)
    result = type_annotation.parse(inp)
    if result is None:
        return None
    return result[0]



# --- [K]V: an array, or a mapping in insertion order -------------------------
# `[...]` is the ordered side of the type table. With a finite ordinal between
# the brackets -- an enum, a subrange, bool, char -- every key and its place
# are known at compile time, and [K]V is an array. With any other key type the
# keys are not known until they arrive, so they are ordered by arrival:
# [str]float is an insertion-ordered mapping on both backends.

_ORDINAL_PRIMITIVES = {"bool", "char"}
_KEYED_PRIMITIVES = {"int", "str", "float", "bytes"}
# Builtin names that are types but no finite domain: Natural and Positive are
# subranges of int, far too large to be an array's index.
_KEYED_BUILTINS = {"Natural", "Positive", "Path", "Job", "RunResult",
                   "ShellFailure_T"}


def _index_name(idx_node):
    """The identifier between the brackets of an enum_array_type, or None."""
    node = idx_node
    while hasattr(node, "nodes") and node.nodes:
        head = node.nodes[0]
        if isinstance(head, str):
            return head if len(node.nodes) == 1 else None
        if len(node.nodes) != 1:
            return None
        node = head
    return node if isinstance(node, str) else None


def _decl_is_ordered_map_key(rhs, decls, seen):
    """Whether a type declared as RHS (its text) keys an ordered mapping."""
    rhs = rhs.strip()
    if rhs.startswith("distinct "):       # as its base does
        rhs = rhs[len("distinct "):].strip()
    if rhs.startswith("enum"):
        return False
    if rhs.startswith("float"):
        return True                       # float range: not ordinal
    if rhs[:1] in "[{(?" or "|" in rhs:
        return True                       # a container, tuple, optional, union
    if ".." in rhs:
        return False                      # an integer subrange
    if rhs.isidentifier():
        return _name_is_ordered_map_key(rhs, decls, seen)
    return True


def _name_is_ordered_map_key(name, decls, seen):
    """True: a type with no finite domain. False: a finite ordinal type.
    None: not a type at all -- a constant giving the length, `[N]T`."""
    from hek_parsec import ParserState
    if name in _ORDINAL_PRIMITIVES:
        return False
    if name in _KEYED_PRIMITIVES or name in _KEYED_BUILTINS:
        return True
    if name in seen:
        return None
    seen = seen | {name}
    if name in decls:
        rhs = decls[name]
        if rhs is None:                   # a class
            return True
        return _decl_is_ordered_map_key(rhs, decls, seen)
    # Not declared in this module: a type a nimported one declared, or a
    # constant. An ordinal type carries its bounds in tick_types.
    info = getattr(ParserState, "tick_types", {}).get(name)
    if info is not None:
        return bool(info.get("is_float_range"))
    sym = ParserState.symbol_table.lookup(name) if getattr(
        ParserState, "symbol_table", None) is not None else None
    if isinstance(sym, dict) and sym.get("kind") in ("type", "class",
                                                     "ref_class"):
        return True
    if name in getattr(ParserState, "py_type_names", ()):
        return True
    return None


def ordered_map_key(idx_node):
    """Whether `[K]V` with K = IDX_NODE is an insertion-ordered mapping.

    False for a finite ordinal K -- an enum, an integer subrange, bool or
    char, or a name for one -- and for a constant naming a length, `[N]T`:
    those are arrays. True for every other type: str, int, float, a class,
    a tuple or container named by an alias. The declarations come from
    scan_type_decls, so a type declared further down the file counts.
    """
    if type(idx_node).__name__ in ("singleton_tuple_type", "multi_tuple_type"):
        return True
    if type(idx_node).__name__ == "empty_tuple_type":
        raise SyntaxError(
            "'[(,)]T' keys a mapping by the empty tuple, which has one value: "
            "a function type is written '(,) -> T' (or '() -> T')")
    name = _index_name(idx_node)
    if name is None:
        return False
    from hek_parsec import ParserState
    decls = getattr(ParserState, "ady_type_decls", None) or {}
    return bool(_name_is_ordered_map_key(name, decls, frozenset()))


# --- distinct types ----------------------------------------------------------
# `type Velocity_T is distinct float` makes a type with float's values and
# operations that mixes with neither float nor any other distinct float: a
# Velocity_T plus a Distance_T is refused, and so is a Velocity_T given a
# plain float variable. `Velocity_T(x)` gets in, `float(v)` gets out. A
# literal takes the type its context asks for, as in Ada -- `let v:
# Velocity_T = 250.0`, `v * 2.0` -- which is why each backend needs to know,
# for a name, whether it is one and what it is made of.

_KIND_OF_PRIMITIVE = {"int": "int", "float": "float", "str": "str",
                      "char": "char", "bool": "bool",
                      "Natural": "int", "Positive": "int"}


def _decl_kind(rhs, decls, seen):
    """The kind of scalar a declared type's values are, or None."""
    rhs = rhs.strip()
    if rhs.startswith("distinct "):
        rhs = rhs[len("distinct "):].strip()
    if rhs in _KIND_OF_PRIMITIVE:
        return _KIND_OF_PRIMITIVE[rhs]
    if rhs.startswith("float"):
        return "float"                    # float range lo .. hi
    if rhs.startswith("enum"):
        return "enum"
    if rhs[:1] in "[{(?" or "|" in rhs:
        return None
    if ".." in rhs:
        return "int"                      # an integer subrange
    if rhs.isidentifier() and rhs not in seen and rhs in decls:
        inner = decls[rhs]
        return None if inner is None else _decl_kind(inner, decls, seen | {rhs})
    return None


def distinct_types(decls):
    """{name: kind} for every `type X is distinct T` in DECLS (the output of
    scan_type_decls), kind being the scalar T is made of -- "int", "float",
    "str", "char", "bool" or "enum" -- or None for anything else."""
    out = {}
    for name, rhs in decls.items():
        if rhs is not None and rhs.strip().startswith("distinct "):
            out[name] = _decl_kind(rhs, decls, frozenset({name}))
    return out


def is_distinct(name):
    """Whether NAME is a distinct type this module declares or imports."""
    from hek_parsec import ParserState
    return name in (getattr(ParserState, "distinct_types", None) or {})


def distinct_kind(name):
    """What a distinct type NAME is made of ("float", "int", ...), or None."""
    from hek_parsec import ParserState
    return (getattr(ParserState, "distinct_types", None) or {}).get(name)
