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

$PostDeploymentMode = if ($env:POST_DEPLOYMENT_MODE) { $env:POST_DEPLOYMENT_MODE } else { "all" }
if ($PostDeploymentMode -notin @("all", "schema", "sample-data")) {
    throw "Unsupported POST_DEPLOYMENT_MODE '$PostDeploymentMode'. Use one of: all, schema, sample-data."
}

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
Write-Host "- Post-deployment mode: $PostDeploymentMode"
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
    $SchemaInfoFile = Join-Path $FullPath "schema_info.json"
    $Manifest = Get-Content $SchemaInfoFile -Raw | ConvertFrom-Json

    $SchemaVaultUrl   = "$ApiBaseUrl/schemavault/"
    $SchemaSetVaultUrl = "$ApiBaseUrl/schemasetvault/"
    $SetName = $Manifest.schemaset.Name
    $SetDesc = $Manifest.schemaset.Description
    $Registered = @{}
    $SchemaSetId = $null

    if ($PostDeploymentMode -eq "sample-data") {
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Resolving existing schemas and schema set for sample data upload"
        Write-Host ("=" * 60)

        $ExistingSchemas = @()
        try {
            $ExistingSchemas = Invoke-RestMethod -Uri $SchemaVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
        } catch {
            Write-Host "Warning: Could not fetch existing schemas. Proceeding..."
        }

        foreach ($entry in $Manifest.schemas) {
            $existing = $ExistingSchemas | Where-Object { $_.ClassName -eq $entry.ClassName } | Select-Object -First 1
            if ($existing) {
                $Registered[$entry.ClassName] = $existing.Id
            } else {
                Write-Host "  ⚠️ Schema '$($entry.ClassName)' is not registered. Run schema registration first."
            }
        }

        $ExistingSets = @()
        try {
            $ExistingSets = Invoke-RestMethod -Uri $SchemaSetVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
        } catch {
            Write-Host "Warning: Could not fetch existing schema sets. Proceeding..."
        }

        $existingSet = $ExistingSets | Where-Object { $_.Name -eq $SetName } | Select-Object -First 1
        if ($existingSet) {
            $SchemaSetId = $existingSet.Id
            Write-Host "  ✅ Using existing schema set '$SetName' ($SchemaSetId)"
        } else {
            Write-Host "  ⚠️ Schema set '$SetName' does not exist yet. Run schema registration first."
        }
    } else {
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Step 1: Register schemas"
        Write-Host ("=" * 60)

        $ExistingSchemas = @()
        try {
            $ExistingSchemas = Invoke-RestMethod -Uri $SchemaVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
            Write-Host "Fetched $($ExistingSchemas.Count) existing schema(s)."
        } catch {
            Write-Host "Warning: Could not fetch existing schemas. Proceeding..."
        }

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

            $existing = $ExistingSchemas | Where-Object { $_.ClassName -eq $ClassName } | Select-Object -First 1
            if ($existing) {
                $schemaId = $existing.Id
                Write-Host "  Schema '$ClassName' already exists with ID: $schemaId"
                $Registered[$ClassName] = $schemaId
                continue
            }

            Write-Host "  Registering new schema '$ClassName'..."

            $extension = [System.IO.Path]::GetExtension($SchemaFile).ToLowerInvariant()
            if ($extension -ne '.json') {
                Write-Host "  Unsupported schema extension '$extension' for '$SchemaFile'. Only .json is accepted. Skipping..."
                continue
            }
            $contentType = 'application/json'

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

        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Step 2: Create schema set"
        Write-Host ("=" * 60)

        $ExistingSets = @()
        try {
            $ExistingSets = Invoke-RestMethod -Uri $SchemaSetVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop
            Write-Host "Fetched $($ExistingSets.Count) existing schema set(s)."
        } catch {
            Write-Host "Warning: Could not fetch existing schema sets. Proceeding..."
        }

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

    if ($PostDeploymentMode -eq "schema") {
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Sample data upload skipped because POST_DEPLOYMENT_MODE=schema"
        Write-Host "Next explicit step: run `$env:POST_DEPLOYMENT_MODE='sample-data'; ./infra/scripts/post_deployment.ps1"
        Write-Host ("=" * 60)
    } elseif ($SchemaSetId -and $Registered.Count -gt 0) {
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
    } else {
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "Sample data upload skipped because required schemas or schema set were not found."
        Write-Host "Run schema registration first, then re-run with POST_DEPLOYMENT_MODE=sample-data."
        Write-Host ("=" * 60)
    }
}

Write-Host ""
Write-Host ("=" * 60)
Write-Host "Post-deployment data setup completed."
Write-Host "Next manual step: configure authentication using infra/scripts/configure_auth.ps1"
Write-Host ("=" * 60)
