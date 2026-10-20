# EXAMPLES/LITTLE_PAGES: a filtered list as one small page per filter.
#
#   make pages      write build/recent.html, popular.html, all.html
#   make open       the same, then open build/recent.html in the browser
#   make clean

ADY2NIM ?= ady2nim
OPEN    ?= $(shell command -v xdg-open || command -v open || command -v wslview || { command -v powershell.exe >/dev/null && echo 'powershell.exe -NoProfile -Command Start-Process'; } || echo true)
# On WSL, PowerShell's Start-Process opens the default browser, given a file: URL.
WINPATH  = $(if $(findstring powershell.exe,$(OPEN)),$(shell echo file:$$(wslpath -m $(1))),$(1))

.PHONY: pages open clean

pages:
	$(ADY2NIM) c -r little_pages.ady build

open: pages
	-$(OPEN) "$(call WINPATH,$(CURDIR)/build/recent.html)"

clean:
	rm -rf build little_pages
