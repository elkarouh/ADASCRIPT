# EXAMPLES/LITTLE_PAGES: a filtered list as one small page per filter.
#
#   make pages      write build/recent.html, popular.html, all.html
#   make open       the same, then open build/recent.html in the browser
#   make clean

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || echo true)

.PHONY: pages open clean

pages:
	$(ADY2NIM) c -r little_pages.ady build

open: pages
	-$(OPEN) build/recent.html

clean:
	rm -rf build little_pages
