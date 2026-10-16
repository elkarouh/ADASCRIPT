"""Stateless decorators, by rewrite, before the parse.

A wrapper is an ordinary top-level function handed the function it wraps,
marked `@decorator`:

    @decorator
    def aligned(width: Positive, f: (str) -> str, s: str) -> str:
        return f(s).alignLeft(width)

    @aligned(64)
    def colored_viewname(view_name: str) -> str: ...

`@aligned(64)` on `def colored_viewname` means colored_viewname = aligned(64,
colored_viewname, ...): the original `def` is kept under a hidden name,
`colored_viewnameBody`, and a forwarding `def` under the original name
returns `aligned(64, colored_viewnameBody, view_name)`. Stacked decorators
apply bottom-up, each through a hidden name of its own. No closures, so the
same text serves both backends; a recursive call inside the body goes through
the decorated name, as in Python.

Each is a one-line SyntaxError: the wrapper's `f` parameter has the decorated
function's type; the parameters after `f` are the decorated function's, in
order; the leading ones are the decorator's arguments; the wrapper returns what
the decorated function returns; a decorator not marked `@decorator` is refused.
Top-level `def`s of one file only. Line numbers after a decorated `def` shift
by the lines added.
"""
import re

_DEF = re.compile(r"def\s+(\w+)\s*(\[[^\]]*\])?\s*\(")


def _split_top(text):
    """TEXT split at the commas outside any bracket or string."""
    parts, depth, cur, quote = [], 0, [], None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            cur.append(c)
            if c == "\\":
                i += 1
                cur.append(text[i:i + 1])
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            cur.append(c)
        elif c in "([{":
            depth += 1
            cur.append(c)
        elif c in ")]}":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    last = "".join(cur)
    if last.strip():
        parts.append(last)
    return [p.strip() for p in parts]


def _norm(t):
    return re.sub(r"\s+", "", t or "")


class _Def:
    """A top-level def: header lines, name, params as (name, type), return type."""

    def __init__(self, lines, start):
        self.start = start
        j, depth = start, 0
        header = []
        while j < len(lines):
            header.append(lines[j])
            text = lines[j].split("#")[0]
            depth += sum(text.count(c) for c in "([") - sum(text.count(c) for c in ")]")
            if depth <= 0 and text.rstrip().endswith(":"):
                break
            j += 1
        self.end = j                      # last header line
        flat = " ".join(h.strip() for h in header)
        m = _DEF.match(flat)
        if not m:
            raise SyntaxError(f"line {start + 1}: cannot read this def")
        self.name = m.group(1)
        self.generics = m.group(2)
        # the parameter list: from after '(' to its matching ')'
        k, depth = m.end(), 1
        while k < len(flat) and depth:
            depth += {"(": 1, ")": -1}.get(flat[k], 0)
            k += 1
        inner = flat[m.end():k - 1]
        rest = flat[k:].strip()
        rm = re.match(r"->\s*(.*?)\s*:\s*(#.*)?$", rest)
        self.ret = rm.group(1) if rm else None
        self.params = []
        for p in _split_top(inner):
            if "=" in re.sub(r"\([^)]*\)", "", p.split(":", 1)[-1]).replace("->", ""):
                raise SyntaxError(f"line {start + 1}: {self.name}: a default value on a "
                                  f"parameter cannot be decorated")
            pm = re.match(r"(\w+)\s*(?::\s*(.*))?$", p)
            if not pm or not pm.group(2):
                raise SyntaxError(f"line {start + 1}: {self.name}: parameter {p!r} needs a type "
                                  f"to be decorated")
            self.params.append((pm.group(1), pm.group(2).strip()))

    def fn_type(self):
        return f"({', '.join(t for _, t in self.params)}) -> {self.ret or 'None'}"


def expand_decorators(code):
    """CODE with every `@decorator`-marked wrapper's uses written out; CODE
    itself when it has none."""
    if "@" not in code:
        return code
    lines = code.split("\n")
    # pass 1: wrappers
    in_doc = False
    wrappers = {}
    marks = []
    for i, ln in enumerate(lines):
        if ln.count('"""') % 2 or ln.count("'''") % 2:
            in_doc = not in_doc
            continue
        if in_doc:
            continue
        if ln.rstrip() == "@decorator":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or not lines[j].startswith("def "):
                raise SyntaxError(f"line {i + 1}: @decorator must stand on a top-level def")
            d = _Def(lines, j)
            fi = [k for k, (_, t) in enumerate(d.params) if t.startswith("(") and "->" in t]
            if not fi:
                raise SyntaxError(f"line {j + 1}: {d.name}: a decorator takes the function "
                                  f"it wraps as a parameter of a function type, f: (T) -> R")
            wrappers[d.name] = (d, fi[0])
            marks.append(i)
    if not wrappers:
        return code
    # pass 2: rewrite
    out = []
    i, in_doc = 0, False
    while i < len(lines):
        ln = lines[i]
        if ln.count('"""') % 2 or ln.count("'''") % 2:
            in_doc = not in_doc
            out.append(ln)
            i += 1
            continue
        if in_doc:
            out.append(ln)
            i += 1
            continue
        if i in marks:
            i += 1                        # the marker itself is not output
            continue
        if ln.startswith("@"):
            decos = []
            j = i
            while j < len(lines) and lines[j].startswith("@"):
                decos.append((j, lines[j][1:].split("#")[0].strip()))
                j += 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            names = [re.match(r"(\w+)", t).group(1) if re.match(r"(\w+)", t) else "" for _, t in decos]
            if not any(n in wrappers for n in names):
                out.extend(lines[i:j])
                i = j
                continue
            if j >= len(lines) or not lines[j].startswith("def "):
                raise SyntaxError(f"line {i + 1}: a decorator stands on a top-level def")
            d = _Def(lines, j)
            for (ln_no, text), n in zip(decos, names):
                if n not in wrappers:
                    raise SyntaxError(f"line {ln_no + 1}: @{n}: not marked @decorator, so it "
                                      f"cannot decorate here")
            # the original under a hidden name
            body_name = f"{d.name}Body"
            hdr = lines[d.start:d.end + 1]
            hdr[0] = hdr[0].replace(f"def {d.name}", f"def {body_name}", 1)
            out.extend(hdr)
            k = d.end + 1
            while k < len(lines) and (lines[k].startswith((" ", "\t")) or not lines[k].strip()):
                out.append(lines[k])
                k += 1
            while out and not out[-1].strip():
                out.pop()
            out.append("")
            # forwarding defs, innermost decorator first
            prev = body_name
            for level, ((ln_no, text), n) in enumerate(reversed(list(zip(decos, names)))):
                w, fidx = wrappers[n]
                am = re.match(r"\w+\s*\((.*)\)$", text, re.S)
                dargs = _split_top(am.group(1)) if am else []
                if len(dargs) != fidx:
                    raise SyntaxError(
                        f"line {ln_no + 1}: @{n} gives {len(dargs)} argument(s), but "
                        f"{n} has {fidx} parameter(s) before its function")
                fparam = w.params[fidx][1]
                if _norm(fparam) != _norm(d.fn_type()):
                    raise SyntaxError(
                        f"line {ln_no + 1}: @{n} wraps {fparam}, but {d.name} is {d.fn_type()}")
                after = w.params[fidx + 1:]
                if [_norm(t) for _, t in after] != [_norm(t) for _, t in d.params]:
                    raise SyntaxError(
                        f"line {ln_no + 1}: the parameters of {n} after its function must be "
                        f"those of {d.name}")
                if _norm(w.ret) != _norm(d.ret):
                    raise SyntaxError(
                        f"line {ln_no + 1}: {n} returns {w.ret or 'nothing'}, but {d.name} "
                        f"returns {d.ret or 'nothing'}")
                last = level == len(decos) - 1
                fname = d.name if last else f"{d.name}Deco{level + 1}"
                plist = ", ".join(f"{a}: {t}" for a, t in d.params)
                call = f"{n}({', '.join(dargs + [prev] + [a for a, _ in d.params])})"
                ret = f" -> {d.ret}" if d.ret else ""
                gen = d.generics or ""
                out.append(f"def {fname}{gen}({plist}){ret}:")
                out.append(f"    return {call}" if d.ret else f"    {call}")
                out.append("")
                prev = fname
            i = k
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)
