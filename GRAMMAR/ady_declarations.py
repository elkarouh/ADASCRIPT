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
                   "ShellFailure_T", "PathFailure_T", "ParseFailure_T",
                   "InputFailure_T"}


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
    if _is_gapped_enum(name, decls):
        from ady_enums import refuse
        refuse(name, "used as an array index")
    return bool(_name_is_ordered_map_key(name, decls, frozenset()))


def _is_gapped_enum(name, decls):
    """Is NAME an enum -- or another name for one -- whose values skip a number?"""
    from hek_parsec import ParserState
    from ady_enums import gaps_in_text
    for _ in range(8):
        rhs = decls.get(name)
        if not isinstance(rhs, str):
            info = getattr(ParserState, "tick_types", {}).get(name)
            return bool(info and info.get("gapped"))
        rhs = rhs.strip()
        if rhs.startswith("distinct "):
            rhs = rhs[len("distinct "):].strip()
        if rhs.startswith("enum"):
            return gaps_in_text(rhs)
        if not rhs.isidentifier():
            return False
        name = rhs
    return False


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


import re as _re_du

_DERIVED = _re_du.compile(r"^([A-Za-z_]\w*)[ \t]*([*/])[ \t]*([A-Za-z_]\w*)$")


def parse_derived(rhs):
    """(A, op, B) for a declaration `type C is A / B` or `A * B`, else None."""
    m = _DERIVED.match((rhs or "").strip())
    return (m.group(1), m.group(2), m.group(3)) if m else None


def distinct_types(decls, known=None, scaled=None):
    """{name: kind} for every `type X is distinct T`, every derived unit
    `type C is A / B` and every scaled unit `type C is K * B` (SCALED, the
    output of scaled_units) in DECLS (the output of scan_type_decls), kind
    being the scalar the type is made of -- "int", "float", "str", "char",
    "bool" or "enum" -- or None for anything else. A derived unit is made of
    what its operands are; a declaration that cannot be one raises
    SyntaxError. KNOWN is what an imported module already declared, which a
    derived unit here may be made from."""
    out = dict(known or {})
    scaled = scaled or {}
    for name, rhs in decls.items():
        if rhs is not None and rhs.strip().startswith("distinct "):
            out[name] = _decl_kind(rhs, decls, frozenset({name}))
    derived = {n: parse_derived(r) for n, r in decls.items()
               if r is not None and n not in scaled and parse_derived(r) is not None}
    # a derived unit may be made from another, and a scaled unit from either:
    # resolve until nothing moves
    pending = dict(derived)
    pending.update({n: (None, "*", b) for n, (_, b) in scaled.items()})
    while pending:
        moved = False
        for name, (a, op, b) in list(pending.items()):
            if a is None and b in out and b not in pending:
                out[name] = _check_scaled(name, scaled[name][0], b, out)
                del pending[name]
                moved = True
            elif a in out and b in out and a not in pending and b not in pending:
                out[name] = _check_derived(name, a, op, b, out)
                del pending[name]
                moved = True
        if not moved:
            name, (a, op, b) = next(iter(pending.items()))
            if a is None:
                raise SyntaxError(
                    f"type {name} is {scaled[name][0]} * {b}: {b} is not a "
                    f"distinct float -- a scaled unit is a multiple of one, "
                    f"declared `type {b} is distinct float`")
            bad = next((x for x in (a, b) if x not in out), a)
            raise SyntaxError(
                f"type {name} is {a} {op} {b}: {bad} is not a distinct "
                f"numeric type -- a derived unit is made from two of them, "
                f"declared `type {bad} is distinct float`")
    return out


# --- scaled units --------------------------------------------------------------
# `type Distance_in_km_T is 1000.0 * Distance_T` says one Distance_in_km_T is
# a thousand Distance_T. The two stay apart -- a km plus a metre is refused --
# and the conversions between them are made from the declaration:
# `Distance_in_km_T(d)` of a Distance_T divides by the factor, and
# `Distance_T(k)` of a Distance_in_km_T multiplies by it. The factor is fixed
# when the program is compiled, a number or a `const` float: a rate that
# changes as the program runs, euros per dollar, is a unit of its own
# (`type Rate_T is Euro_T / Dollar_T`) and a value of it is passed in.
# Only Nim builds them: see ady2py.

_SCALED = _re_du.compile(
    r"^(\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][-+]?\d+)?|[A-Za-z_]\w*)[ \t]*\*[ \t]*([A-Za-z_]\w*)$")


def scaled_units(decls, consts, known=None):
    """{name: (factor, base)} for every `type C is FACTOR * B` in DECLS,
    FACTOR a number or a name in CONSTS ({name: declared type or None}, the
    output of scan_consts). `A * B` between two types is a derived unit and
    not one of these; a name that is neither a type nor a float const
    raises SyntaxError. KNOWN is the distinct types an imported module
    declared."""
    known = known or {}
    out = {}
    for name, rhs in decls.items():
        m = _SCALED.match((rhs or "").strip())
        if not m:
            continue
        factor, base = m.group(1), m.group(2)
        if factor[0].isdigit():
            out[name] = (factor, base)
            continue
        if factor in decls or factor in known:
            continue                          # A * B: a derived unit
        if factor not in consts:
            raise SyntaxError(
                f"type {name} is {factor} * {base}: {factor} is not a const -- "
                f"the factor of a scaled unit is fixed when the program is "
                f"compiled, a number or a `const` float. A rate that changes "
                f"as it runs is a unit of its own, `type Rate_T is A / B`")
        ctype = consts[factor]
        if ctype not in (None, "float"):
            raise SyntaxError(
                f"type {name} is {factor} * {base}: {factor} is a {ctype} -- "
                f"the factor of a scaled unit is a plain number, a `const` "
                f"float")
        out[name] = (factor, base)
    return out


def _check_scaled(name, factor, base, kinds):
    """The kind of `type NAME is FACTOR * BASE`, or SyntaxError."""
    if kinds[base] != "float":
        raise SyntaxError(
            f"type {name} is {factor} * {base}: {base} is made of "
            f"{kinds[base]} -- a scaled unit is a multiple of a distinct "
            f"float, since converting to it divides")
    return "float"


def scaled_sources(target):
    """The units a conversion to TARGET takes and scales -- for a scaled
    unit its base, for a base the units scaled from it -- or None when
    TARGET is not in a scaled declaration, and `TARGET(x)` relabels."""
    from hek_parsec import ParserState
    scaled = getattr(ParserState, "scaled_units", None) or {}
    out = set()
    if target in scaled:
        out.add(scaled[target][1])
    out |= {n for n, (_, b) in scaled.items() if b == target}
    return out or None


def _check_derived(name, a, op, b, kinds):
    """The kind of `type NAME is A op B`, or SyntaxError if it cannot be."""
    ka, kb = kinds[a], kinds[b]
    if ka not in ("float", "int") or ka != kb:
        raise SyntaxError(
            f"type {name} is {a} {op} {b}: both must be distinct float, or "
            f"both distinct int -- {a} is made of {ka}, {b} of {kb}")
    if ka == "int" and op == "/":
        raise SyntaxError(
            f"type {name} is {a} / {b}: a quotient of ints is not an int -- "
            f"make the operands distinct float")
    if op == "/" and a == b:
        raise SyntaxError(
            f"type {name} is {a} / {a}: a ratio of one unit is a plain "
            f"number, and `{a} / {a}` already gives one")
    return ka


def derived_ops(name, a, op, b):
    """The operators `type NAME is A op B` defines, as (op, left, right,
    result): A / B is a NAME, so NAME * B and B * NAME are an A and A / NAME
    is a B; or A * B is a NAME, so NAME / A is a B and NAME / B an A. Where
    A and B are one type there is one of each."""
    if op == "/":
        return [("/", a, b, name), ("*", name, b, a),
                ("*", b, name, a), ("/", a, name, b)]
    if a == b:
        return [("*", a, a, name), ("/", name, a, a)]
    return [("*", a, b, name), ("*", b, a, name),
            ("/", name, a, b), ("/", name, b, a)]


def unit_relations(decls, scaled=None):
    """{(op, left, right): result} for what every derived unit in DECLS says
    about the operators between its units. Anything between two distinct
    types that is not here has no unit, and is refused. SCALED names the
    scaled units, `K * B`, which say nothing about operators."""
    rel = {}
    scaled = scaled or {}
    for name, rhs in decls.items():
        d = parse_derived(rhs) if rhs is not None and name not in scaled else None
        if d is None:
            continue
        for op, l, r, res in derived_ops(name, *d):
            if rel.setdefault((op, l, r), res) != res:
                raise SyntaxError(
                    f"type {name} is derived from the same units as "
                    f"{rel[(op, l, r)]}: `{l} {op} {r}` cannot be both")
    return rel


def unit_relation(op, left, right):
    """The unit of `left op right` where a derived unit says one, else None."""
    from hek_parsec import ParserState
    op = {"div": "/", "//": "/"}.get(op, op)
    return (getattr(ParserState, "unit_relations", None) or {}).get((op, left, right))


def is_distinct(name):
    """Whether NAME is a distinct type this module declares or imports."""
    from hek_parsec import ParserState
    return name in (getattr(ParserState, "distinct_types", None) or {})


def distinct_kind(name):
    """What a distinct type NAME is made of ("float", "int", ...), or None."""
    from hek_parsec import ParserState
    return (getattr(ParserState, "distinct_types", None) or {}).get(name)


# --- the unit of an expression -----------------------------------------------
# What an arithmetic expression is a quantity *of*, worked out from the
# emitted text of the backend -- `v * 2.0`, `d / t + w` -- so the same rules
# serve both. An operand is a distinct type's name, UNIT_LIT for a literal,
# UNIT_PLAIN for a value of a plain type, or None when the backend cannot
# tell. The rules are Ada's derived types with one change: `*` and `/`
# scale by a plain number, and between two units they mean what a derived
# unit says they mean, or nothing at all.
#
#   V + V, V - V, V mod V   -> V       (a literal beside a V is a V)
#   V * n, n * V, V / n     -> V       (n a plain number: a scale, not a V)
#   V / V                   -> plain   (a ratio has no unit)
#   A * B, A / B            -> as `type C is A * B` / `A / B` says, else none

UNIT_LIT = "<lit>"
UNIT_PLAIN = "<plain>"

_SAME_UNIT_OPS = ("+", "-", "mod", "%")
_SCALE_OPS = ("*", "/", "div", "//")
_COMPARE_OPS = ("<", ">", "<=", ">=", "==", "!=")
_LOW_OPS = {"and", "or", "not", "&", "|", "^", "in", "notin", "is", "isnot",
            "if", "else", "elif", "xor", "shl", "shr", "..", "..<", "&&",
            "==", "!=", "<", ">", "<=", ">=", "lambda", "for"}


def _top_tokens(expr):
    """EXPR split on the spaces outside any bracket or string, or None if
    its brackets or quotes do not balance."""
    toks, cur, depth, quote, esc = [], [], 0, "", False
    for ch in expr:
        if quote:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return None
            cur.append(ch)
        elif ch == " " and depth == 0:
            if cur:
                toks.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        toks.append("".join(cur))
    return toks if depth == 0 and not quote else None


def _strip_parens(expr):
    """EXPR without a pair of brackets that wraps all of it."""
    e = expr.strip()
    while e.startswith("(") and e.endswith(")"):
        depth, ok = 0, True
        for i, ch in enumerate(e):
            depth += ch in "(["
            depth -= ch in ")]"
            if depth == 0 and i < len(e) - 1:
                ok = False
                break
        if not ok:
            break
        e = e[1:-1].strip()
    return e


def split_arith(expr):
    """(left, op, right) at the operator of EXPR that binds last -- the
    rightmost `+` or `-`, else the rightmost `*`, `/`, `//`, `%`, `div` or
    `mod` -- or None when EXPR is no arithmetic expression: an atom, or
    something with a comparison, `and`, `if` ... at its top."""
    toks = _top_tokens(expr)
    if not toks or len(toks) < 3 or any(t in _LOW_OPS for t in toks):
        return None
    for group in (("+", "-"), ("*", "/", "//", "%", "div", "mod")):
        for i in range(len(toks) - 2, 0, -1):
            if toks[i] in group:
                return " ".join(toks[:i]), toks[i], " ".join(toks[i + 1:])
    return None


def expr_unit(expr, atom):
    """The unit of the emitted expression EXPR: a distinct type's name,
    UNIT_LIT, UNIT_PLAIN, or None. ATOM(text) says the same for anything
    that is not itself arithmetic -- a name, a call, a literal."""
    e = _strip_parens(expr)
    parts = split_arith(e)
    if parts is None:
        return atom(e)
    left, op, right = parts
    return unit_result(expr_unit(left, atom), op, expr_unit(right, atom))


def unit_result(lu, op, ru):
    """The unit of `l op r` given the units of l and r, or None if it has
    none (or the backend cannot tell)."""
    ld = bool(lu) and is_distinct(lu)
    rd = bool(ru) and is_distinct(ru)
    if not (ld or rd):
        if lu in (UNIT_LIT, UNIT_PLAIN) and ru in (UNIT_LIT, UNIT_PLAIN):
            return UNIT_LIT if lu == ru == UNIT_LIT else UNIT_PLAIN
        return None
    if op in _SAME_UNIT_OPS:
        if ld and rd:
            return lu if lu == ru else None
        return lu if ld else ru
    if op in _SCALE_OPS:
        if ld and rd:
            rel = unit_relation(op, lu, ru)
            if rel:
                return rel
            return UNIT_PLAIN if op != "*" and lu == ru else None
        if ld:
            return lu
        return ru if op == "*" else None
    return None


def unit_mix_error(lu, op, ru):
    """None, or why `l op r` is refused, given the units of l and r. What
    it cannot judge -- a side of unknown unit -- it leaves to the Nim
    compiler, which refuses every one of these itself."""
    ld = bool(lu) and is_distinct(lu)
    rd = bool(ru) and is_distinct(ru)
    if not (ld or rd):
        return None
    if op in _SAME_UNIT_OPS or op in _COMPARE_OPS:
        if ld and rd:
            if lu == ru:
                return None
            return (f"mixes a {lu} with a {ru}: a distinct type does not mix "
                    f"with any other -- convert one side explicitly")
        other, mine = (ru, lu) if ld else (lu, ru)
        if other == UNIT_PLAIN:
            return (f"mixes a {mine} with a plain number: a distinct type "
                    f"does not mix with any other -- convert one side "
                    f"explicitly")
        return None
    if op in _SCALE_OPS:
        if ld and rd:
            if unit_relation(op, lu, ru) or (op != "*" and lu == ru):
                return None
            verb = "multiplying" if op == "*" else "dividing"
            sign = "*" if op == "*" else "/"
            return (f"{verb} a {lu} by a {ru} has no unit: name the result "
                    f"with `type X is {lu} {sign} {ru}`")
        if rd and op != "*" and lu in (UNIT_LIT, UNIT_PLAIN):
            return (f"a plain number divided by a {ru} has no unit: name "
                    f"the result, `type X is A / {ru}`, with A a distinct type")
    return None


# --- type parameters are declared, never guessed ------------------------------
# `def first_of[Elem_T](xs: []Elem_T) -> Elem_T` declares its type parameter,
# and a generic class declares its own (`class Box[T]`). Nothing else is one.
# An older convention took any single capital in a signature -- `def f(xs:
# []T) -> T` -- as a type parameter without a word said; the reader had to
# know the rule to know that `T` was not a type of the program. Adascript is
# explicit: an undeclared name is an error, and the error shows the
# declaration to write.

def type_scope_push(names):
    """Enter a generic class or function: NAMES are its declared parameters,
    visible to every signature written inside it."""
    from hek_parsec import ParserState
    stack = getattr(ParserState, "_type_param_scope", None)
    if stack is None:
        stack = ParserState._type_param_scope = []
    stack.append(set(names))


def type_scope_pop():
    from hek_parsec import ParserState
    stack = getattr(ParserState, "_type_param_scope", None)
    if stack:
        stack.pop()


def type_scope_has(name):
    """Whether NAME is a type parameter declared by an enclosing class or
    function."""
    from hek_parsec import ParserState
    return any(name in scope for scope in getattr(ParserState, "_type_param_scope", ()))


def declared_param_names(text):
    """The names in a rendered `[T, U]` (or `T, U`) type-parameter list."""
    return {n.strip() for n in (text or "").strip("[] ").split(",") if n.strip()}


def refuse_undeclared_type_params(func_name, names):
    """SyntaxError if NAMES -- single capitals a signature uses that are no
    type, constant or declared parameter -- is not empty."""
    if not names:
        return
    ns = ", ".join(sorted(names))
    many = len(names) > 1
    raise SyntaxError(
        f"def {func_name}: {ns} in its signature {'are' if many else 'is'} "
        f"not declared -- write `def {func_name}[{ns}](...)`; Adascript does "
        f"not guess which names are type parameters")
