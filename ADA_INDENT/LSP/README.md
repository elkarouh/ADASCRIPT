# ada-indent-lsp — Ada Indentation via LSP

A lightweight Language Server Protocol server that provides Ada source
indentation by wrapping the `ada_indent` binary.  Works with any LSP-capable
editor: Emacs (eglot/lsp-mode), VS Code, Neovim, Helix, etc.

## What it provides

| LSP capability | Trigger | Description |
|---|---|---|
| `textDocument/formatting` | Format document | Reindent the entire file |
| `textDocument/rangeFormatting` | Format selection | Reindent a region (also used by indent-line) |
| `textDocument/onTypeFormatting` | Enter / dedent keyword | Auto-indent new lines and snap dedenting keywords |

The server maintains a **per-document state cache** (same strategy as
`ada-indent.el`) so incremental formatting only processes lines from the
last cache point — O(distance) per edit instead of O(file size).

## Prerequisites

- **`ada_indent`** binary on your PATH.  Build it once from `ada_indent.ady`:

  ```bash
  ady2nim c ADA_INDENT/ada_indent.ady
  ln -sf "$PWD/ADA_INDENT/ada_indent" ~/.local/bin/ada_indent
  ```

- **Python 3.10+** with `pygls` and `lsprotocol`:

  ```bash
  pip install pygls lsprotocol
  ```

## Usage

Start the server (communicates over stdio):

```bash
python3 ada-indent-lsp.py
```

Options:

```
--ada-indent PATH   Path to ada_indent binary (default: ada_indent on PATH)
--log FILE          Write debug log to FILE (default: no logging)
```

## Editor setup

### Emacs — eglot (built-in since Emacs 29)

```elisp
(with-eval-after-load 'eglot
  (add-to-list 'eglot-server-programs
               '((ada-mode ada-ts-mode) . ("python3" "/path/to/ada-indent-lsp.py"))))

;; Then in an Ada buffer:
;;   M-x eglot    (start the server)
;;   C-M-\        (indent region)
;;   M-x eglot-format-buffer
```

### Emacs — lsp-mode

```elisp
(with-eval-after-load 'lsp-mode
  (lsp-register-client
   (make-lsp-client
    :new-connection (lsp-stdio-connection '("python3" "/path/to/ada-indent-lsp.py"))
    :major-modes '(ada-mode ada-ts-mode)
    :server-id 'ada-indent-lsp)))

(add-hook 'ada-mode-hook #'lsp)
```

### Neovim — nvim-lspconfig

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

configs.ada_indent = {
  default_config = {
    cmd = { "python3", "/path/to/ada-indent-lsp.py" },
    filetypes = { "ada" },
    root_dir = lspconfig.util.find_git_ancestor,
  },
}
lspconfig.ada_indent.setup{}
```

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "ada-indent-lsp.path": "python3",
  "ada-indent-lsp.args": ["/path/to/ada-indent-lsp.py"]
}
```

Or use a generic LSP client extension and point it at the server command.

### Helix

Add to `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "ada"
language-servers = ["ada-indent-lsp"]

[language-server.ada-indent-lsp]
command = "python3"
args = ["/path/to/ada-indent-lsp.py"]
```

## How it works

1. The server tracks document content via `didOpen` / `didChange` / `didClose`
   notifications, applying incremental edits to an in-memory copy.

2. On a formatting request, it pipes the relevant lines through `ada_indent
   --emit-state`, reads back the indented output, and returns LSP `TextEdit`s
   that replace only the leading whitespace of lines whose indentation changed.

3. The `##STATE:` lines emitted by `ada_indent` are captured and cached
   per-document.  Subsequent requests reuse the cache via `--state <data>`,
   skipping all lines before the cache point.

4. The cache is invalidated when an edit occurs before the cache point
   (same rule as `ada-indent.el`).

## Comparison with ada-indent.el

| | ada-indent.el | ada-indent-lsp.py |
|---|---|---|
| Protocol | Emacs-native hooks | LSP (any editor) |
| Communication | `call-process-region` | stdio subprocess |
| State cache | `defvar-local` per buffer | `DocState` per URI |
| On-type indent | `post-self-insert-hook` | `onTypeFormatting` |
| Dependencies | Emacs only | Python 3 + pygls |

Both call the same `ada_indent` binary with the same `--state` / `--emit-state`
protocol.  For Emacs, `ada-indent.el` is lighter (no Python process); for other
editors, the LSP server is the way in.

## Testing

```bash
cd ADA_INDENT/LSP
python3 test_lsp.py
```

The test suite has three layers:

| Layer | What it tests |
|---|---|
| **Unit** | `_apply_change` incremental edit logic (no external dependencies) |
| **Integration** | `ada_indent` binary: package, enum, record indentation, state cache, fixpoint |
| **LSP end-to-end** | Full server over stdio: initialize, didOpen, formatting, rangeFormatting, didChange, shutdown |

The LSP tests start the server as a subprocess and send raw JSON-RPC — no
pygls needed on the test side (only the server subprocess needs it).

## Known limitations

- **On-type formatting triggers on keyword-final letters only** — not every
  keystroke, but still one LSP round-trip per letter that could end a dedenting
  keyword (`d`, `e`, `n`, `s`, `t`, etc.).  The server checks for a complete
  keyword and returns no edits for non-matching lines.

- **No semantic features** — this server provides indentation only.  For
  navigation, completion, and diagnostics, use it alongside an Ada language
  server (e.g. `ada_language_server` from AdaCore).
