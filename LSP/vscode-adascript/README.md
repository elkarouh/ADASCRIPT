# Adascript — VS Code Extension

Language support for [Adascript](https://github.com/elkarouh/adascript) (`.ady` files) in Visual Studio Code.

## Features

- **Syntax highlighting** — type declarations, tick attributes (`Color'First`), Ada/Python keywords, decorators, built-ins
- **Diagnostics** — parse errors underlined in real time as you type
- **Hover** — enum type info (members, `First`/`Last`), symbol types
- **Completion** — tick-attribute suggestions (`EnumType'`), enum member access (`EnumType.`), prefix-filtered type and symbol names

All editor features beyond highlighting are provided by the Adascript language server (`adascript_ls.py`) via the Language Server Protocol.

## Requirements

| Requirement | Version |
|---|---|
| VS Code | ≥ 1.75 |
| Python | 3.13+ |
| Node.js | (build only — any LTS) |

The language server also requires the `pygls` Python package:

```bash
python3.13 -m pip install pygls
```

## Installation

### Development (run from source)

```bash
cd LSP/vscode-adascript
npm install
```

Then open the `ADASCRIPT` folder in VS Code and press **F5** to launch an Extension Development Host with the extension loaded.

### Package as VSIX

```bash
cd LSP/vscode-adascript
npm install
npx vsce package
# produces adascript-0.1.0.vsix
```

Install the resulting `.vsix` via **Extensions → ··· → Install from VSIX…**

## Configuration

| Setting | Default | Description |
|---|---|---|
| `adascript.python` | `python3.13` | Python interpreter used to start the language server |
| `adascript.serverPath` | *(bundled)* | Absolute path to `adascript_ls.py`; defaults to the sibling file at `LSP/adascript_ls.py` |
| `adascript.trace.server` | `off` | LSP trace level: `off`, `messages`, or `verbose` |

Add to your `settings.json` if the defaults do not match your environment:

```json
{
  "adascript.python": "/usr/bin/python3.13",
  "adascript.serverPath": "/absolute/path/to/ADASCRIPT/LSP/adascript_ls.py"
}
```

## Syntax Highlighting

The grammar (`source.adascript`) covers:

| Construct | Example |
|---|---|
| Type declaration | `type Color is enum RED, GREEN, BLUE` |
| Block enum | `type Color is enum:` |
| Record / tuple | `type Point is record:` |
| Tick attribute | `Color'First`, `State'Last` |
| Ada keywords | `type`, `is`, `enum`, `record`, `tuple`, `when` |
| Python keywords | `def`, `class`, `if`, `for`, `match`, … |
| Decorators | `@method(Foo)` |
| Built-in functions | `len(`, `print(`, … |
| Numeric literals | decimal, hex (`0xFF`), binary (`0b101`), octal |
