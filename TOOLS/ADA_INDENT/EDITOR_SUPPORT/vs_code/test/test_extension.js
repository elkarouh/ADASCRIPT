// Drives ../extension.js against the real ada_indent binary, outside VS Code.
//
//     ada_indent must be on PATH; then:  node test/test_extension.js
//
// The editor API is stubbed (test/vscode-stub.js) but the extension code is
// the shipped file and the indenter is the real binary, so what is checked
// here is what the extension does. Expectations are taken from the binary's
// own output wherever they could otherwise drift from it.
"use strict";
const path = require("path");
const Module = require("module");

// Resolve `require("vscode")` to the stub without a node_modules directory.
const stub = require("./vscode-stub.js");
const realLoad = Module._load;
Module._load = function (request, parent, isMain) {
  return request === "vscode" ? stub : realLoad(request, parent, isMain);
};

const vscode = stub;
const ext = require("../extension.js");

// A document that behaves like VS Code's for the parts extension.js touches.
function doc(text, uri = "file:///t.adb") {
  const lines = text.split("\n");
  return {
    uri: { toString: () => uri },
    languageId: "ada",
    get lineCount() { return lines.length; },
    lineAt: (i) => ({ text: lines[i] }),
    _lines: lines,
  };
}
function apply(d, edits) {
  const out = d._lines.slice();
  for (const e of edits) {
    const l = e.range.start.line;
    out[l] = e.newText + out[l].slice(e.range.end.character);
  }
  return out.join("\n");
}

const ctx = { subscriptions: [] };
ext.activate(ctx);
const R = vscode.__registered;

let failed = 0;
function check(name, got, want) {
  const ok = got === want;
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}`);
  if (!ok) console.log(`  got:\n${got}\n  want:\n${want}`);
}

const MESSY = [
  "procedure P is",
  "X : Integer;",
  "begin",
  "if X > 0 then",
  "Y := 1;",
  "else",
  "Y := 2;",
  "end if;",
  "end P;",
].join("\n");

// The binary's own output, so the expectation cannot drift from it.
const CANON = require("child_process")
  .execFileSync("ada_indent", [], { input: MESSY + "\n" })
  .toString().replace(/\n$/, "");

(async () => {
  // 1. Format Document reproduces what the binary does on its own.
  const { execFileSync } = require("child_process");
  const direct = execFileSync("ada_indent", [], { input: MESSY + "\n" }).toString().replace(/\n$/, "");
  const d1 = doc(MESSY);
  check("format document == binary", apply(d1, await R.doc.provideDocumentFormattingEdits(d1)), direct);

  // 2. An already-correct file produces no edits at all.
  const d2 = doc(CANON);
  const e2 = await R.doc.provideDocumentFormattingEdits(d2);
  check("canonical file -> no edits", e2.length, 0);

  // 3. Format Selection touches only the selected lines.
  const d3 = doc(MESSY);
  const e3 = await R.range.provideDocumentRangeFormattingEdits(d3, new vscode.Range(3, 0, 5, 0));
  check("selection edits only lines 3..4", e3.map(e => e.range.start.line).join(","), "3,4");

  // 4. A selection ending at column 0 of a line does not pull that line in.
  const d4 = doc(MESSY);
  const e4 = await R.range.provideDocumentRangeFormattingEdits(d4, new vscode.Range(1, 0, 2, 0));
  check("range end at col 0 excludes its line", e4.map(e => e.range.start.line).join(","), "1");

  // 5. The state cache gives the same answer as a cold run.
  const d5 = doc(MESSY);
  await R.range.provideDocumentRangeFormattingEdits(d5, new vscode.Range(0, 0, 2, 0));  // warms it
  const warm = await R.range.provideDocumentRangeFormattingEdits(d5, new vscode.Range(3, 0, 8, 8));
  vscode.__config.enableStateCache = false;
  const d5b = doc(MESSY, "file:///t2.adb");
  const cold = await R.range.provideDocumentRangeFormattingEdits(d5b, new vscode.Range(3, 0, 8, 8));
  vscode.__config.enableStateCache = true;
  check("warm cache == cold run",
        JSON.stringify(warm.map(e => [e.range.start.line, e.newText])),
        JSON.stringify(cold.map(e => [e.range.start.line, e.newText])));

  // 6. On-type via onChange: a bare "else" snaps left.
  const d6 = doc(["procedure P is", "begin", "   if X then", "      Y := 1;", "else", "end P;"].join("\n"));
  vscode.__clearApplied();
  R.onChange({ document: d6, contentChanges: [{ text: "e", range: { start: { line: 4 } } }] });
  await new Promise(r => setTimeout(r, 500));
  const a6 = vscode.__lastApplied();
  check("bare else snaps to column 2", a6 && a6._edits[0].newText.length, 2);

  // A word that merely ends in "e" does not trigger.
  const d7 = doc(["procedure P is", "begin", "   if X then", "      Something_Else", "end P;"].join("\n"));
  vscode.__clearApplied();
  R.onChange({ document: d7, contentChanges: [{ text: "e", range: { start: { line: 3 } } }] });
  await new Promise(r => setTimeout(r, 500));
  check("non-keyword ending in e -> no edits", vscode.__lastApplied(), null);

  // 7. Enter on a blank line inside a block indents to the block body.
  const d8 = doc(["procedure P is", "begin", "   if X then", "", "end P;"].join("\n"));
  vscode.__clearApplied();
  R.onChange({ document: d8, contentChanges: [{ text: "\n", range: { start: { line: 2 } } }] });
  await new Promise(r => setTimeout(r, 500));
  const a8 = vscode.__lastApplied();
  check("blank line inside if -> body indent 4", a8 && a8._edits[0].newText.length, 4);

  // 9. Formatting is a fixpoint: format twice, nothing the second time.
  const d9 = doc(apply(doc(MESSY), await R.doc.provideDocumentFormattingEdits(doc(MESSY))), "file:///t9.adb");
  check("fixpoint", (await R.doc.provideDocumentFormattingEdits(d9)).length, 0);

  console.log(failed === 0 ? "\nall ok" : `\n${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
})();
