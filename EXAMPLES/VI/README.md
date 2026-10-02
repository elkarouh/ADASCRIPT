# vi_py.ady, vi_nim.ady, vi_core.ady

A tiny vi-like editor in Adascript. It began as a translation of
[vip](https://github.com/maksimKorzh/vip), the 125-line Python editor, to idiomatic
Adascript, and has gone its own way since: it is held to what a vi does, not to what
vip does. The editor is `vi_core.ady`, with no terminal in it; `vi_py.ady` shows it on
curses (Python, built with `ady2py`) and `vi_nim.ady` on illwill, a pure-Nim terminal
library (built with `ady2nim`). Both `import` `vi_core`: ady2nim compiles it as a module, ady2py
brings it into the file it writes.

    ady2py vi_py.ady > vi_py.py && python3 vi_py.py file.txt
    ady2nim c vi_nim.ady && ./vi_nim file.txt        # on illwill
    ady2nim c vi_raw.ady && ./vi_raw file.txt        # on the raw terminal

Normal mode: `h j k l` or the arrow keys, `0 $` or Home and End, `gg G`, PageUp and
PageDown, `x`, `r R`, `i a A o O`, `dd yy p`, `u ^R`, `/` with `n` and `N`, and counts
(`3dd`, `12G`). `^S` saves, `^Q` quits.

The arrow, Home, End and Page keys move the cursor in normal, insert and replace mode
(a modified arrow, as in `ESC [ 1 ; 5 D`, is a plain one); in the middle of `d`, `y`,
`g` or `r` they cancel, as any other key does. Home and End are the start and the end
of the line, and a page is the window less a line.

`/` opens a line on the status row for the text to search for; ENTER searches forward
from the cursor, wrapping round the end of the file, and moves to the match. `n` goes
to the next match and `N` to the one before; ENTER on an empty `/` line searches for the
last text again. The text is matched as it is typed, not as a pattern. Nothing found, or
no text yet, says so on the status row. `:` opens a command line on the status row, as `/` does:
`ESC` drops it, and backspace edits it, then leaves it when it is empty:

| Command | Does |
|---------|------|
| `:w` | write the file |
| `:w NAME` | write the text to NAME, and go on editing the same file |
| `:q` | quit; refused while there are changes not written (the message says so) |
| `:q!` | quit, whatever there is |
| `:wq`, `:x` | write, then quit (not if the write failed) |
| `:N` | go to line N (the last line, for a number past the end) |
| `:$` | go to the last line |

Anything else says `Not an editor command`. A command leaves what to tell the user in
`message` and may set `quitting`, which the terminal looks at after each key.

## What the translation does with the Python

- **The keyboard is decoded once.** `decode(ch)` turns a curses code into a
  `Press_T` (a `Key_T` enum and the character), with a `case` over the codes. Every
  mode is then a `case` over what was pressed; the editor never compares a code.
  vip has one `elif ch == ord('i')` chain, and modes as one-letter strings
  (`mod in 'irRdoOyd'`).
- **Modes are an enum, `case`-ed on.** `case self.mode`, and for the second key of
  `dd`, `yy` and `gg`, `case (self.mode, press.text)`.
- **No exceptions for what is expected.** vip wraps each file operation and each cell
  access in `try/except`. Here a missing file is `Path.read_lines()`'s
  `!PathFailure_T`, which means a new buffer; a save that fails says so on the status
  line instead of crashing the editor; a count is `parse_int(...)`, 1 when there is
  none.
- **Lines are strings**, not lists of character codes, so an edit is a slice and
  there is no `deepcopy`: the undo history is a list of `Snapshot_T` records.

## What a terminal does

`vi_core` knows nothing of any terminal's key codes or of drawing. A terminal tells it the
window size (`fit`), asks what to show (`scroll`, `row_text`, `status`, and `row` and
`col` for the cursor), decodes what was typed (`decode`) and hands it over
(`handle`), and shows what `save` answers. `vi_py.ady` does that with curses in 51
lines (the editor is 312). Nim has no curses, so `vi_nim.ady` uses
[illwill](https://github.com/johnnovak/illwill) (`TO_NIM/STDLIB/illwill.nim`, one file in
pure Nim, `nimport illwill`), which does the two hard parts (reading the arrow keys is one of them):

- **Keys.** `getKeyWithTimeout` reads a key without blocking, tells a lone ESC from an
  arrow key's escape sequence, and returns an enum whose ordinal is the ASCII code for
  the printable keys, so `decode(ord(key))` is all the editor needs; arrows and function
  keys have ordinals of their own, which `decode` takes as `OTHER`.
- **The screen.** The rows are written into a `TerminalBuffer` and `display` sends only
  what changed since the last frame.

What is left in `vi_nim.ady` is small: illwill leaves flow control on, so the terminal
would take `^S` and `^Q`; a three-line `termios` call turns `IXON` off. The bundled
copy has one change from illwill 0.4.1: a modified arrow (`ESC [ 1 ; 5 D`) is read
whole, where illwill left `5D` behind to be typed. There is no resize event: the window
size is read again at every key. At the end of the input (stdin not a terminal) illwill
reports no key, so the editor waits; run it on a terminal.

## vi_raw.ady: the same editor without a terminal library

`vi_raw.ady` is the earlier Nim front end, kept because it shows what a terminal has to
do when nothing does it for you, with only Nim's `terminal` module and `termios`:

- **Raw mode.** No echo, no line editing, no signals, and `^S` and `^Q` reach the
  program instead of stopping the terminal.
- **A lone ESC against an arrow key.** An arrow key is an escape sequence
  (`ESC O A`, or `ESC [ A`); `read_code` tells it from an ESC by whether more bytes
  follow within 25 ms (curses' `ESCDELAY`), and swallows it. The keys are read with
  `read(2)` rather than `getch`, which reads through C's buffer and would hide the
  rest of the sequence from the 25 ms wait.
- **Drawing.** One frame per key, built as a string and written in one go; the window
  size is read again at every key, as there is no resize event.

It is longer than `vi_nim.ady` and passes the same key scripts; it reads an arrow key's escape sequence itself, as it does a lone ESC.

Slices and list edits in `vi_core` are written so that they mean the same on both
backends: a slice past the end raises on Nim, so `tail` and `splice` are the only way
the editor takes part of a string, and the list edits (`insert_line`, `delete_lines`)
build the new list instead of calling `insert` (whose arguments Nim takes the other
way round) or assigning to a slice.

## Tests

`test_vi.py` runs key scripts in a pty -- 69 on curses, 72 on the Nim editors, which are
also held to the `ESC [` forms of the arrows, Home and End -- and compares the file each
leaves. Undo is one step per change, as in vi; typing in replace mode past the end of a
line makes the line grow.

    python3 test_vi.py vi_py.py     # or ./vi_nim
    make test-vi                    # from the top: builds vi_nim and vi_raw, runs all three (about 20 s)
