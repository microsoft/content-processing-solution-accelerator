#!/usr/bin/env bash
# =============================================================================
# test_configure_auth_preflight.sh
#
# Validates that configure_auth.sh --preflight-only exits with the correct code
# and outputs the expected diagnostic text for each insufficient-permission
# scenario. No real Azure credentials are required; az and azd are mocked.
#
# Usage:
#   bash infra/scripts/test_configure_auth_preflight.sh
#
# Exit code: 0 if all tests pass, 1 if any test fails.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/configure_auth.sh"

if [[ ! -f "$SUBJECT" ]]; then
  echo "❌ configure_auth.sh not found at $SUBJECT" >&2
  exit 1
fi

PASS_COUNT=0
FAIL_COUNT=0

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

# =============================================================================
# Mock: az
# Behaviour controlled by AZ_MOCK_SCENARIO environment variable.
# Scenarios: happy | no_auth | no_extension | no_rbac | no_entra_read |
#            no_container_app | insufficient_dir_role | consent_warn_only |
#            sp_login
# =============================================================================
cat > "$TEMP_DIR/az" << 'MOCK_AZ'
#!/usr/bin/env bash
SCENARIO="${AZ_MOCK_SCENARIO:-happy}"
ARGS="$*"
has() { printf '%s' "$ARGS" | grep -qF -- "$1"; }

# az account show (but NOT role assignment list — those share "account" in scope paths)
if has "account show" && ! has "role assignment"; then
  [[ "$SCENARIO" == "no_auth" ]] && exit 1
  has "tenantId"  && { echo "mock-tenant-id";            exit 0; }
  has "user.name" && { echo "sp-mock@service.principal"; exit 0; }
  echo "mock-sub-id-12345"; exit 0
fi

# az ad signed-in-user show
if has "signed-in-user"; then
  [[ "$SCENARIO" == "sp_login" ]] && exit 1
  echo "mock-user-object-id-abc123"; exit 0
fi

# az role assignment list
if has "role assignment list"; then
  [[ "$SCENARIO" == "no_rbac" ]] && { echo ""; exit 0; }
  echo "Contributor"; exit 0
fi

# az ad app list
if has "ad app list"; then
  [[ "$SCENARIO" == "no_entra_read" ]] && exit 1
  echo "mock-app-id-00001"; exit 0
fi

# az containerapp --help  (check before "containerapp show")
if has "containerapp" && has " --help"; then
  [[ "$SCENARIO" == "no_extension" ]] && exit 1
  exit 0
fi

# az containerapp show
if has "containerapp show"; then
  [[ "$SCENARIO" == "no_container_app" ]] && exit 1
  echo "ca-testenv-web"; exit 0
fi

# az rest  (Graph directory-roles query)
if has "rest"; then
  case "$SCENARIO" in
    insufficient_dir_role) echo "Directory Readers";        exit 0 ;;
    consent_warn_only)     echo "Application Administrator"; exit 0 ;;
    *)                     echo "Global Administrator";     exit 0 ;;
  esac
fi

# az ad app show — always "not found" in test context (force create path)
if has "ad app show"; then exit 1; fi

exit 0
MOCK_AZ
chmod +x "$TEMP_DIR/az"

# =============================================================================
# Mock: azd
# Behaviour controlled by AZD_MOCK_SCENARIO environment variable.
# Scenarios: happy | no_env
# =============================================================================
cat > "$TEMP_DIR/azd" << 'MOCK_AZD'
#!/usr/bin/env bash
SCENARIO="${AZD_MOCK_SCENARIO:-happy}"
ARGS="$*"

if printf '%s' "$ARGS" | grep -qF "env get-value"; then
  KEY="${@: -1}"   # the key name is always the last argument

  if [[ "$SCENARIO" == "no_env" ]]; then
    [[ "$KEY" == "AZURE_ENV_NAME" ]] && { echo "testenv"; exit 0; }
    echo ""; exit 0
  fi

  case "$KEY" in
    AZURE_ENV_NAME)         echo "testenv"                               ;;
    AZURE_RESOURCE_GROUP)   echo "mock-rg"                              ;;
    AZURE_SUBSCRIPTION_ID)  echo "mock-sub-id"                          ;;
    AZURE_TENANT_ID)        echo "mock-tenant-id"                       ;;
    CONTAINER_WEB_APP_NAME) echo "ca-testenv-web"                       ;;
    CONTAINER_WEB_APP_FQDN) echo "ca-testenv-web.azurecontainerapps.io" ;;
    CONTAINER_API_APP_NAME) echo "ca-testenv-api"                       ;;
    CONTAINER_API_APP_FQDN) echo "ca-testenv-api.azurecontainerapps.io" ;;
    *)                      echo ""                                     ;;
  esac
  exit 0
fi

# env set and any other azd commands — succeed silently
exit 0
MOCK_AZD
chmod +x "$TEMP_DIR/azd"

# =============================================================================
# Test runner
# =============================================================================
# run_test <label> <expected_exit> <expected_grep_text> <az_scenario> <azd_scenario>
run_test() {
  local name="$1"
  local expected_exit="$2"
  local expected_grep="${3:-}"
  local az_scenario="${4:-happy}"
  local azd_scenario="${5:-happy}"

  local output exit_code=0
  output=$(
    AZ_MOCK_SCENARIO="$az_scenario"   \
    AZD_MOCK_SCENARIO="$azd_scenario" \
    AZURE_SKIP_AUTH_SETUP=""           \
    PATH="$TEMP_DIR:$PATH"             \
    bash "$SUBJECT" --preflight-only 2>&1
  ) || exit_code=$?

  local ok=true reason=""
  if [[ "$exit_code" != "$expected_exit" ]]; then
    ok=false; reason="exit $exit_code (expected $expected_exit)"
  elif [[ -n "$expected_grep" ]] && ! printf '%s' "$output" | grep -qF -- "$expected_grep"; then
    ok=false; reason="expected text '$expected_grep' not in output"
  fi

  if [[ "$ok" == "true" ]]; then
    printf "  \u2705 %-60s\n" "$name"
    (( PASS_COUNT++ )) || true
  else
    printf "  \u274c %-60s  [%s]\n" "$name" "$reason"
    printf "     Last output lines:\n"
    printf '%s\n' "$output" | tail -4 | sed 's/^/       /'
    (( FAIL_COUNT++ )) || true
  fi
}

# =============================================================================
# Test scenarios
# =============================================================================
echo ""
echo "============================================================"
echo " configure_auth.sh — preflight permission scenario tests"
echo "============================================================"

# T01 — Happy path: every check should pass
run_test \
  "T01  Happy path: all checks pass" \
  0 "Preflight-only mode" \
  "happy" "happy"

# T02 — Check 1: Azure CLI not authenticated
run_test \
  "T02  Check 1: not authenticated" \
  1 "Azure CLI authenticated" \
  "no_auth" "happy"

# T03 — Check 2: required azd env values missing
run_test \
  "T03  Check 2: missing required azd env values" \
  1 "Required azd env values" \
  "happy" "no_env"

# T04 — Check 3: Azure Container Apps CLI extension absent
run_test \
  "T04  Check 3: containerapp CLI extension missing" \
  1 "Container Apps CLI" \
  "no_extension" "happy"

# T05 — Check 4: no Contributor or Owner role on resource group
run_test \
  "T05  Check 4: no RBAC Contributor/Owner on resource group" \
  1 "Contributor/Owner" \
  "no_rbac" "happy"

# T06 — Check 5: cannot read Entra app registrations
run_test \
  "T06  Check 5: cannot read Entra app registrations" \
  1 "Entra app registrations" \
  "no_entra_read" "happy"

# T07 — Check 6: target Container App is inaccessible
run_test \
  "T07  Check 6: Container App is inaccessible" \
  1 "Container App" \
  "no_container_app" "happy"

# T08 — Check 7: Entra role present but below Application Administrator
run_test \
  "T08  Check 7: insufficient Entra directory role (FAIL)" \
  1 "App-registration permission" \
  "insufficient_dir_role" "happy"

# T09 — Check 7: Application Administrator present, consent role absent (WARN, non-fatal)
run_test \
  "T09  Check 7: consent-only WARN is non-fatal (exit 0)" \
  0 "Admin-consent permission" \
  "consent_warn_only" "happy"

# T10 — Check 7: service principal login — directory-role check skipped (WARN, non-fatal)
run_test \
  "T10  Check 7: SP login — directory-role check skipped (exit 0)" \
  0 "directory-role check" \
  "sp_login" "happy"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================================"
printf "  Results: %d passed, %d failed\n" "$PASS_COUNT" "$FAIL_COUNT"
echo "============================================================"
echo ""

[[ $FAIL_COUNT -eq 0 ]] || exit 1
