# run_post_deployment.ps1
#
# Manual post-deployment setup for Content Processing Solution Accelerator.
# Run this script AFTER `azd up` has finished provisioning infrastructure.
#
# Steps executed:
#   Step 1 - Schema registration                          (register_schemas.ps1)
#   Step 2 - Sample data upload                          (upload_sample_data.ps1)
#   Step 3 - Entra ID authentication setup               (setup_auth.ps1)
#
# Skip individual steps by setting env vars before running:
#   $env:SKIP_SCHEMA_REGISTRATION = "true"; .\infra\scripts\run_post_deployment.ps1
#   $env:SKIP_SAMPLE_DATA_UPLOAD  = "true"; .\infra\scripts\run_post_deployment.ps1
#   $env:SKIP_AUTH_SETUP          = "true"; .\infra\scripts\run_post_deployment.ps1
#
# To skip auth setup permanently:
#   azd env set AZURE_SKIP_AUTH_SETUP true
#
# Usage (from repo root):
#   .\infra\scripts\run_post_deployment.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot

function Print-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗"
    Write-Host "║      Content Processing Solution Accelerator                 ║"
    Write-Host "║      Post-Deployment Manual Setup                            ║"
    Write-Host "╚══════════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Host "  This script runs post-deployment steps that are intentionally"
    Write-Host "  decoupled from 'azd up' so they can be executed separately,"
    Write-Host "  retried independently, and skipped when permissions are limited."
    Write-Host ""
}

function Print-Step($Num, $Title) {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "  Step $Num`: $Title"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

function Write-StepOk($Num)            { Write-Host ""; Write-Host "  ✅ Step $Num completed successfully." }
function Write-StepSkip($Num, $Reason) { Write-Host ""; Write-Host "  ⏭️  Step $Num skipped ($Reason)." }
function Write-StepFail($Num)          { Write-Host ""; Write-Host "  ❌ Step $Num failed — see errors above." }

function Azd-Get($Key) {
    try { return (azd env get-value $Key 2>$null) } catch { return "" }
}

Print-Banner

if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
    Write-Error "Azure Developer CLI (azd) is not installed or not on PATH.`nInstall it from https://aka.ms/install-azd, then re-run."
    exit 1
}

azd env get-values 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "No active azd environment found.`nRun 'azd env list' and 'azd env select <name>', then re-run."
    exit 1
}

Write-Host "  Active azd environment : $(Azd-Get 'AZURE_ENV_NAME')"
Write-Host "  Resource group         : $(Azd-Get 'AZURE_RESOURCE_GROUP')"
Write-Host "  Subscription           : $(Azd-Get 'AZURE_SUBSCRIPTION_ID')"
Write-Host ""

$Step1Script = Join-Path $ScriptDir "register_schemas.ps1"

Print-Step 1 "Schema registration"
Write-Host "  Script : $Step1Script"
Write-Host "  Purpose: Register sample schemas, create the schema set, and link schemas to it."
Write-Host ""

if ($env:SKIP_SCHEMA_REGISTRATION -eq "true") {
    Write-StepSkip 1 "SKIP_SCHEMA_REGISTRATION=true"
} else {
    if (-not (Test-Path $Step1Script)) {
        Write-Error "Script not found: $Step1Script"
        exit 1
    }

    try {
        & $Step1Script
        Write-StepOk 1
    } catch {
        Write-StepFail 1
        Write-Host "  To retry : .\$Step1Script"
        Write-Host "  To skip  : `$env:SKIP_SCHEMA_REGISTRATION = 'true'; .\$ScriptDir\run_post_deployment.ps1"
        exit 1
    }
}

$Step2Script = Join-Path $ScriptDir "upload_sample_data.ps1"

Print-Step 2 "Sample data upload"
Write-Host "  Script : $Step2Script"
Write-Host "  Purpose: Create sample claim batches, upload sample bundles, and submit them for processing."
Write-Host ""

if ($env:SKIP_SAMPLE_DATA_UPLOAD -eq "true") {
    Write-StepSkip 2 "SKIP_SAMPLE_DATA_UPLOAD=true"
} else {
    if (-not (Test-Path $Step2Script)) {
        Write-Error "Script not found: $Step2Script"
        exit 1
    }

    try {
        & $Step2Script
        Write-StepOk 2
    } catch {
        Write-StepFail 2
        Write-Host "  To retry : .\$Step2Script"
        Write-Host "  To skip  : `$env:SKIP_SAMPLE_DATA_UPLOAD = 'true'; .\$ScriptDir\run_post_deployment.ps1"
        exit 1
    }
}

$Step3Script = Join-Path $ScriptDir "setup_auth.ps1"

Print-Step 3 "Entra ID authentication setup (app registrations + EasyAuth)"
Write-Host "  Script : $Step3Script"
Write-Host "  Purpose: Create app registrations for Web + API, configure EasyAuth,"
Write-Host "           grant admin consent, and wire environment variables."
Write-Host ""
Write-Host "  Required permissions:"
Write-Host "    * Application Administrator (or higher) — to create app registrations"
Write-Host "    * Cloud Application Administrator / Global Administrator — to grant admin consent"
Write-Host "    * Contributor on resource group — to update Container Apps"
Write-Host ""
Write-Host "  To skip this step:"
Write-Host "    `$env:SKIP_AUTH_SETUP = 'true'; .\$ScriptDir\run_post_deployment.ps1"
Write-Host "    — or —"
Write-Host "    azd env set AZURE_SKIP_AUTH_SETUP true"
Write-Host "    then run .\$Step3Script later when permissions are available."
Write-Host ""

$AzureSkipAuth = Azd-Get "AZURE_SKIP_AUTH_SETUP"

if ($env:SKIP_AUTH_SETUP -eq "true" -or $AzureSkipAuth -eq "true" -or $env:AZURE_SKIP_AUTH_SETUP -eq "true") {
    Write-StepSkip 3 "SKIP_AUTH_SETUP=true or AZURE_SKIP_AUTH_SETUP=true"
    Write-Host "  Run manually when permissions are available:"
    Write-Host "    .\$Step3Script"
} else {
    if (-not (Test-Path $Step3Script)) {
        Write-Error "Script not found: $Step3Script"
        exit 1
    }

    try {
        & $Step3Script
        Write-StepOk 3
    } catch {
        Write-StepFail 3
        Write-Host "  To retry auth setup  : .\$Step3Script"
        Write-Host "  For manual portal steps: docs/ConfigureAppAuthentication.md"
        exit 1
    }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗"
Write-Host "║  Post-deployment setup complete.                             ║"
Write-Host "║                                                              ║"
Write-Host "║  Next steps:                                                 ║"
Write-Host "║   1. Wait up to 10 minutes for EasyAuth to propagate.       ║"
Write-Host "║   2. Open the Web App URL and sign in.                       ║"
Write-Host "║   3. Verify the two sample claim bundles appear in the UI.  ║"
Write-Host "╚══════════════════════════════════════════════════════════════╝"
Write-Host ""
