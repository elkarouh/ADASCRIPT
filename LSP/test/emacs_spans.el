;;; emacs_spans.el --- adascript-mode's regex literals, for the editor checks
;;
;; emacs --batch -l emacs_spans.el FILE...
;;
;; Prints FILE:LINE: TEXT for every span adascript-mode fences as a regex,
;; and FILE:LINE: STRING LEAK for every line that starts inside a string
;; whose opening quote is on an earlier line and is not a triple quote -- a
;; quote that opened one and never closed.  Needs nim-mode, which
;; adascript-mode derives from, installed as a package (MELPA).

(require 'package)
(package-initialize)
(load (expand-file-name "../emacs/adascript-mode.el"
                        (file-name-directory load-file-name)))

(defun emacs-spans--fence-p (pos)
  (and (eq (char-after pos) ?/)
       (equal (get-text-property pos 'syntax-table) (string-to-syntax "|"))))

(dolist (file command-line-args-left)
  (with-current-buffer (find-file-noselect file)
    (adascript-mode)
    (syntax-propertize (point-max))
    ;; the regex literals: pairs of fences on slashes
    (goto-char (point-min))
    (let ((open nil))
      (while (not (eobp))
        (when (emacs-spans--fence-p (point))
          (if (not open)
              (setq open (point))
            (princ (format "%s:%d: %s%s\n" file (line-number-at-pos open)
                           (if (eq (char-before open) ?s) "s" "")
                           (buffer-substring-no-properties
                            open (save-excursion (forward-char 1)
                                                 (skip-chars-forward "imsxg")
                                                 (point)))))
            (setq open nil)))
        (forward-char 1)))
    ;; the lines a runaway string swallowed
    (goto-char (point-min))
    (while (not (eobp))
      (let ((ppss (syntax-ppss (point))))
        (when (and (nth 3 ppss)
                   (not (save-excursion (goto-char (nth 8 ppss))
                                        (looking-at-p "\"\"\"\\|'''"))))
          (princ (format "%s:%d: STRING LEAK\n" file (line-number-at-pos)))))
      (forward-line 1))
    (kill-buffer)))
(setq command-line-args-left nil)
