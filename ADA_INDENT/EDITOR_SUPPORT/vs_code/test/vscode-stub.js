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
const config = { program: "ada_indent", enableStateCache: true };
const registered = {};
module.exports = {
  Position, Range, TextEdit,
  workspace: {
    getConfiguration: () => ({ get: (k, d) => (k in config ? config[k] : d) }),
    onDidChangeTextDocument: (f) => { registered.onChange = f; return { dispose() {} }; },
    onDidCloseTextDocument: () => ({ dispose() {} }),
    applyEdit: async () => true,
  },
  languages: {
    registerDocumentFormattingEditProvider: (s, p) => { registered.doc = p; return { dispose() {} }; },
    registerDocumentRangeFormattingEditProvider: (s, p) => { registered.range = p; return { dispose() {} }; },
    registerOnTypeFormattingEditProvider: (s, p, ...t) => { registered.onType = p; registered.triggers = t; return { dispose() {} }; },
  },
  window: { showErrorMessage: (m) => { console.error("ERROR:", m); }, activeTextEditor: null },
  commands: { registerCommand: (n, f) => { registered[n] = f; return { dispose() {} }; } },
  __registered: registered, __config: config,
};
