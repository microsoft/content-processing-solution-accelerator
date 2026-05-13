#Requires -Version 5.1
<#
.SYNOPSIS
    Validates configure_auth.ps1 --preflight-only behavior under each
    insufficient-permission scenario. No real Azure credentials are required.

.DESCRIPTION
    Creates temporary mock az.cmd / azd.cmd executables (backed by PowerShell
    helper scripts) in a temp folder, prepends that folder to PATH, then calls
    configure_auth.ps1 --preflight-only for each scenario and asserts the
    expected exit code and output text.

    Scenarios tested (10 total):
      T01  Happy path — all checks pass
      T02  Check 1: Azure CLI not authenticated
      T03  Check 2: required azd env values missing
      T04  Check 3: Container Apps CLI extension absent
      T05  Check 4: no Contributor/Owner RBAC on resource group
      T06  Check 5: cannot read Entra app registrations
      T07  Check 6: target Container App is inaccessible
      T08  Check 7: Entra role below Application Administrator (FAIL)
      T09  Check 7: consent-only WARN — non-fatal (exit 0)
      T10  Check 7: service-principal login — dir check skipped (exit 0)

.EXAMPLE
    .\test_configure_auth_preflight.ps1
#>

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Subject   = Join-Path $ScriptDir "configure_auth.ps1"

if (-not (Test-Path $Subject)) {
    Write-Error "configure_auth.ps1 not found at $Subject"
    exit 1
}

$PassCount = 0
$FailCount = 0
$TempDir   = Join-Path ([System.IO.Path]::GetTempPath()) "auth_pfl_test_$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $TempDir | Out-Null

# Clean up temp dir on script exit
try {

# =============================================================================
# Mock PowerShell helper for az.cmd
# Behaviour controlled by AZ_MOCK_SCENARIO environment variable.
# =============================================================================
$MockAzPs1Content = @'
$allArgs = $args
$SCENARIO = if ($env:AZ_MOCK_SCENARIO) { $env:AZ_MOCK_SCENARIO } else { "happy" }
$S = ($allArgs -join " ")
function has($t) { $S -like "*$t*" }

if ((has "account show") -and -not (has "role assignment")) {
    if ($SCENARIO -eq "no_auth") { exit 1 }
    if (has "tenantId")   { Write-Output "mock-tenant-id";            exit 0 }
    if (has "user.name")  { Write-Output "sp-mock@service.principal"; exit 0 }
    Write-Output "mock-sub-id-12345"; exit 0
}
if (has "signed-in-user") {
    if ($SCENARIO -eq "sp_login") { exit 1 }
    Write-Output "mock-user-object-id-abc123"; exit 0
}
if (has "role assignment list") {
    if ($SCENARIO -eq "no_rbac") { Write-Output ""; exit 0 }
    Write-Output "Contributor"; exit 0
}
if ((has "ad app list") -and -not (has "ad app show")) {
    if ($SCENARIO -eq "no_entra_read") { exit 1 }
    Write-Output "mock-app-id-00001"; exit 0
}
if ((has "containerapp") -and (has " --help")) {
    if ($SCENARIO -eq "no_extension") { exit 1 }
    exit 0
}
if (has "containerapp show") {
    if ($SCENARIO -eq "no_container_app") { exit 1 }
    Write-Output "ca-testenv-web"; exit 0
}
if (has "rest") {
    switch ($SCENARIO) {
        "insufficient_dir_role" { Write-Output "Directory Readers";         exit 0 }
        "consent_warn_only"     { Write-Output "Application Administrator"; exit 0 }
        default                 { Write-Output "Global Administrator";      exit 0 }
    }
}
if (has "ad app show") { exit 1 }
exit 0
'@

# =============================================================================
# Mock PowerShell helper for azd.cmd
# Behaviour controlled by AZD_MOCK_SCENARIO environment variable.
# =============================================================================
$MockAzdPs1Content = @'
$allArgs = $args
$SCENARIO = if ($env:AZD_MOCK_SCENARIO) { $env:AZD_MOCK_SCENARIO } else { "happy" }
$S = ($allArgs -join " ")

if ($S -like "*env get-value*") {
    $KEY = $allArgs[-1]
    if ($SCENARIO -eq "no_env") {
        if ($KEY -eq "AZURE_ENV_NAME") { Write-Output "testenv" } else { Write-Output "" }
        exit 0
    }
    switch ($KEY) {
        "AZURE_ENV_NAME"         { Write-Output "testenv" }
        "AZURE_RESOURCE_GROUP"   { Write-Output "mock-rg" }
        "AZURE_SUBSCRIPTION_ID"  { Write-Output "mock-sub-id" }
        "AZURE_TENANT_ID"        { Write-Output "mock-tenant-id" }
        "CONTAINER_WEB_APP_NAME" { Write-Output "ca-testenv-web" }
        "CONTAINER_WEB_APP_FQDN" { Write-Output "ca-testenv-web.azurecontainerapps.io" }
        "CONTAINER_API_APP_NAME" { Write-Output "ca-testenv-api" }
        "CONTAINER_API_APP_FQDN" { Write-Output "ca-testenv-api.azurecontainerapps.io" }
        default                  { Write-Output "" }
    }
    exit 0
}
exit 0
'@

# Write helper scripts
$MockAzPs1Content  | Out-File -FilePath (Join-Path $TempDir "mock_az.ps1")  -Encoding UTF8
$MockAzdPs1Content | Out-File -FilePath (Join-Path $TempDir "mock_azd.ps1") -Encoding UTF8

# Write .cmd wrappers — %~dp0 resolves to the directory containing the .cmd file
@"
@echo off
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0mock_az.ps1" %*
"@ | Out-File -FilePath (Join-Path $TempDir "az.cmd")  -Encoding ASCII

@"
@echo off
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0mock_azd.ps1" %*
"@ | Out-File -FilePath (Join-Path $TempDir "azd.cmd") -Encoding ASCII

# =============================================================================
# Test runner
# =============================================================================
function Run-Test {
    param(
        [string]$Name,
        [int]   $ExpectedExit,
        [string]$ExpectedText  = "",
        [string]$AzScenario    = "happy",
        [string]$AzdScenario   = "happy"
    )

    $origPath = $env:PATH
    $env:PATH  = "$TempDir;$env:PATH"
    $env:AZ_MOCK_SCENARIO  = $AzScenario
    $env:AZD_MOCK_SCENARIO = $AzdScenario
    $env:AZURE_SKIP_AUTH_SETUP = ""

    $rawOutput = pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass `
        -File $Subject "--preflight-only" 2>&1
    $exitCode = $LASTEXITCODE
    $outputStr = ($rawOutput | Out-String)

    $env:PATH = $origPath
    $env:AZ_MOCK_SCENARIO  = $null
    $env:AZD_MOCK_SCENARIO = $null

    $ok = $true; $reason = ""
    if ($exitCode -ne $ExpectedExit) {
        $ok = $false; $reason = "exit $exitCode (expected $ExpectedExit)"
    } elseif ($ExpectedText -and ($outputStr -notlike "*$ExpectedText*")) {
        $ok = $false; $reason = "expected text '$ExpectedText' not in output"
    }

    if ($ok) {
        Write-Host ("  `u{2705} {0,-62}" -f $Name)
        $script:PassCount++
    } else {
        Write-Host ("  `u{274C} {0,-62}  [{1}]" -f $Name, $reason)
        ($outputStr -split "`n" | Select-Object -Last 4) | ForEach-Object {
            Write-Host "       $_"
        }
        $script:FailCount++
    }
}

# =============================================================================
# Test scenarios
# =============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host " configure_auth.ps1 — preflight permission scenario tests"
Write-Host "============================================================"

# T01 — Happy path: every check should pass
Run-Test "T01  Happy path: all checks pass" `
    -ExpectedExit 0 -ExpectedText "Preflight-only mode" `
    -AzScenario "happy" -AzdScenario "happy"

# T02 — Check 1: Azure CLI not authenticated
Run-Test "T02  Check 1: not authenticated" `
    -ExpectedExit 1 -ExpectedText "Azure CLI authenticated" `
    -AzScenario "no_auth" -AzdScenario "happy"

# T03 — Check 2: required azd env values missing
Run-Test "T03  Check 2: missing required azd env values" `
    -ExpectedExit 1 -ExpectedText "Required azd env values" `
    -AzScenario "happy" -AzdScenario "no_env"

# T04 — Check 3: Azure Container Apps CLI extension absent
Run-Test "T04  Check 3: containerapp CLI extension missing" `
    -ExpectedExit 1 -ExpectedText "Container Apps CLI" `
    -AzScenario "no_extension" -AzdScenario "happy"

# T05 — Check 4: no Contributor or Owner role on resource group
Run-Test "T05  Check 4: no RBAC Contributor/Owner on resource group" `
    -ExpectedExit 1 -ExpectedText "Contributor/Owner" `
    -AzScenario "no_rbac" -AzdScenario "happy"

# T06 — Check 5: cannot read Entra app registrations
Run-Test "T06  Check 5: cannot read Entra app registrations" `
    -ExpectedExit 1 -ExpectedText "Entra app registrations" `
    -AzScenario "no_entra_read" -AzdScenario "happy"

# T07 — Check 6: target Container App is inaccessible
Run-Test "T07  Check 6: Container App is inaccessible" `
    -ExpectedExit 1 -ExpectedText "Container App" `
    -AzScenario "no_container_app" -AzdScenario "happy"

# T08 — Check 7: Entra role present but below Application Administrator (FAIL)
Run-Test "T08  Check 7: insufficient Entra directory role (FAIL)" `
    -ExpectedExit 1 -ExpectedText "App-registration permission" `
    -AzScenario "insufficient_dir_role" -AzdScenario "happy"

# T09 — Check 7: Application Administrator present, consent role absent (WARN, non-fatal)
Run-Test "T09  Check 7: consent-only WARN is non-fatal (exit 0)" `
    -ExpectedExit 0 -ExpectedText "Admin-consent permission" `
    -AzScenario "consent_warn_only" -AzdScenario "happy"

# T10 — Check 7: service principal login — directory-role check skipped (WARN, non-fatal)
Run-Test "T10  Check 7: SP login — directory-role check skipped (exit 0)" `
    -ExpectedExit 0 -ExpectedText "directory-role check" `
    -AzScenario "sp_login" -AzdScenario "happy"

# =============================================================================
# Summary
# =============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host "  Results: $PassCount passed, $FailCount failed"
Write-Host "============================================================"
Write-Host ""

} finally {
    Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($FailCount -gt 0) { exit 1 }
