# vi.ady, vi_nim.ady

A tiny vi-like editor in Adascript: a translation of
[vip](https://github.com/maksimKorzh/vip), the 125-line Python editor, to idiomatic
Adascript, twice. `vi.ady` uses curses, which is Python's, so it is built with
`ady2py`; `vi_nim.ady` is the same editor for `ady2nim`.

    ady2py vi.ady > vi.py && python3 vi.py file.txt
    ady2nim c vi_nim.ady && ./vi_nim file.txt

Normal mode: `h j k l`, `0 $`, `gg G`, `x`, `r R`, `i a A o O`, `dd yy p`, `u ^R`,
with counts (`3dd`, `12G`). `^S` saves, `^Q` quits.

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

## vi_nim.ady

Nim has no curses. `vi_nim.ady` has the same editing, line for line, and replaces
only the terminal: `std/terminal` for the window size, `termios` for raw mode (no
echo, no line editing, no signals, and `^S` and `^Q` reach the program instead of
stopping the terminal), and the terminal's own escape codes to draw one frame per
key. Two things curses did that it does by hand:

- **A lone ESC against an arrow key.** An arrow key is an escape sequence
  (`ESC O A`, or `ESC [ A`); `read_code` tells it from an ESC by whether more bytes
  follow within 25 ms (curses' `ESCDELAY`), and swallows it. The keys are read with
  `read(2)` rather than `getch`, which reads through C's buffer and would hide the
  rest of the sequence from the 25 ms wait.
- **Resizing.** There is no resize event; the window size is read again at every key.

Slices and list edits are written so that they mean the same on both backends: a
slice past the end raises on Nim, so `tail`, `clip` and `splice` are the only way
the editor takes part of a string, and the list edits (`insert_line`, `delete_lines`)
build the new list instead of calling `insert` (whose arguments Nim takes the other
way round) or assigning to a slice. `diff vi.ady vi_nim.ady` shows only the terminal.

## Differences from vip

- vip records its undo snapshot before a `dd`, `yy` or `R` takes effect, so one `u`
  undoes nothing and `xxxuu` undoes all three `x`. Here every change is one step, as
  in vi.
- Typing in replace mode (`R`) past the end of the line makes vip raise an
  `IndexError` and exit without saving; here the line grows.

`test_vi.py` runs key scripts in a pty; 21 of its 25 cases give byte-identical files
to vip, and the four that differ (one `R` past the end of a line, and three undo and
redo ones) are marked. It also types arrow keys, which vip ignores in insert mode
only by accident; the Nim editor is held to both escape-sequence forms, and curses
to the one it knows.

    python3 test_vi.py vi.py        # or ./vi_nim
