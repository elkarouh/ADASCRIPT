# vi_py.ady, vi_nim.ady, vi_core.ady

A tiny vi-like editor in Adascript: a translation of
[vip](https://github.com/maksimKorzh/vip), the 125-line Python editor, to idiomatic
Adascript. The editor is `vi_core.ady`, with no terminal in it; `vi_py.ady` shows it on
curses (Python, built with `ady2py`) and `vi_nim.ady` on illwill, a pure-Nim terminal
library (built with `ady2nim`). Both `import` `vi_core`: ady2nim compiles it as a module, ady2py
brings it into the file it writes.

    ady2py vi_py.ady > vi_py.py && python3 vi_py.py file.txt
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

## What a terminal does

`vi_core` knows nothing of any terminal's key codes or of drawing. A terminal tells it the
window size (`fit`), asks what to show (`scroll`, `row_text`, `status`, and `row` and
`col` for the cursor), decodes what was typed (`decode`) and hands it over
(`handle`), and shows what `save` answers. `vi_py.ady` does that with curses in 51
lines (the editor is 312). Nim has no curses, so `vi_nim.ady` uses
[illwill](https://github.com/johnnovak/illwill) (`TO_NIM/STDLIB/illwill.nim`, one file in
pure Nim, `nimport illwill`), which does the two hard parts:

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

Slices and list edits in `vi_core` are written so that they mean the same on both
backends: a slice past the end raises on Nim, so `tail` and `splice` are the only way
the editor takes part of a string, and the list edits (`insert_line`, `delete_lines`)
build the new list instead of calling `insert` (whose arguments Nim takes the other
way round) or assigning to a slice.

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

    python3 test_vi.py vi_py.py     # or ./vi_nim
    make test-vi                    # from the top: builds vi_nim, runs both (about 10 s)
