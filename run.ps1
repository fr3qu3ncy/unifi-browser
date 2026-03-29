# run.ps1 — start Unifi Browser inside a Python virtual environment (Windows)
#
# Usage:
#   .\run.ps1
#
# If execution policy blocks the script, run once as Administrator:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"

$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvDir      = Join-Path $ScriptDir ".venv"
$Requirements = Join-Path $ScriptDir "requirements.txt"
$MainScript   = Join-Path $ScriptDir "main.py"

# ── Check Python is available ─────────────────────────────────────────────────
$Python = $null
foreach ($candidate in @("python", "python3")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3") {
            $Python = $candidate
            break
        }
    } catch { }
}

if (-not $Python) {
    Write-Error "Python 3 was not found. Please install Python 3.10+ from https://python.org and ensure it is on your PATH."
    exit 1
}

Write-Host "Using $Python ($( & $Python --version 2>&1 ))" -ForegroundColor Cyan

# ── Create venv if it doesn't exist ──────────────────────────────────────────
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment at $VenvDir ..." -ForegroundColor Cyan
    & $Python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
}

# ── Activate venv ─────────────────────────────────────────────────────────────
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Error "Activation script not found at $ActivateScript. Try deleting .venv and re-running."
    exit 1
}
. $ActivateScript

# ── Install / update dependencies ─────────────────────────────────────────────
Write-Host "Installing requirements ..." -ForegroundColor Cyan
python -m pip install --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit 1 }

python -m pip install --quiet -r $Requirements
if ($LASTEXITCODE -ne 0) { Write-Error "Dependency installation failed."; exit 1 }

# ── Launch the app ────────────────────────────────────────────────────────────
Write-Host "Starting Unifi Browser ..." -ForegroundColor Cyan
python $MainScript
