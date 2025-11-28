# Stop script on any error
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Post-Deployment Configuration                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

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
$DataScriptPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples"

# Resolve to an absolute path
$FullPath = Resolve-Path $DataScriptPath

# Output
Write-Host ""
Write-Host "🧭 Web App Details:"
Write-Host "  ✅ Name: $CONTAINER_WEB_APP_NAME"
Write-Host "  🌐 Endpoint: https://$CONTAINER_WEB_APP_FQDN"
Write-Host "  🔗 Portal URL: $WEB_APP_PORTAL_URL"

Write-Host ""
Write-Host "🧭 API App Details:"
Write-Host "  ✅ Name: $CONTAINER_API_APP_NAME"
Write-Host "  🌐 Endpoint: https://$CONTAINER_API_APP_FQDN"
Write-Host "  🔗 Portal URL: $API_APP_PORTAL_URL"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

# ═══════════════════════════════════════════════════════
# STEP 1: Register Schemas and Upload Sample Data
# ═══════════════════════════════════════════════════════
Write-Host "📦 STEP 1: Schema Registration & Sample Data Upload" -ForegroundColor Magenta
Write-Host ""

$uploadData = Read-Host "Would you like to register schemas and upload sample data now? (yes/no)"

if ($uploadData -eq "yes") {
    Write-Host ""
    Write-Host "Starting schema registration and data upload..." -ForegroundColor Cyan
    
    # Disable API authentication temporarily for schema registration
    Write-Host "ℹ Disabling API authentication for schema registration..." -ForegroundColor Cyan
    try {
        az containerapp auth update --name $CONTAINER_API_APP_NAME --resource-group $RESOURCE_GROUP --enabled false --output none 2>$null
        Write-Host "✓ API authentication disabled" -ForegroundColor Green
        
        # Wait for authentication state to propagate
        Write-Host "⏳ Waiting for authentication changes to propagate (30 seconds)..." -ForegroundColor Cyan
        Start-Sleep -Seconds 30
        
        # Verify API is accessible without auth
        Write-Host "🔍 Verifying API accessibility..." -ForegroundColor Cyan
        $healthCheck = try {
            $response = Invoke-WebRequest -Uri "https://$CONTAINER_API_APP_FQDN/health" -Method GET -UseBasicParsing -TimeoutSec 10 2>$null
            $response.StatusCode
        } catch {
            $_.Exception.Response.StatusCode.value__
        }
        
        if ($healthCheck -eq 200) {
            Write-Host "✓ API is accessible (authentication disabled successfully)" -ForegroundColor Green
        } else {
            Write-Host "⚠ API returned status $healthCheck - authentication may still be active" -ForegroundColor Yellow
            Write-Host "  Waiting additional 20 seconds..." -ForegroundColor Gray
            Start-Sleep -Seconds 20
        }
    } catch {
        Write-Host "⚠ Could not disable API authentication: $_" -ForegroundColor Yellow
        Write-Host "Schema registration may fail if authentication is enabled" -ForegroundColor Gray
    }
    
    # Get API Client ID from azd environment for authentication
    $ApiClientId = azd env get-values --output json | ConvertFrom-Json | Select-Object -ExpandProperty API_CLIENT_ID -ErrorAction SilentlyContinue
    
    $RegisterScriptPath = Join-Path $FullPath "register_and_upload.sh"
    
    $schemaRegistrationSuccess = $false
    
    if (Test-Path $RegisterScriptPath) {
        try {
            Push-Location $FullPath
            
            # Check if Git Bash is available
            $gitBashPath = "C:\Program Files\Git\bin\bash.exe"
            if (Test-Path $gitBashPath) {
                Write-Host "Using Git Bash to execute the script..." -ForegroundColor Gray
                
                # Pass API Client ID for authentication if available
                if ($ApiClientId) {
                    & $gitBashPath $RegisterScriptPath "https://$CONTAINER_API_APP_FQDN" $ApiClientId
                } else {
                    Write-Host "⚠ API Client ID not found. Attempting without authentication..." -ForegroundColor Yellow
                    & $gitBashPath $RegisterScriptPath "https://$CONTAINER_API_APP_FQDN"
                }
                
                # Check if schema registration succeeded by checking exit code
                if ($LASTEXITCODE -eq 0) {
                    $schemaRegistrationSuccess = $true
                    Write-Host ""
                    Write-Host "✅ Schema registration and data upload completed successfully!" -ForegroundColor Green
                } else {
                    Write-Host ""
                    Write-Host "❌ Schema registration failed with exit code: $LASTEXITCODE" -ForegroundColor Red
                    Write-Host ""
                    Write-Host "Common causes:" -ForegroundColor Yellow
                    Write-Host "  • API authentication is still enabled (propagation delay)" -ForegroundColor Gray
                    Write-Host "  • Network connectivity issues" -ForegroundColor Gray
                    Write-Host "  • API container not running" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "Please fix the issues and run schema registration manually:" -ForegroundColor Yellow
                    Write-Host "  cd $FullPath" -ForegroundColor Cyan
                    Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "❌ Post-deployment cannot continue until schema registration succeeds." -ForegroundColor Red
                    Write-Host "   Exiting..." -ForegroundColor Red
                    Pop-Location
                    exit 1
                }
            } else {
                Write-Host "⚠ Git Bash not found. Please run the script manually:" -ForegroundColor Yellow
                Write-Host "  cd $FullPath" -ForegroundColor Gray
                if ($ApiClientId) {
                    Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN $ApiClientId" -ForegroundColor Gray
                } else {
                    Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN" -ForegroundColor Gray
                }
                Write-Host ""
                Write-Host "❌ Cannot continue without Git Bash. Exiting..." -ForegroundColor Red
                exit 1
            }
            
            Pop-Location
        } catch {
            Write-Host ""
            Write-Host "❌ Schema registration encountered an error: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please run schema registration manually:" -ForegroundColor Yellow
            Write-Host "  cd $FullPath" -ForegroundColor Cyan
            if ($ApiClientId) {
                Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN $ApiClientId" -ForegroundColor Cyan
            } else {
                Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN" -ForegroundColor Cyan
            }
            Write-Host ""
            Write-Host "❌ Post-deployment cannot continue. Exiting..." -ForegroundColor Red
            Pop-Location
            exit 1
        }
    } else {
        Write-Host "❌ Registration script not found at: $RegisterScriptPath" -ForegroundColor Red
        Write-Host "Cannot continue without schema registration. Exiting..." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "⏭ Skipping schema registration and data upload." -ForegroundColor Yellow
    Write-Host "⚠ Warning: Authentication configuration requires schemas to be registered first!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To register schemas later, run:" -ForegroundColor Gray
    Write-Host "  cd $FullPath" -ForegroundColor Gray
    Write-Host "  bash register_and_upload.sh https://$CONTAINER_API_APP_FQDN" -ForegroundColor Cyan
    Write-Host ""
    
    $continueWithoutSchemas = Read-Host "Do you want to continue with authentication configuration anyway? (yes/no)"
    if ($continueWithoutSchemas -ne "yes") {
        Write-Host ""
        Write-Host "Exiting post-deployment. Run 'azd provision' again when ready." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

# ═══════════════════════════════════════════════════════
# STEP 2: Configure Authentication
# ═══════════════════════════════════════════════════════
Write-Host "🔐 STEP 2: Authentication Configuration" -ForegroundColor Magenta
Write-Host ""

$configureAuth = Read-Host "Would you like to configure authentication now? (yes/no)"

if ($configureAuth -eq "yes") {
    Write-Host ""
    Write-Host "Starting automated authentication configuration..." -ForegroundColor Cyan
    
    $AuthScriptPath = Join-Path $ScriptDir "configure_auth_automated.ps1"
    
    if (Test-Path $AuthScriptPath) {
        try {
            & $AuthScriptPath
            Write-Host ""
            Write-Host "✅ Authentication configuration completed!" -ForegroundColor Green
        } catch {
            Write-Host "⚠ Authentication configuration encountered an issue: $_" -ForegroundColor Yellow
            Write-Host "You can run it manually later with:" -ForegroundColor Gray
            Write-Host "  $AuthScriptPath" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠ Authentication script not found at: $AuthScriptPath" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "⏭ Skipping authentication configuration." -ForegroundColor Yellow
    Write-Host "To configure later, run:" -ForegroundColor Gray
    Write-Host "  $ScriptDir\configure_auth_automated.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

# ═══════════════════════════════════════════════════════
# STEP 3: Enable API Authentication
# ═══════════════════════════════════════════════════════
Write-Host ""
Write-Host "🔐 STEP 3: Enable API Authentication" -ForegroundColor Magenta
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host ""
Write-Host "Now that schema registration is complete, enabling API authentication..." -ForegroundColor White
Write-Host ""

try {
    az containerapp auth update `
        --name $CONTAINER_API_APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --enabled true `
        --output none 2>$null
    
    Write-Host "✓ API Container App authentication enabled successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "ℹ The API is now protected and requires authentication" -ForegroundColor Cyan
} catch {
    Write-Host "⚠ Warning: Could not enable API authentication: $_" -ForegroundColor Yellow
    Write-Host "You may need to enable it manually in Azure Portal" -ForegroundColor Gray
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "🎉 Post-deployment configuration completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Summary:" -ForegroundColor White
Write-Host "  • Web App: https://$CONTAINER_WEB_APP_FQDN" -ForegroundColor Cyan
Write-Host "  • API App: https://$CONTAINER_API_APP_FQDN" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Test your web application" -ForegroundColor Gray
Write-Host "  2. Verify authentication is working" -ForegroundColor Gray
Write-Host "  3. Check schema processing functionality" -ForegroundColor Gray
Write-Host ""
