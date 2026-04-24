# Automates the app registration + EasyAuth configuration that is otherwise
# performed manually per docs/ConfigureAppAuthentication.md.
#
# Idempotent: safe to re-run. Reuses existing app registrations and container
# app secrets where possible.
#
# Skip with: azd env set AZURE_SKIP_AUTH_SETUP true

$ErrorActionPreference = "Stop"

if ($env:AZURE_SKIP_AUTH_SETUP -eq "true") {
  Write-Host "⏭️  AZURE_SKIP_AUTH_SETUP=true — skipping auth configuration."
  return
}

Write-Host ""
Write-Host "============================================================"
Write-Host "🔐 Configuring Entra ID authentication (Web + API)"
Write-Host "============================================================"

function Azd-Get($key, $default = "") {
  try { return (azd env get-value $key 2>$null) } catch { return $default }
}

$EnvName        = Azd-Get "AZURE_ENV_NAME" "cps"
$ResourceGroup  = Azd-Get "AZURE_RESOURCE_GROUP"
$SubscriptionId = Azd-Get "AZURE_SUBSCRIPTION_ID"
$TenantId       = Azd-Get "AZURE_TENANT_ID"
if (-not $TenantId) { $TenantId = (az account show --query tenantId -o tsv) }

$WebName = Azd-Get "CONTAINER_WEB_APP_NAME"
$WebFqdn = Azd-Get "CONTAINER_WEB_APP_FQDN"
$ApiName = Azd-Get "CONTAINER_API_APP_NAME"
$ApiFqdn = Azd-Get "CONTAINER_API_APP_FQDN"

$WebDisplayName = "$EnvName-web-app"
$ApiDisplayName = "$EnvName-api-app"

$WebUrl = "https://$WebFqdn"
$ApiUrl = "https://$ApiFqdn"
$WebAuthCallback = "$WebUrl/.auth/login/aad/callback"
$ApiAuthCallback = "$ApiUrl/.auth/login/aad/callback"

$GraphAppId            = "00000003-0000-0000-c000-000000000000"
$GraphUserReadScopeId  = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
$CaSecretName          = "microsoft-provider-authentication-secret"

function Retry($Block, $Max = 6, $Delay = 10) {
  for ($i = 1; $i -le $Max; $i++) {
    try { return & $Block } catch {
      if ($i -eq $Max) { throw }
      Write-Host "  ↻ retry $i/$Max after ${Delay}s..."
      Start-Sleep -Seconds $Delay
    }
  }
}

function Find-AppIdByEnvOrName($EnvKey, $DisplayName) {
  $id = Azd-Get $EnvKey ""
  if ($id) {
    $exists = az ad app show --id $id 2>$null
    if ($LASTEXITCODE -eq 0) { return $id }
  }
  $ids = az ad app list --display-name $DisplayName --query "[].appId" -o tsv
  $arr = @($ids -split "`n" | Where-Object { $_ })
  if ($arr.Count -gt 1) { throw "Multiple app registrations with displayName '$DisplayName'. Clean up or set $EnvKey manually." }
  if ($arr.Count -eq 1) { return $arr[0] }
  return ""
}

# --- Step 1: API app registration --------------------------------------------
Write-Host ""
Write-Host "➡️  Step 1/6: API app registration ($ApiDisplayName)"

$ApiClientId = Find-AppIdByEnvOrName "AZURE_AUTH_API_CLIENT_ID" $ApiDisplayName
if (-not $ApiClientId) {
  $ApiClientId = az ad app create --display-name $ApiDisplayName `
    --sign-in-audience AzureADMyOrg `
    --web-redirect-uris $ApiAuthCallback `
    --enable-id-token-issuance true `
    --query appId -o tsv
  Write-Host "  ✓ Created API app: $ApiClientId"
} else {
  Write-Host "  ↺ Reusing API app: $ApiClientId"
  Retry { az ad app update --id $ApiClientId --web-redirect-uris $ApiAuthCallback --enable-id-token-issuance true | Out-Null }
}
azd env set AZURE_AUTH_API_CLIENT_ID $ApiClientId | Out-Null

Retry {
  az ad sp show --id $ApiClientId 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { az ad sp create --id $ApiClientId | Out-Null }
}

$ApiAppObjectId = az ad app show --id $ApiClientId --query id -o tsv
$ApiIdentifierUri = "api://$ApiClientId"

$ApiScopeId = az ad app show --id $ApiClientId --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" -o tsv
if (-not $ApiScopeId -or $ApiScopeId -eq "null") {
  $ApiScopeId = [guid]::NewGuid().ToString()
  $patch = @{
    identifierUris = @($ApiIdentifierUri)
    api = @{
      oauth2PermissionScopes = @(@{
        id = $ApiScopeId
        adminConsentDescription = "Allow the application to access the API on behalf of the signed-in user."
        adminConsentDisplayName = "Access API as user"
        userConsentDescription  = "Allow the application to access the API on your behalf."
        userConsentDisplayName  = "Access API"
        value = "user_impersonation"
        type  = "User"
        isEnabled = $true
      })
    }
  } | ConvertTo-Json -Depth 10
  $tmp = New-TemporaryFile
  $patch | Out-File -FilePath $tmp -Encoding utf8
  Retry { az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$ApiAppObjectId" --headers "Content-Type=application/json" --body "@$tmp" | Out-Null }
  Remove-Item $tmp
  Write-Host "  ✓ Exposed scope api://$ApiClientId/user_impersonation"
} else {
  Write-Host "  ↺ API scope already exposed"
}
$ApiScopeValue = "api://$ApiClientId/user_impersonation"

# --- Step 2: Web app registration --------------------------------------------
Write-Host ""
Write-Host "➡️  Step 2/6: Web app registration ($WebDisplayName)"

$WebClientId = Find-AppIdByEnvOrName "AZURE_AUTH_WEB_CLIENT_ID" $WebDisplayName
if (-not $WebClientId) {
  $WebClientId = az ad app create --display-name $WebDisplayName `
    --sign-in-audience AzureADMyOrg `
    --web-redirect-uris $WebAuthCallback `
    --enable-id-token-issuance true `
    --enable-access-token-issuance true `
    --query appId -o tsv
  Write-Host "  ✓ Created Web app: $WebClientId"
} else {
  Write-Host "  ↺ Reusing Web app: $WebClientId"
  Retry { az ad app update --id $WebClientId --web-redirect-uris $WebAuthCallback --enable-id-token-issuance true --enable-access-token-issuance true | Out-Null }
}
azd env set AZURE_AUTH_WEB_CLIENT_ID $WebClientId | Out-Null

Retry {
  az ad sp show --id $WebClientId 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { az ad sp create --id $WebClientId | Out-Null }
}

$WebAppObjectId = az ad app show --id $WebClientId --query id -o tsv
$WebIdentifierUri = "api://$WebClientId"

$WebScopeId = az ad app show --id $WebClientId --query "api.oauth2PermissionScopes[?value=='user_impersonation'].id | [0]" -o tsv
if (-not $WebScopeId -or $WebScopeId -eq "null") { $WebScopeId = [guid]::NewGuid().ToString() }

$webPatch = @{
  identifierUris = @($WebIdentifierUri)
  spa = @{ redirectUris = @($WebUrl, "$WebUrl/") }
  api = @{
    knownClientApplications = @()
    oauth2PermissionScopes = @(@{
      id = $WebScopeId
      adminConsentDescription = "Allow the app to sign in the user."
      adminConsentDisplayName = "Sign in"
      userConsentDescription  = "Allow the app to sign you in."
      userConsentDisplayName  = "Sign in"
      value = "user_impersonation"
      type  = "User"
      isEnabled = $true
    })
  }
  requiredResourceAccess = @(
    @{ resourceAppId = $ApiClientId; resourceAccess = @(@{ id = $ApiScopeId; type = "Scope" }) },
    @{ resourceAppId = $GraphAppId;  resourceAccess = @(@{ id = $GraphUserReadScopeId; type = "Scope" }) }
  )
} | ConvertTo-Json -Depth 10
$tmp = New-TemporaryFile
$webPatch | Out-File -FilePath $tmp -Encoding utf8
Retry { az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$WebAppObjectId" --headers "Content-Type=application/json" --body "@$tmp" | Out-Null }
Remove-Item $tmp
Write-Host "  ✓ Web SPA redirect, scope, and required permissions configured"
$WebScopeValue = "api://$WebClientId/user_impersonation"

# --- Step 3: Admin consent ---------------------------------------------------
Write-Host ""
Write-Host "➡️  Step 3/6: Granting admin consent"
$ConsentOk = $true
try {
  Retry { az ad app permission admin-consent --id $WebClientId | Out-Null }
  Write-Host "  ✓ Admin consent granted"
} catch {
  $ConsentOk = $false
  Write-Host "  ⚠️ Admin consent failed. Sign-in may fail until a tenant admin runs:"
  Write-Host "       az ad app permission admin-consent --id $WebClientId"
  Write-Host "     Or: https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$WebClientId"
}

# --- Step 4: Container App secrets ------------------------------------------
Write-Host ""
Write-Host "➡️  Step 4/6: Client secrets"

function Ensure-CaSecret($AppId, $CaName) {
  $existing = az containerapp secret list -n $CaName -g $ResourceGroup --query "[?name=='$CaSecretName'].name | [0]" -o tsv
  if ($existing -and $existing -ne "null") {
    Write-Host "  ↺ Container App '$CaName' already has '$CaSecretName' — not rotating."
    return
  }
  $secret = az ad app credential reset --id $AppId --append --display-name "containerapp-easyauth" --years 2 --query password -o tsv
  az containerapp secret set -n $CaName -g $ResourceGroup --secrets "$CaSecretName=$secret" --output none
  Write-Host "  ✓ Stored new client secret in '$CaName'"
}

Ensure-CaSecret $ApiClientId $ApiName
Ensure-CaSecret $WebClientId $WebName

# --- Step 5: Enable EasyAuth ------------------------------------------------
Write-Host ""
Write-Host "➡️  Step 5/6: Enabling EasyAuth on Web + API container apps"
$Issuer = "https://login.microsoftonline.com/$TenantId/v2.0"

function Configure-EasyAuth($CaName, $ClientId, $Audience) {
  az containerapp auth microsoft update -n $CaName -g $ResourceGroup `
    --client-id $ClientId `
    --client-secret-name $CaSecretName `
    --tenant-id $TenantId `
    --issuer $Issuer `
    --allowed-token-audiences $Audience `
    --yes --output none
}

Configure-EasyAuth $ApiName $ApiClientId $ApiIdentifierUri
Configure-EasyAuth $WebName $WebClientId $WebIdentifierUri

az containerapp auth update -n $WebName -g $ResourceGroup --enabled true --unauthenticated-client-action AllowAnonymous --output none
az containerapp auth update -n $ApiName -g $ResourceGroup --enabled true --unauthenticated-client-action AllowAnonymous --output none
Write-Host "  ✓ EasyAuth providers configured"

# --- Step 6: Env vars + allowedApplications + lockdown ----------------------
Write-Host ""
Write-Host "➡️  Step 6/6: Wiring env vars and caller allowlist"

az containerapp update -n $WebName -g $ResourceGroup `
  --set-env-vars "APP_WEB_CLIENT_ID=$WebClientId" "APP_WEB_SCOPE=$WebScopeValue" "APP_API_SCOPE=$ApiScopeValue" "APP_AUTH_ENABLED=true" `
  --output none
Write-Host "  ✓ Web env vars updated"

$authUrl = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.App/containerApps/$ApiName/authConfigs/current?api-version=2024-03-01"
$current = az rest --method get --url $authUrl | ConvertFrom-Json
if (-not $current.properties) { $current | Add-Member -MemberType NoteProperty -Name properties -Value (@{}) }
if (-not $current.properties.identityProviders) { $current.properties | Add-Member -MemberType NoteProperty -Name identityProviders -Value (@{}) }
if (-not $current.properties.identityProviders.azureActiveDirectory) { $current.properties.identityProviders | Add-Member -MemberType NoteProperty -Name azureActiveDirectory -Value (@{}) }
$aad = $current.properties.identityProviders.azureActiveDirectory
if (-not $aad.validation) { $aad | Add-Member -MemberType NoteProperty -Name validation -Value (@{}) }
if (-not $aad.validation.defaultAuthorizationPolicy) { $aad.validation | Add-Member -MemberType NoteProperty -Name defaultAuthorizationPolicy -Value (@{}) }
$policy = $aad.validation.defaultAuthorizationPolicy
$allowed = @()
if ($policy.allowedApplications) { $allowed = @($policy.allowedApplications) }
if ($allowed -notcontains $WebClientId) { $allowed += $WebClientId }
$policy.allowedApplications = $allowed

$tmp = New-TemporaryFile
$current | ConvertTo-Json -Depth 20 | Out-File -FilePath $tmp -Encoding utf8
Retry { az rest --method put --url $authUrl --headers "Content-Type=application/json" --body "@$tmp" | Out-Null }
Remove-Item $tmp
Write-Host "  ✓ API 'allowed applications' includes Web client id"

az containerapp auth update -n $WebName -g $ResourceGroup --unauthenticated-client-action RedirectToLoginPage --output none
az containerapp auth update -n $ApiName -g $ResourceGroup --unauthenticated-client-action Return401 --output none
Write-Host "  ✓ Unauthenticated requests: Web → login, API → 401"

Write-Host ""
Write-Host "============================================================"
Write-Host "🔐 Auth configuration complete."
Write-Host "  Web client id : $WebClientId"
Write-Host "  API client id : $ApiClientId"
Write-Host "  Web scope     : $WebScopeValue"
Write-Host "  API scope     : $ApiScopeValue"
if (-not $ConsentOk) { Write-Host "  ⚠️  Admin consent pending — see step 3 above." }
Write-Host "  Note: EasyAuth rollout can take up to 10 minutes."
Write-Host "============================================================"
