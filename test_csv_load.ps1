# Test loading CSV
$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"

Write-Host "Testing CSV loading..." -ForegroundColor Cyan
Write-Host "Path: $csvPath" -ForegroundColor White

if (Test-Path $csvPath) {
    Write-Host "File EXISTS" -ForegroundColor Green
    $lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
    Write-Host "Lines after header: $($lines.Count)" -ForegroundColor White
    
    # Test parsing first line
    $firstLine = $lines[0]
    $parts = $firstLine -split ','
    Write-Host "Parts count: $($parts.Count)" -ForegroundColor White
    if ($parts.Count -ge 8) {
        $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
        Write-Host "Numbers: $($nums -join ', ')" -ForegroundColor White
        Write-Host "Sum: $(($nums | Measure-Object -Sum).Sum)" -ForegroundColor White
    }
} else {
    Write-Host "File NOT FOUND!" -ForegroundColor Red
}