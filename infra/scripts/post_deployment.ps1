param(
    [Parameter(Position = 0)]
    [string]$ResourceGroupName,

    [Parameter(Position = 1)]
    [string]$SubscriptionId,

    [Parameter(Position = 2)]
    [string]$ApiBaseUrl,

    [Parameter(Position = 3)]
    [string]$ContentUnderstandingAccountName
)

# Stop script on any error
$ErrorActionPreference = "Stop"

function Get-AzdEnvironmentValue {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [string]$DefaultValue = ''
    )

    try {
        $value = azd env get-value $Name 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($value)) {
            $trimmedValue = $value.Trim()
            if ($trimmedValue -match '(?i)^(ERROR|WARN|WARNING|azd|environment not specified)') {
                return $DefaultValue
            }
            return $trimmedValue
        }
    } catch {
        # Ignore and fall back to other sources.
    }

    return $DefaultValue
}

function Invoke-AzureCli {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [switch]$AllowFailure
    )

    $output = @()
    $exitCode = 0

    try {
        $output = & az @Arguments 2>$null
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    } catch {
        $exitCode = 1
        $output = @($_.Exception.Message)
    }

    if ($exitCode -ne 0) {
        $message = ($output | Out-String).Trim()
        if (-not $AllowFailure) {
            if ($message) {
                Write-Host "  [Warn] Azure CLI command failed: az $($Arguments -join ' ')"
                Write-Host "         $message"
            }
        }
        return $null
    }

    return ($output | Out-String).Trim()
}

function Resolve-ContainerAppName {
    param(
        [string]$CurrentName,
        [string]$Keyword,
        [string]$ResourceGroup
    )

    if (-not [string]::IsNullOrWhiteSpace($CurrentName)) {
        return $CurrentName
    }

    if (-not $ResourceGroup) {
        return ''
    }

    $resolved = Invoke-AzureCli -Arguments @('containerapp', 'list', '-g', $ResourceGroup, '--query', '[].name', '-o', 'tsv') -AllowFailure
    if ($resolved) {
        $apps = @($resolved -split "`r?`n" | Where-Object { $_ -and $_.Trim() })
        foreach ($app in $apps) {
            if ($app.ToLowerInvariant().Contains($Keyword.ToLowerInvariant())) {
                return $app.Trim()
            }
        }
    }

    return ''
}

function Resolve-ContainerAppFqdn {
    param(
        [string]$AppName,
        [string]$ResourceGroup
    )

    if (-not [string]::IsNullOrWhiteSpace($AppName) -and $ResourceGroup) {
        $fqdn = Invoke-AzureCli -Arguments @('containerapp', 'show', '-g', $ResourceGroup, '-n', $AppName, '--query', 'properties.configuration.ingress.fqdn', '-o', 'tsv') -AllowFailure
        if ($fqdn) {
            return $fqdn.Trim()
        }
    }

    return ''
}

Write-Host "[Search] Fetching container app info from azd environment..."

# Get subscription and resource group (prefer explicit parameters, then azd env, then current Azure CLI context)
$SUBSCRIPTION_ID = if ($SubscriptionId) { $SubscriptionId } else { Get-AzdEnvironmentValue -Name 'AZURE_SUBSCRIPTION_ID' }
if (-not $SUBSCRIPTION_ID) {
    $SUBSCRIPTION_ID = (Invoke-AzureCli -Arguments @('account', 'show', '--query', 'id', '-o', 'tsv') -AllowFailure)
    if (-not $SUBSCRIPTION_ID) {
        $SUBSCRIPTION_ID = ''
    }
}

$RESOURCE_GROUP = if ($ResourceGroupName) { $ResourceGroupName } else { Get-AzdEnvironmentValue -Name 'AZURE_RESOURCE_GROUP' }
if (-not $RESOURCE_GROUP) {
    $RESOURCE_GROUP = (Invoke-AzureCli -Arguments @('group', 'show', '--query', 'name', '-o', 'tsv') -AllowFailure)
    if (-not $RESOURCE_GROUP) {
        $RESOURCE_GROUP = ''
    }
}

# Load values from azd env, but allow explicit parameters to override them.
$CONTAINER_WEB_APP_NAME = Resolve-ContainerAppName -CurrentName (Get-AzdEnvironmentValue -Name 'CONTAINER_WEB_APP_NAME') -Keyword 'web' -ResourceGroup $RESOURCE_GROUP
$CONTAINER_WEB_APP_FQDN = (Get-AzdEnvironmentValue -Name 'CONTAINER_WEB_APP_FQDN')

$CONTAINER_API_APP_NAME = Resolve-ContainerAppName -CurrentName (Get-AzdEnvironmentValue -Name 'CONTAINER_API_APP_NAME') -Keyword 'api' -ResourceGroup $RESOURCE_GROUP
$CONTAINER_API_APP_FQDN = (Get-AzdEnvironmentValue -Name 'CONTAINER_API_APP_FQDN')

$CONTAINER_WORKFLOW_APP_NAME = Resolve-ContainerAppName -CurrentName (Get-AzdEnvironmentValue -Name 'CONTAINER_WORKFLOW_APP_NAME') -Keyword 'workflow' -ResourceGroup $RESOURCE_GROUP

if (-not $CONTAINER_WEB_APP_FQDN) {
    $CONTAINER_WEB_APP_FQDN = Resolve-ContainerAppFqdn -AppName $CONTAINER_WEB_APP_NAME -ResourceGroup $RESOURCE_GROUP
}
if (-not $CONTAINER_API_APP_FQDN) {
    $CONTAINER_API_APP_FQDN = Resolve-ContainerAppFqdn -AppName $CONTAINER_API_APP_NAME -ResourceGroup $RESOURCE_GROUP
}

# Construct Azure Portal URLs
$WEB_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WEB_APP_NAME"
$API_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_API_APP_NAME"
$WORKFLOW_APP_PORTAL_URL = "https://portal.azure.com/#resource/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_WORKFLOW_APP_NAME"

function Normalize-ApiBaseUrl {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $trimmed = $Value.Trim()
    if ($trimmed -match '^https?://') {
        return $trimmed.TrimEnd('/')
    }

    return "https://$trimmed"
}

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
$ResolvedApiBaseUrl = if ($ApiBaseUrl) { Normalize-ApiBaseUrl -Value $ApiBaseUrl } elseif ($CONTAINER_API_APP_FQDN) { "https://$CONTAINER_API_APP_FQDN" } else { '' }
$ApiReady = $false

if (-not $ResolvedApiBaseUrl) {
    Write-Host "  [Warn] No API base URL was provided and no API container app FQDN was resolved. Skipping schema registration."
} else {
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "$ResolvedApiBaseUrl/schemavault/" -Method GET -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
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

        $SchemaVaultUrl   = "$ResolvedApiBaseUrl/schemavault/"
        $SchemaSetVaultUrl = "$ResolvedApiBaseUrl/schemasetvault/"

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

            if ($null -ne $setResp) {
                $SchemaSetId = $null
                if ($setResp -is [string]) {
                    $SchemaSetId = $setResp.Trim()
                } elseif ($setResp.PSObject.Properties.Name -contains 'Id') {
                    $SchemaSetId = $setResp.Id
                } elseif ($setResp.PSObject.Properties.Name -contains 'id') {
                    $SchemaSetId = $setResp.id
                }

                if ([string]::IsNullOrWhiteSpace([string]$SchemaSetId)) {
                    Write-Host "  Schema set creation returned no usable ID. Response: $($setResp | ConvertTo-Json -Compress -Depth 10)"
                } else {
                    Write-Host "  Created schema set '$SetName' with ID: $SchemaSetId"
                }
            } else {
                Write-Host "  Schema set creation returned an empty response."
            }
        } catch {
            Write-Host "  Failed to create schema set. Error: $_"
        }
    }

    if (-not $SchemaSetId) {
        Write-Host "Error: Could not create or find schema set. Aborting step 3."
        Write-Host "  [Info] The API endpoint responded without a usable schema-set ID. You can retry this step after the API finishes initializing."
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
}

# --- Refresh Content Understanding Cognitive Services account ---
Write-Host ""
Write-Host ("=" * 60)
Write-Host "Refreshing Content Understanding Cognitive Services account..."
Write-Host ("=" * 60)

$ResourceGroupExists = $false
if ($RESOURCE_GROUP) {
    $resourceGroupExistsOutput = Invoke-AzureCli -Arguments @('group', 'exists', '-n', $RESOURCE_GROUP) -AllowFailure
    if ($resourceGroupExistsOutput -eq 'true') {
        $ResourceGroupExists = $true
    } elseif ($resourceGroupExistsOutput -eq 'false') {
        Write-Host "  [Warn] Resource group '$RESOURCE_GROUP' does not exist or is not accessible. Skipping Azure resource discovery and refresh."
    }
}

if (-not $ResourceGroupExists -and $RESOURCE_GROUP) {
    Write-Host "  [Warn] Unable to refresh Content Understanding account because resource group '$RESOURCE_GROUP' is unavailable."
}

$CU_ACCOUNT_NAME = ""
if ($ContentUnderstandingAccountName) {
    $CU_ACCOUNT_NAME = $ContentUnderstandingAccountName
} else {
    $CU_ACCOUNT_NAME = Get-AzdEnvironmentValue -Name 'CONTENT_UNDERSTANDING_ACCOUNT_NAME'
}

if ($CU_ACCOUNT_NAME) {
    $CU_ACCOUNT_NAME = $CU_ACCOUNT_NAME.Trim()
}

# Verify the account from the env value still exists; if not, fall back to discovering
# the AIServices account in the resource group. This protects against stale .env values
# left over from prior deployments (different template/fork) and against the env value
# pointing to a resource that no longer exists.
if ($CU_ACCOUNT_NAME -and $ResourceGroupExists) {
    # Capture stderr so we can distinguish a real "not found" response from a
    # transient/auth/CLI failure. Only treat the env value as stale when Azure
    # actually reports the resource is missing; for any other error keep the
    # env value untouched and log the underlying error for diagnosability.
    $ShowOutput = Invoke-AzureCli -Arguments @('cognitiveservices', 'account', 'show', '-g', $RESOURCE_GROUP, '-n', $CU_ACCOUNT_NAME, '--output', 'none') -AllowFailure
    if (-not $ShowOutput) {
        $ShowOutputStr = ''
        if ($LASTEXITCODE -ne 0) {
            $ShowOutputStr = 'Azure CLI returned a non-zero exit code.'
        }
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

if (-not $CU_ACCOUNT_NAME -and $ResourceGroupExists) {
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

if ($CU_ACCOUNT_NAME -and $ResourceGroupExists) {
    Write-Host "  Refreshing account: $CU_ACCOUNT_NAME in resource group: $RESOURCE_GROUP"
    # Capture stderr so that any Azure CLI error is preserved in deployment
    # logs even though this refresh step is non-fatal.
    $UpdateOutput = Invoke-AzureCli -Arguments @('cognitiveservices', 'account', 'update', '-g', $RESOURCE_GROUP, '-n', $CU_ACCOUNT_NAME, '--tags', 'refresh=true', '--output', 'none') -AllowFailure
    if ($UpdateOutput -ne $null) {
        Write-Host "  [OK] Successfully refreshed Cognitive Services account '$CU_ACCOUNT_NAME'."
    } else {
        $UpdateOutputStr = ''
        Write-Host "  [Warn] Could not refresh Cognitive Services account '$CU_ACCOUNT_NAME'. Continuing - this step is non-fatal."
        Write-Host "         az error: $UpdateOutputStr"
    }
}
