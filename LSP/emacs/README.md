# Adascript — Emacs Major Mode

`adascript-mode` is an Emacs major mode for [Adascript](https://github.com/elkarouh/adascript) (`.ady` files).

## Features

- **Syntax highlighting** — type declarations, tick attributes (`Color'First`), Ada/Adascript keywords, all Python syntax via `python-mode`
- **Indentation** — Python offside rule, inherited from `python-mode`
- **Diagnostics, hover, completion** — via the Adascript language server (`adascript_ls.py`) through either **eglot** (built-in, Emacs 29+) or **lsp-mode** (third-party)
- **Bracket matching and auto-close** — inherited from `python-mode`

## Requirements

| Requirement | Version |
|---|---|
| Emacs | ≥ 28.1 |
| Python | 3.13+ |
| pygls | ≥ 2.1.1 (`python3.13 -m pip install pygls`) |

## Installation

### Manual

```elisp
(add-to-list 'load-path "/path/to/ADASCRIPT/LSP/emacs")
(require 'adascript-mode)
```

### use-package

```elisp
(use-package adascript-mode
  :load-path "/path/to/ADASCRIPT/LSP/emacs")
```

`.ady` files are associated with `adascript-mode` automatically via `auto-mode-alist`.

## LSP Setup

### eglot (Emacs 29+, built-in — recommended)

eglot is registered automatically when `adascript-mode` loads. To start it:

```elisp
;; Manually: open a .ady file, then M-x eglot

;; Or auto-start on every .ady file:
(add-hook 'adascript-mode-hook #'eglot-ensure)
```

### lsp-mode (third-party)

`lsp-mode` is registered automatically when both packages are loaded. To auto-start:

```elisp
;; Option A — via the customization variable:
(setq adascript-lsp-mode-auto-enable t)

;; Option B — manually add the hook:
(add-hook 'adascript-mode-hook #'lsp-deferred)
```

## Customization

| Variable | Default | Description |
|---|---|---|
| `adascript-python-command` | `"python3.13"` | Python interpreter used to start the server |
| `adascript-server-path` | `../adascript_ls.py` | Absolute path to `adascript_ls.py` |
| `adascript-lsp-mode-auto-enable` | `nil` | Auto-start lsp-mode in adascript buffers |

```elisp
(setq adascript-python-command "python3.13"
      adascript-server-path    "/absolute/path/to/ADASCRIPT/LSP/adascript_ls.py")
```

The default `adascript-server-path` resolves to the `adascript_ls.py` sitting one directory above this file (`LSP/adascript_ls.py`), which works when the repository is used as-is.

## Faces

Three custom faces can be themed independently:

| Face | Default | Applied to |
|---|---|---|
| `adascript-type-name-face` | `font-lock-type-face` | The `NAME` in `type NAME is …` |
| `adascript-tick-type-face` | `font-lock-type-face` | The type part of `Color'First` |
| `adascript-tick-attr-face` | `font-lock-builtin-face` | The attribute part of `Color'First` |

## Notes

- `'` is set to punctuation in the syntax table so that `Color'First` is not mis-lexed as the start of a string. Single-quoted Python strings (`'hello'`) are still highlighted correctly by the inherited font-lock string rules.
- The mode derives from `python-mode`, so all standard Python navigation commands (`C-M-f`, `C-M-b`, `C-c C-j`, etc.) work in `.ady` files.
