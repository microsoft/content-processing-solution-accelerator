# =============================================================================
# ACR Build and Push Script (PowerShell)
# This script builds container images remotely using Azure Container Registry
# and updates the Container Apps to use the new images.
# =============================================================================
 param(
    [string]$ResourceGroupName
)

$ErrorActionPreference = "Stop"
 
Write-Host "============================================================"
Write-Host "ACR Build and Push - Starting..."
Write-Host "============================================================"
 
if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) {

    Write-Host "Using azd environment values..."

    $ACR_NAME                    = azd env get-value CONTAINER_REGISTRY_NAME
    $ACR_LOGIN_SERVER            = azd env get-value CONTAINER_REGISTRY_LOGIN_SERVER
    $RESOURCE_GROUP              = azd env get-value AZURE_RESOURCE_GROUP
    $CONTAINER_APP_NAME          = azd env get-value CONTAINER_APP_NAME
    $CONTAINER_API_APP_NAME      = azd env get-value CONTAINER_API_APP_NAME
    $CONTAINER_WEB_APP_NAME      = azd env get-value CONTAINER_WEB_APP_NAME
    $CONTAINER_WORKFLOW_APP_NAME = azd env get-value CONTAINER_WORKFLOW_APP_NAME
    $USER_IDENTITY_ID            = azd env get-value CONTAINER_APP_USER_IDENTITY_ID

}
else {

    Write-Host "Using existing deployment from Resource Group: $ResourceGroupName"

    $RESOURCE_GROUP = $ResourceGroupName

    # Get ACR
    $acr = az acr list `
        --resource-group $RESOURCE_GROUP `
        --query "[0]" `
        | ConvertFrom-Json

    if (-not $acr) {
        throw "No Azure Container Registry found in $RESOURCE_GROUP"
    }

    $ACR_NAME = $acr.name
    $ACR_LOGIN_SERVER = $acr.loginServer

    # Get Container Apps
    $containerApps = az containerapp list `
        --resource-group $RESOURCE_GROUP `
        | ConvertFrom-Json

    foreach ($app in $containerApps) {

        switch -Wildcard ($app.name) {

            "*-api" {
                $CONTAINER_API_APP_NAME = $app.name
            }

            "*-web" {
                $CONTAINER_WEB_APP_NAME = $app.name
            }

            "*-wkfl" {
                $CONTAINER_WORKFLOW_APP_NAME = $app.name
            }

            default {
                $CONTAINER_APP_NAME = $app.name
            }
        }
    }

    # Optional - Get Managed Identity
    $USER_IDENTITY_ID = (
        az identity list `
            --resource-group $RESOURCE_GROUP `
            --query "[0].id" `
            -o tsv
    )
}
 
$IMAGE_TAG = "latest"

# Detect whether this is a WAF deployment
$DeploymentType = az group show `
    --name $RESOURCE_GROUP `
    --query "tags.Type" `
    -o tsv

$IsWAF = $DeploymentType -eq "WAF"

$OriginalPublicNetworkAccess = $null

if ($IsWAF) {

    Write-Host ""
    Write-Host "WAF deployment detected."

    # Save current setting
    $OriginalPublicNetworkAccess = az acr show `
        --name $ACR_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "publicNetworkAccess" `
        -o tsv

    if ($OriginalPublicNetworkAccess -eq "Disabled") {

        Write-Host "Temporarily enabling ACR Public Network Access..."

        az acr update `
            --name $ACR_NAME `
            --resource-group $RESOURCE_GROUP `
            --public-network-enabled true

        if ($LASTEXITCODE -ne 0) {
            throw "Failed to enable ACR Public Network Access."
        }

        Start-Sleep -Seconds 20
    }
}
 
# Get the script directory and navigate to repo root
$ScriptDir = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
 
Write-Host ""
Write-Host "  ACR Name: $ACR_NAME"
Write-Host "  ACR Login Server: $ACR_LOGIN_SERVER"
Write-Host "  Resource Group: $RESOURCE_GROUP"
Write-Host "  Image Tag: $IMAGE_TAG"
Write-Host ""

try {
    # =============================================================================
    # Step 1: Build and push images to ACR using az acr build
    # =============================================================================

    Write-Host "============================================================"
    Write-Host "Step 1: Building and pushing images to ACR..."
    Write-Host "============================================================"
    
    # --- ContentProcessor ---
    Write-Host ""
    Write-Host "  Building contentprocessor image..."
    az acr build `
      --registry $ACR_NAME `
      --image "contentprocessor:$IMAGE_TAG" `
      --file "$RepoRoot\src\ContentProcessor\Dockerfile" `
      --platform linux `
      "$RepoRoot\src\ContentProcessor"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to build contentprocessor image" }
    Write-Host "  [OK] contentprocessor image built and pushed."
    
    # --- ContentProcessorAPI ---
    Write-Host ""
    Write-Host "  Building contentprocessorapi image..."
    az acr build `
      --registry $ACR_NAME `
      --image "contentprocessorapi:$IMAGE_TAG" `
      --file "$RepoRoot\src\ContentProcessorAPI\Dockerfile" `
      --platform linux `
      "$RepoRoot\src\ContentProcessorAPI"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to build contentprocessorapi image" }
    Write-Host "  [OK] contentprocessorapi image built and pushed."
    
    # --- ContentProcessorWeb ---
    Write-Host ""
    Write-Host "  Building contentprocessorweb image..."
    az acr build `
      --registry $ACR_NAME `
      --image "contentprocessorweb:$IMAGE_TAG" `
      --file "$RepoRoot\src\ContentProcessorWeb\Dockerfile" `
      --platform linux `
      "$RepoRoot\src\ContentProcessorWeb"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to build contentprocessorweb image" }
    Write-Host "  [OK] contentprocessorweb image built and pushed."
    
    # --- ContentProcessorWorkflow ---
    Write-Host ""
    Write-Host "  Building contentprocessorworkflow image..."
    az acr build `
      --registry $ACR_NAME `
      --image "contentprocessorworkflow:$IMAGE_TAG" `
      --file "$RepoRoot\src\ContentProcessorWorkflow\Dockerfile" `
      --platform linux `
      "$RepoRoot\src\ContentProcessorWorkflow"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to build contentprocessorworkflow image" }
    Write-Host "  [OK] contentprocessorworkflow image built and pushed."
    
    Write-Host ""
    Write-Host "  All images built and pushed successfully."
    
    # =============================================================================
    # Step 2: Update Container Apps to use the new images from ACR
    # =============================================================================
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "Step 2: Updating Container Apps with new images..."
    Write-Host "============================================================"
    
    # --- Update ContentProcessor Container App ---
    Write-Host ""
    Write-Host "  Updating $CONTAINER_APP_NAME..."
    az containerapp update `
      --name $CONTAINER_APP_NAME `
      --resource-group $RESOURCE_GROUP `
      --image "$ACR_LOGIN_SERVER/contentprocessor:$IMAGE_TAG"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to update $CONTAINER_APP_NAME" }
    Write-Host "  [OK] $CONTAINER_APP_NAME updated."
    
    # --- Update ContentProcessorAPI Container App ---
    Write-Host ""
    Write-Host "  Updating $CONTAINER_API_APP_NAME..."
    az containerapp update `
      --name $CONTAINER_API_APP_NAME `
      --resource-group $RESOURCE_GROUP `
      --image "$ACR_LOGIN_SERVER/contentprocessorapi:$IMAGE_TAG"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to update $CONTAINER_API_APP_NAME" }
    Write-Host "  [OK] $CONTAINER_API_APP_NAME updated."
    
    # --- Update ContentProcessorWeb Container App ---
    Write-Host ""
    Write-Host "  Updating $CONTAINER_WEB_APP_NAME..."
    az containerapp update `
      --name $CONTAINER_WEB_APP_NAME `
      --resource-group $RESOURCE_GROUP `
      --image "$ACR_LOGIN_SERVER/contentprocessorweb:$IMAGE_TAG"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to update $CONTAINER_WEB_APP_NAME" }
    Write-Host "  [OK] $CONTAINER_WEB_APP_NAME updated."
    
    # --- Update ContentProcessorWorkflow Container App ---
    Write-Host ""
    Write-Host "  Updating $CONTAINER_WORKFLOW_APP_NAME..."
    az containerapp update `
      --name $CONTAINER_WORKFLOW_APP_NAME `
      --resource-group $RESOURCE_GROUP `
      --image "$ACR_LOGIN_SERVER/contentprocessorworkflow:$IMAGE_TAG"
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to update $CONTAINER_WORKFLOW_APP_NAME" }
    Write-Host "  [OK] $CONTAINER_WORKFLOW_APP_NAME updated."
    
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "ACR Build and Push - Completed Successfully!"
    Write-Host "============================================================"

}
finally {

    if ($IsWAF -and $OriginalPublicNetworkAccess -eq "Disabled") {

        Write-Host ""
        Write-Host "Restoring ACR Public Network Access..."

        az acr update `
            --name $ACR_NAME `
            --resource-group $RESOURCE_GROUP `
            --public-network-enabled false

        if ($LASTEXITCODE -eq 0) {
            Write-Host "ACR Public Network Access restored."
        }
        else {
            Write-Warning "Failed to restore ACR Public Network Access."
        }
    }
}