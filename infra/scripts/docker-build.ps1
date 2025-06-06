# Define script parameters
param (
    [string]$AZURE_SUBSCRIPTION_ID,
    [string]$ENV_NAME,
    [string]$AZURE_LOCATION,
    [string]$AZURE_RESOURCE_GROUP,
    [string]$USE_LOCAL_BUILD,
    [string]$AZURE_ENV_IMAGETAG
)

# Convert USE_LOCAL_BUILD to Boolean
$USE_LOCAL_BUILD = if ($USE_LOCAL_BUILD -match "^(?i:true)$") { $true } else { $false }

# Validate required parameters
if (-not $AZURE_SUBSCRIPTION_ID -or -not $ENV_NAME -or -not $AZURE_LOCATION -or -not $AZURE_RESOURCE_GROUP) {
    Write-Error "Missing required arguments. Usage: docker-build.ps1 <AZURE_SUBSCRIPTION_ID> <ENV_NAME> <AZURE_LOCATION> <AZURE_RESOURCE_GROUP> <USE_LOCAL_BUILD> <AZURE_ENV_IMAGETAG>"
    exit 1
}

if ($USE_LOCAL_BUILD -eq $false) {
    Write-Output "Local Build not enabled. Using prebuilt image."
    exit 0
}

Write-Output "Local Build enabled. Starting build process."

# Set Azure subscription
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set Azure subscription."
    exit 1
}

# Deploy container registry
Write-Host "Deploying container registry in location: $AZURE_LOCATION"
$OUTPUTS = az deployment group create --resource-group $AZURE_RESOURCE_GROUP --template-file "./infra/deploy_container_registry.bicep" --parameters environmentName=$ENV_NAME --query "properties.outputs" --output json | ConvertFrom-Json

# Extract ACR name and endpoint
$ACR_NAME = $OUTPUTS.createdAcrName.value
$ACR_ENDPOINT = $OUTPUTS.acrEndpoint.value

Write-Host "Extracted ACR Name: $ACR_NAME"
Write-Host "Extracted ACR Endpoint: $ACR_ENDPOINT"

# Store outputs in a .env file
Set-Content -Path .env -Value "ACR_NAME=$ACR_NAME`nACR_ENDPOINT=$ACR_ENDPOINT"

# Set ACR details as environment variables in AZD
azd env set ACR_NAME $ACR_NAME
azd env set ACR_ENDPOINT $ACR_ENDPOINT

Write-Host "Saved ACR details to AZD environment variables."

# Define function to build and push Docker images
function Build-And-Push-Image {
    param (
        [string]$IMAGE_NAME,
        [string]$BUILD_PATH
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
}

# Log in to Azure Container Registry
Write-Host "Logging into Azure Container Registry: $ACR_NAME"
az acr login -n $ACR_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to log in to ACR"
    exit 1
}

# Build and push images
Build-And-Push-Image "contentprocessor" ".\src\ContentProcessor\"
Build-And-Push-Image "contentprocessorapi" ".\src\ContentProcessorAPI\"
Build-And-Push-Image "contentprocessorweb" ".\src\ContentProcessorWeb\"

Write-Host "All Docker images built and pushed successfully."
