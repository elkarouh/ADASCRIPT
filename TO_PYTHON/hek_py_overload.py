"""Overloads on the Python backend: a name defined more than once in a class
body, or at module level, with different parameter types.

Ada overloads on the types of the parameters, and so does Nim, which is why
`def __mul__(self, scale: float)` beside `def __mul__(self, t: Duration_T)`
compiles there. Python has no such thing: the second def replaces the first.
Here each is renamed, and a def of the common name chooses between them from
the types of the arguments at the call -- the exact type first, so that a
Duration_T, which is a float in Python, finds the overload that names it
before the one that names float, then what the argument is an instance of,
and last a plain number for a distinct type of numbers: arithmetic on a
distinct value gives the base type in Python, so `Meters_T(a.x + b.x)` is the
way to say which one a sum is when overloads differ only in such types.
Two defs with the same parameter types are one name defined twice, and
refused. Calls are by position: the dispatcher has no parameter names.
"""
import re

_IDENT = re.compile(r"^[A-Za-z_]\w*$")
_BUILTIN = {"float": "float", "int": "int", "str": "str", "bool": "bool",
            "list": "list", "dict": "dict", "tuple": "tuple", "set": "set"}


def _split_top(text):
    """TEXT split at the commas outside any bracket or string."""
    out, depth, cur, quote = [], 0, [], ""
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return out


def _signature(line, pad):
    """(name, [(param name, type, has default)]) of a one-line `def`, or
    None when it spans lines or has *args, **kwargs or keyword-only parameters."""
    m = re.match(r"^" + re.escape(pad) + r"def ([A-Za-z_]\w*)\(", line)
    if not m:
        return None
    depth, i, quote = 1, m.end(), ""
    while i < len(line) and depth:
        ch = line[i]
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        i += 1
    if depth:
        return None
    params = []
    for p in _split_top(line[m.end():i - 1]):
        p = p.strip()
        if p.startswith("*") or p == "/":
            return None
        default = False
        head, _, _rest = p.partition("=")
        if _ and not head.rstrip().endswith((":", "<", ">", "!")):
            default = True
            p = head.strip()
        name, _, typ = p.partition(":")
        params.append((name.strip(), typ.strip().strip('"').strip(), default))
    return m.group(1), params


def _check(arg, typ, mode):
    """A Python test that ARG is a TYP, or None if it cannot say (a union, a
    generic, a function type, no type at all)."""
    t = typ.strip().strip('"').strip("'")
    if not t:
        return None
    if t.startswith("[") or t.startswith("list["):
        t = "list"
    elif t.startswith("dict[") or t.startswith("{"):
        t = "dict"
    elif t.startswith("_Fixed["):
        t = "list"
    elif t.startswith("tuple[") or t.startswith("("):
        t = "tuple"
    if not _IDENT.match(t) or (len(t) == 1 and t.isupper()):
        return None
    t = _BUILTIN.get(t, t)
    if mode == 0:
        return f"type({arg}) is {t}"
    if t in ("float", "int"):
        return f"isinstance({arg}, (float, int)) and not isinstance({arg}, bool)"
    if mode == 2:
        # arithmetic on a distinct type gives the base type in Python: a plain
        # number is taken for the distinct type its base is
        from ady_declarations import distinct_kind
        base = {"float": "(float, int)", "int": "int", "str": "str", "bool": "bool"}.get(distinct_kind(t) or "")
        if base:
            return f"isinstance({arg}, {base}) and not isinstance({arg}, bool)" if base != "bool" else f"isinstance({arg}, bool)"
    return f"isinstance({arg}, {t})"


def _block_end(lines, start, pad):
    """The index after the def at START: the next line that is not blank and
    not indented past PAD, outside a docstring."""
    in_string = False
    i = start + 1
    while i < len(lines):
        line = lines[i]
        quotes = line.count('"""') + line.count("'''")
        if in_string:
            in_string = in_string != (quotes % 2 == 1)
        elif line.strip() and not (line.startswith(pad) and line[len(pad):len(pad) + 1].isspace()):
            return i
        elif quotes % 2 == 1:
            in_string = True
        i += 1
    return i


def overload_defs(text, indent):
    """TEXT, a class body or a module, with the names defined more than once
    at INDENT made into dispatchers. See the module docstring."""
    pad = "    " * indent
    lines = text.split("\n")
    defs = {}                                   # name -> [(start, end, params)]
    in_string = False
    i = 0
    while i < len(lines):
        line = lines[i]
        quotes = line.count('"""') + line.count("'''")
        if in_string:
            in_string = in_string != (quotes % 2 == 1)
            i += 1
            continue
        if quotes % 2 == 1:
            in_string = True
            i += 1
            continue
        if line.startswith(pad + "def ") and not line[len(pad):len(pad) + 1].isspace():
            sig = _signature(line, pad)
            decorated = i > 0 and lines[i - 1].startswith(pad + "@")
            if sig and not decorated:
                end = _block_end(lines, i, pad)
                defs.setdefault(sig[0], []).append((i, end, sig[1]))
            elif sig is None or decorated:
                defs.setdefault(line.split("(")[0].split()[-1], []).append((i, None, None))
        i += 1
    edits = []                                   # (start, end, replacement lines)
    for name, group in defs.items():
        if len(group) < 2 or any(g[1] is None for g in group):
            continue
        method = bool(group[0][2]) and group[0][2][0][0] in ("self", "cls")
        if any(bool(g[2]) and (g[2][0][0] in ("self", "cls")) != method for g in group):
            continue
        shapes = []
        for k, (start, end, params) in enumerate(group):
            ps = params[1:] if method else params
            key = tuple(t for _, t, _d in ps)
            if key in shapes:
                raise SyntaxError(
                    f"{name} is defined twice with the parameter types "
                    f"({', '.join(key)}) -- an overload differs in the types of its parameters")
            shapes.append(key)
        for k, (start, end, params) in enumerate(group):
            lines[start] = lines[start].replace(f"def {name}(", f"def _ov{k}_{name}(", 1)
        owner = "self." if method else ""
        head = "self, *args" if method else "*args"
        out = [f"{pad}def {name}({head}):", f"{pad}    n = len(args)"]
        for mode in (0, 1, 2):
            for k, (start, end, params) in enumerate(group):
                ps = params[1:] if method else params
                lo = sum(1 for p in ps if not p[2])
                conds = [f"{lo} <= n <= {len(ps)}"]
                for j, (_pn, typ, _d) in enumerate(ps):
                    c = _check(f"args[{j}]", typ, mode)
                    if c:
                        conds.append(c)
                out.append(f"{pad}    if {' and '.join(conds)}: return {owner}_ov{k}_{name}(*args)")
        out.append(f"{pad}    raise TypeError(f\"no {name} takes ({{', '.join(type(a).__name__ for a in args)}})\")")
        edits.append((group[-1][1], group[-1][1], out))
    for start, end, repl in sorted(edits, reverse=True):
        lines[start:end] = repl + lines[start:end]
    return "\n".join(lines)
