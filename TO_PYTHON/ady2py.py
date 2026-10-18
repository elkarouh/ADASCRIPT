#!/usr/bin/env python3
"""Python 3.14 source-to-source translator using parser combinators.

ARCHITECTURE CHANGE (RichNL approach):
======================================
Instead of reconstructing comment positions after parsing, comments are now
attached directly to NL tokens during tokenization as RichNL objects.
Comments travel naturally with the parse tree, eliminating position arithmetic.

CHANGES MADE:
- hek_tokenize.py: Added RichNL class, bundles COMMENT+NL tokens
- hek_parsec.py: Added expect_type_node() to return token nodes (not strings)
- hek_py_parser.py: NL = expect_type_node(tkn.NL), added NL.to_py() method
- hek_py_stmt.py: Fixed import_names_paren to allow NL[:] inside parens
- ady2py.py: Simplified parse_module() and translate()

TEST STATUS (as of implementation):
===================================
29 passed, 3 failed

PASSING:
- Simple statements (x = 1, import, from ... import)
- Compound statements (if/elif/else, while, for, try, with, match)
- Functions, classes, decorators, async variants
- Comments inside blocks (indented comments in compound statements)
- Leading comments (comments before first statement)

FAILING:
1. Blank lines between statements - plain NL tokens are skipped, not emitted
   Input:  'x = 1

y = 2
'
   Expected: 'x = 1

y = 2
'
   Got: 'x = 1
y = 2
'

2. Inline comments - COMMENT+NEWLINE (not NL) not handled
   Input:  'x = 1  # inline
y = 2
'
   Expected: 'x = 1  # inline
y = 2
'
   Got: '
' (broken)

3. Multiple blank lines preserved - same as #1
   Input:  '# header

import os

def f():...'
   Expected: '# header

import os

def f():...'
   Got: '# header
import os
def f():...' (blanks lost)

TODO FOR FUTURE WORK:
=====================
1. Handle plain NL tokens (without comments) - emit them as blank lines
2. Handle inline comments - they use NEWLINE token, not NL
   - Tokenizer needs to bundle COMMENT+NEWLINE or handle separately
3. Preserve blank line counts (currently all blanks collapse to single)
4. Fix statement parsing - only parses ~5 statements from hek_py_expr.py
   - Some grammar rules may still not handle RichNL properly

USAGE:
    python3 ady2py.py [file.py]       # translate a file
    echo "x = 1" | python3 ady2py.py  # translate from stdin
"""

"""Python 3.14 source-to-source translator using parser combinators.

Parses Python source code using the hek_parsec combinator framework
and reconstructs it via to_py() methods on each AST node.

Comments and blank lines are preserved by collecting them as 'trivia'
in the tokenizer and attaching them to AST nodes. This approach is
language-agnostic — trivia travels with the AST, not with line numbers.

Usage:
    python3 ady2py.py [file.py]       # translate a file
    echo "x = 1" | python3 ady2py.py  # translate from stdin
"""

import sys, os

_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "GRAMMAR"))

import re
import sys
import token as token_mod

from hek_py_parser import *  # fw() resolves names in calling module's globals
from hek_tokenize import Tokenizer, RichNL, set_current_tokenizer


def Input(code):
    """Create a token stream for parsing.

    The tokenizer now returns RichNL objects that bundle comments with
    newline tokens. Comments travel naturally with the parse tree,
    eliminating the need for position-based reconstruction.
    """
    gen = Tokenizer(code)
    set_current_tokenizer(gen)
    gen.get_new_token()  # skip ENCODING token
    return gen


def _py_reset():
    """Initialise Python-backend fields on ParserState."""
    from hek_parsec import ParserState
    ParserState.nim_imports = set()   # stores Python import lines (historical naming)
    ParserState.tick_types = {}
    ParserState.ady_type_decls = {}
    ParserState.distinct_types = {}
    ParserState.unit_relations = {}
    ParserState.unit_dims = {}
    ParserState.affine_units = {}
    ParserState.inverse_units = {}
    ParserState.written_as = {}
    ParserState.narrowed_types = {}
    ParserState.mod_types = {}
    ParserState.record_types = set()
    ParserState.py_range_fields = {}      # field name -> its subrange type
    ParserState.py_type_aliases = {}
    ParserState.py_top_decls = []
    # Marks are held by id(), which the allocator reuses once a parse tree is
    # collected, so they must not outlive the module that set them.
    import hek_py_stmt as _stmt
    _stmt.RETURN_NODES.clear()


def parse_module(code):
    """Parse a full module. Comments are embedded in the parse tree via RichNL."""
    from hek_parsec import ParserState
    check_duplicate_types(code)
    check_chained_units(code)
    ParserState.reset()
    _py_reset()
    # Set when a statement fails to parse. translate() goes on with the ones
    # before it -- the language server wants their symbols beside the error --
    # so the command line reads this to know the run failed.
    ParserState.parse_error = None
    stream = Input(code)
    stmts = []
    leading = []
    import token as token_mod

    # Peek at first token
    first_token = None
    try:
        first_token = stream.get_new_token()
    except StopIteration:
        pass

    if first_token is None or first_token.type == token_mod.ENDMARKER:
        return stmts, leading, []

    # Collect leading RichNL comments
    if isinstance(first_token, RichNL):
        leading.append(first_token)
        while True:
            tok = stream.get_new_token()
            if isinstance(tok, RichNL):
                leading.append(tok)
            elif tok.type == token_mod.NL:
                continue
            else:
                stream.reset(stream.mark() - 1)
                break
    else:
        stream.reset(stream.mark() - 1)

    # Parse statements with inter-statement comments
    while True:
        inter_comments = []

        # Collect RichNL comments before this statement
        while True:
            pos = stream.mark()
            try:
                tok = stream.get_new_token()
            except StopIteration:
                break
            if isinstance(tok, RichNL):
                inter_comments.append(tok)
                continue
            if tok.type == token_mod.NL:
                continue
            stream.reset(pos)
            break

        # Check for end of input
        try:
            tok = stream.get_new_token()
        except StopIteration:
            break
        if not tok or tok.type == token_mod.ENDMARKER:
            break
        stream.reset(pos)

        result = statement.parse(stream)
        if not result:
            import sys
            ParserState.parse_error = stream.format_error()
            if not getattr(ParserState, "defer_parse_error", False):
                print(ParserState.parse_error, file=sys.stderr)
            break

        node = result[0]
        node._leading_comments = inter_comments
        stmts.append(node)

    return stmts, leading, []


def _inject_before_elif_else(rendered, spill_lines):
    """Inject spill_lines before the first elif/else at indent 0 in rendered.

    Returns modified rendered string, or None if no injection point found.
    """
    import re
    lines = rendered.split("\n")
    # Find the first line that starts with 'elif ' or 'else:'
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("elif ", "else:")):
            new_lines = lines[:i] + spill_lines + lines[i:]
            return "\n".join(new_lines)
    return None


# Modules Adascript names in source and both languages provide, under the
# same spelling on the Python side. A `nimport` is Nim-only by design, so
# nothing imports these here -- `nimport times` plus `time.time()` gave a
# working Nim program and a NameError on Python. Only the ones whose
# Python spelling matches what the source writes are listed; anything
# needing a rename is a mapping question, not an import one.
_AUTO_STDLIB_MODULES = ("os", "time", "math", "random", "json")


def _drop_type_applications(output):
    """`f[T](x)` -> `f(x)` for a function this module defines.

    Nim takes an explicit type application at the call site and Adascript
    passes it through; Python infers the parameter instead, and a function
    object is not subscriptable. Applied as a post-pass so a call that
    appears above its own `def` is rewritten too. Only names defined here
    are touched, so `list[int](xs)` and friends are left alone.
    """
    import re as _re_ta
    from hek_parsec import ParserState
    names = getattr(ParserState, "py_func_names", set())
    if not names:
        return
    alt = "|".join(sorted((_re_ta.escape(n) for n in names), key=len, reverse=True))
    pat = _re_ta.compile(rf'(?<![\w.])({alt})\[[^][]*\]\s*\(')
    for i, chunk in enumerate(output):
        # A `def f[T](...)` line declares the parameters rather than
        # applying them -- PEP 695, which Python takes as written. Only
        # call sites are rewritten. An entry is a whole statement, so a
        # function is one entry starting with its `def`: the test is made
        # line by line, or the calls in its body were never rewritten.
        if "[" in chunk:
            lines = chunk.split("\n")
            for j, line in enumerate(lines):
                if "[" in line and not line.lstrip().startswith(("def ", "async def ")):
                    lines[j] = pat.sub(r'\1(', line)
            output[i] = "\n".join(lines)


# What Nim's math calls what Python's calls something else: a file `nimport`s math
# and writes Nim's names, so `math.arctan(x)` has to become `math.atan(x)` here.
from hek_py_stmt import _MATH_FOR_PYTHON  # noqa: E402


def _rename_math_for_python(output):
    """`math.arctan(x)` -> `math.atan(x)`, and the other names above."""
    import re as _re_rm
    pat = _re_rm.compile(r'(?<![\w.])math\.(' + "|".join(_MATH_FOR_PYTHON) + r')\b')
    for i, line in enumerate(output):
        if "math." in line:
            output[i] = pat.sub(lambda m: "math." + _MATH_FOR_PYTHON[m.group(1)], line)


def _add_stdlib_module_imports(output):
    """Import a stdlib module the generated code actually calls into."""
    import re as _re_ai
    from hek_parsec import ParserState
    body = "\n".join(output)
    for mod in _AUTO_STDLIB_MODULES:
        # Anchored: `nimport times` contains "import time" as a substring,
        # so a plain `in` test saw an import that is not there.
        # `from math import floor` does not bind `math`
        if _re_ai.search(rf'(?m)^\s*import {mod}\b', body):
            continue
        if any(imp.split()[-1] == mod for imp in ParserState.nim_imports):
            continue
        # A use, not a mention: `time.time()` counts, `self.time` does not.
        if _re_ai.search(rf'(?<![\w.]){mod}\.\w', body):
            ParserState.nim_imports.add(f"import {mod}")


def translate(code):
    """Parse Python source and reconstruct it via to_py()."""
    if not code.strip():
        return code

    from ady_decorators import expand_decorators
    code = expand_decorators(code)             # `@aligned(64)`: see ady_decorators
    from ady_stmt import expand_type_args
    code = expand_type_args(code)              # `f[[]int](x)`: see ady_stmt
    from ady_declarations import refuse_dict_display_types
    refuse_dict_display_types(code)            # `{int: int}` is written {int}int
    from ady_declarations import refuse_paren_enums
    refuse_paren_enums(code)                   # `is (A, B)`: an enum is `is enum A, B`
    from ady_declarations import refuse_let_writes
    refuse_let_writes(code)                    # `let r = Row(); r.x = 1`: Nim refuses it
    from ady_declarations import refuse_override_var_mismatch
    refuse_override_var_mismatch(code)         # an override's `var` parameters: Nim refuses a mismatch
    from ady_stmt import expand_variant_literals
    code = expand_variant_literals(code)   # `VNum(3.0)`: see ady_stmt
    from ady_stmt import resolve_unit_aliases, desugar_optional_unions
    code = desugar_optional_unions(code)    # `A | B | None` is ?(A | B)
    code = resolve_unit_aliases(code)      # an alias of a unit is the unit
    from ady_stmt import scan_failure_types, scan_return_types, either_procs
    _failures = scan_failure_types(code)   # before the parse: see ady2nim
    stmts, leading, trailing = parse_module(code)

    # The types this module declares, for `x is SomeType`; its failure
    # types, which say which side of a `|` is the failure; and the routines
    # returning `T | !F`, for refusing one as a ?T step in a do: block.
    import re as _re_rp
    from hek_parsec import ParserState as _PS_rp
    _PS_rp.py_type_names = set(_re_rp.findall(
        r"^[ \t]*(?:type|class)[ \t]+([A-Za-z_]\w*)", code, _re_rp.MULTILINE))
    from ady_stmt import BUILTIN_FAILURE_TYPES, BUILTIN_RETURN_TYPES, BUILTIN_RESULT_PROCS
    _PS_rp.failure_types = _failures | BUILTIN_FAILURE_TYPES
    _PS_rp.py_type_names |= BUILTIN_FAILURE_TYPES
    _PS_rp.ady_return_types = {**BUILTIN_RETURN_TYPES, **scan_return_types(code)}
    from ady_stmt import scan_method_return_types
    _PS_rp.py_method_return_types = scan_method_return_types(code)
    from ady_stmt import scan_method_overloads
    _PS_rp.py_method_overloads = scan_method_overloads(code)
    from ady_stmt import scan_constructors
    _PS_rp.py_constructors = scan_constructors(code, every=True)
    from ady_stmt import scan_union_aliases, scan_type_decls
    from ady_stmt import check_record_bodies, check_no_failing_init, check_no_where_types
    check_record_bodies(code)
    pass  # check_no_failing_init(code)
    check_no_where_types(code)
    _PS_rp.union_aliases = scan_union_aliases(code)
    _PS_rp.ady_type_decls = scan_type_decls(code)
    from ady_stmt import scan_record_fields
    _PS_rp.record_fields = scan_record_fields(code)
    from ady_declarations import distinct_types, unit_relations, scaled_units
    from ady_stmt import scan_consts
    # A scaled unit's conversions are chosen by the unit of their argument,
    # worked out where they are written (hek_py_expr._scaled_conversion);
    # where it cannot be told the conversion is refused, never guessed.
    _scaled = scaled_units(_PS_rp.ady_type_decls, scan_consts(code))
    _PS_rp.py_scaled_units = _scaled
    from ady_declarations import affine_units, inverse_units
    _PS_rp.affine_units = affine_units(_PS_rp.ady_type_decls)
    _PS_rp.inverse_units = inverse_units(_PS_rp.ady_type_decls)
    from ady_declarations import narrowed_types, mod_types
    _PS_rp.narrowed_types = narrowed_types(_PS_rp.ady_type_decls)
    _PS_rp.mod_types = mod_types(_PS_rp.ady_type_decls)
    _PS_rp.distinct_types = distinct_types(_PS_rp.ady_type_decls, scaled=_scaled,
                                           consts=scan_consts(code))
    _PS_rp.unit_relations = unit_relations(_PS_rp.ady_type_decls, _scaled)
    from ady_declarations import unit_dims, inferred_relations
    _PS_rp.unit_dims = unit_dims(_PS_rp.ady_type_decls)
    _PS_rp.unit_relations.update(inferred_relations(
        _PS_rp.unit_dims, _PS_rp.distinct_types, _PS_rp.unit_relations,
        set(_PS_rp.ady_type_decls)))
    # a generic function must be called with its type arguments written out
    from ady_stmt import scan_generic_funcs, scan_plain_defs, check_generic_calls
    check_generic_calls(stmts, scan_generic_funcs(code), scan_plain_defs(code))
    _PS_rp.union_aliases_py = {}
    _PS_rp.result_procs = (either_procs(_PS_rp.ady_return_types,
                                        _PS_rp.failure_types)
                           | BUILTIN_RESULT_PROCS)

    # Which names live at module level has to be known before the first
    # function is emitted, since a function may assign one declared below it.
    register_module_globals(stmts)

    # The names this module defines at top level, for the same reason: a
    # builtin call rewrite must not capture a call to one of them. Known
    # before the first function is emitted, since a call can precede the def.
    from hek_parsec import ParserState as _PS_udef
    import re as _re_udef
    _PS_udef.user_top_level_procs = set(
        _re_udef.findall(r'^def\s+([A-Za-z_]\w*)\s*[\(\[]', code, _re_udef.M))
    # Whether any routine of its own is named contains: else `s.contains(x)`
    # is Nim's strutils/sets one, which is Python's `in`.
    _PS_udef.py_own_contains = bool(
        _re_udef.search(r'^\s*def\s+contains\s*[\(\[]', code, _re_udef.M))
    # ... and the type of each one's first parameter: `p.total` for a P_T p is
    # total(p), as Nim reads it, when total's first parameter is a P_T
    _PS_udef.py_first_param = {
        m.group(1): m.group(2) for m in _re_udef.finditer(
            r'^def\s+([A-Za-z_]\w*)\s*\(\s*\w+\s*:\s*([A-Za-z_][\w.]*)\s*[,)=]', code, _re_udef.M)}
    # ... unless the type has a field or method of that name: `ed.row` of an
    # Editor with a field row is the field, whatever functions are named row
    # and each field's type, `self.box.area` needing what self.box is
    _members, _fields, _owner, _owner_indent, _member_indent = {}, {}, None, 0, None
    for _ln in code.split("\n"):
        _head = _re_udef.match(r'([ \t]*)(?:class\s+(\w+)|type\s+(\w+)\s+is\s+(?:record|tuple)\b)', _ln)
        if _head:
            _owner, _owner_indent = _head.group(2) or _head.group(3), len(_head.group(1))
            _member_indent = None
            _members.setdefault(_owner, set())
            continue
        if _owner and _ln.strip():
            _ind = len(_ln) - len(_ln.lstrip())
            if _ind <= _owner_indent:
                _owner = None
                continue
            _m = _re_udef.match(r'\s+(?:var\s+|def\s+)?(\w+)\s*[:(]', _ln)
            if _m:
                _members[_owner].add(_m.group(1))
            if _member_indent is None and not _ln.lstrip().startswith(("#", '"')):
                _member_indent = _ind
            _f = _re_udef.match(r'\s+(?:var\s+)?(\w+)\s*:\s*([^=#\n]+?)\s*(?:=.*)?(?:#.*)?$', _ln)
            if _f and _ind == _member_indent and _f.group(1) not in ("def", "class"):
                _fields.setdefault(_owner, {})[_f.group(1)] = _f.group(2).strip()
    _PS_udef.py_type_members = _members
    _PS_udef.py_field_types = _fields
    # each top-level function's parameter types, by position, for the unit
    # check of a call's arguments (hek_py_expr._refuse_argument_units); a name
    # defined twice is an overload, and left out
    _params, _seen_defs = {}, set()
    for _m in _re_udef.finditer(r'^def\s+(\w+)\s*\(', code, _re_udef.M):
        _name, _k, _depth = _m.group(1), _m.end(), 1
        while _k < len(code) and _depth:
            _depth += {"(": 1, ")": -1}.get(code[_k], 0)
            _k += 1
        if _name in _seen_defs:
            _params.pop(_name, None)
            continue
        _seen_defs.add(_name)
        from hek_py_overload import _split_top as _split_params
        _types = []
        for _p in _split_params(code[_m.end():_k - 1]):
            _pm = _re_udef.match(r'\s*\w+\s*:\s*([^=]+?)\s*(?:=.*)?$', _p, _re_udef.S)
            _types.append(_pm.group(1).strip() if _pm else "")
        _params[_name] = _types
    _PS_udef.py_param_types = _params
    # PROG, the program's name, is predeclared for a module that uses it and
    # does not declare its own -- as on the Nim backend.
    if (_re_udef.search(r'\bPROG\b', code)
            and not _re_udef.search(r'^(let|var|const)\s+PROG\b', code, _re_udef.M)):
        from hek_py_expr import ensure_prog_global
        ensure_prog_global()

    output = []

    def emit_richnl(richnl):
        """Emit lines for a RichNL (comments and/or blank lines)."""
        output.extend(richnl.to_lines())

    # Emit leading comments and blank lines
    for richnl in leading:
        emit_richnl(richnl)

    for stmt in stmts:
        # Emit inter-statement comments attached to this statement
        inter = getattr(stmt, '_leading_comments', [])
        for richnl in inter:
            emit_richnl(richnl)

        # Emit the reconstructed statement
        try:
            rendered = stmt.to_py(0)
        except TypeError:
            rendered = stmt.to_py()
        # Compound statement bodies may have absorbed trailing blank lines
        # (blank NL tokens before DEDENT). Strip them from the rendered output
        # and emit them as inter-statement blanks after this statement.
        rendered_lines = rendered.split('\n')
        trailing_blanks = 0
        while rendered_lines and rendered_lines[-1] == '':
            rendered_lines.pop()
            trailing_blanks += 1
        output.append('\n'.join(rendered_lines))
        for _ in range(trailing_blanks):
            output.append('')

    # Emit trailing comments
    for richnl in trailing:
        emit_richnl(richnl)

    # Insert auto-collected imports at the top (after leading comments)
    from hek_parsec import ParserState
    _rename_math_for_python(output)
    _add_stdlib_module_imports(output)
    _drop_type_applications(output)
    from hek_py_overload import overload_defs
    output[:] = overload_defs("\n".join(output), 0).split("\n")
    # Annotations are not evaluated where they are written, so one may name
    # a class defined further down -- `def builds(self) -> list[Build]` in a
    # class above Build raised NameError. Definition order does not matter
    # in Adascript; a call is resolved when it runs, and now so is this.
    ParserState.nim_imports.add("from __future__ import annotations")
    # Find the first non-comment, non-blank line
    insert_pos = 0
    for i, line in enumerate(output):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            insert_pos = i
            break
    # the __future__ import first: Python allows nothing ahead of it
    for imp in sorted(ParserState.nim_imports, key=lambda imp: (not imp.startswith("from __future__"), imp)):
        output.insert(insert_pos, imp)
        insert_pos += 1

    # Inject py_top_decls (e.g. _pymatch helper) right after imports
    py_top_decls = getattr(ParserState, 'py_top_decls', [])
    from hek_py_stmt import _UNIT_OPS_HELPER
    if _UNIT_OPS_HELPER in py_top_decls:
        rels = {k: v for k, v in (getattr(ParserState, "unit_relations", None) or {}).items()
                if k[0] in ("*", "/") and not k[1].startswith("<")
                and not v.startswith("<")}
        py_top_decls.insert(py_top_decls.index(_UNIT_OPS_HELPER),
                            "_UNIT_RELATIONS = {" + ", ".join(
                                f"{k!r}: {v!r}" for k, v in sorted(rels.items())) + "}")
    if py_top_decls:
        insert_pos = 0
        for i, line in enumerate(output):
            stripped = line.strip()
            if stripped and not stripped.startswith(("import ", "from ", "#")):
                insert_pos = i
                break
        for decl in py_top_decls:
            decl_lines = decl.rstrip('\n').split('\n')
            for j, dl in enumerate(decl_lines):
                output.insert(insert_pos + j, dl)
            output.insert(insert_pos + len(decl_lines), '')
            insert_pos += len(decl_lines) + 1

    result = _failing_constructors(chr(10).join(output), code)
    if not result.endswith(chr(10)):
        result += chr(10)
    return result


_FAILING_NEW = """\
    def __new__(cls, *args, **kwargs):
        \"\"\"A constructor that can fail: the failure its __init__ returned, or
        the object made. Python's own __init__ returns nothing.\"\"\"
        self = super().__new__(cls)
        failed = self._ada_init(*args, **kwargs)
        return self if failed is None else failed

    def __init__(self, *args, **kwargs):
        pass  # made by __new__

"""


def _failing_constructors(text, code):
    """TEXT with each class whose __init__ can fail (`-> None | !F`) made by a
    __new__ that returns the failure in place of the object, as the Nim
    backend's constructor returns `C | !F`."""
    from ady_stmt import failing_constructors
    for cls in failing_constructors(code):
        m = re.search(rf"^class {re.escape(cls)}\b[^\n]*:\n", text, re.MULTILINE)
        if not m:
            continue
        end = re.search(r"^\S", text[m.end():], re.MULTILINE)
        stop = m.end() + end.start() if end else len(text)
        body = text[m.end():stop]
        init = re.search(r"^    def __init__\(self", body, re.MULTILINE)
        if not init:
            continue
        body = (body[:init.start()] + _FAILING_NEW
                + body[init.start():].replace("    def __init__(self", "    def _ada_init(self", 1))
        text = text[:m.end()] + body + text[stop:]
    return text
# `nimport geom, util` and `from geom nimport dist`: the names a source file
# imports as Nim modules. ady2nim's own pre-pass reads the same two spellings.
_NIMPORT_LINE = re.compile(
    r'^(?:nimport[ \t]+(?P<names>\w[\w./]*(?:[ \t]*,[ \t]*\w[\w./]*)*)'
    r'|from[ \t]+(?P<from>\w[\w./]*)[ \t]+nimport\b(?:[ \t]*\([^)]*\)|[^\n]*))[ \t]*(?:#[^\n]*)?$',
    re.MULTILINE)


def include_ady_modules(code, search_dir, _seen=None):
    """CODE with each `nimport` of an .ady module replaced by that module.

    ady2nim compiles a program's modules one by one and links them; ady2py
    translates one file, so the modules are brought into it: a module's text
    stands where it is first nimported (its own nimports first), once, and the
    parser then sees the types it declares, which is what `case` and `is` need
    to tell a name from a pattern. Where to look is ady2nim's rule: the
    importing file's directory, then its parent. A name with no .ady there
    (`nimport os`, `nimport strutils`) stays a Nim-only import, dropped from
    the output as before; so do the libraries bundled with ady2nim.
    """
    seen = set() if _seen is None else _seen
    from ady_modules import import_map, resolve_imports, normalize_imports

    from ady_modules import module_dirs

    def find(name, here):
        for base in module_dirs(here):
            path = os.path.join(base, name + ".ady")
            if os.path.isfile(path):
                return path
        return None

    # the rule of what the file may use of its modules, bundled libraries too
    stdlib = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TO_NIM", "STDLIB")

    # a bundled library made of what only Nim has (db.ady on db_sqlite) has its
    # Python version beside this file, in TO_PYTHON/STDLIB, taken first
    py_stdlib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STDLIB")

    def find_checked(name):
        path = find(name, search_dir)
        for lib in (py_stdlib, stdlib):
            bundled = os.path.join(lib, name + ".ady")
            if not path and os.path.isfile(bundled):
                path = bundled
        return path
    # `import M` of an .ady module, `nimport` of a Nim one, `pyimport` of a Python one
    code = normalize_imports(code, lambda name: find_checked(name) is not None)
    from ady_modules import refuse_bare_nim_names
    refuse_bare_nim_names(code, lambda name: find_checked(name) is not None)
    from ady_modules import refuse_python_math_names
    refuse_python_math_names(code, lambda name: find_checked(name) is not None)
    from ady_modules import refuse_shared_names
    refuse_shared_names(code, {mod: (listed, open(find_checked(mod), encoding="utf-8").read())
                               for mod, listed in import_map(code).items() if find_checked(mod)})
    for mod, listed in import_map(code).items():
        path = find_checked(mod)
        if path:
            with open(path, encoding="utf-8") as f:
                code = resolve_imports(code, mod, listed, f.read())
    # a name taken from a module that is merged under another name (geometry's
    # `distance` beside an importer's own, merged as geometry__distance) is
    # that name here too
    from ady_modules import RENAMED, rename_in, STAR as _STAR, _binds, _blank
    for mod, listed in import_map(code).items():
        renames = RENAMED.get(mod.rsplit("/", 1)[-1], {})
        taken = {n: r for n, r in renames.items()
                 if (listed is _STAR or n in listed) and not _binds(_blank(code), n)}
        if taken:
            code = rename_in(code, taken)

    def expand(match):
        names = match.group("names")
        wanted = [n.strip() for n in names.split(",")] if names else [match.group("from")]
        kept, pieces = [], []
        for name in wanted:
            path = find_checked(name)
            if path is None:
                kept.append(name)
                continue
            path = os.path.realpath(path)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if path in seen:
                continue
            seen.add(path)
            MODULE_PATHS[name] = path
            if text.startswith("#!"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
            text = _without_main_block(include_ady_modules(text, os.path.dirname(path), seen))
            # its names the importing file declares too, reached as `M.name`
            from ady_modules import RENAMED, rename_in
            text = rename_in(text, RENAMED.get(name.rsplit("/", 1)[-1], {}))
            pieces.append(f"# ---- {name}.ady, imported ----\n{text.rstrip()}\n# ---- end of {name}.ady ----")
        head = [f"nimport {', '.join(kept)}"] if kept and names else ([match.group(0)] if kept else [])
        return "\n".join(head + pieces)

    return _NIMPORT_LINE.sub(expand, code)


def _without_main_block(text):
    """TEXT without its `if __name__ == "__main__":` block: merged into the
    importer, a module is not the program run, as on Nim it is not."""
    out, skipping = [], False
    for line in text.split("\n"):
        if re.match(r"""if\s+__name__\s*==\s*["']__main__["']\s*:\s*(#.*)?$""", line):
            skipping = True
            continue
        if skipping and (not line.strip() or line[0] in " \t"):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


# {name: path} of each .ady module merged into the file, for an error found in one
MODULE_PATHS = {}


def _module_parse_error(code, error):
    """ERROR, a parse error in CODE (the file with its modules merged in), told at the
    module's own file and line when it is inside one: that module is parsed alone."""
    import re as _re
    m = _re.match(r"Parse error at line (\d+)", error)
    if not m:
        return error
    inside = None
    for i, text in enumerate(code.split("\n")[:int(m.group(1))], 1):
        start = _re.match(r"# ---- (.+)\.ady, imported ----$", text)
        end = _re.match(r"# ---- end of (.+)\.ady ----$", text)
        if start:
            inside = (inside or []) + [start.group(1)]
        elif end and inside:
            inside = inside[:-1] or None
    if not inside or inside[-1] not in MODULE_PATHS:
        return error
    path = MODULE_PATHS[inside[-1]]
    with open(path, encoding="utf-8") as f:
        translate(f.read())
    from hek_parsec import ParserState as _PS
    return f"{path}: {_PS.parse_error or error}"


def _refuse_html_blocks(code, main_path):
    """An `html:` block builds a karax page, which only ady2nim knows: said at
    the block's own file and line, not as a parse error at its first tag."""
    import re as _re
    from ady_html import _OPEN
    inside = []
    for i, text in enumerate(code.split("\n"), 1):
        start = _re.match(r"# ---- (.+)\.ady, imported ----$", text)
        end = _re.match(r"# ---- end of (.+)\.ady ----$", text)
        if start:
            inside.append(start.group(1))
        elif end and inside:
            inside.pop()
        elif _OPEN.match(text):
            path, line = main_path or "<stdin>", i
            if inside and inside[-1] in MODULE_PATHS:
                path = MODULE_PATHS[inside[-1]]
                with open(path, encoding="utf-8") as f:
                    line = next(n for n, t in enumerate(f.read().split("\n"), 1)
                                if _OPEN.match(t))
            raise SyntaxError(
                f"{path}:{line}: an html: block builds a karax page, which is "
                "Nim only (ady2nim c or js); ady2py cannot translate it")


def main(args=None):
    import subprocess
    if args is None:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("file", nargs="?")
        parser.add_argument("rest", nargs="*")
        parser.add_argument("-c", action="store_true")
        args = parser.parse_args()
    if args.file:
        with open(args.file) as f:
            code = f.read()
    else:
        code = sys.stdin.read()
    try:
        code = include_ady_modules(
            code, os.path.dirname(os.path.abspath(args.file)) if args.file else os.getcwd())
        _refuse_html_blocks(code, args.file)
    except SyntaxError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    # A refusal from an emitter is an answer, not a crash: ady2nim prints it
    # and exits 1, and this printed a traceback with the message at the
    # bottom of it.
    from hek_parsec import ParserState as _PS_main
    _PS_main.defer_parse_error = True
    try:
        output = translate(code)
    except SyntaxError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    if getattr(_PS_main, "parse_error", None):
        print(_module_parse_error(code, _PS_main.parse_error), file=sys.stderr)
    # A parse error was printed, and what came before it translated -- for the
    # language server's sake. A command must not pass that off as success: the
    # partial output would build, and exit 0 says nothing was wrong.
    from hek_parsec import ParserState as _PS_main
    if getattr(_PS_main, "parse_error", None):
        sys.exit(1)
    if args.c and args.file:
        base = os.path.splitext(args.file)[0]
        py_file = base + "_gen.py"
        with open(py_file, "w") as f:
            f.write(output)
        print(f"Wrote {py_file}")
        result = subprocess.run([sys.executable, py_file] + (args.rest or []))
        sys.exit(result.returncode)
    else:
        print(output, end="")


###############################################################################
# Tests
###############################################################################


def run_tests():
    print("=" * 60)
    print("Python 3.14 ady2py Translator Tests")
    print("=" * 60)

    tests = [
        # --- simple statements ---
        (
            "x = 1\n",
            "x = 1\n",
        ),
        (
            "x = 1\ny = 2\n",
            "x = 1\ny = 2\n",
        ),
        (
            "x += 1\n",
            "x += 1\n",
        ),
        (
            "import os\n",
            "import os\n",
        ),
        (
            "from os import path\n",
            "from os import path\n",
        ),
        (
            "x = 1; y = 2\n",
            "x = 1; y = 2\n",
        ),
        # --- compound statements ---
        (
            "if x:\n    pass\n",
            "if x:\n    pass\n",
        ),
        (
            "if x:\n    a = 1\nelif y:\n    b = 2\nelse:\n    c = 3\n",
            "if x:\n    a = 1\nelif y:\n    b = 2\nelse:\n    c = 3\n",
        ),
        (
            "while x:\n    pass\n",
            "while x:\n    pass\n",
        ),
        (
            "for x in xs:\n    pass\n",
            "for x in xs:\n    pass\n",
        ),
        (
            "try:\n    pass\nexcept ValueError:\n    pass\n",
            "try:\n    pass\nexcept ValueError:\n    pass\n",
        ),
        (
            "try:\n    pass\nfinally:\n    pass\n",
            "try:\n    pass\nfinally:\n    pass\n",
        ),
        (
            "with f():\n    pass\n",
            "with f():\n    pass\n",
        ),
        (
            "def f():\n    pass\n",
            "def f():\n    pass\n",
        ),
        (
            "def f(a, b=1):\n    return a\n",
            "def f(a, b=1):\n    return a\n",
        ),
        (
            "class Foo:\n    pass\n",
            "class Foo:\n    pass\n",
        ),
        (
            "class Foo(Bar):\n    pass\n",
            "class Foo(Bar):\n    pass\n",
        ),
        (
            "@dec\ndef f():\n    pass\n",
            "@dec\ndef f():\n    pass\n",
        ),
        (
            "async def f():\n    pass\n",
            "async def f():\n    pass\n",
        ),
        (
            "case x:\n    when 1:\n        pass\n",
            "match x:\n    case 1:\n        pass\n",
        ),
        # --- mixed programs ---
        (
            "import os\ndef main():\n    return os\n",
            "import os\ndef main():\n    return os\n",
        ),
        (
            "x = 1\nif x:\n    y = 2\n",
            "x = 1\nif x:\n    y = 2\n",
        ),
        (
            "def f():\n    pass\nclass Foo:\n    pass\n",
            "def f():\n    pass\nclass Foo:\n    pass\n",
        ),
        # --- nested ---
        (
            "if x:\n    if y:\n        pass\n",
            "if x:\n    if y:\n        pass\n",
        ),
        (
            "def f():\n    for x in xs:\n        if x:\n            return x\n",
            "def f():\n    for x in xs:\n        if x:\n            return x\n",
        ),
        (
            "class Foo:\n    def bar(self):\n        pass\n",
            "class Foo:\n    def bar(self):\n        pass\n",
        ),
        # --- a class body cannot name the class it is defining ---
        # Python evaluates an annotation where it is written, and the class
        # does not exist until its body ends, so these have to be forward
        # references. TOOLS/C500/c500.ady could not be imported without this.
        (
            "class Node:\n    nxt: ?Node\n",
            'class Node:\n    nxt: "Node | None"\n',
        ),
        (
            "class Node:\n    def clone(self) -> Node:\n        pass\n",
            'class Node:\n    def clone(self) -> "Node":\n        pass\n',
        ),
        (
            "class Node:\n    def link(self, other: Node):\n        pass\n",
            'class Node:\n    def link(self, other: "Node"):\n        pass\n',
        ),
        # ...but a method body is an ordinary scope, entered only once the
        # class exists, so a local there keeps its plain annotation.
        (
            "class Node:\n    def f(self):\n        n: Node = self\n",
            "class Node:\n    def f(self):\n        n: Node = self\n",
        ),
        # An unrelated type in a class body is not quoted either.
        (
            "class Node:\n    count: int\n",
            "class Node:\n    count: int\n",
        ),
        # --- larger program ---
        (
            "import os\nimport sys\ndef main():\n    x = 1\n    if x:\n        return x\n    return None\n",
            "import os\nimport sys\ndef main():\n    x = 1\n    if x:\n        return x\n    return None\n",
        ),
        # --- comments and blank lines ---
        (
            "# standalone comment\nx = 1\n",
            "# standalone comment\nx = 1\n",
        ),
        (
            "x = 1\n\ny = 2\n",
            "x = 1\n\ny = 2\n",
        ),
        (
            "# comment 1\n# comment 2\nx = 1\n",
            "# comment 1\n# comment 2\nx = 1\n",
        ),
        (
            "x = 1  # inline\ny = 2\n",
            "x = 1  # inline\ny = 2\n",
        ),
        (
            "# header\n\nimport os\n\n# func comment\ndef f():\n    pass\n",
            "# header\n\nimport os\n\n# func comment\ndef f():\n    pass\n",
        ),
        # --- bashisms ---
        (
            "$0\n",
            "import sys\nsys.argv[0]\n",
        ),
        (
            "$1\n",
            "import sys\n(sys.argv[1] if len(sys.argv) > 1 else \"\")\n",
        ),
        (
            "$2\n",
            "import sys\n(sys.argv[2] if len(sys.argv) > 2 else \"\")\n",
        ),
        (
            "$@\n",
            "import sys\nsys.argv[1:]\n",
        ),
        (
            "$#\n",
            "import sys\nlen(sys.argv) - 1\n",
        ),
        (
            "$HOME\n",
            "import os\nos.environ.get('HOME', '')\n",
        ),
        (
            "name = $1\n",
            "import sys\nname = (sys.argv[1] if len(sys.argv) > 1 else \"\")\n",
        ),
        (
            "if $# < 2:\n    pass\n",
            "import sys\nif len(sys.argv) - 1 < 2:\n    pass\n",
        ),
        (
            "for arg in $@:\n    pass\n",
            "import sys\nfor arg in sys.argv[1:]:\n    pass\n",
        ),
        # --- enum declarations ---
        (
            "type Color is enum RED, GREEN, BLUE\n",
            "from enum import Enum\nclass Color(Enum):\n    RED = 0\n    GREEN = 1\n    BLUE = 2\n    def __str__(self): return self.name\n    __repr__ = __str__\nRED = Color.RED\nGREEN = Color.GREEN\nBLUE = Color.BLUE\n",
        ),
        # block-form enum (one member per line) -> same output as inline form
        (
            "type Color is enum:\n    RED\n    GREEN\n    BLUE\n",
            "from enum import Enum\nclass Color(Enum):\n    RED = 0\n    GREEN = 1\n    BLUE = 2\n    def __str__(self): return self.name\n    __repr__ = __str__\nRED = Color.RED\nGREEN = Color.GREEN\nBLUE = Color.BLUE\n",
        ),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            output = translate(code)
            if output == expected:
                label = code.splitlines()[0]
                print(f"  PASS: {label!r}...")
                passed += 1
            else:
                label = code.splitlines()[0]
                print(f"  MISMATCH: {label!r}...")
                print(f"    expected: {expected!r}")
                print(f"    got:      {output!r}")
                failed += 1
        except Exception as e:
            label = code.splitlines()[0]
            print(f"  ERROR: {label!r}... -> {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Translate Adascript (.ady) to Python")
    parser.add_argument("file", nargs="?", help="source file to translate (reads stdin if omitted)")
    parser.add_argument("rest", nargs="*", help="arguments passed to the compiled program")
    parser.add_argument("-c", action="store_true", help="compile and run the generated Python file")
    parser.add_argument("--test", action="store_true", help="run built-in tests")
    args = parser.parse_args()
    if args.test:
        sys.exit(run_tests())
    else:
        main(args)

