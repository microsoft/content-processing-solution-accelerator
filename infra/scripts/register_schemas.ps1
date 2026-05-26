$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$env:POST_DEPLOYMENT_MODE = "schema"
& (Join-Path $ScriptDir "post_deployment.ps1")
