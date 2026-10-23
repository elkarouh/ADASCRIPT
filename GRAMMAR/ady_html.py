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

An attribute value is an expression; a space or a `:` ends it unless it is
inside brackets or a string, so `x=str(a + b)` and `class=("n" if g else "b")`
read whole.
An attribute named on... (`onclick=self.inc`) is an event handler: its value
is run when the event fires, and the module then needs karax's browser side,
so it builds under `ady2nim js` only.
`class`, `for` ... take a trailing underscore on the way (`class_="x"` is
accepted too); `data-id` is spelled `data_id`, and written `data-id` in the
page, as are `marker_end`, `stroke_width` and every other name with `_`.
"""
import re

_CONTROL = ("for", "if", "elif", "else", "while", "match", "case", "try",
            "except", "finally", "with")
_OPEN = re.compile(r"^(\s*)html:\s*(#.*)?$")


def _attrs(pairs):
    """PAIRS of a tag line as ('class_', '"card"') pairs."""
    out = []
    for name, value in pairs:
        name = name.replace("-", "_")
        if name in ("class", "for"):
            name += "_"
        if re.match(r"on[a-z]+$", name):               # an event handler
            value = f"__on({value})"
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
    m = re.match(r"[A-Za-z][A-Za-z0-9]*", line)
    if not m:
        raise SyntaxError(f"html: block: cannot read the line {line!r}")
    pairs, k = _scan_attrs(line, m.end())
    colon = line[k:k + 1] == ":"
    rest = line[k + 1:].strip() if colon else line[k:].strip()
    if rest.startswith("#"):
        rest = ""
    if not colon and rest:
        raise SyntaxError(f"html: block: cannot read {rest!r} in the line {line!r}")
    return (ind, "tag", m.group(0), _attrs(pairs), rest if colon else None)


def _value_end(line, k):
    """Where the attribute value that starts at LINE[k] ends: at a space or a
    `:` outside brackets and strings, so `x=str(a + b)`,
    `class=("n" if g else "b")` and `"url(#"+c[1:]+")"` are each one value."""
    depth, n = 0, len(line)
    while k < n:
        ch = line[k]
        if ch in "\"'":
            q = ch
            k += 1
            while k < n and line[k] != q:
                k += 2 if line[k] == "\\" else 1
            k += 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and (ch.isspace() or ch == ":"):
            break
        k += 1
    if depth:
        raise SyntaxError(f"html: block: unbalanced brackets in {line[:n]!r}")
    return k


def _scan_attrs(line, k):
    """The name=value pairs of a tag line from LINE[k], and where they end."""
    pairs = []
    while True:
        j = k
        while j < len(line) and line[j].isspace():
            j += 1
        m = re.compile(r"([A-Za-z_][\w-]*)=").match(line, j)
        if not m:
            return pairs, j
        end = _value_end(line, m.end())
        if end == m.end():
            raise SyntaxError(f"html: block: {m.group(1)}= has no value in {line!r}")
        pairs.append((m.group(1), line[m.end():end]))
        k = end


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
            # CSS and script are not text: `a > b` and "Segoe UI" stay as written
            raw = tag.lower() in ("style", "script")
            out.append(f"{pad}    {'__raw' if raw else '__text'}({rest})")
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
    # An event handler needs the browser side of karax (karax/karax), which
    # only compiles under `ady2nim js`; a page without one also builds native.
    karax = "karax/[karax, karaxdsl, vdom, vstyles]" if "__on(" in "\n".join(out) \
        else "karax/[karaxdsl, vdom, vstyles]"
    # Under `ady2nim js` karax's `$` of a page is a dump of its nodes, for debugging: str(page) is
    # the page's HTML there too, as natively (the stdlib's karax_text.nim).
    js_karax = karax.replace("vdom, ", "")
    head = ["# nimraw: when defined(js):",
            f"# nimraw:   import {js_karax}, karax_text",
            "# nimraw:   import karax/vdom except `$`",
            "# nimraw: else:",
            f"# nimraw:   import {karax}",
            "# nimraw: type Html = VNode"]
    if "__tag_" in "\n".join(out) and re.search(r"\bstyle\s*=", "\n".join(out)):
        head += ["# nimraw: " + ln for ln in _CSS_HELPER.split("\n")]
    if out and out[0].startswith("#!"):               # keep the shebang first
        return "\n".join([out[0]] + head + out[1:])
    return "\n".join(head + out)


_ROOT = re.compile(r"^(\s*)with __root_(\w+)\((.*)\):\s*$")
_TAGW = re.compile(r"^(\s*)with __tag_(\w+)\((.*)\):\s*$")
_VOID = re.compile(r"^(\s*)__tag_(\w+)\((.*)\)\s*$")
_EMBED = re.compile(r"^(\s*)__embed\((.*)\)\s*$")
_TEXT = re.compile(r"^(\s*)__text\((.*)\)\s*$")
_RAW = re.compile(r"^(\s*)__raw\((.*)\)\s*$")


def _karax(tag, args):
    # karax's names for the tags whose own name is taken in Nim
    tag = {"div": "tdiv", "s": "strikethrough", "i": "italic", "b": "bold",
           "u": "underlined", "text": "stext"}.get(tag, tag)
    args = re.sub(r"\bclass_=", "class=", args)
    args = re.sub(r"\bfor_=", "`for`=", args)
    # `data_hx_get=`, `marker_end=`: the page's own name has hyphens, which a
    # Nim name cannot, so it goes in backticks -- karax takes it as written
    args = re.sub(r"(^|, )([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\s*=",
                  lambda m: m.group(1) + "`" + m.group(2).replace("_", "-") + "`=", args)
    # karax's style= is a VStyle; the page writes it as CSS text
    if (m := re.search(r"(^|, )style\s*=\s*", args)):
        end = _arg_end(args, m.end())
        args = f"{args[:m.end()]}adascriptCss({args[m.end():end]}){args[end:]}"
    return tag, args


# style= as karax's VStyle. karax writes each property `name: value; ` itself,
# so a space the text has after `:` or `;` would come out doubled.
_CSS_HELPER = """\
proc adascriptCss(css: string): VStyle {.used.} =
  var t = ""
  var after = false
  for c in css:
    if after and c == ' ': continue
    after = c in {':', ';'}
    t.add c
  toCss(t)"""


def _arg_end(args, i):
    """Where the argument starting at I of ARGS ends: its top-level comma, or the end."""
    depth, quote = 0, None
    while i < len(args):
        ch = args[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch == '"':
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            return i
        i += 1
    return i


def _handlers(line):
    """LINE with each __on(expr) written as a karax handler, proc() = (expr)."""
    while (i := line.find("__on(")) >= 0:
        depth, j = 1, i + 5
        while j < len(line) and depth:
            depth += {"(": 1, ")": -1}.get(line[j], 0)
            j += 1
        line = f"{line[:i]}proc() = ({line[i + 5:j - 1]}){line[j:]}"
    return line


def finish_html_nim(nim):
    """NIM, the text of a module, with the markers turned into karax."""
    if "__tag_" not in nim and "__root_" not in nim and "__text(" not in nim \
            and "__embed(" not in nim and "__raw(" not in nim:
        return nim
    out = []
    for ln in nim.split("\n"):
        ln = _handlers(ln) if "__on(" in ln else ln
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
        elif (m := _RAW.match(ln)):
            out.append(f"{m.group(1)}verbatim {m.group(2)}")
        else:
            out.append(ln)
    return "\n".join(out)
