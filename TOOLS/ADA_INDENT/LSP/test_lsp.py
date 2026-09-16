#!/usr/bin/env python3
"""Tests for ada-indent-lsp.py — unit and integration.

Tests the pure helper functions and the ada_indent integration without
requiring pygls/lsprotocol (which are only needed by the server itself).
"""

import shutil
import subprocess
import sys
import os

passed = 0
failed = 0

def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {name}")
        print(f"  want: {want!r}")
        print(f"  got:  {got!r}")


# ---------------------------------------------------------------------------
# _apply_change — test the logic directly (copied from the module to avoid
# importing pygls).  If the module changes, update this copy.
# ---------------------------------------------------------------------------

def _apply_change(content, start_line, start_char, end_line, end_char, text):
    """Standalone copy of the incremental change logic."""
    lines = content.split("\n")
    prefix_lines = lines[:start_line]
    if start_line < len(lines):
        prefix_lines.append(lines[start_line][:start_char])
    before = "\n".join(prefix_lines)

    if end_line < len(lines):
        after = lines[end_line][end_char:]
        if end_line + 1 < len(lines):
            after += "\n" + "\n".join(lines[end_line + 1:])
    else:
        after = ""

    return before + text + after


# Insert in the middle of line 0
check("apply: insert at line 0 col 5",
      _apply_change("hello world\nsecond line", 0, 5, 0, 5, " beautiful"),
      "hello beautiful world\nsecond line")

# Replace a word on line 1
check("apply: replace line 1",
      _apply_change("first\nsecond\nthird", 1, 0, 1, 6, "REPLACED"),
      "first\nREPLACED\nthird")

# Insert at the very beginning
check("apply: insert at 0,0",
      _apply_change("hello", 0, 0, 0, 0, "prefix "),
      "prefix hello")

# Delete across lines
check("apply: delete across lines",
      _apply_change("aaa\nbbb\nccc", 0, 2, 1, 1, ""),
      "aabb\nccc")

# Insert newline
check("apply: insert newline",
      _apply_change("line1\nline2", 0, 5, 0, 5, "\n"),
      "line1\n\nline2")

# Edit at end of document
check("apply: append to last line",
      _apply_change("only", 0, 4, 0, 4, " line"),
      "only line")

# Bug 1 regression: no spurious leading newline on line 0
result = _apply_change("hello", 0, 0, 0, 0, "X")
check("apply: no leading newline on line 0",
      result.startswith("\n"), False)


# ---------------------------------------------------------------------------
# Integration: compute_indent via ada_indent binary
# ---------------------------------------------------------------------------

ada_indent_bin = shutil.which("ada_indent")

def run_indent(lines, state=None, start_line=1):
    """Run ada_indent and parse the output, mirroring compute_indent logic."""
    input_text = "\n".join(lines)
    cmd = [ada_indent_bin, "--emit-state"]
    if state:
        cmd[1:1] = ["--state", state]
    result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"ada_indent failed: {result.stderr}"

    out_lines = result.stdout.split("\n")
    code_lines = []
    last_state = None
    state_lnum = 0
    line_idx = start_line

    for raw in out_lines:
        if raw.startswith("##STATE:"):
            last_state = raw[8:]
            state_lnum = line_idx - 1
        elif raw or code_lines:
            code_lines.append(raw)
            line_idx += 1

    edits = []
    for i, indented in enumerate(code_lines):
        new_indent = len(indented) - len(indented.lstrip()) if indented.strip() else 0
        edits.append((start_line - 1 + i, new_indent))

    return edits, last_state, state_lnum


if ada_indent_bin:
    print(f"ada_indent: {ada_indent_bin}")

    # Simple package
    edits, state, slnum = run_indent([
        "package Foo is",
        "  procedure Bar;",
        "end Foo;",
    ])
    ind = {i: c for i, c in edits}
    check("pkg: line 0 at col 0", ind.get(0), 0)
    check("pkg: line 1 at col 2", ind.get(1), 2)
    check("pkg: line 2 at col 0", ind.get(2), 0)
    check("pkg: state returned", state is not None, True)

    # Enum type — TYPE_HEADER must be popped
    edits, _, _ = run_indent([
        "package P is",
        "  type Color is (Red, Green, Blue);",
        "  X : Integer;",
        "end P;",
    ])
    ind = {i: c for i, c in edits}
    check("enum: type at col 2", ind.get(1), 2)
    check("enum: X after enum at col 2 (not 4)", ind.get(2), 2)
    check("enum: end P at col 0", ind.get(3), 0)

    # Record type — TYPE_HEADER into RECORD
    edits, _, _ = run_indent([
        "package P is",
        "  type R is",
        "    record",
        "      X : Integer;",
        "    end record;",
        "  Y : Integer;",
        "end P;",
    ])
    ind = {i: c for i, c in edits}
    check("record: type at col 2", ind.get(1), 2)
    check("record: record at col 4", ind.get(2), 4)
    check("record: X at col 6", ind.get(3), 6)
    check("record: end record at col 4", ind.get(4), 4)
    check("record: Y at col 2", ind.get(5), 2)
    check("record: end P at col 0", ind.get(6), 0)

    # State cache round-trip
    prefix = ["package Foo is", "  procedure Bar;"]
    _, pstate, plnum = run_indent(prefix)
    check("cache: state not None", pstate is not None, True)

    if pstate:
        rest = ["  procedure Baz;", "end Foo;"]
        edits2, _, _ = run_indent(rest, state=pstate, start_line=plnum + 1)
        ind2 = {i: c for i, c in edits2}
        check("cache: Baz at col 2", ind2.get(plnum), 2)

    # User's file if available
    user_file = os.path.expanduser("~/orig.adb")
    if os.path.isfile(user_file):
        with open(user_file) as f:
            orig_lines = f.read().splitlines()
        edits, _, _ = run_indent(orig_lines)
        changed = sum(1 for idx, col in edits
                      if idx < len(orig_lines)
                      and (len(orig_lines[idx]) - len(orig_lines[idx].lstrip())) != col)
        check(f"fixpoint: orig.adb ({len(orig_lines)} lines, {changed} differ)", changed, 0)

else:
    print("SKIP: ada_indent binary not found — integration tests skipped")


# ---------------------------------------------------------------------------
# LSP integration tests — raw JSON-RPC over subprocess
# ---------------------------------------------------------------------------

import json
import time

LSP_SCRIPT = os.path.join(os.path.dirname(__file__), "ada-indent-lsp.py")
# Find a Python that has pygls
LSP_PYTHON = None
for cand in ["python3", "python3.14", "python3.13", "python3.12"]:
    py = shutil.which(cand)
    if py:
        rc = subprocess.run([py, "-c", "import pygls"], capture_output=True).returncode
        if rc == 0:
            LSP_PYTHON = py
            break


class LSPClient:
    """Minimal LSP client over stdio for testing."""

    def __init__(self, cmd):
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._id = 0

    def _next_id(self):
        self._id += 1
        return self._id

    def send(self, method, params, is_notification=False):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        if not is_notification:
            msg["id"] = self._next_id()
        body = json.dumps(msg)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self.proc.stdin.write(header.encode())
        self.proc.stdin.write(body.encode())
        self.proc.stdin.flush()
        if not is_notification:
            return self._read_response()
        return None

    def _read_response(self):
        # Read headers
        headers = {}
        while True:
            line = self.proc.stdout.readline().decode()
            if line == "\r\n" or line == "\n" or line == "":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get("content-length", 0))
        if length == 0:
            return None
        body = self.proc.stdout.read(length).decode()
        return json.loads(body)

    def close(self):
        try:
            self.send("shutdown", {})
            self.send("exit", {}, is_notification=True)
        except Exception:
            pass
        self.proc.terminate()
        self.proc.wait(timeout=5)


if LSP_PYTHON and os.path.isfile(LSP_SCRIPT) and ada_indent_bin:
    print(f"\nLSP integration tests (python: {LSP_PYTHON})")

    client = LSPClient([LSP_PYTHON, LSP_SCRIPT])

    # Initialize
    init_resp = client.send("initialize", {
        "processId": os.getpid(),
        "capabilities": {},
        "rootUri": None,
    })
    check("lsp: initialize succeeds", init_resp is not None, True)
    if init_resp:
        caps = init_resp.get("result", {}).get("capabilities", {})
        check("lsp: formatting capability",
              caps.get("documentFormattingProvider") in (True, {}), True)
        check("lsp: range formatting capability",
              caps.get("documentRangeFormattingProvider") in (True, {}), True)
        check("lsp: on-type formatting capability",
              caps.get("documentOnTypeFormattingProvider") is not None, True)

    # Send initialized notification
    client.send("initialized", {}, is_notification=True)

    # Open a document
    test_uri = "file:///tmp/test.adb"
    test_content = "package Foo is\nprocedure Bar;\nend Foo;\n"
    client.send("textDocument/didOpen", {
        "textDocument": {
            "uri": test_uri,
            "languageId": "ada",
            "version": 1,
            "text": test_content,
        },
    }, is_notification=True)

    # Request full formatting
    fmt_resp = client.send("textDocument/formatting", {
        "textDocument": {"uri": test_uri},
        "options": {"tabSize": 2, "insertSpaces": True},
    })
    check("lsp: formatting response", fmt_resp is not None, True)
    if fmt_resp:
        edits = fmt_resp.get("result", [])
        check("lsp: formatting returns edits", isinstance(edits, list), True)
        # Line 1 "procedure Bar;" should be indented to col 2
        indent_edits = {e["range"]["start"]["line"]: e["newText"] for e in edits}
        check("lsp: line 1 indented to 2 spaces", indent_edits.get(1), "  ")

    # Request range formatting (just line 1)
    range_resp = client.send("textDocument/rangeFormatting", {
        "textDocument": {"uri": test_uri},
        "range": {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 100},
        },
        "options": {"tabSize": 2, "insertSpaces": True},
    })
    check("lsp: range formatting response", range_resp is not None, True)
    if range_resp:
        edits = range_resp.get("result", [])
        check("lsp: range formatting returns edits", isinstance(edits, list), True)

    # Send a didChange (incremental) and re-format
    client.send("textDocument/didChange", {
        "textDocument": {"uri": test_uri, "version": 2},
        "contentChanges": [{
            "range": {
                "start": {"line": 1, "character": 0},
                "end": {"line": 1, "character": 0},
            },
            "text": "  ",  # add correct indent
        }],
    }, is_notification=True)

    # Format again — should return no edits now (line 1 already at col 2)
    fmt_resp2 = client.send("textDocument/formatting", {
        "textDocument": {"uri": test_uri},
        "options": {"tabSize": 2, "insertSpaces": True},
    })
    if fmt_resp2:
        edits2 = fmt_resp2.get("result", [])
        # Line 1 is now "  procedure Bar;" — already correct
        line1_edits = [e for e in edits2 if e["range"]["start"]["line"] == 1]
        check("lsp: no edit for already-correct line", len(line1_edits), 0)

    # Close document
    client.send("textDocument/didClose", {
        "textDocument": {"uri": test_uri},
    }, is_notification=True)

    client.close()
    print("  LSP server shutdown OK")

elif not LSP_PYTHON:
    print("\nSKIP: no Python with pygls found — LSP integration tests skipped")
elif not ada_indent_bin:
    print("\nSKIP: ada_indent not found — LSP integration tests skipped")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
