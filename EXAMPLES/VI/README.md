# vi.ady, vi_core.ady, vi_curses.ady, vi_raw.ady, vi_py.ady

A tiny vi-like editor in Adascript. It began as a translation of
[vip](https://github.com/maksimKorzh/vip), the 125-line Python editor, to idiomatic
Adascript, and has gone its own way since: it is held to what a vi does, not to what
vip does.

    ady2nim c vi.ady && ./vi file.txt          # on illwill, a pure-Nim terminal library
                         ./vi -raw file.txt    # on the raw terminal, by hand
    ady2py vi_py.ady > vi_py.py && python3 vi_py.py file.txt     # on curses (Python)

## How it is put together

`vi_core.ady` is the editor and the high layer: the `Editor`, what a key does, how the
text looks, and `edit(ed, term)`, the loop that runs it. It has no terminal in it. What
it asks of one is the `Terminal` class, which says how a window, a key and a screen are
made; `edit` calls it, so what happens after a key is written once, here:

    start; then, until a quit:  window, fit, draw, key, window again, handle
                                (^S: save and flash its answer; a message: flash it, clear it)
    stop

The terminals are the plumbing, each a subclass of `Terminal`:

| file | class | built with | on |
|------|-------|------------|----|
| `vi_curses.ady` | `IllwillTerminal` | `ady2nim` | illwill |
| `vi_raw.ady` | `RawTerminal` | `ady2nim` | Nim's `terminal` and `termios`, by hand |
| `vi_py.ady` | `CursesTerminal` | `ady2py` | curses |

`Terminal` itself is a terminal with nothing attached -- 80 by 24, nothing to draw, and no
keys, which is the end of the input -- so a subclass overrides what it has.

`vi.ady` is the program for Nim: it imports the two Nim terminals and hands `edit` one of
them, by the `-raw` switch. The choice cannot be made in `vi_core` itself, because the
terminals import it (for the `Editor` they draw and the `Terminal` they are subclasses of).
`vi_py.ady` is its own program for Python, curses being Python's.

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

## What is shown

The text is coloured by language, picked from the file's name: `.ady` and `.py`, `.nim`
and `.sh`; any other file is plain. A scan of each line finds keywords, strings (with
their backslashes, and triple-quoted ones that run over lines), comments (not a `#`
inside a string, nor `$#` in a shell script), numbers (`3.14e2`, `0xFF`) and type names
(`Editor`, `Press_T`: capitalised, with a lower-case letter in them).

| Look | Colour | |
|------|--------|-|
| keyword | yellow | `def`, `let`, `if` |
| string | green | `"s"`, `'c'` |
| comment | bright blue | `# note` |
| number | magenta | `12` |
| type name | cyan | `Editor` |

The line the cursor is on is marked, and so is the cursor's character: a reversed block
in normal mode, an underlined bar in insert and replace mode. `vi_core` does the
looking -- `row_segments(i)` is a screen row cut into stretches that look alike, the
cursor's character a stretch of its own, and `is_current(i)` says whether it is the
cursor's row -- and each terminal says what a look is made of:

- **curses** gives each look a colour pair on the terminal's own background. On 256
  colours the cursor's line gets a dark grey ground to the right edge; on 8 colours it
  is underlined.
- **illwill** sets a colour and a style on its screen buffer before each stretch is
  written; the cursor's line is underlined (illwill has the 8 colours only).
- **raw** writes the escape sequences itself: SGR for the colours, reverse and
  underline, and a 256-colour ground for the cursor's line.

## What the translation does with the Python

- **The keyboard is decoded once.** `decode(ch)` turns a code into a
  `Press_T` (a `Key_T` enum and the character). The codes the terminals name -- the control
  keys and curses' `KEY_*` -- are `Code_T`, an enum with their numbers (8, 10, 13, 27, 127,
  258, ...), and `parse_enum(Code_T, ch)` says whether `ch` is one: if it is, `decode`
  is a `case` over every member (so a member left out is refused); if not, `ch` is a
  printable character or nothing the editor knows. Every
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

`vi_core` knows nothing of any terminal's key codes or of drawing. A terminal says how big
its window is (`window`), reads a key (`key`), draws what the editor shows (`draw`: `scroll`,
`row_segments`, `status`, and `cursor_y` and `cursor_x`) and flashes a message (`flash`);
`edit` does the rest. Nim has no curses, so `vi_curses.ady` uses
[illwill](https://github.com/johnnovak/illwill) (`TO_NIM/STDLIB/illwill.nim`, one file in
pure Nim, `nimport illwill`), which does the two hard parts (reading the arrow keys is one of them):

- **Keys.** `getKeyWithTimeout` reads a key without blocking, tells a lone ESC from an
  arrow key's escape sequence, and returns an enum whose ordinal is the ASCII code for
  the printable keys, so `decode(ord(key))` is all the editor needs; arrows and function
  keys have ordinals of their own, which `decode` takes as `OTHER`.
- **The screen.** The rows are written into a `TerminalBuffer` and `display` sends only
  what changed since the last frame.

What is left in `vi_curses.ady` is small: illwill leaves flow control on, so the terminal
would take `^S` and `^Q`; a three-line `termios` call turns `IXON` off. The bundled
copy has one change from illwill 0.4.1: a modified arrow (`ESC [ 1 ; 5 D`) is read
whole, where illwill left `5D` behind to be typed. There is no resize event: the window
size is read again at every key. At the end of the input (stdin not a terminal) illwill
reports no key, so the editor waits; run it on a terminal.

## vi_raw.ady: the same editor without a terminal library

`vi_raw.ady` is the earlier Nim terminal, kept because it shows what a terminal has to
do when nothing does it for you, with only Nim's `terminal` module and `termios`
(`vi -raw`):

- **Raw mode.** No echo, no line editing, no signals, and `^S` and `^Q` reach the
  program instead of stopping the terminal.
- **A lone ESC against an arrow key.** An arrow key is an escape sequence
  (`ESC O A`, or `ESC [ A`); `read_code` tells it from an ESC by whether more bytes
  follow within 25 ms (curses' `ESCDELAY`), and swallows it. The keys are read with
  `read(2)` rather than `getch`, which reads through C's buffer and would hide the
  rest of the sequence from the 25 ms wait.
- **Drawing.** One frame per key, built as a string and written in one go; the window
  size is read again at every key, as there is no resize event.

It is longer than `vi_curses.ady` and passes the same key scripts; it reads an arrow key's escape sequence itself, as it does a lone ESC.

Slices and list edits in `vi_core` are written so that they mean the same on both
backends: a slice past the end raises on Nim, so `tail` and `splice` are the only way
the editor takes part of a string, and the list edits (`insert_line`, `delete_lines`)
build the new list instead of calling `insert` (whose arguments Nim takes the other
way round) or assigning to a slice.

## Tests

`test_vi.py` runs key scripts in a pty -- 69 on curses, 72 on the Nim terminals (`vi` and
`vi -raw`), which are also held to the `ESC [` forms of the arrows, Home and End -- and
compares the file each leaves. Undo is one step per change, as in vi; typing in replace mode past the end of a
line makes the line grow. Nine screen checks per terminal read what it writes to its
pty: colour before a keyword, a string, a number, a type name and a comment, the
cursor's character reversed, the cursor's line marked, and no colour in a `.txt`.
`EXAMPLES/test_vi_highlight.ady` tests the scan itself, on both backends: one letter for
each character, so a line and its colours read side by side. `EXAMPLES/test_vi_loop.ady`
tests `edit` on a `Terminal` that is a script of keys, with no pty, on both backends: the
window asked for twice a key, a message flashed once and cleared, ^S's "Saved", a quit
that says nothing, and the terminal with nothing attached.

    python3 test_vi.py vi_py.py     # or ./vi, or ./vi -raw
    make test-vi                    # from the top: builds vi, runs all three (about 20 s)
