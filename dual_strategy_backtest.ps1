# Dual Strategy Backtest - 2 best strategies, 2 tickets per draw
# Includes prize for Match 2 (~€2-5)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "dual_strategy_backtest.json"

# Load draws
Write-Host "Loading draws..." -ForegroundColor Cyan
$records = @()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
            $records += [PSCustomObject]@{ Date = $parts[0]; Numbers = $nums }
        } catch { continue }
    }
}
Write-Host "Loaded $($records.Count) draws" -ForegroundColor Green

# Prize structure (updated with Match 2)
$prizes = @{ "2" = 5; "3" = 10; "4" = 100; "5" = 1000; "6" = 1000000 }

# === STRATEGY 1: 90NumberCycle ===
function Get-90NumberCycleTicket {
    param([int]$cycleIndex)
    $cycleCombos = @()
    for ($i = 0; $i -lt 15; $i++) {
        $combo = 1..90 | Select-Object -Skip ($i * 6) -First 6
        $cycleCombos += ,@($combo)
    }
    return $cycleCombos[$cycleIndex % 15] | Sort-Object
}

# === STRATEGY 2: LastDigitSpread (constrained) ===
function Get-LastDigitSpreadTicket {
    $attempts = 0
    while ($attempts -lt 200) {
        $attempts++
        $candidate = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
        $lastDigits = $candidate | ForEach-Object { $_ % 10 }
        if (($lastDigits | Select-Object -Unique).Count -ne 6) { continue }
        $s = ($candidate | Measure-Object -Sum).Sum
        if ($s -lt 246 -or $s -gt 306) { continue }
        $decadeDist = @{}
        foreach ($n in $candidate) {
            $d = [int][Math]::Floor($n / 10)
            if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
        }
        if ($decadeDist.Values -contains 3) { continue }
        if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
        return $candidate
    }
    return Get-Random -InputObject (1..90) -Count 6 | Sort-Object
}

# === STRATEGY 3: SameNumbersPerpetual (1,2,3,4,5,6) ===
function Get-SameNumbersTicket { return @(1, 2, 3, 4, 5, 6) }

# === STRATEGY 4: OddEvenBalanced ===
function Get-OddEvenBalancedTicket {
    $odds = 1..90 | Where-Object { $_ % 2 -eq 1 }
    $evens = 1..90 | Where-Object { $_ % 2 -eq 0 }
    $attempts = 0
    while ($attempts -lt 200) {
        $attempts++
        $candidate = (Get-Random -InputObject $odds -Count 3) + (Get-Random -InputObject $evens -Count 3) | Sort-Object
        $s = ($candidate | Measure-Object -Sum).Sum
        if ($s -lt 246 -or $s -gt 306) { continue }
        $decadeDist = @{}
        foreach ($n in $candidate) {
            $d = [int][Math]::Floor($n / 10)
            if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
        }
        if ($decadeDist.Values -contains 3) { continue }
        if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
        return $candidate
    }
    return Get-Random -InputObject (1..90) -Count 6 | Sort-Object
}

# Test combinations of 2 strategies (1 ticket each per draw)
$strategies = @{
    "90NumberCycle" = { Get-90NumberCycleTicket -cycleIndex $args[0] }
    "LastDigitSpread" = { Get-LastDigitSpreadTicket }
    "SameNumbersPerpetual" = { Get-SameNumbersTicket }
    "OddEvenBalanced" = { Get-OddEvenBalancedTicket }
}

$combos = @(
    @("90NumberCycle", "LastDigitSpread"),
    @("90NumberCycle", "SameNumbersPerpetual"),
    @("90NumberCycle", "OddEvenBalanced"),
    @("LastDigitSpread", "SameNumbersPerpetual"),
    @("LastDigitSpread", "OddEvenBalanced"),
    @("SameNumbersPerpetual", "OddEvenBalanced")
)

$results = @{}

Write-Host "`n=== DUAL STRATEGY BACKTEST (1+1 tickets per draw) ===" -ForegroundColor Cyan

foreach ($combo in $combos) {
    $s1 = $combo[0]; $s2 = $combo[1]
    $key = "$s1 + $s2"
    $r = @{ "2"=0; "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0 }
    $cycleIndex = 0
    
    foreach ($draw in $records) {
        # Ticket 1
        $t1 = & $strategies[$s1] $cycleIndex
        $r.spent += 1
        $m1 = ($t1 | Where-Object { $draw.Numbers -contains $_ }).Count
        if ($m1 -ge 2) { $r[$m1.ToString()]++; $r.won += $prizes[$m1.ToString()] }
        
        # Ticket 2
        $t2 = & $strategies[$s2] $cycleIndex
        $r.spent += 1
        $m2 = ($t2 | Where-Object { $draw.Numbers -contains $_ }).Count
        if ($m2 -ge 2) { $r[$m2.ToString()]++; $r.won += $prizes[$m2.ToString()] }
        
        $cycleIndex++
    }
    $r.net = $r.won - $r.spent
    $r.roi = [Math]::Round(($r.won / $r.spent) * 100, 2)
    $results[$key] = $r
    
    Write-Host ("  " + $key + ": Net " + $r.net + " | M2:" + $r["2"] + " M3:" + $r["3"] + " M4:" + $r["4"] + " M5:" + $r["5"] + " M6:" + $r["6"] + " | ROI: " + $r.roi + "%") -ForegroundColor White
}

# Find best
$best = ($results.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1)
Write-Host "`n=== BEST COMBO: " + $best.Key + " (Net: " + $best.Value.net + ", ROI: " + $best.Value.roi + "%)" -ForegroundColor Green

# Save JSON
$report = @{
    metadata = @{ totalDraws = $records.Count; ticketsPerDraw = 2; totalTickets = $records.Count * 2 }
    bestCombo = $best.Key
    combinations = @{}
}
foreach ($k in $results.Keys) {
    $r = $results[$k]
    $report.combinations[$k] = @{
        totalSpent = $r.spent; totalWon = $r.won; netResult = $r.net
        match2 = $r["2"]; match3 = $r["3"]; match4 = $r["4"]; match5 = $r["5"]; match6 = $r["6"]
        roiPercent = $r.roi
    }
}
$report | ConvertTo-Json -Depth 5 | Set-Content -Path $outputPath -Encoding UTF8
Write-Host "Saved: $outputPath" -ForegroundColor Yellow