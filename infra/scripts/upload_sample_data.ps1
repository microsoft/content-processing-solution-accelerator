$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$env:POST_DEPLOYMENT_MODE = "sample-data"
& (Join-Path $ScriptDir "post_deployment.ps1")
