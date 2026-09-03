#!/usr/bin/env bash
#
# Build the Adascript Book as a styled HTML and/or PDF.
#
# Usage:
#   ./build-pdf.sh                  # -> adascript-book.html (self-contained)
#   ./build-pdf.sh --pdf            # -> adascript-book.pdf  (needs weasyprint)
#   ./build-pdf.sh out.pdf          # -> out.pdf
#   ./build-pdf.sh out.html         # -> out.html
#
# Requirements: pandoc (>= 3.0)
# For PDF:      weasyprint <= 52.5 (pip install 'weasyprint==52.5')
#               On systems with pango < 1.44, weasyprint >= 53 will crash.

set -euo pipefail

cd "$(dirname "$0")"

OUT=""
WANT_PDF=0
for arg in "$@"; do
    case $arg in
        --pdf) WANT_PDF=1 ;;
        *)     OUT=$arg ;;
    esac
done

if [ -z "$OUT" ]; then
    OUT=$([ "$WANT_PDF" -eq 1 ] && echo adascript-book.pdf || echo adascript-book.html)
fi
case $OUT in *.pdf) WANT_PDF=1 ;; esac

CHAPTERS=(
    README.md
    01-introduction.md
    02-types-and-declarations.md
    03-enums-sets-and-tick-attributes.md
    04-tuples-records-and-variants.md
    05-pattern-matching.md
    06-collections-and-iteration.md
    07-regex.md
    08-functions-and-generators.md
    09-classes-and-generics.md
    10-optionals.md
    11-shell-and-scripting.md
    12-two-backends.md
    13-case-studies.md
    14-appendix.md
)

command -v pandoc >/dev/null 2>&1 || { echo "error: pandoc not found" >&2; exit 1; }

# --- Write CSS to a temp file (shared by both HTML and PDF paths) ----------
CSS_FILE=.book-style.css
cat > "$CSS_FILE" <<'CSS'
@page {
    size: A4;
    margin: 2.5cm 2cm;
    @top-left  { content: string(chapter); font-size: 9pt; color: #666; }
    @top-right { content: counter(page);   font-size: 9pt; color: #666; }
}
@page :first { @top-left { content: none; } @top-right { content: none; } }

@media screen {
    body { max-width: 50em; margin: 2em auto; padding: 0 1em; }
}

body {
    font-family: "DejaVu Serif", Georgia, "Times New Roman", serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #222;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "DejaVu Sans", Helvetica, Arial, sans-serif;
    color: #1a1a1a;
    page-break-after: avoid;
}

h1 {
    font-size: 22pt;
    border-bottom: 2pt solid #333;
    padding-bottom: 6pt;
    margin-top: 2em;
    string-set: chapter content();
    page-break-before: always;
}
h1:first-of-type { page-break-before: avoid; }

h2 {
    font-size: 16pt;
    border-bottom: 0.5pt solid #ccc;
    padding-bottom: 3pt;
    margin-top: 1.5em;
}

h3 { font-size: 13pt; margin-top: 1.2em; }

pre, code {
    font-family: "Fira Code", "DejaVu Sans Mono", Consolas, "Courier New", monospace;
    font-size: 9pt;
}

pre {
    background: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 12px;
    page-break-inside: avoid;
    line-height: 1.4;
}

code { background: #f0f0f0; padding: 1px 4px; border-radius: 2px; }
pre code { background: none; padding: 0; border-radius: 0; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; }
th {
    background: #f0f0f0;
    font-family: "DejaVu Sans", Helvetica, sans-serif;
    font-weight: bold;
}
tr:nth-child(even) { background: #fafafa; }

nav#TOC { page-break-after: always; padding: 1em 0; }
nav#TOC ul { list-style: none; padding-left: 0; }
nav#TOC > ul > li { margin: 0.5em 0; font-weight: bold; }
nav#TOC > ul > li > ul > li { font-weight: normal; margin: 0.2em 0; padding-left: 1.5em; }
nav#TOC a { text-decoration: none; color: #333; }

a { color: #1a5276; text-decoration: none; }
a:hover { text-decoration: underline; }

blockquote {
    border-left: 3px solid #999;
    margin: 1em 0;
    padding: 0.5em 1em;
    color: #555;
    background: #fafafa;
    page-break-inside: avoid;
}

header#title-block-header {
    text-align: center;
    padding: 4cm 0 2cm 0;
    page-break-after: always;
}
header#title-block-header h1.title {
    font-size: 28pt; border: none; page-break-before: avoid;
}
header#title-block-header p.subtitle {
    font-size: 14pt; color: #555; font-style: italic; margin-top: 0.5em;
}
header#title-block-header p.author { font-size: 12pt; margin-top: 2em; }
header#title-block-header p.date { font-size: 10pt; color: #888; }

hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
p, li { orphans: 3; widows: 3; }
CSS

echo "Building $OUT ..."

# --- Common pandoc args ----------------------------------------------------
PANDOC_ARGS=(
    "${CHAPTERS[@]}"
    --standalone
    --toc
    --toc-depth=2
    --number-sections
    --shift-heading-level-by=-1
    --highlight-style=tango
    --metadata title="The Adascript Book"
    --metadata subtitle="One source, two targets: type-safe scripting from Python to Nim"
    --metadata author="E. Karouh"
    --metadata date="$(date +%Y-%m-%d)"
    --css="$CSS_FILE"
    -t html5
)

if [ "$WANT_PDF" -eq 1 ]; then
    # For PDF: generate non-embedded HTML, then convert with weasyprint
    HTML_TMP=.book-tmp.html
    pandoc "${PANDOC_ARGS[@]}" -o "$HTML_TMP"

    # Find a working weasyprint
    WEASY=""
    for candidate in \
        /auto/local_build/dhws149/disk1/DOWNLOADS/uv/python/cpython-3.13.7-linux-x86_64-gnu/bin/weasyprint \
        weasyprint; do
        command -v "$candidate" >/dev/null 2>&1 && { WEASY=$candidate; break; }
    done

    if [ -n "$WEASY" ]; then
        echo "  weasyprint: $($WEASY --version 2>&1)"
        "$WEASY" "$HTML_TMP" "$OUT" --stylesheet "$CSS_FILE" 2>&1 | grep -v '^WARNING' || true
        rm -f "$HTML_TMP"
    else
        HTML_FALLBACK=${OUT%.pdf}.html
        mv "$HTML_TMP" "$HTML_FALLBACK"
        echo "  weasyprint not found — saved print-ready HTML instead."
        echo "  Open $HTML_FALLBACK in a browser and use File > Print > Save as PDF."
        OUT=$HTML_FALLBACK
    fi
    rm -f "$CSS_FILE"
else
    # For HTML: embed everything into a single file
    pandoc "${PANDOC_ARGS[@]}" --embed-resources -o "$OUT"
    rm -f "$CSS_FILE"
fi

ls -lh "$OUT" 2>/dev/null && echo "Done: $OUT"
