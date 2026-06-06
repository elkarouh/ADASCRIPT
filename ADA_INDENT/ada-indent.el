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

;; ---------------------------------------------------------------------------
;; Per-buffer state cache
;; ---------------------------------------------------------------------------

(defvar-local ada-indent--state nil
  "Serialized Indenter state after line `ada-indent--state-lnum', or nil.
Set by `ada-indent--column' after each successful indent call.")

(defvar-local ada-indent--state-lnum 0
  "Buffer line number after which `ada-indent--state' was captured.")

(defun ada-indent--invalidate-cache (beg _end)
  "Clear the state cache when a buffer change falls at or before the cache point."
  (when ada-indent--state
    (when (<= (line-number-at-pos beg) ada-indent--state-lnum)
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
;; Minor mode
;; ---------------------------------------------------------------------------

(defvar ada-indent-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "RET")      #'ada-newline-and-indent)
    (define-key map (kbd "<return>") #'ada-newline-and-indent)
    (define-key map (kbd "C-m")      #'ada-newline-and-indent)
    (define-key map (kbd "TAB")      #'ada-indent-line)
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
        (setq-local indent-line-function #'ada-indent-line)
        ;; electric-indent reindents the line just left and moves point back,
        ;; which fights our RET handler.  Turn it off for this buffer.
        (electric-indent-local-mode -1)
        (add-hook 'post-self-insert-hook   #'ada-indent--post-insert       nil t)
        (add-hook 'before-change-functions #'ada-indent--invalidate-cache  nil t))
    (kill-local-variable 'indent-line-function)
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
