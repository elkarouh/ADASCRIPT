#!/usr/bin/env python3
"""Ada Indent LSP Server — thin wrapper around the ada_indent binary.

Provides textDocument/formatting, textDocument/rangeFormatting, and
textDocument/onTypeFormatting by piping buffer content through ada_indent.

Maintains per-document state cache for incremental re-indentation
(same strategy as ada-indent.el).

Usage:
    python3 ada-indent-lsp.py [--ada-indent PATH]

    --ada-indent PATH   Path to ada_indent binary (default: ada_indent on PATH)

Register in eglot:
    (add-to-list 'eglot-server-programs
                 '(ada-mode . ("python3" "/path/to/ada-indent-lsp.py")))
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Optional

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

ADA_INDENT_BIN = "ada_indent"

# Keywords that trigger auto-dedent when typed as a bare line
DEDENT_KEYWORDS = {
    "begin", "end", "else", "elsif", "when", "exception",
    "is", "then", "private", "limited", "record", "loop", "do", "select",
}

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-document state
# ---------------------------------------------------------------------------

class DocState:
    """Cache for a single document's indenter state."""

    __slots__ = ("content", "state_data", "state_lnum")

    def __init__(self, content: str):
        self.content = content
        self.state_data: Optional[str] = None  # serialised indenter state
        self.state_lnum: int = 0                # 1-based line after which state was captured


# ---------------------------------------------------------------------------
# Core: call ada_indent
# ---------------------------------------------------------------------------

def compute_indent(
    ada_indent_bin: str,
    lines: list[str],
    cached_state: Optional[str] = None,
    start_line: int = 1,
) -> tuple[list[tuple[int, int]], Optional[str], int]:
    """Run ada_indent on *lines* and return indentation edits.

    Parameters
    ----------
    ada_indent_bin : path to the binary
    lines : source lines (no trailing newline)
    cached_state : previously emitted state, or None for full parse
    start_line : 1-based line number of the first element of *lines*

    Returns
    -------
    edits : list of (0-based line index, new indent column)
    state : last emitted state (or None)
    state_lnum : 1-based line number after which *state* was captured
    """
    input_text = "\n".join(lines)
    if not input_text:
        return [], None, 0

    cmd = [ada_indent_bin, "--emit-state"]
    if cached_state:
        cmd[1:1] = ["--state", cached_state]

    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        log.error("ada_indent failed: %s", exc)
        return [], None, 0

    if result.returncode != 0:
        log.warning("ada_indent returned %d: %s", result.returncode, result.stderr)

    out_lines = result.stdout.split("\n")
    code_lines: list[str] = []
    last_state: Optional[str] = None
    state_lnum = 0

    line_idx = start_line
    for raw in out_lines:
        if raw.startswith("##STATE:"):
            # State is emitted AFTER the code line it describes; line_idx has
            # already been incremented past that line, so subtract 1.
            last_state = raw[8:]
            state_lnum = line_idx - 1
        elif raw or code_lines:  # skip leading empty, keep trailing
            code_lines.append(raw)
            line_idx += 1

    edits: list[tuple[int, int]] = []
    for i, indented in enumerate(code_lines):
        new_indent = len(indented) - len(indented.lstrip())
        edits.append((start_line - 1 + i, new_indent))

    return edits, last_state, state_lnum


def make_text_edits(
    original_lines: list[str],
    indent_results: list[tuple[int, int]],
) -> list[lsp.TextEdit]:
    """Convert indent columns into LSP TextEdits that replace leading whitespace."""
    text_edits: list[lsp.TextEdit] = []
    for line_idx, new_indent in indent_results:
        if line_idx >= len(original_lines):
            continue
        orig = original_lines[line_idx]
        old_indent = len(orig) - len(orig.lstrip())
        if old_indent == new_indent:
            continue
        text_edits.append(lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=line_idx, character=0),
                end=lsp.Position(line=line_idx, character=old_indent),
            ),
            new_text=" " * new_indent,
        ))
    return text_edits


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

server = LanguageServer(
    "ada-indent-lsp", "v1.0",
    text_document_sync_kind=lsp.TextDocumentSyncKind.Incremental,
)
documents: dict[str, DocState] = {}


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams):
    uri = params.text_document.uri
    documents[uri] = DocState(params.text_document.text)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: lsp.DidChangeTextDocumentParams):
    uri = params.text_document.uri
    doc = documents.get(uri)
    if not doc:
        return

    for change in params.content_changes:
        if hasattr(change, 'range') and change.range is not None:
            # Incremental — invalidate cache if edit is before cache point
            start_line = change.range.start.line + 1  # 1-based
            if doc.state_data and start_line < doc.state_lnum:
                doc.state_data = None
                doc.state_lnum = 0
            # Apply the change to our stored content
            doc.content = _apply_change(doc.content, change)
        else:
            # Full content replacement
            doc.content = change.text
            doc.state_data = None
            doc.state_lnum = 0


def _apply_change(
    content: str,
    change: lsp.TextDocumentContentChangeEvent_Type1,
) -> str:
    """Apply an incremental change to document content."""
    lines = content.split("\n")
    start = change.range.start
    end = change.range.end

    # Convert to string positions
    prefix_lines = lines[:start.line]
    if start.line < len(lines):
        prefix_lines.append(lines[start.line][:start.character])
    before = "\n".join(prefix_lines)

    after_line = end.line
    if after_line < len(lines):
        after = lines[after_line][end.character:]
        if after_line + 1 < len(lines):
            after += "\n" + "\n".join(lines[after_line + 1:])
    else:
        after = ""

    return before + change.text + after


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams):
    documents.pop(params.text_document.uri, None)


@server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(params: lsp.DocumentFormattingParams) -> list[lsp.TextEdit]:
    """Format the entire document."""
    doc = documents.get(params.text_document.uri)
    if not doc:
        return []

    lines = doc.content.split("\n")
    edits, state, state_lnum = compute_indent(ADA_INDENT_BIN, lines)
    if state:
        doc.state_data = state
        doc.state_lnum = state_lnum

    return make_text_edits(lines, edits)


@server.feature(lsp.TEXT_DOCUMENT_RANGE_FORMATTING)
def range_formatting(params: lsp.DocumentRangeFormattingParams) -> list[lsp.TextEdit]:
    """Format a range — used by eglot for indent-line and indent-region."""
    doc = documents.get(params.text_document.uri)
    if not doc:
        return []

    lines = doc.content.split("\n")
    start_line = params.range.start.line  # 0-based
    end_line = params.range.end.line      # 0-based, inclusive

    # We need context from the beginning (or cache point) to compute
    # correct indentation for the range.
    use_cache = (
        doc.state_data is not None
        and doc.state_lnum > 0
        and doc.state_lnum <= start_line  # cache is before range
    )

    if use_cache:
        context_start = doc.state_lnum  # 1-based → feed from this line onward
        input_lines = lines[context_start:end_line + 1]
        edits, state, state_lnum = compute_indent(
            ADA_INDENT_BIN, input_lines,
            cached_state=doc.state_data,
            start_line=context_start + 1,  # 1-based
        )
    else:
        # Feed everything from start of file through end of range
        input_lines = lines[:end_line + 1]
        edits, state, state_lnum = compute_indent(
            ADA_INDENT_BIN, input_lines,
            start_line=1,
        )

    if state:
        doc.state_data = state
        doc.state_lnum = state_lnum

    # Only return edits within the requested range
    range_edits = [
        (idx, col) for idx, col in edits
        if start_line <= idx <= end_line
    ]
    return make_text_edits(lines, range_edits)


# Trigger characters: Enter plus the final letter of each dedenting keyword.
# This avoids an LSP round-trip on every keystroke while still catching the
# moment a keyword is fully typed (end→d, else→e, when→n, record→d, etc.).
_TRIGGER_FINALS = sorted(set(kw[-1] for kw in DEDENT_KEYWORDS))

@server.feature(
    lsp.TEXT_DOCUMENT_ON_TYPE_FORMATTING,
    lsp.DocumentOnTypeFormattingOptions(
        first_trigger_character="\n",
        more_trigger_character=_TRIGGER_FINALS,
    ),
)
def on_type_formatting(params: lsp.DocumentOnTypeFormattingParams) -> list[lsp.TextEdit]:
    """Auto-indent on Enter and snap dedenting keywords."""
    doc = documents.get(params.text_document.uri)
    if not doc:
        return []

    lines = doc.content.split("\n")
    cur_line = params.position.line  # 0-based

    if params.ch == "\n":
        # Indent the new line
        target_line = cur_line
    else:
        # Check if current line is a bare dedenting keyword
        if cur_line < len(lines):
            stripped = lines[cur_line].strip().lower()
            if stripped not in DEDENT_KEYWORDS:
                return []
        target_line = cur_line

    if target_line >= len(lines):
        return []

    # Feed from start (or cache) through target line
    use_cache = (
        doc.state_data is not None
        and doc.state_lnum > 0
        and doc.state_lnum <= target_line
    )

    if use_cache:
        context_start = doc.state_lnum
        input_lines = lines[context_start:target_line + 1]
        edits, state, state_lnum = compute_indent(
            ADA_INDENT_BIN, input_lines,
            cached_state=doc.state_data,
            start_line=context_start + 1,
        )
    else:
        input_lines = lines[:target_line + 1]
        edits, state, state_lnum = compute_indent(
            ADA_INDENT_BIN, input_lines,
            start_line=1,
        )

    if state:
        doc.state_data = state
        doc.state_lnum = state_lnum

    # Only return edit for the target line
    target_edits = [(idx, col) for idx, col in edits if idx == target_line]
    return make_text_edits(lines, target_edits)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global ADA_INDENT_BIN

    parser = argparse.ArgumentParser(description="Ada Indent LSP Server")
    parser.add_argument(
        "--ada-indent",
        default=shutil.which("ada_indent") or "ada_indent",
        help="Path to ada_indent binary (default: ada_indent on PATH)",
    )
    parser.add_argument(
        "--log",
        default=None,
        help="Log file path (default: no logging)",
    )
    args = parser.parse_args()
    ADA_INDENT_BIN = args.ada_indent

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if not shutil.which(ADA_INDENT_BIN):
        print(f"Error: ada_indent binary not found: {ADA_INDENT_BIN}", file=sys.stderr)
        sys.exit(1)

    log.info("Starting ada-indent-lsp with binary: %s", ADA_INDENT_BIN)
    server.start_io()


if __name__ == "__main__":
    main()
