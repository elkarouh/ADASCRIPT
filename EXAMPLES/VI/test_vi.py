#!/usr/bin/env python3
"""Tests for the vi editor (vi_core.ady) on each of its terminals -- vi_py.ady (curses,
built with ady2py as vi_py.py), vi_nim.ady (illwill) and vi_raw.ady (Nim's terminal
module and termios): the editor is run in a terminal of its own (a pty), is typed a
script of keys, and the file it wrote is compared with what is wanted.

    python3 test_vi.py PROGRAM

The script ends with ^S and ^Q unless the program has quit by itself (`:wq`, `:q`).
The wanted files are what a vi writes for the same keys.
"""
import fcntl, os, pathlib, pty, select, struct, subprocess, sys, tempfile, termios

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

# An arrow key arrives as one escape sequence, ESC O A on a terminal in
# application keypad mode (which curses puts it in) or ESC [ A in the other:
# neither is an ESC followed by typing. The Nim editors read the terminal
# themselves, so they are held to both; curses only knows the first.
UP, DOWN, RIGHT, LEFT = ESC + "OA", ESC + "OB", ESC + "OC", ESC + "OD"
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
    ("arrows (CSI)", "ia" + ESC + "[A" + "b" + ESC + "[C" + "c" + ESC + "[1;5D" + "d" + ESC,
     "abodcne\ntwo\nthree\nfour\nfive\n"),
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
    """KEYS one at a time, an arrow key's escape sequence (ESC O A, ESC [ A and
    ESC [ 1 ; 5 D) all at once, as a terminal sends it."""
    i = 0
    while i < len(keys):
        for width in (6, 3):
            part = keys[i:i + width]
            if part[:1] == ESC and (part[1:2] == "[" or part[1:2] == "O") and part[-1:] in "ABCD" \
                    and all(c in "0123456789;" for c in part[2:-1]) and len(part) == width \
                    and not (part[1:2] == "O" and width == 6):
                break
        else:
            width = 1
        yield keys[i:i + width]
        i += width


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

    drain(0.6)
    for key in chunks(keys):
        type_(key.encode())
        drain(0.03)
    type_(b"\x13")
    drain(1.4)                      # saving flashes "Saved" for a second
    type_(b"\x11")
    drain(0.3)
    os.waitpid(pid, 0)


def main(program):
    work = pathlib.Path(tempfile.mkdtemp())
    jobs = []
    cases = CASES + ARROWS + COMMANDS + (ARROWS_CSI if not program.endswith(".py") else [])
    for name, keys, want in cases:
        path = work / (name.replace(",", "_") + ".txt")
        path.write_text(BASE)
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
    return failed


if __name__ == "__main__":
    if sys.argv[1] == "--drive":
        drive(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    sys.exit(1 if main(sys.argv[1]) else 0)
