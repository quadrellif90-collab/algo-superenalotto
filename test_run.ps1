Write-Host "Test path" -ForegroundColor Cyan
$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
Write-Host "Path: $csvPath" -ForegroundColor White
Write-Host "Exists: $(Test-Path $csvPath)" -ForegroundColor White
if (Test-Path $csvPath) {
    $lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
    Write-Host "Lines count: $($lines.Count)" -ForegroundColor White
}
