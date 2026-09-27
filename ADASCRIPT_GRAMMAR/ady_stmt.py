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

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "HPARSEC"))

import tokenize as tkn

from hek_parsec import (
    COLON,
    COMMA,
    DOT,
    EQUAL,
    IDENTIFIER,
    INTEGER,
    LBRACE,
    LBRACKET,
    LPAREN,
    NUMBER,
    RBRACE,
    RBRACKET,
    RPAREN,
    SEMICOLON,
    SSTAR,
    STRING,
    RANGE_OP,
    RANGE_EXCL_OP,
    SUBST,
    Input,
    Parser,
    ParserState,
    expect,
    expect_type,
    expect_type_node,
    expect_nl_or_richnl,
    filt,
    fmap,
    fw,
    ignore,
    literal,
    method,
    nothing,
    shift,
)
from ady_expr import *  # noqa: F403 — need all fw() names in namespace
from ady_declarations import type_annotation, elem_type

###############################################################################
# Tokens not in hek_parsec
###############################################################################

NEWLINE = expect_type_node(tkn.NEWLINE)  # preserve RichNL so inline comments travel with stmt
NL = expect_nl_or_richnl()  # Returns RichNL or NL token node

###############################################################################
# Operator helpers (augmented assignment operators — all visible)
###############################################################################

augop = (
    vop("+=")
    | vop("-=")
    | vop("*=")
    | vop("/=")
    | vop("//=")
    | vop("%=")
    | vop("**=")
    | vop("@=")
    | vop("<<=")
    | vop(">>=")
    | vop("&=")
    | vop("|=")
    | vop("^=")
)

# Visible '=' for assignment (EQUAL from hek_parsec is ignored)
V_EQUAL = vop("=")

# Visible ':' for annotation (COLON from hek_parsec is ignored)
V_COLON = vop(":")

# Visible '.' for dotted names (DOT from hek_parsec is ignored)
V_DOT = vop(".")

# Visible '/' for slash-separated module paths (e.g. nimport js/jsffi)
V_SLASH = vop("/")

###############################################################################
# Forward declarations
###############################################################################

assign_stmt = fw("assign_stmt")
aug_assign_stmt = fw("aug_assign_stmt")
ann_assign_stmt = fw("ann_assign_stmt")
decl_keyword = fw("decl_keyword")
decl_ann_assign_stmt = fw("decl_ann_assign_stmt")
decl_tuple_unpack = fw("decl_tuple_unpack")
own_stmt = fw("own_stmt")
return_stmt = fw("return_stmt")
pass_stmt = fw("pass_stmt")
break_stmt = fw("break_stmt")
continue_stmt = fw("continue_stmt")
del_stmt = fw("del_stmt")
assert_stmt = fw("assert_stmt")
raise_stmt = fw("raise_stmt")
global_stmt = fw("global_stmt")
nonlocal_stmt = fw("nonlocal_stmt")
import_stmt = fw("import_stmt")
from_stmt = fw("from_stmt")
type_stmt = fw("type_stmt")
nimport_stmt = fw("nimport_stmt")
from_nim_abs = fw("from_nim_abs")
from_pyimport = fw("from_pyimport")
pyimport_stmt = fw("pyimport_stmt")
print_stmt = fw("print_stmt")
print_bare = fw("print_bare")
enum_def = fw("enum_def")
subrange_def = fw("subrange_def")
subrange_array_type = fw("subrange_array_type")
tuple_def = fw("tuple_def")
record_def = fw("record_def")
discrim_param = fw("discrim_param")
variant_when = fw("variant_when")
variant_case = fw("variant_case")
discrim_record_def = fw("discrim_record_def")
type_block_stmt = fw("type_block_stmt")
simple_stmt = fw("simple_stmt")
return_bare_if = fw("return_bare_if")
modifier_body = fw("modifier_body")
exit_call = fw("exit_call")
modifier_if_stmt = fw("modifier_if_stmt")
stmt_head = fw("stmt_head")
stmt_line = fw("stmt_line")

# Re-wrap imported Sequence_Parsers as fw() so they don't get flattened
# when used with '+' in grammar rules below (see ParserMeta.__add__).
_star_expressions = fw("star_expressions")
_expressions = fw("expressions")

# Import sub-rules
dotted_name = fw("dotted_name")
import_as = fw("import_as")
import_name = fw("import_name")
import_names = fw("import_names")
from_rel_name = fw("from_rel_name")
from_rel_bare = fw("from_rel_bare")
from_abs = fw("from_abs")

###############################################################################
# Grammar rules
###############################################################################

# --- Assignment ---
# assign: target ('=' target)* '=' expressions
# We need V_EQUAL (visible) so we can count targets vs value.
# Python allows: a = b = c = 1  (chained) and a, b = 1, 2 (tuple unpack)
assign_stmt = _star_expressions + (V_EQUAL + _star_expressions)[1:]

# --- Augmented assignment ---
# aug_assign: target augop expressions
aug_assign_stmt = _star_expressions + augop + _expressions

# --- Annotated assignment ---
# ann_assign: IDENTIFIER ':' type_annotation ['=' expression]
ann_assign_stmt = IDENTIFIER + V_COLON + type_annotation + (V_EQUAL + expression)[:]

# --- Declaration with keyword (var/let/const) ---
# decl_ann_assign: ("var"|"let"|"const") IDENTIFIER ':' type_annotation ['=' expression]
decl_keyword = literal("var") | literal("let") | literal("const")
decl_ann_assign_stmt = decl_keyword + IDENTIFIER + V_COLON + type_annotation + (V_EQUAL + expression)[:]
# decl_tuple_unpack: let (x, y) = expr
decl_tuple_unpack = decl_keyword + paren_group + V_EQUAL + _expressions


# decl_untyped: let x = expr  (no annotation) -- refused
# Adascript is explicitly typed: a declaration names its type. The one
# exception is a shell command's output, `let r = shell: ...`, whose type the
# command fixes (str unless declared otherwise); shell_target_scalar in
# ady_compound_stmt takes that form, so this rule steps aside for it.
# There was never a rule for the untyped form, but it used to parse by
# accident -- `let` read as a name, abandoned, and a backtracking bug in the
# sequence combinator resuming after it -- so `let x = e` silently lost its
# keyword and became `x = e`. With that bug gone it would be a bare parse
# error at the `let`; this rule says what is wrong instead.
from hek_parsec import Parser as _Parser, apply_parsing_context as _parsing_context

_SHELL_WORDS = ("shell", "shellLines", "shellExec", "shellSpawn")


class decl_untyped(_Parser):
    @_parsing_context
    def parse(cls, token_stream):
        start = token_stream.mark()
        kw_tok = token_stream.get_new_token()
        token_stream.reset(start)
        if not decl_keyword.parse(token_stream):
            return False
        name_tok = token_stream.get_new_token()
        token_stream.reset(start)
        decl_keyword.parse(token_stream)
        if not (IDENTIFIER.parse(token_stream) and V_EQUAL.parse(token_stream)):
            token_stream.reset(start)
            return False
        value_tok = token_stream.get_new_token()
        token_stream.reset(start)
        if value_tok is not None and getattr(value_tok, "string", "") in _SHELL_WORDS:
            return False
        kw, name = kw_tok.string, name_tok.string
        raise SyntaxError(
            f"line {kw_tok.start[0]}: '{kw} {name} = ...' has no type. Adascript is "
            f"explicitly typed: write '{kw} {name}: <type> = ...'. Only a shell "
            f"command's output may leave it out.")

# A module declares each type once. Declared twice, the Python backend let
# the second silently win, and the Nim one merged both into a type section
# that lost the second's header ("invalid indentation", pointing at the
# generated file). Module-level names only: those are the ones that clash.
import re as _re_dup

_TYPE_DECL = _re_dup.compile(r"(?:type|class)\s+([A-Za-z_]\w*)\b")


_OLD_FAILURE_DECL = _re_dup.compile(
    r"^[ \t]*type[ \t]+([A-Za-z_]\w*)\b[^\n]*?[ \t](?:is|=)[ \t]+failure[ \t]+\w+",
    _re_dup.MULTILINE)

# `!X` beside a `|`: X marked as a union's failure member. The `|` is what
# tells it from a shell line's `{!x}` and from `!=`.
_FAILURE_MARK = _re_dup.compile(
    r"\|[ \t]*!([A-Za-z_]\w*)|(?<![\w{!=<>])!([A-Za-z_]\w*)[ \t]*\|")


def scan_failure_types(code):
    """The failure types CODE uses: each X marked `!X` in a union, `int |
    !X`, which makes X the failure side of every union it is in."""
    m = _OLD_FAILURE_DECL.search(code)
    if m:
        raise SyntaxError(
            f"type '{m.group(1)}': a failure type is an ordinary record now -- "
            f"`type {m.group(1)} is record:` -- marked where it is the failure "
            f"of a union: `int | !{m.group(1)}`")
    return {a or b for a, b in _FAILURE_MARK.findall(code)}


def check_failure_marks(parts, marked, failure_types):
    """The failure types of a union whose members are PARTS, MARKED[i] when
    part i was written `!T`: FAILURE_TYPES and the ones marked here. A type
    that is a failure anywhere is marked in every union it is in -- the `!`
    is what shows the reader which member a do: block passes on -- so an
    unmarked one is refused."""
    for p, m in zip(parts, marked):
        if m and (not (p[:1].isupper() and p.replace("_", "").isalnum())
                  or _runtime_kind(p) != p):
            raise SyntaxError(
                f"'!{p}': only a record can be a failure -- it has to say what "
                f"went wrong, and on Python be a class of its own to be told "
                f"from the value")
        if p in failure_types and not m:
            shown = " | ".join(("!" if mk else "") + q for q, mk in zip(parts, marked))
            raise SyntaxError(
                f"'{shown}': {p} is a failure type -- mark it `!{p}`, "
                f"which shows the member a do: block passes on")
    return set(failure_types) | {p for p, m in zip(parts, marked) if m}


_RETURN_DECL = _re_dup.compile(
    r"^[ \t]*def[ \t]+(\w+)[ \t]*\((?:[^()]|\([^()]*\))*\)\s*->\s*"
    r"([^\n#]*?)\s*:[ \t]*(?:#.*)?$", _re_dup.MULTILINE)


def scan_return_types(code):
    """Every `def`'s return annotation, as written, by routine name."""
    return {m.group(1): m.group(2) for m in _RETURN_DECL.finditer(code)}


def split_top_level_bar(text):
    """TEXT split at each `|` outside brackets, each side stripped."""
    depth, parts, cur = 0, [], []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "|" and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur).strip())
    # the `!` of a failure member is not part of its type
    return [p[1:].strip() if p.startswith("!") else p for p in parts]


def _runtime_kind(t):
    """What a value of the type spelled T is at run time on the Python
    backend, where a union holds the value itself and only its class says
    which member it is. Takes either backend's spelling of the type."""
    t = t.strip()
    if t.startswith("("):
        return "tuple"
    base = t.split("[", 1)[0].strip()
    return {"string": "str", "Path": "str", "seq": "list", "Sequence": "list",
            "openArray": "list", "Table": "dict", "HashSet": "set",
            "bool": "int",   # a bool is an int to Python
            }.get(base, base)


def classify_union(parts, failure_types):
    """What the members of a `|` type make it: a dict with KIND --
    "optional" (`T | None`, ?T written out), "either" (a value or a
    failure: one member is a failure type) or "plain" (one of the members)
    -- VALUES, the members that are not the failure, and FAILURE, the
    failure type or None. The order of the members does not matter.

    Refused: two failure types; None in anything but `T | None` or
    `None | !F`; the same member twice; two members nothing can tell apart
    at run time -- on Python the value is the member itself, and its class
    is all that says which one it is."""
    shown = " | ".join(parts)
    failures = [p for p in parts if p in failure_types]
    if len(failures) > 1:
        raise SyntaxError(
            f"'{shown}': a union has at most one failure member -- a do: "
            f"step could not tell which of {', '.join(failures)} to pass on")
    failure = failures[0] if failures else None
    values = [p for p in parts if p not in failure_types]
    nones = values.count("None")
    if nones:
        if len(parts) != 2 or nones > 1:
            raise SyntaxError(
                f"'{shown}': None goes with one other type -- `T | None`, "
                f"which is ?T, or `None | !F`, a step that can only fail. For "
                f"an optional union, declare the union as a type and write ?Name")
        if failure is None:
            return {"kind": "optional", "values": [p for p in parts if p != "None"],
                    "failure": None}
        return {"kind": "either", "values": ["None"], "failure": failure}
    if len(set(values)) != len(values):
        raise SyntaxError(f"'{shown}': a member is there twice")
    kinds = {}
    for v in values:
        k = _runtime_kind(v)
        if k in kinds:
            raise SyntaxError(
                f"'{shown}': {kinds[k]} and {v} cannot be told apart at run "
                f"time -- make one of them a record of its own")
        kinds[k] = v
    return {"kind": "either" if failure else "plain", "values": values,
            "failure": failure}


def either_sides(parts, failure_types):
    """The two-sided view of a `|` type some callers still take:
    ("either", value, failure) with VALUE the value members joined by
    ` | `, ("optional", value, None), or ("plain", members joined, None)."""
    u = classify_union(parts, failure_types)
    return (u["kind"], " | ".join(u["values"]), u["failure"])


_ALIAS_DECL = _re_dup.compile(
    r"^[ \t]*type[ \t]+([A-Za-z_]\w*)[ \t]+(?:is|=)[ \t]+([^\n#]+?)[ \t]*(?:#.*)?$",
    _re_dup.MULTILINE)


def scan_union_aliases(code):
    """The union types CODE names -- `type Num_T is int | float` -- as
    {name: its union, as written}. A backend reads a name that is one as
    the union itself, so that `x is int`, `case x:` and the choice of a
    member work the same on `Num_T` as on `int | float`."""
    out = {}
    for m in _ALIAS_DECL.finditer(code):
        rhs = m.group(2).strip()
        if len(split_top_level_bar(rhs)) >= 2:
            out[m.group(1)] = rhs
    return out


def either_procs(return_types, failure_types):
    """The routines among RETURN_TYPES that return `T | !F`, F a failure."""
    out = set()
    for name, text in return_types.items():
        parts = split_top_level_bar(text)
        if len(parts) >= 2 and any(p in failure_types for p in parts):
            out.add(name)
    return out


def refuse_dropped_failure(stmt_text, is_either_call):
    """Refuse STMT_TEXT, an emitted expression statement, when it is nothing
    but a call of a routine returning `T | !F`: its failure would go unseen.
    IS_EITHER_CALL(text) says whether a call returns one -- each backend
    knows its own calls. Taking the result is what a do: step, a test or a
    `return` are for; dropping it silently is the bug the type exists to
    stop, so it is not a spelling the language has."""
    import re as _re_df
    text = stmt_text.strip()
    m = _re_df.match(r"^(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\(", text)
    if not m or not text.endswith(")"):
        return
    depth = 0
    for i, ch in enumerate(text[m.end() - 1:]):
        depth += ch in "([{"
        depth -= ch in ")]}"
        if depth == 0 and i != len(text) - m.end():
            return          # the call is only part of the statement
    if is_either_call(text):
        raise SyntaxError(
            f"'{text}' drops a failure: take its result -- a do: step, a "
            f"`let` and a test, or `return` it -- or it goes unseen")


def check_duplicate_types(code):
    """Refuse a module that declares the same type name twice at its top
    level (`type X ...`, `class X ...`). Text inside triple-quoted strings
    -- docstrings -- is not code and is skipped."""
    seen = {}
    in_string = None
    for n, line in enumerate(code.splitlines(), 1):
        if in_string is None and line and not line[0].isspace():
            m = _TYPE_DECL.match(line)
            if m:
                name = m.group(1)
                if name in seen:
                    raise SyntaxError(
                        f"line {n}: type '{name}' is already declared, at line "
                        f"{seen[name]}. A module declares each type once: give "
                        f"one of them another name.")
                seen[name] = n
        # track triple-quoted strings opened and closed on this line
        i = 0
        while True:
            if in_string is None:
                hits = [(line.find(q, i), q) for q in ('"""', "'''")]
                hits = [(k, q) for k, q in hits if k >= 0]
                if not hits:
                    break
                k, q = min(hits)
                in_string, i = q, k + 3
            else:
                k = line.find(in_string, i)
                if k < 0:
                    break
                in_string, i = None, k + 3

# --- own declaration: own IDENTIFIER ':' type_annotation ['=' expression] ---
# Unique owner; auto-freed at scope end (Nim ARC; Python GC)
own_stmt = literal("own") + IDENTIFIER + V_COLON + type_annotation + (V_EQUAL + expression)[:]

# --- return ---
return_val = ikw("return") + _expressions
return_bare = literal("return")
return_stmt = return_val | return_bare

# --- pass / break / continue ---
pass_stmt = literal("pass")
break_stmt = literal("break")
continue_stmt = literal("continue")

# --- del ---
del_stmt = ikw("del") + _star_expressions

# --- assert ---
assert_msg = ikw("assert") + expression + COMMA + expression
assert_simple = ikw("assert") + expression
assert_stmt = assert_msg | assert_simple

# --- raise ---
raise_from = ikw("raise") + expression + ikw("from") + expression
raise_exc = ikw("raise") + expression
raise_bare = literal("raise")
raise_stmt = raise_from | raise_exc | raise_bare

# --- global / nonlocal ---
global_stmt = ikw("global") + IDENTIFIER + (COMMA + IDENTIFIER)[:]
nonlocal_stmt = ikw("nonlocal") + IDENTIFIER + (COMMA + IDENTIFIER)[:]

# --- import ---
dotted_name = IDENTIFIER + ((V_DOT | V_SLASH) + IDENTIFIER)[:]
import_as = dotted_name + (ikw("as") + IDENTIFIER)[:]
import_stmt = ikw("import") + import_as + (COMMA + import_as)[:]

# --- from ... import ---
import_name = IDENTIFIER + (ikw("as") + IDENTIFIER)[:]
import_star = SSTAR
# Parenthesized imports: (name, name) for multi-line imports
import_names_paren = LPAREN_NODE + NL[:] + import_name + (NL[:] + COMMA + NL[:] + import_name)[:] + COMMA[:] + NL[:] + RPAREN
import_names = import_names_paren | import_name + (COMMA + import_name)[:] | import_star

# from_stmt variants (explicit to avoid dotted_name greedily consuming 'import'):
#   from ..pkg import x     -> from_rel_name: dots + dotted_name + import + names
#   from .   import x       -> from_rel_bare: dots + import + names
#   from os  import x       -> from_abs:      dotted_name + import + names
from_rel_name = ikw("from") + V_DOT[1:] + dotted_name + ikw("import") + import_names
from_rel_bare = ikw("from") + V_DOT[1:] + ikw("import") + import_names
from_abs = ikw("from") + dotted_name + ikw("import") + import_names
from_stmt = from_rel_name | from_rel_bare | from_abs

# nimport: Nim-only import (stripped in Python output, becomes "import" in Nim)
nimport_stmt = ikw("nimport") + dotted_name + (COMMA + dotted_name)[:]

# jsvar: declare a JS global variable (JS backend only)
#   jsvar window: JsObject           ->  var window {.importc, nodecl.}: JsObject
#   jsvar jsThis as "this": JsObject ->  var jsThis {.importc: "this", nodecl.}: JsObject
jsvar_as_clause = ikw("as") + STRING
jsvar_stmt = ikw("jsvar") + IDENTIFIER + jsvar_as_clause[:] + COLON + type_annotation

# from X nimport Y / from X nimport *  — Python-style selective Nim import
from_nim_abs = ikw("from") + dotted_name + ikw("nimport") + import_names

# from X pyimport Y  — selective Python package import via nimpy
from_pyimport = ikw("from") + dotted_name + ikw("pyimport") + import_names

# pyimport: Python-only import via nimpy (becomes pyImport() in Nim)
pyimport_stmt = ikw("pyimport") + import_as + (COMMA + import_as)[:]

# --- Perl substitution: text = s/pattern/replacement/flags ---
# Must be tried before 'expressions' so the parser doesn't try to interpret
# s/.../ as division, and before assign_stmt, which would otherwise take it.
# V_EQUAL (=) is consumed (ignored) in this rule.
#
# The operator is `=` and not `==`: this is a statement that rewrites its
# target, not a test, and `==` read as an equality to everyone who was not
# already expecting Perl. It is also exactly what both backends emit --
# `stem = stem.replace(...)`.
subst_stmt = primary + ignore(V_EQUAL) + SUBST

# --- print statement (Python 2 / Adascript style) ---
# print expr [, expr ...]  with no parentheses.
# ~LPAREN ensures print(...) is NOT captured here — it falls through to the
# expressions fallback and is treated as a normal print() function call.
print_stmt = ikw("print") + ~LPAREN + _star_expressions
# A bare `print`, nothing after it on the line: an empty line. Without this
# it was the expression `print` -- Python evaluated the function and printed
# nothing, while Nim's bare `echo` printed a newline.
print_bare = ikw("print") + ~~(NEWLINE | SEMICOLON)

# --- type alias (3.12+) / enum ---
# type_alias_params: [T] or [T, U] etc. (generic type parameters)
type_alias_params = LBRACKET + IDENTIFIER + (COMMA + IDENTIFIER)[:] + RBRACKET
# enum_def: enum IDENT, IDENT, ...
enum_member = IDENTIFIER | INTEGER
enum_def = ikw("enum") + enum_member + (COMMA + enum_member)[:] + COMMA[:]
# subrange_def: INT '..' INT  or  INT '..<' INT  or  IDENT±INT '..' IDENT±INT
subrange_bound = (IDENTIFIER + (V_PLUS | V_MINUS) + INTEGER) | INTEGER | IDENTIFIER
subrange_def = subrange_bound + (RANGE_EXCL_OP | RANGE_OP) + subrange_bound
# constrained_subrange_def: base_type lo .. hi  (e.g. int 0 .. CAPITAL)
constrained_subrange_def = fw("constrained_subrange_def")
constrained_subrange_def = IDENTIFIER + subrange_def
# float_range_def: float range LO .. HI  (e.g. float range 0.0 .. 100.0)
float_range_def = fw("float_range_def")
float_range_def = literal("float") + literal("range") + NUMBER + (RANGE_EXCL_OP | RANGE_OP) + NUMBER
# int_range_def: int range LO .. HI  (synonym for constrained_subrange_def)
int_range_def = fw("int_range_def")
int_range_def = literal("int") + literal("range") + subrange_def
# [lo..hi]T  ->  array[lo..hi, T]  (subrange-indexed array)
subrange_array_type = LBRACKET + subrange_def + RBRACKET + elem_type
# Allow subrange_def as a type_annotation (e.g. in tuple fields: stage: 1 .. 5)
# Insert before the expression fallback (last element in type_annotation.parsers)
type_annotation.parsers.insert(0, subrange_def)
elem_type.parsers.insert(0, subrange_def)
# Allow [lo..hi]T as a type_annotation; insert before enum_array_type (position 2:
# after seq_type and callable_type, both of which also start with '[')
from ady_declarations import basic_type as _basic_type
_basic_type.parsers.insert(2, subrange_array_type)
# type_stmt for simple (inline) forms only; block forms (tuple/record) are in ady_compound_stmt
type_stmt = ikw("type") + IDENTIFIER + type_alias_params[:] + (V_EQUAL | ikw("is")) + (enum_def | float_range_def | int_range_def | constrained_subrange_def | subrange_def | type_annotation)

# --- simple_stmt: choice of all statement types ---
# Ordering matters: try more specific forms before general expression.
# aug_assign before assign (both start with expr, but augop is distinctive).
# ann_assign before assign (starts with IDENTIFIER + ':').
# subst before assign: both are `target = ...`, and only subst accepts a
# SUBST token on the right, so it must be offered the line first.
# expressions is the fallback (expression statement).
simple_stmt = (
    own_stmt
    | decl_tuple_unpack
    | decl_ann_assign_stmt
    | decl_untyped
    | ann_assign_stmt
    | aug_assign_stmt
    | subst_stmt
    | assign_stmt
    | return_stmt
    | pass_stmt
    | break_stmt
    | continue_stmt
    | del_stmt
    | assert_stmt
    | raise_stmt
    | global_stmt
    | nonlocal_stmt
    | nimport_stmt
    | jsvar_stmt
    | from_nim_abs
    | from_pyimport
    | pyimport_stmt
    | import_stmt
    | from_stmt
    | type_stmt
    | yield_expr
    | print_stmt
    | print_bare
    | expressions
)

# --- statement modifier: `<stmt> if <condition>` (Perl / Ruby style) ---
#
#   return False if code_s == ""      ->      if code_s == "":
#                                                 return False
#
# Only the three statements that leave where they are -- `return`, `break`,
# `continue` -- may carry one. That is what a guard clause is: the exit, and
# the condition it is taken on. An assignment or a call written this way
# reads as a conditional expression whose `else` has gone missing (`x = 1 if
# c` opens exactly like `x = 1 if c else 2`), and a declaration would bind
# its name inside the body the modifier builds, where Nim scopes it to that
# body and the name is gone by the next line. Neither is offered here.
#
# The condition is a disjunction rather than a full expression, the same rule
# a comprehension's `if` uses. ~I_ELSE is the second lock on that door: an
# `else` after the condition means the line was a conditional expression, so
# the modifier declines and the plain form is parsed instead -- which is what
# keeps `return a if c else b` a ternary.
# A bare `return` needs the lookahead, and has to be offered before the form
# that returns a value: IDENTIFIER matches any NAME token, keywords included,
# so `return if q` otherwise has its `if` taken as the expression returned,
# leaving `q` where the modifier expected the keyword. `~~` is a positive
# lookahead (the negation of a negation) and consumes nothing.
return_bare_if = return_bare + ~~I_IF
# `die(...)` and `quit(...)` leave too -- the program, rather than the
# function -- so they are guard clauses in the same sense: `die("no input")
# if not found`. Only these two names: a call to anything else under an
# `if` modifier is still the conditional expression missing its `else`.
exit_call = ~~(literal("die") | literal("quit")) + primary
modifier_body = return_bare_if | return_val | break_stmt | continue_stmt | exit_call
modifier_if_stmt = modifier_body + I_IF + disjunction + ~I_ELSE

# --- stmt_line: semicolon-separated statements on one line ---
# The modifier form is offered first, and only as the whole line: `a; b if c`
# has no reading that both backends can emit on one line, so it is not one.
stmt_head = modifier_if_stmt | simple_stmt
stmt_line = stmt_head + (SEMICOLON + simple_stmt)[:] + SEMICOLON[:] + NEWLINE

###############################################################################


def parse_stmt(code):
    """Parse a Python 3.14 simple statement and return the AST node.

    Parses a single simple_stmt (no NEWLINE required).
    """
    ParserState.reset()
    stream = Input(code)
    result = simple_stmt.parse(stream)
    if not result:
        return None
    return result[0]


def parse_stmt_line(code):
    """Parse a line of semicolon-separated simple statements.

    Expects NEWLINE at end (as produced by tokenizer for complete lines).
    """
    ParserState.reset()
    stream = Input(code)
    result = stmt_line.parse(stream)
    if not result:
        return None
    return result[0]


###############################################################################
# Tests
###############################################################################




# ---------------------------------------------------------------------------
# A case's labels do not overlap
# ---------------------------------------------------------------------------
# As in Ada, each value a case can see belongs to one branch: `when 34 | 92:`
# then `when 32..126:` covers 34 twice, and which branch it takes would
# depend on the order they are written in. Nim refused it ("duplicate case
# label") and Python took the first, so the two backends disagreed; both
# refuse it now, with the value named. A guarded branch is left out -- its
# guard is what decides -- as are patterns that are not plain values.

def _split_label_alternatives(text):
    """TEXT, a rendered pattern, split at its top-level `,` (Nim) or `|`
    (Python) -- outside brackets and quotes."""
    parts, cur, depth, quote, esc = [], [], 0, "", False
    for ch in text:
        if quote:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = ""
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch in ",|" and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur).strip())
    return [p for p in parts if p]


def _label_value(text):
    """TEXT, one rendered label, as (domain, lo, hi) -- an int or a
    character range, or a single string or name -- or None when it is not
    a plain value."""
    import ast as _ast
    t = text.strip()

    def point(x):
        x = x.strip()
        if _re_dup.fullmatch(r"-?\d+", x):
            return ("int", int(x))
        if len(x) >= 2 and x[0] == x[-1] and x[0] in "'\"":
            try:
                s = _ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return None
            return ("chr", ord(s)) if isinstance(s, str) and len(s) == 1 else ("str", s)
        if _re_dup.fullmatch(r"[A-Za-z_][\w.]*", x) and x not in ("_", "others"):
            return ("name", x)
        return None
    lo, sep, hi = t.partition("..")
    if sep:
        a, b = point(lo), point(hi)
        if a and b and a[0] == b[0] and a[0] in ("int", "chr"):
            return (a[0], a[1], b[1])
        return None
    p = point(t)
    if p is None:
        return None
    return (p[0], p[1], p[1])


def refuse_overlapping_labels(branches):
    """BRANCHES: (rendered pattern, guarded) per branch of a case, in order.
    Raises SyntaxError at the first value two unguarded branches both
    cover."""
    seen = []                                  # (domain, lo, hi, label text)
    for text, guarded in branches:
        if guarded:
            continue
        for alt in _split_label_alternatives(text):
            v = _label_value(alt)
            if v is None:
                continue
            dom, lo, hi = v
            for d2, lo2, hi2, alt2 in seen:
                if d2 != dom:
                    continue
                if dom in ("int", "chr"):
                    if max(lo, lo2) > min(hi, hi2):
                        continue
                    first = max(lo, lo2)
                    shown = repr(chr(first)) if dom == "chr" else str(first)
                elif lo != lo2:
                    continue
                else:
                    shown = alt
                raise SyntaxError(
                    f"case: {shown} is covered by two branches -- `when "
                    f"{alt2}` and `when {alt}`; each value belongs to one "
                    f"branch, so that their order does not matter")
            seen.append((dom, lo, hi, alt))
