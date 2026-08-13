[CmdletBinding()]
param(
    [switch]$CoreOnly,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH. Install Python 3.10 or newer and reopen PowerShell."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..." -ForegroundColor Cyan
    python -m venv .venv
}

$VenvPython = ".\.venv\Scripts\python.exe"
$Nimo = ".\.venv\Scripts\nimo.exe"
$InstallTarget = if ($CoreOnly) { "." } else { ".[all,dev]" }

Write-Host "Installing Project NIMO ($InstallTarget)..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e $InstallTarget

Write-Host "Verifying CLI..." -ForegroundColor Cyan
& $Nimo --version

if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    & $VenvPython -m pytest
}

Write-Host "Project NIMO is ready." -ForegroundColor Green
Write-Host "Run: .\.venv\Scripts\nimo.exe dashboard"
