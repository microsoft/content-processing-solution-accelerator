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

echo ""
echo "============================================================"
echo "🔐 Configuring Entra ID authentication (Web + API)"
echo "============================================================"

# --- Load values from azd env -------------------------------------------------
ENV_NAME="$(azd env get-value AZURE_ENV_NAME 2>/dev/null || echo "")"
RESOURCE_GROUP="$(azd env get-value AZURE_RESOURCE_GROUP)"
SUBSCRIPTION_ID="$(azd env get-value AZURE_SUBSCRIPTION_ID)"
TENANT_ID="$(azd env get-value AZURE_TENANT_ID 2>/dev/null || az account show --query tenantId -o tsv)"

WEB_NAME="$(azd env get-value CONTAINER_WEB_APP_NAME)"
WEB_FQDN="$(azd env get-value CONTAINER_WEB_APP_FQDN)"
API_NAME="$(azd env get-value CONTAINER_API_APP_NAME)"
API_FQDN="$(azd env get-value CONTAINER_API_APP_FQDN)"

WEB_APP_DISPLAY_NAME="${ENV_NAME:-cps}-web-app"
API_APP_DISPLAY_NAME="${ENV_NAME:-cps}-api-app"

WEB_URL="https://${WEB_FQDN}"
API_URL="https://${API_FQDN}"
WEB_AUTH_CALLBACK="${WEB_URL}/.auth/login/aad/callback"
API_AUTH_CALLBACK="${API_URL}/.auth/login/aad/callback"

# Graph delegated User.Read permission
GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"
GRAPH_USER_READ_SCOPE_ID="e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read (delegated)

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
  API_SCOPE_ID="$(cat /proc/sys/kernel/random/uuid)"
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
[[ -z "$WEB_SCOPE_ID" || "$WEB_SCOPE_ID" == "null" ]] && WEB_SCOPE_ID="$(cat /proc/sys/kernel/random/uuid)"

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

OPENID_ISSUER="https://login.microsoftonline.com/${TENANT_ID}/v2.0"

configure_easyauth_app() {
  local ca_name="$1"
  local client_id="$2"
  local audience="$3"
  az containerapp auth microsoft update -n "$ca_name" -g "$RESOURCE_GROUP" \
    --client-id "$client_id" \
    --client-secret-name "$CA_SECRET_NAME" \
    --tenant-id "$TENANT_ID" \
    --issuer "$OPENID_ISSUER" \
    --allowed-token-audiences "$audience" \
    --yes --output none
}

configure_easyauth_app "$API_NAME" "$API_CLIENT_ID" "$API_IDENTIFIER_URI"
configure_easyauth_app "$WEB_NAME" "$WEB_CLIENT_ID" "$WEB_IDENTIFIER_URI"

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
az containerapp update -n "$WEB_NAME" -g "$RESOURCE_GROUP" \
  --set-env-vars \
    "APP_WEB_CLIENT_ID=$WEB_CLIENT_ID" \
    "APP_WEB_SCOPE=$WEB_SCOPE_VALUE" \
    "APP_API_SCOPE=$API_SCOPE_VALUE" \
    "APP_AUTH_ENABLED=true" \
  --output none
echo "  ✓ Web env vars: APP_WEB_CLIENT_ID / APP_WEB_SCOPE / APP_API_SCOPE / APP_AUTH_ENABLED"

# Patch API authConfig: restrict to Web client id
# (equivalent to portal "Allow requests from specific client applications")
API_AUTHCONFIG_URL="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.App/containerApps/${API_NAME}/authConfigs/current?api-version=2024-03-01"

CURRENT_AUTH_JSON="$(az rest --method get --url "$API_AUTHCONFIG_URL")"
PATCHED_AUTH_JSON="$(echo "$CURRENT_AUTH_JSON" | python3 -c "
import json, sys
doc = json.load(sys.stdin)
props = doc.setdefault('properties', {})
idp = props.setdefault('identityProviders', {})
aad = idp.setdefault('azureActiveDirectory', {})
val = aad.setdefault('validation', {})
policy = val.setdefault('defaultAuthorizationPolicy', {})
allowed = set(policy.get('allowedApplications') or [])
allowed.add('${WEB_CLIENT_ID}')
policy['allowedApplications'] = sorted(allowed)
print(json.dumps(doc))
")"

echo "$PATCHED_AUTH_JSON" > /tmp/api_authconfig.json
retry az rest --method put --url "$API_AUTHCONFIG_URL" \
  --headers "Content-Type=application/json" \
  --body @/tmp/api_authconfig.json >/dev/null
rm -f /tmp/api_authconfig.json
echo "  ✓ API 'allowed applications' now includes Web client id"

# Final lockdown
az containerapp auth update -n "$WEB_NAME" -g "$RESOURCE_GROUP" \
  --unauthenticated-client-action RedirectToLoginPage --output none
az containerapp auth update -n "$API_NAME" -g "$RESOURCE_GROUP" \
  --unauthenticated-client-action Return401 --output none
echo "  ✓ Unauthenticated requests: Web → login, API → 401"

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
echo "  Note: EasyAuth rollout can take up to 10 minutes."
echo "============================================================"
