#!/usr/bin/env python3
"""Tests for the vi editor (vi_editor.ady) on each of its terminals -- vi_py.ady (curses,
built with ady2py as vi_py.py), vi_curses.ady (illwill) and vi_raw.ady (Nim's terminal
module and termios): the editor is run in a terminal of its own (a pty), is typed a
script of keys, and the file it wrote is compared with what is wanted.

    python3 test_vi.py PROGRAM

The script ends with ^S and ^Q unless the program has quit by itself (`:wq`, `:q`).
The wanted files are what a vi writes for the same keys.
"""
import fcntl, os, pathlib, pty, re, select, struct, subprocess, sys, tempfile, termios

ESC = "\x1b"
BASE = "one\ntwo\nthree\nfour\nfive\n"

CASES = [
    ('dd,p', 'jddp',
     'one\nthree\ntwo\nfour\nfive\n'),
    ('3dd', '3dd',
     'four\nfive\n'),
    ('Gdd', 'Gdd',
     'one\ntwo\nthree\nfour\n'),
    ('yy,p', 'jyyGp',
     'one\ntwo\nthree\nfour\nfive\ntwo\n'),
    ('2yy,p', '2yyjjp',
     'one\ntwo\nthree\none\ntwo\nfour\nfive\n'),
    ('insert', 'ihello\x1b',
     'helloone\ntwo\nthree\nfour\nfive\n'),
    ('append', 'Aend\x1b',
     'oneend\ntwo\nthree\nfour\nfive\n'),
    ('open', 'onew\x1bOtop\x1b',
     'one\ntop\nnew\ntwo\nthree\nfour\nfive\n'),
    ('replace1', 'rXjrY',
     'Xne\nYwo\nthree\nfour\nfive\n'),
    ('replaceR', 'Rabc\x1bjRxyz\x1b',
     'abc\ntwxyz\nthree\nfour\nfive\n'),
    ('x', 'xxxj$x',
     '\ntw\nthree\nfour\nfive\n'),
    ('3G', '3Gx',
     'one\ntwo\nhree\nfour\nfive\n'),
    ('gg', 'Gggx',
     'ne\ntwo\nthree\nfour\nfive\n'),
    ('undo', 'ddu',
     'one\ntwo\nthree\nfour\nfive\n'),
    ('undo,redo', 'ddu\x12',
     'two\nthree\nfour\nfive\n'),
    ('undo3', 'xxxuu',
     'ne\ntwo\nthree\nfour\nfive\n'),
    ('backspace', 'jia\x7f\x7f\x7f\x1b',
     'ontwo\nthree\nfour\nfive\n'),
    ('enter', 'jA\r2nd\x1b',
     'one\ntwo\n2nd\nthree\nfour\nfive\n'),
    ('bs-join', 'jOab\x7f\x7f\x7f\x1b',
     'one\ntwo\nthree\nfour\nfive\n'),
    ('all-del', '5ddihey\x1b',
     'hey\n'),
    ('dd,u,redo', 'dddduu\x12',
     'two\nthree\nfour\nfive\n'),
    ('motions', 'jjjllhkx',
     'one\ntwo\ntree\nfour\nfive\n'),
    ('dollar', '2$x',
     'one\ntw\nthree\nfour\nfive\n'),
    ('count0', '10Gx',
     'one\ntwo\nthree\nfour\nive\n'),
    ('ctrl-keys', 'i\x01\x02abc\x1b',
     'abcone\ntwo\nthree\nfour\nfive\n'),
]

# A special key arrives as one escape sequence, written at once, which is not an ESC
# followed by typing. A test script writes it as a marker character, so that a typed ESC
# and the letter O can never be taken for the start of one. ESC O A on a terminal in
# application keypad mode, which curses puts it in, and ESC [ A in the other: the Nim
# editors read the terminal themselves, so they are held to both; curses only knows the
# first, and the keypad's forms of Home, End, PageUp and PageDown.
UP, DOWN, RIGHT, LEFT, HOME, END, PGUP, PGDN = (chr(0xE000 + i) for i in range(8))
CSI_UP, CSI_RIGHT, CTRL_LEFT, CSI_HOME, CSI_END, TILDE_HOME, TILDE_END = (chr(0xE010 + i) for i in range(7))
SEQUENCES = {
    UP: ESC + "OA", DOWN: ESC + "OB", RIGHT: ESC + "OC", LEFT: ESC + "OD",
    HOME: ESC + "OH", END: ESC + "OF", PGUP: ESC + "[5~", PGDN: ESC + "[6~",
    CSI_UP: ESC + "[A", CSI_RIGHT: ESC + "[C", CTRL_LEFT: ESC + "[1;5D",
    CSI_HOME: ESC + "[H", CSI_END: ESC + "[F", TILDE_HOME: ESC + "[1~", TILDE_END: ESC + "[4~",
}
ARROWS = [
    ("arrow down", DOWN + "x",
     "one\nwo\nthree\nfour\nfive\n"),
    ("arrow up at top", UP + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("arrow down at end", "G" + DOWN + "x",
     "one\ntwo\nthree\nfour\nive\n"),
    ("arrow right,left", RIGHT + RIGHT + LEFT + "x",
     "oe\ntwo\nthree\nfour\nfive\n"),
    ("arrows in insert", "ia" + UP + "b" + RIGHT + "c" + ESC,
     "abocne\ntwo\nthree\nfour\nfive\n"),
    ("arrows in R", "R" + RIGHT + "X" + ESC,
     "oXe\ntwo\nthree\nfour\nfive\n"),
    ("arrow cancels d", "d" + UP + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("arrow, 3dd", DOWN + "3dd",
     "one\nfive\n"),
]
ARROWS_CSI = [
    ("arrows (CSI)", "ia" + CSI_UP + "b" + CSI_RIGHT + "c" + CTRL_LEFT + "d" + ESC,
     "abodcne\ntwo\nthree\nfour\nfive\n"),
    ("home,end (CSI)", "ll" + CSI_HOME + "x" + CSI_END + "x",
     "n\ntwo\nthree\nfour\nfive\n"),
    ("home,end (~)", "ll" + TILDE_HOME + "x" + TILDE_END + "x",
     "n\ntwo\nthree\nfour\nfive\n"),
]

# Home, End, PageUp and PageDown. A page is the window less a line: 22 lines on the
# 24-row terminal the tests give, so "pages" has a file of 60 lines to go down and up.
BASES = {"pages": "".join(f"l{i}\n" for i in range(60))}
KEYS = [
    ("home", "ll" + HOME + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("end", END + "x",
     "on\ntwo\nthree\nfour\nfive\n"),
    ("home in insert", "ll" + "i" + HOME + "X" + ESC,
     "Xone\ntwo\nthree\nfour\nfive\n"),
    ("end in insert", "i" + END + "X" + ESC,
     "oneX\ntwo\nthree\nfour\nfive\n"),
    ("page down", PGDN + "x",
     "one\ntwo\nthree\nfour\nive\n"),
    ("page up", "G" + PGUP + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("pages", PGDN + PGDN + PGUP + "x",
     "".join(f"l{i}\n" if i != 22 else "22\n" for i in range(60))),
    ("page cancels d", "d" + PGDN + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
]

# Search: / and the pattern, ENTER, then n for the next match and N for the one
# before. The text "one two three four five" has an o in one, two and four.
SEARCH = [
    ("/two", "/two\rx",
     "one\nwo\nthree\nfour\nfive\n"),
    ("/hree", "/hree\rx",
     "one\ntwo\ntree\nfour\nfive\n"),
    ("/ wraps", "G/one\rx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("n", "/o\rnx",
     "one\ntwo\nthree\nfur\nfive\n"),
    ("n wraps", "/o\rnnx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("N", "/o\rnNx",
     "one\ntw\nthree\nfour\nfive\n"),
    ("N wraps", "/o\rNNx",
     "one\ntwo\nthree\nfur\nfive\n"),
    ("/ repeats", "/o\r/\rx",
     "one\ntwo\nthree\nfur\nfive\n"),
    ("/ not found", "/zzz\rx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("n, no pattern", "nx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("/ esc", "/two" + ESC + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("/ backspace out", "/\x7fx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    ("/ edited", "/twx\x7fo\rx",
     "one\nwo\nthree\nfour\nfive\n"),
    ("/, dd", "/three\rdd",
     "one\ntwo\nfour\nfive\n"),
]

# The colon commands. :wq and :x and :q! end the program, so the keys typed after
# them are lost, which is checked: the last x of ":wq\rx" must not reach the file.
COMMANDS = [
    (":3", ":3\rx",
     "one\ntwo\nhree\nfour\nfive\n"),
    (":$", ":$\rx",
     "one\ntwo\nthree\nfour\nive\n"),
    (":99 clamps", ":99\rx",
     "one\ntwo\nthree\nfour\nive\n"),
    (":wq", "x:wq\rx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    (":x", "jx:x\rx",
     "one\nwo\nthree\nfour\nfive\n"),
    (":w", "x:w\rjx",
     "ne\nwo\nthree\nfour\nfive\n"),
    (":q unchanged", ":q\rx",
     BASE),
    (":q changed", "x:q\r",
     "ne\ntwo\nthree\nfour\nfive\n"),
    (":q!", "x:q!\rx",
     BASE),
    (":esc", ":3" + ESC + "x",
     "ne\ntwo\nthree\nfour\nfive\n"),
    (":backspace", ":3\x7f2\rx",
     "one\nwo\nthree\nfour\nfive\n"),
    (":backspace out", ":\x7fx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    (":unknown", ":zzz\rx",
     "ne\ntwo\nthree\nfour\nfive\n"),
    (":w name", "x:w copy.txt\rjx:q!\r",
     BASE),
]
# a file a command wrote, beside the one being edited: case name -> (name, what it holds)
WRITTEN = {":w name": ("copy.txt", "ne\ntwo\nthree\nfour\nfive\n")}


def chunks(keys):
    """KEYS one at a time; a marker for a special key (UP, HOME, ...) is the whole
    escape sequence a terminal sends for it, written at once."""
    for key in keys:
        yield SEQUENCES.get(key, key)


def started(fd, limit=30):
    """Wait until the program has written something to its terminal: it is up, and has
    set the terminal the way it wants it. Keys typed before that are taken by the
    terminal's own line editing, not by the program -- and a loaded machine, with all
    these programs starting at once, is slower than any fixed wait."""
    select.select([fd], [], [], limit)


def drive(program, path, keys):
    """Run PROGRAM on PATH in a pty, type KEYS, then ^S and ^Q."""
    program = os.path.abspath(program)
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(os.path.dirname(path))           # where `:w NAME` writes
        os.environ["TERM"] = "xterm"
        if program.endswith(".py"):
            os.execvp(sys.executable, [sys.executable, program, path])
        os.execv(program, [program, path])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))

    def drain(wait):
        while select.select([fd], [], [], wait)[0]:
            try:
                if not os.read(fd, 65536):
                    return
            except OSError:
                return

    def type_(data):
        try:
            os.write(fd, data)
        except OSError:             # the program has quit, as a command can ask
            pass

    started(fd)
    drain(0.6)
    for key in chunks(keys):
        type_(key.encode())
        drain(0.03)
    type_(b"\x13")
    drain(1.4)                      # saving flashes "Saved" for a second
    type_(b"\x11")
    drain(0.3)
    os.waitpid(pid, 0)


SOURCE = '# first\ndef f(): return "s" + 12\nclass Foo:\nz = ""\n'


def screen(program, name, term="xterm"):
    """What the program writes to its terminal: started on the file NAME (SOURCE), moved
    down a line with j, and quit -- the raw bytes, as text."""
    program = os.path.abspath(program)
    path = pathlib.Path(tempfile.mkdtemp()) / name
    path.write_text(SOURCE)
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = term
        if program.endswith(".py"):
            os.execvp(sys.executable, [sys.executable, program, str(path)])
        os.execv(program, [program, str(path)])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    out = b""

    def drain(wait):
        nonlocal out
        while select.select([fd], [], [], wait)[0]:
            try:
                got = os.read(fd, 65536)
            except OSError:
                return
            if not got:
                return
            out += got

    started(fd)
    drain(1.0)
    os.write(fd, b"j")              # the cursor to the second line: the third is not the current one
    drain(0.5)
    os.write(fd, b"\x11")
    drain(0.3)
    os.waitpid(pid, 0)
    return out.decode("latin-1")


# anything a terminal may put between a colour and the text it is for: other attributes,
# a move of the cursor, a change of character set
SKIP = r"(?:\x1b\[[0-9;?]*[A-Za-z]|\x1b\(B)*"


def screen_checks(program):
    """How the text looks on the screen: coloured by language, the cursor's character
    reversed, the line it is on marked, and plain text left alone. Returns the failures."""
    kind = "curses" if program.endswith(".py") else "raw" if os.path.basename(program) == "vi_raw" else "illwill"
    coloured = screen(program, "hl.ady", "xterm-256color")
    plain = screen(program, "hl.txt", "xterm-256color")
    checks = [
        ("keyword colour", re.search(r"\x1b\[(?:[0-9;]*;)?33m" + SKIP + "class", coloured)),
        ("string colour", re.search(r"\x1b\[(?:[0-9;]*;)?32m" + SKIP + '"s"', coloured)),
        ("number colour", re.search(r"\x1b\[(?:[0-9;]*;)?35m" + SKIP + "12", coloured)),
        ("type colour", re.search(r"\x1b\[(?:[0-9;]*;)?36m" + SKIP + "Foo", coloured)),
        ("comment colour", re.search(r"\x1b\[(?:[0-9;]*;)?34m" + SKIP + "# first", coloured)),
        ("cursor reversed", re.search(r"\x1b\[(?:[0-9;]*;)?7m" + SKIP + "d", coloured)),
        ("current line", re.search(r"48;5;236m", coloured) if kind != "illwill"
         else re.search(r"\x1b\[(?:[0-9;]*;)?4m" + SKIP + "ef", coloured)),
        ("quote ends a line", "z = " in coloured and "z = " in plain),
        ("no language, no colour", not re.search(r"\x1b\[(?:[0-9;]*;)?3[2-6]m", plain)),
    ]
    failed = 0
    for name, ok in checks:
        print(f"  screen: {name:24s} {'OK' if ok else 'FAIL'}")
        failed += 0 if ok else 1
    return failed


def main(program):
    work = pathlib.Path(tempfile.mkdtemp())
    jobs = []
    cases = CASES + ARROWS + KEYS + SEARCH + COMMANDS + (ARROWS_CSI if not program.endswith(".py") else [])
    for name, keys, want in cases:
        path = work / (name.replace(",", "_").replace("/", "_") + ".txt")
        path.write_text(BASES.get(name, BASE))
        child = subprocess.Popen([sys.executable, __file__, "--drive", program, str(path), keys])
        jobs.append((name, want, path, child))
    failed = 0
    for name, want, path, child in jobs:
        child.wait()
        got = path.read_text()
        other = WRITTEN.get(name)
        got_other = (path.parent / other[0]).read_text() if other and (path.parent / other[0]).exists() else None
        ok = got == want and (other is None or got_other == other[1])
        print(f"  {name:17s} {'OK' if ok else 'FAIL'}")
        if not ok:
            failed += 1
            print(f"    want: {want!r}\n    got:  {got!r}")
            if other:
                print(f"    {other[0]} want: {other[1]!r}\n    {other[0]} got:  {got_other!r}")
    return failed + screen_checks(program)


if __name__ == "__main__":
    if sys.argv[1] == "--drive":
        drive(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    sys.exit(1 if main(sys.argv[1]) else 0)
