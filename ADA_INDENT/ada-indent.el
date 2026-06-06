;;; ada-indent.el --- Ada indentation via external ada_indent -*- lexical-binding: t -*-

;; Usage:
;;   (require 'ada-indent)          ; from your init.el
;;
;; The mode activates automatically for any buffer in `ada-mode' or
;; `ada-ts-mode'.  It wires up:
;;   RET / C-m  — reindent current line, insert newline, indent new line
;;   TAB        — reindent current line
;;   typing a bare dedenting keyword (end, else, when, …) snaps the
;;                line left on the final character, no extra TAB needed.
;;
;; Aggressive indent (optional):
;;   Set `ada-indent-aggressive' to t (or call M-x ada-indent-toggle-aggressive)
;;   to also enable `aggressive-indent-mode', which continuously reindents the
;;   surrounding lines as you type.  Requires the `aggressive-indent' package.
;;   Efficient on small-to-medium files thanks to the state cache; on very large
;;   files prefer the default RET-only mode plus `format-all' on save.
;;
;; Prerequisites:
;;   - `ada_indent' binary must be on PATH (compile from ada_indent.ady once
;;     with `py2nim ADA_INDENT/ada_indent.ady', then symlink the result onto
;;     your PATH, e.g. ~/.local/bin/ada_indent).
;;
;; Performance:
;;   ada_indent is stateful — it normally replays every line above the cursor.
;;   This file maintains a per-buffer state cache so consecutive edits only
;;   process the lines between the last cache point and the cursor (O(distance)
;;   per keypress instead of O(file size)).  The cache is automatically
;;   invalidated whenever the buffer is edited before the cache point.

;;; Code:

(require 'subr-x)  ; string-blank-p, string-trim-left (Emacs 27+)
(require 'seq)     ; seq-filter, seq-remove

(defgroup ada-indent nil
  "Ada indentation via the external ada_indent program."
  :group 'ada
  :prefix "ada-indent-")

(defcustom ada-indent-program "ada_indent"
  "Name or full path of the ada_indent binary."
  :type 'string
  :group 'ada-indent)

(defcustom ada-indent-aggressive nil
  "If non-nil, enable `aggressive-indent-mode' alongside `ada-indent-mode'.

Aggressive indent reindents the lines around the edit point after every
change, giving a continuous indent-as-you-type effect.  The state cache
keeps each reindent to O(lines since last edit) work rather than O(file
size), so it is practical on small-to-medium files.  On very large files
prefer the default RET-only indentation and `format-all' on save.

Requires the `aggressive-indent' package (MELPA: aggressive-indent).
You can also toggle it interactively with `ada-indent-toggle-aggressive'."
  :type 'boolean
  :group 'ada-indent)

;; ---------------------------------------------------------------------------
;; Per-buffer state cache
;; ---------------------------------------------------------------------------

(defvar-local ada-indent--state nil
  "Serialized Indenter state after line `ada-indent--state-lnum', or nil.
Set by `ada-indent--column' after each successful indent call.")

(defvar-local ada-indent--state-lnum 0
  "Buffer line number after which `ada-indent--state' was captured.")

(defun ada-indent--invalidate-cache (beg _end)
  "Clear the state cache when a buffer change falls before the cache point.

Uses strict `<' rather than `<=': the state captured after line N is derived
from lines 1..N and is unaffected by changes to line N itself (the indenter
strips leading whitespace before analysis, so rewriting a line's indentation
does not change the logical content the state machine saw).  Using `<=' would
cause `indent-line-to' — which changes the current line's whitespace — to
wipe the cache immediately after it is set, making it useless."
  (when ada-indent--state
    (when (< (line-number-at-pos beg) ada-indent--state-lnum)
      (setq-local ada-indent--state     nil
                  ada-indent--state-lnum 0))))

;; ---------------------------------------------------------------------------
;; Core: ask ada_indent what column the current line belongs at
;; ---------------------------------------------------------------------------

(defun ada-indent--column ()
  "Return the column `ada_indent' assigns to the current line.

Pipes the buffer text from the last cache point (or the beginning of the
buffer) through the current line into `ada-indent-program', reads back the
indented output, caches the returned state, and returns the column of the
last output line."
  (let* ((bol   (line-beginning-position))
         (cur   (buffer-substring-no-properties bol (line-end-position)))
         ;; Blank line: probe with a neutral token so ada_indent returns the
         ;; enclosing block's indent rather than column 0.
         (probe (if (string-blank-p cur) "x" cur))
         (lnum  (line-number-at-pos bol))
         ;; Use the cache when it was captured before this line.
         (use-cache (and ada-indent--state
                         (> ada-indent--state-lnum 0)
                         (< ada-indent--state-lnum lnum)))
         (input-start (if use-cache
                          (save-excursion
                            (goto-char (point-min))
                            (forward-line ada-indent--state-lnum)
                            (point))
                        (point-min)))
         (input    (concat (buffer-substring-no-properties input-start bol) probe))
         (cmd-args (if use-cache
                       (list "--state" ada-indent--state "--emit-state")
                     (list "--emit-state")))
         (out      (with-temp-buffer
                     (insert input)
                     (apply #'call-process-region
                            (point-min) (point-max)
                            ada-indent-program
                            t t nil
                            cmd-args)
                     (buffer-string)))
         (all-lines   (split-string out "\n" t))
         (state-lines (seq-filter (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (code-lines  (seq-remove (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (last-state  (car (last state-lines)))
         (last        (car (last code-lines))))
    ;; Cache the state at the current line so the next call can skip ahead.
    (when last-state
      (setq-local ada-indent--state      (substring last-state 8)
                  ada-indent--state-lnum lnum))
    (if last
        (- (length last) (length (string-trim-left last)))
      0)))

;; ---------------------------------------------------------------------------
;; Interactive commands
;; ---------------------------------------------------------------------------

(defun ada-indent-line ()
  "Indent the current line using `ada-indent-program'."
  (interactive)
  (indent-line-to (ada-indent--column)))

(defun ada-indent-region (start end)
  "Reindent every line of the region START..END with `ada-indent-program'.

Installed as `indent-region-function', so `indent-region' (\\[indent-region])
and any command that reindents a region (including reindenting the whole
buffer) go through it.  Runs ada_indent ONCE over the buffer prefix plus the
region — reusing the per-buffer state cache for the prefix when available —
and applies the resulting indentation to each region line.  Lines above the
region are used only to establish the indenter's block state; they are not
modified."
  (let* ((first-line (line-number-at-pos start))
         ;; A line is in the region when its start is before END — the same
         ;; rule the built-in `indent-region' uses, so a region ending at the
         ;; very beginning of a line does not pull that line in.
         (last-line  (save-excursion
                       (goto-char end)
                       (if (and (> end start) (bolp))
                           (1- (line-number-at-pos))
                         (line-number-at-pos))))
         ;; Reuse the cache when its checkpoint sits strictly above the region.
         (use-cache  (and ada-indent--state
                          (> ada-indent--state-lnum 0)
                          (< ada-indent--state-lnum first-line)))
         (start-line (if use-cache (1+ ada-indent--state-lnum) 1))
         (input-beg  (save-excursion
                       (goto-char (point-min))
                       (forward-line (1- start-line))
                       (point)))
         (input-end  (save-excursion
                       (goto-char (point-min))
                       (forward-line last-line)   ; bol of (last-line + 1) = eol incl. \n
                       (point)))
         (input      (buffer-substring-no-properties input-beg input-end))
         (cmd-args   (if use-cache
                         (list "--state" ada-indent--state "--emit-state")
                       (list "--emit-state")))
         (out        (with-temp-buffer
                       (insert input)
                       (apply #'call-process-region
                              (point-min) (point-max)
                              ada-indent-program t t nil cmd-args)
                       (buffer-string)))
         (all-lines   (split-string out "\n"))
         ;; ##STATE: lines are interleaved after each code line; keep code lines
         ;; in order so code-lines[i] is buffer line (start-line + i).
         (code-lines  (seq-remove (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (state-lines (seq-filter (lambda (l) (string-prefix-p "##STATE:" l)) all-lines))
         (last-state  (car (last state-lines))))
    (save-excursion
      (goto-char (point-min))
      (forward-line (1- first-line))
      (let ((ln first-line))
        (while (<= ln last-line)
          (let ((out-line (nth (- ln start-line) code-lines)))
            (when out-line
              (indent-line-to (- (length out-line)
                                 (length (string-trim-left out-line))))))
          (forward-line 1)
          (setq ln (1+ ln)))))
    ;; Advance the cache to the last line we processed.
    (when last-state
      (setq-local ada-indent--state      (substring last-state 8)
                  ada-indent--state-lnum last-line))))

(defun ada-indent-buffer ()
  "Reindent the entire buffer with `ada-indent-program'."
  (interactive)
  (ada-indent-region (point-min) (point-max)))

(defun ada-indent-line-or-region ()
  "Reindent the active region, or the current line when no region is active.
Bound to TAB so selecting text and pressing TAB reindents the whole
selection in one pass."
  (interactive)
  (if (use-region-p)
      (ada-indent-region (region-beginning) (region-end))
    (ada-indent-line)))

(defun ada-newline-and-indent ()
  "Reindent the current line, insert a newline, then indent the new line.

`indent-line-to' internally calls `back-to-indentation', which moves point
to the start of the line's text.  The `save-excursion' keeps point at the
original position so `newline' splits the line correctly (after the cursor,
not at the line start)."
  (interactive)
  (save-excursion
    (indent-line-to (ada-indent--column)))  ; fix the line being left
  (newline)
  (indent-line-to (ada-indent--column)))    ; indent the new line

(defun ada-indent--post-insert ()
  "Snap the current line left when it becomes a bare dedenting keyword.
Runs via `post-self-insert-hook' so the correction fires on the last
character of the keyword with no extra keypress."
  (let ((content (string-trim
                  (buffer-substring-no-properties
                   (line-beginning-position) (line-end-position)))))
    (when (member content
                  '("end" "else" "elsif" "when" "exception"
                    "begin" "is" "then" "private" "limited"
                    "record" "loop" "do" "select"))
      (save-excursion
        (indent-line-to (ada-indent--column))))))

;; ---------------------------------------------------------------------------
;; Aggressive-indent integration
;; ---------------------------------------------------------------------------

(defvar-local ada-indent--owns-aggressive nil
  "Non-nil when `ada-indent-mode' itself activated `aggressive-indent-mode'.
Used to avoid disabling aggressive-indent in buffers where the user enabled
it independently of ada-indent.")

(defun ada-indent--aggressive-enable ()
  "Enable `aggressive-indent-mode' for the current Ada buffer.
Configures it to skip blank lines (which ada_indent always emits at column
0 so there is nothing to correct) and to use our `ada-indent-line' as the
single-line indenter."
  (unless (featurep 'aggressive-indent)
    (require 'aggressive-indent nil t))
  (if (not (featurep 'aggressive-indent))
      (message "ada-indent: aggressive-indent package not found; \
install it from MELPA with M-x package-install RET aggressive-indent RET")
    ;; Skip blank lines — ada_indent returns column 0 for them; agressive-indent
    ;; would otherwise loop trying to "fix" a line that is already correct.
    (add-to-list (make-local-variable 'aggressive-indent-dont-indent-if)
                 '(string-blank-p
                   (buffer-substring-no-properties
                    (line-beginning-position) (line-end-position))))
    (setq-local ada-indent--owns-aggressive t)
    (aggressive-indent-mode 1)))

(defun ada-indent--aggressive-disable ()
  "Disable `aggressive-indent-mode' if `ada-indent-mode' was the one that enabled it."
  (when ada-indent--owns-aggressive
    (setq-local ada-indent--owns-aggressive nil)
    (when (bound-and-true-p aggressive-indent-mode)
      (aggressive-indent-mode -1))))

;;;###autoload
(defun ada-indent-toggle-aggressive ()
  "Toggle `aggressive-indent-mode' for the current Ada buffer.

When turned on, Emacs reindents the lines around every edit as you type.
When turned off, indentation fires only on RET and TAB.

Requires the `aggressive-indent' package (MELPA)."
  (interactive)
  (if (bound-and-true-p aggressive-indent-mode)
      (progn
        (ada-indent--aggressive-disable)
        (message "ada-indent: aggressive mode off"))
    (ada-indent--aggressive-enable)
    (message "ada-indent: aggressive mode on")))

;; ---------------------------------------------------------------------------
;; Minor mode
;; ---------------------------------------------------------------------------

(defvar ada-indent-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "RET")      #'ada-newline-and-indent)
    (define-key map (kbd "<return>") #'ada-newline-and-indent)
    (define-key map (kbd "C-m")      #'ada-newline-and-indent)
    (define-key map (kbd "TAB")      #'ada-indent-line-or-region)
    (define-key map (kbd "C-M-\\")   #'ada-indent-region)
    map)
  "Keymap for `ada-indent-mode'.
Minor-mode keymaps outrank the major-mode local map, so these bindings
win over whatever ada-mode or electric-indent-mode places on RET/TAB.")

;;;###autoload
(define-minor-mode ada-indent-mode
  "Use the external `ada_indent' program for Ada buffer indentation.
Binds RET to reindent-then-newline-then-indent and TAB to reindent-line.
Disables `electric-indent-local-mode' to avoid conflicts."
  :lighter " AdaInd"
  :keymap ada-indent-mode-map
  (if ada-indent-mode
      (progn
        (setq-local indent-line-function   #'ada-indent-line)
        ;; Route `indent-region' (and whole-buffer reindents) through the
        ;; batched single-process path instead of line-by-line.
        (setq-local indent-region-function #'ada-indent-region)
        ;; electric-indent reindents the line just left and moves point back,
        ;; which fights our RET handler.  Turn it off for this buffer.
        (electric-indent-local-mode -1)
        (add-hook 'post-self-insert-hook   #'ada-indent--post-insert       nil t)
        (add-hook 'before-change-functions #'ada-indent--invalidate-cache  nil t)
        (when ada-indent-aggressive
          (ada-indent--aggressive-enable)))
    (ada-indent--aggressive-disable)
    (kill-local-variable 'indent-line-function)
    (kill-local-variable 'indent-region-function)
    (remove-hook 'post-self-insert-hook   #'ada-indent--post-insert          t)
    (remove-hook 'before-change-functions #'ada-indent--invalidate-cache     t)))

;; ---------------------------------------------------------------------------
;; Auto-enable
;; ---------------------------------------------------------------------------

;;;###autoload
(defun ada-indent--maybe-enable ()
  "Enable `ada-indent-mode' in the current buffer if `ada-indent-program' is found."
  (when (executable-find ada-indent-program)
    (ada-indent-mode 1)))

;;;###autoload (add-hook 'ada-mode-hook    #'ada-indent--maybe-enable)
;;;###autoload (add-hook 'ada-ts-mode-hook #'ada-indent--maybe-enable)

(add-hook 'ada-mode-hook    #'ada-indent--maybe-enable)
(add-hook 'ada-ts-mode-hook #'ada-indent--maybe-enable)

;; Retroactively enable in any Ada buffer already open when this file loads.
(dolist (buf (buffer-list))
  (with-current-buffer buf
    (when (derived-mode-p 'ada-mode 'ada-ts-mode)
      (ada-indent--maybe-enable))))

(provide 'ada-indent)
;;; ada-indent.el ends here
