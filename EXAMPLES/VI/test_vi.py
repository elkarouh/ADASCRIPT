#!/usr/bin/env python3
"""Tests for vi_py.ady and vi_nim.ady, the Adascript translations of vip: the
editor is run in a terminal of its own (a pty), is typed a script of keys, saves
with ^S and quits with ^Q, and the file it saved is compared with what is wanted.

    python3 test_vi.py PROGRAM        (vi_py.ady built with ady2py, as vi_py.py,
                                       or vi_nim.ady built with ady2nim)

The wanted files are what vip (github.com/maksimKorzh/vip) writes for the same
keys, except where vip differs: its undo bookkeeping records a snapshot before
a dd/yy/R takes effect, so one `u` undoes nothing and `xxxuu` undoes all
three, and typing in R mode past the end of a line raises IndexError and exits
without saving. Those cases (marked VIP DIFFERS) want what a vi does.
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
VIP_DIFFERS = {"replaceR", "undo,redo", "undo3", "dd,u,redo"}

# An arrow key arrives as one escape sequence, ESC O A on a terminal in
# application keypad mode (which curses puts it in) or ESC [ A in the other:
# neither is an ESC followed by typing. The Nim editor reads the terminal
# itself, so it is held to both; curses only knows the first.
ARROWS = [
    ("arrows (SS3)", "ia" + ESC + "OA" + "b" + ESC + "OC" + "c" + ESC,
     "abcone\ntwo\nthree\nfour\nfive\n"),
]
ARROWS_CSI = [
    ("arrows (CSI)", "ia" + ESC + "[A" + "b" + ESC + "[C" + "c" + ESC + "[1;5D" + "d" + ESC,
     "abcdone\ntwo\nthree\nfour\nfive\n"),
]


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
    pid, fd = pty.fork()
    if pid == 0:
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

    drain(0.6)
    for key in chunks(keys):
        os.write(fd, key.encode())
        drain(0.03)
    os.write(fd, b"\x13")
    drain(1.4)                      # saving flashes "Saved" for a second
    os.write(fd, b"\x11")
    drain(0.3)
    os.waitpid(pid, 0)


def main(program):
    work = pathlib.Path(tempfile.mkdtemp())
    jobs = []
    cases = CASES + ARROWS + (ARROWS_CSI if not program.endswith(".py") else [])
    for name, keys, want in cases:
        path = work / (name.replace(",", "_") + ".txt")
        path.write_text(BASE)
        child = subprocess.Popen([sys.executable, __file__, "--drive", program, str(path), keys])
        jobs.append((name, want, path, child))
    failed = 0
    for name, want, path, child in jobs:
        child.wait()
        got = path.read_text()
        note = "  (VIP DIFFERS)" if name in VIP_DIFFERS else ""
        print(f"  {name:12s} {'OK' if got == want else 'FAIL'}{note}")
        if got != want:
            failed += 1
            print(f"    want: {want!r}\n    got:  {got!r}")
    return failed


if __name__ == "__main__":
    if sys.argv[1] == "--drive":
        drive(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    sys.exit(1 if main(sys.argv[1]) else 0)
