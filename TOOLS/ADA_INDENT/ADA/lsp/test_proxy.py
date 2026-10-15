#!/usr/bin/env python3
"""Tests for ada_indent_proxy.py: unit tests, the proxy alone (--no-als), and
the proxy in front of a stand-in for the Ada Language Server (stub_als.py).

Usage: test_proxy.py            (needs bin/ada_indent built)
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ada_indent_proxy as P   # noqa: E402

BIN = os.path.join(HERE, "..", "bin", "ada_indent")
passed = failed = 0


def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {name}\n  want: {want!r}\n  got:  {got!r}")


# ---------------------------------------------------------------- units

lines = ["abc", "defg", "hi"]
P.apply_change(lines, {"start": {"line": 0, "character": 1},
                       "end": {"line": 1, "character": 2}}, "X\nY")
check("apply_change across lines", lines, ["aX", "Yfg", "hi"])
lines = ["a😀b"]                       # the emoji is two UTF-16 units
P.apply_change(lines, {"start": {"line": 0, "character": 3},
                       "end": {"line": 0, "character": 3}}, "-")
check("apply_change after a surrogate pair", lines, ["a😀-b"])
lines = ["x"]
P.apply_change(lines, {"start": {"line": 1, "character": 0},
                       "end": {"line": 1, "character": 0}}, "\ny")
check("apply_change past the end", lines, ["x", "", "y"])

d = P.Document("a\nb\nc")
d.state, d.state_lines = "S", 2
d.change({"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 0}}, "z")
check("edit after the cache point keeps it", (d.state, d.state_lines), ("S", 2))
d.change({"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 0}}, "z")
check("edit on a cached line drops it", (d.state, d.state_lines), (None, 0))

# ---------------------------------------------------------------- client

MESSY = ("procedure P is\nX : Integer;\nbegin\nif X = 0 then\nnull;\n"
         "-- note\nend if;\n   \nend P;\n")


def apply_edits(text, edits):
    ls = text.split("\n")
    for e in sorted(edits, key=lambda e: -e["range"]["start"]["line"]):
        i = e["range"]["start"]["line"]
        ls[i] = e["newText"] + ls[i][e["range"]["end"]["character"]:]
    return "\n".join(ls)


def binary_output(text):
    return subprocess.run([BIN, "-q"], input=text, capture_output=True,
                          text=True).stdout


class Client:
    def __init__(self, *args):
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "ada_indent_proxy.py"),
             "--ada-indent", BIN, *args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.lock = P.threading.Lock()
        self.next = 1
        self.incoming = []          # requests/notifications from the server

    def notify(self, method, params=None):
        P.write_message(self.proc.stdin, self.lock,
                        {"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method, params=None):
        mid = self.next
        self.next += 1
        P.write_message(self.proc.stdin, self.lock,
                        {"jsonrpc": "2.0", "id": mid, "method": method,
                         "params": params or {}})
        while True:
            msg = P.read_message(self.proc.stdout)
            if msg is None:
                return None
            if msg.get("id") == mid and "method" not in msg:
                return msg
            self.incoming.append(msg)

    def answer(self, mid, result):
        P.write_message(self.proc.stdin, self.lock,
                        {"jsonrpc": "2.0", "id": mid, "result": result})

    def open(self, uri, text):
        self.notify("textDocument/didOpen", {"textDocument": {
            "uri": uri, "languageId": "ada", "version": 1, "text": text}})

    def close(self):
        self.request("shutdown")
        self.notify("exit")
        self.proc.stdin.close()
        try:
            return self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return None


# ---------------------------------------------------------------- saved state

import tempfile
tmp = tempfile.mkdtemp()
logfile = os.path.join(tmp, "calls")
wrapper = os.path.join(tmp, "ada_indent")
with open(wrapper, "w") as f:
    f.write(f'#!/bin/sh\necho "$2" | cut -c1-7 >> {logfile}\nexec {os.path.abspath(BIN)} "$@"\n')
os.chmod(wrapper, 0o755)
fmt = P.Formatter(wrapper)
doc = P.Document("procedure P is\nbegin\nnull;\nnull;\nnull;\nend P;")
fmt.on_type(doc, 2, "\n")
check("on-type at line 2 saves the state before that line", doc.state_lines, 2)
doc.change({"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 0}}, "  ")
check("the editor indenting that line keeps the saved state", doc.state_lines, 2)
before = open(logfile).read().count("\n")
r = fmt.on_type(doc, 3, "\n")
calls = open(logfile).read().split("\n")[before:]
check("the next line resumes from the saved state", calls[0].startswith("--state"), True)
check("...and gets the column from-scratch indenting gives",
      apply_edits("\n".join(doc.lines), r).split("\n")[3],
      binary_output("\n".join(doc.lines)).split("\n")[3])

URI = "file:///t/p.adb"
TD = {"uri": URI}

# ---------------------------------------------------------------- alone

c = Client("--no-als")
init = c.request("initialize", {"capabilities": {}})["result"]["capabilities"]
check("alone: announces formatting",
      (init["documentFormattingProvider"], init["documentRangeFormattingProvider"],
       init["documentOnTypeFormattingProvider"]["firstTriggerCharacter"]),
      (True, True, "\n"))
c.open(URI, MESSY)
r = c.request(P.FORMATTING, {"textDocument": TD, "options": {}})["result"]
check("alone: formatting == ada_indent", apply_edits(MESSY, r), binary_output(MESSY))
r2 = c.request(P.FORMATTING, {"textDocument": TD, "options": {}})["result"]
check("alone: second formatting gives the same edits", r2, r)

want = binary_output(MESSY).split("\n")
r = c.request(P.RANGE_FORMATTING, {"textDocument": TD, "options": {}, "range": {
    "start": {"line": 3, "character": 0}, "end": {"line": 4, "character": 4}}})["result"]
got = apply_edits(MESSY, r).split("\n")
check("alone: range formatting touches only its lines",
      got, MESSY.split("\n")[:3] + want[3:5] + MESSY.split("\n")[5:])

# an edit, then a range request that resumes from the saved state
c.notify("textDocument/didChange", {"textDocument": TD, "contentChanges": [{
    "range": {"start": {"line": 4, "character": 0}, "end": {"line": 4, "character": 5}},
    "text": "if Y then\nnull;\nend if;"}]})
text2 = MESSY.split("\n")
text2[4:5] = ["if Y then", "null;", "end if;"]
text2 = "\n".join(text2)
r = c.request(P.FORMATTING, {"textDocument": TD, "options": {}})["result"]
check("alone: formatting after an edit", apply_edits(text2, r), binary_output(text2))
doc_lines = len(text2.split("\n"))
r = c.request(P.RANGE_FORMATTING, {"textDocument": TD, "options": {}, "range": {
    "start": {"line": doc_lines - 2, "character": 0},
    "end": {"line": doc_lines - 1, "character": 0}}})["result"]
got = apply_edits(text2, r).split("\n")
want = binary_output(text2).split("\n")
check("alone: range formatting resumed from the cache",
      got[doc_lines - 2:doc_lines - 1], want[doc_lines - 2:doc_lines - 1])

# on-type: Enter after 'begin' puts the cursor on the statement column
c.open("file:///t/q.adb", "procedure Q is\nbegin\n\nend Q;\n")
r = c.request(P.ON_TYPE_FORMATTING, {"textDocument": {"uri": "file:///t/q.adb"},
    "position": {"line": 2, "character": 0}, "ch": "\n", "options": {}})["result"]
check("alone: Enter on a blank line indents it", [e["newText"] for e in r], ["  "])
c.open("file:///t/r.adb", "procedure R is\nbegin\n  null;\n      end")
r = c.request(P.ON_TYPE_FORMATTING, {"textDocument": {"uri": "file:///t/r.adb"},
    "position": {"line": 3, "character": 9}, "ch": "d", "options": {}})["result"]
check("alone: typing 'end' snaps it back", apply_edits("procedure R is\nbegin\n  null;\n      end", r).split("\n")[3], "end")
r = c.request(P.ON_TYPE_FORMATTING, {"textDocument": {"uri": "file:///t/r.adb"},
    "position": {"line": 2, "character": 3}, "ch": "l", "options": {}})["result"]
check("alone: a non-keyword line is left alone", r, [])

err = c.request("textDocument/hover", {"textDocument": TD})
check("alone: other requests are refused", err["error"]["code"], -32601)
r = c.request(P.FORMATTING, {"textDocument": {"uri": "file:///nowhere"}, "options": {}})
check("alone: unknown document gives no edits", r["result"], [])
check("alone: clean exit", c.close(), 0)

# ---------------------------------------------------------------- with als

c = Client("--als", sys.executable, "--", os.path.join(HERE, "stub_als.py"))
env_ok = True
init = c.request("initialize", {"capabilities": {}})["result"]
caps = init["capabilities"]
check("als: its own capabilities survive", (caps["hoverProvider"], caps["textDocumentSync"]), (True, 2))
check("als: formatting is ours", (caps["documentFormattingProvider"],
      caps["documentOnTypeFormattingProvider"]["firstTriggerCharacter"]), (True, "\n"))
check("als: serverInfo is als's", init["serverInfo"]["name"], "stub_als")
c.notify("initialized")
c.open(URI, MESSY)
r = c.request("textDocument/hover", {"textDocument": TD, "position": {"line": 0, "character": 0}})
check("als: hover is forwarded", r["result"]["contents"], "hover from als")
r = c.request(P.FORMATTING, {"textDocument": TD, "options": {}})["result"]
check("als: formatting is answered by ada_indent", apply_edits(MESSY, r), binary_output(MESSY))
r = c.request(P.RANGE_FORMATTING, {"textDocument": TD, "options": {}, "range": {
    "start": {"line": 0, "character": 0}, "end": {"line": 2, "character": 0}}})["result"]
check("als: range formatting too", isinstance(r, list), True)
c.notify("textDocument/didChange", {"textDocument": TD, "contentChanges": [{"text": "x"}]})
seen = c.request("stub/seen")["result"]
check("als: notifications are forwarded, formatting requests are not",
      seen, ["initialize", "initialized", "textDocument/didOpen",
             "textDocument/hover", "textDocument/didChange", "stub/seen"])
srv = [m for m in c.incoming if m.get("method") == "window/workDoneProgress/create"]
check("als: its requests reach the client", len(srv), 1)
c.answer(srv[0]["id"], None)
seen = c.request("stub/seen")["result"]
check("als: the client's answer reaches it", "client-answered:null" in seen, True)
check("als: clean exit", c.close(), 0)

# ---------------------------------------------------------------- no als

c = Client("--als", "no_such_ada_language_server")
init = c.request("initialize", {"capabilities": {}})["result"]["capabilities"]
check("missing als: falls back to formatting only", init["documentFormattingProvider"], True)
check("missing als: clean exit", c.close(), 0)

print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
