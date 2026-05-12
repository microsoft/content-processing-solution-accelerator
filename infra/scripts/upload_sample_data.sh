#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed -i 's/\r$//' "$SCRIPT_DIR/post_deployment.sh"
chmod +x "$SCRIPT_DIR/post_deployment.sh"

POST_DEPLOYMENT_MODE=sample-data bash "$SCRIPT_DIR/post_deployment.sh"
