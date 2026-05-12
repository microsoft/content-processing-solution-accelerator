#!/usr/bin/env bash
# run_post_deployment.sh
#
# Manual post-deployment setup for Content Processing Solution Accelerator.
# Run this script AFTER `azd up` has finished provisioning infrastructure.
#
# Steps executed:
#   Step 1 – Schema registration                          (register_schemas.sh)
#   Step 2 – Sample data upload                          (upload_sample_data.sh)
#   Step 3 – Entra ID authentication setup               (setup_auth.sh)
#
# Skip individual steps:
#   SKIP_SCHEMA_REGISTRATION=true ./infra/scripts/run_post_deployment.sh
#   SKIP_SAMPLE_DATA_UPLOAD=true  ./infra/scripts/run_post_deployment.sh
#   SKIP_AUTH_SETUP=true          ./infra/scripts/run_post_deployment.sh
#
# To skip auth setup permanently:
#   azd env set AZURE_SKIP_AUTH_SETUP true
#
# Usage (from repo root):
#   bash ./infra/scripts/run_post_deployment.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_banner() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║      Content Processing Solution Accelerator                 ║"
  echo "║      Post-Deployment Manual Setup                            ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  This script runs post-deployment steps that are intentionally"
  echo "  decoupled from 'azd up' so they can be executed separately,"
  echo "  retried independently, and skipped when permissions are limited."
  echo ""
}

print_step() {
  local num="$1"
  local title="$2"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Step $num: $title"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

step_ok()   { echo ""; echo "  ✅ Step $1 completed successfully."; }
step_skip() { echo ""; echo "  ⏭️  Step $1 skipped (${2})."; }
step_fail() { echo ""; echo "  ❌ Step $1 failed — see errors above."; }

print_banner

if ! command -v azd &>/dev/null; then
  echo "❌ Azure Developer CLI (azd) is not installed or not on PATH." >&2
  echo "   Install it from https://aka.ms/install-azd, then re-run." >&2
  exit 1
fi

if ! azd env get-values &>/dev/null; then
  echo "❌ No active azd environment found." >&2
  echo "   Run 'azd env list' and 'azd env select <name>', then re-run." >&2
  exit 1
fi

echo "  Active azd environment : $(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo '<unknown>')"
echo "  Resource group         : $(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null || echo '<unknown>')"
echo "  Subscription           : $(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null || echo '<unknown>')"
echo ""

STEP1_SCRIPT="$SCRIPT_DIR/register_schemas.sh"

print_step 1 "Schema registration"
echo "  Script : $STEP1_SCRIPT"
echo "  Purpose: Register sample schemas, create the schema set, and link schemas to it."
echo ""

if [[ "${SKIP_SCHEMA_REGISTRATION:-false}" == "true" ]]; then
  step_skip 1 "SKIP_SCHEMA_REGISTRATION=true"
else
  if [[ ! -f "$STEP1_SCRIPT" ]]; then
    echo "  ❌ Script not found: $STEP1_SCRIPT" >&2
    exit 1
  fi

  sed -i 's/\r$//' "$STEP1_SCRIPT"
  chmod +x "$STEP1_SCRIPT"

  STEP1_EXIT=0
  bash "$STEP1_SCRIPT" || STEP1_EXIT=$?

  if [[ $STEP1_EXIT -eq 0 ]]; then
    step_ok 1
  else
    step_fail 1
    echo "  To retry: bash $STEP1_SCRIPT"
    echo "  To skip:  SKIP_SCHEMA_REGISTRATION=true bash $SCRIPT_DIR/run_post_deployment.sh"
    exit $STEP1_EXIT
  fi
fi

STEP2_SCRIPT="$SCRIPT_DIR/upload_sample_data.sh"

print_step 2 "Sample data upload"
echo "  Script : $STEP2_SCRIPT"
echo "  Purpose: Create sample claim batches, upload sample bundles, and submit them for processing."
echo ""

if [[ "${SKIP_SAMPLE_DATA_UPLOAD:-false}" == "true" ]]; then
  step_skip 2 "SKIP_SAMPLE_DATA_UPLOAD=true"
else
  if [[ ! -f "$STEP2_SCRIPT" ]]; then
    echo "  ❌ Script not found: $STEP2_SCRIPT" >&2
    exit 1
  fi

  sed -i 's/\r$//' "$STEP2_SCRIPT"
  chmod +x "$STEP2_SCRIPT"

  STEP2_EXIT=0
  bash "$STEP2_SCRIPT" || STEP2_EXIT=$?

  if [[ $STEP2_EXIT -eq 0 ]]; then
    step_ok 2
  else
    step_fail 2
    echo "  To retry: bash $STEP2_SCRIPT"
    echo "  To skip:  SKIP_SAMPLE_DATA_UPLOAD=true bash $SCRIPT_DIR/run_post_deployment.sh"
    exit $STEP2_EXIT
  fi
fi

STEP3_SCRIPT="$SCRIPT_DIR/setup_auth.sh"

print_step 3 "Entra ID authentication setup (app registrations + EasyAuth)"
echo "  Script : $STEP3_SCRIPT"
echo "  Purpose: Create app registrations for Web + API, configure EasyAuth,"
echo "           grant admin consent, and wire environment variables."
echo ""
echo "  Required permissions:"
echo "    • Application Administrator (or higher) — to create app registrations"
echo "    • Cloud Application Administrator / Global Administrator — to grant admin consent"
echo "    • Contributor on resource group — to update Container Apps"
echo ""
echo "  To skip this step:"
echo "    SKIP_AUTH_SETUP=true bash $SCRIPT_DIR/run_post_deployment.sh"
echo "    — or —"
echo "    azd env set AZURE_SKIP_AUTH_SETUP true"
echo "    then re-run setup_auth.sh later when permissions are available."
echo ""

AZURE_SKIP_AUTH_SETUP_VAL="${AZURE_SKIP_AUTH_SETUP:-$(azd env get-value AZURE_SKIP_AUTH_SETUP 2>/dev/null || echo "false")}"

if [[ "${SKIP_AUTH_SETUP:-false}" == "true" ]] || [[ "$AZURE_SKIP_AUTH_SETUP_VAL" == "true" ]]; then
  step_skip 3 "SKIP_AUTH_SETUP=true or AZURE_SKIP_AUTH_SETUP=true"
  echo "  Run manually when permissions are available:"
  echo "    bash $STEP3_SCRIPT"
else
  if [[ ! -f "$STEP3_SCRIPT" ]]; then
    echo "  ❌ Script not found: $STEP3_SCRIPT" >&2
    exit 1
  fi

  sed -i 's/\r$//' "$STEP3_SCRIPT"
  chmod +x "$STEP3_SCRIPT"

  STEP3_EXIT=0
  bash "$STEP3_SCRIPT" || STEP3_EXIT=$?

  if [[ $STEP3_EXIT -eq 0 ]]; then
    step_ok 3
  else
    step_fail 3
    echo "  To retry auth setup: bash $STEP3_SCRIPT"
    echo "  For manual portal steps: docs/ConfigureAppAuthentication.md"
    exit $STEP3_EXIT
  fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Post-deployment setup complete.                             ║"
echo "║                                                              ║"
echo "║  Next steps:                                                 ║"
echo "║   1. Wait up to 10 minutes for EasyAuth to propagate.       ║"
echo "║   2. Open the Web App URL and sign in.                       ║"
echo "║   3. Verify the two sample claim bundles appear in the UI.  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
