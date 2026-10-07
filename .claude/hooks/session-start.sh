#!/bin/bash
# SessionStart hook: install the toolchain `make test` needs: Nim (so ady2nim
# can compile .ady files), libpcre3 (geo_server), ksh93/zsh/emacs (shell and
# editor tests) and the npm deps of the VS Code grammar test. See requirements.txt for the full
# dependency list. Idempotent and safe to re-run.
set -euo pipefail

# Only run in Claude Code on the web (remote) sessions; local machines are
# assumed to already have their toolchain set up.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

NIM_VERSION="2.2.10"   # pinned tested version (see requirements.txt)

# Persist Nim's bin dir on PATH for the rest of the session.
echo 'export PATH="$HOME/.nimble/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
export PATH="$HOME/.nimble/bin:$PATH"

# Idempotent: skip the (slow) Nim install if the pinned Nim is already present.
if command -v nim >/dev/null 2>&1 && nim --version 2>/dev/null | grep -q "$NIM_VERSION"; then
  echo "Nim $NIM_VERSION already installed."
else
  # Install Nim via choosenim, non-interactively, and pin the tested version.
  export CHOOSENIM_NO_ANALYTICS=1
  curl -fsSL https://nim-lang.org/choosenim/init.sh | sh -s -- -y
  "$HOME/.nimble/bin/choosenim" "$NIM_VERSION"
  nim --version | head -1
fi

# karax: the html: blocks of EXAMPLES/HTML (best effort).
if [ ! -d "$HOME/.nimble/pkgs2" ] || ! ls "$HOME"/.nimble/pkgs2 2>/dev/null | grep -q '^karax-'; then
  nimble install -y karax >/dev/null 2>&1 || echo "warning: could not install karax"
fi

# System packages used by tests (best effort: a failure must not break the
# session). Only apt-get when something is actually missing.
missing=()
dpkg -s libpcre3 >/dev/null 2>&1 || missing+=(libpcre3)
command -v ksh93 >/dev/null 2>&1 || missing+=(ksh)
command -v zsh >/dev/null 2>&1 || missing+=(zsh)
command -v emacs >/dev/null 2>&1 || missing+=(emacs-nox)
if [ ${#missing[@]} -gt 0 ]; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  echo "Installing: ${missing[*]}"
  { $SUDO apt-get update -qq || true; \
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${missing[@]}"; } >/dev/null 2>&1 \
    || echo "warning: could not install ${missing[*]}"
fi

# Node deps for the VS Code grammar test (LSP/test/run_editor_tests.sh).
if [ -f "${CLAUDE_PROJECT_DIR:-.}"/LSP/test/package.json ] && [ ! -d "${CLAUDE_PROJECT_DIR:-.}"/LSP/test/node_modules ] && command -v npm >/dev/null 2>&1; then
  (cd "${CLAUDE_PROJECT_DIR:-.}"/LSP/test && npm install --no-audit --no-fund --silent >/dev/null 2>&1) \
    || echo "warning: npm install in LSP/test failed"
fi
