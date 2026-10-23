## karax_text.nim -- a page's HTML, under `ady2nim js`: what str(page) is in a module with an
## `html:` block (GRAMMAR/ady_html.py imports it there in place of karax's `$`).
##
## karax's `$` of a VNode is, under JavaScript, a dump of its nodes for debugging, and its `add`,
## which writes the HTML natively, takes a JavaScript string a code unit at a time, so that "→"
## comes out as a byte of it. This is karax's `add`, with each text made a str first: the same
## HTML as natively.

when defined(js):
  import karax/[vdom, vstyles, kbase]
  from strutils import tokenize, toLowerAscii

  const selfClosing = {VNodeKind.area, VNodeKind.base, VNodeKind.br, VNodeKind.col,
    VNodeKind.embed, VNodeKind.hr, VNodeKind.img, VNodeKind.input, VNodeKind.link,
    VNodeKind.meta, VNodeKind.param, VNodeKind.source, VNodeKind.track, VNodeKind.wbr}

  proc addEscapedAttr(result: var string, s: kstring) =
    for c in items($s):
      case c
      of '<': result.add("&lt;")
      of '>': result.add("&gt;")
      of '&': result.add("&amp;")
      of '"': result.add("&quot;")
      else: result.add(c)

  proc addEscaped(result: var string, s: kstring) =
    for c in items($s):
      case c
      of '<': result.add("&lt;")
      of '>': result.add("&gt;")
      of '&': result.add("&amp;")
      of '"': result.add("&quot;")
      of '\'': result.add("&#x27;")
      of '/': result.add("&#x2F;")
      else: result.add(c)

  proc addIndent(result: var string, indent: int) =
    result.add("\n")
    for i in 1..indent: result.add(' ')

  proc addHtml(result: var string, n: VNode, indent = 0, indWidth = 2) =
    if n.kind == VNodeKind.text:
      result.addEscaped(n.text)
    elif n.kind == VNodeKind.verbatim:
      result.add($n.text)
    else:
      let kind = $n.kind
      result.add('<')
      result.add(kind)
      if n.id.len > 0:
        result.add " id=\""
        result.addEscapedAttr(n.id)
        result.add('"')
      if n.class.len > 0:
        result.add " class=\""
        result.addEscapedAttr(n.class)
        result.add('"')
      for k, v in attrs(n):
        result.add(' ')
        result.add($k)
        result.add("=\"")
        result.addEscapedAttr(v)
        result.add('"')
      if n.style != nil:
        result.add " style=\""
        for k, v in pairs(n.style):
          if v.len == 0: continue
          for t in tokenize($k, seps={'A' .. 'Z'}):
            if t.isSep: result.add '-'
            result.add toLowerAscii(t.token)
          result.add ": "
          result.add($v)
          result.add "; "
        result.add('"')
      if n.len > 0:
        result.add('>')
        if n.len > 1:
          var noWhitespace = false
          for i in 0..<n.len:
            if n[i].kind == VNodeKind.text:
              noWhitespace = true
              break
          if noWhitespace:
            for i in 0..<n.len: result.addHtml(n[i], indent+indWidth, indWidth)
          else:
            for i in 0..<n.len:
              result.addIndent(indent+indWidth)
              result.addHtml(n[i], indent+indWidth, indWidth)
            result.addIndent(indent)
        else:
          result.addHtml(n[0], indent+indWidth, indWidth)
        result.add("</")
        result.add(kind)
        result.add(">")
      elif n.kind in selfClosing:
        result.add(" />")
      else:
        result.add(">")
        result.add("</")
        result.add(kind)
        result.add(">")

  proc `$`*(n: VNode): string =
    ## The HTML of N, as karax writes it natively.
    result = ""
    result.addHtml(n)
