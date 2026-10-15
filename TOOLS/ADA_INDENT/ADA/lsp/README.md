# ada_indent_proxy -- the Ada Language Server with ada_indent's formatting

`ada_indent_proxy.py` starts the Ada Language Server (`ada_language_server`,
"als", from AdaCore) as a child process and sits between it and the editor.
Everything is forwarded unchanged in both directions -- requests, responses,
notifications, and the requests als itself sends to the editor -- except:

| What | Handled by |
|---|---|
| `initialize` response | als's, with the formatting capabilities added (als's own are kept) |
| `textDocument/formatting` | the proxy, with `ada_indent` -- never sent to als |
| `textDocument/rangeFormatting` | the proxy |
| `textDocument/onTypeFormatting` | the proxy (Enter, and the last letter of a dedenting keyword) |

Documents are tracked from `didOpen` / `didChange` / `didClose` (which als
receives too, so it sees exactly what the editor sent). For an edit near the
end of a file the proxy resumes `ada_indent` from a saved state
(`--emit-state` / `--state`) instead of reading the file from the top; an edit
to a line already covered by the saved state drops it. The state kept
is the one from before the line just formatted, so the editor rewriting that
line's indentation does not discard it.

Enter on a blank line puts the cursor at the column a statement would take
there (`ada_indent` itself leaves blank lines empty).

If als cannot be started, or dies, the proxy keeps answering on its own: it
announces only the formatting capabilities and refuses everything else with
`MethodNotFound`. `--no-als` asks for that from the start.

It is written in Python 3 (3.9 or later) and uses only the standard library,
so there is nothing to install besides als itself.

## Use

```
ada_indent_proxy.py [--ada-indent PATH] [--als COMMAND] [--no-als]
                    [--log FILE] [-- ALS_ARGS...]
```

* `--ada-indent` -- the binary (default: `ada_indent` on PATH, else `../bin/ada_indent`)
* `--als` -- the Ada Language Server command (default: `ada_language_server`)
* arguments after `--` go to als

Point the editor at the proxy instead of at als. The server communicates over
stdio. For example:

```elisp
;; Emacs (eglot)
(add-to-list 'eglot-server-programs
             '((ada-mode ada-ts-mode) . ("python3" "/path/to/ada_indent_proxy.py")))
```

VS Code has no built-in way to start an arbitrary language server, so use a
generic LSP client extension. With
[Generic LSP Client](https://marketplace.visualstudio.com/items?itemName=zsol.vscode-glspc)
(`zsol.vscode-glspc`), in `settings.json`:

```json
{
  "glspc.server.command": "python3",
  "glspc.server.commandArguments": ["/path/to/lsp/ada_indent_proxy.py"],
  "glspc.server.languageId": "ada"
}
```

(Those setting names are from that extension's documentation; this has not
been tried in VS Code here.) If AdaCore's own Ada extension is also installed,
it starts als by itself; disable it for the workspace, or the editor will talk
to two servers.

als reads its project from the editor's `initialize` request as usual; the
proxy does not touch it.

## Tests

```bash
make test-lsp          # from the repository root; or: python3 lsp/test_proxy.py
```

Unit tests (applying incremental edits, UTF-16 positions, when the saved state
is dropped); the proxy on its own (`--no-als`); and the proxy in front of
`stub_als.py`, a stand-in for als that checks what is forwarded, what is not,
that als's own capabilities survive, and that requests als makes of the editor
get through. The tests do not need als. Nor have they been run against the
real `ada_language_server`.

## Limits

* Indentation only: the proxy adds nothing else to als, and replaces als's own
  formatting requests with `ada_indent`'s.
* The editor's `FormattingOptions` (tab size, insert spaces) are ignored:
  `ada_indent` always indents with 2 spaces.
