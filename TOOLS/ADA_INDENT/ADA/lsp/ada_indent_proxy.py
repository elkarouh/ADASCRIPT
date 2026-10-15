#!/usr/bin/env python3
"""A language-server proxy: the Ada Language Server (als) with ada_indent's
formatting.

The proxy starts als as a child process and sits between it and the editor.
Everything is forwarded unchanged in both directions except:

  * the `initialize` response, whose capabilities are extended to announce
    document, range and on-type formatting;
  * textDocument/formatting, rangeFormatting and onTypeFormatting requests,
    which are answered here with ada_indent and never reach als.

Documents are tracked from didOpen/didChange/didClose (which are forwarded to
als as well) so that a request can be answered from the text the editor has.
For an edit near the end of a file the proxy resumes ada_indent from a saved
state (--emit-state / --state) instead of re-reading the file.

If als cannot be started, or is not wanted (--no-als), the proxy answers on its
own: it announces the formatting capabilities only, and every other request
gets a MethodNotFound error.

Usage:
    ada_indent_proxy.py [--ada-indent PATH] [--als COMMAND] [--no-als]
                        [--log FILE] [-- ALS_ARGS...]

Standard library only.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import threading

log = logging.getLogger("ada_indent_proxy")

FORMATTING = "textDocument/formatting"
RANGE_FORMATTING = "textDocument/rangeFormatting"
ON_TYPE_FORMATTING = "textDocument/onTypeFormatting"
OWN_REQUESTS = (FORMATTING, RANGE_FORMATTING, ON_TYPE_FORMATTING)

# Keywords that make a bare line dedent when typed.
DEDENT_KEYWORDS = {
    "begin", "end", "else", "elsif", "when", "exception",
    "is", "then", "private", "limited", "record", "loop", "do", "select",
}
# Enter, plus the final letter of each dedenting keyword: a round trip only
# when a keyword may just have been completed.
TRIGGER_FINALS = sorted({kw[-1] for kw in DEDENT_KEYWORDS})

BLANKS = " \t\v\f\r\n"


# ---------------------------------------------------------------------------
# JSON-RPC framing
# ---------------------------------------------------------------------------

def read_message(stream):
    """The next message from a binary stream, or None at end of input."""
    length = None
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            length = int(value)
    if length is None:
        return None
    body = stream.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream, lock, msg):
    body = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    with lock:
        stream.write(b"Content-Length: %d\r\n\r\n" % len(body))
        stream.write(body)
        stream.flush()


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def utf16_to_index(line, units):
    """Index into `line` of the character at UTF-16 offset `units`."""
    count = 0
    for i, ch in enumerate(line):
        if count >= units:
            return i
        count += 2 if ord(ch) > 0xFFFF else 1
    return len(line)


def apply_change(lines, rng, text):
    """Replace the range of `lines` (a list of strings) with `text`."""
    start, end = rng["start"], rng["end"]
    first = min(start["line"], len(lines))
    last = min(end["line"], len(lines) - 1)
    head = tail = ""
    if start["line"] < len(lines):
        head = lines[first][:utf16_to_index(lines[first], start["character"])]
    if end["line"] < len(lines):
        tail = lines[last][utf16_to_index(lines[last], end["character"]):]
    lines[first:last + 1] = (head + text + tail).split("\n")


class Document:
    """The text of one open document, and a saved indenter state.

    `state` is the indenter's state after the first `state_lines` lines; it is
    dropped when an edit touches any of them.
    """

    def __init__(self, text):
        self.lines = text.split("\n")
        self.state = None
        self.state_lines = 0

    def replace(self, text):
        self.lines = text.split("\n")
        self.state = None
        self.state_lines = 0

    def change(self, rng, text):
        if self.state is not None and rng["start"]["line"] < self.state_lines:
            self.state = None
            self.state_lines = 0
        apply_change(self.lines, rng, text)


# ---------------------------------------------------------------------------
# ada_indent
# ---------------------------------------------------------------------------

def default_binary():
    """ada_indent on PATH, else the one built in this repository (../bin)."""
    found = shutil.which("ada_indent")
    if found:
        return found
    built = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "bin", "ada_indent")
    return built if os.access(built, os.X_OK) else "ada_indent"


def run_indent(binary, lines, state=None):
    """Feed `lines` to ada_indent; one (indented line, state) per input line.

    Returns None if the binary cannot be run.
    """
    if not lines:
        return []
    cmd = [binary, "-q"]
    if state:
        cmd += ["--state", state]
    cmd.append("--emit-state")
    try:
        p = subprocess.run(cmd, input="\n".join(lines) + "\n", text=True,
                           encoding="utf-8", errors="surrogateescape",
                           capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.error("ada_indent failed: %s", exc)
        return None
    out = p.stdout.split("\n")
    if out and out[-1] == "":
        out.pop()
    # Every input line comes back as its indented text, then its ##STATE: line.
    if p.returncode != 0 or len(out) != 2 * len(lines):
        log.error("ada_indent: unexpected output (rc=%d, %d lines for %d)",
                  p.returncode, len(out), len(lines))
        return None
    return [(out[2 * i], out[2 * i + 1][len("##STATE:"):])
            for i in range(len(lines))]


def indent_column(line):
    return len(line) - len(line.lstrip(BLANKS))


class Formatter:
    def __init__(self, binary):
        self.binary = binary

    def indent_upto(self, doc, first, last, lines=None):
        """Indent the lines of `doc` up to `last`; {line index: indent column}.

        The columns are good for lines `first` and after: when the document's
        saved state covers only lines before `first`, ada_indent resumes from
        it instead of reading the file from the top. The state reached is
        saved, unless `lines` (a modified copy of the text) is given.
        """
        start, state = 0, None
        if lines is None and doc.state is not None and doc.state_lines <= first:
            start, state = doc.state_lines, doc.state
        fed = (lines or doc.lines)[start:last + 1]
        res = run_indent(self.binary, fed, state)
        if res is None:
            return None
        if lines is None:
            # Save the state from before the last line fed: the editor is
            # about to rewrite that line's indentation (a didChange on it),
            # which must not invalidate the lines that were read.
            if len(res) >= 2:
                doc.state, doc.state_lines = res[-2][1], last
            elif start == 0:
                doc.state, doc.state_lines = None, 0
        return {start + i: indent_column(out) for i, (out, _) in enumerate(res)}

    @staticmethod
    def edits(doc, columns, first, last):
        """TextEdits that change the leading blanks of lines first..last."""
        out = []
        for i in range(first, min(last, len(doc.lines) - 1) + 1):
            if i not in columns:
                continue
            old = indent_column(doc.lines[i])
            if old != columns[i]:
                out.append({"range": {"start": {"line": i, "character": 0},
                                      "end": {"line": i, "character": old}},
                            "newText": " " * columns[i]})
        return out

    def format_document(self, doc):
        columns = self.indent_upto(doc, 0, len(doc.lines) - 1)
        if columns is None:
            return []
        return self.edits(doc, columns, 0, len(doc.lines) - 1)

    def format_range(self, doc, first, last):
        last = min(last, len(doc.lines) - 1)
        if first > last:
            return []
        columns = self.indent_upto(doc, first, last)
        if columns is None:
            return []
        return self.edits(doc, columns, first, last)

    def on_type(self, doc, line, ch):
        if line >= len(doc.lines):
            return []
        if ch != "\n" and doc.lines[line].strip().lower() not in DEDENT_KEYWORDS:
            return []
        if ch == "\n" and doc.lines[line].strip(BLANKS) == "":
            # A new, empty line: ada_indent leaves blank lines empty, so ask
            # where a statement would go instead, with a stand-in for it.
            lines = list(doc.lines)
            lines[line] = "null;"
            columns = self.indent_upto(doc, line, line, lines)
            if columns is None:
                return []
            old = len(doc.lines[line])
            if columns[line] == old:
                return []
            return [{"range": {"start": {"line": line, "character": 0},
                               "end": {"line": line, "character": old}},
                     "newText": " " * columns[line]}]
        columns = self.indent_upto(doc, line, line)
        if columns is None:
            return []
        return self.edits(doc, columns, line, line)


# ---------------------------------------------------------------------------
# The proxy
# ---------------------------------------------------------------------------

def formatting_capabilities():
    return {
        "documentFormattingProvider": True,
        "documentRangeFormattingProvider": True,
        "documentOnTypeFormattingProvider": {
            "firstTriggerCharacter": "\n",
            "moreTriggerCharacter": TRIGGER_FINALS,
        },
    }


class Proxy:
    def __init__(self, binary, als_cmd):
        self.formatter = Formatter(binary)
        self.documents = {}
        self.client_out = sys.stdout.buffer
        self.client_lock = threading.Lock()
        self.als = None
        self.als_lock = threading.Lock()
        self.init_id = None
        if als_cmd:
            try:
                self.als = subprocess.Popen(als_cmd, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE)
            except OSError as exc:
                log.warning("cannot start %s (%s): formatting only", als_cmd[0], exc)
                print(f"ada_indent_proxy: cannot start {als_cmd[0]} ({exc}); "
                      "serving formatting only", file=sys.stderr)

    # -- plumbing ----------------------------------------------------------

    def to_client(self, msg):
        write_message(self.client_out, self.client_lock, msg)

    def to_als(self, msg):
        if self.als is None:
            return False
        try:
            write_message(self.als.stdin, self.als_lock, msg)
            return True
        except (OSError, ValueError):
            log.warning("als has gone away: formatting only from here on")
            self.als = None
            return False

    def als_to_client(self):
        """Thread: copy als's messages to the client, patching `initialize`."""
        while True:
            try:
                msg = read_message(self.als.stdout)
            except (OSError, ValueError):
                msg = None
            if msg is None:
                return
            if self.init_id is not None and msg.get("id") == self.init_id \
                    and "method" not in msg and "result" in msg:
                self.init_id = None
                caps = msg["result"].setdefault("capabilities", {})
                caps.update(formatting_capabilities())
            self.to_client(msg)

    # -- tracking documents --------------------------------------------------

    def track(self, msg):
        method, params = msg.get("method"), msg.get("params") or {}
        if method == "textDocument/didOpen":
            td = params["textDocument"]
            self.documents[td["uri"]] = Document(td["text"])
        elif method == "textDocument/didClose":
            self.documents.pop(params["textDocument"]["uri"], None)
        elif method == "textDocument/didChange":
            doc = self.documents.get(params["textDocument"]["uri"])
            if doc is None:
                return
            for ch in params["contentChanges"]:
                if ch.get("range"):
                    doc.change(ch["range"], ch["text"])
                else:
                    doc.replace(ch["text"])

    # -- our own requests ------------------------------------------------------

    def answer(self, msg):
        try:
            result = self.compute(msg)
        except Exception as exc:        # a bad request must not end the session
            log.exception("%s failed", msg["method"])
            self.to_client({"jsonrpc": "2.0", "id": msg["id"],
                            "error": {"code": -32603, "message": str(exc)}})
            return
        self.to_client({"jsonrpc": "2.0", "id": msg["id"], "result": result})

    def compute(self, msg):
        params = msg.get("params") or {}
        doc = self.documents.get(params.get("textDocument", {}).get("uri"))
        method = msg["method"]
        if doc is None:
            result = []
        elif method == FORMATTING:
            result = self.formatter.format_document(doc)
        elif method == RANGE_FORMATTING:
            r = params["range"]
            end = r["end"]["line"]
            if end > r["start"]["line"] and r["end"]["character"] == 0:
                end -= 1            # a range ending at column 0 stops before that line
            result = self.formatter.format_range(doc, r["start"]["line"], end)
        else:
            pos = params["position"]
            result = self.formatter.on_type(doc, pos["line"], params["ch"])
        return result

    def standalone(self, msg):
        """Handle a client message ourselves, as a server with no als."""
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:
            return                      # notification
        if method == "initialize":
            caps = {"textDocumentSync": {"openClose": True, "change": 2}}
            caps.update(formatting_capabilities())
            result = {"capabilities": caps,
                      "serverInfo": {"name": "ada_indent_proxy"}}
            self.to_client({"jsonrpc": "2.0", "id": mid, "result": result})
        elif method == "shutdown":
            self.to_client({"jsonrpc": "2.0", "id": mid, "result": None})
        else:
            self.to_client({"jsonrpc": "2.0", "id": mid,
                            "error": {"code": -32601,
                                      "message": f"{method}: not available (no Ada Language Server)"}})

    # -- main loop ---------------------------------------------------------

    def run(self):
        stdin = sys.stdin.buffer
        if self.als is not None:
            threading.Thread(target=self.als_to_client, daemon=True).start()
        while True:
            msg = read_message(stdin)
            if msg is None:
                break
            method = msg.get("method")
            if method in OWN_REQUESTS and "id" in msg:
                self.answer(msg)
                continue
            self.track(msg)
            if method == "initialize":
                self.init_id = msg.get("id")
            if self.als is None or not self.to_als(msg):
                self.standalone(msg)
            if method == "exit":
                break
        self.close()

    def close(self):
        if self.als is None:
            return
        try:
            self.als.stdin.close()
            self.als.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self.als.kill()


def main():
    argv = sys.argv[1:]
    als_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, als_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="Ada Language Server proxy with ada_indent formatting")
    ap.add_argument("--ada-indent", default=default_binary(),
                    help="ada_indent binary (default: on PATH, else ../bin/ada_indent)")
    ap.add_argument("--als", default="ada_language_server",
                    help="the Ada Language Server command (default: ada_language_server)")
    ap.add_argument("--no-als", action="store_true",
                    help="do not start als: serve formatting only")
    ap.add_argument("--log", help="write a debug log to this file")
    args = ap.parse_args(argv)
    logging.basicConfig(filename=args.log,
                        level=logging.DEBUG if args.log else logging.WARNING)
    if not shutil.which(args.ada_indent):
        sys.exit(f"ada_indent_proxy: ada_indent binary not found: {args.ada_indent}")
    als_cmd = None if args.no_als else [args.als] + als_args
    Proxy(args.ada_indent, als_cmd).run()


if __name__ == "__main__":
    main()
