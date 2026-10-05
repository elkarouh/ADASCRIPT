# kilo.ady, kilo_editor.ady

[Kilo](https://github.com/antirez/kilo), Salvatore Sanfilippo's "very simple editor in less
than 1-kilo lines of code", translated from C to Adascript. Kilo is one file of 1300 lines
with a global struct; this is not a line-by-line copy but the same editor in the language's
own terms, following the layout of the vi example next door (`../VI/`): a library with the
editor and the loop that runs it, and a small program that is the terminal.

    ady2nim c kilo.ady && ./kilo file.c

Kilo's license (BSD 2-clause) and its author are in the header of `kilo_editor.ady`, which is the
translation. `kilo.ady` is the plumbing around it.

## How it is put together

`kilo_editor.ady` imports nothing and has no terminal in it:

| kilo.c | here |
|--------|------|
| `HL_*` defines | `Look_T`, an enum |
| `KEY_ACTION`, the numbers `editorReadKey` returns | `Code_T` (what a terminal sends), `decode`, `Key_T` (what it means), `Press_T` |
| `struct erow` | `Row`: `chars`, `render`, `hl`, and whether it starts and ends inside a `/* */` |
| `editorUpdateSyntax` | `highlight(render, syntax, in_comment) -> Scan_T` -- a function of a line and the state it starts in |
| `struct editorSyntax`, `HLDB` | `Syntax_T`, `C_SYNTAX`, `syntax_of(filename)` |
| `struct editorConfig E` | the `Editor` class |
| `editorFind`, a loop that reads keys itself | a mode of the editor (`finding`): the loop is `edit`'s, whatever the mode |
| `editorRefreshScreen`, escapes written as it goes | `frame_of` makes a `Frame_T` -- the rows cut into stretches that look alike, the status bar, the message, the cursor -- and the terminal draws it |
| raw mode, escape sequences, `ioctl` | `Terminal`, a class with nothing attached; `kilo.ady` has `RawTerminal` |

`kilo.ady` is the Nim terminal, on `termios` and the VT100 escapes kilo writes; like
`../VI/vi_raw.ady` it reads the keys with `read(2)` and tells a lone ESC from an arrow key by
waiting for more bytes (100 ms, kilo's `VTIME`).

### What the language is used for

- **Distinct types.** Kilo's `cx` is a place in the row's characters and also a place on the
  screen; with a tab in the row they differ, and kilo's search and scrolling are wrong there.
  `Col_T` (a place in `chars`) and `RCol_T` (a place in `render`) are `distinct int`, so mixing them
  does not compile; `Row.render_col` and `Row.col_of` are the only way from one to the other.
  The match of a search is an `RCol_T`, the cursor it moves to a `Col_T`.
- **Enums.** The colours, the keys, the codes a terminal sends (an enum with values, which
  `parse_enum` turns a code into), and `case` over them, checked for completeness.
- **Failures as values.** Opening a file is `None | !PathFailure_T` and so is writing it, where kilo
  calls `perror` and exits; a file that is not there is a new one, as in kilo.
- **Records, classes, a virtual class.** `Frame_T`, `Seg_T`, `Scan_T`; `Row`, `Editor`; `Terminal`
  and its subclasses, which is also how the tests give the loop a script of keys.
- **Sets.** The keywords are two `{}str`; kilo compares the text with each keyword in turn, and a
  keyword there is a whole word, so a set lookup does the same.

## Keys

Arrows, Home, End, PageUp, PageDown, Backspace, Del; `^Z` undoes and `^Y` redoes; `^K` cuts the
row under the cursor and `^U` pastes it above the cursor's row; `^S` saves; `^Q` quits (a file with unsaved
changes wants it four times, and any other key starts the count again); `^F` searches: type the
text, the arrows go to the next or previous match, ENTER stays on it, ESC goes back to where the
search began. Anything else that is a character is typed, TAB and the control characters too (a
character that is not printable is shown reversed, `^A` as an `A`).

## Differences from kilo

Kept, on purpose: one match to a row in a search, which starts from the top of the file and puts
the match on the top row; a cursor that can sit on the row after the last; kilo's colours; Del that
deletes backwards.

Added, on top of kilo (which has no undo and no cut or paste):

- **Undo and redo**, `^Z` and `^Y`, one step to a change; a run of typed characters is one step, and
  any key that changes nothing (an arrow) ends the run. Undo past a save makes the file modified again,
  and back to what is written makes it unmodified. The history is a list of snapshots of the text, as in
  `../VI/vi_editor.ady`; a new change drops what could have been redone.
- **Cut and paste of a row**, `^K` and `^U`: one buffer, replaced by each cut (not added to, as in
  nano). The key bindings are nano's; `^C` and `^L` do nothing, as in kilo, and `^Z` is undo, not
  suspend, because raw mode takes the signal keys.

Changed:

- **Home and End move** to the start and the end of the row. In kilo the keys are read and then
  typed into the text as characters 1005 and 1006.
- **Tabs stop at multiples of 8.** Kilo's rendering stops at 7 mod 8, which is a bug, and the cursor
  arithmetic follows it.
- **The window follows the cursor in `scroll`**, once, after the key; kilo moves `rowoff` and `coloff`
  in each of the places that can move the cursor. PageUp and PageDown still go to the top
  or the bottom of the screen and then a window's worth, but not below the row after the last.
- **A `//` in a `/* */` comment does not end the block** (kilo marks the rest of the row as a
  line comment and the next row starts outside the block). Rows below an edit are coloured again
  for as long as the comment they start in changes, including when a row is inserted or deleted.
- **A backslash at the very end of a string** is not read past the end of the row.
- **Non-printable characters are marked in every file**, not only in one with a language.
- The welcome line is centred as text (kilo counts its escape sequences), and says "version".
- `decltype` for kilo's `deltype`; `auto` is a keyword only (kilo lists it as a type as well, which
  never wins).
- **Left out:** the `SIGWINCH` handler -- the window is measured again before every key -- and the
  query-the-terminal fallback for the window size (`ESC [ 6 n`), which Nim's `terminalSize` covers.
  `^C` and `^L` do nothing, as in kilo; kilo lists `^D` and `^U` but gives them no action either, so
  they are typed like any other control character.
- The alternate screen is used, so the shell's screen comes back on quit.

## Tests

- `../test_kilo_editor.ady` -- the logic, with no terminal: rows and tabs, 17 lines of colouring (one
  letter to a character) and a block comment that follows an edit, typing, moving and paging, undo, redo, cut and paste, find,
  save and quit, the frame handed to a terminal (status bar, welcome, message fading, scrolling),
  the key codes, and `edit` on a terminal that is a script of keys. A part of `make test`.
- `test_kilo.py` -- 47 key scripts typed into the program in a pty (the file it saves is compared
  with what a kilo writes for the same keys) and 11 checks of what it draws: the colours, the status
  bar, the help message, the match of a search, the welcome, and no colour in a `.txt`.

        python3 test_kilo.py ./kilo
        make test-kilo                 # from the top: builds both, runs both (about 15 s)
