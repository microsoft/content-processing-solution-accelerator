#!/usr/bin/env bash
# Automates the app registration + EasyAuth configuration that is otherwise
# performed manually per docs/ConfigureAppAuthentication.md.
#
# Idempotent: safe to re-run. Reuses existing app registrations and container
# app secrets where possible.
#
# Skip with: azd env set AZURE_SKIP_AUTH_SETUP true

set -euo pipefail

if [[ "${AZURE_SKIP_AUTH_SETUP:-false}" == "true" ]]; then
  echo "⏭️  AZURE_SKIP_AUTH_SETUP=true — skipping auth configuration."
  exit 0
fi

PREFLIGHT_ONLY=false
[[ "${1:-}" == "--preflight-only" ]] && PREFLIGHT_ONLY=true

if [[ "$PREFLIGHT_ONLY" == "true" ]]; then
  echo ""
  echo "============================================================"
  echo "🔍 Preflight permission check (read-only — no changes made)"
  echo "============================================================"
else
  echo ""
  echo "============================================================"
  echo "🔐 Configuring Entra ID authentication (Web + API)"
  echo "============================================================"
fi

if ! command -v az >/dev/null 2>&1; then
  echo "❌ Azure CLI (az) is not installed or not on PATH." >&2
  echo "   Install it from https://aka.ms/installazurecli, then re-run." >&2
  exit 1
fi

if ! command -v azd >/dev/null 2>&1; then
  echo "❌ Azure Developer CLI (azd) is not installed or not on PATH." >&2
  echo "   Install it from https://aka.ms/install-azd, then re-run." >&2
  exit 1
fi

if ! azd env get-values >/dev/null 2>&1; then
  echo "❌ No active azd environment found." >&2
  echo "   Run 'azd env list' and 'azd env select <name>', then re-run." >&2
  exit 1
fi

# --- Load values from azd env -------------------------------------------------
ENV_NAME="$(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo "")"
RESOURCE_GROUP="$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null || true)"
SUBSCRIPTION_ID="$(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null || true)"
TENANT_ID="$(az account show --query tenantId -o tsv 2>/dev/null || true)"
if [[ -z "$TENANT_ID" ]]; then
  TENANT_ID="$(azd env get-value AZURE_TENANT_ID 2>/dev/null || true)"
fi
# (Preflight Check 1 will catch missing authentication with a clear error message)
WEB_NAME="$(azd env get-value CONTAINER_WEB_APP_NAME 2>/dev/null || true)"
WEB_FQDN="$(azd env get-value CONTAINER_WEB_APP_FQDN 2>/dev/null || true)"
API_NAME="$(azd env get-value CONTAINER_API_APP_NAME 2>/dev/null || true)"
API_FQDN="$(azd env get-value CONTAINER_API_APP_FQDN 2>/dev/null || true)"

WEB_APP_DISPLAY_NAME="${ENV_NAME:-cps}-web-app"
API_APP_DISPLAY_NAME="${ENV_NAME:-cps}-api-app"

WEB_URL="https://${WEB_FQDN}"
API_URL="https://${API_FQDN}"
WEB_AUTH_CALLBACK="${WEB_URL}/.auth/login/aad/callback"
API_AUTH_CALLBACK="${API_URL}/.auth/login/aad/callback"

# Graph delegated User.Read permission
GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"
GRAPH_USER_READ_SCOPE_ID="e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read (delegated)
CONSENT_PRECHECK_OK=true

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

# Find app reg by previously persisted appId in azd env, else by displayName.
# Returns: appId on stdout, empty if not found.
find_app_by_env_or_name() {
  local env_key="$1"
  local display_name="$2"
  local app_id
  app_id="$(azd env get-value "$env_key" 2>/dev/null || echo "")"
  if [[ -n "$app_id" ]] && az ad app show --id "$app_id" >/dev/null 2>&1; then
    echo "$app_id"
    return 0
  fi
  # Fall back to displayName
  local ids
  ids="$(az ad app list --display-name "$display_name" --query "[].appId" -o tsv 2>/dev/null || true)"
  local count
  count="$(echo "$ids" | grep -c . || true)"
  if [[ "$count" -gt 1 ]]; then
    echo "❌ Multiple app registrations found with displayName '$display_name'. Delete duplicates or set $env_key manually." >&2
    exit 1
  fi
  echo "$ids" | head -n1
}

# Retry an az command on transient Graph propagation failures.
retry() {
  local max=${RETRY_COUNT:-6}
  local delay=${RETRY_DELAY:-10}
  local i=1
  while true; do
    if "$@"; then return 0; fi
    if (( i >= max )); then return 1; fi
    echo "  ↻ retry $i/$max after ${delay}s..."
    sleep "$delay"
    i=$((i+1))
  done
}

# Generate a UUID in a macOS/Linux portable way.
generate_uuid() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import uuid; print(uuid.uuid4())'
  elif [[ -r /proc/sys/kernel/random/uuid ]]; then
    cat /proc/sys/kernel/random/uuid
  else
    echo "❌ Unable to generate UUID. Install uuidgen or python3." >&2
    exit 1
  fi
}

# Print a preflight check result line
_check() {
  local status="$1"  # PASS | WARN | FAIL
  local label="$2"
  local detail="${3:-}"
  case "$status" in
    PASS) printf "  ✅ %-55s\n" "$label" ;;
    WARN) printf "  ⚠️  %-54s\n" "$label"
          [[ -n "$detail" ]] && echo "       $detail" ;;
    FAIL) printf "  ❌ %-55s\n" "$label"
          [[ -n "$detail" ]] && echo "       $detail" ;;
  esac
}

validate_prerequisites_and_permissions() {
  echo ""
  echo "============================================================"
  echo "Preflight: permission validation"
  echo "============================================================"

  local fatal=false

  # ── 1. Azure CLI authentication ──────────────────────────────────
  local account_id
  account_id="$(az account show --query id -o tsv 2>/dev/null || true)"
  if [[ -z "$account_id" ]]; then
    _check FAIL "Azure CLI authenticated" \
      "Run 'az login' (or 'az login --use-device-code') then re-run this script."
    fatal=true
  else
    _check PASS "Azure CLI authenticated (subscription: $account_id)"
  fi

  # ── 2. Required azd environment values present ───────────────────
  local missing_keys=()
  for key in AZURE_RESOURCE_GROUP AZURE_SUBSCRIPTION_ID CONTAINER_WEB_APP_NAME \
             CONTAINER_WEB_APP_FQDN CONTAINER_API_APP_NAME CONTAINER_API_APP_FQDN; do
    local val
    val="$(azd env get-value "$key" 2>/dev/null || true)"
    if [[ -z "$val" ]]; then
      missing_keys+=("$key")
    fi
  done
  if [[ ${#missing_keys[@]} -gt 0 ]]; then
    _check FAIL "Required azd env values present" \
      "Missing: ${missing_keys[*]}. Run 'azd env get-values' to inspect. Re-run 'azd up' if provisioning is incomplete."
    fatal=true
  else
    _check PASS "Required azd env values present"
  fi

  # Abort early if basics are missing — remaining checks depend on them
  if [[ "$fatal" == "true" ]]; then
    echo ""
    echo "❌ Preflight failed — fix the issues above and re-run configure_auth.sh" >&2
    exit 1
  fi

  # ── 3. Azure Container Apps CLI extension available ──────────────
  if az containerapp --help >/dev/null 2>&1; then
    _check PASS "Azure Container Apps CLI extension available"
  else
    _check FAIL "Azure Container Apps CLI extension available" \
      "Install with: az extension add --name containerapp --upgrade"
    fatal=true
  fi

  # ── 3b. Python 3 available (used for authConfig JSON patching) ───
  if command -v python3 >/dev/null 2>&1; then
    _check PASS "python3 available (required for authConfig patching)"
  else
    _check FAIL "python3 available (required for authConfig patching)" \
      "Install Python 3 and ensure 'python3' is on PATH, then re-run."
    fatal=true
  fi

  # ── 4. Contributor (or Owner) on the resource group ──────────────
  local current_principal
  current_principal="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
  local is_sp=false
  if [[ -z "$current_principal" ]]; then
    is_sp=true
    current_principal="$(az account show --query 'user.name' -o tsv 2>/dev/null || true)"
  fi

  local has_contributor=false
  # Check RBAC on the resource group (works for users and SPs)
  local rbac_roles
  rbac_roles="$(az role assignment list \
    --assignee "$current_principal" \
    --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" \
    --query "[].roleDefinitionName" -o tsv 2>/dev/null || true)"
  if echo "$rbac_roles" | grep -Eiq 'Owner|Contributor'; then
    has_contributor=true
    _check PASS "Contributor/Owner role on resource group '$RESOURCE_GROUP'"
  else
    # Also accept subscription-level assignment inherited down
    local rbac_sub_roles
    rbac_sub_roles="$(az role assignment list \
      --assignee "$current_principal" \
      --scope "/subscriptions/${SUBSCRIPTION_ID}" \
      --query "[].roleDefinitionName" -o tsv 2>/dev/null || true)"
    if echo "$rbac_sub_roles" | grep -Eiq 'Owner|Contributor'; then
      has_contributor=true
      _check PASS "Contributor/Owner role inherited from subscription scope"
    else
      _check FAIL "Contributor/Owner role on resource group '$RESOURCE_GROUP'" \
        "Grant Contributor on the resource group: az role assignment create --assignee \"$current_principal\" --role Contributor --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
      fatal=true
    fi
  fi

  # ── 5. Entra app registration read access ────────────────────────
  if az ad app list --top 1 --query "[0].appId" -o tsv >/dev/null 2>&1; then
    _check PASS "Can read Entra app registrations"
  else
    _check FAIL "Can read Entra app registrations" \
      "Ensure your identity has at least Directory Readers or Application Developer role in Entra."
    fatal=true
  fi

  # ── 6. Container App reachable ───────────────────────────────────
  if az containerapp show -n "$WEB_NAME" -g "$RESOURCE_GROUP" --query name -o tsv >/dev/null 2>&1; then
    _check PASS "Container App '$WEB_NAME' is accessible"
  else
    _check FAIL "Container App '$WEB_NAME' is accessible" \
      "Verify the deployment completed and you have Contributor role on the resource group."
    fatal=true
  fi

  # ── 7. Entra directory role check (users only) ───────────────────
  if [[ "$is_sp" == "true" ]]; then
    _check WARN "Entra directory-role check" \
      "Logged in as a service principal — directory role check skipped. Ensure the SP has Application Administrator and admin-consent permissions."
    CONSENT_PRECHECK_OK=false
  else
    local roles
    roles="$(az rest --method GET \
      --url "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/microsoft.graph.directoryRole?\$select=displayName" \
      --query "value[].displayName" -o tsv 2>/dev/null || true)"

    if [[ -z "$roles" ]]; then
      _check WARN "Entra directory roles resolvable" \
        "Could not enumerate roles. The script will continue; exact permission errors will surface at runtime."
    elif ! echo "$roles" | grep -Eiq 'Global Administrator|Application Administrator|Cloud Application Administrator'; then
      _check FAIL "App-registration permission (Application Administrator or higher)" \
        "Assign 'Application Administrator' (or higher) in Entra ID, then re-run.\n       Portal: https://entra.microsoft.com → Roles and administrators"
      fatal=true
    else
      _check PASS "App-registration permission (Application Administrator or higher)"

      if ! echo "$roles" | grep -Eiq 'Global Administrator|Cloud Application Administrator'; then
        CONSENT_PRECHECK_OK=false
        _check WARN "Admin-consent permission (Cloud Application Administrator or higher)" \
          "Admin consent step will be attempted but may fail. A tenant admin can grant consent at:\n       https://login.microsoftonline.com/${TENANT_ID}/adminconsent?client_id=<web-client-id>"
      else
        _check PASS "Admin-consent permission (Cloud Application Administrator or higher)"
      fi
    fi
  fi

  # ── Summary ──────────────────────────────────────────────────────
  echo ""
  if [[ "$fatal" == "true" ]]; then
    echo "❌ One or more preflight checks FAILED. Resolve the issues above and re-run." >&2
    exit 1
  fi
  echo "  Preflight passed — proceeding with auth configuration."
  echo "============================================================"
}

validate_prerequisites_and_permissions

if [[ "$PREFLIGHT_ONLY" == "true" ]]; then
  echo ""
  echo "✅ Preflight-only mode: all permission checks passed. No changes were made."
  exit 0
fi

# -----------------------------------------------------------------------------
# Step 1: API app registration (exposes user_impersonation scope)
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 1/6: API app registration ($API_APP_DISPLAY_NAME)"

API_CLIENT_ID="$(find_app_by_env_or_name AZURE_AUTH_API_CLIENT_ID "$API_APP_DISPLAY_NAME")"
if [[ -z "$API_CLIENT_ID" ]]; then
  API_CLIENT_ID="$(az ad app create \
    --display-name "$API_APP_DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    --web-redirect-uris "$API_AUTH_CALLBACK" \
    --enable-id-token-issuance true \
    --query appId -o tsv)"
  echo "  ✓ Created API app: $API_CLIENT_ID"
else
  echo "  ↺ Reusing API app: $API_CLIENT_ID"
  retry az ad app update --id "$API_CLIENT_ID" \
    --web-redirect-uris "$API_AUTH_CALLBACK" \
    --enable-id-token-issuance true >/dev/null
fi
azd env set AZURE_AUTH_API_CLIENT_ID "$API_CLIENT_ID" >/dev/null

# Ensure service principal exists (needed for consent + EasyAuth)
retry az ad sp show --id "$API_CLIENT_ID" >/dev/null 2>&1 \
  || az ad sp create --id "$API_CLIENT_ID" >/dev/null

API_APP_OBJECT_ID="$(az ad app show --id "$API_CLIENT_ID" --query id -o tsv)"
API_IDENTIFIER_URI="api://${API_CLIENT_ID}"

# Set identifierUri + expose user_impersonation scope (idempotent via Graph PATCH)
API_SCOPE_ID="$(az ad app show --id "$API_CLIENT_ID" \
  --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" -o tsv)"
if [[ -z "$API_SCOPE_ID" || "$API_SCOPE_ID" == "null" ]]; then
  API_SCOPE_ID="$(generate_uuid)"
  cat > /tmp/api_scope_patch.json <<EOF
{
  "identifierUris": ["$API_IDENTIFIER_URI"],
  "api": {
    "oauth2PermissionScopes": [{
      "id": "$API_SCOPE_ID",
      "adminConsentDescription": "Allow the application to access the API on behalf of the signed-in user.",
      "adminConsentDisplayName": "Access API as user",
      "userConsentDescription": "Allow the application to access the API on your behalf.",
      "userConsentDisplayName": "Access API",
      "value": "user_impersonation",
      "type": "User",
      "isEnabled": true
    }]
  }
}
EOF
  retry az rest --method PATCH \
    --url "https://graph.microsoft.com/v1.0/applications/${API_APP_OBJECT_ID}" \
    --headers "Content-Type=application/json" \
    --body @/tmp/api_scope_patch.json >/dev/null
  rm -f /tmp/api_scope_patch.json
  echo "  ✓ Exposed scope api://${API_CLIENT_ID}/user_impersonation"
else
  echo "  ↺ API scope already exposed"
fi
API_SCOPE_VALUE="api://${API_CLIENT_ID}/user_impersonation"

# -----------------------------------------------------------------------------
# Step 2: Web app registration (SPA + EasyAuth callback + exposes scope)
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 2/6: Web app registration ($WEB_APP_DISPLAY_NAME)"

WEB_CLIENT_ID="$(find_app_by_env_or_name AZURE_AUTH_WEB_CLIENT_ID "$WEB_APP_DISPLAY_NAME")"
if [[ -z "$WEB_CLIENT_ID" ]]; then
  WEB_CLIENT_ID="$(az ad app create \
    --display-name "$WEB_APP_DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    --web-redirect-uris "$WEB_AUTH_CALLBACK" \
    --enable-id-token-issuance true \
    --enable-access-token-issuance true \
    --query appId -o tsv)"
  echo "  ✓ Created Web app: $WEB_CLIENT_ID"
else
  echo "  ↺ Reusing Web app: $WEB_CLIENT_ID"
  retry az ad app update --id "$WEB_CLIENT_ID" \
    --web-redirect-uris "$WEB_AUTH_CALLBACK" \
    --enable-id-token-issuance true \
    --enable-access-token-issuance true >/dev/null
fi
azd env set AZURE_AUTH_WEB_CLIENT_ID "$WEB_CLIENT_ID" >/dev/null

retry az ad sp show --id "$WEB_CLIENT_ID" >/dev/null 2>&1 \
  || az ad sp create --id "$WEB_CLIENT_ID" >/dev/null

WEB_APP_OBJECT_ID="$(az ad app show --id "$WEB_CLIENT_ID" --query id -o tsv)"
WEB_IDENTIFIER_URI="api://${WEB_CLIENT_ID}"

# Expose user_impersonation scope on the Web app (needed for loginRequest)
# + add SPA redirect URI + declare required resource access on API scope + Graph User.Read
WEB_SCOPE_ID="$(az ad app show --id "$WEB_CLIENT_ID" \
  --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" -o tsv)"
[[ -z "$WEB_SCOPE_ID" || "$WEB_SCOPE_ID" == "null" ]] && WEB_SCOPE_ID="$(generate_uuid)"

cat > /tmp/web_patch.json <<EOF
{
  "identifierUris": ["$WEB_IDENTIFIER_URI"],
  "spa": { "redirectUris": ["$WEB_URL", "$WEB_URL/"] },
  "api": {
    "knownClientApplications": [],
    "oauth2PermissionScopes": [{
      "id": "$WEB_SCOPE_ID",
      "adminConsentDescription": "Allow the app to sign in the user.",
      "adminConsentDisplayName": "Sign in",
      "userConsentDescription": "Allow the app to sign you in.",
      "userConsentDisplayName": "Sign in",
      "value": "user_impersonation",
      "type": "User",
      "isEnabled": true
    }]
  },
  "requiredResourceAccess": [
    {
      "resourceAppId": "$API_CLIENT_ID",
      "resourceAccess": [{ "id": "$API_SCOPE_ID", "type": "Scope" }]
    },
    {
      "resourceAppId": "$GRAPH_APP_ID",
      "resourceAccess": [{ "id": "$GRAPH_USER_READ_SCOPE_ID", "type": "Scope" }]
    }
  ]
}
EOF
retry az rest --method PATCH \
  --url "https://graph.microsoft.com/v1.0/applications/${WEB_APP_OBJECT_ID}" \
  --headers "Content-Type=application/json" \
  --body @/tmp/web_patch.json >/dev/null
rm -f /tmp/web_patch.json
echo "  ✓ Web SPA redirect, scope, and required permissions configured"

WEB_SCOPE_VALUE="api://${WEB_CLIENT_ID}/user_impersonation"

# -----------------------------------------------------------------------------
# Step 3: Admin consent (best effort; hard warning if fails)
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 3/6: Granting admin consent"
CONSENT_OK=true
if ! retry az ad app permission admin-consent --id "$WEB_CLIENT_ID" 2>/tmp/consent_err; then
  CONSENT_OK=false
  echo "  ⚠️ Admin consent failed. Sign-in may fail until a tenant admin runs:"
  echo "       az ad app permission admin-consent --id $WEB_CLIENT_ID"
  echo "     Or visit: https://login.microsoftonline.com/${TENANT_ID}/adminconsent?client_id=${WEB_CLIENT_ID}"
  cat /tmp/consent_err | sed 's/^/       /'
  rm -f /tmp/consent_err
else
  echo "  ✓ Admin consent granted"
fi

# Belt-and-suspenders: explicitly grant the API scope to the Web SP.
# `az ad app permission admin-consent` is unreliable for app-to-app delegated
# permissions exposed by a freshly-created custom API — the consent often only
# covers Microsoft Graph permissions and silently skips the API. Without the
# API grant, MSAL.js acquireTokenSilent() fails on the SPA and the page is blank.
WEB_SP_ID="$(az ad sp show --id "$WEB_CLIENT_ID" --query id -o tsv 2>/dev/null || true)"
API_SP_ID="$(az ad sp show --id "$API_CLIENT_ID" --query id -o tsv 2>/dev/null || true)"
if [[ -n "$WEB_SP_ID" && -n "$API_SP_ID" ]]; then
  EXISTING_GRANT="$(az rest --method get \
    --url "https://graph.microsoft.com/v1.0/servicePrincipals/${WEB_SP_ID}/oauth2PermissionGrants" \
    --query "value[?resourceId=='${API_SP_ID}'] | [0].id" -o tsv 2>/dev/null || true)"
  if [[ -z "$EXISTING_GRANT" || "$EXISTING_GRANT" == "null" ]]; then
    if az rest --method POST \
      --url "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" \
      --headers "Content-Type=application/json" \
      --body "{\"clientId\":\"${WEB_SP_ID}\",\"consentType\":\"AllPrincipals\",\"resourceId\":\"${API_SP_ID}\",\"scope\":\"user_impersonation\"}" \
      --output none 2>/dev/null; then
      echo "  ✓ API user_impersonation scope granted to Web SP"
    else
      echo "  ⚠️  Could not auto-grant API user_impersonation; SPA may show blank page until granted manually."
      CONSENT_OK=false
    fi
  else
    echo "  ↺ API user_impersonation scope already granted"
  fi
fi

# -----------------------------------------------------------------------------
# Step 4: Client secrets + Container App secrets
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 4/6: Client secrets"

CA_SECRET_NAME="microsoft-provider-authentication-secret"

ensure_ca_secret_from_app_reg() {
  local app_id="$1"
  local ca_name="$2"
  local existing
  existing="$(az containerapp secret list -n "$ca_name" -g "$RESOURCE_GROUP" \
    --query "[?name=='$CA_SECRET_NAME'].name | [0]" -o tsv 2>/dev/null || true)"
  if [[ -n "$existing" && "$existing" != "null" ]]; then
    echo "  ↺ Container App '$ca_name' already has '$CA_SECRET_NAME' — not rotating."
    return 0
  fi
  local secret
  secret="$(az ad app credential reset --id "$app_id" --append \
    --display-name "containerapp-easyauth" --years 2 \
    --query password -o tsv)"
  az containerapp secret set -n "$ca_name" -g "$RESOURCE_GROUP" \
    --secrets "${CA_SECRET_NAME}=${secret}" --output none
  echo "  ✓ Stored new client secret in '$ca_name'"
}

ensure_ca_secret_from_app_reg "$API_CLIENT_ID" "$API_NAME"
ensure_ca_secret_from_app_reg "$WEB_CLIENT_ID" "$WEB_NAME"

# -----------------------------------------------------------------------------
# Step 5: Enable EasyAuth Microsoft provider on both Container Apps
#         (allowUnauthenticated for now; env vars update next, strict last)
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 5/6: Enabling EasyAuth on Web + API container apps"

configure_easyauth_app() {
  local ca_name="$1"
  local client_id="$2"
  # Note: --tenant-id and --issuer are mutually exclusive; tenant-id derives
  # the v2.0 issuer automatically. Do not override --allowed-token-audiences;
  # EasyAuth issues ID tokens with aud=<client_id>, which is the default.
  az containerapp auth microsoft update -n "$ca_name" -g "$RESOURCE_GROUP" \
    --client-id "$client_id" \
    --client-secret-name "$CA_SECRET_NAME" \
    --tenant-id "$TENANT_ID" \
    --yes --output none
}

configure_easyauth_app "$API_NAME" "$API_CLIENT_ID"
configure_easyauth_app "$WEB_NAME" "$WEB_CLIENT_ID"

# Make sure auth is enabled and (temporarily) permissive so we can still push
# env vars / verify deployment. Final lockdown happens at the end.
az containerapp auth update -n "$WEB_NAME" -g "$RESOURCE_GROUP" \
  --enabled true --unauthenticated-client-action AllowAnonymous --output none
az containerapp auth update -n "$API_NAME" -g "$RESOURCE_GROUP" \
  --enabled true --unauthenticated-client-action AllowAnonymous --output none

echo "  ✓ EasyAuth providers configured"

# -----------------------------------------------------------------------------
# Step 6: Web env vars + API allowedApplications + final lockdown
# -----------------------------------------------------------------------------
echo ""
echo "➡️  Step 6/6: Wiring env vars and caller allowlist"

# Update Web container env vars (other values left untouched)
# Also overwrite APP_WEB_AUTHORITY to fix a pre-existing bicep bug that produces
# a malformed authority URL (double slash before tenant id).
az containerapp update -n "$WEB_NAME" -g "$RESOURCE_GROUP" \
  --set-env-vars \
    "APP_WEB_CLIENT_ID=$WEB_CLIENT_ID" \
    "APP_WEB_SCOPE=$WEB_SCOPE_VALUE" \
    "APP_API_SCOPE=$API_SCOPE_VALUE" \
    "APP_WEB_AUTHORITY=https://login.microsoftonline.com/$TENANT_ID" \
    "APP_AUTH_ENABLED=true" \
  --output none
echo "  ✓ Web env vars: APP_WEB_CLIENT_ID / APP_WEB_SCOPE / APP_API_SCOPE / APP_WEB_AUTHORITY / APP_AUTH_ENABLED"

# Patch both authConfigs:
#   - API: add Web client id to allowedApplications
#   - Both: reset allowedAudiences to only the clientId, normalize openIdIssuer
patch_authconfig() {
  local ca_name="$1"
  local client_id="$2"
  local add_web_allowed="$3"   # "true" (API side) / "false" (Web side)
  local url="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${ca_name}/authConfigs/current?api-version=2024-03-01"
  local cur patched
  cur="$(az rest --method get --url "$url")"
  patched="$(echo "$cur" | ADD_WEB="$add_web_allowed" WEB_CLIENT_ID="$WEB_CLIENT_ID" CLIENT_ID="$client_id" TENANT_ID="$TENANT_ID" python3 -c "
import json, os, sys
d = json.load(sys.stdin)
props = d.setdefault('properties', {})
props['platform'] = props.get('platform') or {}
props['platform']['enabled'] = True
idp = props.setdefault('identityProviders', {})
aad = idp.setdefault('azureActiveDirectory', {})
reg = aad.setdefault('registration', {})
reg['openIdIssuer'] = f\"https://login.microsoftonline.com/{os.environ['TENANT_ID']}/v2.0\"
val = aad.setdefault('validation', {})
val['allowedAudiences'] = [os.environ['CLIENT_ID'], 'api://' + os.environ['CLIENT_ID']]
policy = val.setdefault('defaultAuthorizationPolicy', {})
allowed = set(policy.get('allowedApplications') or [])
if os.environ['ADD_WEB'] == 'true':
    allowed.add(os.environ['WEB_CLIENT_ID'])
policy['allowedApplications'] = sorted(allowed)
gv = props.setdefault('globalValidation', {})
gv['requireAuthentication'] = True
if os.environ['ADD_WEB'] == 'true':
    gv['unauthenticatedClientAction'] = 'Return401'
    gv.pop('redirectToProvider', None)
else:
    gv['unauthenticatedClientAction'] = 'RedirectToLoginPage'
    gv['redirectToProvider'] = 'azureactivedirectory'
print(json.dumps(d))
")"
  echo "$patched" > /tmp/authconfig_patch.json
  retry az rest --method put --url "$url" \
    --headers "Content-Type=application/json" \
    --body @/tmp/authconfig_patch.json >/dev/null
  rm -f /tmp/authconfig_patch.json
}

patch_authconfig "$API_NAME" "$API_CLIENT_ID" "true"
patch_authconfig "$WEB_NAME" "$WEB_CLIENT_ID" "false"
echo "  ✓ authConfigs normalized (issuer, audiences, allowedApplications)"

# Final lockdown handled in patch_authconfig globalValidation above.
echo "  ✓ Unauthenticated requests: Web → login, API → 401"

# Restart active revisions so containers pick up newly-set client secrets.
# (`az containerapp secret set` does NOT trigger a new revision on its own.)
restart_active_revision() {
  local ca_name="$1"
  local rev
  rev="$(az containerapp revision list -n "$ca_name" -g "$RESOURCE_GROUP" \
    --query "[?properties.active] | [0].name" -o tsv 2>/dev/null || true)"
  if [[ -n "$rev" && "$rev" != "null" ]]; then
    az containerapp revision restart -n "$ca_name" -g "$RESOURCE_GROUP" \
      --revision "$rev" --output none 2>/dev/null || true
  fi
}
restart_active_revision "$WEB_NAME"
restart_active_revision "$API_NAME"
echo "  ✓ Restarted Web + API container revisions to apply secrets"

echo ""
echo "============================================================"
echo "🔐 Auth configuration complete."
echo "  Web client id : $WEB_CLIENT_ID"
echo "  API client id : $API_CLIENT_ID"
echo "  Web scope     : $WEB_SCOPE_VALUE"
echo "  API scope     : $API_SCOPE_VALUE"
if [[ "$CONSENT_OK" != "true" ]]; then
  echo "  ⚠️  Admin consent pending — see step 3 above."
fi
if [[ "$CONSENT_PRECHECK_OK" != "true" ]]; then
  echo "  ⚠️  Permission pre-check predicted admin-consent limitations for this identity."
fi
echo "  Note: EasyAuth rollout can take up to 10 minutes."
echo "============================================================"
