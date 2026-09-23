" ada-indent.vim --- Ada indentation via the external ada_indent program
"
" wires the ada_indent binary into Vim's indentation machinery so that Ada buffers are
" indented by ada_indent rather than by Vim's built-in heuristics.
"
" Installation:
"   Drop this file on your 'runtimepath', e.g.
"       ~/.vim/plugin/ada-indent.vim          (Vim)
"       ~/.config/nvim/plugin/ada-indent.vim  (Neovim)
"   or :source it from your vimrc / init.vim.
"
" What you get:
"   TAB / ==            reindent the current line (Vim's 'indentexpr').
"   =  (operator)       reindent a motion/visual selection, e.g.
"                         gg=G   whole buffer
"                         =ip    current paragraph
"                         V}=    a visual range
"   o / O / <CR>        new lines are auto-indented as you open them.
"   typing a bare       a line that becomes a lone dedenting keyword
"     dedent keyword      (end, else, when, ...) snaps left automatically,
"                         via 'indentkeys' — no extra keypress needed.
"   :AdaIndentBuffer    reindent the whole buffer (convenience for gg=G).
"
" Prerequisites:
"   The `ada_indent' binary must be on $PATH (compile it from ada_indent.ady
"   once with ady2nim, then symlink the result onto your PATH, e.g.
"   ~/.local/bin/ada_indent).  Point g:ada_indent_program at a full path if it
"   is not on $PATH.
"
" Performance:
"   ada_indent is stateful — it normally replays every line above the current
"   one.  This plugin keeps a per-buffer state cache (the binary's --emit-state
"   / --state protocol) so consecutive lines only process the text between the
"   last cache point and the current line.  A full-buffer reindent (gg=G) is
"   therefore O(lines) rather than O(lines^2).  The cache is invalidated
"   automatically when the buffer is edited above the cache point.

if exists('g:loaded_ada_indent')
  finish
endif
let g:loaded_ada_indent = 1

if !exists('g:ada_indent_program')
  " Name or full path of the ada_indent binary.
  let g:ada_indent_program = 'ada_indent'
endif

" ---------------------------------------------------------------------------
" Core: ask ada_indent what column a given line belongs at
" ---------------------------------------------------------------------------

" Return the indent column ada_indent assigns to buffer line {lnum}.
"
" Feeds the text from the last cache point (or line 1) through line {lnum}
" into ada_indent, reading back the indented output and the trailing state
" snapshot.  The snapshot is cached on the buffer so the next call can resume
" instead of replaying from the top.
function! s:RunIndent(lnum) abort
  let l:cur = getline(a:lnum)
  " Blank line: probe with a neutral token so ada_indent returns the enclosing
  " block's indent rather than column 0.
  let l:probe = (l:cur =~# '^\s*$') ? 'x' : l:cur

  " Use the cache only when it was captured strictly above this line.
  let l:use_cache = exists('b:ada_indent_state')
        \ && get(b:, 'ada_indent_state_lnum', 0) > 0
        \ && b:ada_indent_state_lnum < a:lnum
  let l:start = l:use_cache ? b:ada_indent_state_lnum + 1 : 1

  " Verbatim lines start..(lnum-1), then the probe standing in for lnum.
  " getline(a, b) with a > b yields [], so the single-line case is handled.
  let l:lines = (a:lnum > l:start) ? getline(l:start, a:lnum - 1) : []
  call add(l:lines, l:probe)
  let l:input = join(l:lines, "\n")

  if l:use_cache
    let l:cmd = g:ada_indent_program
          \ . ' -q --state ' . shellescape(b:ada_indent_state)
          \ . ' --emit-state'
  else
    let l:cmd = g:ada_indent_program . ' -q --emit-state'
  endif
  " -q: system() merges stderr into the output (shellredir), and a diagnostic
  " line there would be read as an indented source line.

  let l:out = system(l:cmd, l:input)
  if v:shell_error != 0
    " ada_indent unavailable or errored: fall back to keeping the indent.
    return -1
  endif

  " ##STATE: lines are interleaved after each code line; separate them.
  " Drop empty strings (incl. the trailing newline's tail) so l:code[-1] is the
  " real last output line — its leading-space width is the indent we want.
  let l:all    = split(l:out, "\n")
  let l:code   = filter(copy(l:all), 'v:val !~# "^##STATE:"')
  let l:states = filter(copy(l:all), 'v:val =~# "^##STATE:"')

  if !empty(l:states)
    " Snapshot is 'STATE:' + 8 chars of "##STATE:"; strip the prefix.
    let b:ada_indent_state      = strpart(l:states[-1], 8)
    let b:ada_indent_state_lnum = a:lnum
  endif

  if empty(l:code) || empty(l:code[-1])
    return 0
  endif
  " ada_indent emits spaces only, so the leading-whitespace width is the indent.
  return strlen(matchstr(l:code[-1], '^ *'))
endfunction

" 'indentexpr' entry point.  Vim sets v:lnum to the line being indented.
function! AdaIndentExpr() abort
  let l:col = s:RunIndent(v:lnum)
  " -1 tells Vim to leave the indent unchanged (used on error).
  return l:col < 0 ? -1 : l:col
endfunction

" ---------------------------------------------------------------------------
" Per-buffer state cache invalidation
" ---------------------------------------------------------------------------

" Clear the cache when an edit lands above the cache point.
"
" Uses strict '<' like the Emacs version: the state captured after line N is
" derived from lines 1..N and is unaffected by re-whitespacing line N itself
" (ada_indent strips leading whitespace before analysis).  Editing line N's
" *content* and then re-indenting line N re-derives the cache from a full
" replay (the cache is only consulted for lines strictly below it), so this
" stays correct while keeping gg=G's incremental cache intact.
function! s:Invalidate() abort
  if exists('b:ada_indent_state') && get(b:, 'ada_indent_state_lnum', 0) > 0
    if line('.') < b:ada_indent_state_lnum
      unlet b:ada_indent_state
      let b:ada_indent_state_lnum = 0
    endif
  endif
endfunction

" ---------------------------------------------------------------------------
" Whole-buffer / region reindent (the '=' operator already does regions)
" ---------------------------------------------------------------------------

function! s:IndentBuffer() abort
  " Mark gymnastics keep the cursor and view where they were.
  let l:save = winsaveview()
  keepjumps normal! gg=G
  call winrestview(l:save)
endfunction

" ---------------------------------------------------------------------------
" Per-buffer setup, hung off the Ada FileType event
" ---------------------------------------------------------------------------

function! s:Setup() abort
  if !executable(g:ada_indent_program)
    return
  endif

  setlocal indentexpr=AdaIndentExpr()
  " Reindent on: <C-F>, opening lines (o/O), and on a line that becomes a lone
  " dedenting keyword.  '0=word' fires when 'word' is typed at the start of the
  " line — the Vim analogue of the Emacs post-self-insert dedent snap.
  setlocal indentkeys=!^F,o,O,0=end,0=else,0=elsif,0=when,0=exception,0=begin,0=is,0=then,0=private,0=record,0=loop,0=do,0=select
  " ada_indent speaks 2-space, all-spaces indentation.
  setlocal autoindent expandtab shiftwidth=2 softtabstop=2

  let b:ada_indent_state_lnum = 0

  augroup ada_indent_buf
    autocmd! * <buffer>
    autocmd TextChanged,TextChangedI <buffer> call s:Invalidate()
  augroup END

  command! -buffer AdaIndentBuffer call s:IndentBuffer()
endfunction

augroup ada_indent
  autocmd!
  autocmd FileType ada call s:Setup()
augroup END

" ada-indent.vim ends here
