"use strict";

const path = require("path");
const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const config = vscode.workspace.getConfiguration("adascript");
  const python = config.get("python") || "python3.13";

  // Default server path: sibling file LSP/adascript_ls.py (one directory up)
  const serverPath =
    config.get("serverPath") ||
    path.join(context.extensionPath, "..", "adascript_ls.py");

  const serverOptions = {
    run: {
      command: python,
      args: [serverPath],
      transport: TransportKind.stdio,
    },
    debug: {
      command: python,
      args: [serverPath],
      transport: TransportKind.stdio,
    },
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "adascript" }],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.ady"),
    },
    traceOutputChannel: vscode.window.createOutputChannel(
      "Adascript Language Server Trace"
    ),
  };

  client = new LanguageClient(
    "adascript",
    "Adascript Language Server",
    serverOptions,
    clientOptions
  );

  client.start();
  context.subscriptions.push(client);
}

function deactivate() {
  return client ? client.stop() : undefined;
}

module.exports = { activate, deactivate };
