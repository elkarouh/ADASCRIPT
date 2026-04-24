#!/usr/bin/env python3
"""Nim translation methods for Python 3.14 simple statements.

Adds to_nim() methods to the statement parser classes defined in
hek_py3_stmt.py. Import this module to enable .to_nim() on statement AST nodes.

Usage:
    from hek_nim_stmt import *
    ast = parse_stmt("x = 1")
    print(ast.to_nim())  # var x = 1
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))
# (no TO_PYTHON dependency needed)

from hek_parsec import method, ParserState
from py3stmt import *  # noqa: F403 — need all parser rule names
from py3stmt import parse_stmt
import hek_nim_expr  # noqa: F401 — registers expr to_nim() methods
import hek_nim_declarations  # noqa: F401
from hek_nim_expr import _infer_literal_nim_type
from hek_helpers import _ind

###############################################################################
# to_nim() methods
###############################################################################

# Augmented assignment operator map: Python augop -> (nim_op, needs_expansion)
# needs_expansion=True means we must expand x op= y -> x = x nim_op y
_AUGOP_TO_NIM = {
    "+=": ("+=", False),
    "-=": ("-=", False),
    "*=": ("*=", False),
    "/=": ("/=", False),
    "//=": ("div", True),
    "%=": ("mod", True),
    "**=": ("^", True),
    "@=": ("@", True),
    "<<=": ("shl", True),
    ">>=": ("shr", True),
    "&=": ("and", True),
    "|=": ("or", True),
    "^=": ("xor", True),
}

# Python stdlib module -> Nim import mapping.
# None means the import is erased (e.g. typing).
# A string is the Nim module to import via ParserState.nim_imports.
# "nimpy" means: use pyImport() via nimpy (no native Nim equivalent).
# Maps nimport names that differ from their Nim module name.
# Only entries where the AdaScript name != the Nim import name are needed.
# Maps nimport names that differ from their Nim module name, plus known
# AdaScript stdlib modules that 'from X import Y' should resolve natively.
# Only entries where the AdaScript name != the Nim import name are needed
# for nimport; the full set is needed for from_abs.to_nim().
_NIMPORT_NAME_MAP = {
    "time":     "times",
    "datetime": "times",
    "calendar": "times",
    "string":   "strutils",
    "cmath":    "complex",
    "fnmatch":  "os",
    "textwrap": "strutils",
    "unicode":  "unicode",
    "itertools":"sequtils",
    "heapq":    "heapqueue",
    "bisect":   "algorithm",
    "json":     "std/json",
    "asyncio":  "asyncdispatch",
    # AdaScript stdlib — 'from stdlib import X' resolves natively
    "stdlib":   "stdlib",
    "math":     "math",
}

# Alias used by from_abs.to_nim() to check known resolvable modules
_PY_MODULE_TO_NIM = _NIMPORT_NAME_MAP

# Per-module function call translations: module_name -> {py_func: nim_expr_template}.
# Templates use {args} for the full argument list and {arg0}, {arg1}, … for individual args.
# All module function translations removed — users write native AdaScript calls.
# 're' is handled via nimpy (Python API), not translated.
_PY_MODULE_FUNC_TO_NIM = {}


# --- visible tokens ---
@method(augop)
def to_nim(self):
    """augop: '+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' | '<<=' | '>>=' | '**=' | '//='"""
    return self.nodes[0].nodes[0]  # raw op string, translated at aug_assign level


@method(V_EQUAL)
def to_nim(self):
    """V_EQUAL: visible '=' token -> Nim: '='"""
    return "="


@method(V_COLON)
def to_nim(self):
    """V_COLON: visible ':' operator token"""
    return ":"


@method(V_DOT)
def to_nim(self):
    """V_DOT: visible '.' token -> unchanged"""
    return "."


def _float_range_assert(varname, type_name):
    """Return a Nim assert statement for a float range type variable.

    Looks up the range bounds in ParserState.tick_types[type_name].
    Returns None if the type is not a float range type.
    """
    info = getattr(ParserState, 'tick_types', {}).get(type_name)
    if not info or not info.get('is_float_range'):
        return None
    lo = info['First']
    hi = info['Last']
    return (
        f'assert {varname} >= {lo} and {varname} <= {hi}, '
        f'"{type_name} value " & ${varname} & " out of range [{lo}, {hi}]"'
    )


# --- assignment ---
@method(assign_stmt)
def to_nim(self):
    """assign_stmt: star_expressions ('=' star_expressions)+
    Python: a = b = 1  ->  Nim: var a = 1 (chained not supported, just use =)
    """
    parts = [self.nodes[0].to_nim()]
    rhs_node = None
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                rhs_node = seq.nodes[1]
                parts.append(rhs_node.to_nim())
    # Skip var for dotted assignments (field mutation), indexed assignments,
    # and variables already declared in the current scope
    lhs = parts[0]
    # Tuple assignment to existing lvalues: a[i], a[j] = a[j], a[i]
    # If every target is a subscript or already-declared name (not a new decl),
    # emit swap() for the two-element swap pattern or temp-var expansion otherwise.
    if "," in lhs and not lhs.startswith("(") and len(parts) == 2:
        import re as _re_ta
        targets = [t.strip() for t in lhs.split(",")]
        rhs_parts = [r.strip() for r in parts[1].split(",")]
        _is_lvalue = lambda s: ("[" in s or "." in s or
                                bool(ParserState.symbol_table.lookup(s.strip())))
        all_lvalues = all(_is_lvalue(t) for t in targets)
        if all_lvalues:
            # Two-target swap: a[i], a[j] = a[j], a[i]  ->  swap(a[i], a[j])
            if (len(targets) == 2 and len(rhs_parts) == 2
                    and targets[0] == rhs_parts[1] and targets[1] == rhs_parts[0]):
                return f"swap({targets[0]}, {targets[1]})"
            # General case: use temps to avoid aliasing
            lines = []
            for k, r in enumerate(rhs_parts):
                lines.append(f"let _t{k} = {r}")
            for k, t in enumerate(targets):
                lines.append(f"{t} = _t{k}")
            return "\n".join(lines)
        # All targets are new names — declare with let
        tgt_str = ", ".join(targets)
        return f"let ({tgt_str}) = {parts[1]}"
    if "." in lhs or "[" in lhs:
        prefix = ""
    elif ParserState.symbol_table.lookup(lhs):
        prefix = ""
    else:
        prefix = "var "
    # Nim's implicit 'result' variable: no var needed inside typed procs
    if lhs == "result" and getattr(ParserState, '_current_return_type', ''):
        prefix = ""
    # Record type in symbol table (after checking for re-declaration)
    name = self.nodes[0].to_nim() if hasattr(self.nodes[0], "to_nim") else None
    if name and rhs_node:
        inferred = _infer_literal_nim_type(rhs_node)
        # Only update type if symbol is not already typed (preserve annotation types)
        _existing_sym = ParserState.symbol_table.lookup(name)
        _existing_type = (_existing_sym.get("type") or "") if _existing_sym else ""
        if inferred is not None and not _existing_type:
            ParserState.symbol_table.add(name, inferred, "var")
        else:
            # If RHS is a call/subscript on a PyObject variable, the result
            # is also a PyObject (until proven otherwise by a type annotation).
            rhs_str = parts[-1] if len(parts) >= 2 else ""
            import re as _re_py
            base_m = _re_py.match(r"^([A-Za-z_]\w*)\b", rhs_str)
            if base_m:
                base = base_m.group(1)
                base_sym = ParserState.symbol_table.lookup(base)
                if base_sym:
                    bt = base_sym.get("type", "") or ""
                    if bt.startswith("_py_module:") or bt == "PyObject":
                        ParserState.symbol_table.add(name, "PyObject", "var")
    if prefix == "var " and len(parts) == 2 and parts[1] in ("@[]", "@{}", "initTable()"):
        import sys as _sys
        print(f"Error: '{lhs} = {parts[1]}' needs a type annotation (e.g. '{lhs}: Type = {parts[1]}')", file=_sys.stderr)
    # When re-assigning initHashSet()/initTable() to an existing variable, add type param
    if len(parts) == 2 and parts[1] == "initHashSet()":
        sym = ParserState.symbol_table.lookup(lhs)
        if sym:
            stype = sym.get("type") or ""
            import re as _re_hs
            m = _re_hs.match(r"HashSet\[(\w+)\]", stype)
            if m:
                parts[1] = f"initHashSet[{m.group(1)}]()"
    if len(parts) == 2 and parts[1] == "initTable()":
        sym = ParserState.symbol_table.lookup(lhs)
        if sym:
            stype = sym.get("type") or ""
            import re as _re_tb
            m = _re_tb.match(r"Table\[([^,]+),\s*([^\]]+)\]", stype)
            if m:
                parts[1] = f"initTable[{m.group(1)}, {m.group(2)}]()"
    # Option[T] assignment: if LHS is known Option[T] and RHS is not some()/none()/nil,
    # wrap RHS in some(...)
    if len(parts) == 2 and prefix == "":
        sym = ParserState.symbol_table.lookup(lhs)
        if sym:
            stype = sym.get("type") or ""
            if stype.startswith("Option["):
                rhs = parts[1]
                # Don't wrap regex match/find calls — post-process handles those
                _is_regex_call = bool(
                    __import__("re").search(r'\.(match|find)\(\w+\)', rhs)
                )
                if not _is_regex_call and rhs not in ("nil",) and not rhs.startswith("some(") and not rhs.startswith("none("):
                    import re as _re_opt2
                    _m = _re_opt2.search(r"Option\[(.+)\]", stype)
                    if _m:
                        parts[1] = f"some({rhs})"
                        ParserState.nim_imports.add("options")
    stmt = prefix + " = ".join(parts)
    # Float range constraint: append assert after assignment
    if len(parts) == 2 and not "," in lhs:
        sym = ParserState.symbol_table.lookup(lhs)
        if sym:
            stype = sym.get("type") or ""
            _fra = _float_range_assert(lhs, stype)
            if _fra:
                stmt = stmt + "\n" + _fra
    return stmt


# --- augmented assignment ---
@method(aug_assign_stmt)
def to_nim(self):
    """aug_assign_stmt: star_expressions augop expressions
    Translate augmented ops: //= -> expand to div, etc.
    """
    target = self.nodes[0].to_nim()
    op_node = self.nodes[1]
    py_op = (
        op_node.nodes[0]
        if isinstance(op_node.nodes[0], str)
        else op_node.nodes[0].nodes[0]
    )
    value = self.nodes[2].to_nim()
    nim_op, expand = _AUGOP_TO_NIM.get(py_op, (py_op, False))
    # String += -> &= in Nim
    if nim_op == "+=" and not expand:
        sym = ParserState.symbol_table.lookup(target)
        ttype = (sym.get("type") or "") if sym else ""
        if ttype in ("string", "str") or value.startswith('"') or value.startswith('fmt"'):
            nim_op = "&="
    # Ada-style &= -> string concat &= (not bitwise and=) when target is string
    if nim_op == "and" and expand and py_op == "&=":
        sym = ParserState.symbol_table.lookup(target)
        ttype = (sym.get("type") or "") if sym else ""
        if ttype in ("string", "str") or value.startswith('"') or value.startswith('fmt"'):
            expand = False
            nim_op = "&="
    if expand:
        stmt = f"{target} = {target} {nim_op} {value}"
    else:
        stmt = f"{target} {nim_op} {value}"
    # Float range constraint: append assert after augmented assignment
    sym = ParserState.symbol_table.lookup(target)
    if sym:
        stype = sym.get("type") or ""
        _fra = _float_range_assert(target, stype)
        if _fra:
            stmt = stmt + "\n" + _fra
    return stmt


def _coerce_scalar_value(value, annotation):
    """If annotation is a range subtype or enum and value is an int literal or
    int-valued expression, wrap with AnnotationType(value)."""
    import re as _re_sc
    _RANGE_SUBTYPES = ("Positive", "Natural", "range[")
    resolved = ParserState.symbol_table.resolve_type(annotation)
    is_range = any(resolved.startswith(r) for r in _RANGE_SUBTYPES)
    is_enum = resolved == 'enum' or (
        ParserState.symbol_table.lookup(annotation) or {}
    ).get('type', '').startswith('enum')
    if not (is_range or is_enum):
        return value
    # Already cast: T(...)
    if value.startswith(annotation + "("):
        return value
    # Integer literal
    if _re_sc.match(r'^\d+$', value):
        return f"{annotation}({value})"
    # Int-valued calls: len(...), sum(...), int(...), ord(...)
    if _re_sc.match(r'^(len|sum|int|ord)\s*\(', value):
        return f"{annotation}({value})"
    return value


def _coerce_tuple_literals(value, elem_type):
    """Given a Nim expression string and a tuple element type name, wrap integer
    literals in range-subtype fields with explicit casts.  Handles both
    positional anonymous tuples and named-field tuples (field: value syntax)."""
    import re as _re_ctl
    _RANGE_SUBTYPES = ("Positive", "Natural", "range[")
    _cft = getattr(ParserState, 'class_field_types', {})
    _fields = _cft.get(elem_type, {})  # {field_name: field_type_str} for named tuples

    if _fields:
        # Named tuple — cast by field name: replace `fieldname: <int>` patterns
        def _cast_named_field(m):
            fname, fval = m.group(1), m.group(2)
            ft = _fields.get(fname)
            if ft:
                resolved = ParserState.symbol_table.resolve_type(ft)
                if any(resolved.startswith(r) for r in _RANGE_SUBTYPES):
                    return f"{fname}: {ft}({fval})"
            return m.group(0)
        return _re_ctl.sub(r'\b(\w+):\s*(\d+)\b', _cast_named_field, value)
    else:
        # Anonymous tuple alias — cast by position
        _sym = ParserState.symbol_table.lookup(elem_type)
        if not (_sym and _sym.get('kind') == 'type'):
            return value
        _alias = _sym.get('type', '') or ''
        _am = _re_ctl.match(r'^\((.+)\)$', _alias.strip())
        if not _am:
            return value
        _parts = [p.strip() for p in _am.group(1).split(',')]
        _casts = {}
        for idx, ft in enumerate(_parts):
            resolved = ParserState.symbol_table.resolve_type(ft)
            if any(resolved.startswith(r) for r in _RANGE_SUBTYPES):
                _casts[idx] = ft
        if not _casts:
            return value
        def _cast_positional(m):
            inner = m.group(1)
            parts = [p.strip() for p in inner.split(",")]
            result_parts = []
            for i, part in enumerate(parts):
                if i in _casts and _re_ctl.match(r'^\d+$', part):
                    result_parts.append(f"{_casts[i]}({part})")
                else:
                    result_parts.append(part)
            return "(" + ", ".join(result_parts) + ")"
        return _re_ctl.sub(r"\(([^()]+)\)", _cast_positional, value)


def _coerce_table_seq_values(value, annotation):
    """Cast integer literals in tuple elements to range subtypes.
    Handles Table[K, seq[T]], Table[K, T], array[E, T], and type aliases thereof."""
    import re as _re_csv
    if ".toTable" not in value:
        return value

    def _resolve_annotation(ann):
        """Resolve type alias one level if needed; return the annotation string."""
        sym = ParserState.symbol_table.lookup(ann.strip())
        if sym and sym.get('kind') == 'type':
            return sym.get('type', ann) or ann
        return ann

    # Resolve top-level annotation if it's a plain name (e.g. Choice_T -> Table[...])
    _ann = annotation.strip()
    if _re_csv.match(r'^\w+$', _ann):
        _ann = _resolve_annotation(_ann)

    # If annotation is array[E, V], recurse on V
    _am = _re_csv.match(r'^array\[.+?,\s*(.+)\]$', _ann)
    if _am:
        _inner_ann = _am.group(1).strip()
        # Resolve the inner type alias too
        if _re_csv.match(r'^\w+$', _inner_ann):
            _inner_ann = _resolve_annotation(_inner_ann)
        # Apply coercion to each .toTable segment
        import re as _re2
        def _coerce_segment(m):
            return _coerce_table_seq_values(m.group(0), _inner_ann)
        return _re2.sub(r'\{[^{}]*\}\.toTable', _coerce_segment, value)

    # Find Table[K, V] and extract V
    _tm = _re_csv.match(r'^Table\[.+?,\s*(seq\[(\w+)\]|(\w+))\]$', _ann)
    if not _tm:
        return value
    _elem_type = _tm.group(2) or _tm.group(3)

    # Scalar V that is a range subtype: cast bare-int dict values explicitly
    # (Nim rejects implicit int -> Natural coercion in a typed Table literal).
    _RANGE_SUBTYPES = ("Positive", "Natural", "range[")
    _resolved = ParserState.symbol_table.resolve_type(_elem_type)
    if any(_resolved.startswith(r) for r in _RANGE_SUBTYPES):
        def _cast_scalar_segment(m):
            seg = m.group(0)
            # Wrap each `: <digits>` in `: <Type>(<digits>)`.
            return _re_csv.sub(
                r':\s*(\d+)\b',
                lambda mm: f": {_elem_type}({mm.group(1)})",
                seg,
            )
        return _re_csv.sub(r'\{[^{}]*\}\.toTable', _cast_scalar_segment, value)

    if value.endswith(".toTable"):
        return _coerce_tuple_literals(value, _elem_type)
    else:
        import re as _re2
        def _coerce_segment(m):
            return _coerce_tuple_literals(m.group(0), _elem_type)
        return _re2.sub(r'\{[^{}]*\}\.toTable', _coerce_segment, value)


def _unwrap_array_values_in_table(value, annotation):
    """For `Table[K, array[E, T]]` (or a type alias resolving to one) fix up
    each value literal:

      * Strip the ``@`` from ``@[...]`` (seq literal -> array literal).
      * If T is a range subtype (Natural, Positive, range[...]) cast bare
        integer elements with the subtype name so Nim's type-checker is
        happy: ``[2, 3]`` -> ``[Natural(2), Natural(3)]``.

    AdaScript's list literal always transpiles to a seq literal ``@[...]``
    regardless of the target type, and integer literals default to ``int``.
    This helper does the minimal textual surgery to make them compatible
    with a fixed-size array[E, RangeT] element type."""
    import re as _re_av
    if ".toTable" not in value:
        return value

    def _resolve_annotation(ann):
        sym = ParserState.symbol_table.lookup(ann.strip())
        if sym and sym.get('kind') == 'type':
            return sym.get('type', ann) or ann
        return ann

    _ann = annotation.strip()
    if _re_av.match(r'^\w+$', _ann):
        _ann = _resolve_annotation(_ann)

    # Need Table[K, array[...]] — resolve V if it's a type alias.
    _tm = _re_av.match(r'^Table\[.+?,\s*(.+)\]$', _ann)
    if not _tm:
        return value
    _vt = _tm.group(1).strip()
    if _re_av.match(r'^\w+$', _vt):
        _vt = _resolve_annotation(_vt)
    if not _vt.startswith("array["):
        return value

    # Extract the element type from array[E, T]
    _em = _re_av.match(r'^array\[.+?,\s*(.+)\]$', _vt)
    _elem_type = _em.group(1).strip() if _em else None
    _RANGE_SUBTYPES = ("Positive", "Natural", "range[")
    _cast_name = None
    if _elem_type:
        resolved = ParserState.symbol_table.resolve_type(_elem_type)
        if any(resolved.startswith(r) for r in _RANGE_SUBTYPES):
            _cast_name = _elem_type

    # Inside each {...}.toTable segment: strip @ and (optionally) cast ints.
    def _fix_segment(m):
        seg = m.group(0).replace(": @[", ": [")
        if _cast_name:
            # Cast bare integer literals inside array literals.
            # Match a `[...]` that follows a `: ` (ensures we're in a value slot).
            def _cast_arr(mm):
                inner = mm.group(1)
                parts = [p.strip() for p in inner.split(",")]
                casted = []
                for p in parts:
                    if _re_av.match(r'^\d+$', p):
                        casted.append(f"{_cast_name}({p})")
                    else:
                        casted.append(p)
                return ": [" + ", ".join(casted) + "]"
            seg = _re_av.sub(r': \[([^\[\]]+)\]', _cast_arr, seg)
        return seg
    return _re_av.sub(r'\{[^{}]*\}\.toTable', _fix_segment, value)


def _wrap_comprehension_for_array(value, annotation):
    """If annotation is `array[N, T]` (or an alias thereof) and value is a
    list/set/dict comprehension that transpiled to `collect(...)`, wrap it in
    a Nim `block:` that copies the collected seq into a fixed-size array.

    Nim's sugar.collect always produces seq[T], and seq[T] is not assignable
    to array[N, T]. Rather than push users into a pre-declared var + loop,
    we emit:

        block:
          let _adasq = collect(...)
          var _adaarr: array[N, T]
          for _adai in 0 ..< N: _adaarr[_adai] = _adasq[_adai]
          _adaarr

    so that `var a: State_T = [x for x in xs]` just works when
    `State_T = array[N, T]`.
    """
    import re as _re_arr
    # Resolve annotation through one level of type alias (matches other helpers)
    _ann = annotation
    _ann_sym = ParserState.symbol_table.lookup(_ann)
    if _ann_sym and _ann_sym.get("kind") == "type":
        _ann = _ann_sym.get("type", _ann) or _ann
    if not _ann.startswith("array["):
        return value
    # Match array[<size>, <elem type>]. <size> may be an identifier (compile-
    # time const) or a literal integer; either works as an array dimension.
    _m = _re_arr.match(r"array\[([^,]+),\s*(.+)\]$", _ann)
    if not _m:
        return value
    _size = _m.group(1).strip()
    # Value must be a fresh `collect(...)` expression (not something like
    # `foo(collect(...))` — the wrapper would change semantics).
    if not value.startswith("collect("):
        return value
    # Wrap the comprehension. Names are prefixed `ada` (no leading underscore
    # — Nim rejects identifiers starting with `_`).
    return (
        "(block:\n"
        f"    let adasq = {value}\n"
        f"    var adaarr: {_ann}\n"
        f"    for adai in 0 ..< {_size}: adaarr[adai] = adasq[adai]\n"
        "    adaarr)"
    )


def _specialize_init_table(value, annotation):
    """Replace bare initTable() in value with typed initTable[K,V]() using annotation context.

    Resolves type aliases. Handles both top-level and nested occurrences.
    """
    import re as _re_it
    # Resolve annotation through one level of type alias
    _ann = annotation
    _ann_sym = ParserState.symbol_table.lookup(_ann)
    if _ann_sym and _ann_sym.get("kind") == "type":
        _ann = _ann_sym.get("type", _ann) or _ann
    if "initTable()" not in value or "Table[" not in _ann:
        return value
    # Top-level: value IS initTable() and annotation is Table[K, V]
    if value == "initTable()":
        _m = _re_it.search(r"Table\[(.+)\]", _ann)
        if _m:
            return f"initTable[{_m.group(1)}]()"
    # Nested: bare initTable() inside a table literal — use value type of outer Table[K, V]
    # e.g. annotation=Table[Node_T, Table[X, Y]] -> replace initTable() with initTable[X, Y]()
    _m2 = _re_it.match(r"Table\[[^,]+,\s*(Table\[[^\]]+\])", _ann)
    if _m2:
        _inner_type = _m2.group(1)
        # Extract K, V from inner Table[K, V]
        _im = _re_it.match(r"Table\[(.+)\]", _inner_type)
        if _im:
            value = value.replace("initTable()", f"initTable[{_im.group(1)}]()")
    return value


# --- annotated assignment ---
@method(ann_assign_stmt)
def to_nim(self):
    """ann_assign_stmt: IDENTIFIER ':' type_annotation ('=' expression)?
    Python: x: int = 1  ->  Nim: var x: int = 1
    """
    name = self.nodes[0].to_nim()
    annotation = self.nodes[2].to_nim()
    # Record type in symbol table
    ParserState.symbol_table.add(name, annotation, "var")
    # Nim's implicit result variable: skip var and type inside typed procs
    _exp = "*" if getattr(ParserState, 'export_symbols', False) and ParserState.symbol_table.depth() == 1 else ""
    if name == "result" and getattr(ParserState, '_current_return_type', ''):
        kw = ""
        result = f"{name}"  # just 'result', no type annotation needed
    else:
        kw = "var "
        result = f"{kw}{name}{_exp}: {annotation}"
    for node in self.nodes[3:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_nim()
                # For array types, strip @ prefix from list literals
                if annotation.startswith("array[") and value.startswith("@["):
                    value = value[1:]
                # For array types with a comprehension RHS, wrap the collect()
                # into a block: that copies the collected seq into the array.
                value = _wrap_comprehension_for_array(value, annotation)
                # initTable() needs explicit type params (handles nested too)
                value = _specialize_init_table(value, annotation)
                # Table[K, seq[T]] with range fields: wrap seq values for coercion
                value = _coerce_table_seq_values(value, annotation)
                # Table[K, array[...]]: each @[...] value needs to become [...]
                value = _unwrap_array_values_in_table(value, annotation)
                # Range/enum scalar: wrap int literals and int-valued calls
                value = _coerce_scalar_value(value, annotation)
                # array types: {} is unnecessary — arrays are zero-initialized
                if value == "initTable()" and annotation.startswith("array["):
                    value = ""
                # initHashSet() sentinel: resolve to correct Nim set initialiser
                if value == "initHashSet()":
                    import re as _re2
                    if "HashSet[" in annotation:
                        _m = _re2.search(r"HashSet\[(.+)\]", annotation)
                        if _m:
                            value = f"initHashSet[{_m.group(1)}]()"
                        ParserState.nim_imports.add("sets")
                    elif annotation.startswith("set["):
                        value = "{}"  # built-in ordinal set empty literal
                    else:
                        ParserState.nim_imports.add("sets")
                        # bare fallback — no type params available
                # seq[T] = lo .. hi  ->  seq[T] = toSeq(lo .. hi)
                if annotation.startswith("seq[") and ".." in value and not value.startswith("toSeq("):
                    ParserState.nim_imports.add("sequtils")
                    value = f"toSeq({value})"
                # PyObject coercion: if annotation is a primitive Nim type
                # and we're in a nimpy context, append .to(T) so the compiler
                # can convert PyObject -> Nim type without an explicit cast.
                _COERCIBLE = {"int", "float", "string", "bool", "int64",
                               "int32", "uint", "uint32", "uint64", "float32",
                               "float64"}
                _is_coercible_type = (
                    annotation in _COERCIBLE
                    or annotation.startswith("seq[")
                )
                if (value
                        and _is_coercible_type
                        and "nimpy" in ParserState.nim_imports
                        and not value.endswith(f".to({annotation})")
                        and not value.lstrip("-").replace(".", "").isdigit()
                        and value not in ("true", "false", "nil", '""', "''")
                        and not value.startswith('"')
                        and not value.startswith("'")
                        and not value.startswith("@[")
                        and not value.startswith('fmt"')
                        and not value.startswith("fmt'")
                        and "if " not in value[:20]):
                    # Only wrap with .to(T) if the value originates from a PyObject.
                    # Check the leading identifier: if it's a pyImport module or PyObject var,
                    # or if the value is a dotted call on one, coerce. Otherwise skip.
                    import re as _re_co
                    _lead_m = _re_co.match(r'^[\(\s]*([A-Za-z_]\w*)', value)
                    _lead = _lead_m.group(1) if _lead_m else None
                    _lead_sym = ParserState.symbol_table.lookup(_lead) if _lead else None
                    _lead_type = (_lead_sym.get("type") or "") if _lead_sym else ""
                    _is_pyobj_base = bool(
                        _lead_type.startswith("_py_module:") or _lead_type == "PyObject"
                    )
                    if _is_pyobj_base:
                        value = f"{value}.to({annotation})"
                # Option[T] = None -> none(T)
                if value == "nil" and annotation.startswith("Option["):
                    import re as _re_opt
                    _m = _re_opt.search(r"Option\[(.+)\]", annotation)
                    if _m:
                        value = f"none({_m.group(1)})"
                        ParserState.nim_imports.add("options")
                if value:
                    result += f" = {value}"
    # Float range constraint: if annotation is a float range type and there's
    # a value, append an assert checking the assigned value is in range.
    _fra = _float_range_assert(name, annotation)
    if _fra and " = " in result:
        result = result + "\n" + _fra
    return result



# --- declaration with keyword (var/let/const) ---

@method(decl_ann_assign_stmt)
def to_nim(self):
    """decl_ann_assign_stmt: decl_keyword IDENTIFIER ':' type_annotation ('=' expression)?"""
    keyword = self.nodes[0].nodes[0]
    name = self.nodes[1].to_nim()
    annotation = self.nodes[3].to_nim()
    ParserState.symbol_table.add(name, annotation, keyword)
    _exp = "*" if getattr(ParserState, 'export_symbols', False) and ParserState.symbol_table.depth() == 1 else ""
    result = f"{keyword} {name}{_exp}: {annotation}"
    for node in self.nodes[4:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_nim()
                # For array types, strip @ prefix from list literals
                if annotation.startswith("array[") and value.startswith("@["):
                    value = value[1:]
                # For array types with a comprehension RHS, wrap the collect()
                # into a block: that copies the collected seq into the array.
                value = _wrap_comprehension_for_array(value, annotation)
                # initTable() needs explicit type params (handles nested too)
                value = _specialize_init_table(value, annotation)
                # Table[K, seq[T]] with range fields: wrap seq values for coercion
                value = _coerce_table_seq_values(value, annotation)
                # Table[K, array[...]]: each @[...] value needs to become [...]
                value = _unwrap_array_values_in_table(value, annotation)
                # Range/enum scalar: wrap int literals and int-valued calls
                value = _coerce_scalar_value(value, annotation)
                # array types: {} is unnecessary — arrays are zero-initialized
                if value == "initTable()" and annotation.startswith("array["):
                    value = ""
                # initHashSet() sentinel: resolve to correct Nim set initialiser
                if value == "initHashSet()":
                    import re as _re2
                    if "HashSet[" in annotation:
                        _m = _re2.search(r"HashSet\[(.+)\]", annotation)
                        if _m:
                            value = f"initHashSet[{_m.group(1)}]()"
                        ParserState.nim_imports.add("sets")
                    elif annotation.startswith("set["):
                        value = "{}"  # built-in ordinal set empty literal
                    else:
                        ParserState.nim_imports.add("sets")
                        # bare fallback — no type params available
                # seq[T] = lo .. hi  ->  seq[T] = toSeq(lo .. hi)
                if annotation.startswith("seq[") and ".." in value and not value.startswith("toSeq("):
                    ParserState.nim_imports.add("sequtils")
                    value = f"toSeq({value})"
                # PyObject coercion: if annotation is a primitive Nim type
                # and we're in a nimpy context, append .to(T) so the compiler
                # can convert PyObject -> Nim type without an explicit cast.
                _COERCIBLE = {"int", "float", "string", "bool", "int64",
                               "int32", "uint", "uint32", "uint64", "float32",
                               "float64"}
                _is_coercible_type = (
                    annotation in _COERCIBLE
                    or annotation.startswith("seq[")
                )
                if (value
                        and _is_coercible_type
                        and "nimpy" in ParserState.nim_imports
                        and not value.endswith(f".to({annotation})")
                        and not value.lstrip("-").replace(".", "").isdigit()
                        and value not in ("true", "false", "nil", '""', "''")
                        and not value.startswith('"')
                        and not value.startswith("'")
                        and not value.startswith("@[")
                        and not value.startswith('fmt"')
                        and not value.startswith("fmt'")
                        and "if " not in value[:20]):
                    # Only wrap with .to(T) if the value originates from a PyObject.
                    # Check the leading identifier: if it's a pyImport module or PyObject var,
                    # or if the value is a dotted call on one, coerce. Otherwise skip.
                    import re as _re_co
                    _lead_m = _re_co.match(r'^[\(\s]*([A-Za-z_]\w*)', value)
                    _lead = _lead_m.group(1) if _lead_m else None
                    _lead_sym = ParserState.symbol_table.lookup(_lead) if _lead else None
                    _lead_type = (_lead_sym.get("type") or "") if _lead_sym else ""
                    _is_pyobj_base = bool(
                        _lead_type.startswith("_py_module:") or _lead_type == "PyObject"
                    )
                    if _is_pyobj_base:
                        value = f"{value}.to({annotation})"
                # Option[T] = None -> none(T)
                if value == "nil" and annotation.startswith("Option["):
                    import re as _re_opt
                    _m = _re_opt.search(r"Option\[(.+)\]", annotation)
                    if _m:
                        value = f"none({_m.group(1)})"
                        ParserState.nim_imports.add("options")
                if value:
                    result += f" = {value}"
    # For record types with defaults and no explicit initializer, call init proc
    if "=" not in result:
        _rdt = getattr(ParserState, 'record_default_types', set())
        if annotation in _rdt:
            result += f" = init{annotation}()"
    # Downgrade `const` to `let` when the value is a runtime expression
    # (e.g. re(...) calls PCRE at runtime and cannot be a compile-time const).
    if keyword == "const" and result.startswith("const "):
        import re as _re_rt
        _val_part = result[result.find("=") + 1:].strip() if "=" in result else ""
        _RUNTIME_PREFIXES = ("re(", "re.compile(")
        if any(_val_part.startswith(p) for p in _RUNTIME_PREFIXES):
            result = "let" + result[5:]
    # Float range constraint: append assert if annotation is a float range type
    _fra = _float_range_assert(name, annotation)
    if _fra and " = " in result:
        result = result + "\n" + _fra
    return result

# --- return ---
@method(decl_tuple_unpack)
def to_nim(self):
    """decl_tuple_unpack: let/var/const (x, y) = expr -> Nim let/var (x, y) = expr"""
    kw = str(self.nodes[0].node)  # var/let/const
    targets = self.nodes[1].to_nim()  # paren_group
    value = self.nodes[3].to_nim()  # expression (nodes[2] is V_EQUAL)
    return f"{kw} {targets} = {value}"

@method(return_val)
def to_nim(self):
    """return_val: 'return' star_expressions -> Nim: 'return expr'; Option-typed returns wrapped in some()/none()"""
    val = self.nodes[0].to_nim()
    ret_type = getattr(ParserState, "_current_return_type", "")
    if ret_type and "Option[" in ret_type:
        import re as _re
        m = _re.search(r"Option\[(.+?)\]", ret_type)
        if m:
            inner_type = m.group(1)
            if val == "nil":
                return f"return none({inner_type})"
            else:
                return f"return some({val})"
    if val == "nil" and ret_type and "seq[" in ret_type:
        return "return @[]"
    if val == "initTable()" and ret_type:
        import re as _re2
        _tm = _re2.search(r"Table\[([^,\]]+),\s*([^\]]+)\]", ret_type)
        if _tm:
            val = f"initTable[{_tm.group(1)}, {_tm.group(2)}]()"
    if val == "initHashSet()" and ret_type:
        import re as _re3
        _hm = _re3.search(r"HashSet\[([^\]]+)\]", ret_type)
        if _hm:
            val = f"initHashSet[{_hm.group(1)}]()"
    # If return value contains commas (tuple), wrap in parens for Nim
    if "," in val and not val.startswith("("):
        val = f"({val})"
    return f"return {val}"


@method(return_bare)
def to_nim(self):
    """return_bare: 'return' (bare) -> Nim: 'return'"""
    return "return"


@method(return_stmt)
def to_nim(self):
    """return_stmt: return_val | return_bare"""
    return self.nodes[0].to_nim()


# --- pass / break / continue ---
@method(pass_stmt)
def to_nim(self):
    """pass_stmt: 'pass' -> Nim: 'discard'"""
    return "discard"


@method(break_stmt)
def to_nim(self):
    """break_stmt: 'break' -> Nim: 'break'"""
    return "break"


@method(continue_stmt)
def to_nim(self):
    """continue_stmt: 'continue' -> Nim: 'continue'"""
    return "continue"


# --- del ---
@method(del_stmt)
def to_nim(self):
    """del x -> reset(x)"""
    return f"reset({self.nodes[0].to_nim()})"


# --- assert ---
@method(assert_msg)
def to_nim(self):
    """assert_msg: 'assert' expression ',' expression -> Nim: 'assert cond, msg'"""
    return f"assert {self.nodes[0].to_nim()}, {self.nodes[1].to_nim()}"


@method(assert_simple)
def to_nim(self):
    """assert_simple: 'assert' expression -> Nim: 'assert cond'"""
    return f"assert {self.nodes[0].to_nim()}"


@method(assert_stmt)
def to_nim(self):
    """assert_stmt: assert_msg | assert_simple"""
    return self.nodes[0].to_nim()


# --- raise ---
@method(raise_from)
def to_nim(self):
    """raise X from Y -> raise X (Nim has no 'from' clause)"""
    return f"raise {self.nodes[0].to_nim()}"


_PY_EXCEPTIONS = {
    "NotImplementedError": "CatchableError",
    "ValueError": "ValueError",
    "RuntimeError": "CatchableError",
    "TypeError": "CatchableError",
    "IndexError": "IndexDefect",
    "KeyError": "KeyError",
    "Exception": "CatchableError",
}

@method(raise_exc)
def to_nim(self):
    """raise_exc: 'raise' expression -> Nim: 'raise newException(Type, msg)' for known Python exceptions"""
    import re as _re
    val = self.nodes[0].to_nim()
    # Translate Python exception constructors: raise XError("msg") -> raise newException(NimError, "msg")
    m = _re.match(r"(\w+)\((.*)\)$", val)
    if m and m.group(1) in _PY_EXCEPTIONS:
        nim_exc = _PY_EXCEPTIONS[m.group(1)]
        args = m.group(2)
        return f"raise newException({nim_exc}, {args})"
    return f"raise {val}"


@method(raise_bare)
def to_nim(self):
    """raise_bare: 'raise' (re-raise) -> Nim: 'raise'"""
    return "raise"


@method(raise_stmt)
def to_nim(self):
    """raise_stmt: raise_from | raise_exc | raise_bare"""
    return self.nodes[0].to_nim()


# --- global / nonlocal (no Nim equivalent — emit as comment) ---
@method(global_stmt)
def to_nim(self):
    """global_stmt: 'global' IDENTIFIER (',' IDENTIFIER)* -> Nim: emitted as '# global ...' comment (no Nim equivalent)"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_nim())
    return "# global " + ", ".join(parts)


@method(nonlocal_stmt)
def to_nim(self):
    """nonlocal_stmt: 'nonlocal' IDENTIFIER (',' IDENTIFIER)* -> Nim: emitted as '# nonlocal ...' comment"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_nim())
    return "# nonlocal " + ", ".join(parts)


# --- import ---
@method(dotted_name)
def to_nim(self):
    """dotted_name: IDENTIFIER ('.' IDENTIFIER)* -> Nim: joined with '.'"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                parts.append(seq.nodes[1].to_nim())
    return ".".join(parts)


@method(import_as)
def to_nim(self):
    """import_as: used only inside import_stmt (plain 'import X').
    Plain 'import' is reserved for 'from stdlib import X' style.
    All other imports must use 'nimport' (Nim modules) or 'pyimport' (Python packages).
    """
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if not hasattr(seq, "nodes"):
                continue
            if (len(seq.nodes) >= 2
                    and hasattr(seq.nodes[0], "nodes")
                    and seq.nodes[0].nodes
                    and seq.nodes[0].nodes[0] == "."):
                parts.append(seq.nodes[1].to_nim())
    module = ".".join(parts)
    import sys as _sys_imp
    print(f"Error: 'import {module}' is not allowed. "
          f"Use 'nimport {module}' for Nim/stdlib modules or "
          f"'pyimport {module}' for Python packages.", file=_sys_imp.stderr)
    return None


def _emit_pyimport(module, alias=None):
    """Emit a single pyImport() line and register the local symbol."""
    local = alias if alias else module.split(".")[-1]
    ParserState.nim_imports.add("nimpy")
    ParserState.symbol_table.add(local, f"_py_module:{module}", "let")
    return f'let {local} = pyImport("{module}")'


def _extract_module_alias(ia):
    """Extract (module_str, alias_str|None) from a single import_as parse node.

    import_as = dotted_name + (ikw("as") + IDENTIFIER)[:]
    dotted_name = IDENTIFIER + (V_DOT + IDENTIFIER)[:]

    Since '+' flattens Sequences, the import_as node has exactly 3 children:
      nodes[0] = IDENTIFIER   (first part of dotted name)
      nodes[1] = Several_Times(V_DOT + IDENTIFIER)  (remaining dotted parts)
      nodes[2] = Several_Times(IDENTIFIER)  (the alias after 'as', if present)
    """
    if not hasattr(ia, "nodes") or len(ia.nodes) < 1:
        return None, None
    # First identifier
    parts = [ia.nodes[0].to_nim() if hasattr(ia.nodes[0], "to_nim") else str(ia.nodes[0])]
    alias = None
    # nodes[1]: Several_Times — may contain (V_DOT + IDENTIFIER) parts and/or (IDENTIFIER) alias.
    # A sequence starting with '.' is a dotted-name part; one without is the 'as alias'.
    if len(ia.nodes) >= 2:
        dot_repeat = ia.nodes[1]
        if hasattr(dot_repeat, "nodes"):
            for seq in dot_repeat.nodes:
                if not hasattr(seq, "nodes") or not seq.nodes:
                    continue
                first_child = seq.nodes[0]
                first_val = (first_child.to_nim() if hasattr(first_child, "to_nim") else str(first_child))
                if first_val == ".":
                    # dotted name part: skip the dot, take the identifier
                    for child in seq.nodes[1:]:
                        v = child.to_nim() if hasattr(child, "to_nim") else str(child)
                        parts.append(v)
                else:
                    # alias (from 'as IDENTIFIER', ikw stripped the 'as')
                    alias = first_val
    # nodes[2]: Several_Times of (IDENTIFIER) — alias when dotted name was present
    if len(ia.nodes) >= 3:
        as_repeat = ia.nodes[2]
        if hasattr(as_repeat, "nodes") and as_repeat.nodes:
            seq = as_repeat.nodes[0]
            if hasattr(seq, "nodes") and seq.nodes:
                alias = seq.nodes[0].to_nim() if hasattr(seq.nodes[0], "to_nim") else str(seq.nodes[0])
    return ".".join(parts), alias


def _collect_import_as_nodes(self):
    """Walk the import_as children of a pyimport_stmt node, yielding (module, alias) pairs.

    pyimport_stmt = ikw("pyimport") + import_as + (COMMA + import_as)[:]
    ikw() is invisible, so the outer Sequence_Parser has one child node.

    For a single import (e.g. 'pyimport matplotlib.pyplot as plt'):
      self -> Sequence_Parser([import_as_node])
      import_as_node -> Sequence_Parser([IDENTIFIER, Several_Times(DOT+IDENT), Several_Times(IDENT)])

    For multiple imports (e.g. 'pyimport os, sys'):
      self -> Sequence_Parser([Sequence_Parser([ia1, Several_Times([COMMA, ia2, ...])])])
    """
    results = []

    def _is_import_as(node):
        """Heuristic: an import_as node has 2-3 children where nodes[0] is an IDENTIFIER."""
        if not hasattr(node, "nodes") or len(node.nodes) < 1:
            return False
        first = node.nodes[0]
        if not hasattr(first, "nodes") or len(first.nodes) != 1:
            return False
        return isinstance(first.nodes[0], str)

    def _collect_from(node):
        """Recursively collect import_as entries from a node tree."""
        if _is_import_as(node):
            module, alias = _extract_module_alias(node)
            if module:
                results.append((module, alias))
        elif hasattr(node, "nodes"):
            for child in node.nodes:
                _collect_from(child)

    _collect_from(self)
    return results


@method(pyimport_stmt)
def to_nim(self):
    """pyimport_stmt: 'pyimport' import_as (',' import_as)* -> Nim: pyImport() for each"""
    lines = []
    for module, alias in _collect_import_as_nodes(self):
        if module:
            lines.append(_emit_pyimport(module, alias))
    unique = list(dict.fromkeys(lines))
    return chr(10).join(unique)


@method(import_stmt)
def to_nim(self):
    """import_stmt: 'import' import_as (',' import_as)* -> Nim: mapped stdlib imports or pyImport()"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_nim())
    # Deduplicate identical import lines
    seen = set()
    unique = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    # Filter out None/erased imports (e.g., typing)
    unique = [p for p in unique if p is not None]
    return chr(10).join(unique)


# --- from ... import ---
@method(import_name)
def to_nim(self):
    """import_name: IDENTIFIER ('as' IDENTIFIER)? -> Nim: name or 'name as alias'"""
    name = self.nodes[0].to_nim()
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                alias = seq.nodes[0].to_nim()
                return f"{name} as {alias}"
    return name


@method(import_star)
def to_nim(self):
    """import_star: '*' (from x import *) -> Nim: '*'"""
    return "*"


@method(import_names_paren)
def to_nim(self):
    """import_names_paren: '(' import_names ')' -> Nim: parenthesised import list"""
    def _find_import_names(node):
        names = []
        if node is None:
            return names
        if type(node).__name__ == "import_name":
            names.append(node.to_nim())
        elif hasattr(node, "nodes") and node.nodes:
            for child in node.nodes:
                names.extend(_find_import_names(child))
        return names
    parts = _find_import_names(self)
    return "(" + ", ".join(parts) + ")"


@method(import_names)
def to_nim(self):
    """import_names: import_name (',' import_name)* | import_star -> Nim: Nim import names"""
    first = self.nodes[0].to_nim()
    if first == "*":
        return "*"
    parts = [first]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_nim())
    return ", ".join(parts)


def _dots_to_nim(nodes):
    dots = ""
    for node in nodes:
        if hasattr(node, "nodes"):
            for sub in node.nodes:
                if hasattr(sub, "nodes") and sub.nodes and sub.nodes[0] == ".":
                    dots += "."
    return dots


def _import_names_to_nim(node):
    """Parallel to _import_names_to_py but calls to_nim()."""
    if not hasattr(node, "nodes"):
        return str(node)
    if type(node).__name__ == "import_names_paren":
        return node.to_nim()
    first = node.nodes[0]
    if first == "*" or (
        hasattr(first, "nodes") and first.nodes and first.nodes[0] == "*"
    ):
        return "*"
    first_name_nodes = [first]
    parts = []
    for nd in node.nodes[1:]:
        if type(nd).__name__ == "Several_Times" and nd.nodes:
            for seq in nd.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    child = seq.nodes[0]
                    if type(child).__name__ == "import_name":
                        if not parts:
                            parts.append(_import_name_to_nim(first_name_nodes))
                        parts.append(child.to_nim())
                    elif type(child).__name__ == "IDENTIFIER":
                        first_name_nodes.append(nd)
                        break
                    else:
                        first_name_nodes.append(nd)
                        break
        else:
            first_name_nodes.append(nd)
    if not parts:
        parts.append(_import_name_to_nim(first_name_nodes))
    return ", ".join(parts)


def _import_name_to_nim(nodes):
    name = nodes[0].to_nim()
    for nd in nodes[1:]:
        if type(nd).__name__ == "Several_Times" and nd.nodes:
            seq = nd.nodes[0]
            if hasattr(seq, "nodes") and seq.nodes:
                child = seq.nodes[0]
                if type(child).__name__ == "IDENTIFIER":
                    name += f" as {child.to_nim()}"
    return name


@method(from_rel_name)
def to_nim(self):
    """from_rel_name: relative 'from' import with leading dots (e.g. 'from ..pkg import x') -> Nim: pyImport or mapped stdlib"""
    dots = ""
    remaining = []
    for node in self.nodes:
        if type(node).__name__ == "Several_Times":
            for sub in node.nodes:
                if hasattr(sub, "nodes") and sub.nodes and sub.nodes[0] == ".":
                    dots += "."
                else:
                    remaining.append(sub)
        else:
            remaining.append(node)
    source = remaining[0].to_nim() if remaining else ""
    module = dots + source
    names_str = (
        _import_names_to_nim(remaining[-1])
        if len(remaining) > 1
        else remaining[0].to_nim()
        if remaining
        else ""
    )
    if names_str == "*":
        return f"from {module} import *"
    raw = names_str.strip("()")
    items = [n.strip() for n in raw.split(",")]
    lines = []
    for item in items:
        if " as " in item:
            orig, alias = item.split(" as ", 1)
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {alias.strip()} = pyImport("{module}").{orig.strip()}')
        else:
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {item} = pyImport("{module}").{item}')
    return chr(10).join(lines)


@method(from_rel_bare)
def to_nim(self):
    """from_rel_bare: bare relative import ('from . import x') -> Nim: pyImport('.').x or stdlib import"""
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
    names_str = _import_names_to_nim(names_node) if names_node else ""
    module = dots
    if names_str == "*":
        return f"from {module} import *"
    raw = names_str.strip("()")
    items = [n.strip() for n in raw.split(",")]
    lines = []
    for item in items:
        if " as " in item:
            orig, alias = item.split(" as ", 1)
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {alias.strip()} = pyImport("{module}").{orig.strip()}')
        else:
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {item} = pyImport("{module}").{item}')
    return chr(10).join(lines)


@method(from_abs)
def to_nim(self):
    """from_abs: absolute 'from module import names' -> Nim: mapped stdlib or pyImport("module").name"""
    source_parts = [self.nodes[0].to_nim()]
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
                    source_parts.append(seq.nodes[1].to_nim())
                    names_start = i + 1
                    continue
        break
    module = ".".join(source_parts)
    if names_start < len(self.nodes):
        names_node = self.nodes[names_start]
        if names_start + 1 < len(self.nodes):
            class _Mock:
                pass
            mock = _Mock()
            mock.nodes = self.nodes[names_start:]
            names_str = _import_names_to_nim(mock)
        else:
            names_str = _import_names_to_nim(names_node)
    else:
        names_str = ""
    # Handle star import
    if names_str == "*":
        return f"from {module} import *"
    # Check if module has a known Nim equivalent
    nim_module = _PY_MODULE_TO_NIM.get(module)
    if nim_module is not None:
        # Always just add to nim_imports — Nim doesn't have 'from X import Y'
        # syntax for stdlib modules; everything comes in via 'import X'.
        if nim_module:
            ParserState.nim_imports.add(nim_module)
        return None  # handled via nim_imports
    # Split names and generate one let per name
    # names_str may be "X", "X, Y", "(X, Y)", or "X as A"
    raw = names_str.strip("()")
    items = [n.strip() for n in raw.split(",")]
    lines = []
    for item in items:
        if " as " in item:
            orig, alias = item.split(" as ", 1)
            orig = orig.strip()
            alias = alias.strip()
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {alias} = pyImport("{module}").{orig}')
        else:
            ParserState.nim_imports.add("nimpy")
            lines.append(f'let {item} = pyImport("{module}").{item}')
    return chr(10).join(lines)


@method(from_stmt)
def to_nim(self):
    """from_stmt: from_rel_name | from_rel_bare | from_abs"""
    return self.nodes[0].to_nim()


# --- type alias ---
@method(enum_def)
def to_nim(self):
    """enum_def: 'enum' enum_member (',' enum_member)*"""
    raw = str(self.nodes[0].node)
    parts = [f"v{raw}" if raw.isdigit() else raw]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes') and len(seq.nodes) >= 1:
                m = str(seq.nodes[0].node)
                parts.append(f"v{m}" if m.isdigit() else m)
    return "enum " + ", ".join(parts)


@method(subrange_def)
def to_nim(self):
    """subrange_def: INTEGER ('..' | '..<') INTEGER -> Nim range[lo..hi] or range[lo..<hi]"""
    lo = str(self.nodes[0].node)
    hi = str(self.nodes[2].node)
    is_exclusive = getattr(self.nodes[1], 'node', None) == "..<"
    if is_exclusive:
        # Nim range[] doesn't support ..<; convert to inclusive by subtracting 1
        try:
            hi = str(int(hi) - 1)
        except ValueError:
            hi = f"({hi}) - 1"
    return f"range[{lo}..{hi}]"



@method(constrained_subrange_def)
def to_nim(self):
    """constrained_subrange_def: IDENTIFIER subrange_def -> Nim range[lo..hi]"""
    return self.nodes[1].to_nim()


@method(float_range_def)
def to_nim(self):
    """float_range_def: 'float' 'range' NUMBER ('..'|'..<') NUMBER -> lo..hi as strings"""
    lo = str(self.nodes[2].node)  # nodes[0]=float, nodes[1]=range, nodes[2]=NUMBER
    hi = str(self.nodes[4].node)  # nodes[3]=RANGE_OP, nodes[4]=NUMBER
    return f"{lo}..{hi}"  # sentinel used by type_stmt to generate float type alias


@method(int_range_def)
def to_nim(self):
    """int_range_def: 'int' 'range' subrange_def -> delegates to subrange_def"""
    return self.nodes[2].to_nim()  # nodes[0]=int, nodes[1]=range, nodes[2]=subrange_def


@method(from_nim_abs)
def to_nim(self):
    """from_nim_abs: 'from' dotted_name 'nimport' import_names -> Nim: import module"""
    module = self.nodes[0].to_nim()
    nim_mod = _NIMPORT_NAME_MAP.get(module, module)
    ParserState.nim_imports.add(nim_mod)
    # Selective names (from X nimport Y) or star (from X nimport *) both just add the import.
    # Individual names become directly accessible after `import nim_mod`.
    return None


@method(from_pyimport)
def to_nim(self):
    """from_pyimport: 'from' dotted_name 'pyimport' import_names -> let X = pyImport("mod").X"""
    module = self.nodes[0].to_nim()
    names_node = self.nodes[1] if len(self.nodes) > 1 else None
    names_str = _import_names_to_nim(names_node) if names_node else ""
    if names_str == "*":
        return _emit_pyimport(module)
    raw = names_str.strip("()")
    items = [n.strip() for n in raw.split(",") if n.strip()]
    lines = []
    for item in items:
        if " as " in item:
            orig, alias = item.split(" as ", 1)
            orig, alias = orig.strip(), alias.strip()
        else:
            orig = alias = item
        ParserState.nim_imports.add("nimpy")
        ParserState.symbol_table.add(alias, "PyObject", "let")
        lines.append(f'let {alias} = pyImport("{module}").{orig}')
    return "\n".join(lines) if lines else None


@method(nimport_stmt)
def to_nim(self):
    """nimport_stmt: 'nimport' dotted_name (',' dotted_name)* -> Nim import"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes'):
                for child in seq.nodes:
                    cname = type(child).__name__
                    if cname == "dotted_name":
                        parts.append(child.to_nim())
    lines = []
    for part in parts:
        if part == "re":
            # 're' uses the Python API via nimpy — register as a py_module
            # so re.search/findall/compile etc. pass through as PyObject calls
            lines.append(_emit_pyimport("re"))
        else:
            nim_mod = _NIMPORT_NAME_MAP.get(part, part)
            ParserState.nim_imports.add(nim_mod)
            # Register `part` as a nim_module alias so `part.func(args)` -> `func(args)`
            ParserState.symbol_table.add(part, f"_nim_module:{part}", "let")
    return chr(10).join(lines) if lines else None


@method(type_alias_params)
def to_nim(self):
    """type_alias_params: '[' IDENTIFIER (',' IDENTIFIER)* ']' (generic type parameters) -> Nim: [T, U, ...]"""
    parts = [self.nodes[0].to_nim()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                parts.append(seq.nodes[0].to_nim())
    return f"[{', '.join(parts)}]"


@method(type_stmt)
def to_nim(self, indent=0):
    """type_stmt: 'type' IDENTIFIER type_alias_params? '=' expression"""
    name = self.nodes[0].to_nim()
    params = ""
    eq_idx = 1
    for i, node in enumerate(self.nodes[1:], 1):
        if type(node).__name__ == "type_alias_params":
            params = node.to_nim()
            eq_idx = i + 1
            break
        elif hasattr(node, "nodes") and node.nodes:
            first = node.nodes[0] if hasattr(node, "nodes") else node
            if type(first).__name__ == "type_alias_params":
                params = first.to_nim()
                eq_idx = i + 1
                break
    # RHS is the last node — works whether V_EQUAL is present ('=') or absent ('is')
    rhs = self.nodes[-1]
    rhs_type = type(rhs).__name__
    if rhs_type == "enum_def":
        ParserState.symbol_table.add(name, "enum", "type")
        # Register First/Last for tick attributes
        # Extract members: first node is first member, rest are in Several_Times groups
        raw0 = str(rhs.nodes[0].node)
        members = [f"v{raw0}" if raw0.isdigit() else raw0]
        for node in rhs.nodes[1:]:
            if hasattr(node, "nodes") and node.nodes:
                for seq in node.nodes:
                    if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                        m = str(seq.nodes[0].node)
                        members.append(f"v{m}" if m.isdigit() else m)
        if members:
            ParserState.tick_types[name] = {"First": members[0], "Last": members[-1], "members": members}
            # Register each member in the symbol table so set literals like
            # {member1, member2} can infer the ordinal element type.
            for m in members:
                ParserState.symbol_table.add(m, name, "let")
    elif rhs_type == "subrange_def":
        lo = str(rhs.nodes[0].node)
        hi = str(rhs.nodes[2].node)  # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
    elif rhs_type == "constrained_subrange_def":
        sr = rhs.nodes[1]  # the subrange_def inside
        lo = str(sr.nodes[0].node)
        hi = str(sr.nodes[2].node)   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
    elif rhs_type == "int_range_def":
        sr = rhs.nodes[2]  # the subrange_def inside (nodes[0]=int, nodes[1]=range)
        lo = str(sr.nodes[0].node)
        hi = str(sr.nodes[2].node)   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
    elif rhs_type == "float_range_def":
        lo = str(rhs.nodes[2].node)
        hi = str(rhs.nodes[4].node)  # [float, range, lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi, "is_float_range": True}
        ParserState.symbol_table.add(name, "float", "type")
        _exp = "*" if getattr(ParserState, 'export_symbols', False) and ParserState.symbol_table.depth() == 1 else ""
        return f"{_ind(indent)}type {name}{_exp}{params} = float"
    value = rhs.to_nim()
    # Record type alias so method translation can resolve it
    if rhs_type not in ("enum_def",):
        ParserState.symbol_table.add(name, value, "type")
    _exp = "*" if getattr(ParserState, 'export_symbols', False) and ParserState.symbol_table.depth() == 1 else ""
    return f"{_ind(indent)}type {name}{_exp}{params} = {value}"


# --- simple_stmt ---
@method(print_stmt)
def to_nim(self):
    """print_stmt: 'print' star_expressions -> Nim: echo star_expressions

    Adascript bare print statement. In Nim output, 'print x' becomes 'echo x'.
    Multiple comma-separated arguments are passed directly to echo.
    """
    return f"echo({self.nodes[0].to_nim()})"


# --- simple_stmt ---
@method(simple_stmt)
def to_nim(self):
    """simple_stmt: assign_stmt | aug_assign_stmt | ann_assign_stmt | decl_* | return_stmt | del_stmt | assert_stmt | raise_stmt | pass_stmt | break_stmt | continue_stmt | import_stmt | from_stmt | type_alias_stmt | expr_stmt"""
    return self.nodes[0].to_nim()


# --- stmt_line ---
@method(stmt_line)
def to_nim(self):
    """stmt_line: simple_stmt NL -> Nim: simple statement line"""
    from hek_tokenize import RichNL

    parts = [self.nodes[0].to_nim()]
    newline_node = None

    for node in self.nodes[1:]:
        if hasattr(node, "nodes") and node.nodes:
            inner = node.nodes[0] if len(node.nodes) == 1 else None
            if inner is not None and isinstance(inner, RichNL):
                newline_node = inner
                continue
            for seq in node.nodes:
                if hasattr(seq, "nodes") and len(seq.nodes) >= 1:
                    parts.append(seq.nodes[0].to_nim())
        elif isinstance(node, RichNL):
            newline_node = node

    result = "; ".join(parts)
    # PyObject method call used as a statement must be discarded in Nim.
    # Detect: single expression that is a dotted call on a known _py_module symbol.
    # Skip discard when inside a function that returns a non-void type — the
    # expression may be the implicit return value.
    _ret = getattr(ParserState, '_current_return_type', '')
    _in_returning_func = bool(_ret and _ret not in (': void', ': None', ': unit'))
    if len(parts) == 1 and "nimpy" in ParserState.nim_imports and not _in_returning_func:
        import re as _re_pyc
        _pyc_m = _re_pyc.match(r'^([A-Za-z_]\w*)\.', result)
        if _pyc_m:
            _root = _pyc_m.group(1)
            _sym = ParserState.symbol_table.lookup(_root)
            if _sym and str(_sym.get("type", "")).startswith("_py_module:"):
                result = f"discard {result}"
    # Bare print (no args) -> echo "" (empty line)
    if result == "echo":
        result = 'echo ""'
    # Convert bare string literals (docstrings) to Nim doc comments
    if len(parts) == 1:
        r = parts[0]
        if r and len(r) >= 2 and r[0] == r[-1] and r[0] in ('"', "'"):
            result = '## ' + r[1:-1]
    if newline_node is not None and hasattr(newline_node, "comments") and newline_node.comments:
        for kind, text, ind in newline_node.comments:
            if kind == "comment":
                result += "  " + text
    return result




###############################################################################
# Tests
###############################################################################

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("Python -> Nim Statement Translation Tests")
    print("=" * 60)

    nim_tests = [
        # --- Assignment ---
        ("x = 1", "var x = 1"),
        ("a = b = 1", "var a = b = 1"),
        ("a, b = 1, 2", "let (a, b) = 1, 2"),
        # --- Augmented assignment (same in Nim) ---
        ("x += 1", "x += 1"),
        ("x -= 1", "x -= 1"),
        ("x *= 2", "x *= 2"),
        ("x /= 2", "x /= 2"),
        # --- Augmented assignment (expanded in Nim) ---
        ("x //= 2", "x = x div 2"),
        ("x %= 3", "x = x mod 3"),
        ("x **= 2", "x = x ^ 2"),
        ("x @= m", "x = x @ m"),
        ("x <<= 1", "x = x shl 1"),
        ("x >>= 1", "x = x shr 1"),
        ("x &= mask", "x = x and mask"),
        ("x |= flag", "x = x or flag"),
        ("x ^= bits", "x = x xor bits"),
        # --- Annotated assignment ---
        ("x: int", "var x: int"),
        ("x: int = 1", "var x: int = 1"),
        ("x: str = 'hello'", 'var x: string = "hello"'),
        # --- Declaration with keyword ---
        ("var x : int", "var x: int"),
        ("let y : int = 8", "let y: int = 8"),
        ("const z : int = 44", "const z: int = 44"),
        # --- return ---
        ("return", "return"),
        ("return x", "return x"),
        ("return x, y", "return (x, y)"),
        # --- pass -> discard ---
        ("pass", "discard"),
        # --- break / continue (same) ---
        ("break", "break"),
        ("continue", "continue"),
        # --- del -> reset() ---
        ("del x", "reset(x)"),
        # --- assert (same) ---
        ("assert x", "assert x"),
        ("assert x, 'msg'", 'assert x, "msg"'),
        # --- raise ---
        ("raise", "raise"),
        ("raise ValueError", "raise ValueError"),
        ("raise ValueError from exc", "raise ValueError"),  # no 'from' in Nim
        # --- global / nonlocal -> comments ---
        ("global x", "# global x"),
        ("global x, y", "# global x, y"),
        ("nonlocal x", "# nonlocal x"),
        ("nonlocal a, b, c", "# nonlocal a, b, c"),
        # --- import (adds to nim_imports set, emits "") ---
        ("import os", ""),
        ("import os.path", ""),
        ("import os as o", ""),
        ("import os, sys", ""),
        # --- from import ---
        ("from os import path", None),
        ("from os import path as p", None),
        ("from os import path, getcwd", None),
        ("from os import *", "from os import *"),
        # --- type alias ---
        ("type Vector = list", "type Vector = seq"),
        ("type Color = enum RED, BLUE, YELLOW", "type Color = enum RED, BLUE, YELLOW"),
        # --- expression statement (delegates to expr to_nim) ---
        ("f(x)", "f(x)"),
        ("1 + 2", "1 + 2"),
    ]

    nim_passed = nim_failed = 0
    for code, expected in nim_tests:
        try:
            result = parse_stmt(code)
            if result:
                output = result.to_nim()
                if output == expected:
                    print(f"  PASS: {code!r} -> {output!r}")
                    nim_passed += 1
                else:
                    print(f"  MISMATCH: {code!r}")
                    print(f"    expected: {expected!r}")
                    print(f"    got:      {output!r}")
                    nim_failed += 1
            elif expected is None:
                # None output is valid for statements that only update nim_imports
                print(f"  PASS: {code!r} -> None (deferred import)")
                nim_passed += 1
            else:
                print(f"  FAIL: {code!r} -> parse returned None")
                nim_failed += 1
        except Exception as e:
            print(f"  ERROR: {code!r} -> {e}")
            import traceback
            traceback.print_exc()
            nim_failed += 1

    print("=" * 60)
    print(f"Results: {nim_passed} passed, {nim_failed} failed")
    print()

