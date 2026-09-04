;;; git1-vc.el --- use C-x v ... on a git1-tracked file  -*- lexical-binding: t; -*-

;; Author: Adascript project
;; Keywords: vc, tools
;; Package-Requires: ((emacs "27.1"))

;;; Commentary:

;; `EXAMPLES/git1.ady' gives each tracked file its own private git repo,
;; stored as ".git1/<file>" and reached through GIT_DIR and
;; GIT_WORK_TREE.  Emacs finds repositories by filename instead --
;; `vc-git-root' is literally (vc-find-root file ".git") -- so a git1 file
;; looks unversioned to VC, and `C-x v ...' does nothing useful with it.
;;
;; Worse, `vc-create-branch' and `vc-switch-branch' work off
;; `default-directory' rather than off the file's registration.  In a
;; directory that is itself inside an ordinary git repo, `C-x v b c' will
;; happily create the branch in that enclosing repo.
;;
;; `git1-vc-focus' writes a one-line ".git" pointer next to the visited
;; file (".git1/notes.txt" being the repo of "notes.txt"):
;;
;;     gitdir: .git1/notes.txt
;;
;; git1 already sets core.worktree to the file's directory, so both git and
;; VC then resolve to that file's private history.  The whole VC interface
;; works from that point on -- `C-x v b c' (create branch), `C-x v b s'
;; (switch branch), `C-x v b l', `C-x v v', `C-x v =', `C-x v l'.
;; `git1-vc-unfocus' removes the pointer again.
;;
;; Two things to know:
;;
;;   * Only one file per directory can be focused at a time -- there is
;;     only one ".git" name to go around.
;;   * While the pointer exists, an enclosing ordinary repo treats that
;;     directory as an embedded repository: it shows up as untracked and
;;     git stops recursing into it.  Unfocusing restores the previous view.
;;
;; Usage:
;;
;;     (require 'git1-vc)
;;     (global-set-key (kbd "C-c g f") #'git1-vc-focus)
;;     (global-set-key (kbd "C-c g u") #'git1-vc-unfocus)

;;; Code:

(require 'vc)

(defgroup git1 nil
  "Emacs support for git1, per-file git repositories."
  :group 'vc
  :prefix "git1-")

(defcustom git1-container ".git1"
  "Directory under which git1 keeps the per-file repositories."
  :type 'string
  :group 'git1)

(defun git1--gitdir (file)
  "Return FILE's git1 repository, or nil if FILE is not tracked by git1.

A repository is named after its file, so \"notes.txt\" is tracked in
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

(defun git1--pointer-p (dotgit)
  "Return non-nil if DOTGIT is a .git pointer into a git1 container."
  (and (file-regular-p dotgit)
       (with-temp-buffer
         (insert-file-contents dotgit)
         (string-match-p (concat "\\`gitdir: .*" (regexp-quote git1-container))
                         (buffer-string)))))

(defun git1--buffer-file ()
  "Return the visited file, or signal an error."
  (or buffer-file-name (user-error "This buffer is not visiting a file")))

;;;###autoload
(defun git1-vc-focus ()
  "Point VC at the git1 repository of the file in this buffer.

Writes a .git pointer file in the file's directory, after which
`C-x v ...' -- branch creation and switching included -- operates on
that file's private history.  Use `git1-vc-unfocus' to undo it."
  (interactive)
  (let* ((file   (git1--buffer-file))
         (dir    (file-name-directory file))
         (repo   (or (git1--gitdir file)
                     (user-error "%s is not tracked by git1"
                                 (file-name-nondirectory file))))
         (dotgit (expand-file-name ".git" dir)))
    (cond
     ((git1--pointer-p dotgit)
      (delete-file dotgit))
     ((file-exists-p dotgit)
      (user-error "%s already exists -- refusing to overwrite it" dotgit)))
    (write-region (format "gitdir: %s\n" (file-relative-name repo dir))
                  nil dotgit nil 'quiet)
    (vc-refresh-state)
    (message "VC follows %s" (file-relative-name repo dir))))

;;;###autoload
(defun git1-vc-unfocus ()
  "Remove the .git pointer written by `git1-vc-focus'."
  (interactive)
  (let* ((dir    (file-name-directory (git1--buffer-file)))
         (dotgit (expand-file-name ".git" dir)))
    (unless (git1--pointer-p dotgit)
      (user-error "%s is not a git1 pointer" dotgit))
    (delete-file dotgit)
    (vc-refresh-state)
    (message "VC no longer follows this file's git1 repository")))

(provide 'git1-vc)

;;; git1-vc.el ends here
