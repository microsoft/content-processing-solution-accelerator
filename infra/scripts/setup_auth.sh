#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed -i 's/\r$//' "$SCRIPT_DIR/configure_auth.sh"
chmod +x "$SCRIPT_DIR/configure_auth.sh"

bash "$SCRIPT_DIR/configure_auth.sh" "$@"