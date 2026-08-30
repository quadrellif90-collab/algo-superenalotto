# Simple CSV test
$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
Write-Host "Testing CSV load..." -ForegroundColor Cyan
Write-Host "Path: $csvPath" -ForegroundColor White

if (Test-Path $csvPath) {
    Write-Host "File exists" -ForegroundColor Green
    $content = Get-Content $csvPath -Encoding UTF8
    Write-Host "Total lines: $($content.Count)" -ForegroundColor White
    
    # Show first few lines
    Write-Host "First 5 lines after header:" -ForegroundColor Yellow
    $content[1..5] | ForEach-Object { Write-Host $_ }
    
    # Try parsing first line
    $firstLine = $content[1]
    Write-Host "First line: $firstLine" -ForegroundColor White
    $parts = $firstLine -split ','
    Write-Host "Parts count: $($parts.Count)" -ForegroundColor White
    
    if ($parts.Count -ge 9) {
        $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
        Write-Host "Numbers parsed: $($nums -join ', ')" -ForegroundColor Green
        Write-Host "Sum: $(($nums | Measure-Object -Sum).Sum)" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Not enough columns!" -ForegroundColor Red
        Write-Host "Parts: $parts" -ForegroundColor Red
    }
} else {
    Write-Host "ERROR: File not found!" -ForegroundColor Red
}