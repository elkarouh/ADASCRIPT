#!/usr/bin/env -S nim r
## lolcate.ady — fast file indexer, Adascript port of lolcate-rs.
## 
## Each named database lives in  ~/.local/share/lolcate-ady/<name>/
## config.txt — dirs to scan, patterns to ignore, symlink policy
## db.txt     — flat newline-delimited path list (the index)
## 
## Config file format (line-based, no external parser needed):
## dirs:              section header — paths follow, one per line
## ignores:           section header — name patterns follow, one per line
## follow_symlinks:   section header — 'true' or 'false' on next line
## 
## Commands:
## create <name>            Create a new named database
## update [name]            Rebuild the file index          (default: 'default')
## query  <pattern> [name]  Search index with regex         (default: 'default')
## ls                       List all databases
## info   [name]            Show database details           (default: 'default')
## add-dir    <name> <dir>  Add a directory to the scan list
## add-ignore <name> <pat>  Add an ignore pattern

import algorithm, os, osproc, re, sequtils, strformat, strutils, times

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

type Config = object
    dirs: seq[string]
    ignores: seq[string]
    follow_symlinks: bool
const DEFAULT_DB: string = "default"
const DEFAULT_IGNORES: seq[string] = @[".git", ".hg", ".svn", "node_modules", "__pycache__", ".mypy_cache", "target", ".cargo", "build", "dist", ".tox", ".venv"]

# ---------------------------------------------------------------------------
# Path helpers  (implicit returns — last expression in function)
# ---------------------------------------------------------------------------

proc data_dir(): string =
    joinPath(getEnv("HOME"), ".local", "share", "lolcate-ady")

proc db_dir(name: string): string =
    joinPath(data_dir(), name)

proc config_path(name: string): string =
    joinPath(db_dir(name), "config.txt")

proc index_path(name: string): string =
    joinPath(db_dir(name), "db.txt")

# ---------------------------------------------------------------------------
# Config I/O — line-based text format, no JSON dependency
# ---------------------------------------------------------------------------

proc default_config(): Config =
    let ign: seq[string] = DEFAULT_IGNORES
    let cfg: Config = Config(dirs: @[getEnv("HOME")], ignores: ign, follow_symlinks: false)
    return cfg

proc load_config(name: string): Config =
    let cpath: string = config_path(name)
    if not fileExists(cpath):
        echo(fmt"Error: database '{name}' not found.")
        echo(fmt"  Run: lolcate.ady create {name}")
        quit(1)
    var dirs: seq[string] = @[]
    var ignores: seq[string] = @[]
    var follow_symlinks: bool = false
    var section: string = ""
    block:
        let f = open(cpath, fmRead)
        defer: f.close()
        for line in f.lines:
            var stripped: string = line.strip()
            if stripped == "" or stripped.startsWith("#"):
                continue
            if stripped == "dirs:":
                section = "dirs"
            elif stripped == "ignores:":
                section = "ignores"
            elif stripped == "follow_symlinks:":
                section = "follow_symlinks"
            elif section == "dirs":
                dirs.add(stripped)
            elif section == "ignores":
                ignores.add(stripped)
            elif section == "follow_symlinks":
                follow_symlinks = (stripped == "true")
    let cfg: Config = Config(dirs: dirs, ignores: ignores, follow_symlinks: follow_symlinks)
    return cfg

proc save_config(name: string, cfg: Config) =
    block:
        let f = open(config_path(name), fmWrite)
        defer: f.close()
        f.write("# lolcate-ady config\n")
        f.write("dirs:\n")
        for d in cfg.dirs:
            f.write(d & "\n")
        f.write("ignores:\n")
        for ig in cfg.ignores:
            f.write(ig & "\n")
        f.write("follow_symlinks:\n")
        let fsym: string = (if cfg.follow_symlinks: "true" else: "false")
        f.write(fsym & "\n")

# ---------------------------------------------------------------------------
# Shell helpers  (shellLines: must be at function-body level, not in nested blocks)
# ---------------------------------------------------------------------------

proc find_files(root_dir: string): seq[string] =
    execCmdEx(fmt"find {root_dir} -type f")[0].splitLines().filterIt(it.len > 0)

proc list_dir(dir: string): seq[string] =
    execCmdEx(fmt"ls -1 {dir}")[0].splitLines().filterIt(it.len > 0)

# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

proc count_lines(path: string): int =
    var n: int = 0
    block:
        let f = open(path, fmRead)
        defer: f.close()
        for line in f.lines:
            n += 1
    return n

proc should_ignore(entry: string, ignores: seq[string]): bool =
    for pat in ignores:
        if entry == pat:
            return true
    return false

proc path_should_skip(fpath: string, ignores: seq[string]): bool =
    let parts: seq[string] = fpath.split("/")
    for part in parts:
        if should_ignore(part, ignores):
            return true
    return false

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

proc cmd_create(name: string) =
    let ddir: string = db_dir(name)
    if dirExists(ddir):
        echo(fmt"Database '{name}' already exists at {ddir}")
        return
    createDir(ddir)
    save_config(name, default_config())
    echo(fmt"Created database '{name}'")
    echo(fmt"  Config : {config_path(name)}")
    let home_dir = getEnv("HOME")
    echo(fmt"  Default scan dir: {home_dir}")
    echo(fmt"  Add more dirs:  lolcate.ady add-dir {name} <path>")
    echo(fmt"  Build index:    lolcate.ady update {name}")

proc cmd_update(name: string) =
    let cfg: Config = load_config(name)
    let ipath: string = index_path(name)
    var all_paths: seq[string] = @[]
    var t0: float = epochTime()
    for root_dir in cfg.dirs:
        if not dirExists(root_dir):
            echo(fmt"Warning: {root_dir} not found — skipping.")
            continue
        let paths: seq[string] = find_files(root_dir)
        for fpath in paths:
            if not path_should_skip(fpath, cfg.ignores):
                all_paths.add(fpath)
    let count: int = len(all_paths)
    block:
        let fout = open(ipath, fmWrite)
        defer: fout.close()
        for fpath in all_paths:
            fout.write(fpath & "\n")
    let elapsed: float = epochTime() - t0
    echo(fmt"Indexed {count} files in {elapsed:.2f}s")
    echo(fmt"  Index : {ipath}")

proc cmd_query(pattern: string, name: string) =
    let ipath: string = index_path(name)
    if not fileExists(ipath):
        echo(fmt"Index for '{name}' not built. Run: lolcate.ady update {name}")
        quit(1)
    var hits: int = 0
    block:
        let f = open(ipath, fmRead)
        defer: f.close()
        for line in f.lines:
            let path: string = line.strip()
            if contains(path, re("(?i)" & pattern)):
                echo(path)
                hits += 1
    if hits == 0:
        echo(fmt"(no matches for '{pattern}' in database '{name}')")

proc cmd_ls() =
    let ddir: string = data_dir()
    if not dirExists(ddir):
        echo("No databases. Create one: lolcate.ady create <name>")
        return
    var found: bool = false
    let raw_entries: seq[string] = list_dir(ddir)
    for entry in raw_entries.sorted:
        let epath: string = joinPath(ddir, entry)
        let cpath: string = joinPath(epath, "config.txt")
        if dirExists(epath) and fileExists(cpath):
            found = true
            let ipath: string = joinPath(epath, "db.txt")
            if fileExists(ipath):
                let n: int = count_lines(ipath)
                let sz: int = int(getFileSize(ipath))
                echo(fmt"  {entry:<20}  {n:>8} files   ({sz} bytes)")
            else:
                echo(fmt"  {entry:<20}  (not indexed yet)")
    if not found:
        echo("No databases. Create one: lolcate.ady create <name>")

proc cmd_info(name: string) =
    let ddir: string = db_dir(name)
    if not dirExists(ddir):
        echo(fmt"Database '{name}' not found.")
        quit(1)
    let cfg: Config = load_config(name)
    let ipath: string = index_path(name)
    echo(fmt"Database : {name}")
    echo(fmt"Location : {ddir}")
    echo(fmt"Dirs     :")
    for d in cfg.dirs:
        echo(fmt"  {d}")
    let ign_str: string = cfg.ignores.join(", ")
    let sym_str: string = (if cfg.follow_symlinks: "follow" else: "skip")
    echo(fmt"Ignores  : {ign_str}")
    echo(fmt"Symlinks : {sym_str}")
    if fileExists(ipath):
        let n: int = count_lines(ipath)
        let sz: int = int(getFileSize(ipath))
        echo(fmt"Index    : {ipath}")
        echo(fmt"Files    : {n}")
        echo(fmt"Size     : {sz} bytes")
    else:
        echo("Index    : not built yet")

proc cmd_add_dir(name: string, new_dir: string) =
    let ddir: string = db_dir(name)
    if not dirExists(ddir):
        echo(fmt"Database '{name}' not found. Run: lolcate.ady create {name}")
        quit(1)
    var expanded: string = new_dir
    if new_dir.startsWith("~"):
        expanded = getEnv("HOME") & new_dir[1..^1]
    let abs_expanded: string = absolutePath(expanded)
    var cfg: Config = load_config(name)
    if abs_expanded in cfg.dirs:
        echo(fmt"'{abs_expanded}' is already in database '{name}'")
        return
    cfg.dirs.add(abs_expanded)
    save_config(name, cfg)
    echo(fmt"Added '{abs_expanded}' to database '{name}'")
    echo(fmt"  Rebuild index with: lolcate.ady update {name}")

proc cmd_add_ignore(name: string, pat: string) =
    let ddir: string = db_dir(name)
    if not dirExists(ddir):
        echo(fmt"Database '{name}' not found. Run: lolcate.ady create {name}")
        quit(1)
    var cfg: Config = load_config(name)
    if pat in cfg.ignores:
        echo(fmt"'{pat}' is already in the ignore list for '{name}'")
        return
    cfg.ignores.add(pat)
    save_config(name, cfg)
    echo(fmt"Added ignore pattern '{pat}' to database '{name}'")

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

proc usage() =
    echo("lolcate.ady — file indexer (Adascript port of lolcate-rs)")
    echo("")
    echo("  lolcate.ady create <name>              create a new database")
    echo("  lolcate.ady update [name]              rebuild the index     (default: 'default')")
    echo("  lolcate.ady query  <pattern> [name]    search via regex      (default: 'default')")
    echo("  lolcate.ady ls                         list all databases")
    echo("  lolcate.ady info   [name]              show database info    (default: 'default')")
    echo("  lolcate.ady add-dir    <name> <path>   add a directory to scan")
    echo("  lolcate.ady add-ignore <name> <pat>    add an ignore pattern")
    quit(1)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if paramCount() < 1:
    usage()

let cmd: string = (if paramCount() >= 1: paramStr(1) else: "")
case cmd:
    of "create":
        if paramCount() < 2:
            usage()
        cmd_create((if paramCount() >= 2: paramStr(2) else: ""))
    of "update":
        cmd_update((if paramCount() >= 2: (if paramCount() >= 2: paramStr(2) else: "") else: DEFAULT_DB))
    of "query":
        if paramCount() < 2:
            usage()
        cmd_query((if paramCount() >= 2: paramStr(2) else: ""), (if paramCount() >= 3: (if paramCount() >= 3: paramStr(3) else: "") else: DEFAULT_DB))
    of "ls":
        cmd_ls()
    of "info":
        cmd_info((if paramCount() >= 2: (if paramCount() >= 2: paramStr(2) else: "") else: DEFAULT_DB))
    of "add-dir":
        if paramCount() < 3:
            usage()
        cmd_add_dir((if paramCount() >= 2: paramStr(2) else: ""), (if paramCount() >= 3: paramStr(3) else: ""))
    of "add-ignore":
        if paramCount() < 3:
            usage()
        cmd_add_ignore((if paramCount() >= 2: paramStr(2) else: ""), (if paramCount() >= 3: paramStr(3) else: ""))
    else:
        echo(fmt"Unknown command: '{cmd}'")
        usage()
