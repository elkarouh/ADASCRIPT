# BROWSER_EXAMPLES/LITTLE_PAGES -- lots of little HTML pages

A list of posts that can be shown as *recent*, *popular* or *all* is the kind of
thing that gets a script in the page: a button per filter, and code that hides
and shows items. Here each filter is a page of its own, and the tabs are links.

```
make pages      # writes build/recent.html, popular.html and all.html
make open       # the same, then opens build/recent.html
```

`little_pages.ady` is a native program that writes the three pages, once. In each
one the tab for that page is marked, and every tab is a plain `<a href>`. The one
line that makes the links feel like an in-page switch is CSS:

```css
@view-transition { navigation: auto; }
```

With it, a browser that supports cross-document view transitions cross-fades from
one page to the next; one that does not just loads the next page. Nothing runs in
the browser, so there is no `ady2nim js` build and no karax.

Use this shape when each view is a different list or document (a filter, a tab of
read-only text, a menu of links). Keep a script for a view that holds state the
reader built up, such as `TOOLS/ACCOUNTING`, where the graph and its dragged
accounts stay put while the tab below changes.

After Jim Nielsen, [Building Websites With LLMS](https://blog.jim-nielsen.com/2025/lots-of-little-html-pages/).
