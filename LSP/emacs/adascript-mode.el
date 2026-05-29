;;; adascript-mode.el --- Major mode for Adascript (.ady) files -*- lexical-binding: t; -*-

;; Author: Adascript Project
;; Version: 0.1.0
;; Keywords: languages ada python
;; Package-Requires: ((emacs "28.1") (python "0.28"))
;; URL: https://github.com/elkarouh/adascript

;;; Commentary:

;; Major mode for Adascript, an Ada-inspired statically-typed superset of Python 3.
;;
;; Derived from `python-mode', this mode adds:
;;   - Syntax highlighting for type declarations, tick attributes, and Ada keywords
;;   - eglot integration (Emacs 29+ built-in LSP client)  — zero extra packages
;;   - lsp-mode integration (opt-in, see `adascript-lsp-mode-auto-enable')
;;
;; Quick setup (init.el):
;;
;;   (add-to-list 'load-path "/path/to/ADASCRIPT/LSP/emacs")
;;   (require 'adascript-mode)
;;
;; With use-package:
;;
;;   (use-package adascript-mode
;;     :load-path "/path/to/ADASCRIPT/LSP/emacs"
;;     :custom
;;     (adascript-python-command "python3.13")
;;     (adascript-server-path    "/path/to/ADASCRIPT/LSP/adascript_ls.py"))
;;
;; eglot (Emacs 29+): open any .ady file, then M-x eglot.
;;   Auto-registers; no extra config needed.
;;
;; lsp-mode: set `adascript-lsp-mode-auto-enable' to t (or add the hook yourself):
;;   (add-hook 'adascript-mode-hook #'lsp-deferred)

;;; Code:

(require 'rx)
(require 'python)
(require 'cl-lib)

;; ---------------------------------------------------------------------------
;; Customization
;; ---------------------------------------------------------------------------

(defgroup adascript nil
  "Support for Adascript (.ady) source files."
  :group 'languages
  :prefix "adascript-")

(defcustom adascript-python-command "python3.13"
  "Python interpreter (3.13+) used to launch the Adascript language server."
  :type 'string
  :group 'adascript)

(defcustom adascript-server-path
  ;; Default: adascript_ls.py lives one directory above this file (LSP/).
  (expand-file-name
   "../adascript_ls.py"
   (file-name-directory (or load-file-name buffer-file-name default-directory)))
  "Absolute path to adascript_ls.py."
  :type 'file
  :group 'adascript)

(defcustom adascript-lsp-mode-auto-enable nil
  "If non-nil, automatically call `lsp-deferred' in every adascript-mode buffer.
Requires the lsp-mode package.  For eglot (built-in), run M-x eglot manually
or add `(add-hook \\='adascript-mode-hook \\=#\\='eglot-ensure)' to your init."
  :type 'boolean
  :group 'adascript)

;; ---------------------------------------------------------------------------
;; Font-lock
;; ---------------------------------------------------------------------------

(defface adascript-type-name-face
  '((t :inherit font-lock-type-face))
  "Face for Adascript type names (the NAME in `type NAME is ...')."
  :group 'adascript)

(defface adascript-tick-type-face
  '((t :inherit font-lock-type-face))
  "Face for the type part of a tick attribute (Color in `Color\\'First')."
  :group 'adascript)

(defface adascript-tick-attr-face
  '((t :inherit font-lock-builtin-face))
  "Face for the attribute part of a tick attribute (First in `Color\\'First')."
  :group 'adascript)

(defconst adascript--type-decl-re
  (rx bol (* space)
      (group "type") (+ space)
      (group (+ (any word "_")))
      (* (any space "[" "]" "," word "_"))   ; optional discriminant params
      (+ space)
      (group (or "is" "=")) (+ space)
      (group (or "enum" "record" "tuple")))
  "Regex matching a type declaration header: type NAME ... is|= enum|record|tuple.")

(defconst adascript--tick-re
  ;; NAME'ATTR where NAME and ATTR are word sequences.
  ;; Placed after strings so 'hello' is not mis-matched.
  (rx (group (+ (any word "_"))) "'" (group (+ (any word "_"))))
  "Regex matching tick attributes: Name'Attr.")

(defconst adascript--ada-keyword-re
  (rx symbol-start
      (or "when" "is" "enum" "record" "tuple" "type")
      symbol-end)
  "Adascript-specific keywords not already highlighted by python-mode.")

(defvar adascript-font-lock-keywords
  `(
    ;; 1. Type declarations: type NAME is|= enum|record|tuple
    (,adascript--type-decl-re
     (1 font-lock-keyword-face)          ; "type"
     (2 'adascript-type-name-face)       ; NAME
     (3 font-lock-keyword-face)          ; "is" / "="
     (4 font-lock-keyword-face))         ; "enum" / "record" / "tuple"

    ;; 2. Tick attributes: Color'First
    (,adascript--tick-re
     (1 'adascript-tick-type-face)       ; Color
     (2 'adascript-tick-attr-face))      ; First

    ;; 3. Ada/Adascript keywords
    (,adascript--ada-keyword-re . font-lock-keyword-face))
  "Additional font-lock keywords for `adascript-mode'.")

;; ---------------------------------------------------------------------------
;; Syntax table tweak
;; ---------------------------------------------------------------------------

(defvar adascript-mode-syntax-table
  (let ((st (copy-syntax-table python-mode-syntax-table)))
    ;; Treat ' as punctuation so that  Color'First  is not lexed as a string.
    ;; Single-char string literals like 'x' still work via the font-lock
    ;; string rules, but multi-word tick sequences won't be confused.
    (modify-syntax-entry ?\' "." st)
    st)
  "Syntax table for `adascript-mode'.")

;; ---------------------------------------------------------------------------
;; Mode definition
;; ---------------------------------------------------------------------------

;;;###autoload
(define-derived-mode adascript-mode python-mode "Adascript"
  "Major mode for Adascript (.ady) files.

Adascript is a statically-typed, Ada-inspired superset of Python 3.
Every valid Python 3 file is valid Adascript.  Extensions include:

  type Color is enum RED, GREEN, BLUE       -- inline enum
  type Color is enum:                       -- block enum
      RED
      GREEN
      BLUE

  type Point is record:                     -- record (struct)
      x: float
      y: float

  n: int = Color'Pos(Color'First)           -- tick attributes

Indentation, string syntax, and comment handling are inherited from
`python-mode'.  This mode adds highlighting for the constructs above
and wires the Adascript language server via eglot or lsp-mode.

\\{adascript-mode-map}"
  :syntax-table adascript-mode-syntax-table
  ;; Prepend so Adascript rules take priority over Python's.
  (font-lock-add-keywords nil adascript-font-lock-keywords 'set)
  (setq-local comment-start "# ")
  (setq-local comment-start-skip "#+\\s-*")
  ;; Reuse Python's indentation engine (offside rule).
  (setq-local indent-tabs-mode nil)
  (when adascript-lsp-mode-auto-enable
    (when (fboundp 'lsp-deferred)
      (lsp-deferred))))

;; ---------------------------------------------------------------------------
;; Helper: server contact list (used by both eglot and lsp-mode)
;; ---------------------------------------------------------------------------

(defun adascript--server-contact ()
  "Return the server command as a list suitable for eglot or lsp-mode."
  (list adascript-python-command adascript-server-path))

;; ---------------------------------------------------------------------------
;; eglot integration (Emacs 29+ built-in)
;; ---------------------------------------------------------------------------

(with-eval-after-load 'eglot
  ;; Register using a function so adascript-python-command / server-path are
  ;; read at server-start time, not at load time.
  (add-to-list 'eglot-server-programs
               (cons 'adascript-mode #'adascript--server-contact)))

;; ---------------------------------------------------------------------------
;; lsp-mode integration (third-party package, opt-in)
;; ---------------------------------------------------------------------------

(with-eval-after-load 'lsp-mode
  (lsp-register-client
   (make-lsp-client
    :new-connection (lsp-stdio-connection #'adascript--server-contact)
    :major-modes '(adascript-mode)
    :language-id "adascript"
    :server-id 'adascript-ls
    :add-on? nil)))

;; ---------------------------------------------------------------------------
;; File association
;; ---------------------------------------------------------------------------

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.ady\\'" . adascript-mode))

(provide 'adascript-mode)
;;; adascript-mode.el ends here
