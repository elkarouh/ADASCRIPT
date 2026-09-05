#!/usr/bin/env python3
"""Python 3.14 Simple Statement Parser using hek_parsec combinator framework.

Builds on hek_py3_expr.py (expression grammar) to parse simple (non-compound)
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

Usage:
    ast = parse_stmt("x = 1")
    print(ast.to_py())  # x = 1
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))

from py3stmt import *
from hek_py3_expr import _get_bracket_start
import hek_py_declarations  # noqa: F401 — registers decl to_py() methods
from hek_parsec import method, ParserState
from hek_helpers import _ind

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


@method(V_COLON)
def to_py(self):
    """V_COLON: ':'"""
    return ":"


@method(V_DOT)
def to_py(self):
    """V_DOT: '.'"""
    return "."


# --- assignment ---
@method(assign_stmt)
def to_py(self):
    """assign_stmt: star_expressions ('=' star_expressions)+"""
    # nodes: [target1, Several_Times[(=, target2), (=, target3), ...]]
    # The last (=, expr) pair is the value; everything before is a target.
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                parts.append(seq.nodes[1].to_py())
    return " = ".join(parts)


# --- augmented assignment ---
@method(aug_assign_stmt)
def to_py(self):
    """aug_assign_stmt: star_expressions augop expressions"""
    target = self.nodes[0].to_py()
    # augop is an Fmap whose nodes[0] is a plain string like '+='
    op_node = self.nodes[1]
    op = (
        op_node.nodes[0]
        if isinstance(op_node.nodes[0], str)
        else op_node.nodes[0].to_py()
    )
    value = self.nodes[2].to_py()
    return f"{target} {op} {value}"


# --- annotated assignment ---
@method(ann_assign_stmt)
def to_py(self):
    """ann_assign_stmt: IDENTIFIER ':' expression ('=' expression)?"""
    name = self.nodes[0].to_py()
    # nodes[1] is V_COLON, nodes[2] is the type annotation
    annotation = self.nodes[2].to_py()
    result = f"{name}: {annotation}"
    # Check for optional '= value' part
    has_value = False
    for node in self.nodes[3:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_py()
                result += f" = {value}"
                has_value = True
    # Deliberately not zero-initialised here, unlike the `var x: T` form:
    # `x: int` with no value is also ordinary Python, which py2py round-trips
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


def _zero_value(annotation):
    """The empty value for ANNOTATION, mirroring Nim's zero-initialisation.

    A bare `x: T` binds nothing in Python, so a declaration written without an
    initialiser -- valid Adascript, since Nim zero-initialises it -- would
    raise on first use.  There is no honest zero for a class or an optional,
    so those become None.
    """
    ann = (annotation or "").strip()
    scalars = {"int": "0", "float": "0.0", "bool": "False", "str": '""',
               "bytes": 'b""', "complex": "0j"}
    if ann in scalars:
        return scalars[ann]
    for prefix, empty in (("list[", "[]"), ("dict[", "{}"), ("set[", "set()"),
                          ("frozenset[", "frozenset()"), ("tuple[", "()"),
                          ("Counter[", "Counter()")):
        if ann.startswith(prefix):
            return empty
    if ann.startswith("Sequence["):
        return "[]"
    return "None"


@method(decl_ann_assign_stmt)
def to_py(self):
    """decl_ann_assign_stmt: decl_keyword IDENTIFIER ':' type_annotation ('=' expression)?"""
    # nodes[0] is decl_keyword (dropped), nodes[1] is name, nodes[2] is V_COLON, nodes[3] is type
    from hek_parsec import ParserState
    name = self.nodes[1].to_py()
    annotation = self.nodes[3].to_py()
    keyword = self.nodes[0].nodes[0] if hasattr(self.nodes[0], "nodes") else ""
    ParserState.symbol_table.add(name, annotation, keyword or "var")
    result = f"{name}: {annotation}"
    has_value = False
    for node in self.nodes[4:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                value = seq.nodes[1].to_py()
                result += f" = {value}"
                has_value = True
    if not has_value:
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
    """return_val: 'return' expressions"""
    return f"return {self.nodes[0].to_py()}"


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


def _dots_to_py(nodes):
    """Extract leading dots from Several_Times of V_DOT nodes."""
    dots = ""
    for node in nodes:
        if hasattr(node, "nodes"):
            for sub in node.nodes:
                if hasattr(sub, "nodes") and sub.nodes and sub.nodes[0] == ".":
                    dots += "."
    return dots


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


@method(from_abs)
def to_py(self):
    """from_abs: 'from' dotted_name 'import' import_names"""
    source, names = _from_import_parts(self)
    return f"from {source} import {names}"


@method(from_pyimport)
def to_py(self):
    """from_pyimport: 'from' dotted_name 'pyimport' import_names

    Python-only import — emit it as an ordinary from-import."""
    source, names = _from_import_parts(self)
    return f"from {source} import {names}"


@method(from_nim_abs)
def to_py(self):
    """from_nim_abs: 'from' dotted_name 'nimport' import_names

    Nim-only import, so it is commented out in Python output — the same
    treatment `nimport_stmt` gets."""
    source, names = _from_import_parts(self)
    return f"# from {source} nimport {names}"


@method(from_stmt)
def to_py(self):
    """from_stmt: from_rel_name | from_rel_bare | from_abs"""
    return self.nodes[0].to_py()


# --- type alias ---
@method(enum_def)
def to_py(self):
    """enum_def: 'enum' enum_member (',' enum_member)* ','?"""
    parts = [str(self.nodes[0].node)]
    for node in self.nodes[1:]:
        if not hasattr(node, 'nodes') or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, 'nodes') and len(seq.nodes) >= 1:
                parts.append(str(seq.nodes[0].node))
    return "enum " + ", ".join(parts)


def _emit_enum_py(name, member_names, indent=0):
    """Emit a Python Enum class body for a type name and its members.

    Shared by the inline 'type T is enum A, B' form (type_stmt) and the
    indented 'type T is enum:' block form (type_block_stmt)."""
    ParserState.nim_imports.add("from enum import Enum")
    ParserState.tick_types[name] = {"First": member_names[0], "Last": member_names[-1], "members": member_names}
    lines = [f"{_ind(indent)}class {name}(Enum):"]
    py_members = []
    for i, m in enumerate(member_names):
        py_m = f"_{m}" if m.isdigit() else m
        lines.append(f"{_ind(indent + 1)}{py_m} = {i}")
        py_members.append((m, py_m))
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


@method(subrange_def)
def to_py(self):
    """subrange_def: INTEGER ('..' | '..<') INTEGER -> Python range()"""
    lo = str(self.nodes[0].node)
    hi = str(self.nodes[2].node)
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
def to_py(self):
    """type_stmt: 'type' IDENTIFIER type_alias_params? '=' (enum_def | expression)"""
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
    if rhs_type == 'float_range_def':
        lo = str(rhs.nodes[2].node)
        hi = str(rhs.nodes[4].node)  # [float, range, lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi, "is_float_range": True}
        return f"{name} = float  # range {lo} .. {hi}"
    if rhs_type == 'int_range_def':
        sr = rhs.nodes[2]  # the subrange_def inside (nodes[0]=int, nodes[1]=range)
        lo = str(sr.nodes[0].node)
        hi = str(sr.nodes[2].node)   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        return f"{name} = {rhs.to_py()}"
    if rhs_type == 'constrained_subrange_def':
        sr = rhs.nodes[1]  # the subrange_def inside
        lo = str(sr.nodes[0].node)
        hi = str(sr.nodes[2].node)   # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        return f"{name} = {rhs.to_py()}"
    if rhs_type == 'subrange_def':
        # Register First/Last for tick attributes (Name'First, Name'Last)
        lo = rhs.nodes[0].node
        hi = rhs.nodes[2].node  # [lo, range_op, hi]
        ParserState.tick_types[name] = {"First": lo, "Last": hi}
        return f"{name} = {rhs.to_py()}"
    if rhs_type == 'enum_def':
        members = rhs.to_py()
        member_names = [m.strip() for m in members[len("enum "):].split(",")]
        return _emit_enum_py(name, member_names)
    value = rhs.to_py()
    return f"{name} = {value}"



# --- simple_stmt ---
@method(subst_stmt)
def to_py(self):
    """subst_stmt: primary '=' s/pat/repl/flags -> Python: lhs = re.sub(r'pat', 'repl', lhs, flags=...)"""
    import re as _re_s
    from hek_py3_expr import _ensure_pymatch_helper, _py_re_flags
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


@method(print_stmt)
def to_py(self):
    """print_stmt: 'print' star_expressions -> Python: print(star_expressions)

    Adascript allows Python-2-style bare print statements without parentheses.
    The transpiler rewrites them as print() calls so the output is valid
    Python 3.
    """
    return f"print({self.nodes[0].to_py()})"


# --- simple_stmt ---
@method(simple_stmt)
def to_py(self):
    """simple_stmt: ann_assign_stmt | aug_assign_stmt | assign_stmt
    | return_stmt | pass_stmt | break_stmt | continue_stmt
    | del_stmt | assert_stmt | raise_stmt
    | global_stmt | nonlocal_stmt
    | import_stmt | from_stmt | type_stmt | expr_stmt"""
    return self.nodes[0].to_py()


# --- stmt_line ---
@method(stmt_line)
def to_py(self):
    """stmt_line: simple_stmt (';' simple_stmt)* ';'? NEWLINE"""
    from hek_tokenize import RichNL

    parts = [self.nodes[0].to_py()]
    newline_node = None

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
        result = "return " + result
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

