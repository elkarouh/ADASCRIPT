## expect — TCL-style process automation via PTY.
##
## Usage:
##   import expect
##
##   var s = spawn("ssh user@host")
##   s.expect("password:")
##   s.send("mypassword\n")
##   s.expect("$ ")
##   s.send("ls\n")
##   let output = s.expectEof()
##   s.close()
##
## API
## ---
##   spawn(cmd)                          spawn `cmd` in a PTY (/bin/sh -c)
##   s.send(text)                        write text to the process stdin
##   s.expect(pattern, timeout=30)       wait until output matches pattern;
##                                       raises ExpectTimeout or ExpectEof
##   s.expectEof(timeout=30) -> string   read until EOF; return all output
##   s.close()                           close master fd; does not wait for child
##   s.before  -> string                 output before the last match
##   s.match   -> string                 the matched text itself

import posix, re

{.passL: "-lutil".}

proc forkpty(amaster: ptr cint; name: cstring;
             termp, winp: pointer): Pid
    {.importc: "forkpty", header: "<pty.h>".}

type
  ExpectError*   = object of IOError
  ExpectTimeout* = object of ExpectError
  ExpectEof*     = object of ExpectError

  Spawn* = ref object
    master*: cint
    pid*:    Pid
    buf:     string
    before*: string
    match*:  string

proc spawn*(cmd: string): Spawn =
  ## Spawn `cmd` as a child process connected to a PTY.
  result = Spawn(master: -1, buf: "")
  var master: cint
  let pid = forkpty(addr master, nil, nil, nil)
  if pid < 0:
    raise newException(ExpectError, "forkpty failed: " & $strerror(errno))
  if pid == 0:
    # child
    let args = [cstring("/bin/sh"), cstring("-c"), cstring(cmd), nil]
    discard execv("/bin/sh", cast[cstringArray](addr args))
    quit(1)
  result.master = master
  result.pid    = pid

proc close*(s: Spawn) =
  ## Close the master PTY fd.
  if s.master >= 0:
    discard posix.close(s.master)

proc send*(s: Spawn; text: string) =
  ## Write `text` to the process.
  var buf = text
  let n = posix.write(s.master, addr buf[0], buf.len)
  if n < 0:
    raise newException(ExpectError, "write failed: " & $strerror(errno))

proc readChunk(s: Spawn; timeout: int): bool =
  ## Read one chunk into s.buf.  Returns false on EOF.
  var fds: TFdSet
  posix.FD_ZERO(fds)
  posix.FD_SET(s.master, fds)
  var tv: Timeval
  tv.tv_sec  = Time(timeout)
  tv.tv_usec = 0
  let r = posix.select(s.master + 1, addr fds, nil, nil, addr tv)
  if r == 0:
    raise newException(ExpectTimeout, "timeout after " & $timeout & "s")
  if r < 0:
    raise newException(ExpectError, "select failed: " & $strerror(errno))
  var tmp = newString(4096)
  let n = posix.read(s.master, addr tmp[0], tmp.len)
  if n <= 0:
    return false
  tmp.setLen(n)
  s.buf.add(tmp)
  return true

proc expect*(s: Spawn; pattern: string; timeout: int = 30) =
  ## Wait until accumulated output matches `pattern` (regex).
  ## Sets s.before and s.match.
  let rx = re(pattern)
  while true:
    let bounds = s.buf.findBounds(rx)
    let first = bounds.first
    let last  = bounds.last
    if first >= 0:
      s.before = s.buf[0 ..< first]
      s.match  = s.buf[first .. last]
      s.buf    = s.buf[last + 1 .. ^1]
      return
    if not readChunk(s, timeout):
      raise newException(ExpectEof, "EOF before pattern matched: " & pattern)

proc expectEof*(s: Spawn; timeout: int = 30): string =
  ## Read until EOF and return all output.
  while true:
    if not readChunk(s, timeout):
      result = s.buf
      s.buf  = ""
      return
