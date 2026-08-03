<#
.SYNOPSIS
    Post-deployment script for Content Processing Solution Accelerator.

.DESCRIPTION
    Supports both AVM deployment (with parameters) and azd deployment (with env file).

.PARAMETER ResourceGroupName
    Azure resource group name containing the deployed resources (required for AVM deployment).

.PARAMETER ApiBaseUrl
    Base URL of the API container app (optional - will be auto-discovered if not provided).

.PARAMETER SubscriptionId
    Azure subscription ID (optional - will use current az context if not provided).

.PARAMETER ContentUnderstandingAccountName
    Name of the Content Understanding (AI Services) account to refresh (optional - will be auto-discovered if not provided).

.EXAMPLE
    # AVM deployment with parameters
    .\post_deployment.ps1 -ResourceGroupName "my-rg" -ApiBaseUrl "https://my-api.azurecontainerapps.io"

.EXAMPLE
    # AVM deployment with auto-discovery
    .\post_deployment.ps1 -ResourceGroupName "my-rg"

.EXAMPLE
    # AVM deployment with specific AI Services account
    .\post_deployment.ps1 -ResourceGroupName "my-rg" -ContentUnderstandingAccountName "aicu-myaccount"

.EXAMPLE
    # Traditional azd deployment (uses azd env)
    .\post_deployment.ps1
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl,

    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId,

    [Parameter(Mandatory=$false)]
    [string]$ContentUnderstandingAccountName
)

# Stop script on any error
$ErrorActionPreference = "Stop"

# Determine deployment mode: AVM (with parameters) or AZD (with env file)
$IsAvmDeployment = -not [string]::IsNullOrEmpty($ResourceGroupName)

if ($IsAvmDeployment) {
    Write-Host "[Info] Running in AVM deployment mode with resource group: $ResourceGroupName"

    # Get subscription ID from parameter or current context
    if ([string]::IsNullOrEmpty($SubscriptionId)) {
        $SUBSCRIPTION_ID = (az account show --query id -o tsv 2>$null)
        if ([string]::IsNullOrEmpty($SUBSCRIPTION_ID)) {
            Write-Host "[Error] Could not determine subscription ID. Please provide -SubscriptionId parameter or ensure you are logged in with 'az login'."
            exit 1
        }
        Write-Host "[Info] Using subscription ID from current context: $SUBSCRIPTION_ID"
    } else {
        $SUBSCRIPTION_ID = $SubscriptionId
    }

    $RESOURCE_GROUP = $ResourceGroupName

    # Discover container apps in the resource group
    Write-Host "[Info] Discovering container apps in resource group..."
    $ContainerApps = @(az containerapp list -g $RESOURCE_GROUP --query "[].{name:name, fqdn:properties.configuration.ingress.fqdn}" -o json 2>$null | ConvertFrom-Json)

    if ($ContainerApps.Count -eq 0) {
        Write-Host "[Error] No container apps found in resource group '$RESOURCE_GROUP'."
        exit 1
    }

    # Identify apps by name patterns (matching AVM naming convention)
    $CONTAINER_API_APP = $ContainerApps | Where-Object { $_.name -like "*-api" } | Select-Object -First 1
    $CONTAINER_WEB_APP = $ContainerApps | Where-Object { $_.name -like "*-web" } | Select-Object -First 1
    # Try multiple patterns for workflow app (AVM uses -wkfl)
    $CONTAINER_WORKFLOW_APP = $ContainerApps | Where-Object { $_.name -like "*-wkfl" -or $_.name -like "*-workflow" -or $_.name -like "*-processor" -or $_.name -like "*-worker" } | Select-Object -First 1
    # Try to find the base ContentProcessor app
    $CONTAINER_APP = $ContainerApps | Where-Object { $_.name -like "*-app" } | Select-Object -First 1

    # Safely extract properties with null checks
    $CONTAINER_APP_NAME = if ($CONTAINER_APP) { $CONTAINER_APP.name } else { $null }
    $CONTAINER_APP_FQDN = if ($CONTAINER_APP) { $CONTAINER_APP.fqdn } else { $null }
    $CONTAINER_API_APP_NAME = if ($CONTAINER_API_APP) { $CONTAINER_API_APP.name } else { $null }
    $CONTAINER_API_APP_FQDN = if ($CONTAINER_API_APP) { $CONTAINER_API_APP.fqdn } else { $null }
    $CONTAINER_WEB_APP_NAME = if ($CONTAINER_WEB_APP) { $CONTAINER_WEB_APP.name } else { $null }
    $CONTAINER_WEB_APP_FQDN = if ($CONTAINER_WEB_APP) { $CONTAINER_WEB_APP.fqdn } else { $null }
    $CONTAINER_WORKFLOW_APP_NAME = if ($CONTAINER_WORKFLOW_APP) { $CONTAINER_WORKFLOW_APP.name } else { $null }

    # Use provided API base URL or construct from discovered FQDN
    if (-not [string]::IsNullOrEmpty($ApiBaseUrl)) {
        # Remove trailing slash if present
        $ApiBaseUrl = $ApiBaseUrl.TrimEnd('/')
        Write-Host "[Info] Using provided API base URL: $ApiBaseUrl"
    } elseif (-not [string]::IsNullOrEmpty($CONTAINER_API_APP_FQDN)) {
        $ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
        Write-Host "[Info] Constructed API base URL from discovered FQDN: $ApiBaseUrl"
    } else {
        Write-Host "[Error] Could not determine API base URL. Please provide -ApiBaseUrl parameter or ensure API container app exists."
        exit 1
    }

} else {
    Write-Host "[Info] Running in AZD deployment mode (using azd env)..."

    # Load values from azd env
    $CONTAINER_WEB_APP_NAME = azd env get-value CONTAINER_WEB_APP_NAME
    $CONTAINER_WEB_APP_FQDN = azd env get-value CONTAINER_WEB_APP_FQDN

    $CONTAINER_API_APP_NAME = azd env get-value CONTAINER_API_APP_NAME
    $CONTAINER_API_APP_FQDN = azd env get-value CONTAINER_API_APP_FQDN

    $CONTAINER_WORKFLOW_APP_NAME = azd env get-value CONTAINER_WORKFLOW_APP_NAME

    # Get subscription and resource group (assuming same for both)
    $SUBSCRIPTION_ID = azd env get-value AZURE_SUBSCRIPTION_ID
    $RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

    $ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
}

# Construct Azure Portal URLs (only for apps that exist)
if ($CONTAINER_APP_NAME) {
    $APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_APP_NAME"
} else {
    $APP_PORTAL_URL = $null
}

if ($CONTAINER_WEB_APP_NAME) {
    $WEB_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
} else {
    $WEB_APP_PORTAL_URL = $null
}

if ($CONTAINER_API_APP_NAME) {
    $API_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"
} else {
    $API_APP_PORTAL_URL = $null
}

if ($CONTAINER_WORKFLOW_APP_NAME) {
    $WORKFLOW_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WORKFLOW_APP_NAME"
} else {
    $WORKFLOW_APP_PORTAL_URL = $null
}

# Get the current script's directory
$ScriptDir = $PSScriptRoot

# Navigate from infra/scripts -> root -> src/api/data/data.sh
$DataScriptPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples\schemas"

# Resolve to an absolute path
$FullPath = Resolve-Path $DataScriptPath

# Output deployment information
Write-Host ""
Write-Host "[Info] Content Processor App Details:"
if ($CONTAINER_APP_NAME) {
    Write-Host "  [OK] Name: $CONTAINER_APP_NAME"
    if ($CONTAINER_APP_FQDN) {
        Write-Host "  [URL] Endpoint: $CONTAINER_APP_FQDN"
    }
    if ($APP_PORTAL_URL) {
        Write-Host "  [Link] Portal URL: $APP_PORTAL_URL"
    }
} else {
    Write-Host "  [Info] Content Processor app not found or not deployed."
}

Write-Host ""
Write-Host "[Info] Web App Details:"
if ($CONTAINER_WEB_APP_NAME) {
    Write-Host "  [OK] Name: $CONTAINER_WEB_APP_NAME"
    Write-Host "  [URL] Endpoint: $CONTAINER_WEB_APP_FQDN"
    if ($WEB_APP_PORTAL_URL) {
        Write-Host "  [Link] Portal URL: $WEB_APP_PORTAL_URL"
    }
} else {
    Write-Host "  [Info] Web app not found or not deployed."
}

Write-Host ""
Write-Host "[Info] API App Details:"
if ($CONTAINER_API_APP_NAME) {
    Write-Host "  [OK] Name: $CONTAINER_API_APP_NAME"
    Write-Host "  [URL] Endpoint: $CONTAINER_API_APP_FQDN"
    if ($API_APP_PORTAL_URL) {
        Write-Host "  [Link] Portal URL: $API_APP_PORTAL_URL"
    }
} else {
    Write-Host "  [Info] API app not found or not deployed."
}

Write-Host ""
Write-Host "[Info] Workflow App Details:"
if ($CONTAINER_WORKFLOW_APP_NAME) {
    Write-Host "  [OK] Name: $CONTAINER_WORKFLOW_APP_NAME"
    if ($WORKFLOW_APP_PORTAL_URL) {
        Write-Host "  [Link] Portal URL: $WORKFLOW_APP_PORTAL_URL"
    }
} else {
    Write-Host "  [Info] Workflow app not found or not deployed."
}

Write-Host ""
Write-Host "[Package] Registering schemas and creating schema set..."
Write-Host "  [Wait] Waiting for API to be ready at: $ApiBaseUrl"

$MaxRetries = 10
$RetryInterval = 15
$ApiReady = $false

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$ApiBaseUrl/schemavault/" -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] API is ready."
            $ApiReady = $true
            break
        }
    } catch {
        # Ignore - API not ready yet
    }
    Write-Host "  Attempt $i/$MaxRetries - API not ready, retrying in ${RetryInterval}s..."
    Start-Sleep -Seconds $RetryInterval
}

if (-not $ApiReady) {
    Write-Host "  API did not become ready after $MaxRetries attempts. Skipping schema registration."
    Write-Host "  Run manually after the API is ready."
} else {
    # ---------- Schema registration (no Python dependency) ----------
    $SchemaInfoFile = Join-Path $FullPath "schema_info.json"
    $Manifest = Get-Content $SchemaInfoFile -Raw | ConvertFrom-Json

    $SchemaVaultUrl   = "$ApiBaseUrl/schemavault/"
    $SchemaSetVaultUrl = "$ApiBaseUrl/schemasetvault/"

    # --- Step 1: Register schemas ---
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "Step 1: Register schemas"
    Write-Host ("=" * 60)

    # Fetch existing schemas
    $ExistingSchemas = @()
    try {
        $ExistingSchemas = Invoke-RestMethod -Uri $SchemaVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
        Write-Host "Fetched $($ExistingSchemas.Count) existing schema(s)."
    } catch {
        Write-Host "Warning: Could not fetch existing schemas. Proceeding..."
    }

    $Registered = @{}  # ClassName -> schema Id

    foreach ($entry in $Manifest.schemas) {
        $ClassName   = $entry.ClassName
        $Description = $entry.Description
        $SchemaFile  = Join-Path $FullPath $entry.File

        Write-Host ""
        Write-Host "Processing schema: $ClassName"

        if (-not (Test-Path $SchemaFile)) {
            Write-Host "Error: Schema file '$SchemaFile' does not exist. Skipping..."
            continue
        }

        # Check if already registered
        $existing = $ExistingSchemas | Where-Object { $_.ClassName -eq $ClassName } | Select-Object -First 1
        if ($existing) {
            $schemaId = $existing.Id
            Write-Host "  Schema '$ClassName' already exists with ID: $schemaId"
            $Registered[$ClassName] = $schemaId
            continue
        }

        Write-Host "  Registering new schema '$ClassName'..."

        # Only JSON Schema descriptors are accepted. The legacy .py format
        # was removed as part of the schemavault RCE remediation.
        $extension = [System.IO.Path]::GetExtension($SchemaFile).ToLowerInvariant()
        if ($extension -ne '.json') {
            Write-Host "  Unsupported schema extension '$extension' for '$SchemaFile'. Only .json is accepted. Skipping..."
            continue
        }
        $contentType = 'application/json'

        # Build multipart form data
        $dataPayload = @{ ClassName = $ClassName; Description = $Description } | ConvertTo-Json -Compress
        $fileBytes   = [System.IO.File]::ReadAllBytes($SchemaFile)
        $fileName    = [System.IO.Path]::GetFileName($SchemaFile)

        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        $bodyLines = (
            "--$boundary",
            "Content-Disposition: form-data; name=`"data`"$LF",
            $dataPayload,
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
            "Content-Type: $contentType$LF",
            [System.Text.Encoding]::UTF8.GetString($fileBytes),
            "--$boundary--$LF"
        ) -join $LF

        try {
            $resp = Invoke-RestMethod -Uri $SchemaVaultUrl -Method POST `
                -ContentType "multipart/form-data; boundary=$boundary" `
                -Body $bodyLines -TimeoutSec 60 -ErrorAction Stop
            $schemaId = $resp.Id
            Write-Host "  Successfully registered: $Description's Schema Id - $schemaId"
            $Registered[$ClassName] = $schemaId
        } catch {
            Write-Host "  Failed to upload '$fileName'. Error: $_"
        }
    }

    # --- Step 2: Create schema set ---
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "Step 2: Create schema set"
    Write-Host ("=" * 60)

    $SetName = $Manifest.schemaset.Name
    $SetDesc = $Manifest.schemaset.Description

    $ExistingSets = @()
    try {
        $ExistingSets = Invoke-RestMethod -Uri $SchemaSetVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
        Write-Host "Fetched $($ExistingSets.Count) existing schema set(s)."
    } catch {
        Write-Host "Warning: Could not fetch existing schema sets. Proceeding..."
    }

    $SchemaSetId = $null
    $existingSet = $ExistingSets | Where-Object { $_.Name -eq $SetName } | Select-Object -First 1
    if ($existingSet) {
        $SchemaSetId = $existingSet.Id
        Write-Host "  Schema set '$SetName' already exists with ID: $SchemaSetId"
    } else {
        Write-Host "  Creating schema set '$SetName'..."
        try {
            $setResp = Invoke-RestMethod -Uri $SchemaSetVaultUrl -Method POST `
                -ContentType "application/json" `
                -Body (@{ Name = $SetName; Description = $SetDesc } | ConvertTo-Json) `
                -TimeoutSec 30 -ErrorAction Stop
            $SchemaSetId = $setResp.Id
            Write-Host "  Created schema set '$SetName' with ID: $SchemaSetId"
        } catch {
            Write-Host "  Failed to create schema set. Error: $_"
        }
    }

    if (-not $SchemaSetId) {
        Write-Host "Error: Could not create or find schema set. Aborting step 3."
    } else {
        # --- Step 3: Add schemas to schema set ---
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Step 3: Add schemas to schema set"
        Write-Host ("=" * 60)

        $AlreadyInSet = @()
        try {
            $AlreadyInSet = Invoke-RestMethod -Uri "$SchemaSetVaultUrl$SchemaSetId/schemas" -Method GET -TimeoutSec 30 -ErrorAction Stop
        } catch { }
        $AlreadyInSetIds = $AlreadyInSet | ForEach-Object { $_.Id }

        foreach ($className in $Registered.Keys) {
            $schemaId = $Registered[$className]
            if ($AlreadyInSetIds -contains $schemaId) {
                Write-Host "  Schema '$className' ($schemaId) already in schema set - skipped"
                continue
            }

            try {
                Invoke-RestMethod -Uri "$SchemaSetVaultUrl$SchemaSetId/schemas" -Method POST `
                    -ContentType "application/json" `
                    -Body (@{ SchemaId = $schemaId } | ConvertTo-Json) `
                    -TimeoutSec 30 -ErrorAction Stop | Out-Null
                Write-Host "  Added '$className' ($schemaId) to schema set"
            } catch {
                Write-Host "  Failed to add '$className' to schema set. Error: $_"
            }
        }
    }

    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "Schema registration process completed."
    Write-Host "  Schemas registered: $($Registered.Count)"
    Write-Host ("=" * 60)
}

# --- Refresh Content Understanding Cognitive Services account ---
Write-Host ""
Write-Host ("=" * 60)
Write-Host "Refreshing Content Understanding Cognitive Services account..."
Write-Host ("=" * 60)

$CU_ACCOUNT_NAME = ""
if ($IsAvmDeployment) {
    # In AVM mode, use parameter if provided
    if (-not [string]::IsNullOrEmpty($ContentUnderstandingAccountName)) {
        $CU_ACCOUNT_NAME = $ContentUnderstandingAccountName
        Write-Host "  Using specified Content Understanding account: $CU_ACCOUNT_NAME"
    }
} else {
    # In AZD mode, try to get from azd env
    try {
        $CU_ACCOUNT_NAME = (azd env get-value CONTENT_UNDERSTANDING_ACCOUNT_NAME 2>$null)
        if (-not $CU_ACCOUNT_NAME) { $CU_ACCOUNT_NAME = "" }
    } catch {
        $CU_ACCOUNT_NAME = ""
    }
}

# Verify the account from the env value still exists; if not, fall back to discovering
# the AIServices account in the resource group. This protects against stale .env values
# left over from prior deployments (different template/fork) and against the env value
# pointing to a resource that no longer exists.
if ($CU_ACCOUNT_NAME) {
    # Capture stderr so we can distinguish a real "not found" response from a
    # transient/auth/CLI failure. Only treat the env value as stale when Azure
    # actually reports the resource is missing; for any other error keep the
    # env value untouched and log the underlying error for diagnosability.
    $ShowOutput = az cognitiveservices account show -g $RESOURCE_GROUP -n $CU_ACCOUNT_NAME --output none 2>&1
    if ($LASTEXITCODE -ne 0) {
        $ShowOutputStr = ($ShowOutput | Out-String).Trim()
        if ($ShowOutputStr -match '(?i)ResourceNotFound|was not found|could not be found') {
            Write-Host "  [Warn] Cognitive Services account '$CU_ACCOUNT_NAME' from azd env was not found in resource group '$RESOURCE_GROUP'."
            Write-Host "         The azd env value may be stale. Attempting to discover the AIServices account in the resource group..."
            $CU_ACCOUNT_NAME = ""
        } else {
            Write-Host "  [Warn] Could not verify Cognitive Services account '$CU_ACCOUNT_NAME' (transient or CLI error). Keeping env value and skipping discovery."
            Write-Host "         az error: $ShowOutputStr"
        }
    }
}

if (-not $CU_ACCOUNT_NAME) {
    # Enumerate ALL AIServices accounts (not just the first). When the resource
    # group contains exactly one we auto-recover; when it contains more than one
    # we refuse to guess and ask the user to set the env value explicitly, to
    # avoid persisting the wrong account name into azd env.
    $CuAccounts = @(az cognitiveservices account list -g $RESOURCE_GROUP --query "[?kind=='AIServices'].name" -o tsv 2>$null)
    $CuAccounts = @($CuAccounts | Where-Object { $_ -and $_.Trim() -ne "" })
    if ($CuAccounts.Count -eq 1) {
        $CU_ACCOUNT_NAME = $CuAccounts[0]
        Write-Host "  Discovered AIServices account in resource group: $CU_ACCOUNT_NAME"
        # Refresh the azd env so subsequent runs use the correct value (only in AZD mode)
        if (-not $IsAvmDeployment) {
            try { azd env set CONTENT_UNDERSTANDING_ACCOUNT_NAME $CU_ACCOUNT_NAME 2>$null | Out-Null } catch { }
        }
    } elseif ($CuAccounts.Count -gt 1) {
        Write-Host "  [Warn] Multiple AIServices accounts found in resource group '$RESOURCE_GROUP': $($CuAccounts -join ', ')"
        if ($IsAvmDeployment) {
            Write-Host "         Please specify the correct account name manually. Skipping refresh."
        } else {
            Write-Host "         Please set CONTENT_UNDERSTANDING_ACCOUNT_NAME in azd env to the correct account name. Skipping refresh."
        }
    } else {
        Write-Host "  [Warn] No Content Understanding (AIServices) account found in resource group '$RESOURCE_GROUP'. Skipping refresh."
    }
}

if ($CU_ACCOUNT_NAME) {
    Write-Host "  Refreshing account: $CU_ACCOUNT_NAME in resource group: $RESOURCE_GROUP"
    # Capture stderr so that any Azure CLI error is preserved in deployment
    # logs even though this refresh step is non-fatal.
    $UpdateOutput = az cognitiveservices account update -g $RESOURCE_GROUP -n $CU_ACCOUNT_NAME --tags refresh=true --output none 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Successfully refreshed Cognitive Services account '$CU_ACCOUNT_NAME'."
    } else {
        $UpdateOutputStr = ($UpdateOutput | Out-String).Trim()
        Write-Host "  [Warn] Could not refresh Cognitive Services account '$CU_ACCOUNT_NAME'. Continuing - this step is non-fatal."
        Write-Host "         az error: $UpdateOutputStr"
    }
}
 