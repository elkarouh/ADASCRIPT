# BROWSER_EXAMPLES/SHOPPING_LIST -- a shopping list, in the browser alone

The app that `DOCS/ADASCRIPT_FOR_JAVASCRIPT.md`'s tutorial builds, step by step: type what to buy,
click an item once it is in the basket, × takes it off the list. The list is kept in the
browser's storage, so it is there again after a reload. No server.

```
make            # build shopping_page.js
make open       # build, and open index.html
make test       # check the model, natively, with no page
```

| File | What it is |
|---|---|
| `shopping_model.ady` | the list: `Item_T`, `Refusal_T`, `Shopping_List` (`want`, `toggle`, `remove`, `left`, `text`, `load`). No page in it; compiles natively and to JavaScript. |
| `tests/test_shopping.ady` | the model checked, natively (`make test`). |
| `shopping_view.ady` | what it looks like: `Item_View`, `List_View`, `Page_View`, each with its look in a `style` block and a `to_html`. |
| `shopping_page.ady` | the script: draws the page, listens to clicks and keys, changes the list, keeps it (`Store`). Built by `ady2nim js`. |
| `index.html` | the page that loads the script. |
