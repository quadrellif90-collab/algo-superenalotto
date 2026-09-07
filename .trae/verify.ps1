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

Write-Output "=== TUTTI I TEST SONO PASSATI CON SUCCESSO ==="
exit 0
