;;; test-ada-indent.el --- Tests for ada-indent.el -*- lexical-binding: t -*-

;; Drives ada-indent.el against the real ada_indent binary, in batch:
;;
;;     ada_indent must be on PATH; then:
;;     emacs -Q --batch -L . -l test-ada-indent.el -f ert-run-tests-batch-and-exit
;;
;; The code under test is the shipped file and the indenter is the real
;; binary, so what passes here is what the mode does.  Expectations are taken
;; from the binary's own output wherever they could otherwise drift from it --
;; the indent width is the indenter's business, not this file's.
;;
;; The counterpart suites are ../vim/test-ada-indent.vim and
;; ../vs_code/test/test_extension.js.  The three check the same properties,
;; because the three share a design and could silently drift apart.

;;; Code:

(require 'ert)
(require 'ada-indent)

(defconst test-ada-indent--messy
  (concat "procedure P is\n"
          "X : Integer;\n"
          "begin\n"
          "if X > 0 then\n"
          "Y := 1;\n"
          "else\n"
          "Y := 2;\n"
          "end if;\n"
          "end P;\n")
  "Unindented input.  Every test starts from this.")

(defun test-ada-indent--via-binary (text)
  "TEXT piped straight through `ada_indent', with no Emacs in the way.
This is the reference: whatever the binary says is the right answer."
  (with-temp-buffer
    (insert text)
    (call-process-region (point-min) (point-max) ada-indent-program t '(t nil) nil)
    (buffer-string)))

(defmacro test-ada-indent--with-buffer (text &rest body)
  "Run BODY in a buffer of TEXT with `ada-indent-mode' on."
  (declare (indent 1))
  `(with-temp-buffer
     (insert ,text)
     (goto-char (point-min))
     (ada-indent-mode 1)
     ,@body))

(defun test-ada-indent--goto-line (n)
  (goto-char (point-min))
  (forward-line (1- n)))

;; ---------------------------------------------------------------------------

(ert-deftest ada-indent-buffer-matches-binary ()
  "Reindenting the buffer agrees with piping the file through the binary."
  (test-ada-indent--with-buffer test-ada-indent--messy
    (ada-indent-buffer)
    (should (equal (buffer-string)
                   (test-ada-indent--via-binary test-ada-indent--messy)))))

(ert-deftest ada-indent-is-a-fixpoint ()
  "Reindenting an already-indented buffer changes nothing."
  (let ((canon (test-ada-indent--via-binary test-ada-indent--messy)))
    (test-ada-indent--with-buffer canon
      (ada-indent-buffer)
      (should (equal (buffer-string) canon)))))

(ert-deftest ada-indent-region-leaves-outside-lines-alone ()
  "A region reindent touches its own lines and no others.
Lines above the region are read to establish the block state; the test
mangles a line below it, which must survive untouched."
  (test-ada-indent--with-buffer test-ada-indent--messy
    ;; Put junk indentation on the last line, outside the region.
    (test-ada-indent--goto-line 9)
    (insert "      ")
    (let ((beg (progn (test-ada-indent--goto-line 4) (point)))
          (end (progn (test-ada-indent--goto-line 6) (point))))
      (ada-indent-region beg end))
    (test-ada-indent--goto-line 9)
    (should (equal (buffer-substring-no-properties
                    (line-beginning-position) (line-end-position))
                   "      end P;"))
    ;; ... while the region itself did get indented.
    (test-ada-indent--goto-line 5)
    (should (> (current-indentation) 0))))

(ert-deftest ada-indent-blank-line-gets-block-body-indent ()
  "A blank line inside a block indents to the body, not to column 0.
Without the neutral-token probe in `ada-indent--column' this returns 0 and
pressing RET drops the cursor to the left margin."
  (test-ada-indent--with-buffer
      (concat "procedure P is\nbegin\n   if X then\n\nend P;\n")
    (test-ada-indent--goto-line 4)
    (let ((blank (ada-indent--column)))
      ;; Deeper than the `if' that encloses it -- the binary picks the width.
      (test-ada-indent--goto-line 3)
      (should (> blank (ada-indent--column))))))

(ert-deftest ada-indent-bare-keyword-snaps-left ()
  "Typing a line that becomes a bare `else' moves it left of the body."
  (test-ada-indent--with-buffer
      (concat "procedure P is\nbegin\n   if X then\n      Y := 1;\nelse\nend P;\n")
    (test-ada-indent--goto-line 5)
    (ada-indent--post-insert)
    (let ((else-col (current-indentation)))
      (test-ada-indent--goto-line 4)
      (ada-indent-line)
      (should (< else-col (current-indentation))))))

(ert-deftest ada-indent-post-insert-ignores-non-keywords ()
  "A line that merely ends in a keyword's last letter is left alone."
  (test-ada-indent--with-buffer
      (concat "procedure P is\nbegin\n   if X then\n          Something_Else\nend P;\n")
    (test-ada-indent--goto-line 4)
    (ada-indent--post-insert)
    (should (= (current-indentation) 10))))

(ert-deftest ada-indent-warm-cache-agrees-with-cold ()
  "The state cache is an optimisation, not a behaviour change.
Indenting the buffer in two passes -- which leaves a warm cache for the
second -- must land in the same place as one cold pass."
  (let ((cold (test-ada-indent--with-buffer test-ada-indent--messy
                (ada-indent-buffer)
                (buffer-string)))
        (warm (test-ada-indent--with-buffer test-ada-indent--messy
                (let ((beg (progn (test-ada-indent--goto-line 1) (point)))
                      (end (progn (test-ada-indent--goto-line 3) (point))))
                  (ada-indent-region beg end))
                (should ada-indent--state)   ; the first pass really cached one
                (ada-indent-region (point-min) (point-max))
                (buffer-string))))
    (should (equal warm cold))))

(ert-deftest ada-indent-cache-survives-reindenting-its-own-line ()
  "Reindenting the cache line through this package keeps the cache.
`ada-indent-line' computes line N's state, caches it, and then rewrites
line N's indentation -- an edit at the cache point.  If that edit cleared
the cache it would be gone the moment it was set.  (The messy input is
unindented, so the rewrite really changes the line.)"
  (test-ada-indent--with-buffer test-ada-indent--messy
    (test-ada-indent--goto-line 5)
    (ada-indent-line)
    (should ada-indent--state)
    (should (= ada-indent--state-lnum 5))))

(ert-deftest ada-indent-cache-drops-on-an-edit-of-its-own-line ()
  "Editing the text of the cache line clears the cache.
The state after line N was computed from line N as it was; typing on it
and then indenting line N+1 must not reuse that state."
  (test-ada-indent--with-buffer test-ada-indent--messy
    (test-ada-indent--goto-line 5)
    (ada-indent-line)
    (should ada-indent--state)
    (end-of-line)
    (insert " -- edited")
    (should-not ada-indent--state)))

(ert-deftest ada-indent-cache-drops-on-an-edit-above-it ()
  "Editing above the cache point clears it, so stale state cannot be reused."
  (test-ada-indent--with-buffer test-ada-indent--messy
    (test-ada-indent--goto-line 7)
    (ada-indent-line)
    (should ada-indent--state)
    (test-ada-indent--goto-line 2)
    (insert "   --  a new line above the cache point\n")
    (should-not ada-indent--state)))

(provide 'test-ada-indent)
;;; test-ada-indent.el ends here
