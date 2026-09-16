"use strict";

// ada-indent for VS Code --- Ada indentation via the external ada_indent program.
//
// The same design as ada-indent.el and ada-indent.vim in this directory: the
// editor calls the binary directly. There is no language server and no Python
// in the path -- TOOLS/ADA_INDENT/LSP/ is the option for editors that would rather
// speak LSP, and this is the option for VS Code, which does not need to.
//
// What it wires up:
//   Format Document      -> reindent the whole file          (one ada_indent run)
//   Format Selection     -> reindent the selected lines      (one ada_indent run)
//   Format On Type       -> Enter indents the new line, and a line that becomes
//                           a bare dedenting keyword (end, else, when, ...)
//                           snaps left on its final character
//   Ada Indent: Reindent Whole Buffer  -- the command, for a keybinding
//
// Format On Type is off by default in VS Code. Turn it on for Ada:
//   "[ada]": { "editor.formatOnType": true }
//
// Performance: ada_indent is stateful -- it normally replays every line above
// the one being indented. This keeps a per-document cache of the serialized
// state (the binary's --emit-state / --state protocol) so consecutive edits
// only process the lines between the cache point and the cursor, O(distance)
// per keypress rather than O(file size). The cache is dropped whenever the
// document is edited above the cache point.

const vscode = require("vscode");
const { execFile } = require("child_process");

const STATE_PREFIX = "##STATE:";

// A line consisting of one of these, and nothing else, belongs one level left
// of the block body. Typing the last letter is the moment to move it, which is
// what the on-type trigger characters below are derived from.
const DEDENT_KEYWORDS = [
  "end", "else", "elsif", "when", "exception",
  "begin", "is", "then", "private", "limited",
  "record", "loop", "do", "select",
];

const DEDENT_FINALS = new Set(DEDENT_KEYWORDS.map((k) => k[k.length - 1]));

let applyingIndent = false;

// ---------------------------------------------------------------------------
// Per-document state cache
// ---------------------------------------------------------------------------

// uri.toString() -> { state: string, lnum: number }
//
// `lnum` is 1-based, matching the line numbering ada-indent.el and
// ada-indent.vim use and the one a reader comparing the three will expect.
// VS Code's own line numbers are 0-based; the conversion happens at the edges
// of this file and nowhere else.
const cache = new Map();

function getCache(document) {
  if (!vscode.workspace.getConfiguration("adaIndent").get("enableStateCache", true)) {
    return null;
  }
  return cache.get(document.uri.toString()) || null;
}

function setCache(document, state, lnum) {
  cache.set(document.uri.toString(), { state, lnum });
}

function dropCache(document) {
  cache.delete(document.uri.toString());
}

// Drop the cache when a change lands above the cache point.
//
// Strictly above, as in the other two integrations: the state captured after
// line N is derived from lines 1..N and is unaffected by re-whitespacing line N
// itself, because ada_indent strips leading whitespace before it looks at a
// line. Using <= instead would wipe the cache on the very edit that formatting
// makes, leaving it permanently useless.
//
// Also drives on-type indentation via handleOnTypeIndent, which uses
// WorkspaceEdit rather than registerOnTypeFormattingEditProvider. VS Code only
// allows one on-type formatting provider per language; when AdaCore's Ada
// extension registers its own, it shadows ours. A change-event listener has
// no such conflict.
function onDocumentChanged(event) {
  const entry = cache.get(event.document.uri.toString());
  if (entry) {
    for (const change of event.contentChanges) {
      if (change.range.start.line + 1 < entry.lnum) {
        dropCache(event.document);
        break;
      }
    }
  }

  if (
    !applyingIndent &&
    event.document.languageId === "ada" &&
    event.contentChanges.length > 0
  ) {
    handleOnTypeIndent(event.document, event.contentChanges);
  }
}

async function handleOnTypeIndent(document, changes) {
  const cfg = vscode.workspace.getConfiguration("editor", { uri: document.uri, languageId: document.languageId });
  if (!cfg.get("formatOnType")) return;

  for (const change of changes) {
    if (change.text.includes("\n")) {
      const nlCount = (change.text.match(/\n/g) || []).length;
      const targetLine = change.range.start.line + nlCount;
      if (targetLine >= document.lineCount) continue;
      await applyOnTypeIndent(document, targetLine);
      return;
    }

    if (change.text.length === 1 && DEDENT_FINALS.has(change.text.toLowerCase())) {
      const targetLine = change.range.start.line;
      if (!DEDENT_KEYWORDS.includes(document.lineAt(targetLine).text.trim().toLowerCase())) {
        continue;
      }
      await applyOnTypeIndent(document, targetLine);
      return;
    }
  }
}

async function applyOnTypeIndent(document, line) {
  const want = await indentColumn(document, line);
  if (want === null) return;

  const text = document.lineAt(line).text;
  const have = text.length - text.replace(/^[ \t]+/, "").length;
  if (want === have && !/^\t/.test(text)) return;

  const edit = new vscode.WorkspaceEdit();
  edit.replace(
    document.uri,
    new vscode.Range(line, 0, line, have),
    " ".repeat(want)
  );

  applyingIndent = true;
  try {
    await vscode.workspace.applyEdit(edit);
  } finally {
    applyingIndent = false;
  }
}

// ---------------------------------------------------------------------------
// Running the binary
// ---------------------------------------------------------------------------

function program() {
  return vscode.workspace.getConfiguration("adaIndent").get("program") || "ada_indent";
}

let warnedMissing = false;

/** Run ada_indent over `input`, resuming from `state` when one is given.
 *
 * Resolves to { code, state } -- the output's code lines in order, and the
 * last state snapshot, or null when the binary emitted none.
 */
function runIndent(input, state) {
  const args = state ? ["--state", state, "--emit-state"] : ["--emit-state"];
  return new Promise((resolve, reject) => {
    const child = execFile(
      program(), args, { maxBuffer: 64 * 1024 * 1024 },
      (err, stdout) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(splitOutput(stdout));
      }
    );
    child.stdin.end(input);
  });
}

/** Separate the interleaved ##STATE: lines from the indented code lines.
 *
 * Only the final empty element is dropped -- the one the trailing newline
 * leaves behind. An empty line in the middle is a blank line in the file, and
 * removing it would shift every line after it, which is what the region path
 * indexes by.
 */
function splitOutput(stdout) {
  const all = stdout.split("\n");
  if (all.length > 0 && all[all.length - 1] === "") {
    all.pop();
  }
  const code = [];
  let state = null;
  for (const line of all) {
    if (line.startsWith(STATE_PREFIX)) {
      state = line.slice(STATE_PREFIX.length);
    } else {
      code.push(line);
    }
  }
  return { code, state };
}

/** ada_indent emits spaces only, so the leading run of them is the indent. */
function indentOf(line) {
  return line.length - line.replace(/^ +/, "").length;
}

function reportFailure(err) {
  if (warnedMissing) {
    return;
  }
  warnedMissing = true;
  vscode.window.showErrorMessage(
    `Ada Indent: could not run '${program()}' (${err.code || err.message}). ` +
      "Build it with `ady2nim TOOLS/ADA_INDENT/ada_indent.ady` and put it on PATH, " +
      "or set adaIndent.program to its full path."
  );
}

// ---------------------------------------------------------------------------
// The two things the providers need
// ---------------------------------------------------------------------------

/** Reindent lines `first`..`last` (0-based, inclusive) of `document`.
 *
 * One ada_indent run: lines above the region are sent only to establish the
 * open-block stack and are never edited, and the cache lets that prefix start
 * partway down the file instead of at line 1.
 *
 * Returns TextEdits that replace each line's leading whitespace, and only
 * where it actually changed -- so an already-correct file produces no edits,
 * and the cursor and selection survive the ones it does produce.
 */
async function indentRange(document, first, last) {
  const entry = getCache(document);
  // 1-based, to match the cache and the other integrations.
  const firstLnum = first + 1;
  const useCache = entry && entry.lnum > 0 && entry.lnum < firstLnum;
  const startLnum = useCache ? entry.lnum + 1 : 1;

  const lines = [];
  for (let i = startLnum - 1; i <= last; i++) {
    lines.push(document.lineAt(i).text);
  }

  let out;
  try {
    out = await runIndent(lines.join("\n"), useCache ? entry.state : null);
  } catch (err) {
    reportFailure(err);
    return [];
  }

  const edits = [];
  for (let line = first; line <= last; line++) {
    // code[i] is the output for document line (startLnum - 1 + i).
    const produced = out.code[line - (startLnum - 1)];
    if (produced === undefined) {
      continue;
    }
    const text = document.lineAt(line).text;
    const want = indentOf(produced);
    const have = text.length - text.replace(/^[ \t]+/, "").length;
    if (want === have && !/^\t/.test(text)) {
      continue;   // already right, and not a tab pretending to be right
    }
    edits.push(
      vscode.TextEdit.replace(
        new vscode.Range(line, 0, line, have),
        " ".repeat(want)
      )
    );
  }

  if (out.state) {
    setCache(document, out.state, last + 1);
  }
  return edits;
}

/** The column ada_indent gives line `line` (0-based) of `document`.
 *
 * The single-line counterpart of indentRange, for the on-type path. A blank
 * line is probed with a neutral token so it picks up the enclosing block's
 * indent rather than column 0 -- otherwise pressing Enter would put the cursor
 * at the left margin.
 */
async function indentColumn(document, line) {
  const entry = getCache(document);
  const lnum = line + 1;
  const useCache = entry && entry.lnum > 0 && entry.lnum < lnum;
  const startLnum = useCache ? entry.lnum + 1 : 1;

  const lines = [];
  for (let i = startLnum - 1; i < line; i++) {
    lines.push(document.lineAt(i).text);
  }
  const current = document.lineAt(line).text;
  lines.push(current.trim() === "" ? "x" : current);

  let out;
  try {
    out = await runIndent(lines.join("\n"), useCache ? entry.state : null);
  } catch (err) {
    reportFailure(err);
    return null;
  }

  if (out.state) {
    setCache(document, out.state, lnum);
  }
  if (out.code.length === 0) {
    return null;
  }
  return indentOf(out.code[out.code.length - 1]);
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

const documentFormatter = {
  provideDocumentFormattingEdits(document) {
    return indentRange(document, 0, document.lineCount - 1);
  },
};

const rangeFormatter = {
  provideDocumentRangeFormattingEdits(document, range) {
    // A range ending at the very start of a line does not pull that line in,
    // which is the rule VS Code's own selection formatting follows.
    let last = range.end.line;
    if (last > range.start.line && range.end.character === 0) {
      last -= 1;
    }
    return indentRange(document, range.start.line, last);
  },
};

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

function activate(context) {
  const selector = { scheme: "file", language: "ada" };

  context.subscriptions.push(
    vscode.languages.registerDocumentFormattingEditProvider(selector, documentFormatter),
    vscode.languages.registerDocumentRangeFormattingEditProvider(selector, rangeFormatter),
    vscode.workspace.onDidChangeTextDocument(onDocumentChanged),
    vscode.workspace.onDidCloseTextDocument(dropCache),
    vscode.commands.registerCommand("adaIndent.reindentBuffer", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document.languageId !== "ada") {
        return;
      }
      const document = editor.document;
      const edits = await indentRange(document, 0, document.lineCount - 1);
      if (edits.length === 0) {
        return;
      }
      const wsEdit = new vscode.WorkspaceEdit();
      wsEdit.set(document.uri, edits);
      await vscode.workspace.applyEdit(wsEdit);
    })
  );
}

function deactivate() {
  cache.clear();
}

module.exports = { activate, deactivate };
