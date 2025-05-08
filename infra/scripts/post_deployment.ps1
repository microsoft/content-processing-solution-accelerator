# Stop script on any error
$ErrorActionPreference = "Stop"

Write-Host "🔍 Fetching container app info from azd environment..."

# Load values from azd env
$CONTAINER_WEB_APP_NAME = azd env get-value CONTAINER_WEB_APP_NAME
$CONTAINER_WEB_APP_FQDN = azd env get-value CONTAINER_WEB_APP_FQDN

$CONTAINER_API_APP_NAME = azd env get-value CONTAINER_API_APP_NAME
$CONTAINER_API_APP_FQDN = azd env get-value CONTAINER_API_APP_FQDN

# Get subscription and resource group (assuming same for both)
$SUBSCRIPTION_ID = azd env get-value AZURE_SUBSCRIPTION_ID
$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

# Construct Azure Portal URLs
$WEB_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
$API_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"

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

# Write-Host ""
# Write-Host "📦 Follow Next steps to import Schemas:"
# Write-Host "👉 Run the following commands in your terminal:"
# $CurrentPath = Get-Location
# Write-Host ""
# Write-Host "   cd $FullPath"
# Write-Host "   ./register_schema.ps1 https://$CONTAINER_API_APP_FQDN/schemavault/ schema_info_ps1.json"
