# vi.ady

A tiny vi-like editor in Adascript: a translation of
[vip](https://github.com/maksimKorzh/vip), the 125-line Python editor, to idiomatic
Adascript. curses is Python's, so it is built with `ady2py`.

    ady2py vi.ady > vi.py && python3 vi.py file.txt

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

## Differences from vip

- vip records its undo snapshot before a `dd`, `yy` or `R` takes effect, so one `u`
  undoes nothing and `xxxuu` undoes all three `x`. Here every change is one step, as
  in vi.
- Typing in replace mode (`R`) past the end of the line makes vip raise an
  `IndexError` and exit without saving; here the line grows.

`test_vi.py` runs key scripts in a pty; 21 of its 25 cases give byte-identical files
to vip, and the four that differ (one `R` past the end of a line, and three undo and
redo ones) are marked.

    python3 test_vi.py vi.py
