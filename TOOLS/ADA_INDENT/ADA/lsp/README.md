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
to a line already covered by the saved state drops it.

Enter on a blank line puts the cursor at the column a statement would take
there (`ada_indent` itself leaves blank lines empty).

If als cannot be started, or dies, the proxy keeps answering on its own: it
announces only the formatting capabilities and refuses everything else with
`MethodNotFound`. `--no-als` asks for that from the start.

Standard library only -- Python 3.9 or later.

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

```lua
-- Neovim (nvim-lspconfig)
require('lspconfig.configs').ada_indent = {
  default_config = {
    cmd = { "python3", "/path/to/ada_indent_proxy.py" },
    filetypes = { "ada" },
    root_dir = require('lspconfig').util.find_git_ancestor,
  },
}
require('lspconfig').ada_indent.setup{}
```

```toml
# Helix, languages.toml
[language-server.ada-indent]
command = "python3"
args = ["/path/to/ada_indent_proxy.py"]
[[language]]
name = "ada"
language-servers = ["ada-indent"]
```

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
