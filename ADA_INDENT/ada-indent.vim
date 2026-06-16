" ada-indent.vim --- Ada indentation via the external ada_indent program
"
" This is the Vim/Neovim counterpart of ada-indent.el.  It wires the same
" `ada_indent' binary into Vim's indentation machinery so that Ada buffers are
" indented by ada_indent rather than by Vim's built-in heuristics.
"
" Installation:
"   Drop this file on your 'runtimepath', e.g.
"       ~/.vim/plugin/ada-indent.vim          (Vim)
"       ~/.config/nvim/plugin/ada-indent.vim  (Neovim)
"   or :source it from your vimrc / init.vim.
"
" What you get (parity with ada-indent.el):
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
" Aggressive indent (optional, off by default):
"   Set  let g:ada_indent_aggressive = 1  before a buffer is opened, or run
"   :AdaIndentToggleAggressive in a buffer, to reindent the current line after
"   every change (continuous indent-as-you-type), mirroring aggressive-indent
"   in the Emacs integration.
"
" Prerequisites:
"   The `ada_indent' binary must be on $PATH (compile it from ada_indent.ady
"   once with py2nim, then symlink the result onto your PATH, e.g.
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

if !exists('g:ada_indent_aggressive')
  " When 1, reindent the current line after every change (see header).
  let g:ada_indent_aggressive = 0
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
          \ . ' --state ' . shellescape(b:ada_indent_state)
          \ . ' --emit-state'
  else
    let l:cmd = g:ada_indent_program . ' --emit-state'
  endif

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
" Aggressive indent (optional): reindent the current line after every change
" ---------------------------------------------------------------------------

function! s:ReindentCurrentLine() abort
  let l:line = getline('.')
  if l:line =~# '^\s*$'
    return
  endif
  let l:want = s:RunIndent(line('.'))
  if l:want < 0
    return
  endif
  let l:have = indent('.')
  " Idempotent: bail when already correct.  This guard also stops the setline()
  " below from re-triggering us into an infinite TextChanged loop.
  if l:want == l:have
    return
  endif
  let l:col = col('.')
  let l:body = substitute(l:line, '^\s*', '', '')
  call setline('.', repeat(' ', l:want) . l:body)
  " Keep the cursor over the same character it was on.
  call cursor(line('.'), l:col + (l:want - l:have))
endfunction

function! s:AggressiveEnable() abort
  augroup ada_indent_aggressive_buf
    autocmd! * <buffer>
    autocmd TextChanged,TextChangedI <buffer> call s:ReindentCurrentLine()
  augroup END
  let b:ada_indent_aggressive_on = 1
endfunction

function! s:AggressiveDisable() abort
  augroup ada_indent_aggressive_buf
    autocmd! * <buffer>
  augroup END
  let b:ada_indent_aggressive_on = 0
endfunction

function! s:ToggleAggressive() abort
  if get(b:, 'ada_indent_aggressive_on', 0)
    call s:AggressiveDisable()
    echo 'ada-indent: aggressive mode off'
  else
    call s:AggressiveEnable()
    echo 'ada-indent: aggressive mode on'
  endif
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

  command! -buffer AdaIndentBuffer          call s:IndentBuffer()
  command! -buffer AdaIndentToggleAggressive call s:ToggleAggressive()

  if g:ada_indent_aggressive
    call s:AggressiveEnable()
  endif
endfunction

augroup ada_indent
  autocmd!
  autocmd FileType ada call s:Setup()
augroup END

" ada-indent.vim ends here
