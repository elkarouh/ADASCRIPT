"use strict";

const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

function cfg() {
  const c = vscode.workspace.getConfiguration("git1");
  return {
    program: c.get("program") || "git1",
    container: c.get("container") || ".git1",
  };
}

// ---------------------------------------------------------------------------
// Repo detection
// ---------------------------------------------------------------------------

function repoForFile(filePath) {
  if (!filePath) return null;
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  const { container } = cfg();
  const repo = path.join(dir, container, base);
  try {
    if (
      fs.statSync(repo).isDirectory() &&
      fs.existsSync(path.join(repo, "HEAD"))
    ) {
      return repo;
    }
  } catch (_) {}
  return null;
}

function isTracked(filePath) {
  return repoForFile(filePath) !== null;
}

// ---------------------------------------------------------------------------
// Run git against a file's repo
// ---------------------------------------------------------------------------

function gitArgs(filePath) {
  const repo = repoForFile(filePath);
  if (!repo) return null;
  const dir = path.dirname(filePath);
  return [`--git-dir=${repo}`, `--work-tree=${dir}`];
}

function gitSync(filePath, args) {
  const extra = gitArgs(filePath);
  if (!extra) throw new Error("Not a git1-tracked file");
  const cmd = ["git", ...extra, ...args].map(shellQuote).join(" ");
  return execSync(cmd, {
    cwd: path.dirname(filePath),
    encoding: "utf-8",
    timeout: 10000,
  });
}

function shellQuote(s) {
  if (/^[\w./:=@-]+$/.test(s)) return s;
  return "'" + s.replace(/'/g, "'\\''") + "'";
}

// ---------------------------------------------------------------------------
// QuickDiff provider — gives VS Code the original (HEAD) content of a file
// so it can compute and render the native gutter change bars.
// ---------------------------------------------------------------------------

const GIT1_SCHEME = "git1-original";

class Git1OriginalProvider {
  provideTextDocumentContent(uri) {
    const filePath = uri.query; // we stash the real path in the query
    try {
      const base = path.basename(filePath);
      return gitSync(filePath, ["show", `HEAD:${base}`]);
    } catch (_) {
      return ""; // no HEAD yet (first commit not done) — treat as empty
    }
  }
}

function originalUri(filePath) {
  return vscode.Uri.parse(
    `${GIT1_SCHEME}:${path.basename(filePath)}?${filePath}`
  );
}

// ---------------------------------------------------------------------------
// SCM provider — one SourceControl per tracked file
// ---------------------------------------------------------------------------

// Track active SCM instances per file path
const scmInstances = new Map();

function ensureSCM(filePath, context) {
  if (scmInstances.has(filePath)) return scmInstances.get(filePath);
  if (!isTracked(filePath)) return null;

  const base = path.basename(filePath);
  const scm = vscode.scm.createSourceControl("git1", `git1: ${base}`, vscode.Uri.file(path.dirname(filePath)));
  scm.quickDiffProvider = { provideOriginalResource: (uri) => originalUri(uri.fsPath) };
  scm.inputBox.placeholder = `Commit message for ${base}`;

  // Resource groups
  const changes = scm.createResourceGroup("changes", "Changes");
  changes.hideWhenEmpty = true;

  // Store references
  const instance = { scm, changes, filePath };
  scmInstances.set(filePath, instance);
  context.subscriptions.push(scm);

  // Accept input box → commit
  scm.acceptInputCommand = {
    command: "git1.commitFromSCM",
    title: "Commit",
    arguments: [filePath],
  };

  return instance;
}

function updateSCMStatus(filePath) {
  const inst = scmInstances.get(filePath);
  if (!inst) return;

  try {
    const status = gitSync(filePath, ["status", "--short", "--", path.basename(filePath)]).trim();
    if (status) {
      const uri = vscode.Uri.file(filePath);
      inst.changes.resourceStates = [{
        resourceUri: uri,
        decorations: {
          strikeThrough: false,
          tooltip: status,
        },
      }];
      inst.scm.count = 1;
    } else {
      inst.changes.resourceStates = [];
      inst.scm.count = 0;
    }
  } catch (_) {
    inst.changes.resourceStates = [];
    inst.scm.count = 0;
  }
}

// ---------------------------------------------------------------------------
// Status bar item
// ---------------------------------------------------------------------------

let statusBar;

function updateStatusBar(editor) {
  if (!editor || !editor.document || editor.document.uri.scheme !== "file") {
    statusBar.hide();
    return;
  }
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath)) {
    statusBar.hide();
    vscode.commands.executeCommand("setContext", "git1:tracked", false);
    vscode.commands.executeCommand("setContext", "git1:dirty", false);
    return;
  }
  vscode.commands.executeCommand("setContext", "git1:tracked", true);
  try {
    const branch = gitSync(filePath, ["rev-parse", "--abbrev-ref", "HEAD"]).trim();
    const status = gitSync(filePath, ["status", "--short"]).trim();
    const dirty = status.length > 0;
    vscode.commands.executeCommand("setContext", "git1:dirty", dirty);
    statusBar.text = `$(git-branch) git1: ${branch}${dirty ? " *" : ""}`;
    statusBar.tooltip = `git1: ${path.basename(filePath)}\nBranch: ${branch}${dirty ? "\nModified" : ""}`;
    statusBar.show();
  } catch (e) {
    statusBar.text = "$(git-branch) git1";
    statusBar.tooltip = `git1-tracked: ${path.basename(filePath)}`;
    statusBar.show();
  }
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

async function cmdInit() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return vscode.window.showErrorMessage("No file open");
  const filePath = editor.document.uri.fsPath;
  if (isTracked(filePath)) {
    return vscode.window.showInformationMessage("Already tracked by git1");
  }
  try {
    const { program } = cfg();
    const dir = path.dirname(filePath);
    const base = path.basename(filePath);
    execSync(`${shellQuote(program)} init ${shellQuote(base)}`, { cwd: dir, encoding: "utf-8" });
    vscode.window.showInformationMessage(`git1: now tracking ${base}`);
    updateStatusBar(editor);
  } catch (e) {
    vscode.window.showErrorMessage(`git1 init failed: ${e.message}`);
  }
}

async function cmdCommit() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  if (editor.document.isDirty) await editor.document.save();
  try {
    gitSync(filePath, ["add", "--", path.basename(filePath)]);
  } catch (e) {
    return vscode.window.showErrorMessage(`git add failed: ${e.message}`);
  }
  const msg = await vscode.window.showInputBox({
    prompt: `Commit message for ${path.basename(filePath)}`,
    placeHolder: "Describe the change",
  });
  if (!msg) return;
  try {
    gitSync(filePath, ["commit", "-m", msg]);
    vscode.window.showInformationMessage(`git1: committed ${path.basename(filePath)}`);
    updateStatusBar(editor);
    updateSCMStatus(filePath);
    fileDecoProvider.fireChange([vscode.Uri.file(filePath)]);
  } catch (e) {
    vscode.window.showErrorMessage(`git commit failed: ${e.message}`);
  }
}

async function cmdCommitFromSCM(filePath) {
  if (!filePath || !isTracked(filePath)) return;
  const inst = scmInstances.get(filePath);
  const msg = inst && inst.scm.inputBox.value;
  if (!msg) {
    vscode.window.showWarningMessage("Enter a commit message in the SCM input box");
    return;
  }
  try {
    gitSync(filePath, ["add", "--", path.basename(filePath)]);
    gitSync(filePath, ["commit", "-m", msg]);
    inst.scm.inputBox.value = "";
    vscode.window.showInformationMessage(`git1: committed ${path.basename(filePath)}`);
    updateStatusBar(vscode.window.activeTextEditor);
    updateSCMStatus(filePath);
    fileDecoProvider.fireChange([vscode.Uri.file(filePath)]);
  } catch (e) {
    vscode.window.showErrorMessage(`git commit failed: ${e.message}`);
  }
}

async function cmdDiff() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  const base = path.basename(filePath);
  const orig = originalUri(filePath);
  const current = vscode.Uri.file(filePath);
  vscode.commands.executeCommand("vscode.diff", orig, current, `${base} (git1 diff)`);
}

async function cmdLog() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  try {
    const log = gitSync(filePath, ["log", "--oneline", "--decorate", "-30"]);
    const doc = await vscode.workspace.openTextDocument({
      content: log || "(no commits)",
      language: "plaintext",
    });
    vscode.window.showTextDocument(doc, { preview: true });
  } catch (e) {
    vscode.window.showErrorMessage(`git log failed: ${e.message}`);
  }
}

async function cmdGraphText() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  try {
    const graph = gitSync(filePath, [
      "log", "--graph", "--oneline", "master", "--all", "--decorate",
      "--color=never",
    ]);
    const doc = await vscode.workspace.openTextDocument({
      content: graph || "(no commits)",
      language: "plaintext",
    });
    vscode.window.showTextDocument(doc, { preview: true });
  } catch (e) {
    vscode.window.showErrorMessage(`git log --graph failed: ${e.message}`);
  }
}

async function cmdGraphVisual() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  const base = path.basename(filePath);
  try {
    // Use git's own graph layout — it handles the topology correctly
    const raw = gitSync(filePath, [
      "log", "--graph", "master", "--all", "--color=never",
      "--format=%x00%h%x00%s%x00%cr%x00%D",
    ]).trim();
    if (!raw) return vscode.window.showInformationMessage("git1: no commits");

    const panel = vscode.window.createWebviewPanel(
      "git1Graph",
      `git1 graph: ${base}`,
      vscode.ViewColumn.Beside,
      { enableScripts: false }
    );

    // Get the hashes on the current branch to highlight them
    let currentHashes = new Set();
    try {
      const headLog = gitSync(filePath, ["log", "--format=%h", "--color=never"]).trim();
      if (headLog) headLog.split("\n").forEach((h) => currentHashes.add(h.trim()));
    } catch (_) {}

    panel.webview.html = graphHTML(base, raw, currentHashes);
  } catch (e) {
    vscode.window.showErrorMessage(`git graph failed: ${e.message}`);
  }
}

function graphHTML(filename, raw, currentHashes) {
  // Parse git log --graph output: each line has graph chars then \0hash\0msg\0date\0refs
  // or just graph chars (for merge lines like |\ |/)
  const lines = raw.split("\n");
  const rows = lines.map((line) => {
    const parts = line.split("\0");
    if (parts.length >= 4) {
      return { graph: parts[0], hash: parts[1], msg: parts[2], date: parts[3], refs: parts[4] || "" };
    }
    return { graph: line, hash: "", msg: "", date: "", refs: "" };
  });

  // Colorise the graph characters: * = node, | / \ = edges
  // Process char-by-char to avoid escaping the HTML we generate.
  function colorGraph(g) {
    let out = "";
    for (const ch of g) {
      if (ch === "*")       out += '<span class="node">●</span>';
      else if (ch === "|")  out += '<span class="edge">│</span>';
      else if (ch === "/")  out += '<span class="edge">╱</span>';
      else if (ch === "\\") out += '<span class="edge">╲</span>';
      else                  out += ch;
    }
    return out;
  }

  const rowsHTML = rows.map((r) => {
    if (!r.hash) {
      return `<div class="line"><span class="graph">${colorGraph(r.graph)}</span></div>`;
    }
    const isCurrent = currentHashes && currentHashes.has(r.hash);
    const cls = isCurrent ? "line current" : "line";
    const refBadge = r.refs ? ` <span class="ref">${escHtml(r.refs)}</span>` : "";
    return `<div class="${cls}"><span class="graph">${colorGraph(r.graph)}</span> <span class="hash">${escHtml(r.hash)}</span>${refBadge} <span class="msg">${escHtml(r.msg)}</span> <span class="date">${escHtml(r.date)}</span></div>`;
  }).join("\n");

  return `<!DOCTYPE html>
<html><head><style>
  body { font-family: 'Fira Code', 'DejaVu Sans Mono', Consolas, monospace;
         font-size: 13px; margin: 0; padding: 16px; color: #ccc; background: #1e1e1e; }
  h2 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       color: #eee; margin: 0 0 12px 0; font-size: 15px; font-weight: 500; }
  .line { white-space: pre; line-height: 1.6; }
  .graph { color: #666; }
  .node { color: #2ea043; font-size: 14px; }
  .edge { color: #555; }
  .hash { color: #f0c674; }
  .ref { background: #2d5a88; color: #58a6ff; padding: 1px 6px; border-radius: 3px;
         font-size: 11px; font-family: -apple-system, sans-serif; }
  .msg { color: #ddd; }
  .date { color: #666; font-size: 11px; }
  .current { background: #1a3a1a; border-radius: 3px; }
  .current .node { color: #58a6ff; }
  .current .hash { color: #58a6ff; }
  .current .msg { color: #fff; }
</style></head><body>
  <h2>git1 commit graph — ${escHtml(filename)}</h2>
  ${rowsHTML}
</body></html>`;
}

function escHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function cmdStatus() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  try {
    const status = gitSync(filePath, ["status", "--short", "--branch"]);
    vscode.window.showInformationMessage(`git1: ${status.trim()}`);
  } catch (e) {
    vscode.window.showErrorMessage(`git status failed: ${e.message}`);
  }
}

async function cmdRm() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  const base = path.basename(filePath);
  const answer = await vscode.window.showWarningMessage(
    `Delete the history of ${base}? The file itself is kept.`,
    { modal: true },
    "Delete History"
  );
  if (answer !== "Delete History") return;
  try {
    const { program } = cfg();
    execSync(`${shellQuote(program)} rm -f ${shellQuote(base)}`, {
      cwd: path.dirname(filePath),
      encoding: "utf-8",
    });
    vscode.window.showInformationMessage(`git1: stopped tracking ${base}`);
    const inst = scmInstances.get(filePath);
    if (inst) { inst.scm.dispose(); scmInstances.delete(filePath); }
    updateStatusBar(editor);
  } catch (e) {
    vscode.window.showErrorMessage(`git1 rm failed: ${e.message}`);
  }
}

async function cmdSwitchBranch() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  try {
    const raw = gitSync(filePath, ["branch", "--list"]).trim();
    if (!raw) return vscode.window.showInformationMessage("git1: no branches");
    const branches = raw.split("\n").map((b) => b.replace(/^\*?\s*/, "").trim());
    const current = raw.split("\n").find((b) => b.startsWith("*"));
    const currentName = current ? current.replace(/^\*\s*/, "").trim() : "";
    const picks = branches.filter((b) => b !== currentName);
    if (picks.length === 0)
      return vscode.window.showInformationMessage("git1: only one branch");
    const chosen = await vscode.window.showQuickPick(picks, {
      placeHolder: `Switch from ${currentName} to...`,
    });
    if (!chosen) return;
    // Check for uncommitted changes
    const dirty = gitSync(filePath, ["status", "--short"]).trim();
    if (dirty) {
      const action = await vscode.window.showWarningMessage(
        `${path.basename(filePath)} has uncommitted changes. What to do?`,
        "Stash & Switch", "Force Switch", "Cancel"
      );
      if (action === "Stash & Switch") {
        gitSync(filePath, ["stash", "push", "-m", `git1: auto-stash before switching to ${chosen}`]);
        gitSync(filePath, ["checkout", chosen]);
        try { gitSync(filePath, ["stash", "pop"]); } catch (_) {
          vscode.window.showWarningMessage("git1: stash pop had conflicts — resolve manually");
        }
      } else if (action === "Force Switch") {
        gitSync(filePath, ["checkout", "-f", chosen]);
      } else {
        return;
      }
    } else {
      gitSync(filePath, ["checkout", chosen]);
    }
    // Reload the file from disk (branch changed the content)
    await vscode.commands.executeCommand("workbench.action.files.revert");
    updateStatusBar(editor);
    updateSCMStatus(filePath);
    fileDecoProvider.fireChange([vscode.Uri.file(filePath)]);
    vscode.window.showInformationMessage(`git1: switched to ${chosen}`);
  } catch (e) {
    vscode.window.showErrorMessage(`git1 switch branch failed: ${e.message}`);
  }
}

async function cmdCreateBranch() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const filePath = editor.document.uri.fsPath;
  if (!isTracked(filePath))
    return vscode.window.showErrorMessage("Not tracked by git1");
  const name = await vscode.window.showInputBox({
    prompt: `New branch name for ${path.basename(filePath)}`,
    placeHolder: "feature/my-branch",
  });
  if (!name) return;
  try {
    gitSync(filePath, ["checkout", "-b", name]);
    updateStatusBar(editor);
    vscode.window.showInformationMessage(`git1: created and switched to ${name}`);
  } catch (e) {
    vscode.window.showErrorMessage(`git1 create branch failed: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// File decoration provider — "M" badge in the Explorer
// ---------------------------------------------------------------------------

class Git1FileDecorationProvider {
  constructor() {
    this._onDidChangeFileDecorations = new vscode.EventEmitter();
    this.onDidChangeFileDecorations = this._onDidChangeFileDecorations.event;
  }

  fireChange(uris) {
    this._onDidChangeFileDecorations.fire(uris);
  }

  provideFileDecoration(uri) {
    if (uri.scheme !== "file") return undefined;
    const filePath = uri.fsPath;
    if (!isTracked(filePath)) return undefined;
    try {
      const status = gitSync(filePath, [
        "status", "--short", "--", path.basename(filePath),
      ]).trim();
      if (!status) return undefined;
      const code = status.charAt(1) || status.charAt(0);
      if (code === "M" || code === "A" || code === "?" || code === " ") {
        const badge = code === " " ? "M" : code; // staged but not committed shows as M
        return {
          badge: status.charAt(0) !== " " ? status.charAt(0) : badge,
          tooltip: `git1: ${status}`,
          color: new vscode.ThemeColor("gitDecoration.modifiedResourceForeground"),
        };
      }
    } catch (_) {}
    return undefined;
  }
}

let fileDecoProvider;

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

function activate(context) {
  // Register the content provider for original (HEAD) file content
  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(
      GIT1_SCHEME,
      new Git1OriginalProvider()
    )
  );

  // File decoration provider for Explorer "M" badges
  fileDecoProvider = new Git1FileDecorationProvider();
  context.subscriptions.push(
    vscode.window.registerFileDecorationProvider(fileDecoProvider)
  );

  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBar.command = "git1.log";
  context.subscriptions.push(statusBar);

  context.subscriptions.push(
    vscode.commands.registerCommand("git1.init", cmdInit),
    vscode.commands.registerCommand("git1.commit", cmdCommit),
    vscode.commands.registerCommand("git1.commitFromSCM", cmdCommitFromSCM),
    vscode.commands.registerCommand("git1.diff", cmdDiff),
    vscode.commands.registerCommand("git1.log", cmdLog),
    vscode.commands.registerCommand("git1.status", cmdStatus),
    vscode.commands.registerCommand("git1.rm", cmdRm),
    vscode.commands.registerCommand("git1.switchBranch", cmdSwitchBranch),
    vscode.commands.registerCommand("git1.createBranch", cmdCreateBranch),
    vscode.commands.registerCommand("git1.graphText", cmdGraphText),
    vscode.commands.registerCommand("git1.graphVisual", cmdGraphVisual)
  );

  // When an editor becomes active, set up its SCM and update decorations
  function onEditor(editor) {
    updateStatusBar(editor);
    if (editor && editor.document && editor.document.uri.scheme === "file") {
      const fp = editor.document.uri.fsPath;
      if (isTracked(fp)) {
        ensureSCM(fp, context);
        updateSCMStatus(fp);
      }
    }
  }

  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(onEditor)
  );

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const editor = vscode.window.activeTextEditor;
      if (editor && editor.document === doc) {
        updateStatusBar(editor);
        const fp = doc.uri.fsPath;
        if (isTracked(fp)) {
          updateSCMStatus(fp);
          fileDecoProvider.fireChange([doc.uri]);
        }
      }
    })
  );

  // Initial setup for already-open editor
  onEditor(vscode.window.activeTextEditor);
}

function deactivate() {
  if (statusBar) statusBar.dispose();
  for (const [, inst] of scmInstances) inst.scm.dispose();
  scmInstances.clear();
}

module.exports = { activate, deactivate };
