#!/usr/bin/env python3
"""Python 3.14 Compound Statement Parser — to_py() methods.

Grammar definitions are in py3compound_stmt.py. This module adds to_py() rendering
methods to the grammar node classes.
"""

import sys, os
_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "HPARSEC"))
sys.path.insert(0, os.path.join(_dir, "..", "ADASCRIPT_GRAMMAR"))

from py3compound_stmt import *  # noqa: F403 — grammar definitions
from hek_tokenize import RichNL
from hek_parsec import method, ParserState
from hek_helpers import INDENT_STR, _ind, _richnl_lines, _block_inline_header_comment, _block_last_stmt
import hek_py3_stmt  # noqa: F401 — registers stmt to_py() methods
from hek_py3_expr import _bash_to_py  # bash placeholder resolution

###############################################################################
# to_py() methods
###############################################################################


# NL parser node wraps a RichNL; delegate rendering to RichNL.to_py()
@method(NL)
def to_py(self, indent=0):
    """NL: delegate to the wrapped RichNL's rendering."""
    rn = RichNL.extract_from(self)
    return rn.to_py() if rn is not None else ''

@method(block)
def to_py(self, indent=0):
    """block: NEWLINE INDENT NL* (statement NL*)+ DEDENT

    Emits body lines joined by newlines. Blank lines and comments between
    statements (stored as RichNL in the NL[:] Several_Times after each
    statement) are preserved with correct indentation.
    """
    lines = []
    for node in self.nodes:
        tname = type(node).__name__
        if tname == "Fmap":
            continue
        if tname == "Several_Times":
            for seq in node.nodes:
                if type(seq).__name__ == "Sequence_Parser" and hasattr(seq, "nodes"):
                    stmt_node = None
                    nl_several = None
                    for child in seq.nodes:
                        if child is None:
                            continue
                        if type(child).__name__ == "Several_Times":
                            nl_several = child
                        elif stmt_node is None:
                            stmt_node = child
                    # Emit the statement
                    if stmt_node is not None and hasattr(stmt_node, "to_py"):
                        try:
                            lines.append(stmt_node.to_py(indent))
                        except TypeError:
                            raw = stmt_node.to_py()
                            if '\n' in raw:
                                # Indent the statement, not the lines inside a
                                # multi-line string literal it may contain --
                                # those belong to the string's own contents.
                                head, _, rest = raw.partition('\n')
                                lines.append(_ind(indent) + head)
                                lines.extend(rest.split('\n'))
                            else:
                                lines.append(_ind(indent) + raw)
                    # Emit trailing NLs (blank lines / comments) after the statement
                    if nl_several is not None:
                        for nl_node in nl_several.nodes:
                            trivia = _richnl_lines(nl_node)
                            if trivia is not None:
                                lines.extend(trivia)
                else:
                    inner = seq
                    if inner is not None and hasattr(inner, "to_py"):
                        try:
                            lines.append(inner.to_py(indent))
                        except TypeError:
                            lines.append(_ind(indent) + inner.to_py())
        elif hasattr(node, "to_py"):
            try:
                lines.append(node.to_py(indent))
            except TypeError:
                lines.append(_ind(indent) + node.to_py())
    # Trailing blank lines in a block belong to the inter-statement spacing
    # of the outer scope. We emit them here so callers can decide what to do.
    return "\n".join(lines)


@method(statement)
def to_py(self, indent=0):
    """statement: compound_stmt | stmt_line"""
    inner = self.nodes[0]
    try:
        return inner.to_py(indent)
    except TypeError:
        return _ind(indent) + inner.to_py()


# Suite (block | stmt_line) helper: block.to_py accepts indent, stmt_line.to_py
# does not — fall back to indent-prefixed plain emission.
def _suite_to_py(node, indent):
    try:
        return node.to_py(indent)
    except TypeError:
        raw = node.to_py()
        if "\n" in raw:
            # Only the statement is indented; a multi-line string literal
            # inside it keeps the layout it was written with.
            head, _, rest = raw.partition("\n")
            return _ind(indent) + head + "\n" + rest
        return _ind(indent) + raw


# --- if / elif / else ---
@method(elif_clause)
def to_py(self, indent=0):
    """elif_clause: 'elif' named_expression ':' suite"""
    cond = self.nodes[0].to_py()
    hc = _block_inline_header_comment(self.nodes[1])
    body = _suite_to_py(self.nodes[1], indent + 1)
    return f"{_ind(indent)}elif {cond}:{hc}\n{body}"


@method(else_clause)
def to_py(self, indent=0):
    """else_clause: 'else' ':' suite"""
    hc = _block_inline_header_comment(self.nodes[0])
    body = _suite_to_py(self.nodes[0], indent + 1)
    return f"{_ind(indent)}else:{hc}\n{body}"


@method(if_stmt)
def to_py(self, indent=0):
    """if_stmt: 'if' named_expression ':' suite ('elif' ...)* ('else' ...)?"""
    cond = self.nodes[0].to_py()
    hc = _block_inline_header_comment(self.nodes[1])
    body = _suite_to_py(self.nodes[1], indent + 1)
    result = f"{_ind(indent)}if {cond}:{hc}\n{body}"
    # Process remaining nodes (elif/else clauses from Several_Times)
    for node in self.nodes[2:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            if hasattr(seq, "nodes") and seq.nodes:
                clause = seq.nodes[0] if hasattr(seq.nodes[0], "to_py") else seq
            else:
                clause = seq
            if hasattr(clause, "to_py"):
                try:
                    result += "\n" + clause.to_py(indent)
                except TypeError:
                    result += "\n" + _ind(indent) + clause.to_py()
    return result


# --- while ---
@method(while_stmt)
def to_py(self, indent=0):
    """while_stmt: 'while' named_expression ':' suite ('else' ':' block)?"""
    cond = self.nodes[0].to_py()
    hc = _block_inline_header_comment(self.nodes[1])
    body = _suite_to_py(self.nodes[1], indent + 1)
    result = f"{_ind(indent)}while {cond}:{hc}\n{body}"
    for node in self.nodes[2:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            clause = (
                seq.nodes[0]
                if hasattr(seq, "nodes")
                and seq.nodes
                and hasattr(seq.nodes[0], "to_py")
                else seq
            )
            if hasattr(clause, "to_py"):
                try:
                    result += "\n" + clause.to_py(indent)
                except TypeError:
                    pass
    return result


# --- for ---
@method(for_target)
def to_py(self):
    """for_target: IDENTIFIER (',' IDENTIFIER)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


@method(for_stmt)
def to_py(self, indent=0):
    """for_stmt: 'for' for_target 'in' star_expressions ':' block ('else' ...)?"""
    target = self.nodes[0].to_py()
    iterable = self.nodes[1].to_py()
    hc = _block_inline_header_comment(self.nodes[2])
    body = self.nodes[2].to_py(indent + 1)
    result = f"{_ind(indent)}for {target} in {iterable}:{hc}\n{body}"
    for node in self.nodes[3:]:
        if not hasattr(node, "nodes") or not node.nodes:
            continue
        for seq in node.nodes:
            clause = (
                seq.nodes[0]
                if hasattr(seq, "nodes")
                and seq.nodes
                and hasattr(seq.nodes[0], "to_py")
                else seq
            )
            if hasattr(clause, "to_py"):
                try:
                    result += "\n" + clause.to_py(indent)
                except TypeError:
                    pass
    return result


# --- try / except / finally ---
@method(except_clause)
def to_py(self, indent=0):
    """except_clause: 'except' expression ('as' IDENTIFIER)? ':' block"""
    exc = self.nodes[0].to_py()
    result = f"except {exc}"
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    result += f" as {seq.nodes[0].to_py()}"
            continue
        if hasattr(node, "to_py") and type(node).__name__ == "block":
            hc = _block_inline_header_comment(node)
            try:
                body = node.to_py(indent + 1)
            except TypeError:
                body = _ind(indent + 1) + node.to_py()
            return f"{_ind(indent)}{result}:{hc}\n{body}"
    return f"{_ind(indent)}{result}:"


@method(except_star_clause)
def to_py(self, indent=0):
    """except_star_clause: 'except' '*' expression ('as' IDENTIFIER)? ':' block"""
    exc = self.nodes[1].to_py()
    result = f"except* {exc}"
    for node in self.nodes[2:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    result += f" as {seq.nodes[0].to_py()}"
            continue
        if hasattr(node, "to_py") and type(node).__name__ == "block":
            hc = _block_inline_header_comment(node)
            try:
                body = node.to_py(indent + 1)
            except TypeError:
                body = _ind(indent + 1) + node.to_py()
            return f"{_ind(indent)}{result}:{hc}\n{body}"
    return f"{_ind(indent)}{result}:"


@method(except_bare)
def to_py(self, indent=0):
    """except_bare: 'except' ':' block"""
    hc = _block_inline_header_comment(self.nodes[0])
    body = self.nodes[0].to_py(indent + 1)
    return f"{_ind(indent)}except:{hc}\n{body}"


@method(finally_clause)
def to_py(self, indent=0):
    """finally_clause: 'finally' ':' block"""
    hc = _block_inline_header_comment(self.nodes[0])
    body = self.nodes[0].to_py(indent + 1)
    return f"{_ind(indent)}finally:{hc}\n{body}"


def _extract_clauses(nodes, indent):
    """Extract except/else/finally clauses from flattened Several_Times nodes."""
    parts = []
    for node in nodes:
        if not hasattr(node, "nodes"):
            if hasattr(node, "to_py"):
                try:
                    parts.append(node.to_py(indent))
                except TypeError:
                    parts.append(_ind(indent) + node.to_py())
            continue
        if type(node).__name__ == "Several_Times":
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    inner = seq.nodes[0] if len(seq.nodes) == 1 else seq
                    if hasattr(inner, "to_py"):
                        try:
                            parts.append(inner.to_py(indent))
                        except TypeError:
                            parts.append(_ind(indent) + inner.to_py())
                elif hasattr(seq, "to_py"):
                    try:
                        parts.append(seq.to_py(indent))
                    except TypeError:
                        parts.append(_ind(indent) + seq.to_py())
        elif hasattr(node, "to_py"):
            try:
                parts.append(node.to_py(indent))
            except TypeError:
                parts.append(_ind(indent) + node.to_py())
    return parts


@method(try_except)
def to_py(self, indent=0):
    """try_except: 'try' ':' block (except_clause | except_star | except_bare)+
    ('else' ':' block)? ('finally' ':' block)?"""
    hc = _block_inline_header_comment(self.nodes[0])
    body = self.nodes[0].to_py(indent + 1)
    result = f"{_ind(indent)}try:{hc}\n{body}"
    try:
        result += "\n" + self.nodes[1].to_py(indent)
    except TypeError:
        result += "\n" + _ind(indent) + self.nodes[1].to_py()
    clauses = _extract_clauses(self.nodes[2:], indent)
    for c in clauses:
        result += "\n" + c
    return result


@method(try_finally)
def to_py(self, indent=0):
    """try_finally: 'try' ':' block 'finally' ':' block"""
    hc = _block_inline_header_comment(self.nodes[0])
    body = self.nodes[0].to_py(indent + 1)
    fin = self.nodes[1].to_py(indent)
    return f"{_ind(indent)}try:{hc}\n{body}\n{fin}"


@method(try_stmt)
def to_py(self, indent=0):
    """try_stmt: try_except | try_finally"""
    return self.nodes[0].to_py(indent)


# --- with ---
@method(with_item)
def to_py(self):
    """with_item: expression ('as' star_expression)?"""
    expr = self.nodes[0].to_py()
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    return f"{expr} as {seq.nodes[0].to_py()}"
    return expr


@method(with_own_stmt)
def to_py(self, indent=0):
    """with own x = expr: block  ->  x = expr / try: body / finally: del x

    Node layout (ikw tokens invisible):
      nodes[0] = IDENTIFIER, nodes[1] = V_EQUAL, nodes[2] = expression, nodes[3] = block
    """
    name_node = expr_node = block_node = None
    for node in self.nodes:
        tname = type(node).__name__
        if tname == "IDENTIFIER" and name_node is None:
            name_node = node
        elif tname == "block":
            block_node = node
        elif name_node is not None and expr_node is None and tname not in ("Fmap", "Filter"):
            val = getattr(node, "node", None)
            if isinstance(val, str) and val == "=":
                continue   # skip visible V_EQUAL
            expr_node = node
    name = name_node.to_py() if name_node else "_own_var"
    expr = expr_node.to_py() if expr_node else "None"
    body = _suite_to_py(block_node, indent + 1) if block_node else f"{_ind(indent + 1)}pass"
    ind = _ind(indent)
    ind1 = _ind(indent + 1)
    return (
        f"{ind}{name} = {expr}\n"
        f"{ind}try:\n"
        f"{body}\n"
        f"{ind}finally:\n"
        f"{ind1}del {name}"
    )


@method(with_stmt)
def to_py(self, indent=0):
    """with_stmt: 'with' with_item (',' with_item)* ':' block"""
    items = [self.nodes[0].to_py()]
    block_node = None
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times":
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    item = seq.nodes[0]
                    if hasattr(item, "to_py"):
                        items.append(item.to_py())
        elif hasattr(node, "to_py"):
            block_node = node
    body = ""
    hc = ""
    if block_node:
        hc = _block_inline_header_comment(block_node)
        try:
            body = block_node.to_py(indent + 1)
        except TypeError:
            body = _ind(indent + 1) + block_node.to_py()
    return f"{_ind(indent)}with {', '.join(items)}:{hc}\n{body}"


@method(with_own_stmt)
def to_py(self, indent=0):
    """with own x = expr: block  ->  x = expr; try: body; finally: del x

    Node layout (ikw tokens consumed/invisible):
      nodes[0] = IDENTIFIER
      nodes[1] = V_EQUAL (visible)
      nodes[2] = expression
      nodes[3] = block
    """
    ind = _ind(indent)
    ind1 = _ind(indent + 1)
    name_node = None
    expr_node = None
    block_node = None
    for node in self.nodes:
        tname = type(node).__name__
        if tname == "IDENTIFIER" and name_node is None:
            name_node = node
        elif tname == "block":
            block_node = node
        elif name_node is not None and expr_node is None and tname not in ("Fmap", "V_EQUAL"):
            expr_node = node
    name = name_node.to_py() if name_node and hasattr(name_node, "to_py") else str(name_node)
    expr = expr_node.to_py() if expr_node and hasattr(expr_node, "to_py") else ""
    hc = _block_inline_header_comment(block_node) if block_node else ""
    body = block_node.to_py(indent + 1) if block_node else f"{ind1}pass"
    return f"{ind}{name} = {expr}\n{ind}try:{hc}\n{body}\n{ind}finally:\n{ind1}del {name}"


@method(with_stmt_paren)
def to_py(self, indent=0):
    """with_stmt_paren: 'with' '(' NL* with_item (',' NL* with_item)* ','? NL* ')' ':' block"""
    items = []
    block_node = None
    for node in self.nodes:
        tname = type(node).__name__
        if tname == "with_item":
            items.append(node.to_py())
        elif tname == "Several_Times":
            for seq in node.nodes:
                sname = type(seq).__name__
                if sname == "Sequence_Parser":
                    # (COMMA + NL[:] + with_item) sequence
                    for child in seq.nodes:
                        if type(child).__name__ == "with_item":
                            items.append(child.to_py())
                elif sname == "with_item":
                    items.append(seq.to_py())
        elif tname == "block":
            block_node = node
    body = ""
    hc = ""
    if block_node:
        hc = _block_inline_header_comment(block_node)
        try:
            body = block_node.to_py(indent + 1)
        except TypeError:
            body = _ind(indent + 1) + block_node.to_py()
    ind1 = _ind(indent + 1)
    items_str = (",\n" + ind1).join(items)
    return f"{_ind(indent)}with (\n{ind1}{items_str},\n{_ind(indent)}):{hc}\n{body}"


# --- case / when ---
@method(pattern_literal)
def to_py(self):
    """pattern_literal: NUMBER | STRING | 'None' | 'True' | 'False'"""
    return (
        self.nodes[0].to_py() if hasattr(self.nodes[0], "to_py") else str(self.nodes[0])
    )


@method(pattern_capture)
def to_py(self, prec=None):
    """pattern_capture: IDENTIFIER

    Handles all IDENTIFIER uses (plain names, tick attributes, bash placeholders).
    pattern_capture = IDENTIFIER in the grammar, so this method is the last writer
    on the shared class and must include every resolution that IDENTIFIER.to_py
    needs — tick attributes, bashisms, and normal name pass-through.
    """
    name = (
        self.nodes[0].to_py() if hasattr(self.nodes[0], "to_py") else str(self.nodes[0])
    )
    # Resolve tick attributes: Type__tick__First -> first value of subrange/enum
    if "__tick__" in name:
        type_name, _, attr = name.partition("__tick__")
        info = ParserState.tick_types.get(type_name)
        if info and attr in info:
            return str(info[attr])
        if attr == "Choice":
            return f"random.choice(list({type_name}))"
        elif attr == "Range":
            return f"list({type_name})"
        elif attr == "Next":
            return type_name + ".__class__((" + type_name + ".value + 1))"
        elif attr == "Prev":
            return type_name + ".__class__((" + type_name + ".value - 1))"
        elif attr == "len" or attr == "Length":
            return f"len({type_name})"
        elif attr == "Size":
            return f"len({type_name})"
    # Qualify known enum members: bare names are capture patterns in Python
    # match/case, but dotted names are value patterns. e.g. cmdArgument ->
    # Kind_T.cmdArgument so 'case Kind_T.cmdArgument:' matches by value.
    for enum_type, info in ParserState.tick_types.items():
        members = info.get("members")
        if members and name in members:
            return f"{enum_type}.{name}"
    if name == "stdin":
        ParserState.nim_imports.add("import sys")
        return "sys.stdin"
    return name


@method(pattern_wildcard)
def to_py(self):
    """pattern_wildcard: '_'"""
    return "_"


@method(pattern_others)
def to_py(self):
    """pattern_others: 'others' (default branch) -> Nim: 'else'"""
    return "_"


@method(pattern_range)
def to_py(self):
    """pattern_range: expression '..' expression (range pattern) -> Nim: 'lo .. hi'"""
    lo = self.nodes[0].to_py()
    hi = self.nodes[-1].to_py()
    return f"{lo} .. {hi}"


@method(pattern_group)
def to_py(self):
    """pattern_group: '(' pattern ')'"""
    return f"({self.nodes[0].to_py()})"


@method(pattern_star)
def to_py(self):
    """pattern_star: '*' (capture | wildcard) -> Python: '*name' or '*_'"""
    name_node = self.nodes[1] if len(self.nodes) > 1 else self.nodes[0]
    inner = name_node.to_py() if hasattr(name_node, "to_py") else str(name_node)
    return f"*{inner}"


@method(pattern_seq_item)
def to_py(self):
    """pattern_seq_item: pattern_star | pattern"""
    return self.nodes[0].to_py()


@method(pattern_empty_seq)
def to_py(self):
    return "[]"


@method(pattern_sequence)
def to_py(self):
    """pattern_sequence: '[' pattern_seq_item (',' pattern_seq_item)* ','? ']'"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    parts.append(seq.nodes[0].to_py())
    return f"[{', '.join(parts)}]"


@method(pattern_or)
def to_py(self):
    """pattern_or: pattern ('|' pattern)+"""
    # Similar to binop — base + Several_Times[(op, pattern)]
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                    parts.append(seq.nodes[1].to_py())
    return " | ".join(parts)


@method(pattern_value)
def to_py(self):
    """pattern_value: IDENTIFIER ('.' IDENTIFIER)+"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                    parts.append(seq.nodes[1].to_py())
    return ".".join(parts)


@method(keyword_pattern)
def to_py(self):
    """keyword_pattern: IDENTIFIER '=' pattern"""
    return f"{self.nodes[0].to_py()}={self.nodes[1].to_py()}"


@method(pattern_class_arg)
def to_py(self):
    """pattern_class_arg: keyword_pattern | pattern"""
    return self.nodes[0].to_py()


@method(pattern_class)
def to_py(self):
    """pattern_class: IDENTIFIER '(' (pattern_class_arg (',' pattern_class_arg)*)? ')'"""
    name = self.nodes[0].to_py()
    patterns = []
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes"):
                    # seq is Sequence_Parser: [pattern_class_arg, Several_Times[(,pattern_class_arg)...]]
                    patterns.append(seq.nodes[0].to_py())
                    for inner in seq.nodes[1:]:
                        if type(inner).__name__ == "Several_Times" and inner.nodes:
                            for sub in inner.nodes:
                                if hasattr(sub, "nodes") and sub.nodes:
                                    patterns.append(sub.nodes[0].to_py())
                elif hasattr(seq, "to_py"):
                    patterns.append(seq.to_py())
    return f"{name}({', '.join(patterns)})"


@method(pattern_mapping)
def to_py(self):
    """pattern_mapping: '{' (expression ':' pattern) (',' expression ':' pattern)* ','? '}'"""
    pairs = []

    def _extract_pair(nodes):
        """Extract key: value from [expr, Fmap(':'), pattern] sequence."""
        key = val = None
        for n in nodes:
            tname = type(n).__name__
            if (
                tname == "Fmap"
                and hasattr(n, "nodes")
                and n.nodes
                and n.nodes[0] == ":"
            ):
                continue
            elif key is None and hasattr(n, "to_py"):
                key = n.to_py()
            elif hasattr(n, "to_py"):
                val = n.to_py()
        if key and val:
            pairs.append(f"{key}: {val}")

    for child in self.nodes:
        tname = type(child).__name__
        if tname == "Sequence_Parser" and hasattr(child, "nodes"):
            _extract_pair(child.nodes)
        elif tname == "Several_Times":
            for seq in child.nodes:
                if hasattr(seq, "nodes"):
                    _extract_pair(seq.nodes)
    return "{" + ", ".join(pairs) + "}"


@method(base_pattern)
def to_py(self):
    """base_pattern: literal | wildcard | group | mapping | sequence | value | class | capture"""
    return self.nodes[0].to_py()


@method(pattern_as)
def to_py(self):
    """pattern_as: base_pattern 'as' IDENTIFIER"""
    pat = self.nodes[0].to_py()
    name = self.nodes[1].to_py()
    return f"{pat} as {name}"


@method(pattern)
def to_py(self):
    """pattern: or_pattern | as_pattern | base_pattern"""
    return self.nodes[0].to_py()


@method(case_guard)
def to_py(self):
    """case_guard: 'if' named_expression"""
    return f" if {self.nodes[0].to_py()}"


@method(when_clause)
def to_py(self, indent=0):
    """case_clause: 'case' pattern ('if' guard)? ':' block"""
    pat = self.nodes[0].to_py()
    guard = ""
    block_node = None
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "to_py"):
                    guard = seq.to_py()
        elif hasattr(node, "to_py"):
            block_node = node
    hc = _block_inline_header_comment(block_node) if block_node else ""
    body = _suite_to_py(block_node, indent + 1) if block_node else ""
    return f"{_ind(indent)}case {pat}{guard}:{hc}\n{body}"


def _block_node_of_py(when_node):
    """Extract the block (or stmt_line) body node from a when_clause node."""
    for n in when_node.nodes[1:]:
        if type(n).__name__ in ("block", "stmt_line"):
            return n
        if type(n).__name__ in ("Several_Times", "case_guard", "Filter", "Fmap"):
            continue
        if hasattr(n, "to_py"):
            return n
    for n in reversed(when_node.nodes):
        tname = type(n).__name__
        if tname not in ("case_guard", "Several_Times", "Filter", "Fmap") and hasattr(n, "to_py"):
            return n
    return None


def _extract_branches_py(case_node):
    """Yield (pat_node, block_node, guard_node_or_None) for each branch in a case_stmt."""
    for node in case_node.nodes[1:]:
        tname = type(node).__name__
        if tname == "when_clause":
            pat = node.nodes[0]
            blk = _block_node_of_py(node)
            guard = None
            for n in node.nodes[1:]:
                if type(n).__name__ == "case_guard":
                    guard = n
                elif type(n).__name__ == "Several_Times":
                    for inner in n.nodes:
                        if type(inner).__name__ == "case_guard":
                            guard = inner
            yield pat, blk, guard
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "when_clause":
                    pat = seq.nodes[0]
                    blk = _block_node_of_py(seq)
                    guard = None
                    for n in seq.nodes[1:]:
                        if type(n).__name__ == "case_guard":
                            guard = n
                        elif type(n).__name__ == "Several_Times":
                            for inner in n.nodes:
                                if type(inner).__name__ == "case_guard":
                                    guard = inner
                    yield pat, blk, guard
                elif stname == "Sequence_Parser" and hasattr(seq, "nodes"):
                    pat_node = None
                    blk_node = None
                    guard_node = None
                    for child in seq.nodes:
                        cname = type(child).__name__
                        if cname in ("block", "stmt_line"):
                            blk_node = child
                        elif cname == "case_guard":
                            guard_node = child
                        elif cname == "Several_Times":
                            for inner in child.nodes:
                                if type(inner).__name__ == "case_guard":
                                    guard_node = inner
                        elif cname not in ("Filter", "Fmap") and hasattr(child, "to_py"):
                            if pat_node is None:
                                pat_node = child
                    if pat_node is not None:
                        yield pat_node, blk_node, guard_node


def _pat_regex_info_py(pat_node):
    """Return (pattern, flags) if pat_node is a regex literal, else None."""
    val = getattr(pat_node, 'node', None)
    if isinstance(val, str) and val.startswith('/'):
        last = val.rfind('/')
        if last > 0:
            return val[1:last], val[last + 1:]
    return None


@method(case_stmt)
def to_py(self, indent=0):
    """case_stmt: 'case' expression ':' when_clause+ — Adascript case/when"""
    subject = self.nodes[0].to_py()

    # If any branch uses a regex pattern, desugar to if/elif/else
    if any(_pat_regex_info_py(p) is not None for p, _, _ in _extract_branches_py(self)):
        from hek_py3_expr import _ensure_pymatch_helper, _py_re_flags
        _ensure_pymatch_helper()
        result = ""
        keyword = "if"
        for pat_node, block_node, guard_node in _extract_branches_py(self):
            hc = _block_inline_header_comment(block_node) if block_node else ""
            body = _suite_to_py(block_node, indent + 1) if block_node else ""
            pat_py = pat_node.to_py() if hasattr(pat_node, "to_py") else str(pat_node)
            if pat_py in ("others", "_"):
                result += f"\n{_ind(indent)}else:{hc}\n{body}"
                continue
            rinfo = _pat_regex_info_py(pat_node)
            if rinfo is not None:
                pat, flags = rinfo
                has_g = 'g' in flags
                flags_val = _py_re_flags(flags)
                safe_pat = pat.replace("'", "\\'")
                if has_g:
                    if flags_val != "0":
                        cond = f"_re_mod.findall(r'{safe_pat}', {subject}, {flags_val})"
                    else:
                        cond = f"_re_mod.findall(r'{safe_pat}', {subject})"
                else:
                    if flags_val != "0":
                        cond = f"_pymatch({subject}, r'{safe_pat}', {flags_val})"
                    else:
                        cond = f"_pymatch({subject}, r'{safe_pat}')"
            else:
                cond = f"{subject} == {pat_py}"
            if guard_node is not None:
                cond = f"{cond} and {guard_node.nodes[0].to_py()}"
            result += f"\n{_ind(indent)}{keyword} {cond}:{hc}\n{body}"
            keyword = "elif"
        return result.lstrip("\n")

    result = f"{_ind(indent)}match {subject}:"
    for node in self.nodes[1:]:
        tname = type(node).__name__
        if tname == "when_clause":
            result += "\n" + node.to_py(indent + 1)
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "when_clause":
                    result += "\n" + seq.to_py(indent + 1)
                elif stname == "Sequence_Parser" and hasattr(seq, "nodes"):
                    result += "\n" + _case_from_seq(seq, indent + 1)
    return result


def _case_from_seq(seq, indent):
    """Reconstruct a case clause from a flattened Sequence_Parser [pattern, guard?, body]."""
    pat = ""
    guard = ""
    block_node = None
    pat_seen = False
    for child in seq.nodes:
        tname = type(child).__name__
        if tname in ("block", "stmt_line"):
            block_node = child
        elif tname == "Several_Times":
            for inner in child.nodes:
                if hasattr(inner, "to_py"):
                    guard = inner.to_py()
        elif tname == "case_guard":
            guard = child.to_py()
        elif not pat_seen:
            pat = child.to_py()
            pat_seen = True
    hc = _block_inline_header_comment(block_node) if block_node else ""
    body = _suite_to_py(block_node, indent + 1) if block_node else ""
    return f"{_ind(indent)}case {pat}{guard}:{hc}\n{body}"


# --- Python 3.10+ match/case ---

@method(case_clause)
def to_py(self, indent=0):
    """case_clause: 'case' pattern guard? ':' suite — Python match/case branch"""
    pat = self.nodes[0].to_py()
    guard = ""
    block_node = None
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "to_py"):
                    guard = seq.to_py()
        elif hasattr(node, "to_py"):
            block_node = node
    hc = _block_inline_header_comment(block_node) if block_node else ""
    body = _suite_to_py(block_node, indent + 1) if block_node else ""
    return f"{_ind(indent)}case {pat}{guard}:{hc}\n{body}"


@method(match_stmt)
def to_py(self, indent=0):
    """match_stmt: 'match' expression ':' NEWLINE INDENT case_clause+ DEDENT"""
    subject = self.nodes[0].to_py()
    result = f"{_ind(indent)}match {subject}:"
    for node in self.nodes[1:]:
        tname = type(node).__name__
        if tname == "case_clause":
            result += "\n" + node.to_py(indent + 1)
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "case_clause":
                    result += "\n" + seq.to_py(indent + 1)
                elif stname == "Sequence_Parser" and hasattr(seq, "nodes"):
                    result += "\n" + _case_from_seq(seq, indent + 1)
    return result


# --- Function parameters ---
@method(param_plain)
def to_py(self):
    """param_plain: IDENTIFIER (':' expression)? ('=' expression)?"""
    name = self.nodes[0].to_py()
    annotation = ""
    default = ""
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if not hasattr(seq, "nodes") or len(seq.nodes) < 2:
                    continue
                # seq.nodes[0] is the visible op (V_COLON or V_EQUAL), nodes[1] is the value
                op_node = seq.nodes[0]
                val_node = seq.nodes[1]
                # Get the operator string
                op_str = ""
                if hasattr(op_node, "node"):
                    op_str = op_node.node
                elif hasattr(op_node, "nodes") and op_node.nodes:
                    op_str = op_node.nodes[0] if isinstance(op_node.nodes[0], str) else ""
                if op_str == ":":
                    annotation = f": {val_node.to_py()}"
                elif op_str == "=":
                    default = f"={val_node.to_py()}"
    # PEP 8: spaces around = when annotation present
    if annotation and default:
        default = " " + default[0] + " " + default[1:]  # "=val" -> "= val"
    return f"{name}{annotation}{default}"


@method(param_star)
def to_py(self):
    """param_star: '*' (IDENTIFIER (':' expression)?)?"""
    # SSTAR is visible, nodes[0] is '*'
    result = "*"
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes"):
                    # First child is IDENTIFIER
                    result += seq.nodes[0].to_py()
                    # Check for annotation
                    for inner in seq.nodes[1:]:
                        if type(inner).__name__ == "Several_Times" and inner.nodes:
                            for ann in inner.nodes:
                                if hasattr(ann, "nodes") and len(ann.nodes) >= 2:
                                    result += f": {ann.nodes[1].to_py()}"
                elif hasattr(seq, "to_py"):
                    val = seq.to_py()
                    if val != "*":
                        result += val
    return result


@method(param_dstar)
def to_py(self):
    """param_dstar: '**' IDENTIFIER (':' expression)?"""
    name = self.nodes[0].to_py()
    annotation = ""
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and len(seq.nodes) >= 2:
                    annotation = f": {seq.nodes[1].to_py()}"
    return f"**{name}{annotation}"


@method(param_slash)
def to_py(self):
    """param_slash: '/'"""
    return "/"


@method(param)
def to_py(self):
    """param: param_dstar | param_star | param_slash | param_plain"""
    return self.nodes[0].to_py()


@method(param_list)
def to_py(self):
    """param_list: param (',' param)* ','?"""
    parts = [self.nodes[0].to_py()]
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times" and node.nodes:
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    parts.append(seq.nodes[0].to_py())
    return ", ".join(parts)


# --- Decorators ---
@method(decorator)
def to_py(self, indent=0):
    """decorator: '@' expression NEWLINE"""
    decorator=self.nodes[0].to_py()
    if decorator == 'virtual':
        return ''
    if decorator == 'contextmanager':
        ParserState.nim_imports.add('import contextlib')
        return f"{_ind(indent)}@contextlib.contextmanager"
    return f"{_ind(indent)}@{decorator}"


@method(decorators)
def to_py(self, indent=0):
    """decorators: decorator+"""
    lines = []
    for node in self.nodes:
        if hasattr(node, "to_py"):
            try:
                lines.append(node.to_py(indent))
            except TypeError:
                lines.append(_ind(indent) + "@" + node.to_py())
    return "\n".join(lines)


# --- return_annotation ---
@method(return_annotation)
def to_py(self):
    """return_annotation: '->' expression"""
    # V_ARROW is visible, so nodes = [V_ARROW, expression]
    return f" -> {self.nodes[1].to_py()}"


def _branch_blocks(node, out):
    """The block nodes belonging directly to one compound statement."""
    for child in (getattr(node, "nodes", None) or []):
        tname = type(child).__name__
        if tname == "block":
            out.append(child)
        elif tname in ("Several_Times", "Sequence_Parser", "Filter", "Fmap",
                       "elif_clause", "else_clause"):
            _branch_blocks(child, out)


def _mark_implicit_returns(stmt, depth=0):
    """Mark the statements whose value is the function's implicit return.

    A bare expression is that value.  An `if`/`elif`/`else` in tail position
    returns whichever branch runs, so each branch's own last statement is
    marked in turn, recursively, since branches nest.

    Marking beats rewriting the rendered text: the keyword then precedes the
    whole statement, so a multi-line string literal stays intact instead of
    having `return` spliced into its middle.
    """
    import hek_py3_stmt as _stmt
    if stmt is None or depth > 8:
        return
    tname = type(stmt).__name__
    if tname == "stmt_line":
        inner = stmt.nodes[0] if getattr(stmt, "nodes", None) else None
        if inner is not None and type(inner).__name__ == "expressions":
            _stmt.RETURN_NODES.add(id(stmt))
        return
    if tname == "if_stmt":
        blocks = []
        _branch_blocks(stmt, blocks)
        for blk in blocks:
            _mark_implicit_returns(_block_last_stmt(blk), depth + 1)


# --- Python's `global` statement -------------------------------------------
#
# Assigning a module-level name inside a function binds a *local* in Python,
# silently leaving the global untouched.  Nim has no such rule, so Adascript
# that is correct on the Nim backend needs a `global` declaration added here.

_MODULE_GLOBALS = []


def _simple_name(text):
    """TEXT if it is a bare identifier, else None."""
    import re as _re_g
    text = (text or "").strip()
    return text if _re_g.match(r'^[A-Za-z_]\w*$', text) else None


def _bound_names(node):
    """The names one statement binds, as written (no rendering of values)."""
    tname = type(node).__name__
    nodes = getattr(node, "nodes", None) or []
    raw = []
    if tname == "assign_stmt":
        # nodes: [target, Several_Times[('=', x), ...]] -- the last x is the
        # value, every earlier one is another target of a chained assignment.
        seqs = []
        for sub in nodes[1:]:
            seqs.extend(getattr(sub, "nodes", None) or [])
        raw.append(nodes[0].to_py())
        for seq in seqs[:-1]:
            if getattr(seq, "nodes", None) and len(seq.nodes) >= 2:
                raw.append(seq.nodes[1].to_py())
    elif tname == "aug_assign_stmt":
        raw.append(nodes[0].to_py())
    elif tname == "ann_assign_stmt":
        raw.append(nodes[0].to_py())
    elif tname in ("decl_ann_assign_stmt", "own_stmt"):
        raw.append(nodes[1].to_py() if len(nodes) > 1 else "")
    elif tname == "for_stmt":
        raw.extend(c.to_py() for c in nodes
                   if type(c).__name__ == "for_target")
    return [n for n in (_simple_name(t) for t in raw) if n]


def _walk_scope(node, assigned, declared, depth=0):
    """Collect what a function body assigns and what it declares local.

    Does not descend into a nested def or class: each gets its own `global`
    when it is emitted.
    """
    tname = type(node).__name__
    if depth and tname in ("func_def", "async_func_def", "class_def"):
        return
    if tname in ("decl_ann_assign_stmt", "own_stmt", "ann_assign_stmt",
                 "decl_tuple_unpack"):
        declared.update(_bound_names(node))
        return
    if tname in ("assign_stmt", "aug_assign_stmt"):
        assigned.update(_bound_names(node))
        return
    if tname == "for_stmt":
        assigned.update(_bound_names(node))
    for child in (getattr(node, "nodes", None) or []):
        _walk_scope(child, assigned, declared, depth + 1)


def register_module_globals(stmts):
    """Record the names bound at module level, for `global` in functions."""
    del _MODULE_GLOBALS[:]
    for stmt in stmts:
        queue = [stmt]
        while queue:
            node = queue.pop(0)
            tname = type(node).__name__
            if tname in ("func_def", "async_func_def", "class_def"):
                continue
            names = _bound_names(node)
            if names:
                for name in names:
                    if name not in _MODULE_GLOBALS:
                        _MODULE_GLOBALS.append(name)
                continue
            queue.extend(getattr(node, "nodes", None) or [])


def _needed_globals(block_node, params):
    """Module-level names this function assigns and must declare `global`."""
    if not _MODULE_GLOBALS or block_node is None:
        return []
    import re as _re_g
    assigned, declared = set(), set()
    _walk_scope(block_node, assigned, declared)
    # A parameter of the same name is a local by definition, and `global` on
    # one is a SyntaxError.
    for chunk in (params or "").split(","):
        name = _simple_name(_re_g.sub(r'[:=].*$', '', chunk).lstrip("*"))
        if name:
            declared.add(name)
    return [n for n in _MODULE_GLOBALS if n in assigned and n not in declared]


def _insert_into_body(body, line):
    """Put LINE at the top of BODY, after a docstring if there is one."""
    import re as _re_g
    doc = _re_g.match(r'((?:\s*"""(?:[^"]|"(?!""))*"""[ \t]*\n))', body,
                      _re_g.DOTALL)
    if doc:
        return body[:doc.end()] + line + body[doc.end():]
    return line + body


# --- Function definition ---
@method(func_def)
def to_py(self, indent=0):
    """func_def: decorators? 'def' IDENTIFIER '(' param_list? ')' ('->' expr)? ':' block"""
    decos = ""
    name = ""
    params = ""
    ret_ann = ""
    body = ""
    block_node = None

    for node in self.nodes:
        tname = type(node).__name__
        if tname == "decorators":
            decos = node.to_py(indent) + "\n"
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "decorators":
                    decos = seq.to_py(indent) + "\n"
                elif stname == "decorator":
                    decos += seq.to_py(indent) + "\n"
                elif stname == "param_list":
                    params = seq.to_py()
                elif stname == "return_annotation":
                    ret_ann = seq.to_py()
                elif stname in (
                    "param_plain",
                    "param_star",
                    "param_dstar",
                    "param_slash",
                ):
                    params = seq.to_py()
        elif tname == "IDENTIFIER":
            name = node.to_py()
        elif tname == "block":
            block_node = node
        elif tname == "param_list":
            params = node.to_py()
        elif tname == "return_annotation":
            ret_ann = node.to_py()

    hc = _block_inline_header_comment(block_node) if block_node else ""
    # A function body is an ordinary scope even inside a class, so a local
    # declared without a value does get its zero here.
    import hek_py3_stmt as _stmt
    if ret_ann and not ret_ann.strip().endswith("None"):
        _mark_implicit_returns(_block_last_stmt(block_node))
    _outer_class_depth = _stmt.CLASS_BODY_DEPTH
    _stmt.CLASS_BODY_DEPTH = 0
    try:
        body = block_node.to_py(indent + 1) if block_node else ""
    finally:
        _stmt.CLASS_BODY_DEPTH = _outer_class_depth
    # Implicit return: mark the statements that carry the function's value, so
    # the body renders with the keyword already in place.
    # Skip for -> None functions (they don't return a value)
    is_none_return = ret_ann.strip().endswith("None")
    # Implicit result variable (mirrors Nim): if the body uses `result`,
    # inject a zero-value initialiser after any leading docstring, and
    # append `return result` unless the body already ends with a return.
    import re as _re_res
    if (ret_ann and not is_none_return and
            _re_res.search(r'\bresult\b', body)):
        _t = ret_ann.strip().lstrip("->").strip()
        _zeros = {"str": '""', "int": "0", "float": "0.0", "bool": "False"}
        _zero = (_zeros.get(_t) or
                 ("[]" if _t.startswith("[") else
                  "{}" if _t.startswith("{") else "None"))
        _init = f"{_ind(indent + 1)}result = {_zero}\n"
        # Insert after a leading docstring (triple-quoted string) if present.
        _doc_m = _re_res.match(
            r'((?:\s*"""(?:[^"]|"(?!""))*"""[ \t]*\n))',
            body, _re_res.DOTALL)
        if _doc_m:
            body = body[:_doc_m.end()] + _init + body[_doc_m.end():]
        else:
            body = _init + body
        # Append implicit return unless the body already ends with a return.
        if not _re_res.search(r'^\s*return\b', body.rstrip().splitlines()[-1]):
            body = body.rstrip("\n") + f"\n{_ind(indent + 1)}return result\n"
    # Declare the module-level names this function assigns, or Python would
    # bind locals and leave the globals untouched.
    _globals = _needed_globals(block_node, params)
    if _globals:
        body = _insert_into_body(
            body, f"{_ind(indent + 1)}global {', '.join(_globals)}\n")
    return f"{decos}{_ind(indent)}def {name}({params}){ret_ann}:{hc}\n{body}"


@method(async_func_def)
def to_py(self, indent=0):
    """async_func_def: decorators? 'async' 'def' IDENTIFIER '(' params? ')' ('->' expr)? ':' block"""
    decos = ""
    name = ""
    params = ""
    ret_ann = ""
    block_node = None

    for node in self.nodes:
        tname = type(node).__name__
        if tname == "decorators":
            decos = node.to_py(indent) + "\n"
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "decorators":
                    decos = seq.to_py(indent) + "\n"
                elif stname == "decorator":
                    decos += seq.to_py(indent) + "\n"
                elif stname == "param_list":
                    params = seq.to_py()
                elif stname == "return_annotation":
                    ret_ann = seq.to_py()
                elif stname in (
                    "param_plain",
                    "param_star",
                    "param_dstar",
                    "param_slash",
                ):
                    params = seq.to_py()
        elif tname == "IDENTIFIER":
            name = node.to_py()
        elif tname == "block":
            block_node = node
        elif tname == "param_list":
            params = node.to_py()
        elif tname == "return_annotation":
            ret_ann = node.to_py()

    hc = _block_inline_header_comment(block_node) if block_node else ""
    # A function body is an ordinary scope even inside a class, so a local
    # declared without a value does get its zero here.
    import hek_py3_stmt as _stmt
    if ret_ann and not ret_ann.strip().endswith("None"):
        _mark_implicit_returns(_block_last_stmt(block_node))
    _outer_class_depth = _stmt.CLASS_BODY_DEPTH
    _stmt.CLASS_BODY_DEPTH = 0
    try:
        body = block_node.to_py(indent + 1) if block_node else ""
    finally:
        _stmt.CLASS_BODY_DEPTH = _outer_class_depth
    # Implicit return: mark the statements that carry the function's value, so
    # the body renders with the keyword already in place.
    # Skip for -> None functions (they don't return a value)
    is_none_return = ret_ann.strip().endswith("None")
    return f"{decos}{_ind(indent)}async def {name}({params}){ret_ann}:{hc}\n{body}"



# --- Type block forms (tuple, record) ---

def _extract_py_fields(block_node, indent=1):
    """Extract field declarations from a block as Python lines."""
    lines = []
    for node in block_node.nodes:
        tname = type(node).__name__
        if tname in ("Fmap", "Filter"):
            continue
        if tname == "Several_Times":
            for seq in node.nodes:
                if type(seq).__name__ == "Sequence_Parser" and hasattr(seq, "nodes"):
                    for child in seq.nodes:
                        if child is None:
                            continue
                        if hasattr(child, "to_py"):
                            cname = type(child).__name__
                            if cname == "stmt_line":
                                try:
                                    line = child.to_py(indent)
                                except TypeError:
                                    line = _ind(indent) + child.to_py()
                                stripped = line.lstrip()
                                # Strip var/let/const keywords
                                for kw in ("var ", "let ", "const "):
                                    if stripped.startswith(kw):
                                        line = line[:len(line) - len(stripped)] + stripped[len(kw):]
                                        break
                                if line.strip():
                                    lines.append(line)
    return lines


def _extract_variant_fields_py(stmt_nodes, indent):
    """Extract field declarations from variant_when stmt_line nodes for Python."""
    import re as _re
    lines = []
    for seq in stmt_nodes:
        if type(seq).__name__ == "Sequence_Parser" and hasattr(seq, "nodes"):
            for child in seq.nodes:
                if child is None:
                    continue
                cname = type(child).__name__
                if cname in ("ann_assign_stmt", "stmt_line", "Sequence_Parser"):
                    try:
                        line = child.to_py(indent)
                    except TypeError:
                        line = _ind(indent) + child.to_py()
                    stripped = line.lstrip()
                    for kw in ("var ", "let ", "const "):
                        if stripped.startswith(kw):
                            line = line[:len(line) - len(stripped)] + stripped[len(kw):]
                            break
                    if line.strip():
                        lines.append(line)
    return lines


def _enum_block_members(rhs):
    """Extract member names from an enum_block_def node (block enum form).

    Members live in a Several_Times of per-member Sequence_Parsers; each
    member's first child carries the identifier/integer string in '.node'."""
    members = []
    for child in getattr(rhs, "nodes", []) or []:
        if type(child).__name__ == "Several_Times":
            for seq in child.nodes:
                if getattr(seq, "nodes", None):
                    members.append(str(seq.nodes[0].node))
    return members


@method(type_block_stmt)
def to_py(self, indent=0):
    """type_block_stmt: 'type' IDENTIFIER discrim_param? type_alias_params? (=|is) (tuple_def|discrim_record_def|record_def|enum_block_def)"""
    name = self.nodes[0].to_py()
    params = ""
    discrim_name = None
    discrim_type = None
    rhs = self.nodes[-1]
    for node in self.nodes[1:-1]:
        ntype = type(node).__name__
        if ntype == "type_alias_params":
            params = node.to_py()
        elif ntype == "Several_Times" and hasattr(node, "nodes"):
            for child in node.nodes:
                cn = type(child).__name__
                if cn == "type_alias_params":
                    params = child.to_py()
                elif cn == "Sequence_Parser" and hasattr(child, "nodes"):
                    # discrim_param: (Name : Type) -> [IDENTIFIER, Fmap(:), type_name]
                    idents = [c for c in child.nodes if type(c).__name__ in ("IDENTIFIER", "type_name", "Filter")]
                    if len(idents) >= 2:
                        discrim_name = idents[0].to_py()
                        discrim_type = idents[1].to_py()
    # rhs is Sequence_Parser containing [Literal_keyword, ...]
    keyword = ""
    block_node = None
    variant_case_node = None
    if hasattr(rhs, "nodes"):
        for child in rhs.nodes:
            cname = type(child).__name__
            if cname.startswith("Literal_"):
                keyword = getattr(child, "node", "")
            elif cname == "block":
                block_node = child
            elif cname == "Sequence_Parser":
                # variant_case: [IDENTIFIER(discrim), NL, INDENT, Several_Times(whens), DEDENT]
                has_ident = any(type(c).__name__ == "IDENTIFIER" for c in child.nodes)
                has_st = any(type(c).__name__ == "Several_Times" for c in child.nodes)
                if has_ident and has_st:
                    variant_case_node = child
    if keyword == "enum":
        # Block enum form: 'type T is enum:' with one member per line.
        member_names = _enum_block_members(rhs)
        return hek_py3_stmt._emit_enum_py(name, member_names, indent)
    if variant_case_node and discrim_name:
        # Discriminated record -> Python @dataclass with all fields flattened
        ParserState.nim_imports.add("from dataclasses import dataclass, field")
        all_fields = []
        # Collect fields from each variant
        whens_node = None
        for child in variant_case_node.nodes:
            if type(child).__name__ == "Several_Times":
                whens_node = child
                break
        if whens_node:
            for when_node in whens_node.nodes:
                fields_node = None
                for child in when_node.nodes:
                    if type(child).__name__ == "Several_Times":
                        fields_node = child
                if fields_node:
                    variant_fields = _extract_variant_fields_py(fields_node.nodes, indent + 1)
                    all_fields.extend(variant_fields)
        result_lines = [f"{_ind(indent)}@dataclass", f"{_ind(indent)}class {name}{params}:"]
        result_lines.append(f"{_ind(indent + 1)}{discrim_name}: {discrim_type}")
        for fld in all_fields:
            # Add default value for variant fields (they may not all be set)
            stripped = fld.strip()
            if "=" not in stripped:
                # Add None default via field(default=None)
                fld = fld + " = None"  # type: ignore
            result_lines.append(fld)
        return "\n".join(result_lines)
    if not block_node:
        block_node = rhs  # fallback
    fields = _extract_py_fields(block_node, indent=indent+1)
    if keyword == "tuple":
        ParserState.nim_imports.add("from typing import NamedTuple")
        lines = [f"{_ind(indent)}class {name}{params}(NamedTuple):"]
        # Register field names for named_tuple_lit constructor emission
        import re as _re
        field_names = []
        for f in fields:
            lines.append(f)
            m = _re.match(r'\s+(\w+)\s*:', f)
            if m:
                field_names.append(m.group(1))
        if field_names:
            from hek_py3_expr import _register_named_tuple
            _register_named_tuple(name, field_names)
        return "\n".join(lines)
    elif keyword == "record":
        ParserState.nim_imports.add("from dataclasses import dataclass")
        lines = [f"{_ind(indent)}@dataclass", f"{_ind(indent)}class {name}{params}:"]
        for f in fields:
            lines.append(f)
        return "\n".join(lines)
    return f"{_ind(indent)}type {name}{params} = {rhs.to_py()}"



# --- Class definition ---
@method(class_def)
def to_py(self, indent=0):
    """class_def: decorators? 'class' IDENTIFIER ('(' arguments? ')')? ':' block"""
    decos = ""
    name = ""
    bases = ""
    type_params = ""
    block_node = None

    for node in self.nodes:
        tname = type(node).__name__
        if tname == "decorators":
            decos = node.to_py(indent) + "\n"
        elif tname == "Several_Times":
            for seq in node.nodes:
                stname = type(seq).__name__
                if stname == "decorator":
                    decos += seq.to_py(indent) + "\n"
                elif stname == "decorators":
                    decos = seq.to_py(indent) + "\n"
                elif stname == "type_alias_params":
                    type_params = seq.to_py()
                elif stname == "class_args":
                    bases = seq.to_py()
        elif tname == "type_alias_params":
            type_params = node.to_py()
        elif tname == "class_args":
            bases = node.to_py()
        elif tname == "IDENTIFIER":
            name = node.to_py()
        elif tname == "block":
            block_node = node

    # Warn if a tuple type is used directly as a generic parameter
    if bases and "[(" in bases and ")]" in bases:
        import re as _re
        _m = _re.search(r'(\w+)\[\(', bases)
        _parent = _m.group(1) if _m else "Base"
        print(f"WARNING: class {name}({_parent}[(...)]): tuple used as generic parameter "
              f"will fail at runtime.\n"
              f"  Use a type alias instead:  type MyTuple is (int, int)\n"
              f"  Then:  class {name}({_parent}[MyTuple]):", file=sys.stderr)

    hc = _block_inline_header_comment(block_node) if block_node else ""
    # A field declared without a value must not be given a mutable one here:
    # at class level that object is shared by every instance.  See
    # _zero_value() in hek_py3_stmt.py.
    import hek_py3_stmt as _stmt
    _outer_class_depth = _stmt.CLASS_BODY_DEPTH
    _stmt.CLASS_BODY_DEPTH = _outer_class_depth + 1
    try:
        body = block_node.to_py(indent + 1) if block_node else ""
    finally:
        _stmt.CLASS_BODY_DEPTH = _outer_class_depth
    return f"{decos}{_ind(indent)}class {name}{type_params}{bases}:{hc}\n{body}"


@method(class_args)
def to_py(self):
    """class_args: '(' arguments? ')'"""
    # nodes[0] is the Several_Times from arguments[:]
    st = self.nodes[0]
    if hasattr(st, "nodes") and st.nodes:
        # The inner match: st.nodes[0] is the arguments node
        args_node = st.nodes[0]
        return f"({args_node.to_py()})"
    return "()"


# --- Async for / with ---
@method(async_for_stmt)
def to_py(self, indent=0):
    """async_for_stmt: 'async' 'for' targets 'in' exprs ':' block"""
    target = self.nodes[0].to_py()
    iterable = self.nodes[1].to_py()
    hc = _block_inline_header_comment(self.nodes[2])
    body = self.nodes[2].to_py(indent + 1)
    return f"{_ind(indent)}async for {target} in {iterable}:{hc}\n{body}"


@method(async_with_stmt)
def to_py(self, indent=0):
    """async_with_stmt: 'async' 'with' with_item (',' with_item)* ':' block"""
    items = [self.nodes[0].to_py()]
    block_node = None
    for node in self.nodes[1:]:
        if type(node).__name__ == "Several_Times":
            for seq in node.nodes:
                if hasattr(seq, "nodes") and seq.nodes:
                    item = seq.nodes[0]
                    if hasattr(item, "to_py"):
                        items.append(item.to_py())
        elif hasattr(node, "to_py"):
            block_node = node
    body = ""
    hc = ""
    if block_node:
        hc = _block_inline_header_comment(block_node)
        try:
            body = block_node.to_py(indent + 1)
        except TypeError:
            body = _ind(indent + 1) + block_node.to_py()
    return f"{_ind(indent)}async with {', '.join(items)}:{hc}\n{body}"


# ---------------------------------------------------------------------------
# Shell statement helpers and to_py()
# ---------------------------------------------------------------------------

def _extract_shell_opts(node):
    """Walk a shell_opts Several_Times node, returning a {key: value_str} dict.

    shell_opt grammar: IDENTIFIER iop("=") expression
    Terminal nodes (STRING, NUMBER, IDENTIFIER) all store their string value in
    .node regardless of what @method() renamed their class to.  We therefore
    match terminals by isinstance(node.node, str) rather than by class name,
    which is stable across decorator renames.
    """
    opts = {}

    def _find_str_value(n):
        """Return the first plain-string .node value found depth-first.

        Skips IDENTIFIER-valued nodes whose string is a keyword or option-name
        to avoid returning the key instead of the value.
        """
        val = getattr(n, "node", None)
        if isinstance(val, str):
            return val
        if hasattr(n, "nodes"):
            for c in n.nodes:
                if c is not None:
                    r = _find_str_value(c)
                    if r is not None:
                        return r
        return None

    def _walk(n):
        if n is None:
            return
        # A shell_opt Sequence_Parser: first child is IDENTIFIER (key), rest is expression.
        # @method(IDENTIFIER) renames the class from "Filter" to "IDENTIFIER", so we
        # match by isidentifier() on the string value rather than the class name.
        if type(n).__name__ == "Sequence_Parser" and hasattr(n, "nodes") and n.nodes:
            first = n.nodes[0]
            first_val = getattr(first, "node", None)
            if isinstance(first_val, str) and first_val.isidentifier():
                for sibling in n.nodes[1:]:
                    val = _find_str_value(sibling)
                    if val is not None:
                        opts[first_val] = val
                        return  # consumed this opt, don't recurse deeper
        if hasattr(n, "nodes"):
            for c in n.nodes:
                _walk(c)

    _walk(node)
    return opts


def _extract_shell_body(body_st):
    """Reconstruct the shell command string from the body Several_Times node.

    Preserves original spacing using token source positions.
    Returns (cmd_str, needs_fstring) where needs_fstring is True when any
    bare '{' or '}' OP token appears (indicating {var} interpolation).
    """
    import tokenize as _tkn
    tokens = []
    for node in body_st.nodes:
        tok = getattr(node, "node", None)
        if tok is not None and hasattr(tok, "string"):
            tokens.append(tok)
    if not tokens:
        return "", False

    from hek_tokenize import DOLLAR_TOKEN as _DOLLAR_TOKEN, \
        BASH_TEST_TOKEN as _BASH_TEST_TOKEN
    parts = []
    for i, tok in enumerate(tokens):
        if i > 0:
            prev = tokens[i - 1]
            # Synthetic tokens inserted by the preprocessor carry artificial
            # column offsets (the sentinel had a space before the name token).
            # Never insert a gap after DOLLAR_TOKEN ($USER -> $USER not $ USER)
            # or after BASH_TEST_TOKEN (-e path -> -e path not - e path).
            if prev.type in (_DOLLAR_TOKEN, _BASH_TEST_TOKEN):
                pass  # no gap — glue directly to previous token
            else:
                gap = tok.start[1] - prev.end[1]
                parts.append(" " * max(gap, 1) if gap >= 1 else "")
        parts.append(tok.string)

    cmd = "".join(parts)
    needs_fstring = any(
        tok.type == _tkn.OP and tok.string in ("{", "}")
        for tok in tokens
    )
    return cmd, needs_fstring


def _collect_identifiers_from_paren(node):
    """Walk a paren_group AST node and collect all IDENTIFIER leaf values.

    After @method(IDENTIFIER) renames classes, IDENTIFIER nodes have
    type().__name__ == 'IDENTIFIER' and .node is a str.
    We collect every plain-string .node that is a valid identifier.
    """
    names = []

    def _walk(n):
        if n is None:
            return
        val = getattr(n, "node", None)
        if isinstance(val, str) and val.isidentifier() and val not in ("(", ")", ","):
            names.append(val)
        if hasattr(n, "nodes"):
            for child in n.nodes:
                _walk(child)

    _walk(node)
    return names


def _flatten_block_lines(seq_node):
    """Walk a shell_block Sequence_Parser and return a list of token-lists,
    one per source line.  Returns None if this is not a block form.

    The block AST shape is:
      Sequence_Parser(
        Filter(NEWLINE),
        Fmap(NL*),
        Several_Times(
          Sequence_Parser(Several_Times(tok, tok, ...)),  # line 1
          Sequence_Parser(Several_Times(tok, tok, ...)),  # line 2
          ...
        ),
        Fmap(DEDENT))
    """
    if type(seq_node).__name__ != "Sequence_Parser":
        return None
    # First child should be a NEWLINE filter (token with empty string and type=NEWLINE).
    if not seq_node.nodes:
        return None
    first = seq_node.nodes[0]
    first_val = getattr(first, "node", None)
    if not (hasattr(first_val, "string") and getattr(first_val, "type", -1) == _tknmod.NEWLINE):
        return None
    # Find the Several_Times that holds the lines
    lines_st = None
    for n in seq_node.nodes:
        if type(n).__name__ == "Several_Times":
            lines_st = n
            break
    if lines_st is None:
        return []
    out = []
    for line_node in lines_st.nodes:
        toks = []
        # line_node is a Sequence_Parser wrapping Several_Times of tokens
        def _gather(nd):
            val = getattr(nd, "node", None)
            if hasattr(val, "string") and not isinstance(val, str):
                if getattr(val, "type", -1) not in (_tknmod.NEWLINE, _tknmod.NL,
                                                    _tknmod.INDENT, _tknmod.DEDENT,
                                                    _tknmod.ENDMARKER, 0):
                    toks.append(val)
            for c in getattr(nd, "nodes", []) or []:
                _gather(c)
        _gather(line_node)
        if toks:
            out.append(toks)
    return out


def _tokens_to_string(tokens):
    """Reconstruct a string from a list of tokens, preserving spacing."""
    if not tokens:
        return "", False
    from hek_tokenize import DOLLAR_TOKEN as _DOLLAR_TOKEN, \
        BASH_TEST_TOKEN as _BASH_TEST_TOKEN
    parts = []
    for i, tok in enumerate(tokens):
        if i > 0:
            prev = tokens[i - 1]
            if prev.type in (_DOLLAR_TOKEN, _BASH_TEST_TOKEN):
                pass
            else:
                # Same-line gap from columns; cross-line, just one space
                if tok.start[0] == prev.end[0]:
                    gap = tok.start[1] - prev.end[1]
                    parts.append(" " * max(gap, 1) if gap >= 1 else "")
                else:
                    parts.append(" ")
        parts.append(tok.string)
    cmd = "".join(parts)
    needs_fstring = any(
        tok.type == _tknmod.OP and tok.string in ("{", "}")
        for tok in tokens
    )
    return cmd, needs_fstring


def _classify_line(tokens):
    """Classify a block-form line as ('expect', arg_str), ('send', arg_str), or ('cmd', cmd_str).
    The arg_str is the raw inner text between the parens (typically a string literal).
    """
    if not tokens:
        return ("cmd", "", False)
    first = tokens[0]
    if (first.type == _tknmod.NAME and first.string in ("expect", "send")
        and len(tokens) >= 3
        and tokens[1].type == _tknmod.OP and tokens[1].string == "("
        and tokens[-1].type == _tknmod.OP and tokens[-1].string == ")"):
        inner, needs_fstring = _tokens_to_string(tokens[2:-1])
        return (first.string, inner.strip(), needs_fstring)
    cmd, needs_fstring = _tokens_to_string(tokens)
    return ("cmd", cmd, needs_fstring)


import tokenize as _tknmod



_SHELL_TIMEOUT_HELPER = """\
def _run_shell(_cmd, **_kw):
    \"\"\"subprocess.run, but a timeout reports 124 instead of raising.

    Nim has no exception to raise here, and 124 is what timeout(1) reports,
    so both backends can say the same thing about a killed command.
    \"\"\"
    try:
        return _subprocess.run(_cmd, **_kw)
    except _subprocess.TimeoutExpired as _e:
        return _types.SimpleNamespace(
            stdout=(_e.stdout or "") if isinstance(_e.stdout, str) else "",
            stderr=(_e.stderr or "") if isinstance(_e.stderr, str) else "",
            returncode=124)\
"""


def _ensure_shell_timeout_helper():
    """Inject the timeout-tolerant runner the first time a timeout is used."""
    decls = getattr(ParserState, "py_top_decls", [])
    if not any("_run_shell" in d for d in decls):
        decls.append(_SHELL_TIMEOUT_HELPER)
        ParserState.py_top_decls = decls



def _py_shell_literal(cmd, needs_fstring):
    """Wrap a shell body as a Python string literal.

    `\"\"\"` is the usual delimiter, since a shell body is full of single
    quotes.  A body that ends in `"` or contains `\"\"\"` runs into it --
    `echo "end"` would emit four quotes in a row and not parse -- so those
    fall back to a `"`-delimited literal with backslashes and quotes escaped,
    the same guard the Nim backend applies.
    """
    prefix = "f" if needs_fstring else ""
    if '"""' not in cmd and not cmd.endswith('"'):
        return f'{prefix}"""{cmd}"""'
    escaped = cmd.replace("\\", "\\\\").replace('"', '\\"')
    return f'{prefix}"{escaped}"'


def _apply_shell_quoting(cmd, wrapper, splat_wrapper=None):
    """Rewrite the quoting sigils in a shell body.

    `{x}` interpolates the value as written, which is what a command fragment
    wants.  `{!x}` asks for it quoted, so a path holding spaces or shell
    metacharacters arrives as one argument instead of several.  `{*xs}` does
    the same for a list, quoting each element and joining them with spaces —
    the form an argument vector needs.

    WRAPPER and SPLAT_WRAPPER are format strings taking `expr`, e.g.
    "quoteShell({expr})".  Returns (rewritten, changed).
    """
    sigils = {"!": wrapper}
    if splat_wrapper:
        sigils["*"] = splat_wrapper
    if not any("{" + s in cmd for s in sigils):
        return cmd, False
    out = []
    i = 0
    n = len(cmd)
    changed = False
    while i < n:
        # `{{` and `}}` are escaped braces, not interpolations
        if cmd.startswith(("{{", "}}"), i):
            out.append(cmd[i:i + 2])
            i += 2
            continue
        sigil = cmd[i + 1] if cmd[i] == "{" and i + 1 < n else ""
        if sigil in sigils:
            depth = 1
            j = i + 2
            while j < n:
                if cmd[j] == "{":
                    depth += 1
                elif cmd[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n and depth == 0:
                expr = cmd[i + 2:j].strip()
                if expr:
                    out.append("{" + sigils[sigil].format(expr=expr) + "}")
                    i = j + 1
                    changed = True
                    continue
        out.append(cmd[i])
        i += 1
    return "".join(out), changed


def _shell_target_annotation(seq):
    """The primitive type named in a shell target's annotation, or None.

    `let code: int = shell: ...` is the one annotation the backends act on:
    it asks for the exit code with the terminal left alone.  Anything else is
    inferred from `shell` versus `shellLines` as before.
    """
    for node in (getattr(seq, "nodes", None) or []):
        stack = [node]
        while stack:
            cur = stack.pop()
            if type(cur).__name__ == "primitive_type":
                name = cur.nodes[0] if getattr(cur, "nodes", None) else None
                return name if isinstance(name, str) else None
            stack.extend(getattr(cur, "nodes", None) or [])
    return None


def _parse_shell_stmt(node):
    """Decompose a shell_stmt AST node into its logical parts.

    Returns (target_kw, target_name, target_tuple, kw, opts, cmd, needs_fstring, block_lines) where:
      target_kw    -- 'let' | 'var' | 'const' | None
      target_name  -- str | None     (scalar form: let result = shell: ...)
      target_tuple -- [str] | None   (tuple  form: let (a,b,c) = shell: ...)
      kw           -- 'shell' | 'shellLines'
      opts         -- dict {str: str}
      cmd          -- reconstructed command string (inline form; '' for block form)
      needs_fstring -- bool (True when {var} interpolation tokens present)
      block_lines  -- None for inline form;
                      list of (kind, text, needs_fstring) tuples for block form
                      where kind ∈ {'cmd','expect','send'}
      target_ann   -- str | None     (the primitive type in `let x: T =`)

    Exactly one of target_name / target_tuple is non-None when a target is
    present; both are None for a bare shell statement.
    """
    nodes = node.nodes

    # Locate the shell keyword node
    kw = None
    kw_idx = -1
    for i, n in enumerate(nodes):
        val = getattr(n, "node", None)
        if isinstance(val, str) and val in ("shell", "shellLines"):
            kw = val
            kw_idx = i
            break

    # Optional assignment target sits before the keyword
    target_kw = target_name = target_tuple = target_ann = None
    if kw_idx > 0:
        target_st = nodes[0]
        if hasattr(target_st, "nodes") and target_st.nodes:
            seq = target_st.nodes[0]
            if hasattr(seq, "nodes"):
                for n in seq.nodes:
                    val = getattr(n, "node", None)
                    ntype = type(n).__name__
                    if not isinstance(val, str):
                        # Could be a paren_group node (tuple target)
                        if ntype in ("paren_group", "Sequence_Parser") or (
                            hasattr(n, "nodes") and any(
                                isinstance(getattr(c, "node", None), str) and
                                getattr(c, "node", "").isidentifier()
                                for c in getattr(n, "nodes", [])
                            )
                        ):
                            names = _collect_identifiers_from_paren(n)
                            if names:
                                target_tuple = names
                        continue
                    if val in ("let", "var", "const"):
                        target_kw = val
                    elif val.isidentifier() and val not in ("let", "var", "const", "="):
                        target_name = val
                # `let name: T =` -- the annotation sits in its own optional slot
                target_ann = _shell_target_annotation(seq)

    # Remaining nodes after the keyword: opts (Several_Times of shell_opt) and
    # body (either inline Several_Times of tokens, or a Sequence_Parser wrapping
    # the (block | inline) alternation).
    opts = {}
    body_st = None
    block_seq = None

    def _scan_for_body(n):
        nonlocal body_st, block_seq, opts
        ntype = type(n).__name__
        if ntype == "Sequence_Parser":
            # Indented block?
            if _flatten_block_lines(n) is not None:
                block_seq = n
                return True
            # Otherwise descend — this wraps the (block|inline) alternation
            for c in n.nodes or []:
                if _scan_for_body(c):
                    return True
            return False
        if ntype != "Several_Times" or not n.nodes:
            return False
        first = n.nodes[0]
        tok = getattr(first, "node", None)
        if hasattr(tok, "string") and not isinstance(tok, str):
            body_st = n
            return True
        # Otherwise it's an opts node
        opts = _extract_shell_opts(n)
        return False

    for n in nodes[kw_idx + 1 :]:
        if _scan_for_body(n):
            break

    if block_seq is not None:
        line_toks = _flatten_block_lines(block_seq)
        block_lines = [_classify_line(tl) for tl in line_toks]
        return (target_kw, target_name, target_tuple, kw, opts, "", False,
                block_lines, target_ann)

    cmd, needs_fstring = _extract_shell_body(body_st) if body_st else ("", False)
    return (target_kw, target_name, target_tuple, kw, opts, cmd, needs_fstring,
            None, target_ann)


@method(shell_stmt)
def to_py(self, indent=0):
    """shell_stmt: [decl_keyword IDENTIFIER '='] ('shell'|'shellLines') [shell_opts] ':' cmd+

    Python output:
      import subprocess as _subprocess, types as _types  (auto-inserted at top)

      # shell: cmd
      _subprocess.run(\"\"\"cmd\"\"\", shell=True)

      # let result = shell: cmd
      _r = _subprocess.run(\"\"\"cmd\"\"\", shell=True, capture_output=True, text=True)
      result = _types.SimpleNamespace(output=_r.stdout, stderr=_r.stderr, code=_r.returncode)

      # let lines = shellLines: cmd
      _r = _subprocess.run(\"\"\"cmd\"\"\", shell=True, capture_output=True, text=True)
      lines = _r.stdout.splitlines()

    Variable interpolation: {name} in cmd body -> f\\\"\\\"\\\"...{name}...\\\"\\\"\\\"
    Options: cwd=\"/tmp\" -> cwd=\"/tmp\"; timeout=5000 -> timeout=5.0 (ms -> s)

    Tuple destructuring:
      # let (out, err, code) = shell: cmd
      _r = _subprocess.run(\"\"\"cmd\"\"\", shell=True, capture_output=True, text=True)
      out, err, code = _r.stdout, _r.stderr, _r.returncode
    """
    ind = _ind(indent)
    (target_kw, target_name, target_tuple, kw, opts, cmd, needs_fstring,
     block_lines, target_ann) = _parse_shell_stmt(self)

    # Block form in Python backend: join cmd lines with " && ", ignore expect/send for now
    if block_lines is not None:
        cmd_parts = [t for (k, t, _f) in block_lines if k == "cmd"]
        cmd = " && ".join(cmd_parts)
        needs_fstring = any(f for (k, _t, f) in block_lines if k == "cmd")

    cmd, _quoted = _apply_shell_quoting(
        cmd, "_shlex.quote({expr})",
        "' '.join(_shlex.quote(_a) for _a in {expr})")
    if _quoted:
        needs_fstring = True
        ParserState.nim_imports.add("import shlex as _shlex")

    has_target = bool(target_name or target_tuple)

    # Mark that shell imports are needed; py2py.translate() inserts them at top
    ParserState.nim_imports.add("import subprocess as _subprocess")
    if has_target and not target_tuple:
        ParserState.nim_imports.add("import types as _types")

    cmd_str = _py_shell_literal(cmd, needs_fstring)

    run_kwargs = ["shell=True"]
    if has_target:
        run_kwargs += ["capture_output=True", "text=True"]
    if "cwd" in opts:
        run_kwargs.append(f"cwd={opts['cwd']}")
    if "timeout" in opts:
        ms = opts["timeout"]
        try:
            run_kwargs.append(f"timeout={int(ms) / 1000}")
        except ValueError:
            run_kwargs.append(f"timeout={ms} / 1000")

    kwargs_str = ", ".join(run_kwargs)
    runner = "_subprocess.run"
    if "timeout" in opts:
        _ensure_shell_timeout_helper()
        ParserState.nim_imports.add("import types as _types")
        runner = "_run_shell"
    lines = []

    if target_tuple:
        # let (out, code) = shell: cmd        — 2-element
        # let (out, code, _) = shell: cmd     — 3-element
        # Slot 1 is the exit code, not stderr: that is the order the Nim
        # backend fills and the one README documents, and the two have to
        # agree or the same source means different things per backend.
        # Slot 2 is stderr, which the Nim backend can now supply too.
        slots = ["_r.stdout", "_r.returncode", "_r.stderr"]
        lhs = ", ".join(target_tuple)
        rhs = ", ".join(slots[:len(target_tuple)])
        lines.append(f"{ind}_r = {runner}({cmd_str}, {kwargs_str})")
        lines.append(f"{ind}{lhs} = {rhs}")
    elif target_name and target_ann == "int" and kw == "shell":
        # `let code: int = shell: cmd` -- the child keeps the terminal, and the
        # exit code comes back directly.  Nothing is captured, so no kwargs
        # beyond the shell itself.
        call_kwargs = ", ".join(k for k in run_kwargs
                                if not k.startswith(("capture_output", "text")))
        lines.append(f"{ind}{target_name} = _subprocess.call({cmd_str}, {call_kwargs})"
                     if "timeout" not in opts else
                     f"{ind}{target_name} = {runner}({cmd_str}, {call_kwargs}).returncode")
    elif target_name:
        lines.append(f"{ind}_r = {runner}({cmd_str}, {kwargs_str})")
        if kw == "shellLines":
            lines.append(f"{ind}{target_name} = _r.stdout.splitlines()")
        else:
            lines.append(
                f"{ind}{target_name} = _types.SimpleNamespace("
                f"output=_r.stdout, stderr=_r.stderr, code=_r.returncode)"
            )
    else:
        lines.append(f"{ind}{runner}({cmd_str}, {kwargs_str})")

    return "\n".join(lines)


# --- compound_stmt ---
@method(compound_stmt)
def to_py(self, indent=0):
    """compound_stmt: if | while | for | try | with | match | def | class | async... | shell_stmt"""
    return self.nodes[0].to_py(indent)


###############################################################################
# Public API
###############################################################################


def parse_compound(code):
    """Parse a Python 3.14 compound statement and return the AST node."""
    ParserState.reset()
    stream = Input(code)
    result = compound_stmt.parse(stream)
    if not result:
        return None
    return result[0]


def parse_statement(code):
    """Parse any statement (simple or compound)."""
    ParserState.reset()
    stream = Input(code)
    result = statement.parse(stream)
    if not result:
        return None
    return result[0]


def parse_module(code):
    """Parse a full module (sequence of statements)."""
    ParserState.reset()
    stream = Input(code)
    stmts = []
    while True:
        # Skip NL tokens between top-level statements
        while True:
            mark = stream.mark()
            tok = stream.get_new_token()
            if not tok or tok.type == tkn.ENDMARKER:
                stream.reset(mark)
                break
            if tok.type == tkn.NL:
                continue
            stream.reset(mark)
            break
        # Try to parse a statement
        result = statement.parse(stream)
        if not result:
            break
        stmts.append(result[0])
    return stmts


###############################################################################
# Tests
###############################################################################

if __name__ == "__main__":
    print("=" * 60)
    print("Python 3.14 Compound Statement Parser Tests")
    print("=" * 60)

    tests = [
        # --- if / elif / else ---
        (
            "if x:\n    pass\n",
            "if x:\n    pass",
        ),
        (
            "if x:\n    y = 1\n",
            "if x:\n    y = 1",
        ),
        (
            "if x:\n    y = 1\n    z = 2\n",
            "if x:\n    y = 1\n    z = 2",
        ),
        (
            "if x:\n    a = 1\nelif y:\n    b = 2\n",
            "if x:\n    a = 1\nelif y:\n    b = 2",
        ),
        (
            "if x:\n    a = 1\nelif y:\n    b = 2\nelse:\n    c = 3\n",
            "if x:\n    a = 1\nelif y:\n    b = 2\nelse:\n    c = 3",
        ),
        # Simple suite (if True: pass) not yet supported — requires block Choice
        # --- while ---
        (
            "while x:\n    pass\n",
            "while x:\n    pass",
        ),
        (
            "while x:\n    y = 1\n    break\n",
            "while x:\n    y = 1\n    break",
        ),
        # --- for ---
        (
            "for x in xs:\n    pass\n",
            "for x in xs:\n    pass",
        ),
        (
            "for i in range:\n    x = i\n",
            "for i in range:\n    x = i",
        ),
        # --- try / except / finally ---
        (
            "try:\n    pass\nexcept:\n    pass\n",
            "try:\n    pass\nexcept:\n    pass",
        ),
        (
            "try:\n    x = 1\nexcept ValueError:\n    pass\n",
            "try:\n    x = 1\nexcept ValueError:\n    pass",
        ),
        (
            "try:\n    x = 1\nexcept ValueError as e:\n    pass\n",
            "try:\n    x = 1\nexcept ValueError as e:\n    pass",
        ),
        (
            "try:\n    x = 1\nfinally:\n    y = 2\n",
            "try:\n    x = 1\nfinally:\n    y = 2",
        ),
        # --- with ---
        (
            "with f():\n    pass\n",
            "with f():\n    pass",
        ),
        (
            "with f() as x:\n    pass\n",
            "with f() as x:\n    pass",
        ),
        # --- def ---
        (
            "def f():\n    pass\n",
            "def f():\n    pass",
        ),
        (
            "def f(a, b):\n    return a\n",
            "def f(a, b):\n    return a",
        ),
        (
            "def f(a, b=1):\n    pass\n",
            "def f(a, b=1):\n    pass",
        ),
        (
            "def f(*args):\n    pass\n",
            "def f(*args):\n    pass",
        ),
        (
            "def f(**kwargs):\n    pass\n",
            "def f(**kwargs):\n    pass",
        ),
        (
            "def f(a, *, b):\n    pass\n",
            "def f(a, *, b):\n    pass",
        ),
        (
            "def f(a, /, b):\n    pass\n",
            "def f(a, /, b):\n    pass",
        ),
        (
            "def f(a: int) -> str:\n    pass\n",
            "def f(a: int) -> str:\n    pass",
        ),
        # --- class ---
        (
            "class Foo:\n    pass\n",
            "class Foo:\n    pass",
        ),
        (
            "class Foo(Bar):\n    pass\n",
            "class Foo(Bar):\n    pass",
        ),
        (
            "class Foo(Bar, Baz):\n    pass\n",
            "class Foo(Bar, Baz):\n    pass",
        ),
        # --- decorator ---
        (
            "@dec\ndef f():\n    pass\n",
            "@dec\ndef f():\n    pass",
        ),
        (
            "@dec\nclass Foo:\n    pass\n",
            "@dec\nclass Foo:\n    pass",
        ),
        # --- async ---
        (
            "async def f():\n    pass\n",
            "async def f():\n    pass",
        ),
        # --- nested ---
        (
            "if x:\n    if y:\n        pass\n",
            "if x:\n    if y:\n        pass",
        ),
        (
            "def f():\n    for x in xs:\n        if x:\n            return x\n",
            "def f():\n    for x in xs:\n        if x:\n            return x",
        ),
        # --- for/while else ---
        (
            "for x in xs:\n    pass\nelse:\n    pass\n",
            "for x in xs:\n    pass\nelse:\n    pass",
        ),
        (
            "while x:\n    pass\nelse:\n    pass\n",
            "while x:\n    pass\nelse:\n    pass",
        ),
        # --- multiple except ---
        (
            "try:\n    pass\nexcept ValueError:\n    pass\nexcept TypeError:\n    pass\n",
            "try:\n    pass\nexcept ValueError:\n    pass\nexcept TypeError:\n    pass",
        ),
        # --- try/except/else/finally ---
        (
            "try:\n    pass\nexcept ValueError:\n    pass\nelse:\n    pass\nfinally:\n    pass\n",
            "try:\n    pass\nexcept ValueError:\n    pass\nelse:\n    pass\nfinally:\n    pass",
        ),
        # --- except* (exception groups) ---
        (
            "try:\n    pass\nexcept* ValueError:\n    pass\n",
            "try:\n    pass\nexcept* ValueError:\n    pass",
        ),
        # --- case / when ---
        (
            "case x:\n    when 1:\n        pass\n",
            "match x:\n    case 1:\n        pass",
        ),
        (
            "case x:\n    when _:\n        pass\n",
            "match x:\n    case _:\n        pass",
        ),
        (
            "case x:\n    when 1:\n        a = 1\n    when 2:\n        b = 2\n",
            "match x:\n    case 1:\n        a = 1\n    case 2:\n        b = 2",
        ),
        (
            "case x:\n    when y if y > 0:\n        pass\n",
            "match x:\n    case y if y > 0:\n        pass",
        ),
        (
            "case x:\n    when 1 | 2:\n        pass\n",
            "match x:\n    case 1 | 2:\n        pass",
        ),
        (
            'case x:\n    when "hello":\n        pass\n',
            'match x:\n    case "hello":\n        pass',
        ),
        (
            "case x:\n    when [1, 2]:\n        pass\n",
            "match x:\n    case [1, 2]:\n        pass",
        ),
        (
            "case x:\n    when Status.OK:\n        pass\n",
            "match x:\n    case Status.OK:\n        pass",
        ),
        (
            "case x:\n    when Point(1, 2):\n        pass\n",
            "match x:\n    case Point(1, 2):\n        pass",
        ),
        (
            "case x:\n    when y as z:\n        pass\n",
            "match x:\n    case y as z:\n        pass",
        ),
        (
            'case x:\n    when {"a": 1}:\n        pass\n',
            'match x:\n    case {"a": 1}:\n        pass',
        ),
        (
            'case x:\n    when {"a": 1, "b": 2}:\n        pass\n',
            'match x:\n    case {"a": 1, "b": 2}:\n        pass',
        ),
        (
            "case x:\n    when others:\n        pass\n",
            "match x:\n    case _:\n        pass",
        ),
        (
            "case x:\n    when 1 .. 5:\n        pass\n",
            "match x:\n    case 1 .. 5:\n        pass",
        ),
        # --- discriminated records ---
        (
            "type Shape (Kind : Shape_Kind) is record:\n    case Kind is\n        when Circle:\n            Radius : float\n        when Rectangle:\n            Width : float\n            Height : float\n",
            "@dataclass\nclass Shape:\n    Kind: Shape_Kind\n    Radius: float = None\n    Width: float = None\n    Height: float = None",
        ),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            result = parse_compound(code)
            if result:
                output = result.to_py()
                if output == expected:
                    print(f"  PASS: {code.splitlines()[0]!r}...")
                    passed += 1
                else:
                    print(f"  MISMATCH: {code.splitlines()[0]!r}...")
                    print(f"    expected: {expected!r}")
                    print(f"    got:      {output!r}")
                    failed += 1
            else:
                print(f"  FAIL: {code.splitlines()[0]!r}... -> parse returned None")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {code.splitlines()[0]!r}... -> {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    # --- parse_module tests ---
    print()
    print("=" * 60)
    print("parse_module Tests")
    print("=" * 60)

    module_tests = [
        # Simple statements only
        (
            "x = 1\ny = 2\n",
            ["x = 1", "y = 2"],
        ),
        # Mixed simple + compound
        (
            "x = 1\nif x:\n    pass\n",
            ["x = 1", "if x:\n    pass"],
        ),
        # Multiple compound
        (
            "def f():\n    pass\nclass Foo:\n    pass\n",
            ["def f():\n    pass", "class Foo:\n    pass"],
        ),
        # Import + function
        (
            "import os\ndef main():\n    return os\n",
            ["import os", "def main():\n    return os"],
        ),
    ]

    mp = mf = 0
    for code, expected_parts in module_tests:
        try:
            stmts = parse_module(code)
            outputs = []
            for s in stmts:
                try:
                    outputs.append(s.to_py())
                except TypeError:
                    outputs.append(s.to_py())
            if outputs == expected_parts:
                print(f"  PASS: {code.splitlines()[0]!r}... ({len(stmts)} stmts)")
                mp += 1
            else:
                print(f"  MISMATCH: {code.splitlines()[0]!r}...")
                print(f"    expected: {expected_parts!r}")
                print(f"    got:      {outputs!r}")
                mf += 1
        except Exception as e:
            print(f"  ERROR: {code.splitlines()[0]!r}... -> {e}")
            import traceback

            traceback.print_exc()
            mf += 1

    print("=" * 60)
    print(f"Results: {mp} passed, {mf} failed")

