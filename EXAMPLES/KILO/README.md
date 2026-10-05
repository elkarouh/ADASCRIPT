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

### Why two files, and not one

Kilo is one file because C makes it cheap to be one, and because it is a demonstration of how
small an editor can be. Here the file is split along a line of abstraction, so that each layer
knows only what is below it:

- **`kilo_editor.ady` is the model and the logic**: rows, colouring, the cursor, what each key does,
  find, undo, and the frame it hands over to be drawn. It imports nothing, and does not know
  there is a terminal, a keyboard, `termios` or an escape sequence.
- **`kilo.ady` is the edge**: raw mode, reading bytes and escape sequences, writing the frame as
  VT100 escapes. It knows nothing about rows or colouring; it turns bytes into key codes and
  a `Frame_T` into bytes.

What that buys, in what is here:

- **The logic is tested without a terminal.** `../test_kilo_editor.ady` types keys into an `Editor` and
  reads the `Frame_T` back, and runs the whole loop (`edit`) on a `Terminal` that is a list of keys: no pty,
  no timing, and it runs in a fraction of a second. The pty test is then left with what only a
  pty can show, the escape sequences.
- **The terminal can be replaced.** `edit` asks for a `Terminal` -- a window size, a key, a clock, a frame to
  draw -- and `RawTerminal` is one of them. `../VI/` has three terminals (illwill, raw, curses) under one editor;
  another here would not touch the editor.
- **The terminal's details stay out of the editor's.** The two kinds of column, the colouring and the history
  are written without a word about timeouts, `poll` or escape sequences, and the escape-sequence reader
  is written without a word about rows.
- **The Nim-only part is small.** `kilo.ady` is the only file that needs `nimport` and `termios`; the
  library is plain Adascript.

The cost is a second file and a small interface to keep (`Code_T`, `Key_T`, `Frame_T`, `Terminal`), which
kilo's global `E` does not have to; for 1300 lines of C that is fair, for a 150-line editor it
would not be.

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

## Size, and what the extra lines buy

| | total lines | code lines |
|---|---|---|
| `kilo.c` | 1308 | 986 |
| `kilo_editor.ady` | 853 | 607 |
| `kilo.ady` | 163 | 114 |
| Adascript, the two together (tests not counted) | 1016 | 721 |

Code lines are the non-blank lines that are not comments: no `//` or `/* */` in the C, no `#` lines
and no `"""` docstrings in Adascript. The Adascript is about a quarter shorter in code lines
(721 against 986) *while doing more*; in total lines the difference is smaller (1016 against 1308),
because the Adascript files carry docstrings and comments that explain the choices.

Added over kilo.c: undo and redo; cut and paste of a row; Home and End; a window that
follows the cursor in render columns, so it is right with tabs; search that lands on the right
character in a row with a tab; colouring of the rows below an edit that changes a `/* */`, including
when rows are inserted or deleted; non-printable characters marked in every file; a failed open or
save reported as a value; and a loop that can be driven by a script, with tests (below) that need no
terminal. What kilo.c has and this does not: the resize signal handler and the cursor-position
fallback for the window size (see Differences).

### Readability, honestly

Clearer than the C:

- **Columns that cannot be mixed up.** In C `cx` is both a place in the characters and a place
  on the screen, and only care keeps them apart; here `Col_T` and `RCol_T` are different types and
  mixing them does not compile.
- **Names for what the numbers mean.** Key codes, colours and modes are enums that `case` checks
  for completeness, where kilo has `#define`s, `int`s, and a `switch` with a `default`.
- **No memory handling.** No `realloc`, `memmove`, `memcpy`, `malloc` or NUL terminators, and no
  `+1` for them; a row is a string and the rows a list. Kilo's buffer arithmetic (`size`, `rsize`, `hl`)
  is the larger part of its row code.
- **Failures are in the types.** `None | !PathFailure_T` says that a write can fail, where C has
  `goto writeerr` and an `errno`.
- **The editor does not know the terminal**, and the frame it hands over is data that tests can look at.
- **Highlighting is a function** of a line and the state it starts in, and a keyword is a set lookup,
  not a loop of `memcmp`.

Not clearer, or worse:

- It is **no shorter where the work is the same**: the colouring scan and the key handling are about
  as long as kilo's, and the scan is as dense as the C.
- **Two files and an interface** to follow (`Code_T`, `Key_T`, `Frame_T`, `Terminal`) where kilo has one
  global; to find what a key does you go through `decode`, `handle` and a method.
- **Slicing is a trap**: a slice past the end of a string raises on Nim, so `clip`, `tail` and `splice`
  stand in for it, and some Adascript quirks (a string concatenation that must go through an
  f-string, a failure value that cannot be used until it is narrowed with an `else`) are worked around
  in the code, and not always obvious to a reader.
- **Snapshots for undo** copy the whole text at each change; that is simple to read and does not
  suit a big file.

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
