# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

<#
.SYNOPSIS
    Configures Microsoft Entra ID (Easy Auth) authentication on the deployed
    API and Web Container Apps, automating the manual portal steps described in
    docs/ConfigureAppAuthentication.md.

.DESCRIPTION
    This script is intended to run AFTER `azd up` (or `azd provision`). It:

        1. Reads Container App / resource-group values from the azd environment.
        2. Creates (or reuses) two Entra app registrations: one for the API
           (resource server) and one for the Web SPA (client).
        3. Exposes a `user_impersonation` scope on the API app registration.
        4. Grants the Web app permission to call the API and attempts admin
           consent (best effort).
        5. Enables Container Apps authentication:
             - API  -> unauthenticated requests receive HTTP 401 (fail closed).
             - Web  -> unauthenticated requests are redirected to login.
        6. Adds the Web client id to the API's allowed client applications.
        7. Updates the Web container app environment variables
           (APP_WEB_CLIENT_ID, APP_WEB_SCOPE, APP_API_SCOPE).

    The script is idempotent: existing registrations and settings are reused.

    NOTE ON TIMING: This is a manual post-deployment step. Run it immediately
    after the post-deployment schema-registration script. Until it completes, the
    API has external ingress and is reachable without authentication, so do not
    defer it. It is intentionally not wired into the azd provisioning hooks, to
    avoid deployment-time failures.

.PARAMETER ApiClientId
    Optional. Reuse an existing API app registration client id instead of
    creating a new one.

.PARAMETER WebClientId
    Optional. Reuse an existing Web app registration client id instead of
    creating a new one.

.PARAMETER TenantId
    Optional. Entra tenant id. Defaults to the current `az account` tenant.

.EXAMPLE
    ./configure_app_authentication.ps1

.EXAMPLE
    ./configure_app_authentication.ps1 -ApiClientId <guid> -WebClientId <guid>
#>

[CmdletBinding()]
param(
    [string]$ApiClientId,
    [string]$WebClientId,
    [string]$TenantId
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 70)
    Write-Host $Message
    Write-Host ("=" * 70)
}

function Get-AzdValue {
    param([string]$Key)
    try {
        $value = azd env get-value $Key 2>$null
        if ($LASTEXITCODE -eq 0 -and $value -and $value -notmatch "not found") {
            return $value.Trim()
        }
    } catch {
        # fall through
    }
    return $null
}

# ---------------------------------------------------------------------------
# Step 0: Resolve context from the azd environment
# ---------------------------------------------------------------------------
Write-Step "Step 0: Resolving deployment context from azd environment"

$ResourceGroup = Get-AzdValue "AZURE_RESOURCE_GROUP"
$SubscriptionId = Get-AzdValue "AZURE_SUBSCRIPTION_ID"
$ApiAppName = Get-AzdValue "CONTAINER_API_APP_NAME"
$ApiAppFqdn = Get-AzdValue "CONTAINER_API_APP_FQDN"
$WebAppName = Get-AzdValue "CONTAINER_WEB_APP_NAME"
$WebAppFqdn = Get-AzdValue "CONTAINER_WEB_APP_FQDN"

if (-not $TenantId) {
    $TenantId = Get-AzdValue "AZURE_TENANT_ID"
}
if (-not $TenantId) {
    $TenantId = az account show --query tenantId --output tsv
}

foreach ($pair in @(
    @{ Name = "AZURE_RESOURCE_GROUP"; Value = $ResourceGroup },
    @{ Name = "CONTAINER_API_APP_NAME"; Value = $ApiAppName },
    @{ Name = "CONTAINER_API_APP_FQDN"; Value = $ApiAppFqdn },
    @{ Name = "CONTAINER_WEB_APP_NAME"; Value = $WebAppName },
    @{ Name = "CONTAINER_WEB_APP_FQDN"; Value = $WebAppFqdn }
)) {
    if (-not $pair.Value) {
        throw "Required value '$($pair.Name)' could not be resolved from the azd environment. Run 'azd provision' first."
    }
}

if ($SubscriptionId) {
    az account set --subscription $SubscriptionId | Out-Null
}

$ApiUri = "https://$ApiAppFqdn"
$WebUri = "https://$WebAppFqdn"

Write-Host "  Resource group : $ResourceGroup"
Write-Host "  Tenant         : $TenantId"
Write-Host "  API app        : $ApiAppName ($ApiUri)"
Write-Host "  Web app        : $WebAppName ($WebUri)"

# ---------------------------------------------------------------------------
# Step 1: API app registration (resource server) + exposed scope
# ---------------------------------------------------------------------------
Write-Step "Step 1: Configuring API app registration"

if (-not $ApiClientId) {
    $ApiClientId = Get-AzdValue "API_CLIENT_ID"
}

if (-not $ApiClientId) {
    Write-Host "  Creating API app registration '$ApiAppName'..."
    $ApiClientId = az ad app create `
        --display-name $ApiAppName `
        --sign-in-audience AzureADMyOrg `
        --query appId --output tsv
} else {
    Write-Host "  Reusing API app registration: $ApiClientId"
}

# Ensure the Application ID URI is api://<appId> so tokens carry a stable audience.
$ApiIdentifierUri = "api://$ApiClientId"
az ad app update --id $ApiClientId --identifier-uris $ApiIdentifierUri | Out-Null

# Expose a user_impersonation scope (idempotent: skip if already present).
$existingScopes = az ad app show --id $ApiClientId --query "api.oauth2PermissionScopes[].value" --output tsv
if ($existingScopes -notcontains "user_impersonation") {
    Write-Host "  Exposing 'user_impersonation' scope on the API app..."
    $scopeId = [guid]::NewGuid().ToString()
    $apiScopes = @{
        oauth2PermissionScopes = @(
            @{
                id                      = $scopeId
                adminConsentDescription = "Allow the application to access the Content Processing API on behalf of the signed-in user."
                adminConsentDisplayName = "Access Content Processing API"
                userConsentDescription  = "Allow the application to access the Content Processing API on your behalf."
                userConsentDisplayName  = "Access Content Processing API"
                value                   = "user_impersonation"
                type                    = "User"
                isEnabled               = $true
            }
        )
    }
    $apiScopesJson = ($apiScopes | ConvertTo-Json -Depth 10 -Compress)
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $apiScopesJson -Encoding utf8
    az ad app update --id $ApiClientId --set "api=@$tmp" | Out-Null
    Remove-Item $tmp -Force
} else {
    Write-Host "  'user_impersonation' scope already exposed."
}

# Ensure a service principal exists for the API app.
$apiSp = az ad sp show --id $ApiClientId --query id --output tsv 2>$null
if (-not $apiSp) {
    az ad sp create --id $ApiClientId | Out-Null
}

$ApiScope = "$ApiIdentifierUri/user_impersonation"
Write-Host "  API scope: $ApiScope"

# ---------------------------------------------------------------------------
# Step 2: Web app registration (SPA client)
# ---------------------------------------------------------------------------
Write-Step "Step 2: Configuring Web app registration"

if (-not $WebClientId) {
    $WebClientId = Get-AzdValue "WEB_CLIENT_ID"
}

if (-not $WebClientId) {
    Write-Host "  Creating Web app registration '$WebAppName'..."
    $WebClientId = az ad app create `
        --display-name $WebAppName `
        --sign-in-audience AzureADMyOrg `
        --query appId --output tsv
} else {
    Write-Host "  Reusing Web app registration: $WebClientId"
}

# Register the SPA redirect URI so MSAL can complete the login flow.
# Use a Microsoft Graph PATCH via `az rest`; `az ad app update --set spa=...`
# is unreliable and fails with "Property spa in payload does not match schema".
# The JSON body is written to a temp file (--body @file) because passing inline
# JSON to az on Windows gets mangled by shell quoting.
Write-Host "  Setting SPA redirect URI: $WebUri"
$webObjectId = az ad app show --id $WebClientId --query id --output tsv
$spaBody = @{ spa = @{ redirectUris = @($WebUri) } } | ConvertTo-Json -Compress -Depth 5
$spaBodyFile = New-TemporaryFile
Set-Content -Path $spaBodyFile -Value $spaBody -Encoding utf8 -NoNewline
try {
    az rest `
        --method PATCH `
        --uri "https://graph.microsoft.com/v1.0/applications/$webObjectId" `
        --headers "Content-Type=application/json" `
        --body "@$spaBodyFile" | Out-Null
} finally {
    Remove-Item -Path $spaBodyFile -ErrorAction SilentlyContinue
}

# Enable ID token issuance for the implicit grant. Container Apps Easy Auth
# requests an id_token during the login redirect; without this Entra returns
# AADSTS700054 "response_type 'id_token' is not enabled for the application".
# The Easy Auth callback (/.auth/login/aad/callback) must also be registered as
# a Web-platform redirect URI, otherwise login fails with AADSTS50011.
Write-Host "  Enabling ID token issuance and Web redirect URI on the Web app..."
$easyAuthRedirect = "$WebUri/.auth/login/aad/callback"
$implicitBody = @{ web = @{ redirectUris = @($easyAuthRedirect); implicitGrantSettings = @{ enableIdTokenIssuance = $true } } } | ConvertTo-Json -Compress -Depth 5
$implicitBodyFile = New-TemporaryFile
Set-Content -Path $implicitBodyFile -Value $implicitBody -Encoding utf8 -NoNewline
try {
    az rest `
        --method PATCH `
        --uri "https://graph.microsoft.com/v1.0/applications/$webObjectId" `
        --headers "Content-Type=application/json" `
        --body "@$implicitBodyFile" | Out-Null
} finally {
    Remove-Item -Path $implicitBodyFile -ErrorAction SilentlyContinue
}

# Grant the Web app permission to call the API's user_impersonation scope.
$scopeGuid = az ad app show --id $ApiClientId --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" --output tsv
Write-Host "  Adding API permission to the Web app..."
az ad app permission add `
    --id $WebClientId `
    --api $ApiClientId `
    --api-permissions "$scopeGuid=Scope" | Out-Null

$webSp = az ad sp show --id $WebClientId --query id --output tsv 2>$null
if (-not $webSp) {
    az ad sp create --id $WebClientId | Out-Null
}

Write-Host "  Attempting admin consent (best effort)..."
try {
    az ad app permission admin-consent --id $WebClientId | Out-Null
    Write-Host "  Admin consent granted."
} catch {
    Write-Warning "  Could not grant admin consent automatically. A tenant administrator must consent to the API permission for '$WebAppName'. See docs/ConfigureAppAuthentication.md."
}

# ---------------------------------------------------------------------------
# Step 3: Enable Container Apps authentication
# ---------------------------------------------------------------------------
Write-Step "Step 3: Enabling Container Apps authentication (Easy Auth)"

$Issuer = "https://sts.windows.net/$TenantId/"

# API: fail closed. Unauthenticated callers get HTTP 401 (no login redirect).
Write-Host "  Configuring API authentication (Return401)..."
az containerapp auth microsoft update `
    --name $ApiAppName `
    --resource-group $ResourceGroup `
    --client-id $ApiClientId `
    --issuer $Issuer `
    --allowed-audiences $ApiIdentifierUri `
    --yes | Out-Null

az containerapp auth update `
    --name $ApiAppName `
    --resource-group $ResourceGroup `
    --unauthenticated-client-action Return401 `
    --redirect-provider AzureActiveDirectory `
    --yes | Out-Null

# Web: redirect unauthenticated browser users to the login page.
Write-Host "  Configuring Web authentication (RedirectToLoginPage)..."
az containerapp auth microsoft update `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --client-id $WebClientId `
    --issuer $Issuer `
    --yes | Out-Null

az containerapp auth update `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --unauthenticated-client-action RedirectToLoginPage `
    --redirect-provider AzureActiveDirectory `
    --yes | Out-Null

# ---------------------------------------------------------------------------
# Step 4: Allow the Web client to call the API
# ---------------------------------------------------------------------------
Write-Step "Step 4: Allowing the Web client on the API"

# The `--allowed-client-applications` flag is not available in older containerapp
# CLI extensions. The authConfigs resource does not support PATCH, so GET the
# current config, merge in the allowed application, and PUT it back.
Write-Host "  Adding Web client id to the API allowed client applications..."
$authConfigUri = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/containerApps/$ApiAppName/authConfigs/current?api-version=2024-03-01"
$authConfig = az rest --method GET --uri $authConfigUri | ConvertFrom-Json
$aad = $authConfig.properties.identityProviders.azureActiveDirectory
if (-not $aad.validation) {
    $aad | Add-Member -NotePropertyName validation -NotePropertyValue ([pscustomobject]@{}) -Force
}
if (-not $aad.validation.defaultAuthorizationPolicy) {
    $aad.validation | Add-Member -NotePropertyName defaultAuthorizationPolicy -NotePropertyValue ([pscustomobject]@{}) -Force
}
$aad.validation.defaultAuthorizationPolicy | Add-Member -NotePropertyName allowedApplications -NotePropertyValue @($WebClientId) -Force
$allowedAppsBody = @{ properties = $authConfig.properties } | ConvertTo-Json -Compress -Depth 20
$allowedAppsFile = New-TemporaryFile
Set-Content -Path $allowedAppsFile -Value $allowedAppsBody -Encoding utf8 -NoNewline
try {
    az rest `
        --method PUT `
        --uri $authConfigUri `
        --headers "Content-Type=application/json" `
        --body "@$allowedAppsFile" | Out-Null
} finally {
    Remove-Item -Path $allowedAppsFile -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# Step 5: Update Web container environment variables
# ---------------------------------------------------------------------------
Write-Step "Step 5: Updating Web container environment variables"

az containerapp update `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --set-env-vars `
        "APP_WEB_CLIENT_ID=$WebClientId" `
        "APP_WEB_SCOPE=$ApiScope" `
        "APP_API_SCOPE=$ApiScope" | Out-Null

# Persist the resulting client ids back into the azd environment for reuse.
if (Get-Command azd -ErrorAction SilentlyContinue) {
    azd env set API_CLIENT_ID $ApiClientId 2>$null | Out-Null
    azd env set WEB_CLIENT_ID $WebClientId 2>$null | Out-Null
}

Write-Step "Authentication configuration complete"
Write-Host "  API client id : $ApiClientId"
Write-Host "  Web client id : $WebClientId"
Write-Host "  API scope     : $ApiScope"
Write-Host ""
Write-Host "  The API now returns HTTP 401 to unauthenticated callers."
Write-Host "  Note: post-deployment data ingestion scripts must send a bearer token."
