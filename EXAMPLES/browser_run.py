"""Run a script built with `ady2nim js` in a real browser and print what it
printed: `python3 browser_run.py prog.js`. The page is a blank one holding the
script. Chromium through Playwright; CHROMIUM names its executable where
Playwright's own download is not the one installed."""
import os
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

script = pathlib.Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as d:
    page_file = pathlib.Path(d) / "page.html"
    page_file.write_text(f'<!doctype html><html><body><script src="{script.as_uri()}"></script></body></html>')
    with sync_playwright() as p:
        exe = os.environ.get("CHROMIUM")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("console", lambda m: print(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_file.as_uri())
        page.wait_for_timeout(500)
        browser.close()
for e in errors:
    print(e, file=sys.stderr)
sys.exit(1 if errors else 0)
