# Debug decade calculation
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"

Write-Host "Testing decade calculation..." -ForegroundColor Cyan

# Load just the numbers
$records = [System.Collections.Generic.List[PSCustomObject]]@()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
            $records.Add([PSCustomObject]@{ Nums = $nums })
        } catch { continue }
    }
}

Write-Host "Total numbers: $($records.Count * 6)" -ForegroundColor White

# Test decade calculation
$allNums = [System.Collections.Generic.List[int]]@()
foreach ($r in $records) { foreach ($n in $r.Nums) { $allNums.Add($n) } }

$decadeDist = @{}
foreach ($n in $allNums) {
    $dec = [Math]::Floor($n / 10)
    if ($decadeDist.ContainsKey($dec)) {
        $decadeDist[$dec]++
    } else {
        $decadeDist[$dec] = 1
    }
}

Write-Host "Decade distribution (raw):" -ForegroundColor Yellow
foreach ($d in 0..9) {
    $start = $d * 10 + 1
    $end = $d * 10 + 10
    if ($d -eq 9) { $end = 90 }
    $count = 0
    if ($decadeDist.ContainsKey($d)) { $count = $decadeDist[$d] }
    Write-Host "  $start-$end (floor=$d): $count numeri" -ForegroundColor White
}

# Test the corrected decadePct logic
$totalNums = $allNums.Count
$decadePct = @{}
foreach ($d in 0..9) {
    $count = 0
    if ($decadeDist.ContainsKey($d)) { $count = $decadeDist[$d] }
    $decadePct[[string]$d] = [Math]::Round($count / $totalNums * 100, 2)
}

Write-Host "`nDecade percentages (calculated):" -ForegroundColor Yellow
foreach ($d in 0..9) {
    $start = $d * 10 + 1
    $end = $d * 10 + 10
    if ($d -eq 9) { $end = 90 }
    $pct = $decadePct[[string]$d]
    Write-Host ("  " + $start + "-" + $end + ": " + $pct + "%") -ForegroundColor White
}