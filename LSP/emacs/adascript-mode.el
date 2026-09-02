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

(defface adascript-range-op-face
  ;; `font-lock-operator-face' only exists from Emacs 30 onwards; referring to
  ;; it directly in a font-lock keyword raises a void-variable error mid-scan
  ;; on older Emacsen, which aborts fontification for the rest of the buffer.
  `((t :inherit ,(if (facep 'font-lock-operator-face)
                     'font-lock-operator-face
                   'font-lock-builtin-face)))
  "Face for the range operators `..' and `..<'."
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
    (,adascript--range-op-re (1 'adascript-range-op-face))

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
    ;; ' is punctuation by default; `adascript--propertize-quotes' promotes
    ;; the pairs that actually delimit a string.  Doing it the other way
    ;; round — string delimiter by default, demoted for tick attributes —
    ;; means every apostrophe in prose ("the command's output" in a
    ;; docstring) opens a string that never closes.
    (modify-syntax-entry ?\' "." st)
    st)
  "Syntax table for `adascript-mode'.")

;; ---------------------------------------------------------------------------
;; Syntax propertize — handle tick attributes vs. string quotes
;; ---------------------------------------------------------------------------

(defun adascript--escaped-p (pos)
  "Return non-nil if the character at POS is escaped.
Only an odd-length run of backslashes escapes, so the closing quote of
`\"\\\\\\\\\"' — a string holding one backslash — is correctly seen as
unescaped."
  (let ((n 0)
        (p (1- pos)))
    (while (and (>= p (point-min)) (eq (char-after p) ?\\))
      (setq n (1+ n)
            p (1- p)))
    (= 1 (mod n 2))))

(defun adascript--restore-escaped-quotes (start end)
  "Keep `\\\"' from ending a string, and so from inverting the rest of the file.

Nim reads `ident\"...\"' as a generalized raw string literal, in which a
backslash is not an escape but an ordinary character.  For a line like

    f\"commit -am \\\"reworked the intro\\\"\"

nim-mode therefore demotes the backslash to punctuation and marks the
quote after it as the end of the string; from there on code is
highlighted as string and string as code, to the end of the buffer.

Adascript's prefixed strings are Python strings — `f\"...\"', `r\"...\"'
and friends all treat a backslash as an escape — so `\\\"' never ends a
string.  Drop the syntax properties nim-mode put on both characters and
let the syntax table speak.

Must run after nim-mode's own syntax-propertize."
  (goto-char start)
  (while (search-forward "\"" end t)
    (let ((q (1- (point))))
      (when (adascript--escaped-p q)
        (remove-text-properties (1- q) (1+ q) '(syntax-table nil))))))

(defun adascript--quote-closes-on-line (pos)
  "Return the position of the apostrophe that closes a string opened at POS.
The search stops at end of line and honours backslash escapes.  Returning
nil for an unpaired apostrophe is the point of this function: it is what
keeps `the command's output' inside a docstring from opening a string."
  (save-excursion
    (goto-char (1+ pos))
    (let ((eol (line-end-position))
          (found nil))
      (while (and (not found) (< (point) eol))
        (cond ((eq (char-after) ?\\) (forward-char 2))
              ((eq (char-after) ?\') (setq found (point)))
              (t (forward-char 1))))
      found)))

(defun adascript--propertize-quotes (start end)
  "Mark the apostrophes between START and END that really delimit strings.

An apostrophe in Adascript is either a Python string delimiter
\(\\='hello\\=') or Ada's attribute tick (Stage_T\\='First).  The syntax
table calls it punctuation, so only genuine string delimiters need a
property here.  An apostrophe is left as punctuation when it follows a
name or a closing bracket (a tick attribute), when it is already inside
a string or comment, or when it has no partner on the same line.

Runs after nim-mode's syntax-propertize."
  (goto-char start)
  (while (search-forward "'" end t)
    (let ((pos (1- (point))))
      (unless (nth 8 (save-excursion (syntax-ppss pos)))
        (unless (and (> pos (point-min))
                     (or (memq (char-syntax (char-before pos)) '(?w ?_))
                         ;; (1 .. i)'Choice — a tick after a closing bracket.
                         (memq (char-before pos) '(?\) ?\]))))
          (let ((close (adascript--quote-closes-on-line pos)))
            (when close
              (put-text-property pos (1+ pos)
                                 'syntax-table (string-to-syntax "\""))
              (put-text-property close (1+ close)
                                 'syntax-table (string-to-syntax "\""))
              (goto-char (1+ close)))))))))

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
  ;; Run nim-mode's syntax-propertize first, then repair the two things it
  ;; gets wrong for Adascript: escaped quotes and apostrophes.
  (let ((nim-spf syntax-propertize-function))
    (setq-local syntax-propertize-function
                (lambda (start end)
                  (when nim-spf (funcall nim-spf start end))
                  (adascript--restore-escaped-quotes start end)
                  (adascript--propertize-quotes start end))))
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
