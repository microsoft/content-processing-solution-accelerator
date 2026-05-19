#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp_file="$(mktemp)" || { echo "Failed to create temp file" >&2; exit 1; }
if ! tr -d '\r' < "$SCRIPT_DIR/configure_auth.sh" > "$tmp_file"; then
  rm -f "$tmp_file"
  echo "Failed to normalize line endings for: $SCRIPT_DIR/configure_auth.sh" >&2
  exit 1
fi
mv "$tmp_file" "$SCRIPT_DIR/configure_auth.sh"
chmod +x "$SCRIPT_DIR/configure_auth.sh"

bash "$SCRIPT_DIR/configure_auth.sh" "$@"