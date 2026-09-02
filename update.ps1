# SuperEnalotto Auto-Update Script
# Controlla GitHub Releases e aggiorna l'EXE se necessario

param(
    [switch]$Force = $false,
    [switch]$Silent = $false
)

$ErrorActionPreference = "Stop"

# Configurazione
$Repo = "quadrellif90-collab/algo-superenalotto"
$InstallDir = "$env:USERPROFILE\Desktop\Superenalotto"
$ExeName = "SuperEnalotto.exe"
$CurrentExe = Join-Path $InstallDir $ExeName
$TempDir = "$env:TEMP\SuperEnalotto_Update"
$CurrentVersionFile = Join-Path $InstallDir ".version"

function Write-Log($msg) {
    if (-not $Silent) {
        Write-Host "[SuperEnalotto] $msg" -ForegroundColor Cyan
    }
}

function Get-CurrentVersion() {
    if (Test-Path $CurrentVersionFile) {
        return (Get-Content $CurrentVersionFile -Raw).Trim()
    }
    return "0.0.0"
}

function Get-LatestRelease() {
    $url = "https://api.github.com/repos/$Repo/releases/latest"
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -Headers @{
            "User-Agent" = "SuperEnalotto-Updater"
            "Accept" = "application/vnd.github.v3+json"
        }
        return $response
    } catch {
        Write-Log "Errore nel controllo aggiornamenti: $_"
        return $null
    }
}

function Download-File($url, $dest) {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "SuperEnalotto-Updater")
    $wc.DownloadFile($url, $dest)
}

# Main
Write-Log "Controllo aggiornamenti..."

$release = Get-LatestRelease
if (-null -eq $release) {
    Write-Log "Impossibile controllare gli aggiornamenti. Riprova più tardi."
    exit 1
}

$latestVersion = $release.tag_name
$currentVersion = Get-CurrentVersion

Write-Log "Versione corrente: $currentVersion"
Write-Log "Ultima versione: $latestVersion"

if (-not $Force -and $latestVersion -eq $currentVersion) {
    Write-Log "L'app è già aggiornata."
    exit 0
}

Write-Log "Nuova versione trovata: $latestVersion"

# Trova l'asset EXE
$asset = $release.assets | Where-Object { $_.name -eq $ExeName } | Select-Object -First 1
if (-null -eq $asset) {
    Write-Log "Asset $ExeName non trovato nella release $latestVersion."
    exit 1
}

# Download
Write-Log "Download $ExeName..."
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
$tempExe = Join-Path $TempDir $ExeName
Download-File $asset.browser_download_url $tempExe

# Verifica download
if (-not (Test-Path $tempExe)) {
    Write-Log "Errore nel download."
    exit 1
}

# Backup versione corrente
if (Test-Path $CurrentExe) {
    $backupExe = Join-Path $InstallDir "SuperEnalotto.backup.exe"
    Copy-Item $CurrentExe $backupExe -Force
    Write-Log "Backup creato: SuperEnalotto.backup.exe"
}

# Chiudi l'app se in esecuzione
$proc = Get-Process -Name "SuperEnalotto" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Log "Chiusura app in corso..."
    $proc | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Installa nuova versione
Copy-Item $tempExe $CurrentExe -Force
Write-Log "Installata versione $latestVersion"

# Salva versione
$latestVersion | Set-Content $CurrentVersionFile -NoNewline

# Pulisci
Remove-Item $TempDir -Recurse -Force

Write-Log "Aggiornamento completato!"

# Riavvia l'app
Start-Process $CurrentExe
Write-Log "App riavviata."
