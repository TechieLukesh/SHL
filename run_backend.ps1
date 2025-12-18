<#
run_backend.ps1

One-step PowerShell script to create a venv, install dependencies,
and start the FastAPI backend (uvicorn). Run from repository root:

  .\run_backend.ps1

This script is idempotent: if the virtual environment already exists
it will reuse it.
#>

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
catch {
    $scriptDir = Get-Location
}

Set-Location (Join-Path $scriptDir 'shl_recommender')

Write-Host "Working directory: $(Get-Location)"

if (-not (Test-Path '.venv')) {
    Write-Host "Creating virtual environment .venv..."
    python -m venv .venv
}
else {
    Write-Host "Virtual environment .venv already exists - reusing."
}

$py = Join-Path (Get-Location) '.venv\Scripts\python.exe'

Write-Host "Upgrading pip and installing dependencies..."
& $py -m pip install --upgrade pip setuptools wheel
& $py -m pip install -r requirements.txt

Write-Host "Starting backend (uvicorn) on http://127.0.0.1:8000 ..."
& $py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
