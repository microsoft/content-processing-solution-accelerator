<#
.SYNOPSIS
    Post-deployment script for the Content Processing Solution Accelerator.

.DESCRIPTION
    Discovers the Web / API / Workflow Container Apps from the supplied resource
    group, waits for the API to become reachable, then registers the bundled
    schemas and creates the schema set.

    No dependency on `azd` or any environment files. Only the resource group
    name is required.

.PARAMETER ResourceGroupName
    The Azure Resource Group where the AVM Content Processing module was
    deployed.

.PARAMETER SubscriptionId
    Optional. Azure Subscription Id. Defaults to the current Az CLI context.

.PARAMETER MaxRetries
    Optional. Number of times to poll the API before giving up. Default: 10.

.PARAMETER RetryIntervalSec
    Optional. Seconds between API readiness polls. Default: 15.

.EXAMPLE
    ./post_deployment.ps1 -ResourceGroupName "rg-cpsv2sw-avm"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $false)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $false)]
    [int]$MaxRetries = 10,

    [Parameter(Mandatory = $false)]
    [int]$RetryIntervalSec = 15,

    [Parameter(Mandatory = $false)]
    [int]$AzCommandRetries = 4,

    [Parameter(Mandatory = $false)]
    [int]$AzRetryDelaySec = 5
)

$ErrorActionPreference = "Stop"

# ---------- Resolve subscription ----------
if ([string]::IsNullOrWhiteSpace($SubscriptionId)) {
    $SubscriptionId = az account show --query id -o tsv
    if ([string]::IsNullOrWhiteSpace($SubscriptionId)) {
        throw "No Azure subscription context found. Run 'az login' first or pass -SubscriptionId."
    }
}
else {
    az account set --subscription $SubscriptionId | Out-Null
}

Write-Host "[Search] Discovering Container Apps in resource group '$ResourceGroupName'..."

# ---------- Discover Container Apps ----------
function Invoke-AzJsonWithRetry {
    param(
        [string[]]$AzArgs,
        [int]$Attempts = 3,
        [int]$DelaySec = 5,
        [string]$OperationName = "Azure CLI command"
    )

    # Transport resets/timeouts from az are transient in many enterprise networks.
    $TransientPattern = "ConnectionResetError|Connection aborted|ProtocolError|WinError 10054|temporarily unavailable|timed out|BadGateway|GatewayTimeout|Too Many Requests|HTTP 429"
    $LastOutput = ""

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $rawOutput = (& az @AzArgs -o json 2>&1) | Out-String
        $exitCode = $LASTEXITCODE
        $trimmedOutput = $rawOutput.Trim()

        if ($exitCode -eq 0) {
            if ([string]::IsNullOrWhiteSpace($trimmedOutput)) {
                return $null
            }

            try {
                return $trimmedOutput | ConvertFrom-Json
            }
            catch {
                throw "$OperationName returned non-JSON output. Raw output: $trimmedOutput"
            }
        }

        $LastOutput = $trimmedOutput
        $isTransient = $trimmedOutput -match $TransientPattern

        if ($isTransient -and $attempt -lt $Attempts) {
            Write-Host "[Retry] $OperationName failed with transient error (attempt $attempt/$Attempts). Retrying in ${DelaySec}s..."
            Start-Sleep -Seconds $DelaySec
            continue
        }

        if ($isTransient) {
            throw "$OperationName failed after $Attempts attempts due to transient connection issues. Last az output: $trimmedOutput"
        }

        throw "$OperationName failed. az exit code: $exitCode. az output: $trimmedOutput"
    }

    throw "$OperationName failed unexpectedly. Last az output: $LastOutput"
}

$allApps = Invoke-AzJsonWithRetry -AzArgs @('containerapp', 'list', '-g', $ResourceGroupName) -Attempts $AzCommandRetries -DelaySec $AzRetryDelaySec -OperationName "Container App discovery"

if (-not $allApps) {
    throw "Container App discovery returned no data for resource group '$ResourceGroupName'."
}

if ($allApps -isnot [System.Array]) {
    $allApps = @($allApps)
}

if ($allApps.Count -eq 0) {
    throw "No Container Apps found in resource group '$ResourceGroupName'."
}

function Find-App {
    param([string[]]$Patterns)
    foreach ($p in $Patterns) {
        $hit = $allApps | Where-Object { $_.name -match $p } | Select-Object -First 1
        if ($hit) { return $hit }
    }
    return $null
}

$webApp      = Find-App -Patterns @('-web$', '-web-', 'web')
$apiApp      = Find-App -Patterns @('-api$', '-api-', 'api')
$workflowApp = Find-App -Patterns @('-wkfl$', '-workflow$', 'wkfl', 'workflow')

if (-not $apiApp) {
    throw "Could not locate the API Container App in resource group '$ResourceGroupName'."
}

$CONTAINER_WEB_APP_NAME      = $webApp.name
$CONTAINER_WEB_APP_FQDN      = $webApp.properties.configuration.ingress.fqdn
$CONTAINER_API_APP_NAME      = $apiApp.name
$CONTAINER_API_APP_FQDN      = $apiApp.properties.configuration.ingress.fqdn
$CONTAINER_WORKFLOW_APP_NAME = $workflowApp.name

# ---------- Construct Azure Portal URLs ----------
$WEB_APP_PORTAL_URL      = "https://portal.azure.com/#resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
$API_APP_PORTAL_URL      = "https://portal.azure.com/#resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"
$WORKFLOW_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.App/containerApps/$CONTAINER_WORKFLOW_APP_NAME"

# ---------- Resolve schema folder ----------
$ScriptDir = $PSScriptRoot

# Default: schemas bundled next to the script
$DataScriptPath = Join-Path $ScriptDir "schemas"

if (-not (Test-Path $DataScriptPath)) {
    # Fallback: original source-repo layout (infra/scripts -> src/ContentProcessorAPI/samples/schemas)
    $DataScriptPath = Join-Path $ScriptDir "..\..\src\ContentProcessorAPI\samples\schemas"
}

if (-not (Test-Path $DataScriptPath)) {
    throw "Schema folder not found. Expected '$ScriptDir\schemas' or '$ScriptDir\..\..\src\ContentProcessorAPI\samples\schemas'."
}

$FullPath = (Resolve-Path $DataScriptPath).Path

# ---------- Output ----------
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

$ApiBaseUrl = "https://$CONTAINER_API_APP_FQDN"
$ApiHealthUrl = "$ApiBaseUrl/startup"
$ApiReady   = $false

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $ApiHealthUrl -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] API startup probe is ready."
            $ApiReady = $true
            break
        }
    } catch {
        # Ignore - API not ready yet
    }
    Write-Host "  Attempt $i/$MaxRetries - API startup probe not ready, retrying in ${RetryIntervalSec}s..."
    Start-Sleep -Seconds $RetryIntervalSec
}

if (-not $ApiReady) {
    Write-Host "  API did not become ready after $MaxRetries attempts. Skipping schema registration."
    Write-Host "  Run manually after the API is ready."
    return
}

# ---------- Schema registration (no Python dependency) ----------
$SchemaInfoFile = Join-Path $FullPath "schema_info.json"
if (-not (Test-Path $SchemaInfoFile)) {
    throw "Schema manifest '$SchemaInfoFile' not found."
}
$Manifest = Get-Content $SchemaInfoFile -Raw | ConvertFrom-Json

$SchemaVaultUrl    = "$ApiBaseUrl/schemavault/"
$SchemaSetVaultUrl = "$ApiBaseUrl/schemasetvault/"

# Validate the schema endpoint before registration starts to avoid noisy downstream failures.
try {
    Invoke-RestMethod -Uri $SchemaVaultUrl -Method GET -TimeoutSec 30 -ErrorAction Stop | Out-Null
} catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        try { $statusCode = [int]$_.Exception.Response.StatusCode } catch { }
    }

    Write-Host ""
    Write-Host "Schema endpoint preflight failed at '$SchemaVaultUrl'."
    if ($statusCode) {
        Write-Host "  HTTP status: $statusCode"
    }
    Write-Host "  API container is running, but schema backend is not healthy/authorized yet."
    Write-Host "  Check API logs for backend dependency errors (for example: Storage AuthorizationFailure)."
    Write-Host "  Skipping schema registration for now. Re-run after backend auth/config is fixed."
    return
}

# --- Step 1: Register schemas ---
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

    $existing = $ExistingSchemas | Where-Object { $_.ClassName -eq $ClassName } | Select-Object -First 1
    if ($existing) {
        $schemaId = $existing.Id
        Write-Host "  Schema '$ClassName' already exists with ID: $schemaId"
        $Registered[$ClassName] = $schemaId
        continue
    }

    Write-Host "  Registering new schema '$ClassName'..."

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
        "Content-Type: text/x-python$LF",
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
