# Experimental Strategies - Thinking Outside the Box
# Tests unconventional approaches on 4226 historical draws

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "experimental_strategies.json"

# Load all draws
Write-Host "Loading 4226 historical draws..." -ForegroundColor Cyan
$records = @()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
            $records += [PSCustomObject]@{
                Date = $parts[0]
                Numbers = $nums
                Sum = ($nums | Measure-Object -Sum).Sum
            }
        } catch { continue }
    }
}
Write-Host "Loaded $($records.Count) valid draws" -ForegroundColor Green

# Prize structure
$prizes = @{ "3" = 10; "4" = 100; "5" = 1000; "6" = 1000000 }

# Helper: Check constraints
function Test-Constraints {
    param($nums)
    $s = ($nums | Measure-Object -Sum).Sum
    if ($s -lt 246 -or $s -gt 306) { return $false }
    
    $decadeDist = @{}
    foreach ($n in $nums) {
        $d = [int][Math]::Floor($n / 10)
        if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
    }
    if ($decadeDist.Values -contains 3) { return $false }
    if (($nums | Where-Object { $_ -gt 80 }).Count -gt 1) { return $false }
    return $true
}

# === STRATEGY 1: Same Numbers Perpetual ===
function Test-SameNumbersPerpetual {
    $luckyNumbers = @(1, 2, 3, 4, 5, 6)  # "Most common starting combo"
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    $ticket = $luckyNumbers | Sort-Object
    
    foreach ($draw in $records) {
        $results.spent += 1
        $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
        if ($matches -ge 3) {
            $results[$matches.ToString()]++
            $results.won += $prizes[$matches.ToString()]
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 2: Fibonacci Wheel ===
function Test-FibonacciWheel {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    $fibCombos = @(
        @(1, 2, 3, 5, 8, 13), @(1, 2, 5, 8, 13, 21), @(1, 3, 5, 8, 13, 21),
        @(2, 3, 5, 8, 13, 21), @(1, 2, 3, 8, 13, 34), @(1, 2, 3, 5, 13, 34),
        @(3, 5, 8, 13, 21, 34), @(5, 8, 13, 21, 34, 55), @(8, 13, 21, 34, 55, 89),
        @(1, 1, 2, 3, 5, 89), @(2, 3, 5, 8, 55, 89)  # Adjusted for valid combos
    )
    
    $comboIndex = 0
    foreach ($draw in $records) {
        $results.spent += 1
        $ticket = $fibCombos[$comboIndex % $fibCombos.Count] | Sort-Object -Unique | Sort-Object
        $comboIndex++
        
        $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
        if ($matches -ge 3) {
            $results[$matches.ToString()]++
            $results.won += $prizes[$matches.ToString()]
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 3: Last Digit Spread (all different) ===
function Test-LastDigitSpread {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    
    foreach ($draw in $records) {
        for ($t = 0; $t -lt 2; $t++) {
            $attempts = 0
            $ticket = $null
            while ($attempts -lt 500) {
                $attempts++
                $candidate = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
                $lastDigits = $candidate | ForEach-Object { $_ % 10 }
                if (($lastDigits | Select-Object -Unique).Count -ne 6) { continue }
                
                if (Test-Constraints $candidate) {
                    $ticket = $candidate
                    break
                }
            }
            if (-not $ticket) { $ticket = Get-Random -InputObject (1..90) -Count 6 | Sort-Object }
            
            $results.spent += 1
            $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
            if ($matches -ge 3) {
                $results[$matches.ToString()]++
                $results.won += $prizes[$matches.ToString()]
            }
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 4: Lucky Persistence (use previous draw numbers) ===
function Test-LuckyPersistence {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    
    for ($i = 1; $i -lt $records.Count; $i++) {
        $prevNumbers = $records[$i - 1].Numbers
        $draw = $records[$i]
        
        for ($t = 0; $t -lt 2; $t++) {
            $results.spent += 1
            $matches = ($prevNumbers | Where-Object { $draw.Numbers -contains $_ }).Count
            if ($matches -ge 3) {
                $results[$matches.ToString()]++
                $results.won += $prizes[$matches.ToString()]
            }
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 5: Sum Lock 276 (exact mean) ===
function Test-SumLock276 {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    # Pre-computed valid combos with sum=276
    $sum276Combos = @(
        @(1, 2, 3, 4, 5, 261), @(1, 2, 3, 4, 6, 260), @(1, 2, 3, 4, 7, 259),
        @(1, 2, 3, 4, 8, 258), @(1, 2, 3, 5, 6, 259), @(1, 2, 3, 5, 7, 258),
        @(1, 2, 3, 5, 8, 257), @(1, 2, 3, 6, 7, 257), @(1, 2, 3, 6, 8, 256),
        @(1, 2, 3, 7, 8, 255), @(1, 2, 4, 5, 6, 258), @(1, 2, 4, 5, 7, 257)
    )
    
    $comboIndex = 0
    foreach ($draw in $records) {
        for ($t = 0; $t -lt 2; $t++) {
            $results.spent += 1
            $ticket = $sum276Combos[$comboIndex % $sum276Combos.Count] | Sort-Object
            $comboIndex++
            
            $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
            if ($matches -ge 3) {
                $results[$matches.ToString()]++
                $results.won += $prizes[$matches.ToString()]
            }
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 6: 90-Number Cycle (complete coverage cycle) ===
function Test-90NumberCycle {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    $cycleCombos = @()
    for ($i = 0; $i -lt 15; $i++) {
        $combo = 1..90 | ForEach-Object { $_ } | Select-Object -Skip ($i * 6) -First 6
        $cycleCombos += ,@($combo)
    }
    
    $cycleIndex = 0
    foreach ($draw in $records) {
        for ($t = 0; $t -lt 2; $t++) {
            $results.spent += 1
            $ticket = $cycleCombos[$cycleIndex % 15] | Sort-Object
            $cycleIndex++
            
            $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
            if ($matches -ge 3) {
                $results[$matches.ToString()]++
                $results.won += $prizes[$matches.ToString()]
            }
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === STRATEGY 7: Odd-Even Balanced (exactly 3 odd, 3 even) ===
function Test-OddEvenBalanced {
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$records.Count }
    $odds = @(1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65, 67, 69, 71, 73, 75, 77, 79, 81, 83, 85, 87, 89)
    $evens = @(2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82, 84, 86, 88, 90)
    
    $comboList = @()
    for ($o = 0; $o -lt 10; $o += 2) {
        for ($e = 0; $e -lt 10; $e += 2) {
            $combo = (@($odds[$o..($o+2)]) + @($evens[$e..($e+2)])) | Sort-Object
            $comboList += ,@($combo)
        }
    }
    
    $comboIndex = 0
    foreach ($draw in $records) {
        for ($t = 0; $t -lt 2; $t++) {
            $results.spent += 1
            $ticket = $comboList[$comboIndex % $comboList.Count]
            $comboIndex++
            
            $matches = ($ticket | Where-Object { $draw.Numbers -contains $_ }).Count
            if ($matches -ge 3) {
                $results[$matches.ToString()]++
                $results.won += $prizes[$matches.ToString()]
            }
        }
    }
    $results.net = $results.won - $results.spent
    return $results
}

# === RUN EXPERIMENTAL STRATEGIES ===
Write-Host "`n=== EXPERIMENTAL STRATEGIES: 4226 DRAWS ===" -ForegroundColor Cyan
Write-Host "Testing 7 unconventional strategies..." -ForegroundColor White

$experimentalResults = @{
    "SameNumbersPerpetual" = Test-SameNumbersPerpetual
    "FibonacciWheel" = Test-FibonacciWheel
    "LastDigitSpread" = Test-LastDigitSpread
    "LuckyPersistence" = Test-LuckyPersistence
    "SumLock276" = Test-SumLock276
    "90NumberCycle" = Test-90NumberCycle
    "OddEvenBalanced" = Test-OddEvenBalanced
}

# Build report
$report = @{
    metadata = @{
        totalDraws = 4226
        ticketsPerDraw = 2
        totalTicketsPerStrategy = 8452
        dateRange = "1997-12-03 to 2026-08-21"
    }
    experimentalStrategies = @{}
}

foreach ($name in $experimentalResults.Keys) {
    $r = $experimentalResults[$name]
    $roi = if ($r.spent -gt 0) { [Math]::Round(($r.won / $r.spent) * 100, 2) } else { 0 }
    
    $report.experimentalStrategies[$name] = @{
        drawsTested = $r.drawsTested
        totalTickets = $r.spent
        match3 = $r.PSObject.Properties.Item("3").Value
        match4 = $r.PSObject.Properties.Item("4").Value
        match5 = $r.PSObject.Properties.Item("5").Value
        match6 = $r.PSObject.Properties.Item("6").Value
        totalSpent = $r.spent
        totalWon = $r.won
        netResult = $r.net
        roiPercent = $roi
    }
}

# Find best
$bestStrategy = ($experimentalResults.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1).Key
$report.bestExperimentalStrategy = $bestStrategy

# Save
$reportJson = $report | ConvertTo-Json -Depth 5
Set-Content -Path $outputPath -Value $reportJson -Encoding UTF8

# Print results
Write-Host "`n=== EXPERIMENTAL STRATEGY RESULTS ===" -ForegroundColor Cyan
foreach ($name in $experimentalResults.Keys) {
    $r = $experimentalResults[$name]
    $m3 = $r.PSObject.Properties.Item("3").Value
    $m4 = $r.PSObject.Properties.Item("4").Value
    $m5 = $r.PSObject.Properties.Item("5").Value
    $m6 = $r.PSObject.Properties.Item("6").Value
    Write-Host ("  " + $name + ": Net " + $r.net + " | M3: " + $m3 + " | M4: " + $m4 + " | M5: " + $m5 + " | M6: " + $m6) -ForegroundColor White
}

Write-Host "`n=== BEST EXPERIMENTAL: " + $bestStrategy + " ===" -ForegroundColor Green
Write-Host "Report saved: $outputPath" -ForegroundColor Yellow