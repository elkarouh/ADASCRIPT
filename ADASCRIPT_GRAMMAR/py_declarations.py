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
    basic_type           = seq_type | callable_type | openarray_type
                         | array_type | enum_array_type
                         | dict_type | set_type | tuple_type
                         | primitive_type | type_name
    seq_type             = '[]' type_annotation
    array_type           = '[' INTEGER ']' type_annotation
    openarray_type       = '[*]' type_annotation
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

    Primitives:   str -> string, bytes -> seq[byte], None -> void
    Sequences:    []int -> seq[int]
    Arrays:       [5]int -> array[5, int]
    Open arrays:  [*]int -> openArray[int]
    Dicts:        {str}int -> Table[string, int]
    Sets:         {}int -> HashSet[int]
    Optionals:    ?int -> Option[int]
    Tuples:       (int, str) -> (int, string)
    Callables:    [(int, str)]bool -> proc(a0: int, a1: string): bool

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
from py3expr import expression

###############################################################################
# Tokens
###############################################################################

QUESTION = ignore(expect(tkn.OP, "?"))

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
tuple_type = fw("tuple_type")
multi_tuple_type = fw("multi_tuple_type")
singleton_tuple_type = fw("singleton_tuple_type")
empty_tuple_type = fw("empty_tuple_type")
primitive_type = fw("primitive_type")
type_name = fw("type_name")

###############################################################################
# Grammar rules
###############################################################################

# --- Primitives: int, str, float, bool, bytes, None ---
_PRIMITIVES = {"int", "str", "float", "bool", "bytes", "char", "None"}
primitive_type = filt(lambda s: s in _PRIMITIVES, IDENTIFIER)

# --- User-defined type name: any non-primitive identifier, including subscripts
# e.g. MyClass, List[int], Optional[str], Dict[str, int]
# We use the full Python primary expression so subscript trailers are consumed.
from py3expr import primary as _primary
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
seq_type = LBRACKET + RBRACKET + type_annotation

# [5]int            -> tuple[int, ...]
array_type = LBRACKET + INTEGER + RBRACKET + type_annotation

# [*]int            -> Sequence[int]  (unconstrained/open array)
openarray_type = LBRACKET + SSTAR + RBRACKET + type_annotation

# [EnumType]int      -> array[EnumType, int]  (enum-indexed array)
# Also accepts primitive ordinal types like char as array index
enum_array_type = LBRACKET + (type_name | primitive_type) + RBRACKET + type_annotation

# {str}int          -> dict[str, int]
dict_type = LBRACE + type_annotation + RBRACE + type_annotation

# {}int             -> set[int]
set_type = LBRACE + RBRACE + type_annotation

# [(int, str)]bool  -> Callable[[int, str], bool]
callable_type = LBRACKET + tuple_type + RBRACKET + type_annotation

# --- basic_type: a non-union, non-optional type ---
# Order matters: try container/callable before primitive/name (both start differently)
# callable_type before array_type (both start with '[', but callable has '(' after '[')
basic_type = (
    seq_type
    | callable_type
    | openarray_type
    | array_type
    | enum_array_type
    | dict_type
    | set_type
    | tuple_type
    | primitive_type
    | type_name
)

# --- Optional: ?int -> int | None ---
optional_type = QUESTION + basic_type
maybe_optional = optional_type | basic_type

# --- Union: int | str -> int | str ---
union_type = maybe_optional + (VBAR + maybe_optional)[1:]

# --- type_annotation: union or single type, with expression fallback ---
type_annotation = union_type | maybe_optional | expression

###############################################################################
def parse_type(source_code):
    """Parse a type annotation string."""
    inp = Input(source_code)
    result = type_annotation.parse(inp)
    if result is None:
        return None
    return result[0]

