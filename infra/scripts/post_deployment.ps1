# Stop script on any error
$ErrorActionPreference = "Stop"

Write-Host "[Search] Fetching container app info from azd environment..."

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

# Navigate from infra/scripts -> root -> src/api/data/data.sh
$DataScriptPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples\schemas"

# Resolve to an absolute path
$FullPath = Resolve-Path $DataScriptPath

# Output
Write-Host ""
Write-Host "[Info] Web App Details:"
Write-Host "  [OK] Name: $CONTAINER_WEB_APP_NAME"
Write-Host "  [URL] Endpoint: $CONTAINER_WEB_APP_FQDN"
Write-Host "  [Link] Portal URL: $WEB_APP_PORTAL_URL"

Write-Host ""
Write-Host "[Info] API App Details:"
Write-Host "  [OK] Name: $CONTAINER_API_APP_NAME"
Write-Host "  [URL] Endpoint: $CONTAINER_API_APP_FQDN"
Write-Host "  [Link] Portal URL: $API_APP_PORTAL_URL"

Write-Host ""
Write-Host "[Info] Workflow App Details:"
Write-Host "  [OK] Name: $CONTAINER_WORKFLOW_APP_NAME"
Write-Host "  [Link] Portal URL: $WORKFLOW_APP_PORTAL_URL"

Write-Host ""
Write-Host "[Package] Registering schemas and creating schema set..."
Write-Host "  [Wait] Waiting for API to be ready..."

$MaxRetries = 10
$RetryInterval = 15
$ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
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

        # Pick MIME type by extension. Both .json (recommended) and .py
        # (legacy) are accepted by the API.
        $extension = [System.IO.Path]::GetExtension($SchemaFile).ToLowerInvariant()
        switch ($extension) {
            '.json' { $contentType = 'application/json' }
            '.py'   { $contentType = 'text/x-python' }
            default {
                Write-Host "  Unsupported schema extension '$extension' for '$SchemaFile'. Skipping..."
                continue
            }
        }

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
