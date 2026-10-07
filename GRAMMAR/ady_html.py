"""`html:` blocks -- a tag tree written as indented source.

    def to_html(self) -> Html:
        html:
            div class="card":
                h2: self.title
                ul:
                    for item in self.items:
                        li: item
                if self.done:
                    span: "done"

The block is rewritten as source text before the parse, so every expression
inside it is translated by the ordinary machinery of the backend.

Nim only: the block becomes marker calls (`with __root_div(class_="card"):`,
`with __tag_h2():`, `__text(x)`) that `finish_html_nim` turns into a karax
`buildHtml` once the Nim is written. The Python backend does not know
`html:`. The page is a karax `VNode` (`Html` is an alias of it): `$page` is
the HTML text, and the same code builds a live DOM under `ady2nim js`.

Line forms inside the block:

    tag attr=value ...:          container; its children are indented below
    tag attr=value ...: expr     a tag around one expression or string
    tag attr=value ...           a void tag (br, hr, img, input ...)
    "text" / f"text"             text, when the line is a string literal
    + expr                       another widget's HTML (an Html value) here
    for / if / elif / else / while   ordinary control flow around tags

An attribute value is a string literal or a bare expression without spaces.
`class`, `for` ... take a trailing underscore on the way (`class_="x"` is
accepted too); `data-id` is spelled `data_id`.
"""
import re

_CONTROL = ("for", "if", "elif", "else", "while", "match", "case", "try",
            "except", "finally", "with")
_OPEN = re.compile(r"^(\s*)html:\s*(#.*)?$")
_ATTR = re.compile(r"""([A-Za-z_][\w-]*)=("[^"]*"|'[^']*'|[^\s:]+)""")
_TAG = re.compile(
    r"""^(?P<tag>[A-Za-z][A-Za-z0-9]*)
        (?P<attrs>(?:\s+[A-Za-z_][\w-]*=(?:"[^"]*"|'[^']*'|[^\s:]+))*)
        \s*(?P<colon>:)?\s*(?P<rest>.*)$""", re.X)


def _attrs(text):
    """TEXT's attributes as ('class_', '"card"') pairs."""
    out = []
    for name, value in _ATTR.findall(text):
        name = name.replace("-", "_")
        if name in ("class", "for"):
            name += "_"
        out.append((name, value))
    return out


def _is_text(line):
    return bool(re.match(r"""^[fF]?["']""", line))


def uses_html(code):
    return any(_OPEN.match(ln) for ln in code.split("\n"))


def _block(lines, i, indent):
    """Index just past the lines of the block that opened at LINES[i-1]."""
    j = i
    while j < len(lines):
        ln = lines[j]
        if ln.strip() and len(ln) - len(ln.lstrip()) <= indent:
            break
        j += 1
    while j > i and not lines[j - 1].strip():
        j -= 1
    return j


def _tag_line(raw):
    """(indent, kind, tag, attrs, rest) of one line of a block."""
    line = raw.strip()
    ind = len(raw) - len(raw.lstrip())
    head = re.split(r"[\s:(]", line, 1)[0]
    if head in _CONTROL and line.endswith(":"):
        return ind, "control", None, None, line
    if _is_text(line):
        return ind, "text", None, None, line
    if line.startswith("+ "):                        # a child's own HTML
        return ind, "embed", None, None, line[2:].strip()
    m = _TAG.match(line)
    if not m:
        raise SyntaxError(f"html: block: cannot read the line {line!r}")
    rest = m.group("rest").strip()
    if rest.startswith("#"):
        rest = ""
    return (ind, "tag", m.group("tag"), _attrs(m.group("attrs")),
            rest if m.group("colon") else None)


def _kw(attrs):
    return ", ".join(f"{n}={v}" for n, v in attrs)


def _expand(lines, start, end, base):
    """The lines of one html: block, with the tags as marker calls."""
    parsed = [_tag_line(raw) for raw in lines[start:end]
              if raw.strip() and not raw.strip().startswith("#")]
    if not parsed:
        raise SyntaxError("html: block is empty")
    top = min(p[0] for p in parsed)
    roots = sum(1 for p in parsed if p[0] == top and p[1] == "tag")
    if roots != 1:
        raise SyntaxError(f"html: block needs exactly one root tag, found {roots}")
    out = []
    for ind, kind, tag, attrs, rest in parsed:
        pad = " " * (base + ind - top)
        root = ind == top and kind == "tag"
        marker = "__root_" if root else "__tag_"
        if kind == "control":
            out.append(pad + rest)
        elif kind == "embed":
            out.append(f"{pad}__embed({rest})")
        elif kind == "text":
            out.append(f"{pad}__text({rest})")
        elif rest is None and root:                   # a root with nothing in it
            out.append(f"{pad}with {marker}{tag}({_kw(attrs)}):")
            out.append(f"{pad}    __text(\"\")")
        elif rest is None:                            # void tag
            out.append(f"{pad}{marker}{tag}({_kw(attrs)})")
        elif rest == "":                              # container
            out.append(f"{pad}with {marker}{tag}({_kw(attrs)}):")
        else:                                         # tag around one expression
            out.append(f"{pad}with {marker}{tag}({_kw(attrs)}):")
            out.append(f"{pad}    __text({rest})")
    return out


def expand_html_blocks(code):
    """CODE with every `html:` block written out as marker calls."""
    if not uses_html(code):
        return code
    lines = code.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if not _OPEN.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        base = len(_OPEN.match(lines[i]).group(1))
        end = _block(lines, i + 1, base)
        out.extend(_expand(lines, i + 1, end, base))
        i = end
    head = ["# nimraw: import karax/[karaxdsl, vdom]", "# nimraw: type Html = VNode"]
    if out and out[0].startswith("#!"):               # keep the shebang first
        return "\n".join([out[0]] + head + out[1:])
    return "\n".join(head + out)


_ROOT = re.compile(r"^(\s*)with __root_(\w+)\((.*)\):\s*$")
_TAGW = re.compile(r"^(\s*)with __tag_(\w+)\((.*)\):\s*$")
_VOID = re.compile(r"^(\s*)__tag_(\w+)\((.*)\)\s*$")
_EMBED = re.compile(r"^(\s*)__embed\((.*)\)\s*$")
_TEXT = re.compile(r"^(\s*)__text\((.*)\)\s*$")


def _karax(tag, args):
    tag = {"div": "tdiv"}.get(tag, tag)
    args = re.sub(r"\bclass_=", "class=", args)
    args = re.sub(r"\bfor_=", "`for`=", args)
    args = re.sub(r"\b([A-Za-z]+)_([A-Za-z]+)=", r"\1-\2=", args) if False else args
    return tag, args


def finish_html_nim(nim):
    """NIM, the text of a module, with the markers turned into karax."""
    if "__tag_" not in nim and "__root_" not in nim and "__text(" not in nim \
            and "__embed(" not in nim:
        return nim
    out = []
    for ln in nim.split("\n"):
        if (m := _ROOT.match(ln)):
            tag, args = _karax(m.group(2), m.group(3))
            out.append(f"{m.group(1)}result = buildHtml({tag}({args})):")
        elif (m := _TAGW.match(ln)):
            tag, args = _karax(m.group(2), m.group(3))
            out.append(f"{m.group(1)}{tag}({args}):" if args else f"{m.group(1)}{tag}:")
        elif (m := _VOID.match(ln)):
            tag, args = _karax(m.group(2), m.group(3))
            out.append(f"{m.group(1)}{tag}({args})")
        elif (m := _EMBED.match(ln)):
            out.append(f"{m.group(1)}{m.group(2)}")
        elif (m := _TEXT.match(ln)):
            out.append(f"{m.group(1)}text {m.group(2)}")
        else:
            out.append(ln)
    return "\n".join(out)
