#!/usr/bin/env python3
"""Python 3.14 to Nim source-to-source translator using parser combinators.

Parses Python source code using the hek_parsec combinator framework
and translates it to Nim via to_nim() methods on each AST node.

Usage:
    python3 hek_py2nim.py [file.py]       # translate a file
    echo "x = 1" | python3 hek_py2nim.py  # translate from stdin
"""

import sys, os

_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_dir, ".."))
sys.path.insert(0, os.path.join(_dir, "..", "GRAMMAR"))
sys.path.insert(0, os.path.join(_dir, "..", "TO_PYTHON"))

import token as token_mod

from hek_py3_parser import *  # fw() resolves names in calling module's globals
from hek_tokenize import Tokenizer, RichNL, set_current_tokenizer

# Import Nim translation modules to register to_nim() methods
import hek_nim_parser  # noqa: F401 (registers compound stmt to_nim methods)


def Input(code):
    """Create a token stream for parsing."""
    gen = Tokenizer(code)
    set_current_tokenizer(gen)
    gen.get_new_token()  # skip ENCODING token
    return gen


def parse_module(code):
    """Parse a full module. Comments are embedded in the parse tree via RichNL."""
    from hek_parsec import ParserState
    ParserState.reset()
    stream = Input(code)
    stmts = []
    leading = []
    import token as token_mod

    # Peek at first token
    first_token = None
    try:
        first_token = stream.get_new_token()
    except StopIteration:
        pass

    if first_token is None or first_token.type == token_mod.ENDMARKER:
        return stmts, leading, []

    # Collect leading RichNL comments
    if isinstance(first_token, RichNL):
        leading.append(first_token)
        while True:
            tok = stream.get_new_token()
            if isinstance(tok, RichNL):
                leading.append(tok)
            elif tok.type == token_mod.NL:
                continue
            else:
                stream.reset(stream.mark() - 1)
                break
    else:
        stream.reset(stream.mark() - 1)

    # Parse statements with inter-statement comments
    while True:
        inter_comments = []

        # Collect RichNL comments before this statement
        while True:
            pos = stream.mark()
            try:
                tok = stream.get_new_token()
            except StopIteration:
                break
            if isinstance(tok, RichNL):
                inter_comments.append(tok)
                continue
            if tok.type == token_mod.NL:
                continue
            stream.reset(pos)
            break

        # Check for end of input
        try:
            tok = stream.get_new_token()
        except StopIteration:
            break
        if not tok or tok.type == token_mod.ENDMARKER:
            break
        stream.reset(pos)

        result = statement.parse(stream)
        if not result:
            import sys
            print(stream.format_error(), file=sys.stderr)
            break

        node = result[0]
        node._leading_comments = inter_comments
        stmts.append(node)

    return stmts, leading, []


def translate(code):
    """Parse Python source and translate to Nim via to_nim()."""
    if not code.strip():
        return code

    from hek_parsec import ParserState
    stmts, leading, trailing = parse_module(code)

    ParserState.symbol_table.push_scope("module")
    output = []

    def emit_richnl(richnl):
        """Emit lines for a RichNL (comments and/or blank lines)."""
        output.extend(richnl.to_lines())

    # Emit leading comments and blank lines
    for richnl in leading:
        emit_richnl(richnl)

    for stmt in stmts:
        # Emit inter-statement comments attached to this statement
        inter = getattr(stmt, '_leading_comments', [])
        for richnl in inter:
            emit_richnl(richnl)

        # Emit the translated Nim statement
        try:
            rendered = stmt.to_nim(0)
        except TypeError:
            rendered = stmt.to_nim()
        # Strip trailing blank lines from compound statement bodies
        rendered_lines = rendered.split('\n')
        trailing_blanks = 0
        while rendered_lines and rendered_lines[-1] == '':
            rendered_lines.pop()
            trailing_blanks += 1
        output.append('\n'.join(rendered_lines))
        for _ in range(trailing_blanks):
            output.append('')

    # Emit trailing comments
    for richnl in trailing:
        emit_richnl(richnl)

    ParserState.symbol_table.pop_scope()

    result = chr(10).join(output)
    if not result.endswith(chr(10)):
        result += chr(10)
    return result


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            code = f.read()
    else:
        code = sys.stdin.read()
    print(translate(code), end="")


###############################################################################
# Tests
###############################################################################


def run_tests():
    print("=" * 60)
    print("Python 3.14 -> Nim Translator Tests")
    print("=" * 60)

    tests = [
        # --- simple statements ---
        (
            "x = 1\n",
            "var x = 1\n",
        ),
        (
            "x = 1\ny = 2\n",
            "var x = 1\nvar y = 2\n",
        ),
        (
            "x += 1\n",
            "x += 1\n",
        ),
        (
            "x //= 2\n",
            "x = x div 2\n",
        ),
        (
            "import os\n",
            "import os\n",
        ),
        (
            "from os import path\n",
            "from os import path\n",
        ),
        (
            "pass\n",
            "discard\n",
        ),
        (
            "return x\n",
            "return x\n",
        ),
        (
            "del x\n",
            "reset(x)\n",
        ),
        (
            "global x\n",
            "# global x\n",
        ),
        (
            "assert x\n",
            "assert x\n",
        ),
        (
            "x: int = 1\n",
            "var x: int = 1\n",
        ),
        # --- compound statements ---
        (
            "if x:\n    pass\n",
            "if x:\n    discard\n",
        ),
        (
            "if x:\n    a = 1\nelif y:\n    b = 2\nelse:\n    c = 3\n",
            "if x:\n    var a = 1\nelif y:\n    var b = 2\nelse:\n    var c = 3\n",
        ),
        (
            "while x:\n    pass\n",
            "while x:\n    discard\n",
        ),
        (
            "for x in xs:\n    pass\n",
            "for x in xs:\n    discard\n",
        ),
        (
            "try:\n    pass\nexcept ValueError:\n    pass\n",
            "try:\n    discard\nexcept ValueError:\n    discard\n",
        ),
        (
            "try:\n    pass\nfinally:\n    pass\n",
            "try:\n    discard\nfinally:\n    discard\n",
        ),
        (
            "with f():\n    pass\n",
            "with f():\n    discard\n",
        ),
        (
            "def f():\n    pass\n",
            "proc f() =\n    discard\n",
        ),
        (
            "def f(a, b=1):\n    return a\n",
            "proc f(a: auto, b: auto = 1) =\n    return a\n",
        ),
        (
            "def f(a: int) -> str:\n    pass\n",
            "proc f(a: int): string =\n    discard\n",
        ),
        (
            "class Foo:\n    pass\n",
            "type Foo = object\n    discard\n",
        ),
        (
            "class Foo(Bar):\n    pass\n",
            "type Foo = object of Bar\n    discard\n",
        ),
        (
            "@dec\ndef f():\n    pass\n",
            "@dec\nproc f() =\n    discard\n",
        ),
        (
            "async def f():\n    pass\n",
            "proc f() {.async.} =\n    discard\n",
        ),
        (
            "match x:\n    case 1:\n        pass\n",
            "case x:\n    of 1:\n        discard\n",
        ),
        # --- mixed programs ---
        (
            "import os\ndef main():\n    return os\n",
            "import os\nproc main() =\n    return os\n",
        ),
        (
            "x = 1\nif x:\n    y = 2\n",
            "var x = 1\nif x:\n    var y = 2\n",
        ),
        (
            "def f():\n    pass\nclass Foo:\n    pass\n",
            "proc f() =\n    discard\ntype Foo = object\n    discard\n",
        ),
        # --- nested ---
        (
            "if x:\n    if y:\n        pass\n",
            "if x:\n    if y:\n        discard\n",
        ),
        (
            "def f():\n    for x in xs:\n        if x:\n            return x\n",
            "proc f() =\n    for x in xs:\n        if x:\n            return x\n",
        ),
        (
            "class Foo:\n    def bar(self):\n        pass\n",
            "type Foo = object\n    proc bar(self: auto) =\n        discard\n",
        ),
        # --- expressions in statements ---
        (
            "x = 10 // 3\n",
            "var x = 10 div 3\n",
        ),
        (
            "x = a ** 2\n",
            "var x = a ^ 2\n",
        ),
        (
            "x = [1, 2, 3]\n",
            "var x = @[1, 2, 3]\n",
        ),
        (
            "x = {1: 2}\n",
            "var x = {1: 2}.toTable\n",
        ),
        (
            "x = None\n",
            "var x = nil\n",
        ),
        (
            "x = True\n",
            "var x = true\n",
        ),
        (
            "x = not y\n",
            "var x = not y\n",
        ),
        # --- comments ---
        (
            "# standalone comment\nx = 1\n",
            "# standalone comment\nvar x = 1\n",
        ),
        (
            "x = 1\n\ny = 2\n",
            "var x = 1\n\nvar y = 2\n",
        ),
        (
            "# comment 1\n# comment 2\nx = 1\n",
            "# comment 1\n# comment 2\nvar x = 1\n",
        ),
    ]

    passed = failed = 0
    for code, expected in tests:
        try:
            output = translate(code)
            if output == expected:
                label = code.splitlines()[0]
                print(f"  PASS: {label!r}...")
                passed += 1
            else:
                label = code.splitlines()[0]
                print(f"  MISMATCH: {label!r}...")
                print(f"    expected: {expected!r}")
                print(f"    got:      {output!r}")
                failed += 1
        except Exception as e:
            label = code.splitlines()[0]
            print(f"  ERROR: {label!r}... -> {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        run_tests()
