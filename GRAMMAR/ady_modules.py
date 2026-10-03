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
`from M nimport *` brings in everything, as `from M import *` does. Neither form of `from`
binds M: `M.name` needs `import M`, and without it is refused, as Python's NameError would.

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
    edits, renames = [], []
    plain_mods, plain_names, import_spans = set(), {}, []

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
            if alias and alias.strip() != mod.rsplit("/", 1)[-1]:
                renames.append(("qualifier", alias.strip(), mod.rsplit("/", 1)[-1], m.start()))
            else:
                plain_mods.add(mod)
            adys.append(mod)
        import_spans.append((m.start(), m.end()))
        edits.append((m.start("kw"), m.end("names"), f"nimport {', '.join(adys)}"))
    for m in _FROM_IMPORT.finditer(text):
        mod = m.group("mod")
        if is_ady(mod):
            edits.append((m.start("kw"), m.end("kw"), "nimport"))
            rest = code[m.start("rest"):m.end("rest")]
            import_spans.append((m.start(), m.end()))
            for old, new in re.findall(r"(\w+)(?:[ \t]+as[ \t]+(\w+))?", text[m.start("rest"):m.end("rest")]):
                if new and new != old:
                    renames.append(("name", new, old, m.start(), mod))
                elif old != "as":
                    plain_names.setdefault(mod, set()).add(old)
            edits.append((m.start("rest"), m.end("rest"), re.sub(r"[ \t]+as[ \t]+\w+", "", rest)))
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
    # what a rename takes away, Python does not give: `from M import A as B` binds B and
    # not A, `import M as N` binds N and not M
    def outside_imports(pattern):
        return next((u for u in re.finditer(pattern, text)
                     if not any(a <= u.start() < b for a, b in import_spans)), None)

    for r in renames:
        kind, new, old, pos = r[:4]
        if kind == "name":
            if old in plain_names.get(r[4], ()) or _binds(text, old):
                continue
            use = outside_imports(rf'(?<![\w.$]){re.escape(old)}\b')
            if use:
                raise SyntaxError(f"line {line(use.start())}: '{old}' is imported from {r[4]} as '{new}': "
                                  f"write {new}")
        elif old not in {m.rsplit("/", 1)[-1] for m in plain_mods} and not _binds(text, old):
            use = outside_imports(rf'(?<![\w.$]){re.escape(old)}(?=\.\w)')
            if use:
                raise SyntaxError(f"line {line(use.start())}: '{old}' is imported as '{new}': write {new}.name")
    for a, b, new in sorted(edits, reverse=True):
        code = code[:a] + new + code[b:]
    # a rename is a rewrite of the new name to the old one, where the file means the import
    for kind, new, old, pos, *_ in renames:
        text = _blank(code)
        if kind == "name" and _binds(text, new):
            raise SyntaxError(f"line {line(pos)}: '{new}' is renamed from {old} but the file gives "
                              f"'{new}' a meaning of its own")
        pattern = rf'(?<![\w.$]){re.escape(new)}(?=\.\w)' if kind == "qualifier" else rf'(?<![\w.$]){re.escape(new)}\b'
        code = "".join(old if i % 2 else part for i, part in enumerate(
            _split_matches(code, [(m.start(), m.end()) for m in re.finditer(pattern, text)])))
    return code


def _split_matches(code, spans):
    """CODE cut at SPANS: the parts between them and the parts they cover,
    alternating, so that the covered parts can be replaced."""
    out, last = [], 0
    for a, b in spans:
        out += [code[last:a], code[a:b]]
        last = b
    return out + [code[last:]]

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
    keeping the lines, so that what is left is what the program names. The
    `{...}` of an f-string is code, and stays."""
    def keep_newlines(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    def string(m):
        if not re.search(r"(?<![\w])(?:[rR][fF]|[fF][rR]|[fF])$", code[max(0, m.start() - 3):m.start()]):
            return keep_newlines(m)
        # a format string: the literal parts go, the `{...}` expressions stay
        return re.sub(r"\{\{|\}\}|\{[^{}\n]*\}|[^\n]",
                      lambda t: t.group(0) if t.group(0)[0] == "{" and len(t.group(0)) > 2 else " " * len(t.group(0)),
                      m.group(0))
    code = re.sub(r'"""[\s\S]*?"""', string, code)
    code = re.sub(r'"(?:\\.|[^"\\\n])*"', string, code)
    code = re.sub(r"'(?:\\.|[^'\\\n])*'", string, code)
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
    for m in re.finditer(r'^type[ \t]+(\w+)[^\n]*?\bis[ \t]+enum[ \t]*:?[ \t]*(?P<rest>[^\n]*)((?:\n[ \t]+\w+(?:[ \t]*=[ \t]*\d+)?[ \t]*(?:,[ \t]*\w+(?:[ \t]*=[ \t]*\d+)?)*[ \t]*(?=\n|$))*)',
                         text, re.MULTILINE):
        # a member's value (`A = 1`) is not a member
        listed = re.sub(r"=[ \t]*\d+", " ", m.group("rest") + " " + (m.group(3) or ""))
        names = re.findall(r"\w+", listed)
        for member in names:
            out.setdefault(member, m.group(1))
    return out


def _binds(text, name):
    """Does the (blanked) TEXT give NAME a meaning of its own: declared, a loop
    variable, a parameter or field, an assignment target, a keyword argument --
    not `x: Name = ...`, which uses it."""
    return re.search(
        rf'(?:\b(?:let|var|const|def|class|type|for)[ \t]+(?:\w+[ \t]*,[ \t]*)*{re.escape(name)}\b)'
        rf'|(?:^|[(,])[ \t]*{re.escape(name)}[ \t]*(?::|=(?!=))', text, re.MULTILINE)


def resolve_imports(code, module, listed, module_source):
    """CODE with `M.name` written `name`, after refusing a use of a name of
    MODULE's that is neither qualified nor in LISTED (STAR: nothing to refuse)."""
    qual = module.rsplit("/", 1)[-1]
    names = exported(module_source)
    # `M.name` is Python's too: only `import M` binds M. `from M import A, B` (or `*`) binds
    # A and B and not M, so `M.A` there is a name that does not exist.
    bare = re.search(rf'^nimport[ \t]+(?:[\w./]+[ \t]*,[ \t]*)*{re.escape(module)}\b', code, re.MULTILINE)
    if not bare:
        text = _blank(code)
        use = next((u for u in re.finditer(rf'(?<![\w.$]){re.escape(qual)}\.(\w+)', text)
                    if u.group(1) in names), None)
        if use and not _binds(text, qual):
            line = text.count("\n", 0, use.start()) + 1
            raise SyntaxError(
                f"line {line}: '{use.group(0)}' needs `import {module}`: "
                f"`from {module} import ...` does not bind '{qual}', as in Python")
    if listed is STAR:
        return code
    allowed = set(listed)
    for n in list(names):
        if names[n] in allowed:        # an enum member comes with its type
            allowed.add(n)
    text = _blank(code)

    for name, owner in sorted(names.items()):
        if name in allowed:
            continue
        use = re.search(rf'(?<![\w.$]){re.escape(name)}\b', text)
        if not use or _binds(text, name):
            continue                   # unused, or a name of the file's own
        line = text.count("\n", 0, use.start()) + 1
        what = f"'{name}'" if owner == name else f"'{name}' (a member of {owner})"
        from_list = f"`from {module} import {', '.join(sorted(set(listed) | {owner}))}`"
        # `M.name` is Python's too: it needs `import M`, which a from-import alone is not
        if bare:
            fix = f"write {qual}.{name}, or add {owner} to {from_list}"
        else:
            fix = f"add {owner} to {from_list}, or `import {module}` and write {qual}.{name}"
        raise SyntaxError(f"line {line}: {what} is not imported from {module}: {fix}")
    out, last = [], 0
    for m in re.finditer(rf'(?<![\w.$]){re.escape(qual)}\.(\w+)', text):
        name = m.group(1)
        if name not in names:
            continue
        if _binds(text, name):
            line = text.count("\n", 0, m.start()) + 1
            raise SyntaxError(
                f"line {line}: '{qual}.{name}' cannot be told from this file's own '{name}': "
                f"the modules are merged into one namespace, so rename one of them")
        out.append(code[last:m.start()]); out.append(name); last = m.end()
    out.append(code[last:])
    return "".join(out)


# What the common Nim modules a file `nimport`s hand out, so that a bare use of one of
# their names is refused here, with the line and what to do, as it is for an .ady module,
# rather than by Nim's compiler at a line of generated code (or, on the Python backend, by
# a NameError at run time). Only names that are unmistakably the module's: a function counts
# when it is called bare (`sqrt(x)`; `x.strip()` is a method of the value, not a use), a
# constant or type when it appears at all. Other Nim modules are left to Nim's compiler.
_NIM_CALLS = {
    "math": "sqrt cbrt sin cos tan arcsin arccos arctan arctan2 sinh cosh tanh exp ln log2 log10 "
            "pow floor ceil trunc hypot degToRad radToDeg fac gcd lcm isNaN",
    "os": "getCurrentDir setCurrentDir fileExists dirExists walkDir walkFiles createDir removeFile "
          "removeDir copyFile moveFile joinPath splitFile splitPath extractFilename expandTilde "
          "getHomeDir getTempDir paramStr paramCount commandLineParams execShellCmd getAppFilename",
    "strutils": "strip startsWith endsWith toUpperAscii toLowerAscii parseInt parseFloat parseBool "
                "parseHexInt align alignLeft center indent unindent splitLines splitWhitespace",
    "sequtils": "filterIt mapIt anyIt allIt countIt toSeq maxIndex minIndex foldl foldr keepIf "
                "applyIt newSeqWith deduplicate distribute",
    "random": "rand randomize sample shuffle initRand gauss",
    "algorithm": "sortedByIt binarySearch lowerBound upperBound nextPermutation isSorted",
    "time": "cpuTime epochTime getTime getLocalTime getGMTime initDuration initTime toUnix fromUnix",
    "json": "parseJson newJObject newJArray newJString newJInt newJFloat newJBool newJNull "
            "getStr getInt getFloat getBool getElems getFields",
}
_NIM_NAMES = {
    "math": "PI TAU",
    "json": "JsonNode",
    "random": "Rand",
}


def refuse_bare_nim_names(code, is_ady):
    """Refuse a bare use of a name of a Nim module the file `nimport`s -- in the
    normalized form, where `import M` of an .ady module is `nimport M` too, IS_ADY(name)
    says which are .ady and so not this function's."""
    imports = import_map(code)
    text = _blank(code)
    for module, listed in imports.items():
        if is_ady(module) or listed is STAR or module not in _NIM_CALLS and module not in _NIM_NAMES:
            continue
        calls = set(_NIM_CALLS.get(module, "").split())
        plain = set(_NIM_NAMES.get(module, "").split())
        bare = re.search(rf'^nimport[ \t]+(?:[\w./]+[ \t]*,[ \t]*)*{re.escape(module)}\b', code, re.MULTILINE)
        for name in sorted(calls | plain):
            if name in listed:
                continue
            pattern = rf'(?<![\w.$]){re.escape(name)}\b' + (r'(?=[ \t]*\()' if name in calls else '')
            use = next((u for u in re.finditer(pattern, text)
                        if not text[:u.start()].rstrip().endswith(("def", "class", "type"))), None)
            if not use or _binds(text, name):
                continue               # unused, or a name of the file's own
            line = text.count("\n", 0, use.start()) + 1
            from_list = f"`from {module} nimport {', '.join(sorted(set(listed) | {name}))}`"
            fix = (f"write {module}.{name}, or add {name} to {from_list}" if bare else
                   f"add {name} to {from_list}, or `nimport {module}` and write {module}.{name}")
            raise SyntaxError(f"line {line}: '{name}' is not imported from {module}: {fix}")
