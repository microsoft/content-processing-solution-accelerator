$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$scriptPath = Join-Path $repoRoot 'infra/scripts/post_deployment.ps1'

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('post-deployment-test-' + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

$stubDir = Join-Path $tempRoot 'bin'
New-Item -ItemType Directory -Path $stubDir -Force | Out-Null

@'
@echo off
if "%~1"=="env" (
  if "%~2"=="get-value" (
    if "%~3"=="CONTENT_UNDERSTANDING_ACCOUNT_NAME" (
      echo ERROR: ensuring environment exists: environment not specified 1>&2
      exit /b 1
    )
  )
)
exit /b 0
'@ | Set-Content (Join-Path $stubDir 'azd.cmd') -Encoding ASCII

@'
@echo off
if "%~1"=="group" (
  if "%~2"=="exists" (
    echo true
    exit /b 0
  )
)
if "%~1"=="containerapp" (
  if "%~2"=="list" (
    exit /b 0
  )
  if "%~2"=="show" (
    exit /b 0
  )
)
if "%~1"=="cognitiveservices" (
  if "%~2"=="account" (
    if "%~3"=="show" (
      exit /b 0
    )
    if "%~3"=="list" (
      echo aicu-cpskm4bh
echo aif-cpskm4bh
      exit /b 0
    )
    if "%~3"=="update" (
      exit /b 0
    )
  )
)
exit /b 0
'@ | Set-Content (Join-Path $stubDir 'az.cmd') -Encoding ASCII

$env:PATH = "$stubDir;$env:PATH"

$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add('http://127.0.0.1:18080/')
$listener.Start()

$listenerJob = Start-Job -ScriptBlock {
    param($listener)
    while ($true) {
        try {
            $context = $listener.GetContext()
            $response = $context.Response
            $response.StatusCode = 200
            $response.ContentType = 'application/json'
            $buffer = [System.Text.Encoding]::UTF8.GetBytes('{"ok":true}')
            $response.ContentLength64 = $buffer.Length
            $response.OutputStream.Write($buffer, 0, $buffer.Length)
            $response.OutputStream.Close()
        } catch {
            break
        }
    }
} -ArgumentList $listener

try {
    $output = & pwsh -NoProfile -File $scriptPath -ResourceGroupName 'rg-test' -SubscriptionId 'sub-test' -ApiBaseUrl 'http://127.0.0.1:18080'
    $outputText = ($output | Out-String)
    if ($outputText -match 'ERROR: ensuring environment exists') {
        throw 'Regression test failed: the script propagated an azd error string as a Cognitive Services account name.'
    }
    if ($outputText -notmatch 'Refreshing account: aif-cpskm4bh') {
        throw 'Regression test failed: the script did not auto-select the deployment-style aif account for refresh.'
    }
    Write-Host 'Regression test passed.'
}
finally {
    $listener.Stop()
    $listener.Close()
    Stop-Job $listenerJob -ErrorAction SilentlyContinue
    Remove-Job $listenerJob -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $tempRoot
}
