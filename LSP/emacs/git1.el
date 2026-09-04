;;; git1.el --- VC integration for git1 single-file repos  -*- lexical-binding: t; -*-

;; A file tracked by git1 lives beside its own repo, ".git1/<name>", and there
;; is no .git anywhere.  Emacs finds repositories by walking up the tree looking
;; for .git, so it finds nothing.  Worse, if the directory happens to sit inside
;; an ordinary repo, Emacs finds *that* one, which knows nothing about the file.
;;
;; The fix has to be per-file rather than per-directory: teach `vc-git' that
;; the file's own directory is a root, and point the resulting git calls at
;; that file's repo.
;;
;; Usage:
;;
;;   (require 'git1)
;;   (git1-global-mode 1)
;;   (add-hook 'find-file-hook #'git1-maybe-enable)
;;
;; Known limitation: `vc-dir' is not supported.  It is inherently a per-
;; directory view, and a directory holding several git1 files has no single
;; repository to show.  Use `git1 each status -s' from a shell instead.

;;; Code:

(require 'vc)
(require 'vc-git)

(declare-function magit-status-setup-buffer "magit-status" (&optional directory))
(defvar magit-git-global-arguments)

(defgroup git1 nil
  "Single-file version control with git1."
  :group 'vc)

(defcustom git1-container ".git1"
  "Name of the container directory that holds all git1 repos in a directory."
  :type 'string
  :group 'git1)

(defcustom git1-program "git1"
  "Name of the git1 executable."
  :type 'string
  :group 'git1)

;;; Locating the repo

(defun git1-repo-for-file (file)
  "Return the absolute git1 repo directory for FILE, or nil if untracked.
A repo is named after its file, so \"notes.txt\" is tracked in
\".git1/notes.txt\"."
  (when file
    (let* ((file (expand-file-name file))
           (repo (expand-file-name
                  (concat git1-container "/" (file-name-nondirectory file))
                  (file-name-directory file))))
      ;; A directory alone is not enough: confirm it is a repository.
      (and (file-directory-p repo)
           (file-exists-p (expand-file-name "HEAD" repo))
           repo))))

(defun git1--files-in (args)
  "Return the first existing file name found among ARGS."
  (catch 'hit
    (dolist (arg args)
      (cond
       ((and (stringp arg) (git1-repo-for-file arg)) (throw 'hit arg))
       ((consp arg)
        (dolist (item arg)
          (when (and (stringp item) (git1-repo-for-file item))
            (throw 'hit item))))))
    nil))

(defun git1--context-file ()
  "The file the command in progress concerns, or nil.

`buffer-file-name' when the current buffer visits one.  vc-git runs some
of its commands inside a temporary buffer (`vc-git-branches') or from the
minibuffer (revision completion), and neither visits a file, so fall back
to what the window is showing."
  (or (buffer-file-name)
      (let ((win (or (minibuffer-selected-window) (selected-window))))
        (and win (buffer-file-name (window-buffer win))))))

(defun git1--current-file-in (dir)
  "Return the file in hand if git1 tracks it and it lives in DIR.

Some VC operations name a directory rather than a file -- branch creation
and switching among them, since a branch belongs to a repository, not to
one of its files.  A directory can hold several git1 files, so the one
meant is the one whose buffer the command was invoked from.  DIR nil
matches any directory."
  (let ((file (git1--context-file)))
    (and file
         (git1-repo-for-file file)
         (or (null dir)
             (equal (file-name-as-directory (expand-file-name dir))
                    (file-name-directory (expand-file-name file))))
         file)))

;;; Teaching vc-git about these repos

(defun git1--root-advice (orig file)
  "Return FILE's own directory as its VC root when git1 tracks it.
Falls back to ORIG, so ordinary repos are unaffected."
  (cond
   ((git1-repo-for-file file)
    (file-name-directory (expand-file-name file)))
   ;; A directory-scoped command, asked from a buffer visiting a git1 file
   ;; in that directory: that file's repo is the one it means.
   ((and (file-directory-p file) (git1--current-file-in file))
    (file-name-as-directory (expand-file-name file)))
   (t (funcall orig file))))

;; Note: setting GIT_DIR in `process-environment' does not work.  Both
;; `vc-git--call' and `vc-git-command' prepend the bare string "GIT_DIR" to
;; `process-environment', which *removes* the variable -- vc-git scrubs it
;; deliberately so that it always relies on directory discovery.  So the repo
;; has to be passed as a command-line argument instead, which we splice in at
;; those same two choke points.

(defvar git1--repo nil
  "Absolute git1 repo directory for the call in progress, or nil.")

(defvar git1--worktree nil
  "Absolute work tree for the call in progress, or nil.")

(defun git1--env-advice (orig &rest args)
  "Note the git1 repo belonging to ARGS, then run ORIG."
  (let* ((file (git1--files-in args))
         (repo (and file (git1-repo-for-file file))))
    (if (not repo)
        (apply orig args)
      (let ((git1--repo (directory-file-name repo))
            (git1--worktree (directory-file-name
                             (file-name-directory (expand-file-name file)))))
        (apply orig args)))))

(defun git1--global-flags ()
  "Git global flags for the repo in progress, or nil."
  (when git1--repo
    (list (concat "--git-dir=" git1--repo)
          (concat "--work-tree=" git1--worktree))))

(defun git1--flags-for-file (file)
  "Compute git1 flags for FILE, or nil if not a git1 file."
  (when-let* ((repo (git1-repo-for-file file)))
    (list (concat "--git-dir=" (directory-file-name repo))
          (concat "--work-tree="
                  (directory-file-name
                   (file-name-directory (expand-file-name file)))))))

(defvar git1--call-has-infile
  (>= emacs-major-version 32)
  "Non-nil if `vc-git--call' takes an INFILE argument before BUFFER.
Emacs 32 changed the signature from (buffer command &rest args)
to (infile buffer command &rest args).")

(defun git1--call-advice (orig &rest args)
  "Splice the git1 repo flags into `vc-git--call'."
  (let* ((has-infile git1--call-has-infile)
         (pre  (if has-infile (list (nth 0 args) (nth 1 args)) (list (nth 0 args))))
         (cmd  (nth (if has-infile 2 1) args))
         (rest (nthcdr (if has-infile 3 2) args))
         (flags (or (git1--global-flags)
                    (git1--flags-for-file
                     (or (git1--files-in rest)
                         (git1--current-file-in default-directory))))))
    (if flags
        (apply orig (append pre (list (car flags))
                            (cdr flags) (list cmd) rest))
      (apply orig args))))

(defun git1--command-advice (orig buffer okstatus file-or-list &rest flags)
  "Splice the git1 repo flags into `vc-git-command'."
  (let ((extra (or (git1--global-flags)
                   (git1--flags-for-file
                    (or (if (consp file-or-list)
                            (car file-or-list)
                          file-or-list)
                        (git1--current-file-in default-directory))))))
    (apply orig buffer okstatus file-or-list
           (append extra flags))))

(defun git1--async-advice (orig buffer root command &rest args)
  "Splice the git1 repo flags into `vc-do-async-command'.

`vc-git-merge-branch' runs git through this rather than through either of
the two choke points above, so without this a merge would run with no
repository at all.  Only fires inside a command that has already resolved
a git1 repo, and only for git itself."
  (if (and git1--repo (equal command vc-git-program))
      (apply orig buffer root command (append (git1--global-flags) args))
    (apply orig buffer root command args)))

(defun git1--dir-command-advice (orig &rest args)
  "Resolve the git1 repo for a command that names a directory, then run ORIG.

Branch creation, switching, branch logs and merges all act on a repository
rather than on a file, and reach git through several layers -- some of
which run in a buffer of their own, where the file in hand can no longer be
seen.  Resolving the repo once, here at the entry point, and binding it for
the duration covers all of them."
  (let* ((file (git1--current-file-in nil))
         (repo (and file (git1-repo-for-file file))))
    (if (not repo)
        (apply orig args)
      (let ((git1--repo (directory-file-name repo))
            (git1--worktree (directory-file-name
                             (file-name-directory (expand-file-name file)))))
        (apply orig args)))))

(defconst git1--dir-commands
  '(vc-create-tag                       ; C-x v b c, C-x v s
    vc-retrieve-tag                     ; C-x v b s, C-x v r
    vc-print-branch-log                 ; C-x v b l
    vc-merge)                           ; C-x v m
  "VC commands that act on a repository rather than on one of its files.")

(defconst git1--advised-functions
  '(vc-git-registered
    vc-git-state
    vc-git-working-revision
    vc-git-mode-line-string
    vc-git-checkin
    vc-git-find-revision
    vc-git-checkout
    vc-git-revert
    vc-git-print-log
    vc-git-log-outgoing
    vc-git-log-incoming
    vc-git-diff
    vc-git-annotate-command
    vc-git-previous-revision
    vc-git-next-revision
    vc-git-register
    vc-git-delete-file
    vc-git-rename-file)
  "vc-git entry points that take a file and therefore need the environment.")

;;;###autoload
(define-minor-mode git1-global-mode
  "Make Emacs's git support work on files tracked by git1."
  :global t
  :group 'git1
  (if git1-global-mode
      (progn
        (advice-add 'vc-git-root :around #'git1--root-advice)
        (advice-add 'vc-git--call :around #'git1--call-advice)
        (advice-add 'vc-git-command :around #'git1--command-advice)
        (advice-add 'vc-do-async-command :around #'git1--async-advice)
        (dolist (fn git1--advised-functions)
          (when (fboundp fn)
            (advice-add fn :around #'git1--env-advice)))
        (dolist (fn git1--dir-commands)
          (when (fboundp fn)
            (advice-add fn :around #'git1--dir-command-advice))))
    (advice-remove 'vc-git-root #'git1--root-advice)
    (advice-remove 'vc-git--call #'git1--call-advice)
    (advice-remove 'vc-git-command #'git1--command-advice)
    (advice-remove 'vc-do-async-command #'git1--async-advice)
    (dolist (fn git1--advised-functions)
      (when (fboundp fn)
        (advice-remove fn #'git1--env-advice)))
    (dolist (fn git1--dir-commands)
      (when (fboundp fn)
        (advice-remove fn #'git1--dir-command-advice)))))

;;; A buffer-local mode, mostly for the mode line and keys

(defvar git1-mode-prefix-map
  (let ((map (make-sparse-keymap "git1")))
    (define-key map "c" #'git1-commit)
    (define-key map "d" #'vc-diff)
    (define-key map "l" #'vc-print-log)
    (define-key map "b" #'vc-annotate)
    (define-key map "s" #'git1-magit-status)
    (define-key map "a" #'git1-adopt)
    map)
  "Prefix keymap for git1 commands, bound under C-c g.")

(defvar git1-mode-map (make-sparse-keymap)
  "Keymap for `git1-mode'.  Empty — keys live in `mode-specific-map'.")

;;;###autoload
(define-minor-mode git1-mode
  "Minor mode for a buffer visiting a file tracked by git1."
  :lighter " git1"
  :keymap git1-mode-map
  :group 'git1
  (when git1-mode
    ;; git1-mode without git1-global-mode is a trap: the keybindings work,
    ;; but none of the vc-git calls get redirected, so git falls back to
    ;; ordinary directory discovery, finds no repo, and vc.el offers to
    ;; register the file under a fresh one -- the "which backend? create a
    ;; repository?" prompts.  Guarantee the advice is always the precondition.
    (unless git1-global-mode
      (git1-global-mode 1)
      (message "git1-global-mode was off; git1-mode turned it on"))
    ;; Also guard against the unrelated but similarly-shaped bug where the
    ;; buffer was visited before the file became tracked: vc.el caches
    ;; "unregistered" the first time it looks, and never re-checks on its
    ;; own once cached.
    (vc-refresh-state)
    (define-key mode-specific-map "g" git1-mode-prefix-map)))

(defun git1-commit ()
  "Commit the current file to its git1 repo."
  (interactive)
  (unless (git1-repo-for-file buffer-file-name)
    (user-error "This file is not tracked by git1"))
  (unless git1-global-mode
    (git1-global-mode 1)
    (vc-refresh-state)
    (message "git1-global-mode was off; turned it on"))
  (when (buffer-modified-p) (save-buffer))
  (vc-next-action nil))

(defun git1-adopt (branch)
  "Make BRANCH the current branch of this file's repo, wholesale.

For trying an idea on a branch and keeping the winner.  Nothing is
combined, so nothing can conflict: the current branch simply moves onto
BRANCH, and what it held before is reachable only through the reflog.
Offers to delete the branches that lost.

Runs `git1 adopt', so the command line and this do the same thing."
  (interactive
   (list (completing-read "Adopt branch: "
                          (or (cdr (vc-git-branches))
                              (user-error "This repo has only one branch"))
                          nil t)))
  (let* ((file (or buffer-file-name (user-error "Not visiting a file")))
         (base (file-name-nondirectory file))
         (default-directory (file-name-directory (expand-file-name file)))
         (current (car (vc-git-branches)))
         (losers (remove branch (cdr (vc-git-branches))))
         prune)
    (unless (git1-repo-for-file file)
      (user-error "%s is not tracked by git1" base))
    (when (buffer-modified-p)
      (if (y-or-n-p (format "Save %s first? " base))
          (save-buffer)
        (user-error "Aborted")))
    (unless (yes-or-no-p
             (format "Move %s onto %s?  What %s holds now is kept only in the reflog: "
                     current branch current))
      (user-error "Aborted"))
    (setq prune (and losers
                     (y-or-n-p (format "Afterwards delete the branches that lost (%s)? "
                                       (mapconcat #'identity losers ", ")))))
    (with-temp-buffer
      (unless (zerop (call-process git1-program nil t nil "adopt" "-f"
                                   (if prune "--prune" "--no-prune")
                                   base branch))
        (user-error "git1 adopt failed: %s"
                    (string-trim (buffer-string)))))
    (revert-buffer t t t)
    (vc-refresh-state)
    (message "%s now holds %s%s" current branch
             (if prune (format ", %s deleted" (mapconcat #'identity losers ", ")) ""))))

;;;###autoload
(defun git1-maybe-enable ()
  "Turn on `git1-mode' if the visited file is tracked by git1."
  (interactive)
  (when (and buffer-file-name (git1-repo-for-file buffer-file-name))
    (git1-mode 1)))

;;;###autoload
(defun git1-init (file)
  "Start tracking FILE with git1."
  (interactive (list (or buffer-file-name (read-file-name "Track file: "))))
  (let ((default-directory (file-name-directory (expand-file-name file))))
    (unless (zerop (call-process git1-program nil nil nil
                                 "init" (file-name-nondirectory file)))
      (user-error "git1 init failed")))
  (when (equal file buffer-file-name)
    (git1-mode 1)
    (vc-refresh-state)))

;;; Magit

(defun git1-magit-status ()
  "Open a Magit status buffer for the current file's git1 repo."
  (interactive)
  (unless (fboundp 'magit-status-setup-buffer)
    (user-error "Magit is not available"))
  (let* ((file (or buffer-file-name (user-error "Not visiting a file")))
         (repo (or (git1-repo-for-file file)
                   (user-error "This file is not tracked by git1")))
         (dir (file-name-directory (expand-file-name file)))
         (args (list (concat "--git-dir=" (directory-file-name repo))
                     (concat "--work-tree=" (directory-file-name dir))))
         (default-directory dir))
    (funcall 'magit-status-setup-buffer dir)
    ;; Magit re-runs git on every refresh, long after this function returns,
    ;; so the setting has to live in the status buffer itself.
    (setq-local magit-git-global-arguments
                (append (default-value 'magit-git-global-arguments) args))))

(provide 'git1)
;;; git1.el ends here
