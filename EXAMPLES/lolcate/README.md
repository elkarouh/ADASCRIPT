# lolcate.ady — Fast File Indexer

An Adascript port of [lolcate-rs](https://github.com/ngirard/lolcate-rs): a fast, regex-based file finder that pre-indexes your filesystem so queries are instant.

## How It Works

lolcate maintains named **databases**, each stored under `~/.local/share/lolcate-ady/<name>/`:

```
~/.local/share/lolcate-ady/
└── default/
    ├── config.txt   ← directories to scan, patterns to ignore, symlink policy
    └── db.txt       ← flat newline-delimited list of indexed paths
```

**Updating** (`update`) walks the configured directories using [`fd`](https://github.com/sharkdp/fd) (`--no-ignore --hidden`) and writes every non-ignored path to `db.txt`. **Querying** (`query`) runs [`rg`](https://github.com/BurntSushi/ripgrep) case-insensitively against that flat list — no filesystem traversal needed.

## Dependencies

| Tool | Purpose |
|------|---------|
| [`fd`](https://github.com/sharkdp/fd) | Fast recursive file finder, used during `update` |
| [`rg`](https://github.com/BurntSushi/ripgrep) (ripgrep) | Fast regex search, used during `query` |

Install on Debian/Ubuntu: `apt install fd-find ripgrep`  
Install on macOS: `brew install fd ripgrep`

## Running

### As a Python script (interpreted)

```sh
python3.12 ../../TO_PYTHON/py2py.py lolcate.ady create default
python3.12 ../../TO_PYTHON/py2py.py lolcate.ady update
python3.12 ../../TO_PYTHON/py2py.py lolcate.ady query myfile
```

### As a compiled Nim binary (fast)

```sh
# Transpile once
python3.12 ../../TO_NIM/py2nim.py lolcate.ady > lolcate.nim

# Compile
nim c -d:release -o:lolcate lolcate.nim

# Run
./lolcate create default
./lolcate update
./lolcate query myfile
```

## Commands

| Command | Description |
|---------|-------------|
| `create <name>` | Create a new named database |
| `update [name]` | Rebuild the file index (default: `default`) |
| `query <pattern> [name]` | Search the index with a regex (default: `default`) |
| `ls` | List all databases with file counts |
| `info [name]` | Show database details (default: `default`) |
| `add-dir <name> <path>` | Add a directory to the scan list |
| `add-ignore <name> <pattern>` | Add a filename pattern to ignore |

### Examples

```sh
# Create and populate the default database
./lolcate create default
./lolcate add-dir default ~/projects
./lolcate update

# Find all Nim source files
./lolcate query '\.nim$'

# Find files with "config" in the name (case-insensitive)
./lolcate query config

# Manage a separate database for a project
./lolcate create work
./lolcate add-dir work /srv/app
./lolcate add-ignore work '*.log'
./lolcate update work
./lolcate query '\.py$' work
```

## Config File Format

`config.txt` uses a simple line-based format — no external parser needed:

```
# lolcate-ady config
dirs:
/home/user
/srv/data
ignores:
.git
node_modules
__pycache__
target
follow_symlinks:
false
```

Lines starting with `#` and blank lines are ignored. Each section header (`dirs:`, `ignores:`, `follow_symlinks:`) introduces the values that follow it, one per line.

**Default ignore list:** `.git`, `.hg`, `.svn`, `node_modules`, `__pycache__`, `.mypy_cache`, `target`, `.cargo`, `build`, `dist`, `.tox`, `.venv`

## Adascript Features Demonstrated

| Feature | Usage in this file |
|---------|--------------------|
| `nimport` | `nimport os, strutils, times` — imports Nim stdlib modules |
| `shellLines:` | Captures `fd` / `rg` / `ls` output as a `seq[string]` |
| `$HOME` | Environment variable expansion → `getEnv("HOME")` |
| `-f`, `-d` | File/directory existence tests (`if -f path:`, `if -d dir:`) |
| `case/when` | String dispatch on CLI commands |
| `type … is record` | Struct-like record type (`Config`) |
| `with open() as f:` | File handle with automatic close (`defer`) |
| f-strings | `f"Indexed {count} files in {elapsed:.2f}s"` |
| Implicit returns | Last expression in a `def` is the return value |
