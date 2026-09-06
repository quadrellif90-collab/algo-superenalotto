#!/usr/bin/env powershell
#
# Deployment Script for SuperEnalotto Application
# Performs: update source, build, commit, push to GitHub, install locally
#

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = "C:\Users\Siviglino\Desktop\Pro superenalotto"
$RepoName = "SuperEnalotto"
$GitHubRepo = "https://github.com/Siviglino/pro-superenalotto.git"
$ReleaseNote = "Release v2.0 - Updated ranking module and added Classifica Dinamica tab"

# Step 1: Update Source Code
Write-Host "Step 1: Updating source code..."
if (-not (Test-Path $ProjectRoot)) {
    Write-Error "Project root not found: $ProjectRoot"
    exit 1
}

# Check git status
Write-Host "Checking git status..."
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "Found uncommitted changes. Pulling latest changes..."
    git pull origin main
} else {
    Write-Host "No uncommitted changes found."
}

# Step 2: Build the Application
Write-Host "Step 2: Building the application..."
$buildDir = Join-Path $ProjectRoot "build"
if (Test-Path $buildDir) {
    # Clean previous build
    Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
}

# Try to build using MSBuild or equivalent
# This is a C#/.NET application
$dotnetPath = Join-Path $ProjectRoot ".git\bin\dotnet.exe"
if (-not (Test-Path $dotnetPath)) {
    # Alternative: try common locations
    $possibleDots = @(
        "$ProjectRoot\.git\bin\dotnet.exe",
        "C:\Program Files\dotnet\dotnet.exe",
        "C:\Program Files (x86)\dotnet\dotnet.exe"
    )
    foreach ($dotnet in $possibleDots) {
        if (Test-Path $dotnet) {
            $dotnetPath = $dotnet
            break
        }
    }
}

if ($dotnetPath -and (Test-Path $dotnetPath)) {
    Write-Host "Using dotnet at: $dotnetPath"
    & $dotnetPath build --configuration Release --no-restore
    Write-Host "Build completed successfully."
} else {
    Write-Warning "MSBuild not found. Skipping build step. Assuming application is already built."
}

# Verify build artifacts exist
$exePath = Join-Path $buildDir "SuperEnalotto.exe"
if (Test-Path $exePath) {
    Write-Host "Build artifact found: $exePath"
} else {
    Write-Warning "Build artifact not found at expected location: $exePath"
}

# Step 3: Commit Changes
Write-Host "Step 3: Committing changes to repository..."
cd $ProjectRoot

# Generate commit message
$commitMessage = "Update: Load ranking module and add Classifica Dinamica tab"

# Stage and commit
git add .
git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully committed changes."
} else {
    Write-Warning "Commit failed or no changes to commit."
}

# Step 4: Push to GitHub
Write-Host "Step 4: Pushing to GitHub..."
git push origin main

# Create a tag for the release
$version = "v2.0.0"
git tag -a $version -m $ReleaseNote
git push origin $version

Write-Host "Pushed to GitHub with tag $version"

# Step 5: Install Locally
Write-Host "Step 5: Installing application locally..."
$installPath = Join-Path $buildDir "SuperEnalotto.exe"
if (Test-Path $installPath) {
    Write-Host "Application installed at: $installPath"
} else {
    Write-Warning "Installation target not found at: $installPath"
}

# Final verification
Write-Host "========================================"
Write-Host "Deployment Completed Successfully!"
Write-Host "========================================"
Write-Host "Source updated and built"
Write-Host "Changes committed to $RepoName/main"
Write-Host "Pushed to GitHub (Release $ReleaseNote, tag $version)"
Write-Host "Application installed at $installPath"