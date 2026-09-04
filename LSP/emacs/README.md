# Adascript — Emacs Major Mode

`adascript-mode` is an Emacs major mode for [Adascript](https://github.com/elkarouh/adascript) (`.ady` files).

## Features

- **Syntax highlighting** — type declarations, tick attributes (`Color'First`), Ada/Adascript keywords, plus Python and Nim syntax via `nim-mode`
- **Indentation** — offside rule, inherited from `nim-mode`
- **Diagnostics, hover, completion** — via the Adascript language server (`adascript_ls.py`) through either **eglot** (built-in, Emacs 29+) or **lsp-mode** (third-party)
- **Bracket matching and auto-close** — inherited from `nim-mode`

## Requirements

| Requirement | Version |
|---|---|
| Emacs | ≥ 28.1 |
| `nim-mode` | ≥ 0.4.1 — `M-x package-install RET nim-mode` (MELPA) |
| Python | 3.13+ |
| pygls | ≥ 2.1.1 (`python3.13 -m pip install pygls`) |

`nim-mode` is not optional: `adascript-mode` derives from it, so without it
`(require 'adascript-mode)` fails with "Cannot open load file: nim-mode".

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

Five custom faces can be themed independently:

| Face | Default | Applied to |
|---|---|---|
| `adascript-type-name-face` | `font-lock-type-face` | The `NAME` in `type NAME is …` |
| `adascript-tick-type-face` | `font-lock-type-face` | The type part of `Color'First` |
| `adascript-tick-attr-face` | `font-lock-builtin-face` | The attribute part of `Color'First` |
| `adascript-shell-face` | `font-lock-preprocessor-face` | The `shell:` / `shellLines:` keywords |
| `adascript-range-op-face` | `font-lock-operator-face`, or `font-lock-builtin-face` before Emacs 30 | The range operators `..` and `..<` |

## Notes

- `'` is punctuation in the syntax table, so `Color'First` is not mis-lexed as the start of a string and an apostrophe in prose — `the command's output` inside a docstring — cannot open one either. `syntax-propertize` then promotes just the pairs that really delimit a string, so `'hello'` is still highlighted as one.
- Escaped quotes inside a prefixed string (`f"... \"x\" ..."`) are repaired after `nim-mode` runs: Nim reads `ident"..."` as a raw string literal where a backslash is not an escape, which would otherwise end the string early and invert the highlighting of the rest of the buffer.
- The mode derives from `nim-mode`, so its navigation commands work in `.ady` files.
