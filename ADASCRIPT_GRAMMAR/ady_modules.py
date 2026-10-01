"""What a file may use of the modules it imports -- Python's rule.

Three words name three worlds: `import` an .ady module, `nimport` a Nim one,
`pyimport` a Python one. `normalize_imports` holds the first to that -- a plain
`import` of anything but an .ady module, and a `nimport` of an .ady module, are
refused -- and writes the .ady imports in the `nimport` form the rest of the
pipeline reads. The rest of this file is written in that form: `nimport M` is
what `import M` becomes.

`nimport M` binds M, as Python's `import M` does: the file reaches M's names as
`M.name`, and a bare `name` is refused. `from M nimport A, B` is the selective
form, as `from M import A, B`: the file may use A and B unqualified, and what
they carry (an enum's members; a class's methods and a record's fields are
reached through a value, not by name), and nothing else of M's unqualified.
`from M nimport *` brings in everything, as `from M import *` does.

Both backends bring the whole module in -- ady2nim links it, ady2py merges it --
so the rule is checked here, from the text, the same way for both: a name of M's
that the file uses without qualifying or listing it is refused, and the message
says what to do. What passes is rewritten, `M.name` to `name`, so that neither
backend has to know about qualified names. For `nimport lib/geom` the qualifier
is `geom`, the last part, as in Nim. A file that declares a name of its own that
M also declares cannot use `M.name` -- the merge has one namespace -- and is told.
"""
import re

_PLAIN_IMPORT = re.compile(r'^(?P<ind>[ \t]*)(?P<kw>import)[ \t]+(?P<names>[^\n]+?)[ \t]*$', re.MULTILINE)
_FROM_IMPORT = re.compile(
    r'^(?P<ind>[ \t]*)from[ \t]+(?P<mod>\w[\w./]*)[ \t]+(?P<kw>import)\b[ \t]*(?P<rest>\([^)]*\)|[^\n]*?)[ \t]*$',
    re.MULTILINE)
_NIM_IMPORT = re.compile(r'^(?P<ind>[ \t]*)nimport[ \t]+(?P<names>[^\n]+?)[ \t]*$', re.MULTILINE)
_FROM_NIMPORT = re.compile(r'^(?P<ind>[ \t]*)from[ \t]+(?P<mod>\w[\w./]*)[ \t]+nimport\b', re.MULTILINE)
_SHIM = "stdlib"      # the bundled shim: one library, a Nim and a Python implementation


def normalize_imports(code, is_ady):
    """CODE with `import M` / `from M import A` of an .ady module written
    `nimport M` / `from M nimport A`; IS_ADY(name) says whether a name is one.

    Refused: `import X` or `from X import A` of anything else (`nimport` is for
    Nim modules, `pyimport` for Python ones; `from stdlib import X` stays), and
    `nimport X` of an .ady module (it is `import X`)."""
    text = _blank(code)
    edits = []

    def line(pos):
        return text.count("\n", 0, pos) + 1

    def refuse_plain(mod, pos, form):
        raise SyntaxError(
            f"line {line(pos)}: '{form}' is not allowed: {mod} is not an .ady module. "
            f"Use 'nimport {mod}' for Nim/stdlib modules or 'pyimport {mod}' for Python packages.")

    for m in _PLAIN_IMPORT.finditer(text):
        adys = []
        for item in (i.strip() for i in code[m.start("names"):m.end("names")].split(",")):
            mod, _, alias = item.partition(" as ")
            mod = mod.strip()
            if not is_ady(mod):
                refuse_plain(mod, m.start(), f"import {mod}")
            if alias:
                raise SyntaxError(f"line {line(m.start())}: 'import {mod} as {alias.strip()}' is not supported: "
                                  f"write {mod}.name, or `from {mod} import name`")
            adys.append(mod)
        edits.append((m.start("kw"), m.end("names"), f"nimport {', '.join(adys)}"))
    for m in _FROM_IMPORT.finditer(text):
        mod = m.group("mod")
        if is_ady(mod):
            edits.append((m.start("kw"), m.end("kw"), "nimport"))
        elif mod != _SHIM:
            refuse_plain(mod, m.start(), f"from {mod} import")
    for m in _NIM_IMPORT.finditer(text):
        for item in (i.strip() for i in code[m.start("names"):m.end("names")].split(",")):
            if is_ady(item):
                raise SyntaxError(f"line {line(m.start())}: '{item}' is an .ady module: write `import {item}`, "
                                  f"`nimport` is for Nim modules")
    for m in _FROM_NIMPORT.finditer(text):
        if is_ady(m.group("mod")):
            raise SyntaxError(f"line {line(m.start())}: '{m.group('mod')}' is an .ady module: write "
                              f"`from {m.group('mod')} import ...`, `nimport` is for Nim modules")
    for a, b, new in sorted(edits, reverse=True):
        code = code[:a] + new + code[b:]
    return code

# `from M nimport A, B`, `from M nimport *`, and the parenthesised form that may
# run over lines, with comments among the names
_FROM_RE = re.compile(
    r'^from[ \t]+(?P<module>\w[\w./]*)[ \t]+nimport[ \t]+'
    r'(?:\((?P<paren>[^)]*)\)|(?P<names>[^#\n]+?))[ \t]*(?:#[^\n]*)?$',
    re.MULTILINE)
_BARE_RE = re.compile(
    r'^nimport[ \t]+(?P<names>\w[\w./]*(?:[ \t]*,[ \t]*\w[\w./]*)*)', re.MULTILINE)


STAR = None        # `from M nimport *`: everything, unqualified


def import_map(code):
    """{module: names} for every module the file imports: [] for a bare
    `nimport M`, the listed names for `from M nimport A, B`, STAR for `*`."""
    out = {}

    def add(mod, names):
        if mod in out and out[mod] is STAR:
            return
        out[mod] = STAR if names is STAR else out.get(mod, []) + names
    for m in _BARE_RE.finditer(code):
        for n in m.group("names").split(","):
            add(n.strip(), [])
    for m in _FROM_RE.finditer(code):
        text = m.group("paren") if m.group("paren") is not None else m.group("names")
        text = re.sub(r"#[^\n]*", "", text)
        names = [n.strip() for n in text.split(",") if n.strip()]
        add(m.group("module"), STAR if names == ["*"] else names)
    return out


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


def resolve_imports(code, module, listed, module_source):
    """CODE with `M.name` written `name`, after refusing a use of a name of
    MODULE's that is neither qualified nor in LISTED (STAR: nothing to refuse)."""
    if listed is STAR:
        return code
    qual = module.rsplit("/", 1)[-1]
    names = exported(module_source)
    allowed = set(listed)
    for n in list(names):
        if names[n] in allowed:        # an enum member comes with its type
            allowed.add(n)
    text = _blank(code)

    def binds(name):
        # a name of its own: declared, a loop variable, a parameter or field, an
        # assignment target, a keyword argument -- not `x: Name = ...`, which uses it
        return re.search(
            rf'(?:\b(?:let|var|const|def|class|type|for)[ \t]+(?:\w+[ \t]*,[ \t]*)*{re.escape(name)}\b)'
            rf'|(?:^|[(,])[ \t]*{re.escape(name)}[ \t]*(?::|=(?!=))', text, re.MULTILINE)

    for name, owner in sorted(names.items()):
        if name in allowed:
            continue
        use = re.search(rf'(?<![\w.$]){re.escape(name)}\b', text)
        if not use or binds(name):
            continue                   # unused, or a name of the file's own
        line = text.count("\n", 0, use.start()) + 1
        what = f"'{name}'" if owner == name else f"'{name}' (a member of {owner})"
        raise SyntaxError(
            f"line {line}: {what} is not imported from {module}: write {qual}.{name}, "
            f"or add {owner} to `from {module} nimport {', '.join(sorted(set(listed) | {owner}))}`")
    out, last = [], 0
    for m in re.finditer(rf'(?<![\w.$]){re.escape(qual)}\.(\w+)', text):
        name = m.group(1)
        if name not in names:
            continue
        if binds(name):
            line = text.count("\n", 0, m.start()) + 1
            raise SyntaxError(
                f"line {line}: '{qual}.{name}' cannot be told from this file's own '{name}': "
                f"the modules are merged into one namespace, so rename one of them")
        out.append(code[last:m.start()]); out.append(name); last = m.end()
    out.append(code[last:])
    return "".join(out)
