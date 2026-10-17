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
A method is wrapped as the function of its other parameters, bound to self, so
one wrapper serves functions and methods alike. Decorated `def`s of one file
only. Line numbers after a decorated `def` shift
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
    """A def: header lines, name, params as (name, type), return type. A
    method's `self` is not among the params; `method` says it was there."""

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
        parts = _split_top(inner)
        self.method = bool(parts) and re.match(r"self\s*(:|$)", parts[0]) is not None
        if self.method:
            parts = parts[1:]
        for p in parts:
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


def _bind(pattern, actual, tvars):
    """The type variables TVARS bound so that PATTERN, a type naming them,
    reads ACTUAL; None when it cannot."""
    rx, seen = "", set()
    for tok in re.split(r"(\w+)", _norm(pattern)):
        if tok in tvars:
            rx += f"(?P={tok})" if tok in seen else f"(?P<{tok}>.+?)"
            seen.add(tok)
        else:
            rx += re.escape(tok)
    m = re.fullmatch(rx, _norm(actual))
    return m.groupdict() if m else None


def _subst(typ, binding):
    return re.sub(r"\w+", lambda m: binding.get(m.group(0), m.group(0)), _norm(typ))


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
        dm = re.match(r"([ \t]*)@", ln)
        if dm:
            ind = dm.group(1)
            decos = []
            j = i
            while j < len(lines) and (re.match(r"[ \t]*@", lines[j])
                                      and lines[j][:len(ind) + 1] == ind + "@"):
                decos.append((j, lines[j][len(ind) + 1:].split("#")[0].strip()))
                j += 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            names = [re.match(r"(\w+)", t).group(1) if re.match(r"(\w+)", t) else "" for _, t in decos]
            if not any(n in wrappers for n in names):
                out.extend(lines[i:j])
                i = j
                continue
            if j >= len(lines) or not lines[j].startswith(ind + "def "):
                raise SyntaxError(f"line {i + 1}: a decorator stands on a def")
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
            while k < len(lines) and (not lines[k].strip() or (
                    lines[k].startswith(ind) and lines[k][len(ind):][:1] in (" ", "\t"))):
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
                # a generic wrapper, [T, R], takes any function of its shape
                tvars = _split_top(w.generics[1:-1]) if w.generics else []
                binding = _bind(fparam, d.fn_type(), set(tvars))
                if binding is None:
                    raise SyntaxError(
                        f"line {ln_no + 1}: @{n} wraps {fparam}, but {d.name} is {d.fn_type()}")
                after = w.params[fidx + 1:]
                if [_subst(t, binding) for _, t in after] != [_norm(t) for _, t in d.params]:
                    raise SyntaxError(
                        f"line {ln_no + 1}: the parameters of {n} after its function must be "
                        f"those of {d.name}")
                if _subst(w.ret or "None", binding) != _norm(d.ret or "None"):
                    raise SyntaxError(
                        f"line {ln_no + 1}: {n} returns {w.ret or 'nothing'}, but {d.name} "
                        f"returns {d.ret or 'nothing'}")
                last = level == len(decos) - 1
                fname = d.name if last else f"{d.name}Deco{level + 1}"
                plist = ", ".join(f"{a}: {t}" for a, t in d.params)
                args = ", ".join(a for a, _ in d.params)
                ret = f" -> {d.ret}" if d.ret else ""
                gen = d.generics or ""
                give = "return " if d.ret else ""
                if d.method:
                    # the wrapper is handed the method bound to self
                    bound = f"{fname}Bound"
                    out.append(f"{ind}def {fname}{gen}({', '.join(['self'] + ([plist] if plist else []))}){ret}:")
                    out.append(f"{ind}    def {bound}({plist}){ret}:")
                    out.append(f"{ind}        {give}self.{prev}({args})")
                    fn = bound
                else:
                    out.append(f"{ind}def {fname}{gen}({plist}){ret}:")
                    fn = prev
                targs = f"[{', '.join(binding.get(v, v) for v in tvars)}]" if tvars else ""
                call = f"{n}{targs}({', '.join(dargs + [fn] + [a for a, _ in d.params])})"
                out.append(f"{ind}    {give}{call}")
                out.append("")
                prev = fname
            i = k
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)
