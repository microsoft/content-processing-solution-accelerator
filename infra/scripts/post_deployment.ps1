# Stop script on any error
$ErrorActionPreference = "Stop"

Write-Host "🔍 Fetching container app info from azd environment..."

# Load values from azd env
$CONTAINER_WEB_APP_NAME = azd env get-value CONTAINER_WEB_APP_NAME
$CONTAINER_WEB_APP_FQDN = azd env get-value CONTAINER_WEB_APP_FQDN

$CONTAINER_API_APP_NAME = azd env get-value CONTAINER_API_APP_NAME
$CONTAINER_API_APP_FQDN = azd env get-value CONTAINER_API_APP_FQDN

$CONTAINER_WORKFLOW_APP_NAME = azd env get-value CONTAINER_WORKFLOW_APP_NAME

# Get subscription and resource group (assuming same for both)
$SUBSCRIPTION_ID = azd env get-value AZURE_SUBSCRIPTION_ID
$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

# Construct Azure Portal URLs
$WEB_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
$API_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"
$WORKFLOW_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WORKFLOW_APP_NAME"

# Get the current script's directory
$ScriptDir = $PSScriptRoot

# Navigate from infra/scripts → root → src/api/data/data.sh
$DataScriptPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples\schemas"

# Resolve to an absolute path
$FullPath = Resolve-Path $DataScriptPath

# Output
Write-Host ""
Write-Host "🧭 Web App Details:"
Write-Host "  ✅ Name: $CONTAINER_WEB_APP_NAME"
Write-Host "  🌐 Endpoint: $CONTAINER_WEB_APP_FQDN"
Write-Host "  🔗 Portal URL: $WEB_APP_PORTAL_URL"

Write-Host ""
Write-Host "🧭 API App Details:"
Write-Host "  ✅ Name: $CONTAINER_API_APP_NAME"
Write-Host "  🌐 Endpoint: $CONTAINER_API_APP_FQDN"
Write-Host "  🔗 Portal URL: $API_APP_PORTAL_URL"

Write-Host ""
Write-Host "🧭 Workflow App Details:"
Write-Host "  ✅ Name: $CONTAINER_WORKFLOW_APP_NAME"
Write-Host "  🔗 Portal URL: $WORKFLOW_APP_PORTAL_URL"

Write-Host ""
Write-Host "📦 Registering schemas and creating schema set..."
Write-Host "  ⏳ Waiting for API to be ready..."

$MaxRetries = 10
$RetryInterval = 15
$ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
$ApiReady = $false

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$ApiBaseUrl/schemavault/" -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ API is ready."
            $ApiReady = $true
            break
        }
    } catch {
        # Ignore – API not ready yet
    }
    Write-Host "  Attempt $i/$MaxRetries – API not ready, retrying in ${RetryInterval}s..."
    Start-Sleep -Seconds $RetryInterval
}

if (-not $ApiReady) {
    Write-Host "  ⚠️  API did not become ready after $MaxRetries attempts. Skipping schema registration."
    Write-Host "  👉 Run manually: cd $FullPath && python register_schema.py $ApiBaseUrl schema_info.json"
} else {
    python "$FullPath/register_schema.py" $ApiBaseUrl "$FullPath/schema_info.json"
    Write-Host "  ✅ Schema registration complete."
}
