#!/bin/bash
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
#
# Configures Microsoft Entra ID (Easy Auth) authentication on the deployed API
# and Web Container Apps, automating the manual portal steps described in
# docs/ConfigureAppAuthentication.md.
#
# Run AFTER `azd up` (or `azd provision`). Idempotent: existing registrations
# and settings are reused.
#
# TIMING: This is a manual post-deployment step. Run it immediately after the
# post-deployment schema-registration script. Until it completes, the API has
# external ingress and is reachable without authentication, so do not defer it.
# It is intentionally not wired into the azd provisioning hooks, to avoid
# deployment-time failures.
#
# Usage:
#   ./configure_app_authentication.sh
#   API_CLIENT_ID=<guid> WEB_CLIENT_ID=<guid> ./configure_app_authentication.sh

set -euo pipefail

step() {
  echo ""
  echo "======================================================================"
  echo "$1"
  echo "======================================================================"
}

get_azd_value() {
  local key="$1"
  local value
  value=$(azd env get-value "$key" 2>/dev/null || echo "")
  if [ -n "$value" ] && [[ "$value" != *"not found"* ]]; then
    echo "$value"
  fi
}

# ---------------------------------------------------------------------------
# Step 0: Resolve context from the azd environment
# ---------------------------------------------------------------------------
step "Step 0: Resolving deployment context from azd environment"

RESOURCE_GROUP=$(get_azd_value "AZURE_RESOURCE_GROUP")
SUBSCRIPTION_ID=$(get_azd_value "AZURE_SUBSCRIPTION_ID")
API_APP_NAME=$(get_azd_value "CONTAINER_API_APP_NAME")
API_APP_FQDN=$(get_azd_value "CONTAINER_API_APP_FQDN")
WEB_APP_NAME=$(get_azd_value "CONTAINER_WEB_APP_NAME")
WEB_APP_FQDN=$(get_azd_value "CONTAINER_WEB_APP_FQDN")

TENANT_ID="${TENANT_ID:-$(get_azd_value "AZURE_TENANT_ID")}"
if [ -z "$TENANT_ID" ]; then
  TENANT_ID=$(az account show --query tenantId --output tsv)
fi

for pair in \
  "AZURE_RESOURCE_GROUP=$RESOURCE_GROUP" \
  "CONTAINER_API_APP_NAME=$API_APP_NAME" \
  "CONTAINER_API_APP_FQDN=$API_APP_FQDN" \
  "CONTAINER_WEB_APP_NAME=$WEB_APP_NAME" \
  "CONTAINER_WEB_APP_FQDN=$WEB_APP_FQDN"; do
  name="${pair%%=*}"
  value="${pair#*=}"
  if [ -z "$value" ]; then
    echo "Error: required value '$name' could not be resolved from the azd environment. Run 'azd provision' first." >&2
    exit 1
  fi
done

if [ -n "$SUBSCRIPTION_ID" ]; then
  az account set --subscription "$SUBSCRIPTION_ID"
fi

API_URI="https://$API_APP_FQDN"
WEB_URI="https://$WEB_APP_FQDN"

echo "  Resource group : $RESOURCE_GROUP"
echo "  Tenant         : $TENANT_ID"
echo "  API app        : $API_APP_NAME ($API_URI)"
echo "  Web app        : $WEB_APP_NAME ($WEB_URI)"

# ---------------------------------------------------------------------------
# Step 1: API app registration (resource server) + exposed scope
# ---------------------------------------------------------------------------
step "Step 1: Configuring API app registration"

API_CLIENT_ID="${API_CLIENT_ID:-$(get_azd_value "API_CLIENT_ID")}"

if [ -z "$API_CLIENT_ID" ]; then
  echo "  Creating API app registration '$API_APP_NAME'..."
  API_CLIENT_ID=$(az ad app create \
    --display-name "$API_APP_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId --output tsv)
else
  echo "  Reusing API app registration: $API_CLIENT_ID"
fi

API_IDENTIFIER_URI="api://$API_CLIENT_ID"
az ad app update --id "$API_CLIENT_ID" --identifier-uris "$API_IDENTIFIER_URI"

EXISTING_SCOPES=$(az ad app show --id "$API_CLIENT_ID" --query "api.oauth2PermissionScopes[].value" --output tsv || echo "")
if ! echo "$EXISTING_SCOPES" | grep -q "user_impersonation"; then
  echo "  Exposing 'user_impersonation' scope on the API app..."
  SCOPE_ID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python -c "import uuid;print(uuid.uuid4())")
  TMP_API=$(mktemp)
  cat > "$TMP_API" <<EOF
{
  "oauth2PermissionScopes": [
    {
      "id": "$SCOPE_ID",
      "adminConsentDescription": "Allow the application to access the Content Processing API on behalf of the signed-in user.",
      "adminConsentDisplayName": "Access Content Processing API",
      "userConsentDescription": "Allow the application to access the Content Processing API on your behalf.",
      "userConsentDisplayName": "Access Content Processing API",
      "value": "user_impersonation",
      "type": "User",
      "isEnabled": true
    }
  ]
}
EOF
  az ad app update --id "$API_CLIENT_ID" --set "api=@$TMP_API"
  rm -f "$TMP_API"
else
  echo "  'user_impersonation' scope already exposed."
fi

if ! az ad sp show --id "$API_CLIENT_ID" --query id --output tsv >/dev/null 2>&1; then
  az ad sp create --id "$API_CLIENT_ID"
fi

API_SCOPE="$API_IDENTIFIER_URI/user_impersonation"
echo "  API scope: $API_SCOPE"

# ---------------------------------------------------------------------------
# Step 2: Web app registration (SPA client)
# ---------------------------------------------------------------------------
step "Step 2: Configuring Web app registration"

WEB_CLIENT_ID="${WEB_CLIENT_ID:-$(get_azd_value "WEB_CLIENT_ID")}"

if [ -z "$WEB_CLIENT_ID" ]; then
  echo "  Creating Web app registration '$WEB_APP_NAME'..."
  WEB_CLIENT_ID=$(az ad app create \
    --display-name "$WEB_APP_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId --output tsv)
else
  echo "  Reusing Web app registration: $WEB_CLIENT_ID"
fi

echo "  Setting SPA redirect URI: $WEB_URI"
az ad app update --id "$WEB_CLIENT_ID" --set "spa={\"redirectUris\":[\"$WEB_URI\"]}"

SCOPE_GUID=$(az ad app show --id "$API_CLIENT_ID" --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" --output tsv)
echo "  Adding API permission to the Web app..."
az ad app permission add \
  --id "$WEB_CLIENT_ID" \
  --api "$API_CLIENT_ID" \
  --api-permissions "$SCOPE_GUID=Scope"

if ! az ad sp show --id "$WEB_CLIENT_ID" --query id --output tsv >/dev/null 2>&1; then
  az ad sp create --id "$WEB_CLIENT_ID"
fi

echo "  Attempting admin consent (best effort)..."
if az ad app permission admin-consent --id "$WEB_CLIENT_ID" 2>/dev/null; then
  echo "  Admin consent granted."
else
  echo "  WARNING: Could not grant admin consent automatically. A tenant administrator must consent to the API permission for '$WEB_APP_NAME'. See docs/ConfigureAppAuthentication.md." >&2
fi

# ---------------------------------------------------------------------------
# Step 3: Enable Container Apps authentication
# ---------------------------------------------------------------------------
step "Step 3: Enabling Container Apps authentication (Easy Auth)"

ISSUER="https://sts.windows.net/$TENANT_ID/"

echo "  Configuring API authentication (Return401)..."
az containerapp auth microsoft update \
  --name "$API_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --client-id "$API_CLIENT_ID" \
  --issuer "$ISSUER" \
  --allowed-audiences "$API_IDENTIFIER_URI" \
  --yes

az containerapp auth update \
  --name "$API_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --unauthenticated-client-action Return401 \
  --redirect-provider AzureActiveDirectory \
  --yes

echo "  Configuring Web authentication (RedirectToLoginPage)..."
az containerapp auth microsoft update \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --client-id "$WEB_CLIENT_ID" \
  --issuer "$ISSUER" \
  --yes

az containerapp auth update \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --unauthenticated-client-action RedirectToLoginPage \
  --redirect-provider AzureActiveDirectory \
  --yes

# ---------------------------------------------------------------------------
# Step 4: Allow the Web client to call the API
# ---------------------------------------------------------------------------
step "Step 4: Allowing the Web client on the API"

echo "  Adding Web client id to the API allowed client applications..."
az containerapp auth microsoft update \
  --name "$API_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --client-id "$API_CLIENT_ID" \
  --issuer "$ISSUER" \
  --allowed-audiences "$API_IDENTIFIER_URI" \
  --allowed-client-applications "$WEB_CLIENT_ID" \
  --yes

# ---------------------------------------------------------------------------
# Step 5: Update Web container environment variables
# ---------------------------------------------------------------------------
step "Step 5: Updating Web container environment variables"

az containerapp update \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars \
    "APP_WEB_CLIENT_ID=$WEB_CLIENT_ID" \
    "APP_WEB_SCOPE=$API_SCOPE" \
    "APP_API_SCOPE=$API_SCOPE"

if command -v azd >/dev/null 2>&1; then
  azd env set API_CLIENT_ID "$API_CLIENT_ID" 2>/dev/null || true
  azd env set WEB_CLIENT_ID "$WEB_CLIENT_ID" 2>/dev/null || true
fi

step "Authentication configuration complete"
echo "  API client id : $API_CLIENT_ID"
echo "  Web client id : $WEB_CLIENT_ID"
echo "  API scope     : $API_SCOPE"
echo ""
echo "  The API now returns HTTP 401 to unauthenticated callers."
echo "  Note: post-deployment data ingestion scripts must send a bearer token."
