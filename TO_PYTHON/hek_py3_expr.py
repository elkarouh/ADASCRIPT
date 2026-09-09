#!/usr/bin/env python3
"""Python 3.14 Expression Parser using hek_parsec combinator framework.

Implements the Python 3.14 expression grammar with correct operator
precedence, rewritten from PEG left-recursive form into iterative
right-recursive form suitable for hek_parsec.

Precedence (low to high):
    lambda, if/else, :=, or, and, not, comparisons, |, ^, &, <</>>,
    +/-, */%//@, unary +/-/~, **, await, atom+trailers

New in Python 3.x (vs 2.7):
    - walrus operator:  x := expr
    - await expression: await f()
    - matmul operator:  a @ b
    - f-strings:        f"hello {name}"
    - ellipsis literal: ...
    - set literals:     {1, 2, 3}
    - comprehensions:   [x for x in xs], {k:v for k,v in d}, {x for x in s}
    - star expressions: *x in calls and displays
    - extended slicing:  a[1:2:3]
    - yield expressions: yield x, yield from x

Removed from Python 2:
    - <> operator, backtick repr, 123L long literals

Usage:
    ast, rest = expression.parse(Input("1 + 2 * 3"))
    print(ast.to_py())  # (1 + (2 * 3))
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))

from py3expr import *
from hek_parsec import method, ParserState



def _get_bracket_start(node):
    """Extract the (line, col) start position from a bracket node."""
    if hasattr(node, 'nodes') and node.nodes:
        tok = node.nodes[0]
        if hasattr(tok, 'start'):
            return tok.start
    if hasattr(node, 'start'):
        return node.start
    return None


###############################################################################
# Bashism resolution helpers
###############################################################################

def binop_to_py(self, prec=None, my_prec=None):
    """Generic to_py for left-associative binary operators.

    Due to Sequence flattening, inner rule nodes may be inlined.
    e.g. sum_expr parsing 'a * b + c' produces:
      nodes = [power(a), Several_Times[(*,b)], Several_Times[(+,c)]]
    where the first Several_Times is from term (inner) and the second
    is from sum_expr (this level).

    Strategy: find the LAST Several_Times with (op, operand) pairs —
    that's ours. Everything before it is the base (first operand),
    reconstructed by calling binop_to_py on a synthetic node.

    Args:
        prec: parent context's precedence (None = no wrapping needed)
        my_prec: this operator's precedence level
    """
    # Find the last Several_Times that has (op, operand) pairs
    last_st_idx = None
    for i in range(len(self.nodes) - 1, -1, -1):
        node = self.nodes[i]
        if (
            type(node).__name__ == "Several_Times"
            and hasattr(node, "nodes")
            and node.nodes
        ):
            first_seq = node.nodes[0]
            if hasattr(first_seq, "nodes") and len(first_seq.nodes) >= 2:
                last_st_idx = i
                break

    if last_st_idx is None:
        # No operator repetitions, just delegate to child
        return self.nodes[0].to_py(prec)

    # Reconstruct the base from nodes before last_st_idx
    # Left child gets my_prec (same precedence, left-assoc = no parens)
    left_prec = my_prec
    if last_st_idx == 1:
        result = self.nodes[0].to_py(left_prec)
    else:
        # Inner nodes were flattened; rebuild by calling binop_to_py
        # on a mock with just the prefix nodes
        class _Mock:
            pass

        mock = _Mock()
        mock.nodes = self.nodes[:last_st_idx]
        result = binop_to_py(mock, left_prec, my_prec)

    # Apply our (op, operand) pairs
    # Right child gets my_prec+1 (forces parens for same-precedence right operands)
    right_prec = my_prec + 1 if my_prec is not None else None
    st = self.nodes[last_st_idx]
    for seq in st.nodes:
        if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
            op = seq.nodes[0].to_py()
            right = seq.nodes[1].to_py(right_prec)
            result = f"{result} {op} {right}"

    # Only wrap in parens if parent context requires higher precedence
    if prec is not None and my_prec is not None and my_prec < prec:
        return f"({result})"
    return result


###############################################################################
# to_py() methods
###############################################################################


# --- leaf tokens ---
@method(NUMBER)
def to_py(self, prec=None):
    """NUMBER: a numeric literal token."""
    return self.node


@method(STRING)
def to_py(self, prec=None):
    """STRING: a string literal token."""
    return self.node


@method(fstring)
def to_py(self, prec=None):
    """fstring: FSTRING_START FSTRING_MIDDLE? ('{' expr '}' FSTRING_MIDDLE?)* FSTRING_END

    Reassemble by collecting the raw token strings from all nodes.
    FSTRING_START/MIDDLE/END nodes are Fmap nodes (str); expression nodes have to_py().
    OP nodes for { and } are Fmap nodes (str).
    """
    parts = []
    def _collect(node):
        tname = type(node).__name__
        if tname == "Fmap":
            parts.append(node.node)
        elif tname in ("Several_Times", "Sequence_Parser"):
            for child in node.nodes:
                _collect(child)
        elif hasattr(node, "to_py"):
            parts.append(node.to_py())
        elif hasattr(node, "node"):
            parts.append(node.node)
    for node in self.nodes:
        _collect(node)
    return "".join(parts)


@method(IDENTIFIER)
def to_py(self, prec=None):
    """IDENTIFIER: a name token (filtered by str.isidentifier)."""
    name = self.node
    if name == "stdin":
        ParserState.nim_imports.add("import sys")
        return "sys.stdin"
    return name


@method(K_NONE)
def to_py(self, prec=None):
    """K_NONE: 'None'"""
    return "None"


@method(K_TRUE)
def to_py(self, prec=None):
    """K_TRUE: 'True'"""
    return "True"


@method(K_FALSE)
def to_py(self, prec=None):
    """K_FALSE: 'False'"""
    return "False"


@method(ellipsis_lit)
def to_py(self, prec=None):
    """ellipsis_lit: '...'"""
    return "..."


# Visible operators — all just return their string
for _p in [
    V_PLUS,
    V_MINUS,
    V_STAR,
    V_SLASH,
    V_PERCENT,
    V_DSLASH,
    V_DSTAR,
    V_TILDE,
    V_AT,
    V_PIPE,
    V_CARET,
    V_AMPER,
    V_LSHIFT,
    V_RSHIFT,
    V_LT,
    V_GT,
    V_EQ,
    V_NE,
    V_LE,
    V_GE,
    V_COLONEQUAL,
    SSTAR,
    K_AND,
    K_OR,
    K_NOT,
    K_IN,
    K_IS,
]:

    @method(_p)
    def to_py(self, prec=None):
        """Visible operator token: returns operator string unchanged."""
        return self.node


# --- str_concat ---
@method(str_concat)
def to_py(self, prec=None):
    """str_concat: STRING STRING+"""
    parts = [self.nodes[0].to_py()]
    rep = self.nodes[1]
    if hasattr(rep, "nodes"):
        parts.extend(n.to_py() for n in rep.nodes)
    else:
        parts.append(rep.to_py())
    return " ".join(parts)


# --- atom containers ---

# Registry: frozenset of field names -> type name, for named tuple constructor emission
_named_tuple_registry = {}  # {frozenset(field_names): type_name}

def _register_named_tuple(type_name, field_names):
    """Register a NamedTuple type so named_tuple_lit can emit constructors."""
    _named_tuple_registry[frozenset(field_names)] = type_name

def _lookup_named_tuple(field_names):
    """Look up a NamedTuple type by its field names."""
    return _named_tuple_registry.get(frozenset(field_names))

def _has_named_tuple(node):
    """Check if node tree contains named_tuple_field nodes needing transformation."""
    if type(node).__name__ == "named_tuple_field":
        return True
    if hasattr(node, "nodes"):
        return any(_has_named_tuple(c) for c in node.nodes)
    return False

@method(empty_paren)
def to_py(self, prec=None):
    """empty_paren: '(' ')'"""
    return "()"


def _keep_layout(pos, ml, rendered):
    """The source's own layout when it says the same thing, else the render.

    A bracketed expression spanning lines is emitted as the source wrote it,
    which keeps a long call or a table literal readable instead of collapsing
    it onto one line.  The catch is that the source is *Adascript*: anything
    the backend had to translate — `xs'Length`, `readFile(p)`, `run(argv)`,
    a named-tuple literal — is still in Adascript spelling in that text, and
    went into the Python output untranslated, to fail at import or at run
    time depending on which line it was.

    So the raw span is used only where it agrees with what the tree renders,
    whitespace aside.  Where they differ something was translated, and the
    translation wins even though the layout is lost.  That is the right way
    round: a long line is ugly, a wrong line is a bug.
    """
    raw = ml.get(pos)
    if raw is None:
        return rendered
    return raw if _same_but_for_layout(raw, rendered) else rendered


def _same_but_for_layout(raw, rendered):
    """True when two spellings differ only in whitespace and trailing commas.

    The trailing comma matters: a table literal written one entry per line
    almost always has one, the renderer does not emit it, and treating that
    as a difference would collapse exactly the literals whose layout was
    worth keeping.
    """
    def norm(s):
        s = "".join(s.split())
        for close in ")]}":
            s = s.replace("," + close, close)
        return s
    return norm(raw) == norm(rendered)


@method(paren_group)
def to_py(self, prec=None):
    """paren_group: '(' (yield_expr | walrus | expressions) ')'
    Explicit parens from source — always preserved."""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    rendered = f"({self.nodes[1].to_py()})"
    if pos and pos in ml and not _has_named_tuple(self):
        return _keep_layout(pos, ml, rendered)
    return rendered


@method(empty_list)
def to_py(self, prec=None):
    """empty_list: '[' ']'"""
    return "[]"


@method(list_display)
def to_py(self, prec=None):
    """list_display: '[' (listcomp | star_expressions) ']'"""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    rendered = f"[{self.nodes[1].to_py()}]"
    if pos and pos in ml and not _has_named_tuple(self):
        return _keep_layout(pos, ml, rendered)
    return rendered


@method(empty_set)
def to_py(self, prec=None):
    """empty_set: '{' '}' -> Python: set()

    Adascript treats {} as an empty set literal.  Python's {} creates an empty
    dict, so we always emit set() here.  Use type annotations on the variable
    to convey the element type; the Nim backend reads those to pick the right
    Nim initialiser.
    """
    return "set()"


@method(empty_dict)
def to_py(self, prec=None):
    """empty_dict: '{' ':' '}' -> Python: {}

    Adascript uses {:} as the empty dict literal to free up {} for empty sets.
    """
    return "{}"


@method(dict_display)
def to_py(self, prec=None):
    """dict_display: '{' (dictcomp | dictmaker) '}'"""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    rendered = "{" + self.nodes[1].to_py() + "}"
    if pos and pos in ml and not _has_named_tuple(self):
        return _keep_layout(pos, ml, rendered)
    return rendered


@method(enum_array_display)
def to_py(self, prec=None):
    """enum_array_display: '[' enum_key ':' value (',' enum_key ':' value)* ']' -> Python: dict {K: V, ...}"""
    from hek_py_declarations import _ensure_enum_array_alias
    _ensure_enum_array_alias()
    return "_EnumArray({" + self.nodes[1].to_py() + "})"


@method(set_display)
def to_py(self, prec=None):
    """set_display: '{' (setcomp | setmaker) '}'"""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    rendered = "{" + self.nodes[1].to_py() + "}"
    if pos and pos in ml and not _has_named_tuple(self):
        return _keep_layout(pos, ml, rendered)
    return rendered


@method(atom)
def to_py(self, prec=None):
    """atom: empty_paren | paren_group | empty_list | list_display
    | empty_set | empty_dict | dict_display | set_display | '...'
    | 'None' | 'True' | 'False' | IDENTIFIER | NUMBER
    | str_concat | STRING"""
    return self.nodes[0].to_py(prec)


# --- trailers ---
@method(call_trailer)
def to_py(self, prec=None):
    """call_trailer: '(' arguments? ')'"""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    if len(self.nodes) > 1 and hasattr(self.nodes[1], "nodes") and self.nodes[1].nodes:
        rendered = "(" + self.nodes[1].nodes[0].to_py() + ")"
    elif len(self.nodes) > 1 and hasattr(self.nodes[1], "to_py"):
        rendered = "(" + self.nodes[1].to_py() + ")"
    else:
        rendered = "()"
    if pos and pos in ml and not _has_named_tuple(self):
        return _keep_layout(pos, ml, rendered)
    return rendered


@method(slice_trailer)
def to_py(self, prec=None):
    """slice_trailer: '[' slices ']'"""
    return "[" + self.nodes[0].to_py() + "]"


@method(attr_trailer)
def to_py(self, prec=None):
    """attr_trailer: '.' IDENTIFIER"""
    attr_name = self.nodes[0].node if hasattr(self.nodes[0], 'node') else str(self.nodes[0])
    # .lines on a file/stdin is a Nim-ism; Python files are directly iterable
    if attr_name == "lines":
        return ""
    return "." + self.nodes[0].to_py()


_SHUFFLE_HELPER = '''\
def _adascript_shuffle(_x):
    """expr'Shuffle: shuffle in place, and return the container.

    Both halves matter. It returns, because 'Shuffle is an expression and is
    routinely the last one in a function -- the Nim backend spells the same
    thing `(block: shuffle(x); x)`. And it mutates, because callers may hold
    another reference.

    An ordinal-indexed array `[O]T` is a dict on this backend and an array
    on Nim, so shuffling one means permuting the values while the domain
    stays where it is; random.shuffle on the dict itself raises KeyError.
    """
    import random as _r
    if isinstance(_x, dict):
        _vals = list(_x.values())
        _r.shuffle(_vals)
        _x.update(zip(list(_x.keys()), _vals))
        return _x
    _r.shuffle(_x)
    return _x\
'''


def _ensure_shuffle_helper():
    """Define _adascript_shuffle the first time 'Shuffle is used."""
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("_adascript_shuffle" in d for d in decls):
        decls.append(_SHUFFLE_HELPER)
        ParserState.py_top_decls = decls


# The queue types from TO_NIM/STDLIB/stdlib.nim, as Python.  Nim gets them
# from the shim it compiles against; here they are emitted into the output so
# it stays a single self-contained file, the same way _adascript_shuffle is.
#
# Each mirrors the Nim object's surface exactly -- push, pop, len, and
# truthiness, so `while queue:` reads the same on both backends.
_QUEUE_HELPERS = {
    "PriorityQueue": '''\
class PriorityQueue:
    """Min-heap, ordered on the first element of each item.

    heapq is the natural fit: Nim's version is a hand-written binary heap
    over `data[i][0]`, which is heapq's ordering with the payload carried
    along.  The counter is not decoration -- heapq falls through to the next
    tuple element when priorities tie, and the next element here is a node,
    which for an enum or a record raises TypeError rather than ordering.
    The counter is unique and always comparable, so the tie is settled
    before the payload is ever reached, and equal priorities come out in
    push order.
    """

    def __init__(self, first=None):
        import itertools as _it
        self._counter = _it.count()
        self._heap = []
        if first is not None:
            self.push(first)

    def push(self, item):
        import heapq as _hq
        _hq.heappush(self._heap, (item[0], next(self._counter), item[1:]))

    def pop(self):
        import heapq as _hq
        priority, _count, rest = _hq.heappop(self._heap)
        return (priority,) + rest

    def __len__(self):
        return len(self._heap)

    def __bool__(self):
        return bool(self._heap)\
''',
    "FifoQueue": '''\
class FifoQueue:
    """First in, first out.  Nim backs this with a Deque; so do we."""

    def __init__(self, first=None):
        from collections import deque as _dq
        self._items = _dq()
        if first is not None:
            self.push(first)

    def push(self, item):
        self._items.append(item)

    def pop(self):
        return self._items.popleft()

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)\
''',
    "LifoQueue": '''\
class LifoQueue:
    """Last in, first out -- a stack."""

    def __init__(self, first=None):
        self._items = []
        if first is not None:
            self.push(first)

    def push(self, item):
        self._items.append(item)

    def pop(self):
        return self._items.pop()

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)\
''',
}


_ANY_HELPER = '''\
class _Any:
    """The ANY wildcard: compares equal to everything.

    Nim gets this from three `==` overloads on AnyType.  Python needs only
    the one, because when `x == ANY` finds x's own __eq__ returning
    NotImplemented it retries with the operands swapped -- but defining
    __eq__ drops the inherited __hash__, so that is restored explicitly or
    ANY could not be a dict key or set member.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __eq__(self, _other):
        return True

    def __hash__(self):
        return hash("ANY")

    def __repr__(self):
        return "ANY"


ANY = _Any()\
'''


def ensure_queue_helper(name):
    """Define one of the stdlib queue classes the first time it is used.

    Returns True when `name` is a queue type this backend supplies, so
    callers can also use it as the membership test.
    """
    if name not in _QUEUE_HELPERS:
        return False
    decls = getattr(ParserState, 'py_top_decls', [])
    marker = "class %s:" % name
    if not any(marker in d for d in decls):
        decls.append(_QUEUE_HELPERS[name])
        ParserState.py_top_decls = decls
    return True


# Everything this backend can supply in place of `from stdlib import ...`.
# Checked before anything is emitted, so a statement naming one supplied and
# one unsupplied thing does not leave a stray class definition behind.
STDLIB_SUPPLIED = frozenset(_QUEUE_HELPERS) | {"ANY"}


def ensure_stdlib_helper(name):
    """Define anything `from stdlib import ...` names that we supply here.

    Returns True if the name was supplied, so the import emitter can tell
    whether the statement still has to be carried into the output.
    """
    if ensure_queue_helper(name):
        return True
    if name == "ANY":
        decls = getattr(ParserState, 'py_top_decls', [])
        if not any("class _Any:" in d for d in decls):
            decls.append(_ANY_HELPER)
            ParserState.py_top_decls = decls
        return True
    return False


def _tick_to_py(expr, attr):
    """Render `expr'attr` for the Python backend.

    Mirrors _tick_to_nim in the Nim backend, including the distinction that
    matters most: a tick on a *type name* asks about the type's domain,
    while the same tick on any other expression asks about the value. That
    is why the type case is tried first -- `Color'First` is the first
    member, where `xs'First` is the index 0.

    Unknown attributes raise rather than falling through. The catch-all this
    replaced handed anything it did not recognise to the Next/Prev codegen,
    so `E'Range` and `x'choose` silently emitted `type(x)(x.value - 1)` --
    which parses, runs, and is nonsense.
    """
    info = getattr(ParserState, "tick_types", {}).get(expr)
    if info is not None:
        if attr in ("First", "Low"):
            return str(info["First"])
        if attr in ("Last", "High"):
            return str(info["Last"])
        if attr == "Range":
            if "members" in info:
                # An enum's range is the set of its members, matching the
                # Nim backend's {E.low..E.high}. A set is also what the
                # annotation says it is -- `{}Door_T` -- so set arithmetic
                # (`E'Range - {x}`) works and the order is not promised.
                return f"set({expr})"
            if info.get("is_float_range"):
                raise ValueError(
                    f"'Range is not defined for the float subrange {expr!r}: "
                    "a float interval has no enumerable domain")
            return f"range({info['First']}, {info['Last']} + 1)"
        if attr == "choose":
            ParserState.nim_imports.add("import random as _random")
            return f"_random.choice(list({expr}))"
    if attr in ("Length", "len"):
        return f"len({expr})"
    if attr in ("First", "Low"):
        return "0"
    if attr in ("Last", "High"):
        return f"(len({expr}) - 1)"
    if attr == "Range":
        # On a value rather than a type: its index range, matching the Nim
        # backend's non-enum `expr.low..expr.high`. `for i in word'Range`
        # walks the positions of a string or sequence.
        return f"range(len({expr}))"
    if attr == "Image":
        return f"({expr}).name"
    if attr == "Next":
        return f"type({expr})({expr}.value + 1)"
    if attr == "Prev":
        return f"type({expr})({expr}.value - 1)"
    if attr == "choose":
        # list() so a set, a range and a seq all work, as they do on Nim.
        ParserState.nim_imports.add("import random as _random")
        return f"_random.choice(list({expr}))"
    if attr == "Shuffle":
        _ensure_shuffle_helper()
        return f"_adascript_shuffle({expr})"
    raise ValueError(
        f"unknown tick attribute {attr!r} in {expr}'{attr}. Known: "
        "First, Last, Range, Next, Prev, choose, Shuffle, Image, Length")


@method(tick_trailer)
def to_py(self, prec=None):
    """tick_trailer: TICK IDENTIFIER -> stored as _tick_attr for primary to consume"""
    attr = self.nodes[0].node if hasattr(self.nodes[0], 'node') else str(self.nodes[0])
    if attr in ("len", "Length"):
        self._tick_attr = "Length"
    else:
        self._tick_attr = attr
    return ""


@method(trailer)
def to_py(self, prec=None):
    """trailer: call_trailer | slice_trailer | attr_trailer | tick_trailer"""
    return self.nodes[0].to_py()


# --- primary: atom + trailer[:] ---
# --- Nim's stream objects --------------------------------------------------
#
# stderr, stdout and stdin are Nim names.  Emitted unchanged they raise
# NameError on the first call, since Python keeps the streams on `sys`.
_STREAM_CALLS = (
    ("stderr", "writeLine", lambda a: f"print({a}, file=sys.stderr)"
                                      if a.strip() else "print(file=sys.stderr)"),
    ("stdout", "writeLine", lambda a: f"print({a})"),
    ("stderr", "write",     lambda a: f"sys.stderr.write({a})"),
    ("stdout", "write",     lambda a: f"sys.stdout.write({a})"),
    ("stderr", "flushFile", lambda a: "sys.stderr.flush()"),
    ("stdout", "flushFile", lambda a: "sys.stdout.flush()"),
    ("stdin",  "readLine",  lambda a: "input()"),
)


# --- Nim's whole-file builtins ---------------------------------------------
#
# readFile/writeFile are Nim names, so Python needs its own pair.  Nim strings
# hold bytes; surrogateescape is what lets the Python side read and rewrite a
# file it cannot decode, rather than raising where Nim would not.
_FILE_HELPERS = '''\
def _read_file(_path):
    """Nim's readFile: the whole file, as text."""
    with open(_path, encoding="utf-8", errors="surrogateescape") as _f:
        return _f.read()


def _write_file(_path, _text):
    """Nim's writeFile: replace the file's contents."""
    with open(_path, "w", encoding="utf-8", errors="surrogateescape") as _f:
        _f.write(_text)\
'''


def _ensure_file_helpers():
    """Inject the file helpers the first time readFile/writeFile is seen."""
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("_read_file" in d for d in decls):
        decls.append(_FILE_HELPERS)
        ParserState.py_top_decls = decls


def _file_helper_call(name, call_trailer):
    """`readFile(args)` -> `_read_file(args)`, or None if not that shape.

    CALL_TRAILER is the rendered `(...)` that follows the name.  The rewrite
    happens as the trailer is consumed, not on the finished expression, so
    that anything chained onto it -- `readFile(p).strip()` -- still works.
    """
    if not (call_trailer.startswith("(") and call_trailer.endswith(")")):
        return None
    if not call_trailer[1:-1].strip():
        return None
    _ensure_file_helpers()
    return f"_{'read' if name == 'readFile' else 'write'}_file{call_trailer}"


def _run_argv_call(name, call_trailer):
    """`run(argv, ...)` -> `_run_argv(argv, ...)`, or None if not that shape.

    The keyword options are spelled the same as the helper's parameters --
    cwd, env, stdin, timeout, check -- so the trailer passes through as
    written; only `runLines` needs anything added.  Rewritten as the trailer
    is consumed, like readFile, so `run(argv).output` still chains.
    """
    if not (call_trailer.startswith("(") and call_trailer.endswith(")")):
        return None
    inner = call_trailer[1:-1].strip()
    if not inner:
        return None
    # `stdin = x` is a keyword here, but the trailer has already been through
    # the stdlib rewrite that turns a bare `stdin` into `sys.stdin`, which is
    # not a name a keyword argument may have.  Put it back -- only where it
    # is a keyword, never where someone really is passing sys.stdin along.
    import re as _re_r
    inner = _re_r.sub(r'(?<![\w.])sys\.stdin(\s*)=(?!=)', r'stdin\1=', inner)
    from hek_py3_parser import _ensure_run_argv_helper
    _ensure_run_argv_helper()
    if name == "runLines":
        return f"_run_argv({inner}, _lines=True)"
    return f"_run_argv({inner})"


_HAVE_HELPER = '''\
def _have(_name):
    """True when _name is a program on PATH.

    The shell answer is `command -v x` and knowing that 127 means no, which
    costs a process and a shell to ask a question PATH already answers.
    """
    import shutil as _shutil
    return _shutil.which(_name) is not None\
'''


def _have_call(call_trailer):
    """`have(x)` -> `_have(x)`, or None if not that shape."""
    if not (call_trailer.startswith("(") and call_trailer.endswith(")")):
        return None
    if not call_trailer[1:-1].strip():
        return None
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("def _have(" in d for d in decls):
        decls.append(_HAVE_HELPER)
        ParserState.py_top_decls = decls
    return "_have" + call_trailer


_ENUM_RANGE_HELPER = '''\
def _ada_enum_range(_lo, _hi, _inclusive=True):
    """The members from _lo to _hi, the way Nim's `lo .. hi` walks an enum.

    Python's range is integers only, so an enum-bounded range has no
    builtin to fall back on.  Positions are taken by looking the members
    up, which stays right for an enum that names its own values.
    """
    _members = list(type(_lo))
    _start = _members.index(_lo)
    _stop = _members.index(_hi) + (1 if _inclusive else 0)
    return _members[_start:_stop]\
'''


def _enum_member_owner(text):
    """The enum a member name belongs to, or None.

    Only the two spellings the emitter itself writes are recognised -- the
    bare alias and the qualified `E.MEMBER` -- because the type of an
    arbitrary expression is not known here.
    """
    from hek_parsec import ParserState
    t = (text or "").strip()
    if not t:
        return None
    tick = getattr(ParserState, "tick_types", {})
    if "." in t:
        head, _, tail = t.rpartition(".")
        info = tick.get(head)
        if info and tail in (info.get("members") or ()):
            return head
        return None
    for enum_type, info in tick.items():
        if t in (info.get("members") or ()):
            return enum_type
    return None


def _ensure_enum_range_helper():
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("def _ada_enum_range(" in d for d in decls):
        decls.append(_ENUM_RANGE_HELPER)
        ParserState.py_top_decls = decls


def range_bounds_to_py(lo, hi, op_val):
    """`lo .. hi` / `lo ..< hi` as a Python iterable.

    An enum-bounded range -- `Stage_T'First .. Stage_T'Last` -- is written
    exactly like an integer one and means the same thing on Nim, but
    Python's range() takes integers: it used to emit `range(STAGE1, STAGE3
    + 1)` and die on the addition.
    """
    _owner = _enum_member_owner(lo)
    if _owner is not None and _enum_member_owner(hi) == _owner:
        _ensure_enum_range_helper()
        if op_val == "..<":
            return f"_ada_enum_range({lo}, {hi}, False)"
        return f"_ada_enum_range({lo}, {hi})"
    if op_val == "..<":
        return f"range({lo}, {hi})"
    return f"range({lo}, {hi} + 1)"


def _builtin_ordinal_domain(name):
    """`bool` / `char` as something to iterate, or None for anything else.

    A named ordinal type is already iterable on this backend -- an enum is a
    class, a subrange is a `range` object -- so `for c in Color` needs no
    help.  These two are spelled as builtins and are not, though Nim
    iterates them like any other ordinal.
    """
    from hek_parsec import ParserState
    if name not in ("bool", "char"):
        return None
    if ParserState.symbol_table.lookup(name):
        return None
    if name == "bool":
        return "(False, True)"
    return "(chr(_i) for _i in range(256))"


_ORD_HELPER = '''\
def _ada_ord(_x):
    """The ordinal position of an ordinal value, as Nim's `ord` gives it.

    Python's builtin is the character case alone -- it takes a
    one-character string and nothing else.  Adascript has more ordinals
    than that: an enum member's position is its value, and an int is
    already its own.  A bool is an int in Python, so it needs converting
    or `ord(True)` prints as True rather than 1.
    """
    _v = getattr(_x, "value", _x)
    if isinstance(_v, bool):
        return int(_v)
    if isinstance(_v, int):
        return _v
    return ord(_v)\
'''


def _ord_call(call_trailer):
    """`ord(x)` -> `_ada_ord(x)`, or None if not that shape."""
    if not (call_trailer.startswith("(") and call_trailer.endswith(")")):
        return None
    if not call_trailer[1:-1].strip():
        return None
    from hek_parsec import ParserState
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("def _ada_ord(" in d for d in decls):
        decls.append(_ORD_HELPER)
        ParserState.py_top_decls = decls
    return "_ada_ord" + call_trailer


def _translate_dir_call(expr):
    """Make directory creation idempotent, or return None.

    Both `os.makedirs` and `os.mkdir` map to Nim's `createDir`, which creates
    the whole path and, in Nim's words, "does not fail if the directory
    already exists".  Python's raise `FileExistsError` in that case, so the
    same source behaves differently on the two backends unless the call is
    emitted as `os.makedirs(..., exist_ok=True)`.
    """
    import re as _re_d
    from hek_parsec import ParserState
    m = _re_d.match(r'^os\.(?:makedirs|mkdir)\((.*)\)$', expr, _re_d.DOTALL)
    if not m or "exist_ok" in m.group(1):
        return None
    args = m.group(1).strip()
    if not args:
        return None
    # The call we emit needs the module, even where the source said
    # `nimport os` and meant it only for the Nim side.
    ParserState.nim_imports.add("import os")
    return f"os.makedirs({args}, exist_ok=True)"


def _translate_stream_call(stream, expr):
    """Rewrite a call on a Nim stream object onto `sys`, or return None."""
    import re as _re_s
    from hek_parsec import ParserState
    for name, meth, build in _STREAM_CALLS:
        if name != stream:
            continue
        m = _re_s.match(rf'^{name}\.{meth}\((.*)\)$', expr, _re_s.DOTALL)
        if m:
            ParserState.nim_imports.add("import sys")
            return build(m.group(1))
    return None


@method(primary)
def to_py(self, prec=None):
    """primary: atom trailer*"""
    from hek_parsec import ParserState
    result = self.nodes[0].to_py()
    # drop(x) -> del x  (Python: GC can't do deterministic drop, del is closest)
    if result == "drop" and len(self.nodes) > 1:
        trailers = self.nodes[1].nodes if hasattr(self.nodes[1], "nodes") else []
        if trailers and trailers[0].to_py().startswith("(") and trailers[0].to_py().endswith(")"):
            arg = trailers[0].to_py()[1:-1]
            return f"del {arg}"
    # move(x) -> x  (Python: assignment already moves under GC)
    if result == "move" and len(self.nodes) > 1:
        trailers = self.nodes[1].nodes if hasattr(self.nodes[1], "nodes") else []
        if trailers and trailers[0].to_py().startswith("(") and trailers[0].to_py().endswith(")"):
            return trailers[0].to_py()[1:-1]
    if len(self.nodes) > 1 and hasattr(self.nodes[1], "nodes") and self.nodes[1].nodes:
        trailers = self.nodes[1].nodes
        i = 0
        while i < len(trailers):
            tr = trailers[i]
            tr_str = tr.to_py()
            # .get() on an Optional-typed variable is a no-op in Python (value is already unwrapped)
            # Parsed as two trailers: attr_trailer(".get") + call_trailer("()")
            if i == 0 and result in ("readFile", "writeFile"):
                helper = _file_helper_call(result, tr_str)
                if helper is not None:
                    result = helper
                    i += 1
                    continue
            if i == 0 and result in ("run", "runLines"):
                helper = _run_argv_call(result, tr_str)
                if helper is not None:
                    result = helper
                    i += 1
                    continue
            if i == 0 and result == "have":
                helper = _have_call(tr_str)
                if helper is not None:
                    result = helper
                    i += 1
                    continue
            if i == 0 and result == "ord":
                helper = _ord_call(tr_str)
                if helper is not None:
                    result = helper
                    i += 1
                    continue
            if i == 0 and result == "waitAll" and tr_str.startswith("("):
                from hek_py3_parser import _ensure_spawn_helper
                _ensure_spawn_helper()
                result = "_wait_all" + tr_str
                i += 1
                continue
            if tr_str == ".maxIndex":
                result = f"{result}.index(max({result}))"
                i += 1
                continue
            if (tr_str == ".get"
                    and i + 1 < len(trailers)
                    and trailers[i + 1].to_py() == "()"):
                _sym = ParserState.symbol_table.lookup(result)
                _sym_type = (_sym.get("type", "") if isinstance(_sym, dict) else "") if _sym else ""
                if "Option[" in _sym_type or "| None" in _sym_type:
                    i += 2  # skip both .get and ()
                    continue
            result += tr_str
            # Handle tick attributes on expressions
            if hasattr(tr, '_tick_attr'):
                result = _tick_to_py(result, tr._tick_attr)
            i += 1
    atom_name = self.nodes[0].to_py()
    if atom_name in ("stderr", "stdout", "stdin"):
        translated = _translate_stream_call(atom_name, result)
        if translated is not None:
            return translated
    if atom_name == "os":
        translated = _translate_dir_call(result)
        if translated is not None:
            return translated
    return result


# --- await ---
@method(await_expr)
def to_py(self, prec=None):
    """await_expr: 'await' primary"""
    return f"await {self.nodes[0].to_py()}"


@method(await_primary)
def to_py(self, prec=None):
    """await_primary: await_expr | primary"""
    return self.nodes[0].to_py(prec)


# --- bash file-test operators ---
@method(file_test)
def to_py(self, prec=None):
    """file_test: BASH_TEST IDENTIFIER primary -> Python os.path.* / os.access call."""
    from hek_parsec import ParserState
    flag = self.nodes[1].node   # IDENTIFIER node: 'e', 'f', 'd', etc.
    path = self.nodes[2].to_py()
    ParserState.nim_imports.add("import os")
    if flag == "e":
        return f"os.path.exists({path})"
    elif flag == "f":
        return f"os.path.isfile({path})"
    elif flag == "d":
        return f"os.path.isdir({path})"
    elif flag == "L":
        return f"os.path.islink({path})"
    elif flag == "r":
        return f"os.access({path}, os.R_OK)"
    elif flag == "w":
        return f"os.access({path}, os.W_OK)"
    elif flag == "x":
        return f"os.access({path}, os.X_OK)"
    elif flag == "s":
        return f"(os.path.getsize({path}) > 0)"
    elif flag == "c":
        ParserState.nim_imports.add("import stat")
        return f"stat.S_ISCHR(os.stat({path}).st_mode)"
    elif flag == "b":
        ParserState.nim_imports.add("import stat")
        return f"stat.S_ISBLK(os.stat({path}).st_mode)"
    elif flag == "p":
        ParserState.nim_imports.add("import stat")
        return f"stat.S_ISFIFO(os.stat({path}).st_mode)"
    elif flag == "S":
        ParserState.nim_imports.add("import stat")
        return f"stat.S_ISSOCK(os.stat({path}).st_mode)"
    return f"os.path.exists({path})"  # fallback


@method(BASH_CMP)
def to_py(self, prec=None):
    """BASH_CMP: '-nt' or '-ot' token -> forwarded to comparison handler"""
    return self.node  # already the string "-nt" or "-ot"


# --- dollar variables: $0, $1..N, $#, $@, $NAME ---
@method(dollar_var)
def to_py(self, prec=None):
    """dollar_var: DOLLAR DOLLAR_SUFFIX -> Python sys.argv / os.environ equivalent."""
    from hek_parsec import ParserState
    raw = self.nodes[0].node  # TokenInfo or string
    name = raw.string if hasattr(raw, 'string') else str(raw)
    if name == "0":
        ParserState.nim_imports.add("import sys")
        return "sys.argv[0]"
    if name == "#":
        ParserState.nim_imports.add("import sys")
        return "(len(sys.argv) - 1)"
    if name == "@":
        ParserState.nim_imports.add("import sys")
        return "sys.argv[1:]"
    if name.isdigit():
        n = int(name)
        ParserState.nim_imports.add("import sys")
        return f"sys.argv[{n}]"
    ParserState.nim_imports.add("import os")
    return f"os.environ.get('{name}', '')"


# --- range expression (.., ..<) ---
@method(range_incl_op)
def to_py(self, prec=None):
    """range_incl_op: '..' (inclusive range operator) -> Python: used in range(lo, hi + 1)"""
    return ".."

@method(range_excl_op)
def to_py(self, prec=None):
    """range_excl_op: '..<' (exclusive upper bound) -> Python: used in range(lo, hi)"""
    return "..<"

@method(range_expr)
def to_py(self, prec=None):
    """range_expr: bitor_expr (('..' | '..<') bitor_expr)? -> Python: 'lo .. hi' -> range(lo, hi+1); 'lo ..< hi' -> range(lo, hi)"""
    # lo .. hi  -> range(lo, hi + 1)  (inclusive)
    # lo ..< hi -> range(lo, hi)      (exclusive)
    lo = self.nodes[0].to_py(prec)
    # Check if there's a range operator (Several_Times node with content)
    if len(self.nodes) < 2:
        return lo
    st = self.nodes[1]
    if not hasattr(st, 'nodes') or not st.nodes:
        return lo
    # st.nodes[0] is a Sequence_Parser: [range_op, bitor_expr]
    seq = st.nodes[0]
    if not hasattr(seq, 'nodes') or len(seq.nodes) < 2:
        return lo
    range_op_node = seq.nodes[0]
    op_val = getattr(range_op_node, 'node', None)
    if op_val not in ("..", "..<"):
        # Not a range at all. Sequence flattening can leave an ordinary
        # binary operator on this node, and the old code asked only whether
        # the operator was "..<" -- so everything that was not, `/`
        # included, fell into the inclusive branch below. `a == b / c` came
        # out as `a == range(b, c + 1)`: it parsed, it ran, and it answered
        # a different question. Hand those back to the generic binary
        # emitter, which is what builds them everywhere else.
        return binop_to_py(self, prec, None)
    hi = seq.nodes[1].to_py(prec)
    return range_bounds_to_py(lo, hi, op_val)


# --- power ---
@method(power_rhs)
def to_py(self, prec=None):
    """power_rhs: '**' factor"""
    return f"** {self.nodes[1].to_py(prec)}"


@method(power)
def to_py(self, prec=None):
    """power: await_primary power_rhs*  (right-associative)"""
    has_power = False
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        first = node.nodes[0]
        if type(first).__name__ == "power_rhs":
            has_power = True
            break

    if not has_power:
        # No ** operator, just delegate
        result = self.nodes[0].to_py(prec)
        for node in self.nodes[1:]:
            if not hasattr(node, "nodes") or not node.nodes:
                continue
            for tr in node.nodes:
                result += tr.to_py()
        return result

    # Right-associative: pass PREC_POWER+1 to left, PREC_POWER to right
    result = self.nodes[0].to_py(PREC_POWER + 1)
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        first = node.nodes[0]
        fname = type(first).__name__
        if fname == "power_rhs":
            exponents = [seq.nodes[1].to_py(PREC_POWER) for seq in node.nodes]
            for exp in reversed(exponents):
                result = f"{result} ** {exp}"
        elif fname in (
            "call_trailer",
            "index_trailer",
            "slice_trailer",
            "attr_trailer",
            "trailer",
        ):
            for tr in node.nodes:
                result += tr.to_py()
    if prec is not None and PREC_POWER < prec:
        return f"({result})"
    return result


# --- factor (unary) ---
@method(unary_plus)
def to_py(self, prec=None):
    """unary_plus: '+' factor"""
    result = f"+{self.nodes[0].to_py(PREC_UNARY)}"
    if prec is not None and PREC_UNARY < prec:
        return f"({result})"
    return result


@method(unary_minus)
def to_py(self, prec=None):
    """unary_minus: '-' factor"""
    result = f"-{self.nodes[0].to_py(PREC_UNARY)}"
    if prec is not None and PREC_UNARY < prec:
        return f"({result})"
    return result


@method(unary_tilde)
def to_py(self, prec=None):
    """unary_tilde: '~' factor"""
    result = f"~{self.nodes[0].to_py(PREC_UNARY)}"
    if prec is not None and PREC_UNARY < prec:
        return f"({result})"
    return result


@method(factor)
def to_py(self, prec=None):
    """factor: unary_plus | unary_minus | unary_tilde | power"""
    return self.nodes[0].to_py(prec)


# --- left-associative binary ops ---
@method(term)
def to_py(self, prec=None):
    """term: factor (('*' | '/' | '//' | '%' | '@') factor)*"""
    return binop_to_py(self, prec, PREC_TERM)


@method(sum_expr)
def to_py(self, prec=None):
    """sum_expr: term (('+' | '-') term)*"""
    return binop_to_py(self, prec, PREC_ARITH)


@method(shift_expr)
def to_py(self, prec=None):
    """shift_expr: sum_expr (('<<' | '>>') sum_expr)*"""
    return binop_to_py(self, prec, PREC_SHIFT)


@method(bitand_expr)
def to_py(self, prec=None):
    """bitand_expr: shift_expr ('&' shift_expr)*"""
    return binop_to_py(self, prec, PREC_BAND)


@method(bitxor_expr)
def to_py(self, prec=None):
    """bitxor_expr: bitand_expr ('^' bitand_expr)*"""
    return binop_to_py(self, prec, PREC_BXOR)


@method(bitor_expr)
def to_py(self, prec=None):
    """bitor_expr: bitxor_expr ('|' bitxor_expr)*"""
    return binop_to_py(self, prec, PREC_BOR)


# --- comparison ---
@method(not_in_op)
def to_py(self, prec=None):
    """not_in_op: 'not' 'in'"""
    return "not in"


@method(is_not_op)
def to_py(self, prec=None):
    """is_not_op: 'is' 'not'"""
    return "is not"


@method(comp_op)
def to_py(self, prec=None):
    """comp_op: '==' | '!=' | '<=' | '<' | '>=' | '>'
    | not_in_op | is_not_op | 'in' | 'is'"""
    return self.nodes[0].to_py()


_COMP_OPS = {"==", "!=", "<", ">", "<=", ">=", "in", "is", "not in", "is not",
             "-nt", "-ot"}


@method(comparison)
def to_py(self, prec=None):
    """comparison: bitor_expr (comp_op bitor_expr)*  (chained, not nested)"""
    # Find the LAST Several_Times whose first pair's operator is a comp_op
    last_comp_idx = None
    for i in range(len(self.nodes) - 1, -1, -1):
        node = self.nodes[i]
        if (
            type(node).__name__ == "Several_Times"
            and hasattr(node, "nodes")
            and node.nodes
        ):
            first_seq = node.nodes[0]
            if (
                hasattr(first_seq, "nodes")
                and len(first_seq.nodes) >= 2
                and hasattr(first_seq.nodes[0], "to_py")
                and first_seq.nodes[0].to_py() in _COMP_OPS
            ):
                last_comp_idx = i
                break

    if last_comp_idx is None:
        # Check if this is a range expression (2 .. n or 2 ..< n)
        # that was flattened into comparison from range_expr
        for _idx, node in enumerate(self.nodes):
            if (type(node).__name__ == "Several_Times"
                    and hasattr(node, "nodes") and node.nodes):
                seq = node.nodes[0]
                if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                    op_node = seq.nodes[0]
                    op_val = getattr(op_node, 'node', None)
                    if op_val in ("..", "..<"):
                        # The lower bound is everything *before* the range
                        # operator, not just the first node. Arithmetic
                        # arrives here flattened across self.nodes, so
                        # `n-k+1 .. n` used to take `n` and silently drop
                        # `- k + 1`, emitting range(n, n + 1) -- a loop of
                        # one where Nim ran k of them. Rebuilt the same way
                        # the comparison branch below rebuilds its base.
                        if _idx <= 1:
                            lo = self.nodes[0].to_py(prec)
                        else:
                            class _MockLo:
                                pass

                            _m = _MockLo()
                            _m.nodes = self.nodes[:_idx]
                            lo = binop_to_py(_m, None, None)
                        hi = seq.nodes[1].to_py(prec)
                        return range_bounds_to_py(lo, hi, op_val)
        # No comparison ops — delegate to binop_to_py for inner reconstruction
        return binop_to_py(self, prec, PREC_CMP)

    # Reconstruct base from nodes before the comparison Several_Times
    operand_prec = PREC_CMP + 1
    if last_comp_idx == 1:
        base = self.nodes[0].to_py(operand_prec)
    else:
        # Reconstruct the base expression. Pass None as my_prec to avoid
        # incorrect wrapping - the inner binop_to_py will handle precedence.
        class _Mock:
            pass

        mock = _Mock()
        mock.nodes = self.nodes[:last_comp_idx]
        base = binop_to_py(mock, None, None)

    # Chain comparison operators (no nesting): a < b < c -> a < b < c
    chain = base
    st = self.nodes[last_comp_idx]
    for seq in st.nodes:
        if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
            op = seq.nodes[0].to_py()
            # Handle 'in lo .. hi' / 'in lo ..< hi' -> 'lo <= x <= hi' / 'lo <= x < hi'
            if op == "in" and len(seq.nodes) >= 4:
                lo = seq.nodes[1].to_py(operand_prec)
                range_op_node = seq.nodes[2]
                hi = seq.nodes[3].to_py(operand_prec)
                # `in_range_excl` puts the whole `..<` token here, so the
                # operator is this node's own value. Looking for a child
                # spelled '<' never matched, and every `x in lo ..< hi`
                # came out as `lo <= x <= hi` -- inclusive at the top,
                # where Nim excludes it. `100 in 1 ..< 100` was True here
                # and false there.
                _rop = str(getattr(range_op_node, 'node', '') or '')
                is_exclusive = _rop == "..<" or (
                    hasattr(range_op_node, 'nodes')
                    and any(str(getattr(n, 'node', '')) in ('<', '..<')
                            for n in range_op_node.nodes))
                # Enum bounds have no ordering to chain: a plain Enum
                # rejects `<=` outright. Ask the members instead, which is
                # what the loop form over the same range walks.
                _owner = _enum_member_owner(lo)
                if _owner is not None and _enum_member_owner(hi) == _owner:
                    _rng = range_bounds_to_py(lo, hi, "..<" if is_exclusive else "..")
                    chain = f"{chain} in {_rng}"
                    continue
                hi_op = "<" if is_exclusive else "<="
                chain = f"{lo} <= {chain} {hi_op} {hi}"
                continue
            # Bash file-comparison: f1 -nt f2 / f1 -ot f2
            if op in ("-nt", "-ot"):
                right = seq.nodes[1].to_py(operand_prec)
                from hek_parsec import ParserState
                ParserState.nim_imports.add("import os")
                cmp_op = ">" if op == "-nt" else "<"
                chain = f"(os.path.getmtime({chain}) {cmp_op} os.path.getmtime({right}))"
                continue
            # == / != with regex RHS: dispatch to _pymatch / findall
            if op in ("==", "!="):
                rhs_node = seq.nodes[1]
                _rinfo = _get_regex_info_py(rhs_node)
                if _rinfo is not None:
                    _ensure_pymatch_helper()
                    _pat, _flags = _rinfo
                    _has_g = 'g' in _flags
                    _flags_val = _py_re_flags(_flags)
                    _safe_pat = _pat.replace("'", "\\'")
                    if _has_g:
                        _call = (f"_pyfindall({chain}, r'{_safe_pat}')" if _flags_val == "0"
                                 else f"_pyfindall({chain}, r'{_safe_pat}', {_flags_val})")
                        # `!=` asks whether the pattern matched at all, which
                        # is the length of that list -- the Nim side spells it
                        # `.len == 0`. It used to count empty strings, so a
                        # subject that *did* match still came back True.
                        chain = (f"len({_call}) == 0" if op == "!=" else _call)
                    else:
                        _call = f"_pymatch({chain}, r'{_safe_pat}')" if _flags_val == "0" else f"_pymatch({chain}, r'{_safe_pat}', {_flags_val})"
                        chain = f"not {_call}" if op == "!=" else _call
                    continue
            right = seq.nodes[1].to_py(operand_prec)
            chain += f" {op} {right}"
    if prec is not None and PREC_CMP < prec:
        return f"({chain})"
    return chain


# --- inversion ---
@method(not_prefix)
def to_py(self, prec=None):
    """not_prefix: 'not' inversion"""
    result = f"not {self.nodes[0].to_py(PREC_NOT)}"
    if prec is not None and PREC_NOT < prec:
        return f"({result})"
    return result


@method(inversion)
def to_py(self, prec=None):
    """inversion: not_prefix | comparison"""
    return self.nodes[0].to_py(prec)


# --- conjunction / disjunction ---
@method(conjunction)
def to_py(self, prec=None):
    """conjunction: inversion ('and' inversion)*"""
    return binop_to_py(self, prec, PREC_AND)


@method(disjunction)
def to_py(self, prec=None):
    """disjunction: conjunction ('or' conjunction)*"""
    return binop_to_py(self, prec, PREC_OR)


# --- walrus / named_expression ---
@method(walrus)
def to_py(self, prec=None):
    """walrus: IDENTIFIER ':=' expression — nodes: [IDENTIFIER, V_COLONEQUAL, expression]"""
    result = f"{self.nodes[0].to_py()} := {self.nodes[2].to_py()}"
    if prec is not None and PREC_WALRUS < prec:
        return f"({result})"
    return result


@method(named_expression)
def to_py(self, prec=None):
    """named_expression: walrus | expression"""
    return self.nodes[0].to_py(prec)


# --- conditional ---
@method(conditional)
def to_py(self, prec=None):
    """conditional: disjunction 'if' disjunction 'else' expression"""
    result = f"{self.nodes[0].to_py()} if {self.nodes[1].to_py()} else {self.nodes[2].to_py()}"
    if prec is not None and PREC_CONDITIONAL < prec:
        return f"({result})"
    return result


# --- lambda ---
@method(lambda_param)
def to_py(self, prec=None):
    """lambda_param: IDENTIFIER ['=' expression]"""
    name = self.nodes[0].to_py()
    if len(self.nodes) > 1 and hasattr(self.nodes[1], "nodes") and self.nodes[1].nodes:
        # Optional part matched: Several_Times containing one Sequence_Parser (iop("=") + expression)
        seq = self.nodes[1].nodes[0]
        # iop("=") is ignored, so seq.nodes[0] is the expression
        default = seq.nodes[0].to_py()
        return f"{name}={default}"
    return name


@method(lambda_star)
def to_py(self, prec=None):
    """lambda_star: '*' IDENTIFIER — nodes: [SSTAR('*'), IDENTIFIER]"""
    return f"*{self.nodes[1].to_py()}"


@method(lambda_dstar)
def to_py(self, prec=None):
    """lambda_dstar: '**' IDENTIFIER"""
    return f"**{self.nodes[0].to_py()}"


@method(lambda_params_entry)
def to_py(self, prec=None):
    """lambda_params_entry: lambda_dstar | lambda_star | lambda_param"""
    return self.nodes[0].to_py()


@method(lambda_params)
def to_py(self, prec=None):
    """lambda_params: lambda_params_entry (',' lambda_params_entry)*"""
    parts = [self.nodes[0].to_py()]
    if len(self.nodes) > 1 and hasattr(self.nodes[1], "nodes"):
        for seq in self.nodes[1].nodes:
            if hasattr(seq, "nodes") and seq.nodes:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


@method(lambda_expr)
def to_py(self, prec=None):
    """lambda_expr: 'lambda' lambda_params? ':' expression"""
    if len(self.nodes) >= 2:
        params_st = self.nodes[0]
        if hasattr(params_st, "nodes") and params_st.nodes:
            params = params_st.nodes[0].to_py()
        else:
            params = ""
        body = self.nodes[1].to_py()
        result = f"lambda {params}: {body}"
    else:
        body = self.nodes[0].to_py()
        result = f"lambda: {body}"
    if prec is not None and PREC_CONDITIONAL < prec:
        return f"({result})"
    return result


# --- expression ---
@method(expression)
def to_py(self, prec=None):
    """expression: conditional | lambda_expr | disjunction"""
    return self.nodes[0].to_py(prec)


# --- expressions ---
@method(expressions)
def to_py(self, prec=None):
    """expressions: expression (',' expression)* ','?"""
    parts = [self.nodes[0].to_py()]
    trailing_comma = False
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        found_pair = False
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
                found_pair = True
        if not found_pair:
            # Several_Times from COMMA[:] — trailing comma
            trailing_comma = True
    result = ", ".join(parts)
    if len(parts) == 1 and trailing_comma:
        result += ","
    return result


# --- yield ---
@method(yield_from)
def to_py(self, prec=None):
    """yield_from: 'yield' 'from' expression"""
    return f"yield from {self.nodes[0].to_py()}"


@method(yield_val)
def to_py(self, prec=None):
    """yield_val: 'yield' star_expressions?"""
    if self.nodes and hasattr(self.nodes[0], "nodes") and self.nodes[0].nodes:
        return f"yield {self.nodes[0].nodes[0].to_py()}"
    elif self.nodes:
        return f"yield {self.nodes[0].to_py()}"
    return "yield"


@method(yield_expr)
def to_py(self, prec=None):
    """yield_expr: yield_from | yield_val"""
    return self.nodes[0].to_py()


# --- star expressions ---
@method(star_single)
def to_py(self, prec=None):
    """star_single: '*' bitor_expr"""
    return f"*{self.nodes[1].to_py()}"


@method(star_expression)
def to_py(self, prec=None):
    """star_expression: star_single | expression"""
    return self.nodes[0].to_py(prec)


@method(star_expressions)
def to_py(self, prec=None):
    """star_expressions: star_expression (',' star_expression)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


# --- slices ---
@method(slice_3)
def to_py(self, prec=None):
    """slice_3: expression ':' expression ':' expression"""
    return f"{self.nodes[0].to_py()}:{self.nodes[2].to_py()}:{self.nodes[4].to_py()}"


@method(slice_3ns)
def to_py(self, prec=None):
    """slice_3ns: expression ':' ':' expression  (no stop)"""
    return f"{self.nodes[0].to_py()}::{self.nodes[3].to_py()}"


@method(slice_3nn)
def to_py(self, prec=None):
    """slice_3nn: ':' expression ':' expression  (no start)"""
    return f":{self.nodes[1].to_py()}:{self.nodes[3].to_py()}"


@method(slice_3bare)
def to_py(self, prec=None):
    """slice_3bare: ':' ':' expression  (no start, no stop)"""
    return f"::{self.nodes[2].to_py()}"


@method(slice_2)
def to_py(self, prec=None):
    """slice_2: expression ':' expression"""
    return f"{self.nodes[0].to_py()}:{self.nodes[2].to_py()}"


@method(slice_1_start)
def to_py(self, prec=None):
    """slice_1_start: expression ':'"""
    return f"{self.nodes[0].to_py()}:"


@method(slice_1_stop)
def to_py(self, prec=None):
    """slice_1_stop: ':' expression"""
    return f":{self.nodes[1].to_py()}"


@method(slice_bare)
def to_py(self, prec=None):
    """slice_bare: ':'"""
    return ":"


@method(slice_full)
def to_py(self, prec=None):
    """slice_full: slice_3 | slice_3ns | slice_3nn | slice_3bare
    | slice_2 | slice_1_start | slice_1_stop | slice_bare"""
    return self.nodes[0].to_py()


@method(slice_expr)
def to_py(self, prec=None):
    """slice_expr: slice_full | named_expression"""
    return self.nodes[0].to_py()


@method(slices)
def to_py(self, prec=None):
    """slices: slice_expr (',' slice_expr)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


# --- arguments ---
@method(kwarg)
def to_py(self, prec=None):
    """kwarg: IDENTIFIER '=' expression"""
    return f"{self.nodes[0].to_py()}={self.nodes[1].to_py()}"


@method(star_arg)
def to_py(self, prec=None):
    """star_arg: '*' expression"""
    return f"*{self.nodes[1].to_py()}"


@method(dstar_arg)
def to_py(self, prec=None):
    """dstar_arg: '**' expression"""
    return f"**{self.nodes[0].to_py()}"


@method(arg)
def to_py(self, prec=None):
    """arg: kwarg | dstar_arg | star_arg | expression"""
    return self.nodes[0].to_py()


@method(arguments)
def to_py(self, prec=None):
    """arguments: arg (',' arg)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


# --- comprehensions ---
@method(target)
def to_py(self, prec=None):
    """target: IDENTIFIER (',' IDENTIFIER)*"""
    parts = [self.nodes[0].to_py()]
    if len(self.nodes) > 1 and hasattr(self.nodes[1], "nodes"):
        for seq in self.nodes[1].nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


@method(for_if_clause)
def to_py(self, prec=None):
    """for_if_clause: 'for' target 'in' disjunction ('if' disjunction)*"""
    tgt = self.nodes[0].to_py()
    iterable = self.nodes[1].to_py()
    iterable = _builtin_ordinal_domain(iterable) or iterable
    result = f"for {tgt} in {iterable}"
    # nodes[2] is Several_Times of Sequence_Parser(I_IF + disjunction).
    # I_IF is ignored so each Sequence_Parser has exactly one node: the disjunction.
    if len(self.nodes) > 2:
        st = self.nodes[2]
        if hasattr(st, "nodes"):
            for seq in st.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    result += f" if {seq.nodes[0].to_py()}"
                elif hasattr(seq, "to_py"):
                    result += f" if {seq.to_py()}"
    return result


@method(for_if_clauses)
def to_py(self, prec=None):
    """for_if_clauses: for_if_clause+"""
    parts = []
    for n in self.nodes:
        if hasattr(n, "to_py"):
            parts.append(n.to_py())
        elif hasattr(n, "nodes"):
            for nn in n.nodes:
                if hasattr(nn, "to_py"):
                    parts.append(nn.to_py())
    return " ".join(parts)


@method(listcomp)
def to_py(self, prec=None):
    """listcomp: named_expression for_if_clauses"""
    return f"{self.nodes[0].to_py()} {self.nodes[1].to_py()}"


@method(genexpr)
def to_py(self, prec=None):
    """genexpr: named_expression for_if_clauses"""
    return f"{self.nodes[0].to_py()} {self.nodes[1].to_py()}"


@method(dictcomp)
def to_py(self, prec=None):
    """dictcomp: expression ':' expression for_if_clauses"""
    return f"{self.nodes[0].to_py()}: {self.nodes[1].to_py()} {self.nodes[2].to_py()}"


@method(setcomp)
def to_py(self, prec=None):
    """setcomp: expression for_if_clauses"""
    return f"{self.nodes[0].to_py()} {self.nodes[1].to_py()}"


# --- dict/set makers ---
@method(V_COLON)
def to_py(self, prec=None):
    """V_COLON: ':'  (visible colon token)"""
    return ":"


@method(kvpair)
def to_py(self, prec=None):
    """kvpair: expression ':' expression"""
    return f"{self.nodes[0].to_py()}: {self.nodes[2].to_py()}"


@method(dictmaker)
def to_py(self, prec=None):
    """dictmaker: kvpair (',' kvpair)* ','?"""
    first_pair = f"{self.nodes[0].to_py()}: {self.nodes[2].to_py()}"
    parts = [first_pair]
    for node in self.nodes[3:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                # Each seq inside Several_Times is a kvpair
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


@method(setmaker)
def to_py(self, prec=None):
    """setmaker: star_expression (',' star_expression)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)



###############################################################################
# Public API
###############################################################################


def parse_expr(code):
    """Parse a Python 3.14 expression and return the AST node."""
    ParserState.reset()
    stream = Input(code)
    result = expression.parse(stream)
    if not result:
        return None
    return result[0]


###############################################################################
# Tests
###############################################################################

if __name__ == "__main__":
    print("=" * 60)
    print("Python 3.14 Expression Parser Tests")
    print("=" * 60)

    tests = [
        # --- Literals ---
        ("42", "42"),
        ("3.14", "3.14"),
        ('"hello"', '"hello"'),
        ("'world'", "'world'"),
        ("None", "None"),
        ("True", "True"),
        ("False", "False"),
        ("...", "..."),
        # --- Arithmetic ---
        ("1 + 2", "1 + 2"),
        ("1 + 2 * 3", "1 + 2 * 3"),
        ("(1 + 2) * 3", "(1 + 2) * 3"),
        ("10 / 3", "10 / 3"),
        ("10 // 3", "10 // 3"),
        ("10 % 3", "10 % 3"),
        ("a @ b", "a @ b"),
        # --- Unary ---
        ("-x", "-x"),
        ("+x", "+x"),
        ("~x", "~x"),
        ("not x", "not x"),
        # --- Power (right-associative) ---
        ("x ** 2", "x ** 2"),
        # --- Comparison ---
        ("x < y", "x < y"),
        ("x == y", "x == y"),
        ("x != y", "x != y"),
        ("x <= y", "x <= y"),
        ("x >= y", "x >= y"),
        # --- Bitwise ---
        ("x | y", "x | y"),
        ("x ^ y", "x ^ y"),
        ("x & y", "x & y"),
        ("x << 2", "x << 2"),
        ("x >> 1", "x >> 1"),
        # --- Boolean ---
        ("x and y", "x and y"),
        ("x or y", "x or y"),
        ("x and y or z", "x and y or z"),
        ("not x and y", "not x and y"),
        # --- Conditional ---
        ("a if b else c", "a if b else c"),
        # --- Lambda ---
        ("lambda x: x + 1", "lambda x: x + 1"),
        ("lambda x, y: x + y", "lambda x, y: x + y"),
        # --- Calls, subscripts, attributes ---
        ("f(x)", "f(x)"),
        ("f(x, y)", "f(x, y)"),
        ("a[i]", "a[i]"),
        ("obj.attr", "obj.attr"),
        ("f(x).y", "f(x).y"),
        # --- Containers ---
        ("[1, 2, 3]", "[1, 2, 3]"),
        ("[]", "[]"),
        ("()", "()"),
        # --- String concat ---
        ('"a" "b"', '"a" "b"'),
        # --- Python 3 specifics ---
        ("{1, 2, 3}", "{1, 2, 3}"),
        ("{1: 2, 3: 4}", "{1: 2, 3: 4}"),
        ("f(x=1)", "f(x=1)"),
        ("f(*args)", "f(*args)"),
        ("f(**kwargs)", "f(**kwargs)"),
        ("f(a, *b, **c)", "f(a, *b, **c)"),
        # --- Comprehensions ---
        ("[x for x in xs]", "[x for x in xs]"),
        ("{x for x in xs}", "{x for x in xs}"),
        # --- Slicing ---
        ("a[1:2]", "a[1:2]"),
        # --- Await ---
        ("await f()", "await f()"),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            result = parse_expr(code)
            if result:
                output = result.to_py()
                if output == expected:
                    print(f"  PASS: {code!r} -> {output!r}")
                    passed += 1
                else:
                    print(f"  MISMATCH: {code!r}")
                    print(f"    expected: {expected!r}")
                    print(f"    got:      {output!r}")
                    failed += 1
            else:
                print(f"  FAIL: {code!r} -> parse returned None")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {code!r} -> {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    # ==================================================================


@method(named_tuple_field)
def to_py(self, prec=None):
    """named_tuple_field: IDENTIFIER ':' expression (Adascript named-tuple field literal) -> Python: just the value (positional)"""
    # In Python, named tuple fields become positional: just emit the value
    val = self.nodes[2].to_py()
    return val

@method(named_tuple_lit)
def to_py(self, prec=None):
    """named_tuple_lit: '(' named_tuple_field (',' named_tuple_field)* ')' -> Python: TypeName(field=val, ...) if type known, else (val, ...)"""
    # Collect field names and values
    def _extract_field(node):
        """Extract (name, value) from a named_tuple_field node."""
        name = str(node.nodes[0].nodes[0]) if hasattr(node.nodes[0], 'nodes') else str(node.nodes[0])
        val = node.nodes[2].to_py()
        return name, val
    first_name, first_val = _extract_field(self.nodes[1])
    field_names = [first_name]
    field_vals = [first_val]
    rest = self.nodes[2]  # Several_Times
    if hasattr(rest, 'nodes'):
        for seq in rest.nodes:
            if hasattr(seq, 'nodes'):
                for child in seq.nodes:
                    if type(child).__name__ == "named_tuple_field":
                        n, v = _extract_field(child)
                        field_names.append(n)
                        field_vals.append(v)
            elif type(seq).__name__ == "named_tuple_field":
                n, v = _extract_field(seq)
                field_names.append(n)
                field_vals.append(v)
    # Look up if these fields match a known NamedTuple type
    type_name = _lookup_named_tuple(field_names)
    if type_name:
        # Emit as NamedTuple constructor: TypeName(field=val, ...)
        args = ", ".join(f"{n}={v}" for n, v in zip(field_names, field_vals))
        return f"{type_name}({args})"
    # Fallback: plain tuple with just the values
    return "(" + ", ".join(field_vals) + ")"


# ---------------------------------------------------------------------------
# Regex literals and capture variables
# ---------------------------------------------------------------------------

_PYMATCH_HELPER = """\
import re as _re_mod
matches = []
namedCaptures = {}

def _pymatch(s, pat, flags=0):
    global matches, namedCaptures
    m = _re_mod.search(pat, s, flags)
    if m is None:
        matches = []
        namedCaptures = {}
        return False
    matches = [m.group(0)] + [g if g is not None else "" for g in m.groups()]
    namedCaptures = {k: (v if v is not None else "") for k, v in m.groupdict().items()}
    return True

def _pyfindall(s, pat, flags=0):
    '''`x == /pat/g`: every match, whole, as a list of str.

    Deliberately not re.findall, which returns the capture groups whenever
    the pattern has any -- a list of tuples for two groups. Nim emits
    std/re.findAll, which returns the whole match either way, so a grouped
    pattern used to mean different things on the two backends. finditer
    keeps group(0) whatever the pattern contains.
    '''
    return [m.group(0) for m in _re_mod.finditer(pat, s, flags)]
"""

def _ensure_pymatch_helper():
    """Inject the _pymatch helper into py_top_decls the first time regex is used."""
    decls = getattr(ParserState, 'py_top_decls', [])
    if not any("_pymatch" in d for d in decls):
        decls.append(_PYMATCH_HELPER)
        ParserState.py_top_decls = decls

def _get_regex_info_py(node):
    """Walk single-child wrapper nodes to find a regex_lit leaf.
    Returns (pattern, flags) or None."""
    while node is not None:
        val = getattr(node, 'node', None)
        if isinstance(val, str) and val.startswith('/'):
            last_slash = val.rfind('/')
            if last_slash > 0:
                return val[1:last_slash], val[last_slash + 1:]
        if hasattr(node, 'nodes') and len(node.nodes) == 1:
            node = node.nodes[0]
        else:
            return None
    return None

def _py_re_flags(flags_str):
    """Convert regex flag chars to a Python re.FLAGS expression, or '0'."""
    # The generated file imports the module as `_re_mod` (see _PYMATCH_HELPER),
    # so the flag constants must be spelled with that alias too.
    mapping = {'i': '_re_mod.IGNORECASE', 'm': '_re_mod.MULTILINE', 's': '_re_mod.DOTALL'}
    parts = [mapping[f] for f in flags_str.replace('g', '') if f in mapping]
    return " | ".join(parts) if parts else "0"


@method(regex_lit)
def to_py(self, prec=None):
    """regex_lit: /pattern/flags — standalone (rare); emit as re.compile(r"pat", flags)."""
    _ensure_pymatch_helper()
    s = self.node
    last_slash = s.rfind('/')
    pat = s[1:last_slash].replace("'", "\\'")
    flags_str = s[last_slash + 1:]
    flags_val = _py_re_flags(flags_str)
    if flags_val != "0":
        return f"_re_mod.compile(r'{pat}', {flags_val})"
    return f"_re_mod.compile(r'{pat}')"


@method(capture_var)
def to_py(self, prec=None):
    """capture_var: $+N -> matches[N]"""
    num = int(self.node[2:])
    return f"matches[{num}]"


@method(named_capture_var)
def to_py(self, prec=None):
    """named_capture_var: $+{name} -> namedCaptures["name"]"""
    name = self.node[3:-1]   # strip "$+{" and "}"
    return f'namedCaptures["{name}"]'

