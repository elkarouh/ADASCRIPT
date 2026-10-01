"""What `from M nimport A, B` lets a file use of M.

`nimport M` brings in everything M declares, as `from M import *` does.
`from M nimport A, B` is the selective form: the file may use A and B, and what
they carry (an enum's members; a class's methods and a record's fields are
reached through a value, not by name), and nothing else of M's. Both backends
bring the whole module in -- ady2nim links it, ady2py merges it -- so the rule
is checked here, from the text, the same way for both: a name of M's that the
file uses without having listed it is refused, and the message says what to add.
"""
import re

# `from M nimport A, B` and `from M nimport *`; a name may carry a comment after it
_FROM_RE = re.compile(
    r'^from[ \t]+(?P<module>\w[\w./]*)[ \t]+nimport[ \t]+(?P<names>[^#\n]+?)[ \t]*(?:#[^\n]*)?$',
    re.MULTILINE)
_BARE_RE = re.compile(
    r'^nimport[ \t]+(?P<names>\w[\w./]*(?:[ \t]*,[ \t]*\w[\w./]*)*)', re.MULTILINE)


def selective_imports(code):
    """{module: [names]} for each module the file imports only by name.

    A module that is also imported whole (`nimport M`, or `from M nimport *`)
    is not here: the whole module wins."""
    whole, listed = set(), {}
    for m in _BARE_RE.finditer(code):
        whole.update(n.strip() for n in m.group("names").split(","))
    for m in _FROM_RE.finditer(code):
        names = [n.strip() for n in m.group("names").split(",") if n.strip()]
        if names == ["*"]:
            whole.add(m.group("module"))
        else:
            listed.setdefault(m.group("module"), []).extend(names)
    return {mod: names for mod, names in listed.items() if mod not in whole}


def _blank(code):
    """CODE with its comments and the insides of its strings and chars blanked,
    keeping the lines, so that what is left is what the program names."""
    def keep_newlines(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    code = re.sub(r'"""[\s\S]*?"""', keep_newlines, code)
    code = re.sub(r'"(?:\\.|[^"\\\n])*"', keep_newlines, code)
    code = re.sub(r"'(?:\\.|[^'\\\n])*'", keep_newlines, code)
    return re.sub(r"#[^\n]*", keep_newlines, code)


def exported(source):
    """{name: owner} for what a module declares at its top level. The owner is the
    name itself, or the enum type an enum member belongs to."""
    out = {}
    text = _blank(source)
    for m in re.finditer(r'^(?:@\w+[ \t]*\n)*(?:async[ \t]+)?(?:def|class|const|let|var)[ \t]+(\w+)', text, re.MULTILINE):
        out[m.group(1)] = m.group(1)
    for m in re.finditer(r'^type[ \t]+(\w+)', text, re.MULTILINE):
        out[m.group(1)] = m.group(1)
    # an enum's members: `type K is enum A, B, C` or the block form
    for m in re.finditer(r'^type[ \t]+(\w+)[^\n]*?\bis[ \t]+enum[ \t]*:?[ \t]*(?P<rest>[^\n]*)((?:\n[ \t]+\w+[ \t]*(?:,[ \t]*\w+)*[ \t]*(?=\n|$))*)',
                         text, re.MULTILINE):
        names = re.findall(r"\w+", m.group("rest")) + re.findall(r"\w+", m.group(3) or "")
        for member in names:
            out.setdefault(member, m.group(1))
    return out


def check_from_imports(code, module, listed, module_source):
    """Refuse a use, in CODE, of a name of MODULE's that LISTED does not include."""
    names = exported(module_source)
    allowed = set(listed)
    for n in list(names):
        if names[n] in allowed:        # an enum member comes with its type
            allowed.add(n)
    text = _blank(code)
    for name, owner in sorted(names.items()):
        if name in allowed:
            continue
        use = re.search(rf'(?<![\w.$]){re.escape(name)}\b', text)
        if not use:
            continue
        # a name of its own: declared, a loop variable, a parameter or field, an
        # assignment target, a keyword argument -- not `x: Name = ...`, which uses it
        bound = re.search(
            rf'(?:\b(?:let|var|const|def|class|type|for)[ \t]+(?:\w+[ \t]*,[ \t]*)*{re.escape(name)}\b)'
            rf'|(?:^|[(,])[ \t]*{re.escape(name)}[ \t]*(?::|=(?!=))', text, re.MULTILINE)
        if bound:
            continue                   # the file has a name of its own that way
        line = text.count("\n", 0, use.start()) + 1
        what = f"'{name}'" if owner == name else f"'{name}' (a member of {owner})"
        add = owner
        raise SyntaxError(
            f"line {line}: {what} is not imported from {module}: "
            f"add {add} to `from {module} nimport {', '.join(sorted(set(listed) | {add}))}`")
