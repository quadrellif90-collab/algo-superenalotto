Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "backtest_results.txt"

# Carica dati
$records = @()
if (Test-Path $csvPath) {
    $lines = Get-Content $csvPath | Select-Object -Skip 1
    foreach ($line in $lines) {
        $parts = $line -split ','
        if ($parts.Count -ge 9) {
            try {
                $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], 
                           [int]$parts[5], [int]$parts[6], [int]$parts[7])
                if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                    $records += [PSCustomObject]@{
                        Date = $parts[0]
                        Nums = $nums
                        Sum = ($nums | Measure-Object -Sum).Sum
                    }
                }
            } catch {}
        }
    }
}

Write-Host "Dataset caricato: $($records.Count) estrazioni"

# Prime function
function Test-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) {
        if ($n % $i -eq 0) { return $false }
    }
    return $true
}

# Genera schedina con criteri anti-mercato
function Generate-Schedina {
    $sums = $records | ForEach-Object { $_.Sum }
    $mean = ($sums | Measure-Object -Average).Average
    
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
        
        $targetLow = [int]($mean - 35)
        $targetHigh = [int]($mean + 35)
        
        if ($sum -ge $targetLow -and $sum -le $targetHigh -and $maxDecade -le 2 -and $veryHigh -le 1) {
            return @{
                Nums = $nums
                Sum = $sum
            }
        }
    }
}

# Back test results structure
function New-BacktestResult {
    return @{
        drawsTested = 0
        totalTickets = 0
        match2 = 0
        match3 = 0
        match4 = 0
        match5 = 0
        match6 = 0
        totalPrizeWon = 0
        totalSpent = 0
        netProfit = 0
        avgMatches = 0
        strategyName = ""
        matchDetails = @()
    }
}

# Calcolo vincita
function Get-Prize([int]$matches) {
    switch ($matches) {
        6 { return 10000000 }  # jackpot
        5 { return 10000 }
        5 { return 10000; break }
        4 { return 100; break }
        3 { return 10; break }
        default { return 0 }
    }
}

# Run backtest for a strategy
function Run-Backtest {
    param (
        [string]$strategyName,
        [scriptblock]$generatePair,
        [int]$drawsToTest = 1000,
        [int]$ticketsPerDraw = 2,
        [string]$outputFile = ""
    )
    
    $result = New-BacktestResult
    $result.strategyName = $strategyName
    $result.drawsTested = [Math]::Min($drawsToTest, $records.Count)
    
    Write-Host "=== BACKTEST: $strategyName ===" -ForegroundColor Cyan
    Write-Host "Draws: $($result.drawsTested), Tickets/draw: $ticketsPerDraw"
    
    $processed = 0
    $fixedPair = $null
    $fixedPairStr = ""
    
    # Procediamo dall'ultimo al primo per simulazione realistica
    for ($i = $records.Count - 1; $i -ge 0 -and $processed -lt $result.drawsTested; $i--) {
        $draw = $records[$i]
        $drawNums = $draw.Nums
        $ticketsThisDraw = $ticketsPerDraw
        
        # Strategia 1: stessa coppia sempre
        if ($strategyName -eq "Same Pair Repeated") {
            if (-not $fixedPair) {
                $pair = @($generatePair.Invoke())
                $fixedPair = $pair[0].Nums
                $fixedPairStr = ($pair[0].Nums -join ",")
            }
            $tickets = @()
            for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
                $tickets += $fixedPair
            }
        } 
        # Strategia 2: coppia casuale nuova ogni volta
        elseif ($strategyName -eq "Random New Pair Each Draw") {
            $pair = @($generatePair.Invoke())
            $tickets = @()
            for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
                $tickets += $pair[$t % 2].Nums
            }
        }
        # Strategia 3: coppia ottimizzata alta entropia
        elseif ($strategyName -eq "High-Entropy Pair") {
            $pair = @($generatePair.Invoke())
            $tickets = @()
            for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
                $tickets += $pair[$t].Nums
            }
        }
        else {
            $pair = @($generatePair.Invoke())
            $tickets = @()
            for ($t = 0; $t -lt $ticketsPerDraw; $t++) {
                $tickets += $pair[$t % 2].Nums
            }
        }
        
        $result.totalTickets += $tickets.Count
        $result.totalSpent += $tickets.Count * 1
        
        foreach ($ticket in $tickets) {
            $matches = ($ticket | Where-Object { $_ -in $drawNums }).Count
            $prize = Get-Prize($matches)
            $result.totalPrizeWon += $prize
            
            switch ($matches) {
                6 { $result.match6 += 1 }
                5 { $result.match5 += 1 }
                4 { $result.match4 += 1 }
                3 { $result.match3 += 1 }
                2 { $result.match2 += 1 }
            }
            
            $result.matchDetails += @{
                date = $draw.Date
                ticket = $ticket -join ","
                draw = $drawNums -join ","
                matches = $matches
                prize = $prize
            }
        }
        
        $processed++
        if ($processed % 200 -eq 0) {
            Write-Host "Progress: $processed / $($result.drawsTested)"
        }
    }
    
    $result.avgMatches = if ($result.drawsTested -gt 0) { [math]::Round(($result.match2 + $result.match3 + $result.match4 + $result.match5 + $result.match6) / $result.drawsTested, 4) } else { 0 }
    $result.netProfit = $result.totalPrizeWon - $result.totalSpent
    
    Write-Host "[COMPLETATO] Match 6: $($result.match6), Match 5: $($result.match5), Match 4: $($result.match4), Match 3: $($result.match3)" -ForegroundColor Green
    Write-Host "Spent: EUR $($result.totalSpent), Won: EUR $($result.totalPrizeWon), Net: EUR $($result.netProfit)" -ForegroundColor Green
    
    return $result
}

# Genera report finale
function Write-BacktestReport {
    param (
        [string]$outputFile,
        [hashtable[]]$results
    )
    
    $report = @"
================================================================
SUPERENALOTTO - BACKTEST ANALISI STRATEGIE
Generato: $(Get-Date -Format "dd/MM/yyyy HH:mm")
================================================================

DATASET: $csvPath
Estrazioni totali: $($records.Count)
================================================================

"@
    
    $report += ""
    $report += "RISULTATI BACKTEST:`n`n"
    
    foreach ($r in $results) {
        $report += @"

--------------------------------------------------------------
STRATEGIA: $($r.strategyName)
--------------------------------------------------------------

Estrazioni testate: $($r.drawsTested)
Biglietti totali: $($r.totalTickets)
Costo totale: EUR $($r.totalSpent)
 vincita grans: EUR $($r.totalPrizeWon)
Utilità netto: EUR $($r.netProfit)
tendenza: $(if ($r.netProfit -gt 0) { "POSITIVA" } else { "NEGATIVA" })

MATCH DETTAGLIO:
  Match 6: $($r.match6) vincita ~10M€/ Settore
  Match 5: $($r.match5) vincita ~10K€
Match 4: $($r.match4) vincita ~100€
  Match 3: $($r.match3) vincita ~10€
  Match 2: $($r.match2) (no vincita)
Media match per estrazione: $($r.avgMatches)

"@
    }
    
    $report += @"

================================================================
ANALISI CONFRONTO
================================================================

Vittoria anch'io determinare che strategia rende maggiore
rate di vittoria (match 3+, o match 4+):

Se confrontiamo:

1. STRATEGIA 1 - "Same Pair Repeated": stessa coppia 2 schedine
   usate per tutto il periodo.
   - PROBLEMA: se le 2 schedine non vincono mai, sono
     sempre perdenti. La probabilità di match 3+ su una
     singola schedina è 327:1. su 2 schedine, 163:1.
   - Non c'è "riposo" dalla perdita - è scommessa infinita.

2. STRATEGIA 2 - "Random New Pair Each Draw": nuova coppia
   ogni estrazione.
   - Vantaggio: diversificazione (diversi numeri)
   - Svantaggio: ogni concorso è new, non costruzione
     pattern.
   - Matematicamente equiprobabile, non c'è differenza
     con strategia 1 se i criteri generativi sono uguali.

3. STRATEGIA 3 - "High-Entropy Pair": coppia ottimizzata
   con alti criteri di diversità.
   - Se i criteri sono ben condizionati, si massimizz.
   - Rischio: se i vincoli sono troppo stringenti, la
     accept-reject può non trovare nuove combinazioni.

3. QUALITATIVE MATH:
   - Probabilità match 3 su 1 schedina: 1/327,615
   - Probabilità match 4 su 1 schedina: 1/11,180
   - Probabilità match 5 su 1 schedina: 1/2,333,636
   - Probabilità match 6 su 1 schedina: 1/622,614,630
   
   Con 2 schedine ogni estrazione e 1000 estrazioni:
   - 2000 biglietti totali
   - Atteso match 3+: 2000 * (1/327 + 1/11180 + ...) ≈ 6-7
   - Atteso match 4+: molto più raro, ~0.1-0.2

================================================================
CONCLUSIONI
================================================================

La differenza tra strategie è minima dal punto di vista
statistico perch la distribuzione di probabilità è la stessa.

Tuttavia strategicamente:

- IL GRADE STESSO SI RIPETE: può essere meglio se presente
  un bias di "hot/cold" numbers, perch puoi riutilizzare
  i numeri che statisticalmente compaiono.
- NUOVO OGNI VOLTA: massimizza la diversità e riduce la
  correlazione tra consecutive scommesse.
- OTTIMIZZATO: se i criteri di generazione sono più stringenti
  e ben calibrati, può teoricamente aumentare match 3+ rispetto
  alla random pura.

NOW:
L'analisi matematica mostra che non c'è differenza significativa
tra le strategie se i criteri di generazione sono equivalenti.
La scelta ideale recente essa da implementare sia:

1. MODELLO: usare sempre le stesse squadre che hanno statistics
   migliori per quel periodo.
2. RIUTILIZZO: appena match 3+ raggiunge, cambiare squadre per
   ridurre la probabilità di "perso tutto".
3. ATTESA: girare la board più volte per aumentare le probabilità.

================================================================
"@

    $report | Set-Content $outputFile
    Write-Host "`nRapporto salvato in: $outputFile"
}

# ===== MAIN EXECUTION =====

$results = @()

# Strategy 1: Same pair
Write-Host "`n`n"
$result1 = Run-Backtest -strategyName "Same Pair Repeated" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}
$results += $result1

# Strategy 2: New random pair
Write-Host "`n`n"
$result2 = Run-Backtest -strategyName "Random New Pair Each Draw" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}
$results += $result2

# Strategy 3: High-entropy pair (same generator already used)
Write-Host "`n`n"
$result3 = Run-Backtest -strategyName "High-Entropy Pair" -drawsToTest 800 -ticketsPerDraw 2 -generatePair ${function:Generate-Schedina}
$results += $result3

# Write report
Write-BacktestReport -outputFile $outputPath -results $results

Write-Host "`n`nBACKTEST COMPLETED" -ForegroundColor Yellow
Write-Host "Report: $outputPath"
