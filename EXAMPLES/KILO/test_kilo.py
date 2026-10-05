#!/usr/bin/env python3
"""Tests for kilo (kilo.ady, built with ady2nim): the editor is run in a terminal of its own
(a pty), is typed a script of keys, and the file it wrote is compared with what is wanted;
then what it writes to the terminal is read for colours, the status bar and the welcome.

    python3 test_kilo.py PROGRAM

The script ends with ^S and ^Q unless the program has quit by itself. The unit tests of the
editor's logic, with no terminal at all, are EXAMPLES/test_kilo_editor.ady.
"""
import fcntl, os, pathlib, pty, re, select, signal, struct, subprocess, sys, tempfile, termios

ESC = "\x1b"
BASE = "one\ntwo\nthree\nfour\nfive\n"

# a special key arrives as one escape sequence, written at once, not as an ESC and typing:
# the script writes a marker character, so that a typed ESC can never be taken for the start of one
UP, DOWN, RIGHT, LEFT, HOME, END, PGUP, PGDN, DEL, CSI_HOME, CSI_END, TILDE_HOME, TILDE_END, CTRL_LEFT, SS3_UP = (
    chr(0xE000 + i) for i in range(15))
SEQUENCES = {
    UP: ESC + "[A", DOWN: ESC + "[B", RIGHT: ESC + "[C", LEFT: ESC + "[D",
    HOME: ESC + "[H", END: ESC + "[F", PGUP: ESC + "[5~", PGDN: ESC + "[6~", DEL: ESC + "[3~",
    CSI_HOME: ESC + "OH", CSI_END: ESC + "OF", TILDE_HOME: ESC + "[1~", TILDE_END: ESC + "[4~",
    CTRL_LEFT: ESC + "[1;5D", SS3_UP: ESC + "OA",
}
FIND, QUIT, SAVE = "\x06", "\x11", "\x13"

CASES = [
    ("typing", "hello", "helloone\ntwo\nthree\nfour\nfive\n"),
    ("enter splits", "ab\r", "ab\none\ntwo\nthree\nfour\nfive\n"),
    ("enter in the middle", RIGHT + RIGHT + "\r", "on\ne\ntwo\nthree\nfour\nfive\n"),
    ("enter at column 0", "\r", "\none\ntwo\nthree\nfour\nfive\n"),
    ("backspace", RIGHT + RIGHT + "\x7f", "oe\ntwo\nthree\nfour\nfive\n"),
    ("^H", RIGHT + "\x08", "ne\ntwo\nthree\nfour\nfive\n"),
    ("backspace joins", DOWN + "\x7f", "onetwo\nthree\nfour\nfive\n"),
    ("backspace at the start", "\x7f", BASE),
    ("del is backspace", RIGHT + DEL, "ne\ntwo\nthree\nfour\nfive\n"),
    ("arrows", DOWN + DOWN + RIGHT + UP + "x", "one\ntxwo\nthree\nfour\nfive\n"),
    ("arrow right wraps", RIGHT * 3 + RIGHT + "x", "one\nxtwo\nthree\nfour\nfive\n"),
    ("arrow left wraps", DOWN + LEFT + "x", "onex\ntwo\nthree\nfour\nfive\n"),
    ("arrow up at the top", UP + "x", "xone\ntwo\nthree\nfour\nfive\n"),
    ("arrows, ESC O", DOWN + SS3_UP + "x", "xone\ntwo\nthree\nfour\nfive\n"),
    ("arrows, modifier", RIGHT + RIGHT + CTRL_LEFT + "x", "oxne\ntwo\nthree\nfour\nfive\n"),
    ("home, end", END + "x" + HOME + "y", "yonex\ntwo\nthree\nfour\nfive\n"),
    ("home, end (ESC O)", CSI_END + "x" + CSI_HOME + "y", "yonex\ntwo\nthree\nfour\nfive\n"),
    ("home, end (~)", TILDE_END + "x" + TILDE_HOME + "y", "yonex\ntwo\nthree\nfour\nfive\n"),
    ("end, then a shorter row", END + DOWN + "x", "one\ntwox\nthree\nfour\nfive\n"),
    ("page down", PGDN + "x", "one\ntwo\nthree\nfour\nfive\nx\n"),
    ("page up", PGDN + PGUP + "x", "xone\ntwo\nthree\nfour\nfive\n"),
    ("tab", "\tx", "\txone\ntwo\nthree\nfour\nfive\n"),
    ("control character", "\x01", "\x01one\ntwo\nthree\nfour\nfive\n"),
    ("^C and ESC do nothing", "\x03" + ESC + "x", "xone\ntwo\nthree\nfour\nfive\n"),
    ("below the last row", DOWN * 8 + "x", "one\ntwo\nthree\nfour\nfive\nx\n"),
    ("append rows", DOWN * 5 + "a\rb", "one\ntwo\nthree\nfour\nfive\na\nb\n"),
    # find: ^F, the text, then ENTER (stay on the match) or ESC (go back); the arrows look further
    ("find", FIND + "thr\rx", "one\ntwo\nxthree\nfour\nfive\n"),
    ("find next", FIND + "o" + DOWN + DOWN + "\rx", "one\ntwo\nthree\nfxour\nfive\n"),
    ("find previous", FIND + "o" + LEFT + "\rx", "one\ntwo\nthree\nfxour\nfive\n"),
    ("find, esc", DOWN + FIND + "five" + ESC + "x", "one\nxtwo\nthree\nfour\nfive\n"),
    ("find, backspace", FIND + "fiz\x7f" + "v\rx", "one\ntwo\nthree\nfour\nxfive\n"),
    ("find, not found", FIND + "zzz\rx", "xone\ntwo\nthree\nfour\nfive\n"),
    ("find, mid-row", FIND + "ee\rx", "one\ntwo\nthrxee\nfour\nfive\n"),
    # the quit: a file with changes takes ^Q four times; any other key in between starts again
    ("quit refused", "x" + QUIT * 3, BASE),
    ("quit, the fourth", "x" + QUIT * 4, BASE),
    ("quit, interrupted", "x" + QUIT * 3 + "y" + QUIT * 3, BASE),
    ("save then quit", "x" + SAVE + QUIT, "xone\ntwo\nthree\nfour\nfive\n"),
]
BASES = {}


def chunks(keys):
    for key in keys:
        yield SEQUENCES.get(key, key)


def start(program, path, term="xterm"):
    """Run PROGRAM on PATH in a pty of 24 by 80; returns (pid, fd)."""
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(os.path.dirname(path))
        os.environ["TERM"] = term
        os.execv(program, [program, os.path.basename(path)])      # as the user types it
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    return pid, fd


def drive(program, path, keys):
    """Run PROGRAM on PATH in a pty, type KEYS, then ^S and ^Q."""
    program = os.path.abspath(program)
    pid, fd = start(program, path)

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
        except OSError:             # the program has quit
            pass

    drain(0.6)
    for key in chunks(keys):
        type_(key.encode("latin-1"))
        drain(0.2 if key == ESC else 0.03)       # a lone ESC is told from a sequence by waiting
    if QUIT not in keys:
        type_(SAVE.encode())
        drain(0.3)
        type_(QUIT.encode())
    drain(0.3)
    # a script that asks for ^Q itself is about what ^Q does: if the program is still there it
    # was refused, and the program is stopped
    done, _ = os.waitpid(pid, os.WNOHANG)
    if not done:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)


SOURCE = '// first\nint f(void) { return "s" + 12; }\nstatic x;\n'


def screen(program, name, keys=b"", term="xterm-256color", source=SOURCE):
    """What the program writes to its terminal: started on the file NAME (SOURCE), typed KEYS,
    and quit with ^Q -- the raw bytes, as text."""
    program = os.path.abspath(program)
    path = pathlib.Path(tempfile.mkdtemp()) / name
    if source is not None:
        path.write_text(source)
    pid, fd = start(program, str(path), term)
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

    drain(1.0)
    for k in keys:
        os.write(fd, bytes([k]))
        drain(0.1)
    os.write(fd, QUIT.encode())
    drain(0.3)
    os.waitpid(pid, 0)
    return out.decode("latin-1")


# anything a terminal may put between a colour and the text it is for
SKIP = r"(?:\x1b\[[0-9;?]*[A-Za-z])*"


def screen_checks(program):
    """How the text looks: coloured by language, the status bar reversed, the welcome in an
    empty file, the match of a search, and plain text left alone. Returns the failures."""
    coloured = screen(program, "hl.c")
    plain = screen(program, "hl.txt")
    empty = screen(program, "new.c", source=None)
    searched = screen(program, "hl.c", b"\x06static\x1b")        # ESC leaves the search, so that ^Q quits
    checks = [
        ("keyword colour", re.search(r"\x1b\[33m" + SKIP + "return", coloured)),
        ("type colour", re.search(r"\x1b\[32m" + SKIP + "int", coloured)),
        ("string colour", re.search(r"\x1b\[35m" + SKIP + '"s"', coloured)),
        ("number colour", re.search(r"\x1b\[31m" + SKIP + "12", coloured)),
        ("comment colour", re.search(r"\x1b\[36m" + SKIP + "// first", coloured)),
        ("status bar", re.search(r"\x1b\[7mhl\.c - 3 lines +1/3", coloured)),
        ("help message", "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find" in coloured),
        ("search match", re.search(r"\x1b\[34m" + SKIP + "static", searched)),
        ("search prompt", "Search: static (Use ESC/Arrows/Enter)" in searched),
        ("welcome", "Kilo editor -- version 0.0.1" in empty),
        ("no language, no colour", not re.search(r"\x1b\[3[1-6]m", plain)),
    ]
    failed = 0
    for name, ok in checks:
        print(f"  screen: {name:24s} {'OK' if ok else 'FAIL'}")
        failed += 0 if ok else 1
    return failed


def main(program):
    work = pathlib.Path(tempfile.mkdtemp())
    jobs = []
    for name, keys, want in CASES:
        path = work / (name.replace(",", "_").replace("/", "_").replace("^", "ctrl_").replace(" ", "_") + ".txt")
        path.write_text(BASES.get(name, BASE))
        child = subprocess.Popen([sys.executable, __file__, "--drive", program, str(path), keys])
        jobs.append((name, want, path, child))
    failed = 0
    for name, want, path, child in jobs:
        child.wait(timeout=60)
        got = path.read_text()
        ok = got == want
        print(f"  {name:26s} {'OK' if ok else 'FAIL'}")
        if not ok:
            failed += 1
            print(f"    want: {want!r}\n    got:  {got!r}")
    return failed + screen_checks(program)


if __name__ == "__main__":
    if sys.argv[1] == "--drive":
        drive(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(0)
    sys.exit(1 if main(sys.argv[1]) else 0)
