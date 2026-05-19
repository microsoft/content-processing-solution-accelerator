#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! tmp_file="$(mktemp "${TMPDIR:-/tmp}/cpsa-sample.XXXXXX" 2>/dev/null)"; then
  tmp_file="$(mktemp -t cpsa-sample.XXXXXX 2>/dev/null)" || {
    echo "Failed to create temp file" >&2
    exit 1
  }
fi
if ! tr -d '\r' < "$SCRIPT_DIR/post_deployment.sh" > "$tmp_file"; then
  rm -f "$tmp_file"
  echo "Failed to normalize line endings for: $SCRIPT_DIR/post_deployment.sh" >&2
  exit 1
fi
mv "$tmp_file" "$SCRIPT_DIR/post_deployment.sh"
chmod +x "$SCRIPT_DIR/post_deployment.sh"

POST_DEPLOYMENT_MODE=sample-data bash "$SCRIPT_DIR/post_deployment.sh"
