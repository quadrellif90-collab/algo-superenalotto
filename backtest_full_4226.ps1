# Comprehensive Backtest - Full 4226 draws
# Tests multiple strategies on entire dataset

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "backtest_full_4226.json"

# Load all draws
Write-Host "Loading superenalotto.csv..." -ForegroundColor Cyan
$records = @()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
            foreach ($n in $nums) { if ($n -lt 1 -or $n -gt 90) { throw "Invalid number" } }
            $records += [PSCustomObject]@{
                Date = $parts[0]
                Numbers = $nums
            }
        } catch { continue }
    }
}
Write-Host "Loaded $($records.Count) valid draws" -ForegroundColor Green

# Prize structure (EUR)
$prizes = @{
    "3" = 10
    "4" = 100
    "5" = 1000
    "6" = 1000000
}

# Strategy 1: Pure Random
function Test-RandomStrategy {
    param([PSCustomObject[]]$draws, [int]$ticketsPerDraw)
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$draws.Count }
    foreach ($draw in $draws) {
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $results.spent += 1
            $ticket = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
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

# Strategy 2: Original Constraints (Sum ±30, Max 2/decade, Max 1>80)
function Test-OriginalConstraintsStrategy {
    param([PSCustomObject[]]$draws, [int]$ticketsPerDraw)
    $meanSum = 276.37
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$draws.Count }
    foreach ($draw in $draws) {
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $attempts = 0
            $ticket = $null
            while ($attempts -lt 500) {
                $attempts++
                $candidate = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
                $s = ($candidate | Measure-Object -Sum).Sum
                if ($s -lt $meanSum - 30 -or $s -gt $meanSum + 30) { continue }
                $decadeDist = @{}
                foreach ($n in $candidate) {
                    $d = [int][Math]::Floor($n / 10)
                    if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
                }
                if ($decadeDist.Values -contains 3) { continue }
                if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
                $ticket = $candidate
                break
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

# Strategy 3: Hot-Cold Optimized (using pre-computed hot/cold numbers)
function Test-HotColdStrategy {
    param([PSCustomObject[]]$draws, [int]$ticketsPerDraw)
    # Pre-compute hot/cold from entire dataset (same for all tests)
    $allNums = @()
    foreach ($d in $draws) { $allNums += $d.Numbers }
    $freq = @{}
    foreach ($n in $allNums) { if ($freq.ContainsKey($n)) { $freq[$n]++ } else { $freq[$n] = 1 } }
    $sortedFreq = $freq.GetEnumerator() | Sort-Object Value -Descending
    $totalUnique = $sortedFreq.Count
    $hotCount = [Math]::Max(1, [int]($totalUnique * 0.1))
    $coldCount = [Math]::Max(1, [int]($totalUnique * 0.2))
    $hotNumbers = $sortedFreq | Select-Object -First $hotCount | ForEach-Object { $_.Name } | Sort-Object
    $coldNumbers = $sortedFreq | Select-Object -Last $coldCount | ForEach-Object { $_.Name } | Sort-Object
    
    $meanSum = 276.37
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$draws.Count }
    
    foreach ($draw in $draws) {
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $attempts = 0
            $ticket = $null
            while ($attempts -lt 500) {
                $attempts++
                # Pick 3 hot + 3 cold (or 4 hot + 2 cold)
                $hotToPick = Get-Random -Minimum 2 -Maximum 4
                $coldToPick = 6 - $hotToPick
                $selectedHot = Get-Random -InputObject $hotNumbers -Count $hotToPick
                $selectedCold = Get-Random -InputObject $coldNumbers -Count $coldToPick
                $candidate = ($selectedHot + $selectedCold) | Sort-Object
                
                $s = ($candidate | Measure-Object -Sum).Sum
                if ($s -lt $meanSum - 30 -or $s -gt $meanSum + 30) { continue }
                
                $decadeDist = @{}
                foreach ($n in $candidate) {
                    $d = [int][Math]::Floor($n / 10)
                    if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
                }
                if ($decadeDist.Values -contains 3) { continue }
                if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
                
                # Check GT31 balance
                $gt31Ratio = ($candidate | Where-Object { $_ -gt 31 }).Count / 6.0
                if ([Math]::Abs($gt31Ratio - 0.6636) -gt 0.15) { continue }
                
                $ticket = $candidate
                break
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

# Strategy 4: Anti-Recent (avoid numbers from last 5 draws)
function Test-AntiRecentStrategy {
    param([PSCustomObject[]]$draws, [int]$ticketsPerDraw)
    $meanSum = 276.37
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$draws.Count }
    
    for ($i = 0; $i -lt $draws.Count; $i++) {
        $draw = $draws[$i]
        # Get recent draws to avoid
        $recentAvoid = @()
        for ($j = [Math]::Max(0, $i - 5); $j -lt $i; $j++) {
            $recentAvoid += $draws[$j].Numbers
        }
        
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $attempts = 0
            $ticket = $null
            while ($attempts -lt 500) {
                $attempts++
                $candidate = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
                
                # Avoid recent numbers
                $recentMatches = ($candidate | Where-Object { $recentAvoid -contains $_ }).Count
                if ($recentMatches -gt 2) { continue }
                
                $s = ($candidate | Measure-Object -Sum).Sum
                if ($s -lt $meanSum - 30 -or $s -gt $meanSum + 30) { continue }
                $decadeDist = @{}
                foreach ($n in $candidate) {
                    $d = [int][Math]::Floor($n / 10)
                    if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
                }
                if ($decadeDist.Values -contains 3) { continue }
                if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
                
                $ticket = $candidate
                break
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

# Strategy 5: Position-Based (favor numbers in certain positions)
function Test-PositionStrategy {
    param([PSCustomObject[]]$draws, [int]$ticketsPerDraw)
    # Pre-compute position frequencies
    $posFreq = @{}
    for ($p = 0; $p -lt 6; $p++) { $posFreq[$p] = @{} }
    foreach ($d in $draws) {
        $sorted = $d.Numbers | Sort-Object
        for ($p = 0; $p -lt 6; $p++) {
            $n = $sorted[$p]
            if ($posFreq[$p].ContainsKey($n)) { $posFreq[$p][$n]++ } else { $posFreq[$p][$n] = 1 }
        }
    }
    
    $meanSum = 276.37
    $results = @{ "3"=0; "4"=0; "5"=0; "6"=0; spent=0; won=0; drawsTested=$draws.Count }
    
    foreach ($draw in $draws) {
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $attempts = 0
            $ticket = $null
            while ($attempts -lt 500) {
                $attempts++
                $candidate = @()
                for ($p = 0; $p -lt 6; $p++) {
                    $freq = $posFreq[$p]
                    $sortedFreq = $freq.GetEnumerator() | Sort-Object Value -Descending
                    $topCandidates = $sortedFreq | Select-Object -First 15 | ForEach-Object { $_.Name }
                    $pick = Get-Random -InputObject $topCandidates
                    $candidate += $pick
                }
                $candidate = $candidate | Sort-Object -Unique
                if ($candidate.Count -ne 6) { continue }
                
                $s = ($candidate | Measure-Object -Sum).Sum
                if ($s -lt $meanSum - 30 -or $s -gt $meanSum + 30) { continue }
                $decadeDist = @{}
                foreach ($n in $candidate) {
                    $d = [int][Math]::Floor($n / 10)
                    if ($decadeDist.ContainsKey($d)) { $decadeDist[$d]++ } else { $decadeDist[$d] = 1 }
                }
                if ($decadeDist.Values -contains 3) { continue }
                if (($candidate | Where-Object { $_ -gt 80 }).Count -gt 1) { continue }
                
                $ticket = $candidate
                break
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

# Run all strategies
$ticketsPerDraw = 2
Write-Host "`n=== BACKTEST SUITE: 4226 DRAWS ===" -ForegroundColor Cyan
Write-Host "Strategies: Random, OriginalConstraints, HotCold, AntiRecent, PositionBased" -ForegroundColor White
Write-Host "Tickets per draw: $ticketsPerDraw" -ForegroundColor White
Write-Host "Total tickets per strategy: $($records.Count * $ticketsPerDraw)" -ForegroundColor White
Write-Host ""

# Test each strategy
$strategies = @{
    "Random" = { Test-RandomStrategy -draws $records -ticketsPerDraw $ticketsPerDraw }
    "OriginalConstraints" = { Test-OriginalConstraintsStrategy -draws $records -ticketsPerDraw $ticketsPerDraw }
    "HotColdOptimized" = { Test-HotColdStrategy -draws $records -ticketsPerDraw $ticketsPerDraw }
    "AntiRecent" = { Test-AntiRecentStrategy -draws $records -ticketsPerDraw $ticketsPerDraw }
    "PositionBased" = { Test-PositionStrategy -draws $records -ticketsPerDraw $ticketsPerDraw }
}

$allResults = @{}
foreach ($name in $strategies.Keys) {
    Write-Host "Testing $name..." -ForegroundColor Yellow
    $result = & $strategies[$name]
    $allResults[$name] = $result
    $m3 = $result.PSObject.Properties['3'].Value
$m4 = $result.PSObject.Properties['4'].Value
$m5 = $result.PSObject.Properties['5'].Value
$m6 = $result.PSObject.Properties['6'].Value
Write-Host "  ${name}: Net $($result.net) | M3: $m3 | M4: $m4 | M5: $m5 | M6: $m6" -ForegroundColor White
}

# Create summary report
$report = @{
    metadata = @{
        totalDraws = $records.Count
        ticketsPerDraw = $ticketsPerDraw
        totalTicketsPerStrategy = $records.Count * $ticketsPerDraw
        prizeStructure = $prizes
        dateRange = "$($records[0].Date) to $($records[-1].Date)"
    }
    strategies = @{}
}

foreach ($name in $allResults.Keys) {
    $r = $allResults[$name]
    $roi = if ($r.spent -gt 0) { [Math]::Round(($r.won / $r.spent) * 100, 2) } else { 0 }
    $report.strategies[$name] = @{
        drawsTested = $r.drawsTested
        totalTickets = $r.spent
        match3 = $r."3"
        match4 = $r."4"
        match5 = $r."5"
        match6 = $r."6"
        totalSpent = $r.spent
        totalWon = $r.won
        netResult = $r.net
        roiPercent = $roi
    }
}

# Find best strategy
$bestStrategy = ($allResults.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1).Name
$report.bestStrategy = $bestStrategy

$reportJson = $report | ConvertTo-Json -Depth 10
Set-Content -Path $outputPath -Value $reportJson -Encoding UTF8

Write-Host "`n=== BACKTEST COMPLETE ===" -ForegroundColor Cyan
Write-Host "Best strategy: $bestStrategy" -ForegroundColor Green
Write-Host "Report saved: $outputPath" -ForegroundColor Yellow

# Print summary table
WriteHost "`n=== SUMMARY TABLE ===" -ForegroundColor Cyan
foreach ($name in $allResults.Keys) {
    $r = $allResults[$name]
    $roi = if ($r.spent -gt 0) { [Math]::Round(($r.won / $r.spent) * 100, 2) } else { 0 }
    WriteHost ("{0,-20} {1,>10} {2,>8} {3,>8} {4,>8} {5,>8} {6,>10} {7,>8}" -f $name, $r.net, $r.'3', $r.'4', $r.'5', $r.'6', $r.spent, $roi)
}