" test-ada-indent.vim --- Tests for ada-indent.vim
"
" Drives ada-indent.vim against the real ada_indent binary, in batch:
"
"     ada_indent must be on PATH; then:
"     vim -es -N -u NONE -S test-ada-indent.vim
"
" Exit status is 0 when every assertion holds, 1 otherwise, and the failures
" are printed.  The code under test is the shipped plugin and the indenter is
" the real binary, so what passes here is what the plugin does.  Expectations
" come from the binary's own output wherever they could otherwise drift from
" it -- the indent width is the indenter's business, not this file's.
"
" The counterpart suites are ../emacs/test-ada-indent.el and
" ../vs_code/test/test_extension.js.  The three check the same properties,
" because the three share a design and could silently drift apart.

set nocompatible
source <sfile>:h/ada-indent.vim

let s:messy = [
      \ 'procedure P is',
      \ 'X : Integer;',
      \ 'begin',
      \ 'if X > 0 then',
      \ 'Y := 1;',
      \ 'else',
      \ 'Y := 2;',
      \ 'end if;',
      \ 'end P;',
      \ ]

" The reference answer: the file piped straight through the binary, with no
" Vim in the way.  Whatever it says is right.
function! s:ViaBinary(lines) abort
  return split(system(g:ada_indent_program, join(a:lines, "\n") . "\n"), "\n")
endfunction

" A fresh Ada buffer holding `lines`.  `setf ada` is what fires the plugin's
" FileType autocmd, which is the whole of its per-buffer setup.
function! s:Fresh(lines) abort
  enew!
  setf ada
  call setline(1, a:lines)
  return bufnr('%')
endfunction

function! s:Report(name) abort
  if empty(v:errors)
    call writefile(['PASS  ' . a:name], '/dev/stdout')
  else
    call writefile(['FAIL  ' . a:name] + map(copy(v:errors), '"        " . v:val'),
          \ '/dev/stdout')
    let s:failed += 1
    let v:errors = []
  endif
endfunction

let s:failed = 0

" ---------------------------------------------------------------------------

" The plugin's setup ran and owns the buffer's indentation.
call s:Fresh(s:messy)
call assert_equal('AdaIndentExpr()', &indentexpr)
call assert_equal(2, &shiftwidth)
call assert_equal(1, &expandtab)
call s:Report('FileType ada installs indentexpr and 2-space indent')

" indentkeys carries the dedent keywords, which is what makes a bare `end' or
" `else' snap left as the last letter is typed.  Without these entries the
" feature is silently absent -- nothing else would notice.
call s:Fresh(s:messy)
for s:kw in ['end', 'else', 'elsif', 'when', 'exception', 'begin', 'is',
      \      'then', 'private', 'record', 'loop', 'do', 'select']
  call assert_true(stridx(&indentkeys, '0=' . s:kw) >= 0, 'missing 0=' . s:kw)
endfor
call s:Report('indentkeys covers every dedenting keyword')

" gg=G agrees with piping the file through the binary.
call s:Fresh(s:messy)
normal! gg=G
call assert_equal(s:ViaBinary(s:messy), getline(1, '$'))
call s:Report('gg=G matches the binary')

" Reindenting an already-indented buffer changes nothing.
let s:canon = s:ViaBinary(s:messy)
call s:Fresh(s:canon)
normal! gg=G
call assert_equal(s:canon, getline(1, '$'))
call s:Report('indentation is a fixpoint')

" `=' over a motion touches its own lines and no others.  Lines above are read
" to establish the block state; a mangled line below must survive untouched.
call s:Fresh(s:messy)
call setline(9, '      end P;')
call cursor(4, 1)
normal! =2j
call assert_equal('      end P;', getline(9))
call assert_true(indent(5) > 0, 'line 5 inside the range was not indented')
call s:Report('= over a range leaves outside lines alone')

" Opening a line inside a block indents it to the body.  Vim asks indentexpr
" with the new line still empty, so this is the neutral-token probe in
" s:RunIndent doing its job -- without it the answer is 0 and `o' inside an
" `if' drops the cursor to the left margin.
call s:Fresh(['procedure P is', 'begin', '  if X then', 'end P;'])
call cursor(3, 1)
execute "normal! oY := 1;\<Esc>"
call assert_true(indent(4) > indent(3),
      \ 'opened line got ' . indent(4) . ', not deeper than the if at ' . indent(3))
call s:Report('o inside a block indents to the body')

" Typing a line that becomes a bare `else' snaps it left of the body, on the
" final letter, with no extra keypress.  This goes through `indentkeys' the
" way a person typing does.
call s:Fresh(['procedure P is', 'begin', '  if X then', '    Y := 1;', 'end P;'])
call cursor(4, 1)
execute "normal! oelse\<Esc>"
call assert_true(indent(5) < indent(4),
      \ 'else landed at ' . indent(5) . ', not left of the statement at ' . indent(4))
call s:Report('typing a bare else snaps it left')

" ... and a word that merely ends in a keyword's last letter does not move.
call s:Fresh(['procedure P is', 'begin', '  if X then', '    Y := 1;', 'end P;'])
call cursor(4, 1)
execute "normal! oSomething_Else\<Esc>"
call assert_equal(indent(4), indent(5))
call s:Report('a non-keyword ending in e stays put')

" The state cache is an optimisation, not a behaviour change: indenting in two
" passes -- which leaves a warm cache for the second -- lands where one cold
" pass does.
call s:Fresh(s:messy)
call cursor(1, 1)
normal! =2j
call assert_true(exists('b:ada_indent_state'), 'the first pass cached nothing')
normal! gg=G
let s:warm = getline(1, '$')
call s:Fresh(s:messy)
normal! gg=G
call assert_equal(getline(1, '$'), s:warm)
call s:Report('a warm cache agrees with a cold run')

" A cache captured below the line being indented must not be used for it.
" This is the guard that keeps the cache honest when an edit lands above the
" checkpoint: warm deep, mangle above, reindent, and the answer is still the
" binary's.
call s:Fresh(s:messy)
call cursor(8, 1)
normal! ==
call assert_true(exists('b:ada_indent_state'), 'nothing cached at line 8')
call setline(2, 'Z : Integer;')
normal! gg=G
call assert_equal(s:ViaBinary(getline(1, '$')), getline(1, '$'))
call s:Report('a stale cache is not used for a line above it')

" ---------------------------------------------------------------------------

if s:failed == 0
  call writefile(['', 'all ok'], '/dev/stdout')
  qall!
else
  call writefile(['', s:failed . ' failed'], '/dev/stdout')
  cquit!
endif
