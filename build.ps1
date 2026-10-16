# Automated Build Script for Offline Windows Translator
param (
    [switch]$CreateZip = $true,
    [string]$Version = "v1.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building Offline Windows Translator with PyInstaller     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Locate Python 3.11
$pythonCmd = "python"
if (Test-Path "C:\Users\mosta\AppData\Local\Programs\Python\Python311\python.exe") {
    $pythonCmd = "C:\Users\mosta\AppData\Local\Programs\Python\Python311\python.exe"
}

Write-Host "[1/5] Using Python: $pythonCmd" -ForegroundColor Yellow
& $pythonCmd -V

Write-Host "[2/5] Verifying dependencies..." -ForegroundColor Yellow
& $pythonCmd -m pip install -r requirements.txt -r requirements-build.txt --quiet

Write-Host "[3/5] Cleaning prior build artifacts..." -ForegroundColor Yellow
if (Test-Path "dist\Localex") {
    Remove-Item -Recurse -Force "dist\Localex"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

Write-Host "[4/5] Running PyInstaller build..." -ForegroundColor Yellow
& $pythonCmd -m PyInstaller --noconfirm Localex.spec

# Ensure portable directories exist inside the build
$distFolder = "dist\Localex"
if (Test-Path $distFolder) {
    New-Item -ItemType Directory -Force -Path "$distFolder\models" | Out-Null
    New-Item -ItemType Directory -Force -Path "$distFolder\data" | Out-Null
    New-Item -ItemType Directory -Force -Path "$distFolder\logs" | Out-Null

    # Copy README and license/guide if present
    if (Test-Path "README.md") {
        Copy-Item "README.md" "$distFolder\README.txt"
    }

    # Calculate size
    $totalBytes = (Get-ChildItem -Recurse $distFolder | Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($totalBytes / 1MB, 2)
    Write-Host "[OK] Standalone folder built at: $distFolder ($sizeMB MB)" -ForegroundColor Green

    if ($CreateZip) {
        $zipName = if ($Version) { "Localex_Portable_$Version.zip" } else { "Localex_Portable.zip" }
        $zipPath = "dist\$zipName"
        if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
        Write-Host "[5/5] Compressing portable zip package..." -ForegroundColor Yellow
        Compress-Archive -Path "$distFolder\*" -DestinationPath $zipPath
        $zipBytes = (Get-Item $zipPath).Length
        $zipMB = [math]::Round($zipBytes / 1MB, 2)
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host " Portable Archive created successfully: $zipPath ($zipMB MB) " -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Cyan
    }
} else {
    Write-Host "[ERROR] Build failed, dist directory not found." -ForegroundColor Red
    exit 1
}
