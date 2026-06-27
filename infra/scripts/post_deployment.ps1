# Stop script on any error
$ErrorActionPreference = "Stop"

Write-Host "- Fetching container app info from azd environment..."

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
Write-Host "- Web App Details:"
Write-Host "  - Name: $CONTAINER_WEB_APP_NAME"
Write-Host "  - Endpoint: $CONTAINER_WEB_APP_FQDN"
Write-Host "  - Portal URL: $WEB_APP_PORTAL_URL"

Write-Host ""
Write-Host "- API App Details:"
Write-Host "  - Name: $CONTAINER_API_APP_NAME"
Write-Host "  - Endpoint: $CONTAINER_API_APP_FQDN"
Write-Host "  - Portal URL: $API_APP_PORTAL_URL"

Write-Host ""
Write-Host "- Workflow App Details:"
Write-Host "  - Name: $CONTAINER_WORKFLOW_APP_NAME"
Write-Host "  - Portal URL: $WORKFLOW_APP_PORTAL_URL"

Write-Host ""
Write-Host "- Registering schemas and creating schema set..."
Write-Host "  - Waiting for API to be ready..."

$MaxRetries = 10
$RetryInterval = 15
$ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
$ApiReady = $false

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$ApiBaseUrl/schemavault/" -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  - API is ready."
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

    # --- Step 4: Process sample file bundles ---
    if ($SchemaSetId -and $Registered.Count -gt 0) {
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Step 4: Process sample file bundles"
        Write-Host ("=" * 60)

        $SamplesDir = Resolve-Path (Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples")
        $BundleFolders = @("claim_date_of_loss", "claim_hail")
        $ClaimProcessorUrl = "$ApiBaseUrl/claimprocessor/claims"

        foreach ($bundle in $BundleFolders) {
            $bundleDir = Join-Path $SamplesDir $bundle
            $bundleInfoPath = Join-Path $bundleDir "bundle_info.json"

            if (-not (Test-Path $bundleInfoPath)) {
                Write-Host "  Skipping '$bundle' - no bundle_info.json found."
                continue
            }

            Write-Host ""
            Write-Host "  Processing bundle: $bundle"

            $bundleManifest = Get-Content $bundleInfoPath -Raw | ConvertFrom-Json

            # Step 4a: Create claim batch with schemaset ID
            Write-Host "    - Creating claim batch..."
            try {
                $claimResp = Invoke-RestMethod -Uri $ClaimProcessorUrl -Method PUT `
                    -ContentType "application/json" `
                    -Body (@{ schema_collection_id = $SchemaSetId } | ConvertTo-Json) `
                    -TimeoutSec 30 -ErrorAction Stop
                $claimId = $claimResp.claim_id
                Write-Host "    - Claim batch created with ID: $claimId"
            } catch {
                Write-Host "    - Failed to create claim batch. Error: $_"
                continue
            }

            # Step 4b: Upload each file with its mapped schema ID
            Add-Type -AssemblyName System.Net.Http
            $httpClient = New-Object System.Net.Http.HttpClient
            $httpClient.Timeout = [TimeSpan]::FromSeconds(60)
            $uploadSuccess = $true
            foreach ($entry in $bundleManifest.files) {
                $schemaClass = $entry.schema_class
                $fileName = $entry.file_name
                $filePath = Join-Path $bundleDir $fileName

                if (-not (Test-Path $filePath)) {
                    Write-Host "    - File '$fileName' not found. Skipping."
                    continue
                }

                $schemaId = $Registered[$schemaClass]
                if (-not $schemaId) {
                    Write-Host "    - No schema ID found for '$schemaClass'. Skipping '$fileName'."
                    continue
                }

                Write-Host "    - Uploading '$fileName' (schema: $schemaClass)..."

                $dataPayload = @{
                    Claim_Id    = $claimId
                    Schema_Id   = $schemaId
                    Metadata_Id = "sample-$bundle"
                } | ConvertTo-Json -Compress

                $fileBytes = [System.IO.File]::ReadAllBytes((Resolve-Path $filePath))
                $mimeType = switch ([System.IO.Path]::GetExtension($fileName).ToLower()) {
                    ".pdf"  { "application/pdf" }
                    ".png"  { "image/png" }
                    ".jpg"  { "image/jpeg" }
                    ".jpeg" { "image/jpeg" }
                    default { "application/octet-stream" }
                }

                try {
                    $multipartContent = New-Object System.Net.Http.MultipartFormDataContent
                    $jsonContent = [System.Net.Http.StringContent]::new($dataPayload, [System.Text.Encoding]::UTF8, "application/json")
                    $jsonContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::Parse("form-data; name=`"data`"")
                    $multipartContent.Add($jsonContent, "data")

                    $fileContent = [System.Net.Http.ByteArrayContent]::new($fileBytes)
                    $fileContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::Parse("form-data; name=`"file`"; filename=`"$fileName`"")
                    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($mimeType)
                    $multipartContent.Add($fileContent, "file", $fileName)

                    $response = $httpClient.PostAsync("$ClaimProcessorUrl/$claimId/files", $multipartContent).Result
                    $responseBody = $response.Content.ReadAsStringAsync().Result

                    if ($response.IsSuccessStatusCode) {
                        Write-Host "    - Uploaded '$fileName' successfully."
                    } else {
                        Write-Host "    - Failed to upload '$fileName'. HTTP Status: $($response.StatusCode)"
                        Write-Host "    - Error: $responseBody"
                        $uploadSuccess = $false
                    }
                } catch {
                    Write-Host "    - Failed to upload '$fileName'. Error: $_"
                    $uploadSuccess = $false
                }
            }
            $httpClient.Dispose()

            # Step 4c: Launch processing
            if ($uploadSuccess) {
                Write-Host "    - Submitting claim batch for processing..."
                try {
                    Invoke-RestMethod -Uri $ClaimProcessorUrl -Method POST `
                        -ContentType "application/json" `
                        -Body (@{ claim_process_id = $claimId } | ConvertTo-Json) `
                        -TimeoutSec 30 -ErrorAction Stop | Out-Null
                    Write-Host "    - Claim batch '$claimId' submitted for processing."
                } catch {
                    Write-Host "    - Failed to submit claim batch. Error: $_"
                }
            } else {
                Write-Host "    - Skipping batch submission due to upload failures."
            }
        }

        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Sample file processing completed."
        Write-Host ("=" * 60)
    }
}

# --- Configure Entra ID authentication (app registrations + EasyAuth) ---
$authScript = Join-Path $PSScriptRoot "configure_auth.ps1"
if (Test-Path $authScript) {
  try { & $authScript } catch { Write-Host "⚠️ Auth configuration had errors: $_" }
}

# --- Refresh Content Understanding Cognitive Services account ---
Write-Host ""
Write-Host ("=" * 60)
Write-Host "Refreshing Content Understanding Cognitive Services account..."
Write-Host ("=" * 60)

$CU_ACCOUNT_NAME = ""
try {
    $CU_ACCOUNT_NAME = (azd env get-value CONTENT_UNDERSTANDING_ACCOUNT_NAME 2>$null)
    if (-not $CU_ACCOUNT_NAME) { $CU_ACCOUNT_NAME = "" }
} catch {
    $CU_ACCOUNT_NAME = ""
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
        # Refresh the azd env so subsequent runs use the correct value.
        try { azd env set CONTENT_UNDERSTANDING_ACCOUNT_NAME $CU_ACCOUNT_NAME 2>$null | Out-Null } catch { }
    } elseif ($CuAccounts.Count -gt 1) {
        Write-Host "  [Warn] Multiple AIServices accounts found in resource group '$RESOURCE_GROUP': $($CuAccounts -join ', ')"
        Write-Host "         Please set CONTENT_UNDERSTANDING_ACCOUNT_NAME in azd env to the correct account name. Skipping refresh."
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
