#!/usr/bin/env python3
"""A stand-in for the Ada Language Server, for test_proxy.py.

Answers `initialize` (claiming a hover provider and, wrongly, a formatting
provider of its own), `textDocument/hover` and `stub/seen` (the methods it has
been sent, in order), asks the client for a work-done progress token after
`initialized`, and records the answer.
"""
import json
import sys

from ada_indent_proxy import read_message, write_message
import threading

lock = threading.Lock()
seen = []


def send(msg):
    write_message(sys.stdout.buffer, lock, msg)


while True:
    msg = read_message(sys.stdin.buffer)
    if msg is None:
        break
    method = msg.get("method")
    if method:
        seen.append(method)
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {
            "capabilities": {"hoverProvider": True,
                             "documentFormattingProvider": False,
                             "textDocumentSync": 2},
            "serverInfo": {"name": "stub_als"}}})
    elif method == "initialized":
        send({"jsonrpc": "2.0", "id": "als-1",
              "method": "window/workDoneProgress/create", "params": {"token": "t"}})
    elif method == "textDocument/hover":
        send({"jsonrpc": "2.0", "id": msg["id"],
              "result": {"contents": "hover from als"}})
    elif method == "stub/seen":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": seen})
    elif method in ("textDocument/formatting", "textDocument/rangeFormatting",
                    "textDocument/onTypeFormatting"):
        send({"jsonrpc": "2.0", "id": msg["id"], "result": "WRONG: reached als"})
    elif method == "shutdown":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": None})
    elif method == "exit":
        break
    elif method is None and msg.get("id") == "als-1":
        seen.append("client-answered:" + json.dumps(msg.get("result")))
