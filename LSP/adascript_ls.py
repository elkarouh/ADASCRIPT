#!/usr/bin/env python3.13
"""Adascript Language Server

Implements LSP features for .ady files:
  - Diagnostics  parse errors on open/change/save
  - Hover        type and enum info for identifiers
  - Completion   enum type names, members, tick attributes

Usage (stdio — the standard mode for editors):
    python3.13 adascript_ls.py

VS Code extension settings (example):
    {
        "adascript.server.command": ["python3.13", "/path/to/adascript_ls.py"]
    }

Requirements:
    python3.13 -m pip install pygls
"""

import sys
import os
import re
import io
import logging

_here = os.path.dirname(os.path.realpath(__file__))
_root = os.path.dirname(_here)  # one level up: ADASCRIPT/
for _p in [
    _root,
    os.path.join(_root, "HPARSEC"),
    os.path.join(_root, "ADASCRIPT_GRAMMAR"),
    os.path.join(_root, "TO_PYTHON"),
]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pygls.lsp.server import LanguageServer
from lsprotocol import types

logging.basicConfig(level=logging.ERROR)

server = LanguageServer(name="adascript-ls", version="0.1.0")

# ---------------------------------------------------------------------------
# Parser interface
# ---------------------------------------------------------------------------

def _parse(source: str) -> tuple[bool, list, dict, object]:
    """Parse and transpile Adascript source. Returns (ok, diag_tuples, tick_types, symbol_table).

    diag_tuples: list of (line_1based, col_0based, message) for each parse error.
    tick_types:  ParserState.tick_types — populated by running to_py() on each node.
    symbol_table: ParserState.symbol_table (or None).

    We call translate() rather than parse_module() because tick_types and
    symbol_table are only filled during the to_py() emission pass.
    """
    import py2py
    from hek_parsec import ParserState

    captured = io.StringIO()
    old_stderr, sys.stderr = sys.stderr, captured
    try:
        py2py.translate(source)
    except Exception as exc:
        sys.stderr = old_stderr
        return False, [(1, 0, str(exc))], {}, None
    finally:
        sys.stderr = old_stderr

    diags = []
    for ln in captured.getvalue().splitlines():
        m = re.match(r"Parse error at line (\d+), col (\d+): (.+)", ln)
        if m:
            diags.append((int(m.group(1)), int(m.group(2)), m.group(3)))
        elif ln.strip():
            diags.append((1, 0, ln.strip()))

    return (
        len(diags) == 0,
        diags,
        dict(getattr(ParserState, "tick_types", {}) or {}),
        getattr(ParserState, "symbol_table", None),
    )


def _lsp_diagnostics(raw: list) -> list[types.Diagnostic]:
    out = []
    for ln, col, msg in raw:
        pos = types.Position(line=max(0, ln - 1), character=max(0, col))
        out.append(types.Diagnostic(
            range=types.Range(start=pos, end=pos),
            message=msg,
            severity=types.DiagnosticSeverity.Error,
            source="adascript",
        ))
    return out


# ---------------------------------------------------------------------------
# Per-document state cache
# ---------------------------------------------------------------------------

_cache: dict[str, dict] = {}


def _validate(ls: LanguageServer, uri: str, source: str) -> None:
    _, raw_diags, tick_types, sym_table = _parse(source)
    _cache[uri] = {"tick_types": tick_types, "sym_table": sym_table}
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, diagnostics=_lsp_diagnostics(raw_diags))
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _word_at(line: str, col: int) -> str:
    start = col
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
        start -= 1
    end = col
    while end < len(line) and (line[end].isalnum() or line[end] == "_"):
        end += 1
    return line[start:end]


def _all_sym_names(sym_table) -> list[str]:
    if sym_table is None:
        return []
    names = []
    for scope in getattr(sym_table, "stack", []):
        names.extend(scope.get("symbols", {}).keys())
    return names


# ---------------------------------------------------------------------------
# LSP feature handlers
# ---------------------------------------------------------------------------

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams) -> None:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    _validate(ls, params.text_document.uri, doc.source or "")


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams) -> None:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    _validate(ls, params.text_document.uri, doc.source or "")


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams) -> None:
    doc = ls.workspace.get_text_document(params.text_document.uri)
    _validate(ls, params.text_document.uri, doc.source or "")


@server.feature(types.TEXT_DOCUMENT_HOVER, types.HoverOptions())
def hover(ls: LanguageServer, params: types.HoverParams) -> types.Hover | None:
    uri = params.text_document.uri
    pos = params.position
    source = (ls.workspace.get_text_document(uri).source or "")
    lines = source.splitlines()
    if pos.line >= len(lines):
        return None
    word = _word_at(lines[pos.line], pos.character)
    if not word:
        return None

    state = _cache.get(uri, {})
    tick_types = state.get("tick_types", {})
    sym_table = state.get("sym_table")

    if word in tick_types:
        info = tick_types[word]
        members = info.get("members", [])
        first = info.get("First", members[0] if members else "?")
        last = info.get("Last", members[-1] if members else "?")
        md = (
            f"**{word}** — `enum` type\n\n"
            f"Members: `{', '.join(members)}`\n\n"
            f"`{word}'First = {first}` · `{word}'Last = {last}`"
        )
        return types.Hover(
            contents=types.MarkupContent(kind=types.MarkupKind.Markdown, value=md)
        )

    for type_name, info in tick_types.items():
        if word in info.get("members", []):
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{word}** — member of enum `{type_name}`",
                )
            )

    if sym_table:
        sym = sym_table.lookup(word)
        if sym:
            sym_type = sym.get("type") or "?"
            sym_kind = sym.get("kind") or ""
            detail = f" ({sym_kind})" if sym_kind else ""
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{word}** : `{sym_type}`{detail}",
                )
            )

    return None


@server.feature(
    types.TEXT_DOCUMENT_COMPLETION,
    types.CompletionOptions(trigger_characters=["'", "."]),
)
def completions(ls: LanguageServer, params: types.CompletionParams) -> types.CompletionList:
    uri = params.text_document.uri
    pos = params.position
    source = ls.workspace.get_text_document(uri).source or ""
    lines = source.splitlines()
    before = lines[pos.line][:pos.character] if pos.line < len(lines) else ""

    state = _cache.get(uri, {})
    tick_types = state.get("tick_types", {})
    sym_table = state.get("sym_table")
    items: list[types.CompletionItem] = []

    # Tick-attribute trigger: EnumType'<cursor>
    m = re.match(r".*\b(\w+)'$", before)
    if m:
        name = m.group(1)
        if name in tick_types:
            for attr in ("First", "Last", "Range", "Pos", "Val", "Succ", "Pred"):
                items.append(types.CompletionItem(
                    label=attr,
                    kind=types.CompletionItemKind.Property,
                    detail=f"{name}'{attr}",
                ))
        return types.CompletionList(is_incomplete=False, items=items)

    # Dot trigger: EnumType.<cursor>  (Python enum member access)
    m = re.match(r".*\b(\w+)\.$", before)
    if m:
        name = m.group(1)
        if name in tick_types:
            for mem in tick_types[name].get("members", []):
                items.append(types.CompletionItem(
                    label=mem,
                    kind=types.CompletionItemKind.EnumMember,
                    detail=f"{name}.{mem}",
                ))
        return types.CompletionList(is_incomplete=False, items=items)

    # General: prefix-filtered enum types + known symbols
    prefix = re.match(r".*?(\w*)$", before).group(1)

    for name, info in tick_types.items():
        if name.startswith(prefix):
            n = len(info.get("members", []))
            items.append(types.CompletionItem(
                label=name,
                kind=types.CompletionItemKind.Enum,
                detail=f"enum ({n} members)",
            ))

    seen = set(tick_types)
    for sym_name in _all_sym_names(sym_table):
        if sym_name.startswith(prefix) and sym_name not in seen:
            seen.add(sym_name)
            items.append(types.CompletionItem(
                label=sym_name,
                kind=types.CompletionItemKind.Variable,
            ))

    return types.CompletionList(is_incomplete=False, items=items)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server.start_io()
