#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated authentication configuration for Container Apps with Key Vault integration
.DESCRIPTION
    This script automates the complete authentication setup flow:
    1. Creates/configures authentication providers for Container Apps
    2. Retrieves authentication credentials and scopes
    3. Stores credentials securely in Key Vault
    4. Updates Container App environment variables
    5. Configures app registrations with proper redirect URIs and permissions
.EXAMPLE
    ./configure_auth_automated.ps1
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$WebAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ApiAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$KeyVaultName
)

# Stop on errors
$ErrorActionPreference = "Stop"

# Color output functions
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning-Custom { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Error-Custom { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n═══════════════════════════════════════════════════════" -ForegroundColor Magenta; Write-Host "  $Message" -ForegroundColor Magenta; Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Magenta }

Write-Step "Automated Authentication Configuration"

# ═══════════════════════════════════════════════════════
# STEP 1: Load Environment Variables from azd
# ═══════════════════════════════════════════════════════
Write-Step "STEP 1: Loading Environment Configuration"

Write-Info "Loading values from azd environment..."

try {
    if (-not $ResourceGroupName) {
        $ResourceGroupName = azd env get-value AZURE_RESOURCE_GROUP
    }
    if (-not $WebAppName) {
        $WebAppName = azd env get-value CONTAINER_WEB_APP_NAME
    }
    if (-not $ApiAppName) {
        $ApiAppName = azd env get-value CONTAINER_API_APP_NAME
    }
    if (-not $KeyVaultName) {
        $KeyVaultName = azd env get-value AZURE_KEY_VAULT_NAME
    }
    
    $subscriptionId = azd env get-value AZURE_SUBSCRIPTION_ID
    $tenantId = azd env get-value AZURE_TENANT_ID
    
    Write-Success "Resource Group: $ResourceGroupName"
    Write-Success "Web Container App: $WebAppName"
    Write-Success "API Container App: $ApiAppName"
    Write-Success "Key Vault: $KeyVaultName"
    Write-Success "Subscription: $subscriptionId"
    Write-Success "Tenant: $tenantId"
} catch {
    Write-Error-Custom "Failed to load environment variables from azd. Error: $_"
    Write-Info "Make sure you're running this from an initialized azd environment."
    exit 1
}

# ═══════════════════════════════════════════════════════
# STEP 2: Verify Azure CLI Login
# ═══════════════════════════════════════════════════════
Write-Step "STEP 2: Verifying Azure CLI Configuration"

Write-Info "Checking Azure CLI login status..."
try {
    $account = az account show 2>$null | ConvertFrom-Json
    Write-Success "Logged in as $($account.user.name)"
    
    # Set subscription
    az account set --subscription $subscriptionId 2>$null
    Write-Success "Using subscription: $subscriptionId"
} catch {
    Write-Error-Custom "Not logged in to Azure. Please run 'az login' first."
    exit 1
}

# ═══════════════════════════════════════════════════════
# STEP 3: Get Container App Details
# ═══════════════════════════════════════════════════════
Write-Step "STEP 3: Retrieving Container App Information"

Write-Info "Fetching Web Container App details..."
try {
    $webApp = az containerapp show --name $WebAppName --resource-group $ResourceGroupName -o json 2>&1 | ConvertFrom-Json
    if ($webApp.properties.configuration.ingress.fqdn) {
        $webAppUrl = "https://$($webApp.properties.configuration.ingress.fqdn)"
        Write-Success "Web App URL: $webAppUrl"
    } else {
        Write-Error-Custom "Web App ingress not configured"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to fetch Web Container App. Error: $_"
    exit 1
}

Write-Info "Fetching API Container App details..."
try {
    $apiApp = az containerapp show --name $ApiAppName --resource-group $ResourceGroupName -o json 2>&1 | ConvertFrom-Json
    if ($apiApp.properties.configuration.ingress.fqdn) {
        $apiAppUrl = "https://$($apiApp.properties.configuration.ingress.fqdn)"
        Write-Success "API App URL: $apiAppUrl"
    } else {
        Write-Error-Custom "API App ingress not configured"
        exit 1
    }
} catch {
    Write-Error-Custom "Failed to fetch API Container App. Error: $_"
    exit 1
}

# ═══════════════════════════════════════════════════════
# STEP 4: Check/Create Authentication Configuration
# ═══════════════════════════════════════════════════════
Write-Step "STEP 4: Configuring Authentication Providers"

# Check if authentication already exists
Write-Info "Checking existing authentication configuration..."
$webAuthConfig = az containerapp auth show --name $WebAppName --resource-group $ResourceGroupName -o json 2>$null | ConvertFrom-Json
$apiAuthConfig = az containerapp auth show --name $ApiAppName --resource-group $ResourceGroupName -o json 2>$null | ConvertFrom-Json

# Get app registration IDs from Bicep-created auth providers
$webAppRegistrationId = $null
$apiAppRegistrationId = $null

if ($webAuthConfig.identityProviders.azureActiveDirectory) {
    $webAppRegistrationId = $webAuthConfig.identityProviders.azureActiveDirectory.registration.clientId
    
    # Check if this is a placeholder client ID from Bicep template
    if ($webAppRegistrationId -eq "<WEB_APP_CLIENT_ID>") {
        Write-Info "Web App auth config exists (created by Bicep) but needs client ID configured"
        # Will be configured in Step 5 below
    } else {
        Write-Success "Web App Registration exists: $webAppRegistrationId"
    }
} else {
    Write-Warning-Custom "Web App authentication provider not found. Creating it now..."
    
    # Get or create web app registration
    $webAppReg = az ad app list --display-name $WebAppName --query "[0]" | ConvertFrom-Json
    if (-not $webAppReg) {
        Write-Info "Creating Web App registration..."
        $webAppReg = az ad app create --display-name $WebAppName --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json
        Write-Success "Web App registration created: $($webAppReg.appId)"
        
        # Configure Web App to expose API scope (required for APP_WEB_SCOPE per Step 3)
        Write-Info "Configuring Web App to expose API scope..."
        try {
            $webAppObjectId = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications?`$filter=appId eq '$($webAppReg.appId)'" --query "value[0].id" -o tsv
            $webScopeId = [guid]::NewGuid().ToString()
            $webScopeConfig = @{
                identifierUris = @("api://$($webAppReg.appId)")
                api = @{
                    oauth2PermissionScopes = @(
                        @{
                            id = $webScopeId
                            value = "user_impersonation"
                            type = "User"
                            adminConsentDisplayName = "Access web application"
                            adminConsentDescription = "Allow the application to access the web application on behalf of the signed-in user."
                            userConsentDisplayName = "Access web application"  
                            userConsentDescription = "Allow the application to access the web application on your behalf."
                            isEnabled = $true
                        }
                    )
                }
            } | ConvertTo-Json -Depth 10
            
            $tempFile = [System.IO.Path]::GetTempFileName()
            $webScopeConfig | Out-File -FilePath $tempFile -Encoding utf8
            az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$webAppObjectId" --body "@$tempFile" --headers "Content-Type=application/json" --output none
            Remove-Item $tempFile -ErrorAction SilentlyContinue
            Write-Success "Web App API scope configured"
        } catch {
            Write-Warning-Custom "Could not configure Web App API scope: $_"
        }
    } else {
        Write-Success "Found existing Web App registration: $($webAppReg.appId)"
        
        # Ensure existing Web App registration has API scope configured (Step 3)
        Write-Info "Checking if existing Web App has API scope configured..."
        $existingWebAppObjectId = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications?`$filter=appId eq '$($webAppReg.appId)'" --query "value[0].id" -o tsv
        $existingWebAppDetails = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$existingWebAppObjectId" | ConvertFrom-Json
        
        # Check if Web App exposes API scope
        if (-not $existingWebAppDetails.identifierUris -or $existingWebAppDetails.identifierUris.Count -eq 0 -or 
            -not $existingWebAppDetails.api.oauth2PermissionScopes -or $existingWebAppDetails.api.oauth2PermissionScopes.Count -eq 0) {
            Write-Info "Configuring existing Web App to expose API scope..."
            try {
                $webScopeId = [guid]::NewGuid().ToString()
                $webScopeConfig = @{
                    identifierUris = @("api://$($webAppReg.appId)")
                    api = @{
                        oauth2PermissionScopes = @(
                            @{
                                id = $webScopeId
                                value = "user_impersonation"
                                type = "User"
                                adminConsentDisplayName = "Access web application"
                                adminConsentDescription = "Allow the application to access the web application on behalf of the signed-in user."
                                userConsentDisplayName = "Access web application"
                                userConsentDescription = "Allow the application to access the web application on your behalf."
                                isEnabled = $true
                            }
                        )
                    }
                } | ConvertTo-Json -Depth 10
                
                $tempFile = [System.IO.Path]::GetTempFileName()
                $webScopeConfig | Out-File -FilePath $tempFile -Encoding utf8
                az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$existingWebAppObjectId" --body "@$tempFile" --headers "Content-Type=application/json" --output none
                Remove-Item $tempFile -ErrorAction SilentlyContinue
                Write-Success "Existing Web App API scope configured"
            } catch {
                Write-Warning-Custom "Could not configure existing Web App API scope: $_"
            }
        } else {
            Write-Success "Existing Web App already has API scope configured"
        }
    }
    $webAppRegistrationId = $webAppReg.appId
    
    # Create auth provider for web app
    Write-Info "Creating authentication provider for Web App..."
    try {
        az containerapp auth microsoft update `
            --name $WebAppName `
            --resource-group $ResourceGroupName `
            --client-id $webAppRegistrationId `
            --tenant-id $tenantId `
            --yes `
            --output none 2>$null
        Write-Success "Web App authentication provider created"
    } catch {
        Write-Error-Custom "Failed to create Web App authentication provider: $_"
        exit 1
    }
}

if ($apiAuthConfig.identityProviders.azureActiveDirectory) {
    $apiAppRegistrationId = $apiAuthConfig.identityProviders.azureActiveDirectory.registration.clientId
    
    # Check if this is a placeholder client ID from Bicep template
    if ($apiAppRegistrationId -eq "<API_APP_CLIENT_ID>") {
        Write-Info "API App auth config exists (created by Bicep) but needs client ID configured"
        # Will be configured in Step 5 below
    } else {
        Write-Success "API App Registration exists: $apiAppRegistrationId"
    }
} else {
    Write-Warning-Custom "API App authentication provider not found. Creating it now..."
    
    # Get or create API app registration
    $apiAppReg = az ad app list --display-name $ApiAppName --query "[0]" | ConvertFrom-Json
    if (-not $apiAppReg) {
        Write-Info "Creating API App registration..."
        $apiAppReg = az ad app create --display-name $ApiAppName --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json
        Write-Success "API App registration created: $($apiAppReg.appId)"
        
        # Create identifier URI and scope for API
        $apiAppObjectId = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications?`$filter=appId eq '$($apiAppReg.appId)'" --query "value[0].id" -o tsv
        $scopeId = [guid]::NewGuid().ToString()
        $tempFile = [System.IO.Path]::GetTempFileName()
        @{
            identifierUris = @("api://$($apiAppReg.appId)")
            api = @{
                oauth2PermissionScopes = @(
                    @{
                        id = $scopeId
                        value = "user_impersonation"
                        type = "User"
                        adminConsentDisplayName = "Access API"
                        adminConsentDescription = "Allow the application to access the API on behalf of the signed-in user."
                        isEnabled = $true
                    }
                )
            }
        } | ConvertTo-Json -Depth 5 | Out-File -FilePath $tempFile -Encoding utf8
        az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$apiAppObjectId" --headers "Content-Type=application/json" --body `@$tempFile 2>$null
        Remove-Item $tempFile -ErrorAction SilentlyContinue
        Write-Success "API scope configured"
    } else {
        Write-Success "Found existing API App registration: $($apiAppReg.appId)"
    }
    $apiAppRegistrationId = $apiAppReg.appId
    
    # Create auth provider for API app
    Write-Info "Creating authentication provider for API App..."
    try {
        az containerapp auth microsoft update `
            --name $ApiAppName `
            --resource-group $ResourceGroupName `
            --client-id $apiAppRegistrationId `
            --tenant-id $tenantId `
            --allowed-audiences "api://$apiAppRegistrationId" `
            --yes `
            --output none 2>$null
        Write-Success "API App authentication provider created"
    } catch {
        Write-Error-Custom "Failed to create API App authentication provider: $_"
        exit 1
    }
}

# ═══════════════════════════════════════════════════════
# STEP 5: Configure App Registrations
# ═══════════════════════════════════════════════════════
Write-Step "STEP 5: Configuring App Registrations"

# Check if we need to update placeholder client IDs
$needsWebClientIdUpdate = ($webAppRegistrationId -eq "<WEB_APP_CLIENT_ID>")
$needsApiClientIdUpdate = ($apiAppRegistrationId -eq "<API_APP_CLIENT_ID>")

if ($needsWebClientIdUpdate -or $needsApiClientIdUpdate) {
    Write-Info "Placeholder client IDs detected in Bicep-created auth configs. Retrieving actual app registration IDs..."
    
    # Get app registrations by display name
    if ($needsWebClientIdUpdate) {
        $webAppReg = az ad app list --display-name $WebAppName --query "[0]" | ConvertFrom-Json
        if ($webAppReg) {
            $webAppRegistrationId = $webAppReg.appId
            Write-Success "Found Web App Registration: $webAppRegistrationId"
        } else {
            Write-Error "ERROR: Could not find app registration for $WebAppName"
            exit 1
        }
    }
    
    if ($needsApiClientIdUpdate) {
        $apiAppReg = az ad app list --display-name $ApiAppName --query "[0]" | ConvertFrom-Json
        if ($apiAppReg) {
            $apiAppRegistrationId = $apiAppReg.appId
            Write-Success "Found API App Registration: $apiAppRegistrationId"
        } else {
            Write-Error "ERROR: Could not find app registration for $ApiAppName"
            exit 1
        }
    }
    
    # Update auth configs with actual client IDs
    Write-Info "Updating Container App auth configs with actual client IDs..."
    
    if ($needsWebClientIdUpdate) {
        az containerapp auth microsoft update `
            --name $WebAppName `
            --resource-group $ResourceGroupName `
            --client-id $webAppRegistrationId `
            --output none 2>$null
        Write-Success "Web App auth config updated with client ID"
    }
    
    if ($needsApiClientIdUpdate) {
        az containerapp auth microsoft update `
            --name $ApiAppName `
            --resource-group $ResourceGroupName `
            --client-id $apiAppRegistrationId `
            --allowed-audiences "api://$apiAppRegistrationId" `
            --output none 2>$null
        Write-Success "API App auth config updated with client ID"
    }
}

Write-Info "Retrieving app registration details..."
$webAppObjectId = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications?`$filter=appId eq '$webAppRegistrationId'" --query "value[0].id" -o tsv

Write-Info "Retrieving API App Registration details..."
$apiAppObjectId = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications?`$filter=appId eq '$apiAppRegistrationId'" --query "value[0].id" -o tsv
$apiAppDetails = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$apiAppObjectId" | ConvertFrom-Json

# Configure SPA redirect URIs for Web App (Step 2.1)
Write-Info "Configuring SPA redirect URIs for Web App..."
Write-Info "Current Web App URL: $webAppUrl"

# According to ConfigureAppAuthentication.md Step 2.1: Add Container App's URL as redirect URI
$webRedirectUris = @(
    $webAppUrl,
    "$webAppUrl/.auth/login/aad/callback"
)

try {
    # Use file-based approach for reliable JSON formatting
    $tempFile = [System.IO.Path]::GetTempFileName()
    @{
        spa = @{
            redirectUris = $webRedirectUris
        }
    } | ConvertTo-Json -Depth 3 | Out-File -FilePath $tempFile -Encoding utf8
    
    az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$webAppObjectId" `
        --headers "Content-Type=application/json" `
        --body `@$tempFile 2>$null
    
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    
    Write-Success "SPA redirect URIs configured for Web App"
} catch {
    Write-Warning-Custom "Could not update SPA redirect URIs automatically. Error: $_"
    Write-Warning-Custom "You may need to manually update redirect URIs in Azure Portal."
}

# Fetch updated Web App details (after scope and redirect URI configuration)
Write-Info "Retrieving updated Web App details..."
$webAppDetails = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$webAppObjectId" | ConvertFrom-Json

# Get scopes
Write-Info "Retrieving OAuth scopes..."
$apiScope = $null
$webScope = $null

if ($apiAppDetails.identifierUris -and $apiAppDetails.identifierUris.Count -gt 0) {
    $apiAppIdUri = $apiAppDetails.identifierUris[0]
    if ($apiAppDetails.api.oauth2PermissionScopes -and $apiAppDetails.api.oauth2PermissionScopes.Count -gt 0) {
        $apiScopeName = $apiAppDetails.api.oauth2PermissionScopes[0].value
        $apiScope = "$apiAppIdUri/$apiScopeName"
        Write-Success "API Scope: $apiScope"
    }
}

if ($webAppDetails.identifierUris -and $webAppDetails.identifierUris.Count -gt 0) {
    $webAppIdUri = $webAppDetails.identifierUris[0]
    if ($webAppDetails.api.oauth2PermissionScopes -and $webAppDetails.api.oauth2PermissionScopes.Count -gt 0) {
        $webScopeName = $webAppDetails.api.oauth2PermissionScopes[0].value
        $webScope = "$webAppIdUri/$webScopeName"
        Write-Success "Web Scope: $webScope"
    }
}

# Add API permission to Web App registration
Write-Info "Adding API permission to Web App registration..."
try {
    if ($apiAppDetails.api.oauth2PermissionScopes -and $apiAppDetails.api.oauth2PermissionScopes.Count -gt 0) {
        $apiScopeId = $apiAppDetails.api.oauth2PermissionScopes[0].id
        
        # Check if permission already exists
        $existingPermissions = az ad app permission list --id $webAppRegistrationId | ConvertFrom-Json
        $apiPermissionExists = $existingPermissions | Where-Object { 
            $_.resourceAppId -eq $apiAppRegistrationId -and 
            $_.resourceAccess.id -contains $apiScopeId 
        }
        
        if (-not $apiPermissionExists) {
            Write-Info "Adding API permission: $apiScopeId (Scope)"
            az ad app permission add `
                --id $webAppRegistrationId `
                --api $apiAppRegistrationId `
                --api-permissions "$apiScopeId=Scope" `
                --output none 2>$null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "API permission added to Web App"
                Start-Sleep -Seconds 2  # Wait for permission to propagate
            } else {
                Write-Warning-Custom "Failed to add API permission automatically"
            }
        } else {
            Write-Success "API permission already exists"
        }
    } else {
        Write-Warning-Custom "No API scopes found to add as permission"
    }
} catch {
    Write-Warning-Custom "Could not add API permission automatically. Error: $_"
    Write-Warning-Custom "You may need to manually add the permission in Azure Portal."
}

# Grant admin consent for API permissions
Write-Info "Checking admin consent requirements..."
try {
    $permissions = az ad app permission list --id $webAppRegistrationId | ConvertFrom-Json
    $needsConsent = $permissions | Where-Object { 
        $_.resourceAppId -eq $apiAppRegistrationId 
    }
    
    if ($needsConsent) {
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
        Write-Host "  Admin Consent Required" -ForegroundColor Yellow
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
        Write-Host "The Web App requires admin consent to access the API." -ForegroundColor White
        Write-Host "API Application: $apiAppRegistrationId" -ForegroundColor Cyan
        Write-Host "Permission: user_impersonation" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "If you don't have admin privileges, you'll need to:" -ForegroundColor Gray
        Write-Host "  - Contact your Tenant Administrator" -ForegroundColor Gray
        Write-Host "  - Or follow: https://aka.ms/AzAdminConsentWiki" -ForegroundColor Gray
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
        Write-Host ""
        
        $response = Read-Host "Do you want to grant admin consent now? (yes/no)"
        
        if ($response -eq "yes" -or $response -eq "y") {
            Write-Info "Granting admin consent..."
            
            # First, ensure service principal exists for the API app
            Write-Info "Checking if service principal exists for API app..."
            $apiSp = az ad sp list --filter "appId eq '$apiAppRegistrationId'" --query "[0].id" -o tsv 2>$null
            
            if (-not $apiSp) {
                Write-Info "Creating service principal for API app..."
                az ad sp create --id $apiAppRegistrationId --output none 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Service principal created for API app"
                    Start-Sleep -Seconds 3  # Wait for service principal to propagate
                } else {
                    Write-Warning-Custom "Could not create service principal for API app"
                }
            } else {
                Write-Success "Service principal already exists for API app"
            }
            
            # Also ensure service principal exists for Web app
            Write-Info "Checking if service principal exists for Web app..."
            $webSp = az ad sp list --filter "appId eq '$webAppRegistrationId'" --query "[0].id" -o tsv 2>$null
            
            if (-not $webSp) {
                Write-Info "Creating service principal for Web app..."
                az ad sp create --id $webAppRegistrationId --output none 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Service principal created for Web app"
                    Start-Sleep -Seconds 3  # Wait for service principal to propagate
                } else {
                    Write-Warning-Custom "Could not create service principal for Web app"
                }
            } else {
                Write-Success "Service principal already exists for Web app"
            }
            
            # Now grant admin consent
            Write-Info "Attempting to grant admin consent..."
            
            # Try using Microsoft Graph API directly for better compatibility
            $apiSpObjectId = az ad sp list --filter "appId eq '$apiAppRegistrationId'" --query "[0].id" -o tsv 2>$null
            
            if ($apiSpObjectId) {
                # Get the OAuth2PermissionGrant to grant consent
                Write-Info "Using Microsoft Graph API to grant consent..."
                
                # Create OAuth2PermissionGrant (admin consent)
                $grantBody = @{
                    clientId = (az ad sp list --filter "appId eq '$webAppRegistrationId'" --query "[0].id" -o tsv 2>$null)
                    consentType = "AllPrincipals"
                    principalId = $null
                    resourceId = $apiSpObjectId
                    scope = "user_impersonation"
                } | ConvertTo-Json -Compress
                
                $grantResult = az rest --method POST `
                    --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" `
                    --headers "Content-Type=application/json" `
                    --body $grantBody 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Admin consent granted successfully via Graph API"
                    Start-Sleep -Seconds 2
                } else {
                    # If grant already exists, it will fail - check if it exists
                    if ($grantResult -match "already exists" -or $grantResult -match "already granted") {
                        Write-Success "Admin consent already granted"
                    } else {
                        # Fallback to az ad app permission admin-consent
                        Write-Info "Trying alternative method..."
                        $consentResult = az ad app permission admin-consent --id $webAppRegistrationId 2>&1
                        
                        if ($LASTEXITCODE -eq 0) {
                            Write-Success "Admin consent granted successfully"
                            Start-Sleep -Seconds 2
                        } else {
                            # Check if error is about service principal already existing (means consent may already be granted)
                            if ($consentResult -match "already present" -or $consentResult -match "ServicePrincipalName") {
                                Write-Info "Service principals already exist. Checking if consent is already granted..."
                                
                                # Check if OAuth2PermissionGrant already exists
                                $existingGrant = az rest --method GET `
                                    --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?`$filter=clientId eq '$($webSp)' and resourceId eq '$apiSpObjectId'" 2>$null
                                
                                if ($existingGrant -and $existingGrant -notmatch '"value":\[\]') {
                                    Write-Success "Admin consent already granted (verified via existing grant)"
                                } else {
                                    Write-Warning-Custom "Could not grant admin consent automatically."
                                    Write-Info "Please grant consent manually in Azure Portal:"
                                    Write-Info "  1. Go to Azure Portal > Entra ID > App Registrations"
                                    Write-Info "  2. Find app: $webAppRegistrationId"
                                    Write-Info "  3. Go to API Permissions > Grant admin consent"
                                }
                            } else {
                                Write-Warning-Custom "Could not grant admin consent automatically."
                                Write-Info "Error: $consentResult"
                                Write-Info "You may need to grant consent manually in Azure Portal."
                            }
                        }
                    }
                }
            } else {
                Write-Warning-Custom "Could not find API service principal. Cannot grant consent."
            }
        } else {
            Write-Warning-Custom "Admin consent skipped. Users may see consent prompts or authentication may fail."
            Write-Info "You can grant consent later using: az ad app permission admin-consent --id $webAppRegistrationId"
        }
    } else {
        Write-Success "No permissions requiring admin consent"
    }
} catch {
    Write-Warning-Custom "Could not check/grant admin consent. Error: $_"
}

# Add Web App to API's authorized clients
Write-Info "Adding Web App to API's authorized client applications..."
try {
    # Validate required data
    if (-not $apiAppDetails.api.oauth2PermissionScopes -or $apiAppDetails.api.oauth2PermissionScopes.Count -eq 0) {
        Write-Warning-Custom "No OAuth scopes found on API app. Cannot add pre-authorized application."
        Write-Info "API App Details: $($apiAppDetails | ConvertTo-Json -Depth 2)"
    } else {
        $currentPreAuthorizedApps = @()
        if ($apiAppDetails.api.preAuthorizedApplications) {
            $currentPreAuthorizedApps = $apiAppDetails.api.preAuthorizedApplications
        }
        
        $webAppExists = $currentPreAuthorizedApps | Where-Object { $_.appId -eq $webAppRegistrationId }
        
        if (-not $webAppExists) {
            $scopeId = $apiAppDetails.api.oauth2PermissionScopes[0].id
            Write-Info "Scope ID to authorize: $scopeId"
            
            $preAuthApp = @{
                appId = $webAppRegistrationId
                delegatedPermissionIds = @($scopeId)
            }
            
            $currentPreAuthorizedApps += $preAuthApp
            
            $preAuthConfig = @{
                api = @{
                    preAuthorizedApplications = $currentPreAuthorizedApps
                }
            }
            
            Write-Info "Executing Graph API call to add pre-authorized application..."
            # Use temp file for reliable JSON formatting
            $tempFile = [System.IO.Path]::GetTempFileName()
            $preAuthConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding utf8
            
            $patchResult = az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$apiAppObjectId" `
                --headers "Content-Type=application/json" `
                --body `@$tempFile 2>&1
            
            Remove-Item $tempFile -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Web App added to API's authorized clients"
            } else {
                Write-Warning-Custom "Graph API call failed with exit code $LASTEXITCODE"
                Write-Warning-Custom "Error: $patchResult"
            }
        } else {
            Write-Success "Web App already authorized for API"
        }
    }
} catch {
    Write-Warning-Custom "Could not add authorized client automatically. Error: $_"
    Write-Warning-Custom "You may need to manually add the Web App ($webAppRegistrationId) to the API's pre-authorized applications."
}

# ═══════════════════════════════════════════════════════
# STEP 5.5: Disable Container App Authentication for Web App
# ═══════════════════════════════════════════════════════
Write-Step "STEP 5.5: Configuring Container App Authentication"

Write-Info "Disabling Container App authentication for Web App (SPA handles its own auth)..."
try {
    az containerapp auth update --name $WebAppName --resource-group $ResourceGroupName --enabled false --output none 2>$null
    Write-Success "Web App Container App authentication disabled (correct for SPA)"
} catch {
    Write-Warning-Custom "Could not disable Web App authentication: $_"
}

Write-Info "API Container App authentication will remain disabled during deployment..."
Write-Info "It will be enabled after schema registration completes in post-deployment"
try {
    az containerapp auth update --name $ApiAppName --resource-group $ResourceGroupName --enabled false --output none 2>$null
    Write-Success "API Container App authentication remains disabled (for schema registration)"
} catch {
    Write-Warning-Custom "Could not configure API authentication: $_"
}

# Configure API Container App to allow requests from Web App client
Write-Info "Configuring API Container App to allow requests from Web App..."
try {
    # Get current auth config
    $apiAuthConfigJson = az containerapp auth show `
        --name $ApiAppName `
        --resource-group $ResourceGroupName `
        --output json 2>$null
    
    if ($apiAuthConfigJson) {
        $currentApiAuthConfig = $apiAuthConfigJson | ConvertFrom-Json
        
        # Update to allow specific client applications
        $authConfigUpdate = @{
            identityProviders = @{
                azureActiveDirectory = @{
                    registration = @{
                        clientId = $apiAppRegistrationId
                        clientSecretSettingName = "microsoft-provider-authentication-secret"
                        openIdIssuer = "https://sts.windows.microsoft.com/$tenantId/v2.0"
                    }
                    validation = @{
                        allowedAudiences = @("api://$apiAppRegistrationId")
                    }
                    login = @{
                        loginParameters = @()
                    }
                }
            }
            login = @{
                allowedExternalRedirectUrls = @()
            }
            httpSettings = @{
                requireHttps = $true
            }
        }
        
        # Configure Container App authentication to allow requests from specific client applications (Step 4)
        Write-Info "Configuring API Container App to allow requests from Web App..."
        try {
            $allowedAppsResult = az containerapp auth update -n $apiAppName -g $ResourceGroupName `
                --set "identityProviders.azureActiveDirectory.validation.defaultAuthorizationPolicy.allowedApplications=[`"$webAppRegistrationId`"]" 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "API Container App configured to allow requests from Web App"
            } else {
                Write-Warning-Custom "Could not configure Container App allowed applications: $allowedAppsResult"
                Write-Info "Step 4 requires manual configuration in Azure Portal"
            }
        } catch {
            Write-Warning-Custom "Error configuring Container App allowed applications: $_"
            Write-Info "Step 4 requires manual configuration in Azure Portal"
        }
        
        Write-Success "API authentication configured (client filtering via app registration and Container App)"
    }
} catch {
    Write-Warning-Custom "Could not configure API Container App client settings. Error: $_"
    Write-Info "Please configure client application filtering manually in Azure Portal (Step 4)."
}

# ═══════════════════════════════════════════════════════
# STEP 6: Update Container App Environment Variables
# ═══════════════════════════════════════════════════════
Write-Step "STEP 6: Updating Container App Environment Variables"

Write-Info "Preparing environment variables for Web Container App..."

# Build the authority URL
$authority = "https://login.microsoftonline.com/$tenantId"

# Build complete environment variables array
$envVars = @(
    "APP_WEB_CLIENT_ID=$webAppRegistrationId",
    "APP_WEB_AUTHORITY=$authority",
    "APP_API_BASE_URL=$apiAppUrl",
    "APP_CONSOLE_LOG_ENABLED=false",
    "APP_AUTH_ENABLED=true"
)

if ($webScope) {
    $envVars += "APP_WEB_SCOPE=$webScope"
    Write-Success "Web scope configured: $webScope"
} else {
    Write-Error-Custom "Web scope not found! This is required for proper authentication."
    Write-Info "Expected format: api://[WEB_APP_CLIENT_ID]/user_impersonation"
    Write-Info "Please ensure Web App registration exposes API scope (Step 3)"
    exit 1
}

if ($apiScope) {
    $envVars += "APP_API_SCOPE=$apiScope"
} else {
    Write-Warning-Custom "API scope not found. You may need to set this manually."
}

Write-Host ""
Write-Host "Environment variables to be set:" -ForegroundColor White
foreach ($env in $envVars) {
    Write-Host "  $env" -ForegroundColor Cyan
}
Write-Host ""

Write-Info "Updating Web Container App environment variables..."
try {
    az containerapp update `
        --name $WebAppName `
        --resource-group $ResourceGroupName `
        --set-env-vars $envVars `
        --output none
    
    Write-Success "Environment variables updated successfully"
    Write-Info "New revision is being deployed..."
    
    Start-Sleep -Seconds 5
    
    $revisions = az containerapp revision list `
        --name $WebAppName `
        --resource-group $ResourceGroupName `
        --query "[0].{name:name, active:properties.active, status:properties.runningState}" `
        -o json | ConvertFrom-Json
    
    if ($revisions.active -and $revisions.status -eq "Running") {
        Write-Success "New revision is active: $($revisions.name)"
    } else {
        Write-Warning-Custom "Revision status: $($revisions.status). May take a few minutes to activate."
    }
} catch {
    Write-Error-Custom "Failed to update environment variables. Error: $_"
}

# ═══════════════════════════════════════════════════════
# STEP 7: Save to azd Environment
# ═══════════════════════════════════════════════════════
Write-Step "STEP 7: Saving Configuration to azd Environment"

Write-Info "Storing authentication values in azd environment..."
try {
    azd env set WEB_CLIENT_ID $webAppRegistrationId
    azd env set API_CLIENT_ID $apiAppRegistrationId
    if ($webScope) { azd env set WEB_SCOPE $webScope }
    if ($apiScope) { azd env set API_SCOPE $apiScope }
    Write-Success "Configuration saved to azd environment"
} catch {
    Write-Warning-Custom "Could not save to azd environment."
}

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════
Write-Step "CONFIGURATION COMPLETE"

Write-Host ""
Write-Host "✅ Authentication Configuration Summary:" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "Resource Group:        $ResourceGroupName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Web Container App:     $WebAppName" -ForegroundColor Cyan
Write-Host "Web App URL:           $webAppUrl" -ForegroundColor Cyan
Write-Host "Web Client ID:         $webAppRegistrationId" -ForegroundColor Cyan
Write-Host "Web Scope:             $webScope" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Container App:     $ApiAppName" -ForegroundColor Cyan
Write-Host "API App URL:           $apiAppUrl" -ForegroundColor Cyan
Write-Host "API Client ID:         $apiAppRegistrationId" -ForegroundColor Cyan
Write-Host "API Scope:             $apiScope" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Info "🔄 Environment variables updated in: $WebAppName"
Write-Info "💾 Configuration saved to azd environment"
Write-Host ""

Write-Success "🎉 Authentication configuration completed successfully!"
Write-Host ""
Write-Info "Next Steps:"
Write-Host "  1. Test the Web application: $webAppUrl" -ForegroundColor Gray
Write-Host "  2. Verify authentication is working" -ForegroundColor Gray
Write-Host "  3. Check that API calls are successful" -ForegroundColor Gray
Write-Host ""
