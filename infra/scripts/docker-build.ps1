
# Get all environment values
$envValues = azd env get-values --output json | ConvertFrom-Json

# Full path to this script's folder
$ScriptDir = $PSScriptRoot

# Resolve relative paths based on the script location
$TemplateFile = Join-Path $ScriptDir "..\deploy_container_registry.bicep"
$ContentProcessorPath = Join-Path $ScriptDir "..\..\src\ContentProcessor"
$ContentApiPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI"
$ContentWebPath = Join-Path $ScriptDir "..\..\src\ContentProcessorWeb"

# Define function to build and push Docker images
function Build-And-Push-Image {
    param (
        [string]$IMAGE_NAME,
        [string]$BUILD_PATH,
        [string]$CONTAINER_APP_NAME
    )

    $IMAGE_URI = "$ACR_NAME.azurecr.io/$($IMAGE_NAME):$AZURE_ENV_IMAGETAG"

    Write-Host "Building Docker image: $IMAGE_URI"
    docker build $BUILD_PATH --no-cache -t $IMAGE_URI
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker image: $IMAGE_URI"
        exit 1
    }

    Write-Host "Pushing Docker image to ACR: $IMAGE_URI"
    docker push $IMAGE_URI
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push Docker image: $IMAGE_URI"
        exit 1
    }

    Write-Host "Docker image pushed successfully: $IMAGE_URI"

    if($CONTAINER_APP_NAME)
    {
        $timestamp = Get-Date -Format "yyyyMMddHHmmss"
        Write-Host "Updating the Container app registry server & image"
        az containerapp registry set --name $CONTAINER_APP_NAME --resource-group $AZURE_RESOURCE_GROUP --server "$ACR_NAME.azurecr.io" --identity $CONTAINER_APP_USER_IDENTITY_ID --only-show-errors
        az containerapp update --name $CONTAINER_APP_NAME --resource-group $AZURE_RESOURCE_GROUP --image $IMAGE_URI --set-env-vars REFRESH_TIMESTAMP=$timestamp --only-show-errors
        Write-Host "Updated the registry for Container: $CONTAINER_APP_NAME"
    }
}

function Ensure-AzLogin {
    try {
        $accountInfo = az account show --only-show-errors | ConvertFrom-Json
        Write-Host "Already logged in as: $($accountInfo.user.name)"
    } catch {
        Write-Host "No active Azure session found. Logging in..."
        az login --only-show-errors | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Azure login failed."
            exit 1
        }

        # Set Azure subscription
        az account set --subscription "$AZURE_SUBSCRIPTION_ID"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to set Azure subscription."
            exit 1
        }
    }
}

# Validate and fetch required parameters from azd env if missing
function Get-AzdEnvValueOrDefault {
    param (
        [Parameter(Mandatory = $true)]
        [string]$KeyName,

        [Parameter(Mandatory = $false)]
        [string]$DefaultValue = "",

        [Parameter(Mandatory = $false)]
        [bool]$Required = $false
    )

    # Check if key exists
    if ($envValues.PSObject.Properties.Name -contains $KeyName) {
        return $envValues.$KeyName
    }

    # Key doesn't exist
    if ($Required) {
        Write-Error "Required environment key '$KeyName' not found in azd environment."
        exit 1
    } else {
        return $DefaultValue
    }
}

# Read the required details from Bicep deployment output
$AZURE_SUBSCRIPTION_ID = Get-AzdEnvValueOrDefault -KeyName "AZURE_SUBSCRIPTION_ID" -Required $true
$ENV_NAME = Get-AzdEnvValueOrDefault -KeyName "AZURE_ENV_NAME" -Required $true
$CONTAINER_APP_USER_IDENTITY_ID = Get-AzdEnvValueOrDefault -KeyName "CONTAINER_APP_USER_IDENTITY_ID" -Required $true
$AZURE_RESOURCE_GROUP = Get-AzdEnvValueOrDefault -KeyName "AZURE_RESOURCE_GROUP" -Required $true
$CONTAINER_APP_USER_PRINCIPAL_ID = Get-AzdEnvValueOrDefault -KeyName "CONTAINER_APP_USER_PRINCIPAL_ID" -Required $true
$AZURE_ENV_IMAGETAG = Get-AzdEnvValueOrDefault -KeyName "AZURE_ENV_IMAGETAG" -DefaultValue "latest"
$CONTAINER_WEB_APP_NAME=Get-AzdEnvValueOrDefault -KeyName "CONTAINER_WEB_APP_NAME" -Required $true
$CONTAINER_API_APP_NAME=Get-AzdEnvValueOrDefault -KeyName "CONTAINER_API_APP_NAME" -Required $true
$CONTAINER_APP_NAME=Get-AzdEnvValueOrDefault -KeyName "CONTAINER_APP_NAME" -Required $true
$ACR_NAME = Get-AzdEnvValueOrDefault -KeyName "CONTAINER_REGISTRY_NAME" -Required $true
$ACR_ENDPOINT = Get-AzdEnvValueOrDefault -KeyName "CONTAINER_REGISTRY_LOGIN_SERVER" -Required $true

# Export the variables for later use
Write-Host "Using the following parameters:"
Write-Host "AZURE_SUBSCRIPTION_ID = $AZURE_SUBSCRIPTION_ID"
Write-Host "ENV_NAME = $ENV_NAME"
Write-Host "AZURE_RESOURCE_GROUP = $AZURE_RESOURCE_GROUP"
Write-Host "AZURE_ENV_IMAGETAG = $AZURE_ENV_IMAGETAG"

Ensure-AzLogin

Write-Output "Starting build process."

# Deploy container registry
# Write-Host "Deploying container registry"
# $OUTPUTS = az deployment group create --resource-group $AZURE_RESOURCE_GROUP --template-file "$TemplateFile" --parameters environmentName=$ENV_NAME acrPullPrincipalIds="['$($CONTAINER_APP_USER_PRINCIPAL_ID)']" --query "properties.outputs" --output json | ConvertFrom-Json

# Extract ACR name and endpoint
# $ACR_NAME = $OUTPUTS.createdAcrName.value
# $ACR_ENDPOINT = $OUTPUTS.acrEndpoint.value

Write-Host "Extracted ACR Name: $ACR_NAME"
Write-Host "Extracted ACR Endpoint: $ACR_ENDPOINT"

# # Set ACR details as environment variables in AZD
# azd env set ACR_NAME $ACR_NAME
# azd env set ACR_ENDPOINT $ACR_ENDPOINT

# Write-Host "Saved ACR details to AZD environment variables."

# Log in to Azure Container Registry
Write-Host "Logging into Azure Container Registry: $ACR_NAME with endpoint $ACR_ENDPOINT"
az acr login -n $ACR_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to log in to ACR"
    exit 1
}

# Build and push images
Build-And-Push-Image "contentprocessor" "$ContentProcessorPath" $CONTAINER_APP_NAME
Build-And-Push-Image "contentprocessorapi" "$ContentApiPath" $CONTAINER_API_APP_NAME
Build-And-Push-Image "contentprocessorweb" "$ContentWebPath" $CONTAINER_WEB_APP_NAME

Write-Host "All Docker images built and pushed successfully."