#!/bin/bash
set -euo pipefail

# Only needed in remote (Claude Code on the web) sessions — local sessions
# already have credentials.json/token.json on disk from the manual setup.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

DEST_DIR="$CLAUDE_PROJECT_DIR/google-workspace-access"
mkdir -p "$DEST_DIR"

# GOOGLE_SHEETS_CREDENTIALS_JSON / GOOGLE_SHEETS_TOKEN_JSON are expected to be
# set as environment secrets on this environment (Settings -> Claude Code ->
# Environment/Secrets). They hold the raw contents of credentials.json and
# token.json produced by google-workspace-access/setup_oauth.py.
if [ -n "${GOOGLE_SHEETS_CREDENTIALS_JSON:-}" ]; then
  printf '%s' "$GOOGLE_SHEETS_CREDENTIALS_JSON" > "$DEST_DIR/credentials.json"
fi

if [ -n "${GOOGLE_SHEETS_TOKEN_JSON:-}" ]; then
  printf '%s' "$GOOGLE_SHEETS_TOKEN_JSON" > "$DEST_DIR/token.json"
fi

if ! command -v uv >/dev/null 2>&1; then
  pip install --quiet uv
fi
