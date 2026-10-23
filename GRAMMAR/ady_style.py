"""`style` blocks -- the look of what a class draws, written in the class.

    class Node_View:
        style "g.node":
            &:                  cursor="grab"
            circle:             fill=PAPER stroke=RIM stroke_width=2
            &:hover circle:     stroke=INK
            [START] circle:     fill=PALE_GREEN stroke=GREEN stroke_width=4

The block is rewritten as source text before the parse, into the field the
stdlib's style.ady reads (a `Style`, from `from style import Look, Rule, Style`):

    var style: Style = Style("g.node", [Rule("", Look(cursor="grab")), Rule(" circle", Look(...)), ...])

so both backends translate it with their ordinary machinery, and a property
that `Look` does not have is refused by the compiler as a field it does not
know.

Each line is a selector, relative to the scope, a `:` and the properties:

    circle              a circle in the element (a space before it)
    &                   the element itself; `&:hover circle`, `&.selected circle`
    [STATE] circle      the element in STATE, an enum value: [START] is the class
                        `start` (Style.class_of), which the element carries

A property is name=value, the value an expression up to a space outside
brackets and strings; `#` starts a comment.
"""
import re

_OPEN = re.compile(r'^(\s+)style\s+("(?:[^"\\]|\\.)*")\s*:\s*(#.*)?$')
_PROP = re.compile(r"([A-Za-z_]\w*)=")


def uses_style(code):
    return re.search(r'^\s+style\s+"', code, re.M) is not None


def _value_end(line, k):
    """Where the value that starts at LINE[k] ends: at a space outside brackets and strings."""
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
        elif depth == 0 and ch.isspace():
            break
        k += 1
    if depth:
        raise SyntaxError(f"style block: unbalanced brackets in {line!r}")
    return k


def _props(text, line):
    """The name=value pairs of TEXT, as `name=value` arguments of Look."""
    out, k = [], 0
    while True:
        while k < len(text) and text[k].isspace():
            k += 1
        if k >= len(text) or text[k] == "#":
            return out
        m = _PROP.match(text, k)
        if not m:
            raise SyntaxError(f"style block: a property is name=value, in {line.strip()!r}")
        end = _value_end(text, m.end())
        if end == m.end():
            raise SyntaxError(f"style block: {m.group(1)}= has no value in {line.strip()!r}")
        out.append(f"{m.group(1)}={text[m.end():end]}")
        k = end


def _part(selector, line):
    """SELECTOR, relative to the scope, as the expression of the part that follows the scope."""
    if selector.startswith("&"):
        return '"' + selector[1:] + '"'
    m = re.match(r"\[([A-Za-z_]\w*)\](.*)$", selector)
    if m:
        rest = m.group(2)
        if rest.startswith("&"):
            rest = rest[1:]
        elif rest and not rest[0].isspace():
            raise SyntaxError(f"style block: after [{m.group(1)}], a space or &, in {line.strip()!r}")
        return f'"." + str({m.group(1)}).lower() + "{rest}"'
    if not selector or "[" in selector or '"' in selector:
        raise SyntaxError(f"style block: cannot read the selector {selector!r}")
    return '" ' + selector + '"'


def _rule(line):
    """A rule line, `selector: properties`, as a Rule(...) expression."""
    text = line.strip()
    # the selector ends at the first `:` followed by a space or the end: `&:hover circle:` reads whole
    k = 0
    while True:
        k = text.find(":", k)
        if k < 0:
            raise SyntaxError(f"style block: a rule is `selector: name=value ...`, in {text!r}")
        if k + 1 == len(text) or text[k + 1].isspace():
            break
        k += 1
    selector, props = text[:k].strip(), text[k + 1:]
    return f"Rule({_part(selector, line)}, Look({', '.join(_props(props, line))}))"


def expand_style_blocks(code):
    """CODE with every `style "scope":` block in a class written out as the field `style`."""
    if not uses_style(code):
        return code
    lines = code.split("\n")
    out = []
    i = 0
    in_string = False
    while i < len(lines):
        line = lines[i]
        m = None if in_string else _OPEN.match(line)
        if line.count('"""') % 2 == 1:
            in_string = not in_string
        if not m:
            out.append(line)
            i += 1
            continue
        base = len(m.group(1))
        rules = []
        start = i
        i += 1
        while i < len(lines):
            body = lines[i]
            if body.strip() == "" or body.strip().startswith("#"):
                i += 1
                continue
            if len(body) - len(body.lstrip()) <= base:
                break
            rules.append(_rule(body))
            i += 1
        out.append(f"{m.group(1)}var style: Style = Style({m.group(2)}, [{', '.join(rules)}])")
        out.extend([""] * (i - start - 1))        # the same number of lines, so errors keep their line
    return "\n".join(out)
