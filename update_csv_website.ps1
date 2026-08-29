# update_csv_website.ps1 - Aggiornamento CSV da fonti web pubbliche
# Usa SuperEnalotto.net come fonte alternativa

$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$reportPath = Join-Path $scriptDir "update_log.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGGIORNAMENTO CSV - FONTI WEB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Prova fonte alternativa: Superenalotto.net
$webUrls = @(
    "https://www.superenalotto.net/en/results",
    "https://www.estrazionedellotto.it/superenalotto/"
)

$success = $false
foreach ($url in $webUrls) {
    try {
        Write-Host "Tentativo: $url" -ForegroundColor Yellow
        $req = [System.Net.WebRequest]::Create($url)
        $req.Timeout = 10000
        $resp = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $html = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()
        
        if ($html -like "*superEnalotto*") {
            Write-Host "  -> HTML caricato ($($html.Length) caratteri)" -ForegroundColor Green
            $success = $true
            break
        }
    } catch {
        Write-Host "  -> Fallito: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not $success) {
    Write-Host " -> NESSUNA FONTE WEB DISPONIBILE" -ForegroundColor Red
    Write-Host " -> Usa CSV locale e aggiorna manualmente." -ForegroundColor Gray
    
    if (Test-Path $csvPath) {
        $lastLine = (Get-Content $csvPath | Select-Object -Last 1)
        Write-Host " -> Ultima estrazione locale: $lastLine" -ForegroundColor Yellow
    }
    exit 1
}

# Estrazione dati da HTML (base, da migliorare)
# Per ora, informa che serve scraping manuale
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  NOTA: Per aggiornamento automatico" -ForegroundColor Yellow
Write-Host "  serve API funzionante o scraper HTML." -ForegroundColor Yellow
Write-Host "  Per ora usa CSV locale + aggiornamento" -ForegroundColor Yellow
Write-Host "  manuale da superenalotto.net" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# Scrivi log
"$(Get-Date -Format "yyyy-MM-dd HH:mm"): Update tentato da web. Successo: $success" | Out-File $reportPath -Encoding UTF8 -Append
