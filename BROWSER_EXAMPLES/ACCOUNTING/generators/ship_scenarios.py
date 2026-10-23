#!/usr/bin/env python3
"""ship_scenarios -- writes frontend/shipped.ady: accounting.conf and scenarios/*.books as texts,
for the page alone (frontend/frontend_server.ady), which has no files to read them from.

Run (from BROWSER_EXAMPLES/ACCOUNTING; make alone does): python3 generators/ship_scenarios.py [frontend/shipped.ady]
"""
import sys
from pathlib import Path


def literal(text: str, where: Path) -> str:
    """TEXT as an Adascript string literal: between triple quotes, which it must not hold."""
    if '"""' in text or "\\" in text or text.endswith('"'):
        sys.exit(f"{where}: has a triple quote, a backslash or ends with a quote, which a literal cannot hold")
    return '"""' + text + '"""'


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/shipped.ady")
    lines = ['"""shipped -- accounting.conf and scenarios/*.books, as texts, for the page alone',
             '(frontend_server.ady). Written by generators/ship_scenarios.py: do not edit."""',
             "",
             f"const CONFIG_TEXT: str = {literal(Path('accounting.conf').read_text(), Path('accounting.conf'))}",
             "",
             "# A scenario's name, then its text, for each one.",
             "const SHIPPED: []str = ["]
    for books in sorted(Path("scenarios").glob("*.books")):
        lines.append(f'    "{books.stem}", {literal(books.read_text(), books)},')
    lines.append("]")
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
