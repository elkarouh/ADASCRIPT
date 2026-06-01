#!/bin/bash
# SessionStart hook: install the Nim toolchain so py2nim can compile .ady files
# (e.g. `make test`, `py2nim c ...`). See requirements.txt for the full
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

# Idempotent: skip the (slow) install if the pinned Nim is already present.
if command -v nim >/dev/null 2>&1 && nim --version 2>/dev/null | grep -q "$NIM_VERSION"; then
  echo "Nim $NIM_VERSION already installed."
  exit 0
fi

# Install Nim via choosenim, non-interactively, and pin the tested version.
export CHOOSENIM_NO_ANALYTICS=1
curl -fsSL https://nim-lang.org/choosenim/init.sh | sh -s -- -y
"$HOME/.nimble/bin/choosenim" "$NIM_VERSION"

nim --version | head -1
