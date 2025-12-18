<#
push_to_github.ps1

Usage:
  .\push_to_github.ps1 -RemoteUrl 'https://github.com/TechieLukesh/SHL.git' -Branch main

This script will initialize git (if needed), add all files, commit, set the remote URL,
and push to the specified branch. You must run this locally and authenticate (GitHub CLI or
username/password / PAT). The script does NOT store credentials for you.
#>

param(
    [string]$RemoteUrl = 'https://github.com/TechieLukesh/SHL.git',
    [string]$Branch = 'main',
    [string]$CommitMessage = 'Prepare repo for submission'
)

function Exec($cmd) {
    Write-Host "> $cmd"
    & cmd /c $cmd
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not in PATH. Install git and retry."
    exit 1
}

Set-Location $PSScriptRoot

if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..."
    Exec "git init"
} else {
    Write-Host "Existing git repository detected."
}

# Ensure branch exists locally
Exec "git checkout -B $Branch"

Exec "git add -A"
Exec "git commit -m \"$CommitMessage\"" 2>$null

# Configure remote
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Remote 'origin' already exists with URL: $existing"
    Write-Host "Updating remote URL to $RemoteUrl"
    Exec "git remote set-url origin $RemoteUrl"
} else {
    Exec "git remote add origin $RemoteUrl"
}

Write-Host "Pushing to remote... You may be prompted to authenticate."
Exec "git push -u origin $Branch"

Write-Host "Done. If push failed, authenticate locally using 'gh auth login' or provide a PAT."
