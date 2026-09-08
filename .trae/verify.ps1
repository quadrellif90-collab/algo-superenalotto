# Script di collaudo automatico per Windows PowerShell
Write-Output "=== INIZIO VERIFICA AUTOMATICA (WINDOWS) ==="

# Type-Check TypeScript (se presente)
if (Test-Path "tsconfig.json") {
    npx tsc --noEmit
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# Test Node.js (se presente)
if (Test-Path "package.json") {
    npm test
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# --- Collaudo Python (progetto SuperEnalotto, solo stdlib) ---
# 1) Compilazione bytecode di tutti i sorgenti .py
Write-Output "--- Python: verifica compilazione ---"
$pyFiles = Get-ChildItem -Filter "*.py" -File | Where-Object { $_.Name -ne "make_icon.py" }
foreach ($f in $pyFiles) {
    python -m py_compile $f.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Compilazione fallita: $($f.Name)"
        exit 1
    }
}
Write-Output "Compilazione OK ($($pyFiles.Count) file)"

# 2) Riga di test necessaria: esegue lo script di audit rigoroso
Write-Output "--- Python: esecuzione audit rigoroso ---"
python rigorous_backtest_audit.py
if ($LASTEXITCODE -ne 0) { exit 1 }

# 3) Verifica presenza e validità degli output
Write-Output "--- Python: verifica output generati ---"
$jsonOk = $false
$mdOk = $false
foreach ($f in @("rigorous_audit_results.json", "AUDIT_RIGOROSO_SUPERENALOTTO.md")) {
    if (-not (Test-Path $f)) {
        Write-Error "Output mancante: $f"
        exit 1
    }
    if ($f -like "*.json") {
        try {
            Get-Content $f -Raw | ConvertFrom-Json | Out-Null
            $jsonOk = $true
            Write-Output "JSON valido: $f"
        } catch {
            Write-Error "JSON non valido: $f"
            exit 1
        }
    } else {
        $mdOk = $true
        Write-Output "Report presente: $f"
    }
}

# 4) Sanity check statistico: nessuna strategia deve avere ROI positivo
Write-Output "--- Python: sanity check conclusioni ---"
if ($jsonOk) {
    $data = Get-Content "rigorous_audit_results.json" -Raw | ConvertFrom-Json
    $positiveRoi = @($data.PSObject.Properties | Where-Object { $_.Value.roi -gt 0 })
    if ($positiveRoi.Count -gt 0) {
        Write-Error "ROI positivo trovato in $($positiveRoi.Count) strategie: incoerente con l'audit"
        exit 1
    }
    Write-Output "Verifica ROI OK: nessuna strategia con ROI positivo"
}

Write-Output "=== TUTTI I TEST SONO PASSATI CON SUCCESSO ==="
exit 0
