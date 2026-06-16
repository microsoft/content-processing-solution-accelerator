# Keep post-deployment best-effort so provisioning does not fail.
$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

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
    # ---------- Schema registration ----------
    $SchemaInfoFile = Join-Path $FullPath "schema_info.json"
    $Manifest = Get-Content $SchemaInfoFile -Raw | ConvertFrom-Json

    $SchemaVaultUrl   = "$ApiBaseUrl/schemavault/"
    $SchemaSetVaultUrl = "$ApiBaseUrl/schemasetvault/"

    $PythonBin = $null
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $PythonBin = "python3"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonBin = "python"
    }

    function Convert-PythonSchemaToJson {
        param(
            [Parameter(Mandatory = $true)] [string]$PythonFile,
            [Parameter(Mandatory = $true)] [string]$ClassName,
            [Parameter(Mandatory = $true)] [string]$OutputFile,
            [Parameter(Mandatory = $true)] [string]$PythonCmd
        )

        $script = @'
import importlib.util
import json
import sys

py_path, class_name, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("schema_module", py_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load schema module from {py_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cls = getattr(module, class_name, None)
if cls is None:
    raise RuntimeError(f"Class '{class_name}' not found in {py_path}")
if not hasattr(cls, "model_json_schema"):
    raise RuntimeError(f"Class '{class_name}' does not expose model_json_schema()")
schema = cls.model_json_schema()
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)
'@

        $script | & $PythonCmd - $PythonFile $ClassName $OutputFile
        if ($LASTEXITCODE -ne 0) {
            throw "Failed generating JSON schema from '$PythonFile'."
        }
    }

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
        $SchemaFileOriginal = $SchemaFile

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

        $UploadFile = $SchemaFile
        $UploadFileName = [System.IO.Path]::GetFileName($SchemaFile)
        $UploadContentType = "application/json"
        $IsGeneratedJson = $false

        if ([System.IO.Path]::GetExtension($SchemaFile).ToLowerInvariant() -eq ".py") {
            if (-not $PythonBin) {
                Write-Host "  Error: Python is required to convert '$UploadFileName' to JSON schema. Skipping..."
                continue
            }

            $GeneratedJsonPath = Join-Path $FullPath ("{0}.json" -f $ClassName)
            try {
                Convert-PythonSchemaToJson -PythonFile $SchemaFile -ClassName $ClassName -OutputFile $GeneratedJsonPath -PythonCmd $PythonBin
                $UploadFile = $GeneratedJsonPath
                $UploadFileName = [System.IO.Path]::GetFileNameWithoutExtension($SchemaFile) + ".json"
                $IsGeneratedJson = $true
            } catch {
                Write-Host "  Error: $_"
                continue
            }
        }

        Write-Host "  Registering new schema '$ClassName'..."

        # Build multipart form data
        $dataPayload = @{ ClassName = $ClassName; Description = $Description } | ConvertTo-Json -Compress
        $fileBytes   = [System.IO.File]::ReadAllBytes($UploadFile)

        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        $bodyLines = (
            "--$boundary",
            "Content-Disposition: form-data; name=`"data`"$LF",
            $dataPayload,
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$UploadFileName`"",
            "Content-Type: $UploadContentType$LF",
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
            $statusCode = $null
            $responseBody = ""
            if ($_.Exception.Response) {
                $statusCode = [int]$_.Exception.Response.StatusCode
                try {
                    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                    $responseBody = $reader.ReadToEnd()
                    $reader.Close()
                } catch {
                    $responseBody = ""
                }
            }

            if ($IsGeneratedJson -and $statusCode -eq 415 -and $responseBody -match "Only \.py schema files are supported") {
                Write-Host "  API expects legacy .py schemas. Retrying with '$([System.IO.Path]::GetFileName($SchemaFileOriginal))'..."
                try {
                    $legacyBytes = [System.IO.File]::ReadAllBytes($SchemaFileOriginal)
                    $legacyName = [System.IO.Path]::GetFileName($SchemaFileOriginal)
                    $legacyBoundary = [System.Guid]::NewGuid().ToString()
                    $legacyBody = (
                        "--$legacyBoundary",
                        "Content-Disposition: form-data; name=`"data`"$LF",
                        $dataPayload,
                        "--$legacyBoundary",
                        "Content-Disposition: form-data; name=`"file`"; filename=`"$legacyName`"",
                        "Content-Type: text/x-python$LF",
                        [System.Text.Encoding]::UTF8.GetString($legacyBytes),
                        "--$legacyBoundary--$LF"
                    ) -join $LF

                    $legacyResp = Invoke-RestMethod -Uri $SchemaVaultUrl -Method POST `
                        -ContentType "multipart/form-data; boundary=$legacyBoundary" `
                        -Body $legacyBody -TimeoutSec 60 -ErrorAction Stop
                    $schemaId = $legacyResp.Id
                    Write-Host "  Successfully registered (legacy): $Description's Schema Id - $schemaId"
                    $Registered[$ClassName] = $schemaId
                } catch {
                    Write-Host "  Failed to upload '$legacyName'. Error: $_"
                }
            } else {
                Write-Host "  Failed to upload '$UploadFileName'. Error: $_"
            }
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

exit 0
