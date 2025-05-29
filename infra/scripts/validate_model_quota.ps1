param (
    [string]$Location,
    [string]$Model,
    [string]$DeploymentType = "Standard",
    [int]$Capacity
)

# Verify all required parameters are provided
$MissingParams = @()

if (-not $Location) {
    $MissingParams += "location"
}

if (-not $Model) {
    $MissingParams += "model"
}

if (-not $Capacity) {
    $MissingParams += "capacity"
}

if (-not $DeploymentType) {
    $MissingParams += "deployment-type"
}

if ($MissingParams.Count -gt 0) {
    Write-Error "❌ ERROR: Missing required parameters: $($MissingParams -join ', ')"
    Write-Host "Usage: .\validate_model_quota.ps1 -Location <LOCATION> -Model <MODEL> -Capacity <CAPACITY> [-DeploymentType <DEPLOYMENT_TYPE>]"
    exit 1
}

if ($DeploymentType -ne "Standard" -and $DeploymentType -ne "GlobalStandard") {
    Write-Error "❌ ERROR: Invalid deployment type: $DeploymentType. Allowed values are 'Standard' or 'GlobalStandard'."
    exit 1
}

$ModelType = "OpenAI.$DeploymentType.$Model"

Write-Host "🔍 Checking quota for $ModelType in $Location ..."

# Get model quota information
$ModelInfo = az cognitiveservices usage list --location $Location --query "[?name.value=='$ModelType']" --output json | ConvertFrom-Json

if (-not $ModelInfo) {
    Write-Information "❌ ERROR: No quota information found for model: $Model in location: $Location for model type: $ModelType."
    exit 1
}

if ($ModelInfo) {
    $CurrentValue = ($ModelInfo | Where-Object { $_.name.value -eq $ModelType }).currentValue
    $Limit = ($ModelInfo | Where-Object { $_.name.value -eq $ModelType }).limit

    $CurrentValue = [int]($CurrentValue -replace '\.0+$', '') # Remove decimals
    $Limit = [int]($Limit -replace '\.0+$', '') # Remove decimals

    $Available = $Limit - $CurrentValue
    Write-Host "✅ Model available - Model: $ModelType | Used: $CurrentValue | Limit: $Limit | Available: $Available"

    if ($Available -lt $Capacity) {
        Write-Error "❌ ERROR: Insufficient quota for model: $Model in location: $Location. Available: $Available, Requested: $Capacity."
        exit 1
    }
    else {
        Write-Host "✅ Sufficient quota for model: $Model in location: $Location. Available: $Available, Requested: $Capacity."
    }
}