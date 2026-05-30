# Adascript — Sublime Text package

Syntax highlighting for Adascript (`.ady`) files in Sublime Text 3 / 4.

## Files

| File | Purpose |
|---|---|
| `Adascript.sublime-syntax` | Syntax definition (colours) |
| `Adascript.sublime-settings` | Language defaults: 3-space indent, `'` word separator |
| `Comments.tmPreferences` | Maps **Edit › Toggle Comment** (`Ctrl+/`) to `# ` |

## Installation

Copy (or symlink) this directory into your Sublime Text **Packages** folder:

| Platform | Packages folder |
|---|---|
| macOS | `~/Library/Application Support/Sublime Text/Packages/` |
| Linux | `~/.config/sublime-text/Packages/` |
| Windows | `%APPDATA%\Sublime Text\Packages\` |

```bash
# macOS / Linux example:
cd "~/Library/Application Support/Sublime Text/Packages"   # or the Linux path
ln -s /path/to/ADASCRIPT/LSP/sublime-adascript Adascript
```

Sublime Text picks up the package immediately — no restart required.  Open any
`.ady` file and the syntax should appear in the bottom-right status bar as
**Adascript**.

## Language Server (LSP)

Install the [LSP package](https://packagecontrol.io/packages/LSP) from Package
Control, then add a custom client to **Preferences › Package Settings › LSP ›
Settings**:

```json
{
    "clients": {
        "adascript": {
            "enabled": true,
            "command": ["python3.13", "/path/to/ADASCRIPT/LSP/adascript_ls.py"],
            "selector": "source.adascript"
        }
    }
}
```

Replace `/path/to/ADASCRIPT` with the absolute path to the repository root.
The server requires Python 3.13 and the `pygls` package (`pip install pygls`).

Once configured, open an `.ady` file and run **LSP: Enable Language Server in
Project** from the Command Palette.  Hover, go-to-definition, and diagnostics
will be available.

## What is highlighted

| Construct | Example |
|---|---|
| Comments | `# this is a comment` |
| Triple-quoted strings | `"""docstring"""`, `'''alt'''` |
| F-strings with interpolation | `f"value is {x + 1}"` |
| Type declarations | `type Color is enum RED, GREEN, BLUE` |
| Tick attributes | `Color'First`, `s'Length` |
| Storage modifiers | `var`, `let`, `const` |
| Control keywords | `case`, `when`, `enum`, `record`, `type`, … |
| Built-in constants | `True`, `False`, `None` |
| Built-in functions | `len(…)`, `print(…)`, … |
| Numeric literals | `0xFF`, `0b1010`, `3.14e-2` |
| Bash-style variables | `$1`, `$#`, `$@`, `$HOME` |
| Range operators | `1..10`, `0..<n` |
| Operators | `:=`, `==`, `**`, `//`, `+=`, … |
| Decorators | `@staticmethod` |
| Function / class names | `def foo(…)`, `class Bar:` |
