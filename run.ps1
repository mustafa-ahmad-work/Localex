# PowerShell runner for Offline Windows Translator
$ErrorActionPreference = "Stop"

$pythonExe = "C:\Users\mosta\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$scriptDir\src;$env:PYTHONPATH"

Set-Location $scriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Launching Offline Windows Translator...                " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

& $pythonExe -m Localex $args
