#!/usr/bin/env python3
"""Shared helper functions for compound statement translators.

Used by both TO_PYTHON/hek_py_parser.py and TO_NIM/hek_nim_parser.py.
"""

from hek_tokenize import RichNL

###############################################################################
# Indentation
###############################################################################

INDENT_STR = "    "


def _ind(level):
    """Return indentation string for the given nesting level."""
    return INDENT_STR * level


###############################################################################
# RichNL helpers
###############################################################################

def _richnl_lines(richnl_node):
    """Extract trivia lines from a RichNL or NL wrapper node.

    Returns a list of strings, or None if the node is not a RichNL.
    """
    rn = RichNL.extract_from(richnl_node)
    return rn.to_lines() if rn is not None else None


def _block_inline_header_comment(block_node):
    """Return the inline comment string on the compound header, or ''."""
    if not block_node or not block_node.nodes:
        return ''
    rn = RichNL.extract_from(block_node.nodes[0])
    return rn.inline_comment() if rn is not None else ''


###############################################################################
# Block statement helpers
###############################################################################

def _block_last_stmt(block_node):
    """Return the last stmt_line node in a block, or None.

    Walks the block's Several_Times children to find the last statement,
    skipping NL/trivia nodes.
    """
    last_stmt = None
    if not block_node or not hasattr(block_node, 'nodes'):
        return None
    for node in block_node.nodes:
        if type(node).__name__ == "Several_Times":
            for seq in node.nodes:
                if type(seq).__name__ == "Sequence_Parser" and hasattr(seq, "nodes"):
                    for child in seq.nodes:
                        if child is None:
                            continue
                        if type(child).__name__ != "Several_Times":
                            last_stmt = child
    return last_stmt


###############################################################################
# Assignment targets that are reads
###############################################################################

# The `$…` forms, all of which read something the program does not own.
# ENVOPT rather than env_optional: `$?NAME` is a single token, so the node
# that reaches an assignment target is the token parser's, named for it.
_DOLLAR_TARGETS = ("dollar_var", "env_default", "env_optional", "ENVOPT", "ENVDEF")


def _leftmost_spine(node, limit=12):
    """The chain of node class names down a node's first child.

    An assignment target arrives wrapped in the expression grammar --
    star_expressions > disjunction > comparison > power > primary > … -- and
    what it really is sits at the bottom of that chain.
    """
    names = []
    for _ in range(limit):
        names.append(type(node).__name__)
        kids = getattr(node, "nodes", None)
        if not kids:
            break
        node = kids[0]
    return names


def _dollar_target_name(node, limit=12):
    """The `$…` node at the bottom of TARGET's spine, with its name.

    Returns (kind, name) -- kind being the grammar rule, name the text after
    the `$` where it can be read -- or None when the target is an ordinary
    one.
    """
    for _ in range(limit):
        tname = type(node).__name__
        if tname in _DOLLAR_TARGETS:
            name = ""
            raw = getattr(node, "node", None)
            kids = getattr(node, "nodes", None) or []
            for cand in [raw] + list(kids):
                got = getattr(cand, "node", cand)
                text = getattr(got, "string", got)
                if isinstance(text, str) and text and text != "$":
                    name = text
                    break
            return tname, name
        kids = getattr(node, "nodes", None)
        if not kids:
            return None
        node = kids[0]
    return None


def reject_dollar_assignment(target_node, op="="):
    """Refuse an assignment whose target is a `$…` read.

    `$PATH = "x:" + $PATH` looks like the shell's `export`, and the grammar
    takes it -- an assignment target is any expression -- so both backends
    used to emit the *read* into target position and hand the mistake to the
    generated file: `os.environ.get('PATH', '') = …` is a Python SyntaxError
    about a function call, and `var getEnv("PATH") = …` is a nim parse error.
    Neither names the line that caused it.

    The environment is not writable here by design, and the design has a
    point: a process's own environment reaches nothing but the commands it
    starts, and those take one directly.
    """
    found = _dollar_target_name(target_node)
    if found is None:
        return
    kind, name = found
    shown = f"${name}" if name and kind == "dollar_var" else "the environment"
    if kind == "dollar_var" and name and (name.isdigit() or name in ("@", "#", "0")):
        raise SyntaxError(
            f"'{shown} {op} ...' assigns to an argument, which is read-only.\n"
            f"  Copy it first:\n"
            f"      var arg: str = {shown}"
        )
    raise SyntaxError(
        f"'{shown} {op} ...' assigns to the environment, which is read-only.\n"
        f"  A program's own environment reaches nothing but the commands it\n"
        f"  starts, and those take one directly:\n"
        f"      let extra: {{str}}str = {{\"PATH\": \"dddd:\" + $PATH}}\n"
        f"      shell(env = extra): make\n"
        f"  `run(argv, env = extra)` and `shellExec(env = extra)` take the\n"
        f"  same option, and it adds to the child's environment rather than\n"
        f"  replacing it."
    )
