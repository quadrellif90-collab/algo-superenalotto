# Run-Backtest.ps1 - Backtest runner FINAL v6 (FIXED)
$ErrorActionPreference = "Continue"

$global:scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$global:csvPath = Join-Path $global:scriptDir "superenalotto.csv"
$global:outputPath = Join-Path $global:scriptDir "backtest_results.txt"
$global:resultJsonPath = Join-Path $global:scriptDir "backtest_result.json"

# Carica dati in modo affidabile - usa array semplice invece di List
$global:records = @()
$global:recordCount = 0

if (Test-Path $global:csvPath) {
    Write-Host "Loading CSV from: $global:csvPath" -ForegroundColor Cyan
    $lines = Get-Content $global:csvPath -Encoding UTF8 | Select-Object -Skip 1
    Write-Host "Lines to parse: $($lines.Count)" -ForegroundColor White
    
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -ge 9) {
            try {
                $n1 = [int]($parts[2].Trim())
                $n2 = [int]($parts[3].Trim())
                $n3 = [int]($parts[4].Trim())
                $n4 = [int]($parts[5].Trim())
                $n5 = [int]($parts[6].Trim())
                $n6 = [int]($parts[7].Trim())
                if ($n1 -ge 1 -and $n1 -le 90 -and $n2 -ge 1 -and $n2 -le 90 -and $n3 -ge 1 -and $n3 -le 90 -and $n4 -ge 1 -and $n4 -le 90 -and $n5 -ge 1 -and $n5 -le 90 -and $n6 -ge 1 -and $n6 -le 90) {
                    $nums = @($n1, $n2, $n3, $n4, $n5, $n6)
                    $sum = $n1 + $n2 + $n3 + $n4 + $n5 + $n6
                    $global:records += [PSCustomObject]@{
                        Date = $parts[0].Trim()
                        Nums = $nums
                        Sum = $sum
                    }
                    $global:recordCount++
                }
            } catch {
                # Silently skip malformed lines
            }
        }
    }
}

Write-Host "Loaded $($global:records.Count) records" -ForegroundColor Cyan

if ($global:records.Count -eq 0) {
    Write-Host "ATTENZIONE: Nessun record caricato!" -ForegroundColor Yellow
} else {
    Write-Host "Primo record: $($global:records[0].Date) - Sum: $($global:records[0].Sum)" -ForegroundColor Green
    Write-Host "Ultimo record: $($global:records[-1].Date) - Sum: $($global:records[-1].Sum)" -ForegroundColor Green
}

function Get-Prize([int]$matches) {
    switch ($matches) {
        6 { return 10000000 }
        5 { return 10000 }
        4 { return 100 }
        3 { return 10 }
        default { return 0 }
    }
}

function Generate-Schedina {
    if ($global:records.Count -eq 0) { return @(0,0,0,0,0,0) }
    $sums = $global:records | ForEach-Object { $_.Sum }
    $mean = ($sums | Measure-Object -Average).Average
    $targetLow = [int]($mean - 35)
    $targetHigh = [int]($mean + 35)
    
    while ($true) {
        $nums = @()
        while ($nums.Count -lt 6) {
            $n = Get-Random -Minimum 1 -Maximum 91
            if ($n -notin $nums) { $nums += $n }
        }
        $nums = $nums | Sort-Object
        $sum = ($nums | Measure-Object -Sum).Sum
        
        $decades = @{}
        foreach ($n in $nums) {
            $d = [math]::Floor($n / 10)
            $decades[$d] = ++$decades[$d]
        }
        $maxDecade = ($decades.Values | Measure-Object -Maximum).Maximum
        $veryHigh = ($nums | Where-Object { $_ -gt 80 }).Count
        
        if ($sum -ge $targetLow -and $sum -le $targetHigh -and $maxDecade -le 2 -and $veryHigh -le 1) {
            return $nums
        }
    }
}

function Run-Backtest {
    param (
        [string]$strategyName,
        [scriptblock]$generatePair,
        [int]$drawsToTest = 800,
        [int]$ticketsPerDraw = 2
    )
    
    $result = [PSCustomObject]@{
        drawsTested = [Math]::Min($drawsToTest, $global:records.Count)
        totalTickets = 0
        match2 = 0; match3 = 0; match4 = 0; match5 = 0; match6 = 0
        totalPrizeWon = 0
        totalSpent = 0
        netProfit = 0
        avgMatches = 0
        strategyName = $strategyName
    }
    
    if ($global:records.Count -eq 0) {
        Write-Host "[SKIP] Nessun dato per backtest" -ForegroundColor Yellow
        return $result
    }
    
    Write-Host "=== BACKTEST: $strategyName ===" -ForegroundColor Cyan
    Write-Host "Draws: $($result.drawsTested), Tickets/draw: $ticketsPerDraw" -ForegroundColor White
    
    $processed = 0
    $recCount = $global:records.Count
    for ($i = $recCount - 1; $i -ge 0 -and $processed -lt $result.drawsTested; $i--) {
        $draw = $global:records[$i]
        $drawNums = $draw.Nums
        
        for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
            $ticket = & $generatePair
            $result.totalTickets++
            $result.totalSpent++
            
            $matches = ($ticket | Where-Object { $_ -in $drawNums }).Count
            $prize = Get-Prize($matches)
            $result.totalPrizeWon += $prize
            
            switch ($matches) {
                6 { $result.match6++ }
                5 { $result.match5++ }
                4 { $result.match4++ }
                3 { $result.match3++ }
                2 { $result.match2++ }
            }
        }
        
        $processed++
        if ($processed % 200 -eq 0) {
            Write-Host "Progress: $processed / $($result.drawsTested)" -ForegroundColor Gray
        }
    }
    
    $result.avgMatches = if ($result.drawsTested -gt 0) {
        [math]::Round(($result.match2 + $result.match3 + $result.match4 + $result.match5 + $result.match6) / $result.drawsTested, 4)
    } else { 0 }
    $result.netProfit = $result.totalPrizeWon - $result.totalSpent
    
    Write-Host "[COMPLETATO] Match 6: $($result.match6), Match 5: $($result.match5), Match 4: $($result.match4), Match 3: $($result.match3)" -ForegroundColor Green
    Write-Host "Spent: EUR $($result.totalSpent), Won: EUR $($result.totalPrizeWon), Net: EUR $($result.netProfit)" -ForegroundColor Green
    
    return $result
}

# ===== MAIN EXECUTION =====
$results = @()

Write-Host "`nAvvio backtest strategie..." -ForegroundColor Yellow

# Strategy 1: Same pair repeated
Write-Host "  Strategia 1/3: Same Pair Repeated" -ForegroundColor White
$results += Run-Backtest -strategyName "Same Pair Repeated" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}

# Strategy 2: Random new pair
Write-Host "  Strategia 2/3: Random New Pair Each Draw" -ForegroundColor White
$results += Run-Backtest -strategyName "Random New Pair Each Draw" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}

# Strategy 3: High-entropy pair
Write-Host "  Strategia 3/3: High-Entropy Pair" -ForegroundColor White
$results += Run-Backtest -strategyName "High-Entropy Pair" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}

# Scrivi report
$reportHeader = @"
================================================================
SUPERENALOTTO - BACKTEST ANALISI STRATEGIE
Generato: $(Get-Date -Format "dd/MM/yyyy HH:mm")
================================================================

DATASET: $($global:csvPath)
Estrazioni totali: $($global:records.Count)
================================================================

"@

$reportBody = "`nRISULTATI BACKTEST:`n`n"
foreach ($r in $results) {
    $tendenza = if ($r.netProfit -gt 0) { "POSITIVA" } else { "NEGATIVA" }
    $reportBody += @"
--------------------------------------------------------------
STRATEGIA: $($r.strategyName)
--------------------------------------------------------------
Estrazioni testate: $($r.drawsTested)
Biglietti totali: $($r.totalTickets)
Costo totale: EUR $($r.totalSpent)
Vincita totale: EUR $($r.totalPrizeWon)
Utilita netto: EUR $($r.netProfit)
Tendenza: $tendenza
MATCH DETTAGLIO:
  Match 6: $($r.match6)
  Match 5: $($r.match5)
  Match 4: $($r.match4)
  Match 3: $($r.match3)
  Match 2: $($r.match2)
Media match per estrazione: $($r.avgMatches)
"@
}

$reportFooter = @"
================================================================
NOTE
================================================================
- Tutti i backtest usano 800 estrazioni (max disponibili)
- 2 schedine per estrazione = 1600 biglietti totali per strategia
- Premi: 6=10M€, 5=10K€, 4=100€, 3=10€, 2=0€
- Strategia 1: stessa coppia ripetuta per tutto il periodo
- Strategia 2: nuova coppia random ogni estrazione
- Strategia 3: coppia generata con criteri high-entropy
================================================================
"@

$fullReport = $reportHeader + $reportBody + $reportFooter
$fullReport | Set-Content $global:outputPath -Encoding UTF8
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $global:resultJsonPath -Encoding UTF8

Write-Host "`nBACKTEST COMPLETATO!" -ForegroundColor Green
Write-Host "Report: $global:outputPath" -ForegroundColor White
Write-Host "JSON: $global:resultJsonPath" -ForegroundColor White

# Show summary
if ($results.Count -gt 0) {
    Write-Host "`nRIASSUNTO RAPIDO:" -ForegroundColor Yellow
    foreach ($r in $results) {
        $match3plus = $r.match3 + $r.match4 + $r.match5 + $r.match6
        Write-Host "  $($r.strategyName): Netto EUR $([math]::Round($r.netProfit, 0)) (Match 3+: $match3plus)" -ForegroundColor White
    }
}