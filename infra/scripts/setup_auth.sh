#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="${ORIGINAL_SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
tmp_file=""
cleanup() {
  if [[ -n "$tmp_file" ]]; then
    rm -f "$tmp_file" || true
  fi
}
trap cleanup EXIT

if ! tmp_file="$(mktemp "${TMPDIR:-/tmp}/cpsa-auth.XXXXXX" 2>/dev/null)"; then
  tmp_file="$(mktemp -t cpsa-auth.XXXXXX 2>/dev/null)" || {
    echo "Failed to create temp file" >&2
    exit 1
  }
fi
if ! tr -d '\r' < "$SCRIPT_DIR/configure_auth.sh" > "$tmp_file"; then
  rm -f "$tmp_file"
  echo "Failed to normalize line endings for: $SCRIPT_DIR/configure_auth.sh" >&2
  exit 1
fi
chmod +x "$tmp_file"
ORIGINAL_SCRIPT_DIR="$SCRIPT_DIR" bash "$tmp_file" "$@"