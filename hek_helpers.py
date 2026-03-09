#!/usr/bin/env python3
"""Shared helper functions for compound statement translators.

Used by both TO_PYTHON/hek_py3_parser.py and TO_NIM/hek_nim_parser.py.
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
