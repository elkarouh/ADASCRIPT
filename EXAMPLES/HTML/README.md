# EXAMPLES/HTML -- pages written as Adascript objects, with `html:` blocks

Three small programs that show how a page is built from objects. Each class has a
`to_html` method that says what it looks like, and the page is the objects' output
put together. The HTML comes from karax, which Adascript's `html:` blocks compile to.

```
make card       # one widget: a Card, printed as HTML           (html_card.ady)
make app        # a page as a tree of widgets, opened in the browser (html_app.ady)
make counter    # a counter in the browser, with buttons       (html_counter.ady)
make all        # build every page into build/, open none
```

You need karax 1.5.0 or later: `nimble install karax@1.5.0`.

## The three programs

| File | What it shows | Runs as |
|---|---|---|
| `html_card.ady` | A class with `to_html`, printed to standard output. Start here: no browser, no events. | native, `ady2nim c -r` |
| `html_app.ady` | `@virtual` and inheritance: a `Widget` base class, with `Label` and `Button` subclasses. The page asks each child for its own HTML, and each child asks its children in turn. | native, printed; `make app` opens it |
| `html_counter.ady` | Events: an attribute starting with `on`, such as `onclick=self.inc`, is a call on the object. The page is drawn again after each click. | browser: `ady2nim js`, served by `make counter` |

`index.html` is the page that loads `html_counter.js`, and `make counter` copies it into
`build/` beside the script.

## The pattern

- Give each thing on the page a class, with a `to_html(self) -> Html` method.
- Build the HTML in an `html:` block. Tags are the names, `class=` and `id=` are attributes,
  and a string after a colon is the text: `h2: self.title`.
- Use `@virtual` on a base class when subclasses override `to_html`, so the call picks the
  right one.
- For a page with buttons, mark the class `@virtual` too, so a handler and the page share
  one object. A handler is a method, named as the attribute value: `onclick=self.inc`.

## Where the real apps are

These three show the pattern and nothing else. The worked web apps are in:

- `TOOLS/ACCOUNTING`: Kleppmann's accounting, with the model, a ledger, a static page
  (`make gui`) and a page the server draws and htmx keeps up to date.
- `EXAMPLES/DIJKSTRA_HTMX`: a shortest-path demo in the same shape, with a small browser
  script built on the stdlib's `browser` and `svg_drag` modules.

The accounting example that used to be here is now the tool in `TOOLS/ACCOUNTING`.
