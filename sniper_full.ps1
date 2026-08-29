# sniper_full.ps1 - Protocollo Sniper Completo Automatico
# Esegue: update CSV, backtest, verifica vincite, generazione numeri, export

Add-Type -AssemblyName System.Windows.Forms

$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$trackingPath = Join-Path $scriptDir "tracking.csv"
$backtestResultPath = Join-Path $scriptDir "backtest_result.json"
$dailyLimitPath = Join-Path $scriptDir "daily_limit.csv"
$analisiJsonPath = Join-Path $scriptDir "analisi_completa.json"

$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=712"

$drawDays = @("Tuesday", "Thursday", "Friday", "Saturday")
$today = Get-Date -Format "yyyy-MM-dd"
$dayOfWeekName = (Get-Date).DayOfWeek.ToString()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUPERENALOTTO - PROTOCOLLO SNIPER v3" -ForegroundColor Cyan
Write-Host "  Data: $today ($dayOfWeekName)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) { if ($n % $i -eq 0) { return $false } }
    return $true
}

function Get-Stats {
    $lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
    $records = @()
    foreach ($line in $lines) {
        $parts = $line -split ','
        if ($parts.Count -ge 9) {
            try {
                $nums = @([int]($parts[2].Trim()), [int]($parts[3].Trim()), [int]($parts[4].Trim()),
                           [int]($parts[5].Trim()), [int]($parts[6].Trim()), [int]($parts[7].Trim()))
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
    return $records
}

function Save-AnalisiJson($records) {
    if ($records.Count -eq 0) { return }
    $sums = $records | ForEach-Object { $_.Sum }
    $allNums = $records | ForEach-Object { $_.Nums } | ForEach-Object { $_ }
    $sumsSorted = $sums | Sort-Object
    $n = $sumsSorted.Count
    $mean = ($sums | Measure-Object -Average).Average
    $median = $sumsSorted[[int]($n / 2)]
    $sumSq = 0
    foreach ($s in $sums) { $sumSq += [math]::Pow($s - $mean, 2) }
    $std = [math]::Sqrt($sumSq / $n)
    $primesPct = [math]::Round(($allNums | Where-Object { Test-Prime $_ }).Count / $allNums.Count * 100, 2)
    $extremesPct = [math]::Round(($allNums | Where-Object { $_ -ge 76 }).Count / $allNums.Count * 100, 2)
    $gt31Pct = [math]::Round(($allNums | Where-Object { $_ -gt 31 }).Count / $allNums.Count * 100, 2)
    $gt80Pct = [math]::Round(($allNums | Where-Object { $_ -gt 80 }).Count / $allNums.Count * 100, 2)
    $even = ($allNums | Where-Object { $_ % 2 -eq 0 }).Count
    $odd = ($allNums | Where-Object { $_ % 2 -ne 0 }).Count
    $evenPct = [math]::Round($even / $allNums.Count * 100, 2)
    $oddPct = [math]::Round($odd / $allNums.Count * 100, 2)
    $histogram = @{}
    foreach ($s in $sums) { $bucket = [math]::Floor($s / 20) * 20; $histogram[$bucket] = ++$histogram[$bucket] }
    $topSums = ($histogram.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 | ForEach-Object {
        @{bucket = $_.Key; count = $_.Value }
    })
    $obj = [PSCustomObject]@{
        recordCount = $records.Count
        firstDate = $records[0].Date
        lastDate = $records[-1].Date
        sumMean = [math]::Round($mean, 2)
        sumMedian = $median
        sumStd = [math]::Round($std, 2)
        sumMin = ($sums | Measure-Object -Minimum).Minimum
        sumMax = ($sums | Measure-Object -Maximum).Maximum
        q1 = $sumsSorted[[int]($n * 0.25)]
        q3 = $sumsSorted[[int]($n * 0.75)]
        primesPct = $primesPct
        extremesPct = $extremesPct
        gt31Pct = $gt31Pct
        gt80Pct = $gt80Pct
        evenPct = $evenPct
        oddPct = $oddPct
        topSumBuckets = $topSums
    }
    $obj | ConvertTo-Json -Depth 5 | Set-Content $analisiJsonPath -Encoding UTF8
}

function Update-CSVFromAPI {
    Write-Host "[1] Aggiornamento database da API..." -ForegroundColor Green
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 15 -ErrorAction Stop
        $newCount = 0
        $existingDates = @()
        if (Test-Path $csvPath) {
            $existingLines = Get-Content $csvPath -Encoding UTF8
            foreach ($l in $existingLines) {
                $p = $l -split ','
                if ($p.Count -ge 2) { $existingDates += $p[0] }
            }
        }
        foreach ($r in $response.results) {
            $date = $r.draw_date
            if ($date -in $existingDates) { continue }
            $balls = $r.balls
            $jolly = if ($r.ball_bonus) { $r.ball_bonus[0] } else { 0 }
            $star = if ($r.ball_bonus -and $r.ball_bonus.Count -gt 1) { $r.ball_bonus[1] } else { 0 }
            $line = "$date,,$([int]$balls[0]),$([int]$balls[1]),$([int]$balls[2]),$([int]$balls[3]),$([int]$balls[4]),$([int]$balls[5]),$jolly,$star"
            Add-Content -Path $csvPath -Value $line -Encoding UTF8
            $newCount++
        }
        if ($newCount -gt 0) {
            Write-Host "  -> Aggiunti $newCount estrazioni!" -ForegroundColor Yellow
        } else {
            Write-Host "  -> Database gia aggiornato." -ForegroundColor Gray
        }
    } catch {
        Write-Host "  -> API non raggiungibile: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  -> Uso database locale esistente." -ForegroundColor Gray
    }
}

function Run-Backtest($records) {
    Write-Host ""
    Write-Host "[2] Esecuzione Backtest..." -ForegroundColor Green
    if ($records.Count -eq 0) {
        Write-Host "  -> Nessun dato per il backtest." -ForegroundColor Red
        return
    }
    $sums = $records | ForEach-Object { $_.Sum }
    $mean = ($sums | Measure-Object -Average).Average
    $targetLow = [int]($mean - 30)
    $targetHigh = [int]($mean + 30)

    $results = @{
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
    }

    $testCount = [Math]::Min(500, $records.Count)
    for ($i = $records.Count - 1; $i -ge 0 -and $results.drawsTested -lt $testCount; $i--) {
        $draw = $records[$i]
        $results.totalSpent++
        $attempts = 0
        $valid = $false
        while (-not $valid -and $attempts -lt 500) {
            $nums = @()
            while ($nums.Count -lt 6) {
                $n = Get-Random -Minimum 1 -Maximum 91
                if ($n -notin $nums) { $nums += $n }
            }
            $nums = $nums | Sort-Object
            $sum = ($nums | Measure-Object -Sum).Sum
            $decades = @{}
            foreach ($nn in $nums) { $d = [math]::Floor($nn / 10); $decades[$d] = ++$decades[$d] }
            $maxDecade = ($decades.Values | Measure-Object -Maximum).Maximum
            $veryHigh = ($nums | Where-Object { $_ -gt 80 }).Count
            $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($veryHigh -le 1)
            $attempts++
        }
        if ($valid) {
            $matches = ($nums | Where-Object { $_ -in $draw.Nums }).Count
            switch ($matches) {
                2 { $results.match2++ }
                3 { $results.match3++; $results.totalPrizeWon += 10 }
                4 { $results.match4++; $results.totalPrizeWon += 100 }
                5 { $results.match5++; $results.totalPrizeWon += 10000 }
                6 { $results.match6++; $results.totalPrizeWon += 10000000 }
            }
        }
        $results.totalTickets++
        $results.drawsTested++
    }
    $results.netProfit = $results.totalPrizeWon - $results.totalSpent
    $results.avgMatches = if ($results.drawsTested -gt 0) { [math]::Round(($results.match2+$results.match3+$results.match4+$results.match5+$results.match6)/$results.drawsTested, 4) } else { 0 }

    Write-Host "  Estrazioni testate: $($results.drawsTested)" -ForegroundColor White
    Write-Host "  Biglietti: $($results.totalTickets)" -ForegroundColor White
    Write-Host "  Speso: EUR $($results.totalSpent) | Vinto: EUR $($results.totalPrizeWon)" -ForegroundColor White
    Write-Host "  Netto: EUR $($results.netProfit)" -ForegroundColor $(if ($results.netProfit -ge 0) { "Green" } else { "Red" })
    Write-Host "  Match2: $($results.match2) | Match3: $($results.match3) | Match4: $($results.match4) | Match5: $($results.match5) | Match6: $($results.match6)" -ForegroundColor White
    Write-Host "  Media match/estrazione: $($results.avgMatches)" -ForegroundColor Gray

    $results | ConvertTo-Json | Set-Content $backtestResultPath -Encoding UTF8
    Write-Host "  -> Risultati salvati in backtest_result.json" -ForegroundColor Gray
}

function Verify-Wins($records) {
    Write-Host ""
    Write-Host "[3] Verifica Vincite..." -ForegroundColor Green
    if (-not (Test-Path $trackingPath)) {
        Write-Host "  -> Nessun tracking trovato." -ForegroundColor Gray
        return
    }
    $tracking = Import-Csv -Path $trackingPath
    if ($tracking.Count -eq 0) {
        Write-Host "  -> Nessuna giocata registrata." -ForegroundColor Gray
        return
    }
    $lastDraw = $records[-1]
    Write-Host "  Ultima estrazione ($($lastDraw.Date)): $($lastDraw.Nums -join ', ')" -ForegroundColor White
    $unverified = $tracking | Where-Object { $_.verificato -ne "si" }
    $winCount = 0
    foreach ($t in $unverified) {
        $nums = ($t.numeri -replace '-', ' ').Trim() -split ' '
        $nums = $nums | Where-Object { $_ -ne "" } | ForEach-Object { [int]$_ }
        $matches = ($nums | Where-Object { $_ -in $lastDraw.Nums }).Count
        if ($matches -ge 3) {
            $winCount++
            Write-Host "  -> VINCITA! $($t.data): $matches numeri indovinati!" -ForegroundColor Yellow
        }
    }
    if ($winCount -eq 0) {
        Write-Host "  -> Nessuna vincita rilevata." -ForegroundColor Gray
    }
    $tracking | Export-Csv -Path $trackingPath -NoTypeInformation -Encoding UTF8
}

function Generate-Schedine($records, $numSchedine) {
    Write-Host ""
    Write-Host "[4] Generazione Numeri..." -ForegroundColor Green
    $sums = $records | ForEach-Object { $_.Sum }
    $mean = ($sums | Measure-Object -Average).Average
    $targetLow = [int]($mean - 30)
    $targetHigh = [int]($mean + 30)
    Write-Host "  Target somma: $targetLow - $targetHigh (media: $([math]::Round($mean, 0)))" -ForegroundColor White

    $generated = @()
    for ($s = 0; $s -lt $numSchedine; $s++) {
        $attempts = 0
        $valid = $false
        while (-not $valid -and $attempts -lt 1000) {
            $nums = @()
            while ($nums.Count -lt 6) {
                $n = Get-Random -Minimum 1 -Maximum 91
                if ($n -notin $nums) { $nums += $n }
            }
            $nums = $nums | Sort-Object
            $sum = ($nums | Measure-Object -Sum).Sum
            $decades = @{}
            foreach ($nn in $nums) { $d = [math]::Floor($nn / 10); $decades[$d] = ++$decades[$d] }
            $maxDecade = ($decades.Values | Measure-Object -Maximum).Maximum
            $veryHigh = ($nums | Where-Object { $_ -gt 80 }).Count
            $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($veryHigh -le 1)
            $attempts++
        }
        if ($valid) {
            $generated += [PSCustomObject]@{
                Numeri = $nums -join '-'
                Somma = $sum
            }
            Write-Host "  SCHEDINA $($s+1): $($nums -join '-') [somma: $sum]" -ForegroundColor Cyan
        }
    }
    return $generated
}

function Can-PlayToday {
    if (-not (Test-Path $dailyLimitPath)) { return $true }
    try {
        $limits = Import-Csv -Path $dailyLimitPath | Where-Object { $_.data -eq $today }
        if ($limits.Count -eq 0) { return $true }
        $played = [int]$limits[0].schedine_giocate
        return $played -lt 2
    } catch { return $true }
}

function Save-TrackingAndLimit($schedine, $jackpot) {
    Write-Host ""
    Write-Host "[5] Salvataggio Tracking..." -ForegroundColor Green
    if ($schedine.Count -eq 0) {
        Write-Host "  -> Nessuna schedina da salvare." -ForegroundColor Gray
        return
    }
    if (-not (Test-Path $trackingPath)) {
        "data,giornata,budget_speso,schede,numeri,somma,jackpot,verificato" | Out-File -FilePath $trackingPath -Encoding UTF8
    }
    foreach ($s in $schedine) {
        $line = "$today,$dayOfWeekName,$($schedine.Count).00,1,$($s.Numeri),$($s.Somma),$jackpot,no"
        Add-Content -Path $trackingPath -Value $line -Encoding UTF8
    }
    Write-Host "  -> $($schedine.Count) schedina/e salvata/e in tracking.csv" -ForegroundColor Gray

    $played = 0
    if (Test-Path $dailyLimitPath) {
        $existing = Import-Csv -Path $dailyLimitPath | Where-Object { $_.data -eq $today }
        if ($existing.Count -gt 0) {
            $played = [int]$existing[0].schedine_giocate
        }
    }
    if ($played -lt 2) {
        $played++
        $entry = [PSCustomObject]@{ data = $today; schedine_giocate = $played }
        if (-not (Test-Path $dailyLimitPath)) {
            "data,schedine_giocate" | Out-File -FilePath $dailyLimitPath -Encoding UTF8
        }
        $existingAll = @()
        if (Test-Path $dailyLimitPath) {
            $existingAll = @(Import-Csv -Path $dailyLimitPath | Where-Object { $_.data -ne $today })
        }
        $existingAll += $entry
        $existingAll | Export-Csv -Path $dailyLimitPath -NoTypeInformation -Encoding UTF8
        Write-Host "  -> Limite giornaliero: $played/2" -ForegroundColor Gray
    }
}

function Export-WeeklyReport($records) {
    Write-Host ""
    Write-Host "[6] Report Settimanale..." -ForegroundColor Green
    if (-not (Test-Path $trackingPath)) {
        Write-Host "  -> Nessun tracking." -ForegroundColor Gray
        return
    }
    $tracking = Import-Csv -Path $trackingPath
    $weekAgo = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
    $weekTracking = $tracking | Where-Object { $_.data -ge $weekAgo }
    if ($weekTracking.Count -eq 0) {
        Write-Host "  -> Nessuna giocata questa settimana." -ForegroundColor Gray
        return
    }
    $speso = ($weekTracking | Measure-Object { [double]$_.budget_speso } -Sum).Sum
    $vinte = ($weekTracking | Where-Object { $_.verificato -eq "si" } | Measure-Object { [double]$_.budget_speso } -Sum).Sum
    Write-Host "  Settimana: $($weekAgo) - $today" -ForegroundColor White
    Write-Host "  Giocate: $($weekTracking.Count) | Speso: EUR $speso" -ForegroundColor White
    Write-Host "  Vincite: EUR $vinte | Netto: EUR $($vinte - $speso)" -ForegroundColor White

    $reportPath = Join-Path $scriptDir "report_settimanale_$(Get-Date -Format 'yyyyMMdd').txt"
    $report = @"
========================================
SUPERENALOTTO - REPORT SETTIMANALE
========================================
Generato: $(Get-Date -Format "dd/MM/yyyy HH:mm")
Periodo: $weekAgo - $today
----------------------------------------
DATI STORICI
Estrazioni totali: $($records.Count)
Periodo dati: $($records[0].Date) - $($records[-1].Date)

STATISTICHE ATTUALI
Media somme: $([math]::Round(($records | ForEach-Object { $_.Sum } | Measure-Object -Average).Average, 2))
Mediana: $(($records | ForEach-Object { $_.Sum } | Sort-Object)[[int]($records.Count/2)])
Deviazione std: $([math]::Round([math]::Sqrt((($records | ForEach-Object { $_.Sum } | ForEach-Object { [math]::Pow($_ - (($records | ForEach-Object { $_.Sum } | Measure-Object -Average).Average), 2) } | Measure-Object -Sum).Sum / $records.Count)), 2))

TRACKING SETTIMANALE
Giocate: $($weekTracking.Count)
Speso: EUR $speso
Vincite: EUR $vinte
Netto: EUR $($vinte - $speso)
----------------------------------------
ULTIME ESTRAZIONI
"@
    foreach ($r in ($records | Select-Object -Last 5)) {
        $report += "`n$($r.Date): $($r.Nums -join ' ')"
    }
    $report += @"

========================================
"@
    $report | Out-File -FilePath $reportPath -Encoding UTF8
    Write-Host "  -> Report salvato: $reportPath" -ForegroundColor Gray
}

$records = Get-Stats
Write-Host "  Record caricati: $($records.Count)" -ForegroundColor Gray
Update-CSVFromAPI
$records = Get-Stats
Write-Host "  Record dopo update: $($records.Count)" -ForegroundColor Gray
Save-AnalisiJson($records)
Run-Backtest($records)
Verify-Wins($records)

if ($dayOfWeekName -in $drawDays) {
    if (Can-PlayToday) {
        $jackpot = 0
        try {
            $headers = @{ "X-API-KEY" = $apiKey }
            $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 10 -ErrorAction Stop
            $jackpot = $response.results[0].jackpot
        } catch {}
        $numSchedine = 2
        if ($jackpot -ge 100000000) {
            Write-Host "  [TRIGGER] Jackpot >= 100M - Giocata massima!" -ForegroundColor Magenta
        }
        $schedine = Generate-Schedine $records $numSchedine
        Save-TrackingAndLimit $schedine $jackpot
        Export-WeeklyReport($records)
    } else {
        Write-Host ""
        Write-Host "[4] LIMITE GIORNALIERO RAGGIUNTO" -ForegroundColor Yellow
        Write-Host "  -> Hai gia giocato 2 schedine oggi." -ForegroundColor Yellow
        Write-Host "  -> Riprova domani o alla prossima estrazione." -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "  Oggi ($dayOfWeekName) non e giorno di estrazione." -ForegroundColor Yellow
    Write-Host "  Giorni di estrazione: Mar, Gio, Ven, Sab" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Protocollo completato - $today" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""