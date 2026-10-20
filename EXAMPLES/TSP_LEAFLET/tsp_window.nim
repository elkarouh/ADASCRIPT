## tsp_window -- tsp_map.html in a native window (the system's web engine) instead of the browser.
##
##   nim c -r tsp_window.nim            open the window
##   nim c -r tsp_window.nim --check    load the page, print what it shows, exit
##
## The page is unchanged: the script is put inline, so no server is needed. Two Nim procs are bound
## for the page, `nim_log` (the page's console and errors reach this terminal) and `nim_quit`.
import std/[json, os, strutils]
import webview

# webview's own `bind` hands its callback context to C without keeping a reference, so Nim's memory
# manager frees it and the first call from the page crashes. This keeps the context alive.
type Handler = proc (req: JsonNode): string
type Context = ref object
  w: Webview
  fn: Handler

proc dispatch(id: cstring; req: cstring; arg: pointer) {.cdecl.} =
  let ctx = cast[Context](arg)
  var failed: cint
  let res = try: ctx.fn(parseJson($req))
            except CatchableError: failed = -1; $ %* getCurrentExceptionMsg()
  discard webviewReturn(ctx.w, id, failed, cstring res)

proc bindProc(w: Webview, name: string, fn: Handler) =
  let ctx = Context(w: w, fn: fn)
  GC_ref(ctx)
  discard w.webviewBind(name, dispatch, cast[pointer](ctx))

let here = currentSourcePath().parentDir
let check = "--check" in commandLineParams()

let html = readFile(here / "tsp_map.html").replace(
  "<script src=\"tsp_map.js\"></script>",
  "<script>" & readFile(here / "tsp_map.js").replace("</script", "<\\/script") & "</script>")

# Runs before the page's own scripts: console and errors go to nim_log.
const hook = """
for (const level of ["log", "warn", "error"]) {
  const old = console[level];
  console[level] = (...a) => { window.nim_log(level + ": " + a.join(" ")); old.apply(console, a); };
}
window.addEventListener("error", e => window.nim_log("error: " + e.message));
window.addEventListener("load", () => setTimeout(() => window.nim_log("loaded: " +
  document.querySelectorAll("tr.algo").length + " rows, selected: " +
  (document.querySelector("tr.selected td") || {}).textContent), 500));
"""

let w = newWebview(debug = not check)
if w == nil:
  quit "no web engine (on Linux: libwebkit2gtk-4.1 and a display)"
w.title = "Travelling salesman in Adascript"
w.size = (1100, 700)

w.bindProc("nim_log") do (req: JsonNode) -> string:
  let msg = req[0].getStr()
  echo msg
  if check and msg.startsWith("loaded:"):
    w.terminate()
  "null"
w.bindProc("nim_quit") do (req: JsonNode) -> string:
  w.terminate()
  "null"

w.init(hook)
w.html = html
w.run()
w.destroy()
