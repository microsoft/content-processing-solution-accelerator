$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
& (Join-Path $ScriptDir "configure_auth.ps1") @args