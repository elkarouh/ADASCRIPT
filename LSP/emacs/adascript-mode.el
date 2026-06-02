;;; adascript-mode.el --- Major mode for Adascript (.ady) files -*- lexical-binding: t; -*-

;; Author: Adascript Project
;; Version: 0.2.0
;; Keywords: languages ada nim
;; Package-Requires: ((emacs "28.1") (nim-mode "0.4.1"))
;; URL: https://github.com/elkarouh/adascript

;;; Commentary:

;; Major mode for Adascript, an Ada-inspired statically-typed superset of Python 3.
;;
;; Derived from `nim-mode', this mode adds:
;;   - Syntax highlighting for type declarations, tick attributes, and Ada keywords
;;   - Single-quote strings and f-strings (Python-style, not native to Nim)
;;   - eglot integration (Emacs 29+ built-in LSP client) — zero extra packages
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
;;     (adascript-python-command "python3")
;;     (adascript-server-path    "/path/to/ADASCRIPT/LSP/adascript_ls.py"))
;;
;; eglot (Emacs 29+): open any .ady file, then M-x eglot.
;;   Auto-registers; no extra config needed.
;;
;; lsp-mode: set `adascript-lsp-mode-auto-enable' to t (or add the hook yourself):
;;   (add-hook 'adascript-mode-hook #'lsp-deferred)

;;; Code:

(require 'rx)
(require 'nim-mode)
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

(defface adascript-shell-face
  '((t :inherit font-lock-preprocessor-face))
  "Face for shell: and shellLines: keywords."
  :group 'adascript)

;; --- Regexps ---

(defconst adascript--type-decl-re
  (rx bol (* space)
      (group "type") (+ space)
      (group (+ (any word "_")))
      (* (any space "[" "]" "," word "_"))
      (+ space)
      (group (or "is" "=")) (+ space)
      (group (or "enum" "record" "tuple")))
  "Regex matching a type declaration header: type NAME ... is|= enum|record|tuple.")

(defconst adascript--type-subrange-re
  (rx bol (* space)
      (group "type") (+ space)
      (group (+ (any word "_")))
      (+ space)
      (group "is") (+ space)
      (group (or (seq (+ (any digit "_")) (* space) (or ".." "..<"))
                 (seq (+ (any word "_")) (+ space) "range"))))
  "Regex matching subrange: type SmallInt is 0 .. 255 or type Age is int range 0..100.")

(defconst adascript--tick-re
  (rx (group (+ (any word "_"))) "'" (group (+ (any word "_"))))
  "Regex matching tick attributes: Name'Attr.")

(defconst adascript--var-decl-re
  (rx symbol-start
      (group (or "var" "let" "const"))
      symbol-end)
  "Regex matching variable declaration keywords.")

(defconst adascript--keyword-re
  (rx symbol-start
      (or "when" "others" "is" "enum" "record" "tuple" "type"
          "case" "nimport" "shell" "shellLines"
          "def" "class" "if" "elif" "else" "for" "while"
          "return" "yield" "import" "from" "as" "in"
          "not" "and" "or" "pass" "break" "continue"
          "try" "except" "finally" "raise" "with"
          "assert" "del" "global" "nonlocal" "lambda")
      symbol-end)
  "Adascript keywords (Ada + Python keywords not covered by nim-mode).")

(defconst adascript--shell-keyword-re
  (rx symbol-start
      (group (or "shell" "shellLines"))
      (* space) ":")
  "Regex matching shell: and shellLines: constructs.")

(defconst adascript--range-op-re
  (rx (group (or "..<" "..")))
  "Regex matching range operators.")

(defconst adascript--builtin-type-re
  (rx symbol-start
      (group (or "int" "float" "str" "bool" "Natural" "Positive"
                 "Byte" "Int8" "Int16" "Int32" "Int64"
                 "UInt8" "UInt16" "UInt32" "UInt64"
                 "Float32" "Float64" "char"
                 "list" "dict" "set" "tuple" "None" "True" "False"))
      symbol-end)
  "Regex matching built-in Adascript types and constants.")

(defconst adascript--decorator-re
  (rx bol (* space) (group "@" (+ (any word "_"))))
  "Regex matching decorators.")

(defconst adascript--def-re
  (rx symbol-start
      (group (or "def" "class"))
      (+ space)
      (group (+ (any word "_"))))
  "Regex matching def/class NAME.")

(defconst adascript--builtin-fn-re
  (rx symbol-start
      (group (or "print" "len" "range" "enumerate" "zip" "map" "filter"
                 "sorted" "reversed" "any" "all" "sum" "min" "max"
                 "isinstance" "issubclass" "hasattr" "getattr" "setattr"
                 "input" "open" "type" "super" "property"
                 "staticmethod" "classmethod" "abs" "round"
                 "int" "float" "str" "bool" "list" "dict" "set" "tuple"))
      "(")
  "Regex matching Python builtin function calls.")

(defvar adascript-font-lock-keywords
  `(
    ;; 1. Type declarations: type NAME is|= enum|record|tuple
    (,adascript--type-decl-re
     (1 font-lock-keyword-face)
     (2 'adascript-type-name-face)
     (3 font-lock-keyword-face)
     (4 font-lock-keyword-face))

    ;; 2. Subrange type declarations
    (,adascript--type-subrange-re
     (1 font-lock-keyword-face)
     (2 'adascript-type-name-face)
     (3 font-lock-keyword-face))

    ;; 3. def/class NAME
    (,adascript--def-re
     (1 font-lock-keyword-face)
     (2 font-lock-function-name-face))

    ;; 4. shell:/shellLines: constructs
    (,adascript--shell-keyword-re
     (1 'adascript-shell-face))

    ;; 5. Tick attributes: Color'First
    (,adascript--tick-re
     (1 'adascript-tick-type-face)
     (2 'adascript-tick-attr-face))

    ;; 6. var/let/const declarations
    (,adascript--var-decl-re (1 font-lock-keyword-face))

    ;; 7. Range operators .. and ..<
    (,adascript--range-op-re (1 font-lock-operator-face))

    ;; 8. Built-in types
    (,adascript--builtin-type-re (1 font-lock-type-face))

    ;; 9. Builtin function calls
    (,adascript--builtin-fn-re (1 font-lock-builtin-face))

    ;; 10. Decorators (@virtual etc.)
    (,adascript--decorator-re (1 font-lock-preprocessor-face))

    ;; 11. Keywords
    (,adascript--keyword-re . font-lock-keyword-face))
  "Additional font-lock keywords for `adascript-mode'.")

;; ---------------------------------------------------------------------------
;; Syntax table — extend nim-mode's to support single-quote strings
;; ---------------------------------------------------------------------------

(defvar adascript-mode-syntax-table
  (let ((st (make-syntax-table nim-mode-syntax-table)))
    ;; Make ' a string delimiter so 'hello' is highlighted as a string.
    ;; Tick attributes (Color'First) are handled via syntax-propertize.
    (modify-syntax-entry ?\' "\"" st)
    st)
  "Syntax table for `adascript-mode'.")

;; ---------------------------------------------------------------------------
;; Syntax propertize — handle tick attributes vs. string quotes
;; ---------------------------------------------------------------------------

(defun adascript--syntax-propertize (start end)
  "Mark tick apostrophes (WORD'WORD) as punctuation.
Runs after nim-mode's syntax-propertize.  Skips ticks inside
double-quoted strings (delimiter char 34) to avoid breaking them."
  (goto-char start)
  (while (re-search-forward "\\([[:word:]_]\\)\\('\\)\\([[:word:]_]\\)" end t)
    (let* ((tick-pos (match-beginning 2))
           (state (parse-partial-sexp (point-min) tick-pos))
           (str-delim (nth 3 state)))
      (when (not (eq str-delim 34))
        (put-text-property tick-pos (1+ tick-pos)
                           'syntax-table '(1 . nil)))))
  (syntax-ppss-flush-cache start))

;; ---------------------------------------------------------------------------
;; Mode definition
;; ---------------------------------------------------------------------------

;;;###autoload
(define-derived-mode adascript-mode nim-mode "Adascript"
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

Indentation and comment handling are inherited from `nim-mode'.
This mode adds highlighting for the constructs above plus
single-quote strings, and wires the Adascript language server
via eglot or lsp-mode.

\\{adascript-mode-map}"
  :syntax-table adascript-mode-syntax-table
  ;; Prepend so Adascript rules take priority over Nim's.
  (font-lock-add-keywords nil adascript-font-lock-keywords 'set)
  (setq-local comment-start "# ")
  (setq-local comment-start-skip "#+\\s-*")
  ;; Chain our tick-handling after nim-mode's syntax-propertize.
  (let ((nim-spf syntax-propertize-function))
    (setq-local syntax-propertize-function
                (lambda (start end)
                  (when nim-spf (funcall nim-spf start end))
                  (adascript--syntax-propertize start end))))
  ;; Force re-propertization since nim-mode may have already run
  ;; syntax-propertize during mode setup.
  (setq-local syntax-propertize--done (point-min))
  (syntax-propertize (point-max))
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
