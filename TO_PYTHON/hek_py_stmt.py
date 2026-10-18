#!/usr/bin/env python3
"""Python 3.14 Simple Statement Parser using hek_parsec combinator framework.

Builds on hek_py_expr.py (expression grammar) to parse simple (non-compound)
Python 3.14 statements. Simple statements fit on one line, can be separated
by ';', and are terminated by NEWLINE.

Statements implemented:
    - Assignment:          x = 1, a = b = 1
    - Augmented assignment: x += 1, x @= m
    - Annotated assignment: x: int = 1
    - return, pass, break, continue
    - del, assert, raise
    - global, nonlocal
    - import, from ... import
    - type alias:          type X = int | str  (3.12+)
    - Expression statement: f(x), x
    - Statement modifier: return False if x == ""  (return/break/continue)

Usage:
    ast = parse_stmt("x = 1")
    print(ast.to_py())  # x = 1
"""

from ady_words import a_
import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "GRAMMAR"))

from ady_stmt import *
from hek_py_expr import _get_bracket_start
import hek_py_declarations  # noqa: F401 — registers decl to_py() methods
from hek_parsec import method, ParserState
import re as _re_mod_p2s
from hek_helpers import _ind, reject_dollar_assignment

# to_py() methods
###############################################################################


# --- augop ---
@method(augop)
def to_py(self):
    """augop: '+=' | '-=' | '*=' | '/=' | '//=' | '%=' | '**='
    | '@=' | '<<=' | '>>=' | '&=' | '|=' | '^='"""
    return self.nodes[0].to_py()


# --- visible tokens ---
@method(V_EQUAL)
def to_py(self):
    """V_EQUAL: '='"""
    return "="




@method(V_DOT)
def to_py(self):
    """V_DOT: '.'"""
    return "."


# --- assignment ---
def _unlines_target(target):
    """`r.lines = ...`: the `.lines` the expression emitter left to be asked
    at run time is, as a target, the field itself."""
    if target.startswith("_lines_of(") and target.endswith(")"):
        depth = 0
        for k, ch in enumerate(target):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0 and k > 8:
                if k == len(target) - 1:
                    return target[len("_lines_of("):-1] + ".lines"
                break
    return target


@method(assign_stmt)
def to_py(self):
    """assign_stmt: star_expressions ('=' star_expressions)+"""
    reject_dollar_assignment(self.nodes[0])
    # nodes: [target1, Several_Times[(=, target2), (=, target3), ...]]
    # The last (=, expr) pair is the value; everything before is a target.
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                parts.append(seq.nodes[1].to_py())
    parts[:-1] = [_unlines_target(x) for x in parts[:-1]]
    # `p = s` where p was declared a Path: the same refusal as at declaration.
    if len(parts) > 1:
        _t = ParserState.symbol_table.lookup(parts[0])
        if isinstance(_t, dict) and (_t.get("type") or "") == "Path":
            _reject_str_to_path(parts[0], "Path", parts[-1])
        if isinstance(_t, dict) and _t.get("type"):
            _reject_distinct_mix(parts[0], _t["type"], parts[-1])
            parts[-1] = _wrap_narrowed_literal(parts[-1], _t["type"])
        # `m = {...}` on a [K]V map keeps it one
        if isinstance(_t, dict) and _t.get("type"):
            parts[-1] = _wrap_for_ordered_array(parts[-1], _t["type"])
        if len(parts) == 2:
            parts[-1] = _range_checked(parts[-1], _target_range_type(parts[0]))
    return " = ".join(parts)


# --- augmented assignment ---
@method(aug_assign_stmt)
def to_py(self):
    """aug_assign_stmt: star_expressions augop expressions"""
    reject_dollar_assignment(self.nodes[0], "+=")
    target = _unlines_target(self.nodes[0].to_py())
    # augop is an Fmap whose nodes[0] is a plain string like '+='
    op_node = self.nodes[1]
    op = (
        op_node.nodes[0]
        if isinstance(op_node.nodes[0], str)
        else op_node.nodes[0].to_py()
    )
    value = self.nodes[2].to_py()
    _rt = _target_range_type(target)
    if _rt and op[:-1] in ("+", "-", "*", "//", "%", "**", "<<", ">>", "&", "|", "^"):
        return f"{target} = {_range_checked(f'{target} {op[:-1]} {value}', _rt)}"
    return f"{target} {op} {value}"


# --- annotated assignment ---
@method(ann_assign_stmt)
def to_py(self):
    """ann_assign_stmt: IDENTIFIER ':' expression ('=' expression)?"""
    name = self.nodes[0].to_py()
    # nodes[1] is V_COLON, nodes[2] is the type annotation
    from hek_py_expr import py_self_ref_annotation
    annotation = py_self_ref_annotation(self.nodes[2].to_py())
    result = f"{name}: {annotation}"
    # Check for optional '= value' part
    has_value = False
    for node in self.nodes[3:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_py()
                _reject_str_to_path(name, annotation, value)
                _reject_distinct_mix(name, annotation, value)
                value = _wrap_narrowed_literal(value, annotation)
                value = _wrap_seq_for_enum_array(value, annotation)
                value = _wrap_for_ordered_array(value, annotation)
                value = _wrap_list_for_queue(value, annotation)
                value = _range_checked(value, annotation)
                result += f" = {value}"
                has_value = True
    # Deliberately not zero-initialised here, unlike the `var x: T` form:
    # `x: int` with no value is also ordinary Python, which ady2py round-trips
    # unchanged.  Write `var x: T` to mean an Adascript declaration.
    return result





# Non-zero while a class body is being rendered.  A class-level field must not
# be given a mutable default: that object would be shared by every instance,
# which is worse than the AttributeError it replaces.  Set by the `class_def`
# emitter and cleared by `func_def`, since a method body is an ordinary scope.
CLASS_BODY_DEPTH = 0

# Statement nodes to render with a leading `return`, held by id().  The
# implicit-return pass marks them before the body is rendered, so the keyword
# goes in front of the whole statement -- a multi-line string included --
# instead of being patched into the finished text afterwards.  Cleared per
# module by `_py_reset()`.
RETURN_NODES = set()

_MUTABLE_ZEROS = ("[]", "{}", "set()", "frozenset()", "Counter()")


def _wrap_list_for_queue(value, annotation):
    """`q: PriorityQueue[T] = [seed]` -> `q = PriorityQueue(seed)`.

    The mirror of _wrap_seq_for_queue on the Nim side, which turns the same
    declaration into `newPriorityQueueWith(seed)`.  Without it the annotation
    is decoration and the name is left bound to a plain list, so the first
    `q.push(...)` fails with "'list' object has no attribute 'push'".

    Only a single-element literal is rewritten, matching both the Nim
    constructors and this shim's `__init__(first=None)`.  An empty or
    multi-element seed is left alone, as on Nim, where the user writes the
    constructor and pushes the rest.

    Declaring the queue is also what pulls its class into the output, so the
    helper is ensured here rather than at the use site.
    """
    from hek_py_expr import ensure_queue_helper
    ann = (annotation or "").strip()
    # The annotation reaches us with its type arguments already dropped
    # (`PriorityQueue[(float, Node_T)]` renders as `PriorityQueue`), but
    # accept the subscripted spelling too rather than depend on that.
    base = ann.split("[", 1)[0].strip()
    if not ensure_queue_helper(base):
        return value
    v = (value or "").strip()
    if not (v.startswith("[") and v.endswith("]")):
        return value                     # already a constructor call, or empty
    item = v[1:-1].strip()
    if not item:
        return value
    # A comma at depth zero means several elements, which no constructor takes.
    depth = 0
    for ch in item:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            return value
    return f"{base}({item})"


def _enum_array_key(ann):
    """The key of an `_EnumArray[K, T]` annotation, K taken whole: an
    inline subrange's key is `range(2, 4 + 1)`, commas and all."""
    inner = ann[len("_EnumArray["):]
    depth = 0
    for i, ch in enumerate(inner):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "," and depth == 0:
            return inner[:i].strip()
    return inner.strip()


def _wrap_seq_for_enum_array(value, annotation):
    """`[O]T = [ ... ]` -> keyed by the domain rather than by position.

    A comprehension or list literal yields a plain list, and an
    ordinal-keyed array is a dict on this backend, so the two have to be
    zipped together. For a domain that does not start at zero -- `type Off
    is 2 .. 6` -- positional indexing is not merely untidy but wrong:
    `byOff[2]` would be the third element and `byOff[6]` an IndexError. The
    Nim backend indexes such an array by the ordinal itself, so this is what
    keeps the two agreeing.
    """
    from hek_parsec import ParserState
    ann = (annotation or "").strip()
    if not ann.startswith("_EnumArray["):
        return value
    v = (value or "").strip()
    # Already keyed (the `[KEY: v]` literal, or the zero value), or not a
    # sequence at all: leave it alone.
    if v.startswith("{") and " for " in v:   # `[k: v for k in E]`, keyed
        return f"_EnumArray({v})"
    if v.startswith("_EnumArray(") or not v.startswith("["):
        return value
    key = _enum_array_key(ann)
    info = getattr(ParserState, "tick_types", {}).get(key)
    if key.startswith("range("):         # [lo..hi]T, written inline
        domain = key
    elif info is not None and "members" in info:
        domain = key                     # an Enum class iterates its members
    elif info is not None:
        domain = f"range({info['First']}, {info['Last']} + 1)"
    elif key == "bool":
        domain = "(False, True)"
    elif key == "str":                   # [char]T
        domain = "(chr(_i) for _i in range(256))"
    else:
        return value
    return f"_EnumArray(zip({domain}, {v}))"


@method(derived_def)
def to_py(self, prec=None):
    """derived_def: IDENTIFIER ('*' | '/') IDENTIFIER -- a unit made from two
    others; type_stmt renders it, from the declaration scan."""
    return ""


@method(distinct_float_range_def)
def to_py(self, prec=None):
    return "float"


@method(narrowed_def)
def to_py(self, prec=None):
    """narrowed_def: IDENTIFIER 'range' BOUND '..' BOUND -> the parent; the
    class is built by type_stmt"""
    return self.nodes[0].to_py()


@method(mod_def)
def to_py(self, prec=None):
    """mod_def: 'mod' NUMBER; the class is built by type_stmt"""
    return "int"


@method(parent_mod_def)
def to_py(self, prec=None):
    """parent_mod_def: IDENTIFIER 'mod' NUMBER -> the parent; the class is
    built by type_stmt"""
    return self.nodes[0].to_py()


@method(distinct_def)
def to_py(self, prec=None):
    """distinct_def: 'distinct' type_annotation -> the base type; the class
    is built by type_stmt"""
    return self.nodes[0].to_py()


_DISTINCT_BASES = {"float": "float", "int": "int", "str": "str", "bool": "bool"}


def _py_type_of_name(value):
    """The annotation a bare name VALUE was declared with, or None."""
    v = (value or "").strip()
    if not _re_p2s.match(v):
        return None
    sym = ParserState.symbol_table.lookup(v)
    return (sym.get("type") or None) if isinstance(sym, dict) else None


def _py_value_side(t):
    """T without its failure side: `int | ParseFailure_T` is an int where the
    unit is asked, the failure having been ruled out or raised by then."""
    parts = [p.strip().lstrip("!").strip() for p in (t or "").split("|")]
    failures = getattr(ParserState, "failure_types", set())
    if len(parts) > 1 and all(p in failures for p in parts[1:]):
        return parts[0]
    return (t or "").strip()


def _py_overload_type(cls, method, args_text):
    """The return type of the overload of CLS.METHOD that the arguments
    ARGS_TEXT, emitted Python, pick by their types; None unless exactly one."""
    from ady_stmt import overload_return, _top_split
    overloads = (getattr(ParserState, "py_method_overloads", None) or {}).get(f"{cls}.{method}")
    if not overloads:
        return None
    types = []
    for a in (_top_split(args_text) if args_text.strip() else []):
        if _re_mod_p2s.match(r"^\w+\s*=[^=]", a):
            return None                 # by name: not taken in order
        if _re_mod_p2s.match(r"^-?\d[\d_]*$", a):
            types.append("int")
        elif _PY_NUMBER.match(a):
            types.append("float")
        elif a.startswith(('"', "'", 'f"', "f'")):
            types.append("str")
        else:
            types.append(_py_type_of_name(a))
    return overload_return(overloads, types)


_PY_NUMBER = _re_mod_p2s.compile(r"^-?\d[\d_]*(\.\d+)?([eE][-+]?\d+)?$")
_PY_PLAIN_TYPES = ("float", "int", "Natural", "Positive")


def _py_resolve_alias(t):
    """T through plain aliases -- `type Speed_T is Velocity_T` is the same
    type on Nim -- but not through a distinct one, which is its own."""
    from ady_declarations import is_distinct
    aliases = getattr(ParserState, "py_type_aliases", {})
    seen = set()
    while t in aliases and aliases[t] != t and t not in seen and not is_distinct(t):
        seen.add(t)
        t = aliases[t]
    return t


def _py_call_name(e):
    """The name F of `F(...)` when E is exactly one such call, else None."""
    m = _re_mod_p2s.match(r"^([A-Za-z_]\w*)\(", e)
    if not m or not e.endswith(")"):
        return None
    depth = 0
    for i, ch in enumerate(e[m.end() - 1:], m.end() - 1):
        depth += ch in "(["
        depth -= ch in ")]"
        if depth == 0 and i < len(e) - 1:
            return None
    return m.group(1)


def _py_field_type(e):
    """The declared type of `name.field`, when NAME is typed as a record that
    declares FIELD, else None."""
    m = _re_mod_p2s.match(r"^([A-Za-z_]\w*)\.([A-Za-z_]\w*)$", e)
    if not m:
        return None
    owner = _py_type_of_name(m.group(1))
    if not owner:
        return None
    owner = _py_resolve_alias(owner.strip())
    return getattr(ParserState, "record_fields", {}).get(owner, {}).get(m.group(2))


def _py_atom_unit(e):
    """The unit of E, emitted Python that is no arithmetic: a distinct
    type's name for a name of one, `Velocity_T(x)` or a call declared to
    return one; UNIT_LIT for a number; UNIT_PLAIN for a name or call of a
    plain number type, `float(v)` too; None where it cannot be told."""
    from ady_declarations import is_distinct, UNIT_LIT, UNIT_PLAIN
    e = (e or "").strip()
    if _PY_NUMBER.match(e):
        return UNIT_LIT
    t = None
    if e.startswith("math.") and _py_call_name(e[5:]):
        return UNIT_PLAIN               # `math.atan2(y, x)`: a plain number
    m = _re_mod_p2s.match(r"^([A-Za-z_][\w.]*)\.(\w+)\(", e)
    if m and _py_call_name(e[len(m.group(1)) + 1:]):
        # `self.length()`: the method's own return type, by the receiver's class
        from hek_py_expr import _py_receiver_type, _py_bare_type
        parts = m.group(1).split(".")
        cls = _py_bare_type(_py_receiver_type(parts[0], ["." + p for p in parts[1:]]))
        t = getattr(ParserState, "py_method_return_types", {}).get(f"{cls}.{m.group(2)}")
        if not t:
            t = _py_overload_type(cls, m.group(2), e[m.end():-1])
        if not t:
            return None
        t = _py_resolve_alias(_py_value_side(t))
        return t if is_distinct(t) else (UNIT_PLAIN if t in _PY_PLAIN_TYPES else None)
    called = _py_call_name(e)
    if called:
        if is_distinct(called):
            return called
        if called in ("float", "int", "_ada_ord", "len"):
            return UNIT_PLAIN
        if called == "abs":             # `abs(x)` is of x's unit
            from ady_declarations import expr_unit
            return expr_unit(e[4:-1], _py_atom_unit)
        t = getattr(ParserState, "ady_return_types", {}).get(called)
        if t is None and (called in _MATH_FOR_PYTHON or called in _MATH_NAMES):
            return UNIT_PLAIN           # `hypot(x, y)` from math: a plain number
    else:
        t = _py_type_of_name(e)
        if t is None:
            t = _py_field_type(e)
        if t is None and _re_mod_p2s.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", e):
            from hek_py_expr import _py_receiver_type   # `self.east`, `a.b.c`
            parts = e.split(".")
            t = _py_receiver_type(parts[0], ["." + p for p in parts[1:]]) or None
    if not t:
        return None
    t = _py_resolve_alias(_py_value_side(t))
    if is_distinct(t):
        return t
    from ady_declarations import narrow_root
    if t and narrow_root(t) != t and is_distinct(narrow_root(t)):
        return t                        # `Latitude_T`, narrowed from a Degree_T
    return UNIT_PLAIN if t in _PY_PLAIN_TYPES else None


_RANGE_CHECK_HELPER = """\
def _in_range(v, r):
    \"\"\"A value of an integer subrange stays in it, as on Nim.\"\"\"
    if v not in r:
        raise ValueError(f"value out of range: {v} notin {r.start} .. {r.stop - 1}")
    return v\
"""


_UNIT_OPS_HELPER = """\
def _unit_ops(cls, base):
    \"\"\"A distinct number type keeps its type through arithmetic, as on Nim:
    a sum or difference of two, or one scaled by a plain number, is one too;
    one over or times another is a plain number.\"\"\"
    def same(op):
        f = getattr(base, op)
        def g(self, o):
            r = f(self, o)
            return r if r is NotImplemented else cls(r)
        return g
    def scaled(op):
        f = getattr(base, op)
        sym = "*" if "mul" in op else "/"
        def g(self, o):
            r = f(self, o)
            if r is NotImplemented:
                return r
            if type(o) in (int, float):
                return cls(r) if type(r) is base else r
            # a unit times or over another: the one a derived unit names, if any
            pair = (type(o).__name__, cls.__name__) if op == "__rmul__" else (cls.__name__, type(o).__name__)
            made = _UNIT_RELATIONS.get((sym,) + pair)
            return globals()[made](r) if made else r
        return g
    for op in ("__add__", "__radd__", "__sub__", "__rsub__", "__mod__"):
        setattr(cls, op, same(op))
    for op in ("__mul__", "__rmul__", "__truediv__", "__floordiv__"):
        setattr(cls, op, scaled(op))
    cls.__neg__ = lambda self: cls(base.__neg__(self))
    cls.__pos__ = lambda self: self
    cls.__abs__ = lambda self: cls(base.__abs__(self))
    return cls\
"""


def _unit_class(name, base, indent):
    """`class Velocity_T(float)`: a distinct number type, which keeps its type
    through arithmetic (_UNIT_OPS_HELPER), so an overload chosen by type at run
    time chooses as Nim did when it compiled."""
    line = f"{_ind(indent)}class {name}({base}): __slots__ = ()"
    if base not in ("float", "int"):
        return line
    decls = getattr(ParserState, "py_top_decls", [])
    if _UNIT_OPS_HELPER not in decls:
        decls.append(_UNIT_OPS_HELPER)
        ParserState.py_top_decls = decls
    return f"{line}\n{_ind(indent)}_unit_ops({name}, {base})"


def _subrange_type(annotation):
    """ANNOTATION when it names an integer subrange, `type Q is 0 .. 100`;
    None otherwise."""
    t = (annotation or "").strip()
    info = getattr(ParserState, "tick_types", {}).get(t)
    if not info or "members" in info or info.get("is_float_range"):
        return None
    return t


def _range_checked(value, annotation):
    """VALUE checked against the subrange ANNOTATION names, as Nim checks
    every value given to one: a literal here, now, anything else when the
    program runs. VALUE itself for any other type."""
    t = _subrange_type(annotation)
    if t is None or not (value or "").strip():
        return value
    info = ParserState.tick_types[t]
    v, lo, hi = value.strip(), str(info["First"]).strip(), str(info["Last"]).strip()
    if all(_re_mod_p2s.fullmatch(r"-?\d[\d_]*", s) for s in (v, lo, hi)):
        if not int(lo) <= int(v) <= int(hi):
            raise SyntaxError(f"{v} is out of the range of {t}, {lo} .. {hi}")
        return value
    decls = getattr(ParserState, "py_top_decls", [])
    if not any("def _in_range" in d for d in decls):
        decls.append(_RANGE_CHECK_HELPER)
        ParserState.py_top_decls = decls
    return f"_in_range({v}, {t})"


def _target_range_type(target):
    """The subrange a target of an assignment is declared of: a variable's,
    or a field's, `self.q`, by the field's name."""
    sym = ParserState.symbol_table.lookup(target)
    if isinstance(sym, dict) and sym.get("type"):
        return _subrange_type(sym["type"])
    m = _re_mod_p2s.match(r"^[\w.\[\]()]+\.(\w+)$", target)
    if m:
        return getattr(ParserState, "py_range_fields", {}).get(m.group(1))
    return None


def distinct_kind_of(t):
    from ady_declarations import distinct_kind
    return distinct_kind(t)


def _wrap_narrowed_literal(value, annotation):
    """A number given where a narrowed type is declared is of it, and its
    range is checked: `let lat: Latitude_T = 45.0` is `Latitude_T(45.0)`."""
    from ady_declarations import wraps_or_checks, is_distinct
    t = _py_resolve_alias((annotation or "").strip())
    if (wraps_or_checks(t) or is_distinct(t) and distinct_kind_of(t) in ("float", "int")) \
            and _PY_NUMBER.match((value or "").strip()):
        return f"{t}({value.strip()})"
    return value


def _reject_distinct_mix(name, annotation, value):
    """Refuse a value of one type where a distinct type is declared, or a
    distinct value where another type is: `let d: Distance_T = v` over a
    Velocity_T, `let d: Distance_T = f` over a float, `let f: float = d`.
    The Nim backend refuses all three, and so does this one, at the same
    place: `Distance_T(f)` gets a float in and `float(d)` gets it out.

    The value may be arithmetic -- `let d: Distance_T = v * t` -- whose unit
    is worked out as the Nim backend's operators would. A literal takes the
    declared type, as it does on Nim; what cannot be told is left to Nim,
    which still refuses everything this lets through."""
    from ady_declarations import expr_unit, is_distinct, narrow_ancestors, UNIT_PLAIN
    target = _py_resolve_alias(_py_value_side(annotation))     # `T | !F` holds a T
    source = expr_unit(value, _py_atom_unit)
    if not source or source == target:
        return
    if target in narrow_ancestors(source):
        return                          # a narrowed type is its parent's value
    v = value.strip()
    if is_distinct(source):
        pass
    elif source == UNIT_PLAIN and is_distinct(target):
        source = _py_type_of_name(v) or "plain number"
    else:
        return
    if not (is_distinct(target) or is_distinct(source)):
        return
    from ady_declarations import as_written, unit_fix
    if is_distinct(target) and is_distinct(source):
        fix = unit_fix(target, v, source)       # an unrelated unit goes through the number
    elif is_distinct(target):
        fix = f"write {target}({as_written(v)})"
    else:
        fix = f"write {target}({as_written(v)})" if target in _DISTINCT_BASES else "convert it explicitly"
    raise SyntaxError(
        f"cannot give {as_written(v)}, {a_(source)}, to {name}, {a_(target)}: a distinct type "
        f"does not mix with any other -- {fix}")


def _reject_distinct_operands(left, op, right):
    """Refuse `v + d`, `v < d`, `v * v` and `d / v` where the units of the
    two sides do not allow it -- what the Nim backend refuses because it has
    no such operator. Sides are worked out with ady_declarations.expr_unit,
    so `v * 2.0 + d` is a Velocity_T plus a Distance_T; a side of unknown
    unit is left to Nim."""
    from ady_declarations import expr_unit, unit_mix_error
    op = op.strip()
    lu, ru = expr_unit(left, _py_atom_unit), expr_unit(right, _py_atom_unit)
    why = unit_mix_error(lu, op, ru)
    if why:
        raise SyntaxError(f"'{left.strip()} {op} {right.strip()}' {why}")


def _wrap_for_ordered_array(value, annotation):
    """A mapping value for a `dict[K, V]` -- a {K}V, or a [K]V whose K is no
    finite ordinal -- built as a plain dict. The `[k: v]` literal renders as
    an _EnumArray, which iterates its values: right for a [Color_T]V, whose
    keys are known in advance, wrong for a map whose keys are the news."""
    from hek_parsec import ParserState
    ann = (annotation or "").strip()
    ann = getattr(ParserState, "py_type_aliases", {}).get(ann, ann)
    if not ann.startswith("dict["):
        return value
    v = (value or "").strip()
    if v.startswith("_EnumArray(") and v.endswith(")"):
        return v[len("_EnumArray("):-1]
    return value


_re_p2s = _re_mod_p2s.compile(r'^[A-Za-z_]\w*$')


def _reject_str_to_path(name, annotation, value):
    """Refuse a plain str where a Path is declared, as the Nim backend does.

    Path is a distinct string there, so neither a literal nor a str-typed
    variable assigns to one -- `Path(s)` is how you make one (appendix A.1).
    Here Path is a str subclass and both went through silently, so a program
    written against this backend alone failed only once someone built it
    with ady2nim. Same rule, same place, both backends now.

    Deliberately narrow: a literal, or a name the symbol table types as str.
    An arbitrary expression's type is not known here, and a false refusal is
    worse than a missed one -- Nim still catches everything this does not.
    """
    from hek_parsec import ParserState
    if annotation != 'Path':
        return
    v = (value or '').strip()
    if not v:
        return
    lit = (v[:1] in (chr(34), chr(39))
           or (v[:1] in 'fFrR' and v[1:2] in (chr(34), chr(39))))
    if not lit:
        if not _re_p2s.match(v):
            return
        sym = ParserState.symbol_table.lookup(v)
        if not (isinstance(sym, dict) and (sym.get('type') or '') == 'str'):
            return
    raise SyntaxError(
        f'cannot assign a str to {name}, which is a Path: write Path({v}). '
        'Path is a distinct type on the Nim backend, so the conversion is '
        'explicit on both.')


def _domain_expr(key, dom):
    """How to iterate an `[O]T`'s domain in the generated Python, or None.

    Nim gives `array[O, T]` a slot for every value of O, already zeroed, so
    the Python side has to name the same values to fill the dict with. An
    enum iterates itself; a named integer subrange is a range over the bounds
    tick_types recorded; bool is its two values.

    `str` is deliberately absent. `[str]T` is `array[char, T]` on Nim, which
    rejects it outright -- "ordinal type expected; given: string" -- so there
    is no Nim behaviour for a fill to match. A float range is not ordinal
    either and cannot index an array on either backend.
    """
    if key.startswith("range("):
        return key                       # [lo..hi]T written inline
    if "members" in dom:
        return key                       # an Enum class, iterable in order
    if key == "bool":
        return "(False, True)"
    if "First" in dom and "Last" in dom and not dom.get("is_float_range"):
        # The bounds as written, not the Python name of the type: a subrange
        # renders as a plain `int` there and would not iterate.
        return f"range({dom['First']}, {dom['Last']} + 1)"
    return None


def _zero_value(annotation, _depth=0):
    """The empty value for ANNOTATION, mirroring Nim's zero-initialisation.

    A bare `x: T` binds nothing in Python, so a declaration written without an
    initialiser -- valid Adascript, since Nim zero-initialises it -- would
    raise on first use.  There is no honest zero for an arbitrary class or an
    optional, so those become None.

    A record is the exception: Nim gives it a real object with every field at
    its zero, and since the dataclass this backend emits now gives every field
    a default, `T()` is exactly that object.  Without it a record declared and
    then filled in field by field -- the ordinary way to build one -- starts
    as None and fails on the first assignment.
    """
    from hek_parsec import ParserState
    ann = (annotation or "").strip()
    if ann in getattr(ParserState, "record_types", ()):
        return f"{ann}()"
    scalars = {"int": "0", "float": "0.0", "bool": "False", "str": '""',
               "bytes": 'b""', "complex": "0j",
               # Natural is an int here and a 0-based subrange on Nim, which
               # zeroes to 0. Positive is deliberately absent: Nim would zero
               # it to 0 too, which is outside the type.
               "Natural": "0",
               # Nim zeroes a distinct string to an empty one, so `var p: Path`
               # compares equal to "" there while None here did not.
               "Path": 'Path("")'}
    if ann in scalars:
        return scalars[ann]
    # a distinct type zeroes as its base does: Velocity_T() is 0.0
    from ady_declarations import is_distinct
    if is_distinct(ann):
        return f"{ann}()"
    # another name for a type -- `type Reward_T is float` -- zeroes as it
    _target = getattr(ParserState, "py_type_aliases", {}).get(ann)
    if _target and _target != ann:
        return _zero_value(_target, _depth)
    # [E]T: Nim's array[E, T] has a slot per member, already zeroed, so
    # `var counts: [Phase_T]Natural` counts from the first += on either
    # backend. An empty _EnumArray raised KeyError on the first read here.
    # A generator rather than a literal, so a mutable zero -- [] for an
    # [E][]T -- is a fresh one per member and not one list shared by all.
    if ann.startswith("_Fixed[") and ann.endswith("]"):
        # [N]T: N slots, each with the zero of T, a fresh one apiece
        inner = ann[len("_Fixed["):-1]
        depth = 0
        for _i, _ch in enumerate(inner):
            if _ch in "[(":
                depth += 1
            elif _ch in "])":
                depth -= 1
            elif _ch == "," and depth == 0:
                n, elem = inner[:_i].strip(), inner[_i + 1:].strip()
                return f"[{_zero_value(elem, _depth + 1)} for _ in range({n})]"
    if ann.startswith("_EnumArray[") and ann.endswith("]"):
        inner = ann[len("_EnumArray["):-1]
        depth = 0
        for _i, _ch in enumerate(inner):
            if _ch in "[(":
                depth += 1
            elif _ch in "])":
                depth -= 1
            elif _ch == "," and depth == 0:
                _key, _elem = inner[:_i].strip(), inner[_i + 1:].strip()
                # Only when both halves are known: the domain has to be
                # one _domain_expr can name -- [3]int and [str]int reach
                # here too -- and the element needs a zero worth filling
                # with.
                # A nested [E][F]T nests the generators, each over a loop
                # name of its own; one that cannot be filled whole -- its
                # element has no zero -- is left empty, as before.
                _dom = getattr(ParserState, "tick_types", {}).get(_key, {})
                _ez = _zero_value(_elem, _depth + 1)
                _domain = _domain_expr(_key, _dom)
                if (_domain is not None and _ez not in ("None", "_EnumArray()")):
                    _m = f"_m{_depth}" if _depth else "_m"
                    return f"_EnumArray(({_m}, {_ez}) for {_m} in {_domain})"
                break
        return "_EnumArray()"
    # an integer subrange, `type Count_T is int range 0 .. N`, is a range()
    # here and zeroes to 0, as Nim's does
    if ann.startswith("range(") and ann.endswith(")"):
        return "0"
    for prefix, empty in (("_EnumArray[", "_EnumArray()"),
                          ("list[", "[]"), ("dict[", "{}"), ("set[", "set()"),
                          ("frozenset[", "frozenset()"), ("tuple[", "()"),
                          ("Counter[", "Counter()")):
        if ann.startswith(prefix):
            return empty
    if ann.startswith("Sequence["):
        return "[]"
    return "None"


def _either_zero(annotation):
    """The value a union declared without one holds: the zero of its first
    value member, as on Nim -- `var r: int | !Failure_T` and `var x: int |
    float` are both 0; None when that member is None. None (the Python
    object) when ANNOTATION is no such union."""
    from hek_py_declarations import union_of
    u = union_of(annotation)
    if u is None or u["kind"] not in ("plain", "either"):
        return None
    first = u["values"][0]
    return "None" if first == "None" else _zero_value(first)


@method(decl_ann_assign_stmt)
def to_py(self):
    """decl_ann_assign_stmt: decl_keyword IDENTIFIER ':' type_annotation ('=' expression)?"""
    # nodes[0] is decl_keyword (dropped), nodes[1] is name, nodes[2] is V_COLON, nodes[3] is type
    from hek_parsec import ParserState
    # The target is a name being bound, not a name being read, so the
    # substitutions the name emitter makes for reads -- `Inf` and the other
    # float specials -- must not apply: `let Inf: int = 3` shadows them,
    # exactly as it does on Nim.
    ParserState._declaring_target = True
    name = self.nodes[1].to_py()
    ParserState._declaring_target = False
    annotation = self.nodes[3].to_py()
    keyword = self.nodes[0].nodes[0] if hasattr(self.nodes[0], "nodes") else ""
    ParserState.symbol_table.add(name, annotation, keyword or "var")
    if CLASS_BODY_DEPTH and _subrange_type(annotation):
        # a field of a subrange: `self.q = ...` is checked, by its name
        ParserState.py_range_fields = getattr(ParserState, "py_range_fields", {})
        ParserState.py_range_fields[name] = annotation
    result = f"{name}: {annotation}"
    has_value = False
    for node in self.nodes[4:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_py()
                _reject_str_to_path(name, annotation, value)
                _reject_distinct_mix(name, annotation, value)
                value = _wrap_narrowed_literal(value, annotation)
                value = _wrap_seq_for_enum_array(value, annotation)
                value = _wrap_for_ordered_array(value, annotation)
                value = _wrap_list_for_queue(value, annotation)
                value = _range_checked(value, annotation)
                result += f" = {value}"
                has_value = True
    if not has_value and _either_zero(annotation) is not None:
        result += f" = {_either_zero(annotation)}"
    elif not has_value:
        zero = _zero_value(annotation)
        if not (CLASS_BODY_DEPTH and zero in _MUTABLE_ZEROS):
            result += f" = {zero}"
    return result

# --- own declaration ---
@method(own_stmt)
def to_py(self):
    """own x: T = expr  ->  x: T = expr  (Python GC handles lifecycle; 'own' is stripped)"""
    name = self.nodes[1].to_py()
    annotation = self.nodes[3].to_py()
    result = f"{name}: {annotation}"
    for node in self.nodes[4:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_py()
                result += f" = {value}"
    return result


# --- return ---
@method(decl_tuple_unpack)
def to_py(self):
    """decl_tuple_unpack: let/var/const (x, y) = expr -> Python (x, y) = expr"""
    # Strip the declaration keyword in Python
    targets = self.nodes[1].to_py()  # paren_group
    value = self.nodes[3].to_py()  # expression (nodes[2] is V_EQUAL)
    return f"{targets} = {value}"

@method(return_val)
def to_py(self):
    """return_val: 'return' expressions. A `T | E` needs nothing here: the
    value returned is the T or the E itself."""
    val = self.nodes[0].to_py()
    return f"return {_wrap_for_ordered_array(val, getattr(ParserState, '_py_return_type', ''))}"


@method(return_bare)
def to_py(self):
    """return_bare: 'return'"""
    return "return"


@method(return_stmt)
def to_py(self):
    """return_stmt: return_val | return_bare"""
    return self.nodes[0].to_py()


# --- pass / break / continue ---
@method(pass_stmt)
def to_py(self):
    """pass_stmt: 'pass'"""
    return "pass"


@method(break_stmt)
def to_py(self):
    """break_stmt: 'break'"""
    return "break"


@method(continue_stmt)
def to_py(self):
    """continue_stmt: 'continue'"""
    return "continue"


# --- del ---
@method(del_stmt)
def to_py(self):
    """del_stmt: 'del' star_expressions"""
    return f"del {self.nodes[0].to_py()}"


# --- assert ---
@method(assert_msg)
def to_py(self):
    """assert_msg: 'assert' expression ',' expression"""
    return f"assert {self.nodes[0].to_py()}, {self.nodes[1].to_py()}"


@method(assert_simple)
def to_py(self):
    """assert_simple: 'assert' expression"""
    return f"assert {self.nodes[0].to_py()}"


@method(assert_stmt)
def to_py(self):
    """assert_stmt: assert_msg | assert_simple"""
    return self.nodes[0].to_py()


# --- raise ---
@method(raise_from)
def to_py(self):
    """raise_from: 'raise' expression 'from' expression"""
    return f"raise {self.nodes[0].to_py()} from {self.nodes[1].to_py()}"


@method(raise_exc)
def to_py(self):
    """raise_exc: 'raise' expression"""
    return f"raise {self.nodes[0].to_py()}"


@method(raise_bare)
def to_py(self):
    """raise_bare: 'raise'"""
    return "raise"


@method(raise_stmt)
def to_py(self):
    """raise_stmt: raise_from | raise_exc | raise_bare"""
    return self.nodes[0].to_py()


# --- global / nonlocal ---
@method(global_stmt)
def to_py(self):
    """global_stmt: 'global' IDENTIFIER (',' IDENTIFIER)*"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return "global " + ", ".join(parts)


@method(nonlocal_stmt)
def to_py(self):
    """nonlocal_stmt: 'nonlocal' IDENTIFIER (',' IDENTIFIER)*"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return "nonlocal " + ", ".join(parts)


# --- import ---
@method(dotted_name)
def to_py(self):
    """dotted_name: IDENTIFIER ('.' IDENTIFIER)*"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                # seq is (V_DOT, IDENTIFIER)
                parts.append(seq.nodes[1].to_py())
    return ".".join(parts)


@method(import_as)
def to_py(self):
    """import_as: dotted_name ('as' IDENTIFIER)?

    Flattened: [IDENTIFIER, Several_Times[(V_DOT, IDENT)...maybe (IDENT)]]
    The Several_Times contains BOTH dotted_name tails and the optional 'as' alias.
    Distinguish by checking for V_DOT in each seq.
    """
    parts = [self.nodes[0].to_py()]
    alias = None
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if not hasattr(seq, "nodes"):
                continue
            # Check if this seq starts with V_DOT -> dotted_name part
            if (
                len(seq.nodes) >= 2
                and hasattr(seq.nodes[0], "nodes")
                and seq.nodes[0].nodes
                and seq.nodes[0].nodes[0] == "."
            ):
                parts.append(seq.nodes[1].to_py())
            elif len(seq.nodes) >= 1:
                # 'as' alias (ikw('as') is ignored, leaving just IDENTIFIER)
                alias = seq.nodes[0].to_py()
    name = ".".join(parts)
    if alias:
        return f"{name} as {alias}"
    return name


def _import_as_list_to_py(node):
    """Comma-separated import_as list -> 'mod, mod as alias, ...'.

    Shared by `import` and `pyimport`, which have the same shape."""
    parts = [node.nodes[0].to_py()]
    for nd in node.nodes[1:]:
        if not hasattr(nd, "nodes") or not nd.nodes:
            continue
        for seq in nd.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


@method(import_stmt)
def to_py(self):
    """import_stmt: 'import' import_as (',' import_as)*"""
    return "import " + _import_as_list_to_py(self)


@method(pyimport_stmt)
def to_py(self):
    """pyimport_stmt: 'pyimport' import_as (',' import_as)*

    pyimport marks an import that exists only in Python output — the Nim
    backend routes it through nimpy — so here it is a plain import."""
    return "import " + _import_as_list_to_py(self)


# --- from ... import ---
@method(import_name)
def to_py(self):
    """import_name: IDENTIFIER ('as' IDENTIFIER)?"""
    name = self.nodes[0].to_py()
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                alias = seq.nodes[0].to_py()
                return f"{name} as {alias}"
    return name


@method(import_star)
def to_py(self):
    """import_star: '*'"""
    return "*"


@method(import_names_paren)
def to_py(self):
    """import_names_paren with NL support."""
    from hek_tokenize import get_multiline_brackets
    pos = _get_bracket_start(self.nodes[0])
    ml = get_multiline_brackets()
    if pos and pos in ml:
        return ml[pos]

    def _find_import_names(node):
        names = []
        if node is None:
            return names
        if type(node).__name__ == 'import_name':
            names.append(node.to_py())
        elif hasattr(node, 'nodes') and node.nodes:
            for child in node.nodes:
                names.extend(_find_import_names(child))
        return names

    parts = _find_import_names(self)
    return '(' + ', '.join(parts) + ')'

@method(import_names)
def to_py(self):
    """import_names: import_name (',' import_name)* | '*'"""
    # If it's a star import, nodes[0] is import_star
    first = self.nodes[0].to_py()
    if first == "*":
        return "*"
    parts = [first]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)




def _import_name_to_py(nodes):
    """Render one import_name from a list of flattened nodes.

    An import_name is IDENTIFIER optionally followed by 'as' IDENTIFIER.
    After flattening: [IDENTIFIER, optional Several_Times[(IDENTIFIER)]]
    where the Several_Times holds the alias (ikw('as') was ignored).
    """
    name = nodes[0].to_py()
    for nd in nodes[1:]:
        if type(nd).__name__ == "Several_Times" and nd.nodes:
            seq = nd.nodes[0]
            if hasattr(seq, "nodes") and seq.nodes:
                child = seq.nodes[0]
                # If child is a raw IDENTIFIER (not import_name), it's an 'as' alias
                if type(child).__name__ == "IDENTIFIER":
                    name += f" as {child.to_py()}"
    return name


def _import_names_to_py(node):
    """Render import_names from a possibly flattened node.

    Flattened structure for import_names = import_name (',' import_name)* | '*':
      - '*': SSTAR(nodes=['*'])
      - 'path': [IDENTIFIER('path')]
      - 'path as p': [IDENTIFIER('path'), Several_Times[(IDENTIFIER('p'))]]
      - 'path, getcwd': [IDENTIFIER('path'), Several_Times[(import_name)]]
      - 'a as b, c as d': [IDENT('a'), ST[(IDENT('b'))], ST[(import_name('c','d'))]]

    The first Several_Times whose child wraps a raw IDENTIFIER is an 'as' alias.
    A Several_Times whose child wraps an import_name is a comma-separated next name.
    """
    if not hasattr(node, "nodes"):
        return str(node)
    # Check for parenthesized import (node itself is import_names_paren)
    if type(node).__name__ == "import_names_paren":
        return node.to_py()
    # Check for star import
    first = node.nodes[0]
    if first == "*" or (
        hasattr(first, "nodes") and first.nodes and first.nodes[0] == "*"
    ):
        return "*"

    # Collect import name parts
    # First import_name is built from leading nodes until we hit a comma-sep Several_Times
    first_name_nodes = [first]
    parts = []
    for nd in node.nodes[1:]:
        if type(nd).__name__ == "Several_Times" and nd.nodes:
            # Several_Times may contain multiple comma-separated items
            for seq in nd.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    child = seq.nodes[0]
                    if type(child).__name__ == "import_name":
                        # Comma-separated: finish the first name, add this one
                        if not parts:
                            parts.append(_import_name_to_py(first_name_nodes))
                        parts.append(child.to_py())
                    elif type(child).__name__ == "IDENTIFIER":
                        # 'as' alias for the current first name
                        first_name_nodes.append(nd)
                        break  # only one alias per Several_Times
                    else:
                        first_name_nodes.append(nd)
                        break
        else:
            first_name_nodes.append(nd)

    if not parts:
        parts.append(_import_name_to_py(first_name_nodes))
    return ", ".join(parts)


@method(from_rel_name)
def to_py(self):
    """from_rel_name: 'from' '.'+ dotted_name 'import' import_names"""
    # nodes: [Several_Times(dots), dotted_name, import_names]
    # But flattening may merge dotted_name into the node list.
    # Find dots first, then dotted_name, then import_names.
    dots = ""
    remaining = []
    for node in self.nodes:
        if type(node).__name__ == "Several_Times":
            # Check if this is dots or import_names parts
            for sub in node.nodes:
                if hasattr(sub, "nodes") and sub.nodes and sub.nodes[0] == ".":
                    dots += "."
                else:
                    remaining.append(sub)
        else:
            remaining.append(node)
    # remaining should be [dotted_name_parts..., import_names_parts...]
    # dotted_name starts with IDENTIFIER
    source = remaining[0].to_py() if remaining else ""
    names = (
        _import_names_to_py(remaining[-1])
        if len(remaining) > 1
        else remaining[0].to_py()
        if remaining
        else ""
    )
    return f"from {dots}{source} import {names}"


@method(from_rel_bare)
def to_py(self):
    """from_rel_bare: 'from' '.'+ 'import' import_names"""
    # nodes: [Several_Times(dots), import_names]
    dots = ""
    names_node = None
    for node in self.nodes:
        if type(node).__name__ == "Several_Times":
            for sub in node.nodes:
                if hasattr(sub, "nodes") and sub.nodes and sub.nodes[0] == ".":
                    dots += "."
                else:
                    names_node = sub
        elif names_node is None:
            names_node = node
    names = _import_names_to_py(names_node) if names_node else ""
    return f"from {dots} import {names}"


def _from_import_parts(self):
    """Split a 'from X <kw> Y' statement into its (source, names) strings.

    Flattened nodes: dotted_name may flatten to [IDENTIFIER, Several_Times...]
    followed by import_names nodes. The dotted_name part is nodes[0] (an IDENTIFIER);
    its dot-separated tails and the import_names are in subsequent nodes.
    For simple cases (single-segment source): [dotted_name, import_names_node].

    Shared by `from X import Y`, `from X pyimport Y` and `from X nimport Y`,
    which differ only in the keyword and so in how the result is rendered.
    """
    # Build source from dotted_name (nodes[0] + any V_DOT Several_Times)
    source_parts = [self.nodes[0].to_py()]
    names_start = 1
    for i, nd in enumerate(self.nodes[1:], 1):
        if type(nd).__name__ == "Several_Times" and nd.nodes:
            seq = nd.nodes[0]
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                first_child = seq.nodes[0]
                if (
                    hasattr(first_child, "nodes")
                    and first_child.nodes
                    and first_child.nodes[0] == "."
                ):
                    # Part of dotted_name: (V_DOT, IDENTIFIER)
                    source_parts.append(seq.nodes[1].to_py())
                    names_start = i + 1
                    continue
        break
    source = ".".join(source_parts)
    # Remaining nodes form import_names
    if names_start < len(self.nodes):
        names_node = self.nodes[names_start]
        # Wrap remaining nodes if needed
        if names_start + 1 < len(self.nodes):
            # Multiple remaining nodes — create a mock to pass to _import_names_to_py
            class _Mock:
                pass

            mock = _Mock()
            mock.nodes = self.nodes[names_start:]
            names = _import_names_to_py(mock)
        else:
            names = _import_names_to_py(names_node)
    else:
        names = ""
    return source, names


def _supply_stdlib_names(source, names):
    """Emit the bundled stdlib shims rather than importing them.

    `from stdlib import PriorityQueue` names the Nim shim in
    TO_NIM/STDLIB/stdlib.nim, which has no Python counterpart on the import
    path -- the statement raises ModuleNotFoundError before any of the
    generated code runs.  The classes are written into the output instead,
    so what comes out is a single file that stands on its own.

    Returns a replacement line, or None when the import is left alone --
    either it is not `stdlib`, or it names something not supplied here, in
    which case the statement is carried through unchanged rather than
    silently dropping part of it.
    """
    if source != "stdlib":
        return None
    from hek_py_expr import ensure_stdlib_helper, STDLIB_SUPPLIED
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    # Decided before anything is emitted: a statement naming one supplied and
    # one unsupplied thing keeps its import and gets no definitions, rather
    # than half of each.
    if not wanted or not all(n in STDLIB_SUPPLIED for n in wanted):
        return None
    for n in wanted:
        ensure_stdlib_helper(n)
    return f"# from {source} import {names}  (supplied inline for Python)"


@method(from_abs)
def to_py(self):
    """from_abs: 'from' dotted_name 'import' import_names"""
    source, names = _from_import_parts(self)
    supplied = _supply_stdlib_names(source, names)
    if supplied is not None:
        return supplied
    return f"from {source} import {names}"


@method(from_pyimport)
def to_py(self):
    """from_pyimport: 'from' dotted_name 'pyimport' import_names

    Python-only import — emit it as an ordinary from-import."""
    source, names = _from_import_parts(self)
    return f"from {source} import {names}"


# What Nim's math calls what Python's calls something else: a file `nimport`s math
# and writes Nim's names (ady2py renames `math.arctan(x)`; this, a name taken bare).
# Nim's os routines that a program takes with `from os nimport`, as Python
# functions doing what Nim's do: removeFile and removeDir succeed on what is
# not there, createDir makes the parents, splitFile gives (dir, name, ext).
_NIM_OS_FOR_PYTHON = {
    "fileExists": "def fileExists(p):\n    return _os.path.isfile(p)",
    "dirExists": "def dirExists(p):\n    return _os.path.isdir(p)",
    "removeFile": ("def removeFile(p):\n    if _os.path.lexists(p):\n"
                   "        _os.remove(p)"),
    "removeDir": "def removeDir(p):\n    _shutil.rmtree(p, ignore_errors=True)",
    "createDir": "def createDir(p):\n    _os.makedirs(p, exist_ok=True)",
    "walkFiles": ("def walkFiles(pattern):\n"
                  "    return [f for f in sorted(_glob.glob(pattern)) if _os.path.isfile(f)]"),
    "splitFile": ("class _SplitFile(NamedTuple):\n    dir: str\n    name: str\n    ext: str\n\n"
                  "def splitFile(p):\n    d, base = _os.path.split(p)\n"
                  "    name, ext = _os.path.splitext(base)\n"
                  "    if base.startswith(\".\") and not ext:\n        name, ext = base, \"\"\n"
                  "    return _SplitFile(d, name, ext)"),
    "getCurrentDir": "def getCurrentDir():\n    return _os.getcwd()",
    "setCurrentDir": "def setCurrentDir(p):\n    _os.chdir(p)",
    "joinPath": "def joinPath(*parts):\n    return _os.path.join(*parts)",
    "getLastModificationTime": ("class _Time(float):\n    def toUnix(self):\n        return int(self)\n\n"
                                "def getLastModificationTime(p):\n    return _Time(_os.path.getmtime(p))"),
}

_MATH_NAMES = {n for n in dir(__import__("math")) if not n.startswith("_")}

_MATH_FOR_PYTHON = {
    "arcsin": "asin", "arccos": "acos", "arctan": "atan", "arctan2": "atan2",
    "arcsinh": "asinh", "arccosh": "acosh", "arctanh": "atanh",
    "ln": "log", "degToRad": "radians", "radToDeg": "degrees",
}


@method(from_nim_abs)
def to_py(self):
    """from_nim_abs: 'from' dotted_name 'nimport' import_names

    Nim-only import, so it is commented out in Python output — the same
    treatment `nimport_stmt` gets."""
    source, names = _from_import_parts(self)
    if source == "math":
        # Nim's math and Python's are one library under two spellings: the names
        # taken bare are Python's, under Nim's (`arctan2` is atan2, `PI` is pi)
        import math as _pymath
        consts = {"PI": "pi", "TAU": "tau", "E": "e", "Inf": "inf", "NaN": "nan"}
        taken = []
        for n in (x.strip() for x in names.strip("()").split(",")):
            py = consts.get(n) or _MATH_FOR_PYTHON.get(n, n)
            if n and hasattr(_pymath, py):
                taken.append(n if py == n else f"{py} as {n}")
        if taken:
            return f"from math import {', '.join(taken)}  # from math nimport {names}"
    if source == "os":
        # Nim's os routines, written in Python's: each name taken that has one
        taken = [n for n in (x.strip() for x in names.strip("()").split(",")) if n in _NIM_OS_FOR_PYTHON]
        if taken:
            decls = getattr(ParserState, "py_top_decls", [])
            for n in taken:
                if _NIM_OS_FOR_PYTHON[n] not in decls:
                    decls.append(_NIM_OS_FOR_PYTHON[n])
            ParserState.py_top_decls = decls
            ParserState.nim_imports.update({"import os as _os", "import glob as _glob",
                                            "import shutil as _shutil"})
            if "splitFile" in taken:
                ParserState.nim_imports.add("from typing import NamedTuple")
    return f"# from {source} nimport {names}"


@method(from_stmt)
def to_py(self):
    """from_stmt: from_rel_name | from_rel_bare | from_abs"""
    return self.nodes[0].to_py()


# --- type alias ---
@method(enum_def)
def to_py(self):
    """enum_def: 'enum' enum_member (',' enum_member)* ','?"""
    from ady_enums import member
    found = [member(self.nodes[0])]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes') and len(seq.nodes) >= 1:
                found.append(member(seq.nodes[0]))
    # a valued member is written NAME=VALUE; _emit_enum_py reads it back
    return "enum " + ", ".join(n if v is None else f"{n}={v}" for n, v in found)


def _emit_enum_py(name, member_names, indent=0):
    """Emit a Python Enum class body for a type name and its members.

    Shared by the inline 'type T is enum A, B' form (type_stmt) and the
    indented 'type T is enum:' block form (type_block_stmt). A member may be
    written NAME=VALUE: then every member is, and the values are the order."""
    from ady_enums import checked, has_gaps
    pairs = []
    for text in member_names:
        n, _, v = text.partition("=")
        pairs.append((n.strip(), int(v) if v.strip() else None))
    checked(name, pairs)
    member_names = [n for n, _ in pairs]
    ParserState.nim_imports.add("from enum import Enum")
    ParserState.tick_types[name] = {"First": member_names[0], "Last": member_names[-1], "members": member_names,
                                    "gapped": has_gaps(pairs)}
    lines = [f"{_ind(indent)}class {name}(Enum):"]
    py_members = []
    for i, (m, value) in enumerate(pairs):
        py_m = f"_{m}" if m.isdigit() else m
        lines.append(f"{_ind(indent + 1)}{py_m} = {i if value is None else value}")
        py_members.append((m, py_m))
    # Nim orders members by their values; Python's Enum does not order at all.
    for op, dunder in (("<", "lt"), ("<=", "le"), (">", "gt"), (">=", "ge")):
        lines.append(f"{_ind(indent + 1)}def __{dunder}__(self, other): return self.value {op} other.value")
    # Nim's `$` on an enum is the bare member name, and so is 'Image here.
    # Python's default is "Stage_T.STAGE2", so the same f-string printed two
    # different things depending on the backend.
    # and a container of them shows the same names, as `repr` would otherwise
    # give "<Stage_T.STAGE2: 1>" for each element.
    lines.append(f"{_ind(indent + 1)}def __str__(self): return self.name")
    # `int(k)` is the member's value on Nim; Python's Enum refuses it.
    lines.append(f"{_ind(indent + 1)}def __int__(self): return self.value")
    lines.append(f"{_ind(indent + 1)}__index__ = __int__")
    lines.append(f"{_ind(indent + 1)}__repr__ = __str__")
    # Unpack enum members as bare names (Nim uses bare names)
    for orig, py_m in py_members:
        if not orig.isdigit():
            lines.append(f"{_ind(indent)}{py_m} = {name}.{py_m}")
    return "\n".join(lines)


@method(nimport_stmt)
def to_py(self):
    """nimport_stmt: Nim-only import, stripped in Python output"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes'):
                for child in seq.nodes:
                    cname = type(child).__name__
                    if cname == "dotted_name":
                        parts.append(child.to_py())
    return "# nimport " + ", ".join(parts)


def _bound_text(node):
    """The text of a subrange bound: `3`, `N`, `N - 1`, `-1`."""
    if hasattr(node, "nodes") and node.nodes:
        return "".join(_bound_text(n) for n in node.nodes)
    return str(getattr(node, "node", node))


@method(subrange_def)
def to_py(self):
    """subrange_def: INTEGER ('..' | '..<') INTEGER -> Python range()"""
    lo = _bound_text(self.nodes[0])
    hi = _bound_text(self.nodes[2])
    is_exclusive = getattr(self.nodes[1], 'node', None) == "..<"
    if is_exclusive:
        return f"range({lo}, {hi})"
    else:
        return f"range({lo}, {hi} + 1)"



@method(constrained_subrange_def)
def to_py(self):
    """constrained_subrange_def: IDENTIFIER subrange_def -> Python range()"""
    return self.nodes[1].to_py()


@method(float_range_def)
def to_py(self):
    """float_range_def: 'float' 'range' NUMBER ('..'|'..<') NUMBER -> float (Python has no float subrange)"""
    lo = str(self.nodes[2].node)
    hi = str(self.nodes[4].node)
    return f"float  # range {lo} .. {hi}"


@method(int_range_def)
def to_py(self):
    """int_range_def: 'int' 'range' subrange_def -> delegates to subrange_def"""
    return self.nodes[2].to_py()  # nodes[0]=int, nodes[1]=range, nodes[2]=subrange_def


@method(type_alias_params)
def to_py(self):
    """type_alias_params: '[' IDENTIFIER (',' IDENTIFIER)* ']'"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes') and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_py())
    return f"[{', '.join(parts)}]"

@method(type_stmt)
def to_py(self, indent=0):
    """type_stmt: 'type' IDENTIFIER type_alias_params? '=' (enum_def | expression)

    Takes an indent, as its block-form sibling type_block_stmt does. Without
    one, a declaration inside a function reached the caller's fallback for a
    statement that renders to several lines -- which indents the first line
    and leaves the rest alone, because the lines after the first are usually
    the contents of a multi-line string and must not be touched. An enum's
    are not: they are generated code, and landed at column zero, outside the
    function they were declared in.
    """
    name = self.nodes[0].to_py()
    params = ""
    eq_idx = 1
    for i, node in enumerate(self.nodes[1:], 1):
        if type(node).__name__ == 'type_alias_params':
            params = node.to_py()
            eq_idx = i + 1
            break
        elif hasattr(node, 'nodes') and node.nodes:
            first = node.nodes[0] if hasattr(node, 'nodes') else node
            if type(first).__name__ == 'type_alias_params':
                params = first.to_py()
                eq_idx = i + 1
                break
    # RHS is the last node — works whether V_EQUAL is present ('=') or absent ('is')
    rhs = self.nodes[-1]
    rhs_type = type(rhs).__name__
    if name in (getattr(ParserState, "py_scaled_units", None) or {}):
        # `type Dollar_T is 100 * Dollar_in_cent_T`: the float view of the
        # base; the conversions between them are written where they are
        # called (hek_py_expr._scaled_conversion)
        _note_alias(name, name)
        ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
        return _unit_class(name, "float", indent)
    if rhs_type == 'distinct_def':
        # A class of its own, so `Velocity_T(x)` makes one and `float(v)`
        # takes it back out; the values are the base type's, and print and
        # format as they do. That a Velocity_T does not mix with a float or
        # a Distance_T is checked where it is given one: see
        # _reject_distinct_mix, and the Nim compiler for everything else.
        base = rhs.nodes[0].to_py()
        _note_alias(name, name)
        ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
        return _unit_class(name, base, indent)
    if rhs_type == 'derived_def':
        # `type Velocity_T is Distance_T / Duration_T`: a class of the
        # operands' base, like any distinct type. What the operators between
        # the units make is checked at transpile time -- see
        # _reject_distinct_operands -- and by the Nim compiler.
        from ady_declarations import distinct_kind
        base = _DISTINCT_BASES.get(distinct_kind(name), "float")
        _note_alias(name, name)
        ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
        return _unit_class(name, base, indent)
    if rhs_type == 'narrowed_def':
        # a subclass of the parent, so it goes up without a cast; a new one
        # is made only from a number in range
        from ady_declarations import distinct_kind, parse_narrowed
        parent, lo, hi, excl = parse_narrowed(ParserState.ady_type_decls[name])
        base = _DISTINCT_BASES.get(distinct_kind(name), "float")
        if base == "float" and not any(c in lo + hi for c in ".eE"):
            lo, hi = lo + ".0", hi + ".0"
        _note_alias(name, name)
        ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
        ind = _ind(indent)
        shown = f"[{lo}, {hi}{')' if excl else ']'}"
        # its zero, a field's value until one is given: 0 where the range holds it
        try:
            zero = ("0.0" if base == "float" else "0") if float(lo) <= 0 <= float(hi) else lo
        except ValueError:
            zero = lo
        return "\n".join([
            f"{ind}class {name}({parent}):",
            f"{ind}    __slots__ = ()",
            f"{ind}    def __new__(cls, x={zero}):",
            f"{ind}        if not ({lo} <= x {'<' if excl else '<='} {hi}):",
            f'{ind}            raise AssertionError(f"{name} value {{x}} out of range {shown}")',
            f"{ind}        return super().__new__(cls, {base}(x))"])
    if rhs_type in ('mod_def', 'parent_mod_def'):
        return _py_mod_class(name, indent)
    if rhs_type == 'distinct_float_range_def':
        fr = rhs.nodes[0]
        lo = "".join(str(getattr(n, "node", n)) for n in (fr.nodes[2].nodes if getattr(fr.nodes[2], "nodes", None) else [fr.nodes[2]]))
        hi = "".join(str(getattr(n, "node", n)) for n in (fr.nodes[4].nodes if getattr(fr.nodes[4], "nodes", None) else [fr.nodes[4]]))
        ParserState.tick_types[name] = {"First": lo, "Last": hi, "is_float_range": True}
        _note_alias(name, name)
        ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
        return f"{_ind(indent)}class {name}(float): __slots__ = ()  # range {lo} .. {hi}"
    if rhs_type == 'float_range_def':
        lo = str(rhs.nodes[2].node)
        hi = str(rhs.nodes[4].node)  # [float, range, lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi, "is_float_range": True}
        _note_alias(name, "float")
        return f"{_ind(indent)}{name} = float  # range {lo} .. {hi}"
    if rhs_type == 'int_range_def':
        sr = rhs.nodes[2]  # the subrange_def inside (nodes[0]=int, nodes[1]=range)
        lo = _bound_text(sr.nodes[0])
        hi = _bound_text(sr.nodes[2])   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        _note_alias(name, rhs.to_py())
        return f"{_ind(indent)}{name} = {rhs.to_py()}"
    if rhs_type == 'constrained_subrange_def':
        sr = rhs.nodes[1]  # the subrange_def inside
        lo = _bound_text(sr.nodes[0])
        hi = _bound_text(sr.nodes[2])   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        _note_alias(name, rhs.to_py())
        return f"{_ind(indent)}{name} = {rhs.to_py()}"
    if rhs_type == 'subrange_def':
        # Register First/Last for tick attributes (Name'First, Name'Last)
        lo = _bound_text(rhs.nodes[0])
        hi = _bound_text(rhs.nodes[2])  # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        _note_alias(name, rhs.to_py())
        return f"{_ind(indent)}{name} = {rhs.to_py()}"
    if rhs_type == 'enum_def':
        members = rhs.to_py()
        member_names = [m.strip() for m in members[len("enum "):].split(",")]
        return _emit_enum_py(name, member_names, indent)
    value = rhs.to_py()
    _note_alias(name, value)
    return f"{_ind(indent)}{name} = {value}"


def _py_mod_class(name, indent):
    """`type N is mod M` / `type N is P mod M` -> a class whose every value is
    wrapped into 0 .. M by `%`, which takes the sign of M on both backends. The
    operators give an N again, so a sum or a scaled N wraps; N / N is a ratio."""
    from ady_declarations import distinct_kind, parse_mod, mod_modulus
    parent, mod = parse_mod(ParserState.ady_type_decls[name])
    base = _DISTINCT_BASES.get(distinct_kind(name), "float")
    mod = mod_modulus(mod, base)
    _note_alias(name, name)
    ParserState.py_type_names = getattr(ParserState, "py_type_names", set()) | {name}
    ind = _ind(indent)
    ops = ["__add__", "__radd__", "__sub__", "__rsub__", "__mul__", "__rmul__"]
    lines = [f"{ind}class {name}({parent or base}):",
             f"{ind}    __slots__ = ()",
             f"{ind}    def __new__(cls, x=0):",
             f"{ind}        return super().__new__(cls, {base}(x) % {mod})"]
    for op in ops:
        lines.append(f"{ind}    def {op}(self, o): return {name}({base}.{op}(self, o))")
    lines.append(f"{ind}    def __neg__(self): return {name}(-{base}(self))")
    if base == "float":
        lines += [f"{ind}    def __truediv__(self, o):",
                  f"{ind}        r = float.__truediv__(self, o)",
                  f"{ind}        return r if isinstance(o, {name}) else {name}(r)"]
    else:
        lines.append(f"{ind}    def __floordiv__(self, o): return {name}(int.__floordiv__(self, o))")
    return "\n".join(lines)


def _note_alias(name, value):
    """Remember that NAME is another name for the type VALUE -- `type Reward_T
    is float` -- so that _zero_value zeroes it as that type."""
    aliases = getattr(ParserState, "py_type_aliases", None)
    if aliases is None:
        aliases = ParserState.py_type_aliases = {}
    aliases[name] = value



# --- simple_stmt ---
@method(subst_stmt)
def to_py(self):
    """subst_stmt: primary '=' s/pat/repl/flags -> Python: lhs = re.sub(r'pat', 'repl', lhs, flags=...)"""
    import re as _re_s
    from hek_py_expr import _ensure_pymatch_helper, _py_re_flags
    _ensure_pymatch_helper()
    lhs = self.nodes[0].to_py()
    raw = self.nodes[1].node     # e.g. "s/\d+/[N]/gi"
    j = 2                        # skip leading 's/'
    pat_start = j
    while j < len(raw):
        if raw[j] == '\\': j += 2
        elif raw[j] == '/': break
        else: j += 1
    pat = raw[pat_start:j]
    repl_start = j + 1
    j = repl_start
    while j < len(raw):
        if raw[j] == '\\': j += 2
        elif raw[j] == '/': break
        else: j += 1
    repl = raw[repl_start:j]
    repl = repl.replace('\\/', '/')      # an escaped delimiter is the delimiter
    flags_str = raw[j + 1:]
    # $+N → \N and $+{name} → \g<name>  (Python re.sub backreference syntax)
    repl = _re_s.sub(r'\$\+(\d+)', r'\\\1', repl)
    repl = _re_s.sub(r'\$\+\{(\w+)\}', r'\\g<\1>', repl)
    flags_val = _py_re_flags(flags_str)
    safe_pat = pat.replace("'", "\\'")
    safe_repl = repl.replace("'", "\\'")
    if flags_val != "0":
        return f"{lhs} = _re_mod.sub(r'{safe_pat}', r'{safe_repl}', {lhs}, flags={flags_val})"
    return f"{lhs} = _re_mod.sub(r'{safe_pat}', r'{safe_repl}', {lhs})"


@method(print_bare)
def to_py(self):
    """print_bare: a bare 'print' -> an empty line."""
    return 'print()'


@method(print_stmt)
def to_py(self):
    """print_stmt: 'print' star_expressions -> Python: print(star_expressions)

    Adascript allows Python-2-style bare print statements without parentheses.
    The transpiler rewrites them as print() calls so the output is valid
    Python 3.
    """
    return f"print({self.nodes[0].to_py()})"


# --- simple_stmt ---


# --- statement modifier ---
@method(return_bare_if)
def to_py(self):
    """return_bare_if: a bare 'return' standing before an `if` modifier."""
    return self.nodes[0].to_py()


@method(exit_call)
def to_py(self, indent=0):
    """exit_call: `die(...)` or `quit(...)` standing before an `if` modifier;
    the call is emitted as any other call, builtin rewrite included."""
    return self.nodes[0].to_py()


@method(modifier_if_stmt)
def to_py(self, indent=0):
    """modifier_if_stmt: ('return'|'break'|'continue'|die()|quit()) 'if' disjunction

    -> Python: `if cond: <stmt>`, the one-line form both backends emit rather
    than a two-line block: stmt_line hands a statement a single indent and
    joins whatever comes back, so a rendering that spans lines would have
    every line after the first re-indented to the first one's column.
    """
    body, cond = self.nodes[0], self.nodes[1]
    return f"{_ind(indent)}if {cond.to_py()}: {body.to_py().strip()}"


# --- stmt_line ---
_TAKES_INDENT_CACHE = {}


def _to_py_takes_indent(fn):
    """True when this to_py's first parameter is an indent rather than a prec.

    Statement nodes take `indent`, expression nodes take `prec`, and both are
    a single positional -- so calling one as the other is accepted in silence.
    Cached: this is asked once per statement rendered.
    """
    import inspect
    key = getattr(fn, "__func__", fn)
    hit = _TAKES_INDENT_CACHE.get(key)
    if hit is None:
        try:
            params = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            params = []
        hit = bool(params) and params[0] == "indent"
        _TAKES_INDENT_CACHE[key] = hit
    return hit


@method(stmt_line)
def to_py(self, indent=0):
    """stmt_line: simple_stmt (';' simple_stmt)* ';'? NEWLINE

    Takes an indent so that a statement rendering to several lines can place
    them itself.  The caller's fallback for a statement that cannot take one
    indents the first line and leaves the rest, since the lines after the
    first are usually the contents of a multi-line string and must not be
    touched.  A `type T is enum ...` inside a function is the exception:
    those lines are generated code, and used to land at column zero.

    Only the first statement on the line is placed -- the ones after a
    semicolon are continuations of it, and carry no indentation of their own.
    """
    from hek_tokenize import RichNL
    ind = _ind(indent)

    def _placed(node):
        """Render a statement, letting it place its own lines when it can.

        The test has to be on the parameter's *name*, not on whether the call
        raises: an expression node's to_py takes `prec`, so passing an indent
        positionally is accepted in silence, adds no indentation, and quietly
        rewrites the expression's parenthesisation into the bargain.
        """
        if not hasattr(node, "to_py"):
            # a statement of the JavaScript backend only (jsvar): nothing here renders it
            raise SyntaxError("`jsvar` is for the JavaScript backend (ady2nim js); "
                              "it has no meaning in Python")
        if _to_py_takes_indent(node.to_py):
            return node.to_py(indent)
        return ind + node.to_py()

    parts = [_placed(self.nodes[0])]
    newline_node = None
    # A call returning `T | !F` whose result nobody takes drops its failure --
    # unless it stands last in a routine, where it is the routine's value.
    if (type(self.nodes[0]).__name__ == "expressions"
            and id(self) not in RETURN_NODES):
        from ady_stmt import refuse_dropped_failure
        from hek_parsec import ParserState as _PS_df
        import re as _re_df
        def _is_either_call(text):
            _m = _re_df.match(r"^(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\(", text)
            return bool(_m) and _m.group(1) in getattr(_PS_df, "result_procs", set())
        refuse_dropped_failure(parts[0], _is_either_call)

    for node in self.nodes[1:]:
        # Check if this node wraps a RichNL (NEWLINE token preserved as node)
        if hasattr(node, 'nodes') and node.nodes:
            inner = node.nodes[0] if len(node.nodes) == 1 else None
            if inner is not None and isinstance(inner, RichNL):
                newline_node = inner
                continue
            # Otherwise it's a Several_Times of semicolon-separated stmts
            for seq in node.nodes:
                if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                    parts.append(seq.nodes[0].to_py())
        elif isinstance(node, RichNL):
            newline_node = node

    result = "; ".join(parts)
    if id(self) in RETURN_NODES:
        # `return` goes before the statement, not before its indentation.
        result = ind + "return " + (result[len(ind):] if result.startswith(ind)
                                    else result)
    # Append inline comment if present in the NEWLINE RichNL
    if newline_node is not None and hasattr(newline_node, 'comments') and newline_node.comments:
        for kind, text, ind in newline_node.comments:
            if kind == 'comment':
                result += '  ' + text
    return result



###############################################################################
# Public API
###############################################################################


if __name__ == "__main__":
    print("=" * 60)
    print("Python 3.14 Simple Statement Parser Tests")
    print("=" * 60)

    tests = [
        # --- Assignment ---
        ("x = 1", "x = 1"),
        ("a = b = 1", "a = b = 1"),
        ("a, b = 1, 2", "a, b = 1, 2"),
        ("x = y = z = 0", "x = y = z = 0"),
        # --- Augmented assignment ---
        ("x += 1", "x += 1"),
        ("x -= 1", "x -= 1"),
        ("x *= 2", "x *= 2"),
        ("x /= 2", "x /= 2"),
        ("x //= 2", "x //= 2"),
        ("x %= 3", "x %= 3"),
        ("x **= 2", "x **= 2"),
        ("x @= m", "x @= m"),
        ("x <<= 1", "x <<= 1"),
        ("x >>= 1", "x >>= 1"),
        ("x &= mask", "x &= mask"),
        ("x |= flag", "x |= flag"),
        ("x ^= bits", "x ^= bits"),
        # --- Annotated assignment ---
        ("x: int", "x: int"),
        ("x: int = 1", "x: int = 1"),
        ("x: str = 'hello'", "x: str = 'hello'"),
        # --- Declaration with keyword ---
        ("var x : int", "x: int"),
        ("let y : int = 8", "y: int = 8"),
        ("const z : int = 44", "z: int = 44"),
        # --- return ---
        ("return", "return"),
        ("return x", "return x"),
        ("return x, y", "return x, y"),
        # --- pass / break / continue ---
        ("pass", "pass"),
        ("break", "break"),
        ("continue", "continue"),
        # --- del ---
        ("del x", "del x"),
        ("del a, b", "del a, b"),
        # --- assert ---
        ("assert x", "assert x"),
        ("assert x, 'msg'", "assert x, 'msg'"),
        # --- raise ---
        ("raise", "raise"),
        ("raise ValueError", "raise ValueError"),
        ("raise ValueError from exc", "raise ValueError from exc"),
        # --- global / nonlocal ---
        ("global x", "global x"),
        ("global x, y", "global x, y"),
        ("nonlocal x", "nonlocal x"),
        ("nonlocal a, b, c", "nonlocal a, b, c"),
        # --- import ---
        ("import os", "import os"),
        ("import os.path", "import os.path"),
        ("import os as o", "import os as o"),
        ("import os, sys", "import os, sys"),
        # --- from import ---
        ("from os import path", "from os import path"),
        ("from os import path as p", "from os import path as p"),
        ("from os import path, getcwd", "from os import path, getcwd"),
        ("from . import foo", "from . import foo"),
        ("from ..pkg import bar", "from ..pkg import bar"),
        ("from os import *", "from os import *"),
        # --- type alias ---
        ("type Vector = list", "type Vector = list"),
        ("type Color = enum RED, BLUE, YELLOW", "class Color(Enum):\n    RED = auto()\n    BLUE = auto()\n    YELLOW = auto()"),
        # --- expression statement ---
        ("f(x)", "f(x)"),
        ("x", "x"),
        ("1 + 2", "1 + 2"),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            result = parse_stmt(code)
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

