#!/usr/bin/env bash
#
# Build the Adascript Book as a styled HTML (and optionally PDF).
#
# Usage:
#   ./build-pdf.sh                  # -> adascript-book.html
#   ./build-pdf.sh --pdf            # -> adascript-book.pdf  (needs weasyprint)
#   ./build-pdf.sh out.pdf          # -> out.pdf
#   ./build-pdf.sh out.html         # -> out.html
#
# The HTML output is self-contained and print-ready.  Open it in a browser
# and use File > Print > Save as PDF if weasyprint is not available.
#
# Requirements: pandoc (>= 3.0)
# Optional:     weasyprint (pip install weasyprint) — for direct PDF output

set -euo pipefail

cd "$(dirname "$0")"

# Parse args
OUT=""
WANT_PDF=0
for arg in "$@"; do
    case $arg in
        --pdf) WANT_PDF=1 ;;
        *)     OUT=$arg ;;
    esac
done

# Determine output format from extension or --pdf flag
if [ -z "$OUT" ]; then
    if [ "$WANT_PDF" -eq 1 ]; then
        OUT=adascript-book.pdf
    else
        OUT=adascript-book.html
    fi
fi

case $OUT in
    *.pdf) WANT_PDF=1 ;;
esac

# Ordered chapter list
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

echo "Building $OUT ..."

# Determine HTML output path
if [ "$WANT_PDF" -eq 1 ]; then
    HTML_OUT=.book-tmp.html
else
    HTML_OUT=$OUT
fi

# pandoc -> self-contained HTML with embedded CSS and print styles
pandoc "${CHAPTERS[@]}" \
    --standalone \
    --embed-resources \
    --toc \
    --toc-depth=2 \
    --number-sections \
    --shift-heading-level-by=-1 \
    --highlight-style=tango \
    --metadata title="The Adascript Book" \
    --metadata subtitle="One source, two targets: type-safe scripting from Python to Nim" \
    --metadata author="E. Karouh" \
    --metadata date="$(date +%Y-%m-%d)" \
    --css=/dev/stdin \
    -t html5 \
    -o "$HTML_OUT" <<'CSS'
/* --- Page layout (for print / weasyprint) --- */
@page {
    size: A4;
    margin: 2.5cm 2cm;
    @top-left  { content: string(chapter); font-size: 9pt; color: #666; }
    @top-right { content: counter(page);   font-size: 9pt; color: #666; }
}
@page :first { @top-left { content: none; } @top-right { content: none; } }

/* --- Screen layout --- */
@media screen {
    body { max-width: 50em; margin: 2em auto; padding: 0 1em; }
}

/* --- Typography --- */
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

/* --- Code blocks --- */
pre, code {
    font-family: "Fira Code", "DejaVu Sans Mono", Consolas, "Courier New", monospace;
    font-size: 9pt;
}

pre {
    background: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 12px;
    overflow-x: auto;
    page-break-inside: avoid;
    line-height: 1.4;
}

code {
    background: #f0f0f0;
    padding: 1px 4px;
    border-radius: 2px;
}

pre code {
    background: none;
    padding: 0;
    border-radius: 0;
}

/* --- Tables --- */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #ccc;
    padding: 5px 8px;
    text-align: left;
}

th {
    background: #f0f0f0;
    font-family: "DejaVu Sans", Helvetica, sans-serif;
    font-weight: bold;
}

tr:nth-child(even) { background: #fafafa; }

/* --- Table of contents --- */
nav#TOC {
    page-break-after: always;
    padding: 1em 0;
}

nav#TOC ul { list-style: none; padding-left: 0; }
nav#TOC > ul > li { margin: 0.5em 0; font-weight: bold; }
nav#TOC > ul > li > ul > li { font-weight: normal; margin: 0.2em 0; padding-left: 1.5em; }

nav#TOC a { text-decoration: none; color: #333; }

/* --- Links --- */
a { color: #1a5276; text-decoration: none; }
a:hover { text-decoration: underline; }

/* --- Blockquotes --- */
blockquote {
    border-left: 3px solid #999;
    margin: 1em 0;
    padding: 0.5em 1em;
    color: #555;
    background: #fafafa;
    page-break-inside: avoid;
}

/* --- Title page --- */
header#title-block-header {
    text-align: center;
    padding: 4cm 0 2cm 0;
    page-break-after: always;
}

header#title-block-header h1.title {
    font-size: 28pt;
    border: none;
    page-break-before: avoid;
}

header#title-block-header p.subtitle {
    font-size: 14pt;
    color: #555;
    font-style: italic;
    margin-top: 0.5em;
}

header#title-block-header p.author { font-size: 12pt; margin-top: 2em; }
header#title-block-header p.date { font-size: 10pt; color: #888; }

/* --- Misc --- */
hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
p, li { orphans: 3; widows: 3; }
CSS

if [ "$WANT_PDF" -eq 1 ]; then
    if command -v weasyprint >/dev/null 2>&1; then
        echo "  Converting HTML to PDF via weasyprint..."
        weasyprint "$HTML_OUT" "$OUT"
        rm -f "$HTML_OUT"
    else
        # Fallback: rename HTML and tell the user
        HTML_FALLBACK=${OUT%.pdf}.html
        mv "$HTML_OUT" "$HTML_FALLBACK"
        echo ""
        echo "  weasyprint not found — saved print-ready HTML instead."
        echo "  Open $HTML_FALLBACK in a browser and use File > Print > Save as PDF."
        echo ""
        OUT=$HTML_FALLBACK
    fi
fi

echo "Done: $OUT ($(du -h "$OUT" | cut -f1))"
