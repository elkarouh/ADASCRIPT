// Minimal stand-in for the VS Code API: just enough of it to drive
// extension.js outside the editor.
"use strict";
class Position { constructor(line, character) { this.line = line; this.character = character; } }
class Range {
  constructor(a, b, c, d) {
    if (typeof a === "number") { this.start = new Position(a, b); this.end = new Position(c, d); }
    else { this.start = a; this.end = b; }
  }
}
class TextEdit {
  constructor(range, newText) { this.range = range; this.newText = newText; }
  static replace(range, newText) { return new TextEdit(range, newText); }
}
class WorkspaceEdit {
  constructor() { this._edits = []; }
  replace(uri, range, newText) { this._edits.push({ uri, range, newText }); }
  set(uri, edits) { for (const e of edits) this._edits.push({ uri, range: e.range, newText: e.newText }); }
}
const config = { program: "ada_indent", enableStateCache: true, formatOnType: true };
const registered = {};
let lastApplied = null;
module.exports = {
  Position, Range, TextEdit, WorkspaceEdit,
  workspace: {
    getConfiguration: () => ({ get: (k, d) => (k in config ? config[k] : d) }),
    onDidChangeTextDocument: (f) => { registered.onChange = f; return { dispose() {} }; },
    onDidCloseTextDocument: () => ({ dispose() {} }),
    applyEdit: async (wsEdit) => { lastApplied = wsEdit; return true; },
  },
  languages: {
    registerDocumentFormattingEditProvider: (s, p) => { registered.doc = p; return { dispose() {} }; },
    registerDocumentRangeFormattingEditProvider: (s, p) => { registered.range = p; return { dispose() {} }; },
  },
  window: { showErrorMessage: (m) => { console.error("ERROR:", m); }, activeTextEditor: null },
  commands: { registerCommand: (n, f) => { registered[n] = f; return { dispose() {} }; } },
  __registered: registered, __config: config,
  __lastApplied: () => lastApplied, __clearApplied: () => { lastApplied = null; },
};
