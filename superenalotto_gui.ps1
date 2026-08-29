# superenalotto_gui.ps1 - SuperEnalotto GUI Completa v4
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$trackingPath = Join-Path $scriptDir "tracking.csv"
$dailyLimitPath = Join-Path $scriptDir "daily_limit.csv"
$analisiJsonPath = Join-Path $scriptDir "analisi_completa.json"

$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=712"

$script:records = @()
$script:stats = $null
$script:generatedNumbers = @()
$script:jackpot = 0
$script:lastDrawDate = ""

function Is-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) {
        if ($n % $i -eq 0) { return $false }
    }
    return $true
}

function Get-Decade($n) {
    return [math]::Floor(($n - 1) / 10)
}

function Parse-CSV {
    if (-not (Test-Path $csvPath)) { return @() }
    $lines = Get-Content $csvPath -Encoding UTF8
    $records = @()
    for ($i = 1; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -lt 9) { continue }
        $nums = @()
        $valid = $true
        for ($j = 2; $j -le 7; $j++) {
            $valStr = $parts[$j].Trim()
            if ([string]::IsNullOrWhiteSpace($valStr)) { $valid = $false; break }
            $val = 0
            if ([int]::TryParse($valStr, [ref]$val)) {
                if ($val -lt 1 -or $val -gt 90) { $valid = $false; break }
                $nums += $val
            } else { $valid = $false; break }
        }
        if (-not $valid -or $nums.Count -ne 6) { continue }
        $jolly = 0; $star = 0
        $jollyStr = $parts[8].Trim()
        if (-not [string]::IsNullOrWhiteSpace($jollyStr)) { [void][int]::TryParse($jollyStr, [ref]$jolly) }
        if ($parts.Count -gt 9) {
            $starStr = $parts[9].Trim()
            if (-not [string]::IsNullOrWhiteSpace($starStr)) { [void][int]::TryParse($starStr, [ref]$star) }
        }
        $records += [PSCustomObject]@{
            Date = $parts[0].Trim()
            Nums = ($nums | Sort-Object)
            Sum = ($nums | Measure-Object -Sum).Sum
            Jolly = $jolly
            Star = $star
        }
    }
    return $records
}

function Calculate-Stats {
    if ($script:records.Count -eq 0) {
        $script:stats = @{ Count = 0; Mean = 276.64; Median = 0; StdDev = 0; Q1 = 0; Q3 = 0; SumMin = 0; SumMax = 0; PrimesPct = 0; ExtremesPct = 0; Gt31Pct = 0; Gt80Pct = 0; EvenPct = 0; OddPct = 0; Top20Numbers = @(); FirstDate = ""; LastDate = "" }
        return
    }
    $sums = $script:records | ForEach-Object { $_.Sum }
    $allNums = $script:records | ForEach-Object { $_.Nums } | ForEach-Object { $_ }
    $sumsSorted = $sums | Sort-Object
    $n = $sumsSorted.Count
    $mean = ($sums | Measure-Object -Average).Average
    $median = $sumsSorted[[int]($n / 2)]
    $sumSq = 0
    foreach ($s in $sums) { $sumSq += [math]::Pow($s - $mean, 2) }
    $stdDev = [math]::Sqrt($sumSq / $n)
    $q1 = $sumsSorted[[int]($n * 0.25)]
    $q3 = $sumsSorted[[int]($n * 0.75)]
    $primesCount = 0; $extremesCount = 0; $gt31Count = 0; $gt80Count = 0; $evenCount = 0
    foreach ($num in $allNums) {
        if (Is-Prime $num) { $primesCount++ }
        if ($num -ge 76) { $extremesCount++ }
        if ($num -gt 31) { $gt31Count++ }
        if ($num -gt 80) { $gt80Count++ }
        if ($num % 2 -eq 0) { $evenCount++ }
    }
    $oddCount = $allNums.Count - $evenCount
    $freqMap = @{}
    for ($i = 1; $i -le 90; $i++) { $freqMap[$i] = 0 }
    foreach ($num in $allNums) { $freqMap[$num]++ }
    $top20 = ($freqMap.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20 | ForEach-Object { @{Number = $_.Key; Frequency = $_.Value} })
    $script:stats = @{
        Count = $n; Mean = [math]::Round($mean, 2); Median = $median; StdDev = [math]::Round($stdDev, 2)
        Q1 = $q1; Q3 = $q3; SumMin = ($sums | Measure-Object -Minimum).Minimum; SumMax = ($sums | Measure-Object -Maximum).Maximum
        PrimesPct = [math]::Round($primesCount / $allNums.Count * 100, 2)
        ExtremesPct = [math]::Round($extremesCount / $allNums.Count * 100, 2)
        Gt31Pct = [math]::Round($gt31Count / $allNums.Count * 100, 2)
        Gt80Pct = [math]::Round($gt80Count / $allNums.Count * 100, 2)
        EvenPct = [math]::Round($evenCount / $allNums.Count * 100, 2)
        OddPct = [math]::Round($oddCount / $allNums.Count * 100, 2)
        Top20Numbers = $top20; FirstDate = $script:records[0].Date; LastDate = $script:records[-1].Date
    }
    $jsonObj = [PSCustomObject]@{
        recordCount = $n; firstDate = $script:records[0].Date; lastDate = $script:records[-1].Date
        sumMean = [math]::Round($mean, 2); sumMedian = $median; sumStd = [math]::Round($stdDev, 2)
        sumMin = ($sums | Measure-Object -Minimum).Minimum; sumMax = ($sums | Measure-Object -Maximum).Maximum
        q1 = $q1; q3 = $q3
        primesPct = [math]::Round($primesCount / $allNums.Count * 100, 2)
        extremesPct = [math]::Round($extremesCount / $allNums.Count * 100, 2)
        evenPct = [math]::Round($evenCount / $allNums.Count * 100, 2)
        oddPct = [math]::Round($oddCount / $allNums.Count * 100, 2)
        top20Numbers = $top20
    }
    $jsonObj | ConvertTo-Json -Depth 5 | Set-Content $analisiJsonPath -Encoding UTF8
}

function Load-Data {
    $script:records = Parse-CSV
    Calculate-Stats
    if ($script:records.Count -gt 0) { $script:lastDrawDate = $script:records[-1].Date }
    Update-StatsUI
    Update-ResultsUI
    Update-PlayStatus
}

function Can-PlayToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not (Test-Path $dailyLimitPath)) { return $true }
    $lines = Get-Content $dailyLimitPath -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -ge 2 -and $parts[0] -eq $today) {
            $played = 0
            if ([int]::TryParse($parts[1], [ref]$played)) { return $played -lt 2 }
        }
    }
    return $true
}

function Get-PlayCountToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not (Test-Path $dailyLimitPath)) { return 0 }
    $lines = Get-Content $dailyLimitPath -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -ge 2 -and $parts[0] -eq $today) {
            $played = 0
            if ([int]::TryParse($parts[1], [ref]$played)) { return $played }
        }
    }
    return 0
}

function Increment-PlayCount {
    $today = Get-Date -Format "yyyy-MM-dd"
    $lines = @()
    if (Test-Path $dailyLimitPath) { $lines = @(Get-Content $dailyLimitPath -Encoding UTF8) }
    $found = $false
    $newLines = @()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts[0] -eq $today) {
            $count = 1
            if ($parts.Count -ge 2) { [void][int]::TryParse($parts[1], [ref]$count); $count++ }
            $newLines += "$today,$count"
            $found = $true
        } else { $newLines += $line }
    }
    if (-not $found) { $newLines += "$today,1" }
    $newLines | Out-File -FilePath $dailyLimitPath -Encoding UTF8
}

function Generate-Numbers {
    if (-not (Can-PlayToday)) {
        [System.Windows.Forms.MessageBox]::Show("Hai raggiunto il limite massimo di 2 schedine per oggi.", "Limite Giornaliero", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Carica prima i dati! Clicca 'AGGIORNA CSV'.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    $meanValue = 276.64
    if ($script:stats -ne $null -and $script:stats.Mean -gt 0) { $meanValue = $script:stats.Mean }
    $targetLow = [int]($meanValue - 30)
    $targetHigh = [int]($meanValue + 30)
    $script:generatedNumbers = @()
    for ($s = 0; $s -lt 2; $s++) {
        $attempts = 0; $valid = $false; $bestNums = $null
        while (-not $valid -and $attempts -lt 2000) {
            $nums = @()
            while ($nums.Count -lt 6) {
                $n = Get-Random -Minimum 1 -Maximum 91
                if ($n -notin $nums) { $nums += $n }
            }
            $nums = $nums | Sort-Object
            $sum = ($nums | Measure-Object -Sum).Sum
            $decadeCounts = @{}
            for ($d = 0; $d -lt 9; $d++) { $decadeCounts[$d] = 0 }
            foreach ($n in $nums) {
                $d = Get-Decade $n
                if ($d -lt 9) { $decadeCounts[$d]++ }
            }
            $maxDecade = ($decadeCounts.Values | Measure-Object -Maximum).Maximum
            $gt80 = ($nums | Where-Object { $_ -gt 80 }).Count
            $le31 = ($nums | Where-Object { $_ -le 31 }).Count
            $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($gt80 -le 1) -and ($le31 -ge 1)
            if ($valid) { $bestNums = $nums }
            $attempts++
        }
        if ($valid -and $bestNums -ne $null) {
            $sum = ($bestNums | Measure-Object -Sum).Sum
            $evenCount = ($bestNums | Where-Object { $_ % 2 -eq 0 }).Count
            $script:generatedNumbers += [PSCustomObject]@{
                Nums = $bestNums; Sum = $sum; EvenCount = $evenCount; OddCount = 6 - $evenCount; DecadeDist = $decadeCounts
            }
        }
    }
    if ($script:generatedNumbers.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Impossibile generare numeri validi. Riprova.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    Display-Generated
    Save-Tracking
    Increment-PlayCount
    Update-PlayStatus
    $script:statusLabel.Text = "Generati $($script:generatedNumbers.Count) schedine! (Totale oggi: $(Get-PlayCountToday))"
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
}

function Display-Generated {
    if ($script:generatedNumbers.Count -eq 0) { return }
    $text = ""
    for ($i = 0; $i -lt $script:generatedNumbers.Count; $i++) {
        $sched = $script:generatedNumbers[$i]
        $numsStr = ($sched.Nums -join " - ")
        $text += "SCHEDINA $($i + 1): $numsStr" + [Environment]::NewLine
        $text += "  Somma: $($sched.Sum) | Pari: $($sched.EvenCount) | Dispari: $($sched.OddCount)" + [Environment]::NewLine
        $text += [Environment]::NewLine
    }
    $script:txtNumeri.Text = $text
}

function Save-Tracking {
    if ($script:generatedNumbers.Count -eq 0) { return }
    $today = Get-Date -Format "yyyy-MM-dd"
    $dayName = (Get-Date).DayOfWeek.ToString()
    $header = "data,giornata,budget,schedine,numeri,somma,jackpot,verificato"
    if (-not (Test-Path $trackingPath)) { $header | Out-File -Path $trackingPath -Encoding UTF8 }
    foreach ($sched in $script:generatedNumbers) {
        $numsStr = $sched.Nums -join "-"
        $line = "$today,$dayName,1.00,1,$numsStr,$($sched.Sum),$script:jackpot,no"
        Add-Content -Path $trackingPath -Value $line -Encoding UTF8
    }
}

function Verify-Wins {
    if (-not (Test-Path $trackingPath)) {
        [System.Windows.Forms.MessageBox]::Show("Nessuna giocata registrata in tracking.csv", "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Carica prima i dati delle estrazioni!", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    $lastDraw = $script:records[-1]
    $lines = Get-Content $trackingPath -Encoding UTF8
    $results = @(); $updatedLines = @(); $updated = $false
    $header = $lines[0]; $updatedLines += $header
    for ($i = 1; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -lt 8) { $updatedLines += $line; continue }
        $verificato = $parts[7].Trim()
        if ($verificato -eq "si") { $updatedLines += $line; continue }
        $numsStr = $parts[4]
        $playedNums = @()
        foreach ($n in ($numsStr -split '-')) {
            $val = 0
            if ([int]::TryParse($n.Trim(), [ref]$val)) { $playedNums += $val }
        }
        $matches = 0
        foreach ($n in $playedNums) { if ($n -in $lastDraw.Nums) { $matches++ } }
        $prize = 0
        switch ($matches) {
            2 { $prize = 5 }
            3 { $prize = 25 }
            4 { $prize = 300 }
            5 { $prize = 10000 }
            6 { $prize = 2000000000 }
        }
        $results += "Data: $($parts[0]) | Numeri: $numsStr | Match: $matches | Premio: EUR $prize"
        $parts[7] = "si"
        $updatedLines += ($parts -join ',')
        $updated = $true
    }
    if ($updated) { $updatedLines | Out-File -FilePath $trackingPath -Encoding UTF8 }
    if ($results.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Nessuna giocata da verificare con l'ultima estrazione." + [Environment]::NewLine + "Ultima estrazione: $($lastDraw.Date)" + [Environment]::NewLine + "Numeri: $($lastDraw.Nums -join ' - ')", "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    } else {
        $msg = "ULTIMA ESTRAZIONE: $($lastDraw.Date)" + [Environment]::NewLine
        $msg += "Numeri: $($lastDraw.Nums -join ' - ')" + [Environment]::NewLine + [Environment]::NewLine
        $msg += "RISULTATI VERIFICA:" + [Environment]::NewLine + [Environment]::NewLine
        $msg += $results -join [Environment]::NewLine
        [System.Windows.Forms.MessageBox]::Show($msg, "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    }
}

function Export-Tracking {
    if (-not (Test-Path $trackingPath)) {
        [System.Windows.Forms.MessageBox]::Show("Nessun file di tracking da esportare.", "Esporta Tracking", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    $saveDialog = New-Object System.Windows.Forms.SaveFileDialog
    $saveDialog.Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
    $saveDialog.FileName = "superenalotto_tracking_$(Get-Date -Format 'yyyyMMdd').csv"
    $saveDialog.Title = "Esporta Tracking"
    if ($saveDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        Copy-Item -Path $trackingPath -Destination $saveDialog.FileName -Force
        [System.Windows.Forms.MessageBox]::Show("Tracking esportato in: $($saveDialog.FileName)", "Esporta Tracking", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    }
}

function Update-CSV {
    $script:statusLabel.Text = "Tentativo aggiornamento API..."
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
    $script:form.Refresh()
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 15 -ErrorAction Stop
        $newCount = 0
        $existingDates = @()
        if (Test-Path $csvPath) {
            $existingLines = Get-Content $csvPath -Encoding UTF8
            foreach ($l in $existingLines) {
                if ([string]::IsNullOrWhiteSpace($l)) { continue }
                $p = $l -split ','
                if ($p.Count -ge 2) { $existingDates += $p[0].Trim() }
            }
        }
        foreach ($r in $response.results) {
            $date = $r.draw_date
            if ($date -in $existingDates) { continue }
            $balls = $r.balls
            $jolly = 0; $star = 0
            if ($r.ball_bonus) {
                if ($r.ball_bonus.Count -gt 0) { $jolly = [int]$r.ball_bonus[0] }
                if ($r.ball_bonus.Count -gt 1) { $star = [int]$r.ball_bonus[1] }
            }
            $line = "$date,,$([int]$balls[0]),$([int]$balls[1]),$([int]$balls[2]),$([int]$balls[3]),$([int]$balls[4]),$([int]$balls[5]),$jolly,$star"
            Add-Content -Path $csvPath -Value $line -Encoding UTF8
            $newCount++
        }
        if ($newCount -gt 0) {
            $script:statusLabel.Text = "OK! Aggiunti $newCount estrazioni da API!"
            $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
            Load-Data
        } else {
            $script:statusLabel.Text = "API OK. Dati gia aggiornati."
            $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
            Load-Data
        }
    } catch {
        $script:statusLabel.Text = "API non raggiungibile. Uso CSV locale."
        $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 68, 68)
        Load-Data
        [System.Windows.Forms.MessageBox]::Show("API non raggiungibile." + [Environment]::NewLine + "I dati sono stati caricati dal CSV locale." + [Environment]::NewLine + "Ultima estrazione: $script:lastDrawDate", "Aggiornamento API", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
    }
}

function Get-Jackpot {
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        if ($response.results -and $response.results.Count -gt 0) {
            $jpRaw = $response.results[0].jackpot
            $jp = [double]$jpRaw
            $script:jackpot = if ($jp -gt 1000000) { [math]::Round($jp / 1000000, 1) } else { 0 }
            if ($script:jackpot -gt 0) { $script:jackpotLabel.Text = "Jackpot: EUR $script:jackpot M" }
            else { $script:jackpotLabel.Text = "Jackpot: N/D" }
        }
    } catch {
        $script:jackpot = 0
        $script:jackpotLabel.Text = "Jackpot: N/D"
    }
}

function Update-StatsUI {
    if ($script:stats -eq $null) {
        $script:lblTotEstrazioni.Text = "Estrazioni: 0"
        $script:lblMedia.Text = "Media: N/D"
        return
    }
    $script:lblTotEstrazioni.Text = "Estrazioni: $($script:stats.Count)"
    $script:lblMedia.Text = "Media: $($script:stats.Mean)"
    $script:lblMediana.Text = "Mediana: $($script:stats.Median)"
    $script:lblStdDev.Text = "Std Dev: $($script:stats.StdDev)"
    $script:lblQ1Q3.Text = "Q1: $($script:stats.Q1) | Q3: $($script:stats.Q3)"
    $script:lblSommaRange.Text = "Range: $($script:stats.SumMin) - $($script:stats.SumMax)"
    $script:lblPrimes.Text = "Primi: $($script:stats.PrimesPct)%"
    $script:lblExtremes.Text = "Estremi: $($script:stats.ExtremesPct)%"
    $script:lblGt80.Text = ">80: $($script:stats.Gt80Pct)%"
    $script:lblEvenOdd.Text = "Pari: $($script:stats.EvenPct)% | Dispari: $($script:stats.OddPct)%"
    if ($script:stats.FirstDate -and $script:stats.LastDate) {
        $script:lblDateRange.Text = "Periodo: $($script:stats.FirstDate) - $($script:stats.LastDate)"
    }
    $topText = "TOP 10 NUMERI:" + [Environment]::NewLine
    for ($i = 0; $i -lt [Math]::Min(10, $script:stats.Top20Numbers.Count); $i++) {
        $item = $script:stats.Top20Numbers[$i]
        $topText += "$($i + 1). Numero $($item.Number) (freq: $($item.Frequency))" + [Environment]::NewLine
    }
    $script:lblTop10.Text = $topText
}

function Update-ResultsUI {
    $script:dataGrid.Rows.Clear()
    $count = 0
    for ($i = $script:records.Count - 1; $i -ge 0 -and $count -lt 15; $i--) {
        $rec = $script:records[$i]
        $numsStr = ($rec.Nums -join " - ")
        $jollyStr = if ($rec.Jolly -gt 0) { $rec.Jolly.ToString() } else { "-" }
        $starStr = if ($rec.Star -gt 0) { $rec.Star.ToString() } else { "-" }
        $bgColor = if ($count % 2 -eq 0) { [System.Drawing.Color]::FromArgb(30, 30, 60) } else { [System.Drawing.Color]::FromArgb(45, 45, 75) }
        $script:dataGrid.Rows.Add($rec.Date, $numsStr, $jollyStr, $starStr, $rec.Sum)
        $script:dataGrid.Rows[$count].DefaultCellStyle.BackColor = $bgColor
        $script:dataGrid.Rows[$count].DefaultCellStyle.ForeColor = [System.Drawing.Color]::White
        $count++
    }
}

function Update-PlayStatus {
    $played = Get-PlayCountToday
    $remaining = 2 - $played
    if ($remaining -gt 0) {
        $script:lblPlayStatus.Text = "Schedine oggi: $played / 2 (restano: $remaining)"
        $script:lblPlayStatus.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
    } else {
        $script:lblPlayStatus.Text = "LIMITE RAGGIUNTO (2/2 oggi)"
        $script:lblPlayStatus.ForeColor = [System.Drawing.Color]::FromArgb(255, 68, 68)
    }
    $today = (Get-Date).DayOfWeek.ToString()
    $nextDraw = "Martedi"
    switch ($today) {
        "Monday" { $nextDraw = "Martedi" }
        "Tuesday" { $nextDraw = "Giovedi" }
        "Wednesday" { $nextDraw = "Giovedi" }
        "Thursday" { $nextDraw = "Venerdi" }
        "Friday" { $nextDraw = "Sabato" }
        "Saturday" { $nextDraw = "Martedi" }
        "Sunday" { $nextDraw = "Martedi" }
    }
    $script:lblNextDraw.Text = "Prossima estrazione: $nextDraw"
}
# superenalotto_gui.ps1 - SuperEnalotto GUI Completa v4
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$trackingPath = Join-Path $scriptDir "tracking.csv"
$dailyLimitPath = Join-Path $scriptDir "daily_limit.csv"
$analisiJsonPath = Join-Path $scriptDir "analisi_completa.json"

$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=712"

$script:records = @()
$script:stats = $null
$script:generatedNumbers = @()
$script:jackpot = 0
$script:lastDrawDate = ""

function Is-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) {
        if ($n % $i -eq 0) { return $false }
    }
    return $true
}

function Get-Decade($n) {
    return [math]::Floor(($n - 1) / 10)
}

function Parse-CSV {
    if (-not (Test-Path $csvPath)) { return @() }
    $lines = Get-Content $csvPath -Encoding UTF8
    $records = @()
    for ($i = 1; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -lt 9) { continue }
        $nums = @()
        $valid = $true
        for ($j = 2; $j -le 7; $j++) {
            $valStr = $parts[$j].Trim()
            if ([string]::IsNullOrWhiteSpace($valStr)) { $valid = $false; break }
            $val = 0
            if ([int]::TryParse($valStr, [ref]$val)) {
                if ($val -lt 1 -or $val -gt 90) { $valid = $false; break }
                $nums += $val
            } else { $valid = $false; break }
        }
        if (-not $valid -or $nums.Count -ne 6) { continue }
        $jolly = 0; $star = 0
        $jollyStr = $parts[8].Trim()
        if (-not [string]::IsNullOrWhiteSpace($jollyStr)) { [void][int]::TryParse($jollyStr, [ref]$jolly) }
        if ($parts.Count -gt 9) {
            $starStr = $parts[9].Trim()
            if (-not [string]::IsNullOrWhiteSpace($starStr)) { [void][int]::TryParse($starStr, [ref]$star) }
        }
        $records += [PSCustomObject]@{
            Date = $parts[0].Trim()
            Nums = ($nums | Sort-Object)
            Sum = ($nums | Measure-Object -Sum).Sum
            Jolly = $jolly
            Star = $star
        }
    }
    return $records
}

function Calculate-Stats {
    if ($script:records.Count -eq 0) {
        $script:stats = @{ Count = 0; Mean = 276.64; Median = 0; StdDev = 0; Q1 = 0; Q3 = 0; SumMin = 0; SumMax = 0; PrimesPct = 0; ExtremesPct = 0; Gt31Pct = 0; Gt80Pct = 0; EvenPct = 0; OddPct = 0; Top20Numbers = @(); FirstDate = ""; LastDate = "" }
        return
    }
    $sums = $script:records | ForEach-Object { $_.Sum }
    $allNums = $script:records | ForEach-Object { $_.Nums } | ForEach-Object { $_ }
    $sumsSorted = $sums | Sort-Object
    $n = $sumsSorted.Count
    $mean = ($sums | Measure-Object -Average).Average
    $median = $sumsSorted[[int]($n / 2)]
    $sumSq = 0
    foreach ($s in $sums) { $sumSq += [math]::Pow($s - $mean, 2) }
    $stdDev = [math]::Sqrt($sumSq / $n)
    $q1 = $sumsSorted[[int]($n * 0.25)]
    $q3 = $sumsSorted[[int]($n * 0.75)]
    $primesCount = 0; $extremesCount = 0; $gt31Count = 0; $gt80Count = 0; $evenCount = 0
    foreach ($num in $allNums) {
        if (Is-Prime $num) { $primesCount++ }
        if ($num -ge 76) { $extremesCount++ }
        if ($num -gt 31) { $gt31Count++ }
        if ($num -gt 80) { $gt80Count++ }
        if ($num % 2 -eq 0) { $evenCount++ }
    }
    $oddCount = $allNums.Count - $evenCount
    $freqMap = @{}
    for ($i = 1; $i -le 90; $i++) { $freqMap[$i] = 0 }
    foreach ($num in $allNums) { $freqMap[$num]++ }
    $top20 = ($freqMap.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20 | ForEach-Object { @{Number = $_.Key; Frequency = $_.Value} })
    $script:stats = @{
        Count = $n; Mean = [math]::Round($mean, 2); Median = $median; StdDev = [math]::Round($stdDev, 2)
        Q1 = $q1; Q3 = $q3; SumMin = ($sums | Measure-Object -Minimum).Minimum; SumMax = ($sums | Measure-Object -Maximum).Maximum
        PrimesPct = [math]::Round($primesCount / $allNums.Count * 100, 2)
        ExtremesPct = [math]::Round($extremesCount / $allNums.Count * 100, 2)
        Gt31Pct = [math]::Round($gt31Count / $allNums.Count * 100, 2)
        Gt80Pct = [math]::Round($gt80Count / $allNums.Count * 100, 2)
        EvenPct = [math]::Round($evenCount / $allNums.Count * 100, 2)
        OddPct = [math]::Round($oddCount / $allNums.Count * 100, 2)
        Top20Numbers = $top20; FirstDate = $script:records[0].Date; LastDate = $script:records[-1].Date
    }
    $jsonObj = [PSCustomObject]@{
        recordCount = $n; firstDate = $script:records[0].Date; lastDate = $script:records[-1].Date
        sumMean = [math]::Round($mean, 2); sumMedian = $median; sumStd = [math]::Round($stdDev, 2)
        sumMin = ($sums | Measure-Object -Minimum).Minimum; sumMax = ($sums | Measure-Object -Maximum).Maximum
        q1 = $q1; q3 = $q3
        primesPct = [math]::Round($primesCount / $allNums.Count * 100, 2)
        extremesPct = [math]::Round($extremesCount / $allNums.Count * 100, 2)
        evenPct = [math]::Round($evenCount / $allNums.Count * 100, 2)
        oddPct = [math]::Round($oddCount / $allNums.Count * 100, 2)
        top20Numbers = $top20
    }
    $jsonObj | ConvertTo-Json -Depth 5 | Set-Content $analisiJsonPath -Encoding UTF8
}

function Load-Data {
    $script:records = Parse-CSV
    Calculate-Stats
    if ($script:records.Count -gt 0) { $script:lastDrawDate = $script:records[-1].Date }
    Update-StatsUI
    Update-ResultsUI
    Update-PlayStatus
}

function Can-PlayToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not (Test-Path $dailyLimitPath)) { return $true }
    $lines = Get-Content $dailyLimitPath -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -ge 2 -and $parts[0] -eq $today) {
            $played = 0
            if ([int]::TryParse($parts[1], [ref]$played)) { return $played -lt 2 }
        }
    }
    return $true
}

function Get-PlayCountToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not (Test-Path $dailyLimitPath)) { return 0 }
    $lines = Get-Content $dailyLimitPath -Encoding UTF8
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -ge 2 -and $parts[0] -eq $today) {
            $played = 0
            if ([int]::TryParse($parts[1], [ref]$played)) { return $played }
        }
    }
    return 0
}

function Increment-PlayCount {
    $today = Get-Date -Format "yyyy-MM-dd"
    $lines = @()
    if (Test-Path $dailyLimitPath) { $lines = @(Get-Content $dailyLimitPath -Encoding UTF8) }
    $found = $false
    $newLines = @()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts[0] -eq $today) {
            $count = 1
            if ($parts.Count -ge 2) { [void][int]::TryParse($parts[1], [ref]$count); $count++ }
            $newLines += "$today,$count"
            $found = $true
        } else { $newLines += $line }
    }
    if (-not $found) { $newLines += "$today,1" }
    $newLines | Out-File -FilePath $dailyLimitPath -Encoding UTF8
}

function Generate-Numbers {
    if (-not (Can-PlayToday)) {
        [System.Windows.Forms.MessageBox]::Show("Hai raggiunto il limite massimo di 2 schedine per oggi.", "Limite Giornaliero", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Carica prima i dati! Clicca 'AGGIORNA CSV'.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    $meanValue = 276.64
    if ($script:stats -ne $null -and $script:stats.Mean -gt 0) { $meanValue = $script:stats.Mean }
    $targetLow = [int]($meanValue - 30)
    $targetHigh = [int]($meanValue + 30)
    $script:generatedNumbers = @()
    for ($s = 0; $s -lt 2; $s++) {
        $attempts = 0; $valid = $false; $bestNums = $null
        while (-not $valid -and $attempts -lt 2000) {
            $nums = @()
            while ($nums.Count -lt 6) {
                $n = Get-Random -Minimum 1 -Maximum 91
                if ($n -notin $nums) { $nums += $n }
            }
            $nums = $nums | Sort-Object
            $sum = ($nums | Measure-Object -Sum).Sum
            $decadeCounts = @{}
            for ($d = 0; $d -lt 9; $d++) { $decadeCounts[$d] = 0 }
            foreach ($n in $nums) {
                $d = Get-Decade $n
                if ($d -lt 9) { $decadeCounts[$d]++ }
            }
            $maxDecade = ($decadeCounts.Values | Measure-Object -Maximum).Maximum
            $gt80 = ($nums | Where-Object { $_ -gt 80 }).Count
            $le31 = ($nums | Where-Object { $_ -le 31 }).Count
            $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($gt80 -le 1) -and ($le31 -ge 1)
            if ($valid) { $bestNums = $nums }
            $attempts++
        }
        if ($valid -and $bestNums -ne $null) {
            $sum = ($bestNums | Measure-Object -Sum).Sum
            $evenCount = ($bestNums | Where-Object { $_ % 2 -eq 0 }).Count
            $script:generatedNumbers += [PSCustomObject]@{
                Nums = $bestNums; Sum = $sum; EvenCount = $evenCount; OddCount = 6 - $evenCount; DecadeDist = $decadeCounts
            }
        }
    }
    if ($script:generatedNumbers.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Impossibile generare numeri validi. Riprova.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    Display-Generated
    Save-Tracking
    Increment-PlayCount
    Update-PlayStatus
    $script:statusLabel.Text = "Generati $($script:generatedNumbers.Count) schedine! (Totale oggi: $(Get-PlayCountToday))"
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
}

function Display-Generated {
    if ($script:generatedNumbers.Count -eq 0) { return }
    $text = ""
    for ($i = 0; $i -lt $script:generatedNumbers.Count; $i++) {
        $sched = $script:generatedNumbers[$i]
        $numsStr = ($sched.Nums -join " - ")
        $text += "SCHEDINA $($i + 1): $numsStr" + [Environment]::NewLine
        $text += "  Somma: $($sched.Sum) | Pari: $($sched.EvenCount) | Dispari: $($sched.OddCount)" + [Environment]::NewLine
        $text += [Environment]::NewLine
    }
    $script:txtNumeri.Text = $text
}

function Save-Tracking {
    if ($script:generatedNumbers.Count -eq 0) { return }
    $today = Get-Date -Format "yyyy-MM-dd"
    $dayName = (Get-Date).DayOfWeek.ToString()
    $header = "data,giornata,budget,schedine,numeri,somma,jackpot,verificato"
    if (-not (Test-Path $trackingPath)) { $header | Out-File -Path $trackingPath -Encoding UTF8 }
    foreach ($sched in $script:generatedNumbers) {
        $numsStr = $sched.Nums -join "-"
        $line = "$today,$dayName,1.00,1,$numsStr,$($sched.Sum),$script:jackpot,no"
        Add-Content -Path $trackingPath -Value $line -Encoding UTF8
    }
}

function Verify-Wins {
    if (-not (Test-Path $trackingPath)) {
        [System.Windows.Forms.MessageBox]::Show("Nessuna giocata registrata in tracking.csv", "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Carica prima i dati delle estrazioni!", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    $lastDraw = $script:records[-1]
    $lines = Get-Content $trackingPath -Encoding UTF8
    $results = @(); $updatedLines = @(); $updated = $false
    $header = $lines[0]; $updatedLines += $header
    for ($i = 1; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts.Count -lt 8) { $updatedLines += $line; continue }
        $verificato = $parts[7].Trim()
        if ($verificato -eq "si") { $updatedLines += $line; continue }
        $numsStr = $parts[4]
        $playedNums = @()
        foreach ($n in ($numsStr -split '-')) {
            $val = 0
            if ([int]::TryParse($n.Trim(), [ref]$val)) { $playedNums += $val }
        }
        $matches = 0
        foreach ($n in $playedNums) { if ($n -in $lastDraw.Nums) { $matches++ } }
        $prize = 0
        switch ($matches) {
            2 { $prize = 5 }
            3 { $prize = 25 }
            4 { $prize = 300 }
            5 { $prize = 10000 }
            6 { $prize = 2000000000 }
        }
        $results += "Data: $($parts[0]) | Numeri: $numsStr | Match: $matches | Premio: EUR $prize"
        $parts[7] = "si"
        $updatedLines += ($parts -join ',')
        $updated = $true
    }
    if ($updated) { $updatedLines | Out-File -FilePath $trackingPath -Encoding UTF8 }
    if ($results.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Nessuna giocata da verificare con l'ultima estrazione." + [Environment]::NewLine + "Ultima estrazione: $($lastDraw.Date)" + [Environment]::NewLine + "Numeri: $($lastDraw.Nums -join ' - ')", "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    } else {
        $msg = "ULTIMA ESTRAZIONE: $($lastDraw.Date)" + [Environment]::NewLine
        $msg += "Numeri: $($lastDraw.Nums -join ' - ')" + [Environment]::NewLine + [Environment]::NewLine
        $msg += "RISULTATI VERIFICA:" + [Environment]::NewLine + [Environment]::NewLine
        $msg += $results -join [Environment]::NewLine
        [System.Windows.Forms.MessageBox]::Show($msg, "Verifica Vincite", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    }
}

function Export-Tracking {
    if (-not (Test-Path $trackingPath)) {
        [System.Windows.Forms.MessageBox]::Show("Nessun file di tracking da esportare.", "Esporta Tracking", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    $saveDialog = New-Object System.Windows.Forms.SaveFileDialog
    $saveDialog.Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
    $saveDialog.FileName = "superenalotto_tracking_$(Get-Date -Format 'yyyyMMdd').csv"
    $saveDialog.Title = "Esporta Tracking"
    if ($saveDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        Copy-Item -Path $trackingPath -Destination $saveDialog.FileName -Force
        [System.Windows.Forms.MessageBox]::Show("Tracking esportato in: $($saveDialog.FileName)", "Esporta Tracking", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    }
}

function Update-CSV {
    $script:statusLabel.Text = "Tentativo aggiornamento API..."
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
    $script:form.Refresh()
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 15 -ErrorAction Stop
        $newCount = 0
        $existingDates = @()
        if (Test-Path $csvPath) {
            $existingLines = Get-Content $csvPath -Encoding UTF8
            foreach ($l in $existingLines) {
                if ([string]::IsNullOrWhiteSpace($l)) { continue }
                $p = $l -split ','
                if ($p.Count -ge 2) { $existingDates += $p[0].Trim() }
            }
        }
        foreach ($r in $response.results) {
            $date = $r.draw_date
            if ($date -in $existingDates) { continue }
            $balls = $r.balls
            $jolly = 0; $star = 0
            if ($r.ball_bonus) {
                if ($r.ball_bonus.Count -gt 0) { $jolly = [int]$r.ball_bonus[0] }
                if ($r.ball_bonus.Count -gt 1) { $star = [int]$r.ball_bonus[1] }
            }
            $line = "$date,,$([int]$balls[0]),$([int]$balls[1]),$([int]$balls[2]),$([int]$balls[3]),$([int]$balls[4]),$([int]$balls[5]),$jolly,$star"
            Add-Content -Path $csvPath -Value $line -Encoding UTF8
            $newCount++
        }
        if ($newCount -gt 0) {
            $script:statusLabel.Text = "OK! Aggiunti $newCount estrazioni da API!"
            $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
            Load-Data
        } else {
            $script:statusLabel.Text = "API OK. Dati gia aggiornati."
            $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
            Load-Data
        }
    } catch {
        $script:statusLabel.Text = "API non raggiungibile. Uso CSV locale."
        $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 68, 68)
        Load-Data
        [System.Windows.Forms.MessageBox]::Show("API non raggiungibile." + [Environment]::NewLine + "I dati sono stati caricati dal CSV locale." + [Environment]::NewLine + "Ultima estrazione: $script:lastDrawDate", "Aggiornamento API", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
    }
}

function Get-Jackpot {
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        if ($response.results -and $response.results.Count -gt 0) {
            $jpRaw = $response.results[0].jackpot
            $jp = [double]$jpRaw
            $script:jackpot = if ($jp -gt 1000000) { [math]::Round($jp / 1000000, 1) } else { 0 }
            if ($script:jackpot -gt 0) { $script:jackpotLabel.Text = "Jackpot: EUR $script:jackpot M" }
            else { $script:jackpotLabel.Text = "Jackpot: N/D" }
        }
    } catch {
        $script:jackpot = 0
        $script:jackpotLabel.Text = "Jackpot: N/D"
    }
}

function Update-StatsUI {
    if ($script:stats -eq $null) {
        $script:lblTotEstrazioni.Text = "Estrazioni: 0"
        $script:lblMedia.Text = "Media: N/D"
        return
    }
    $script:lblTotEstrazioni.Text = "Estrazioni: $($script:stats.Count)"
    $script:lblMedia.Text = "Media: $($script:stats.Mean)"
    $script:lblMediana.Text = "Mediana: $($script:stats.Median)"
    $script:lblStdDev.Text = "Std Dev: $($script:stats.StdDev)"
    $script:lblQ1Q3.Text = "Q1: $($script:stats.Q1) | Q3: $($script:stats.Q3)"
    $script:lblSommaRange.Text = "Range: $($script:stats.SumMin) - $($script:stats.SumMax)"
    $script:lblPrimes.Text = "Primi: $($script:stats.PrimesPct)%"
    $script:lblExtremes.Text = "Estremi: $($script:stats.ExtremesPct)%"
    $script:lblGt80.Text = ">80: $($script:stats.Gt80Pct)%"
    $script:lblEvenOdd.Text = "Pari: $($script:stats.EvenPct)% | Dispari: $($script:stats.OddPct)%"
    if ($script:stats.FirstDate -and $script:stats.LastDate) {
        $script:lblDateRange.Text = "Periodo: $($script:stats.FirstDate) - $($script:stats.LastDate)"
    }
    $topText = "TOP 10 NUMERI:" + [Environment]::NewLine
    for ($i = 0; $i -lt [Math]::Min(10, $script:stats.Top20Numbers.Count); $i++) {
        $item = $script:stats.Top20Numbers[$i]
        $topText += "$($i + 1). Numero $($item.Number) (freq: $($item.Frequency))" + [Environment]::NewLine
    }
    $script:lblTop10.Text = $topText
}

function Update-ResultsUI {
    $script:dataGrid.Rows.Clear()
    $count = 0
    for ($i = $script:records.Count - 1; $i -ge 0 -and $count -lt 15; $i--) {
        $rec = $script:records[$i]
        $numsStr = ($rec.Nums -join " - ")
        $jollyStr = if ($rec.Jolly -gt 0) { $rec.Jolly.ToString() } else { "-" }
        $starStr = if ($rec.Star -gt 0) { $rec.Star.ToString() } else { "-" }
        $bgColor = if ($count % 2 -eq 0) { [System.Drawing.Color]::FromArgb(30, 30, 60) } else { [System.Drawing.Color]::FromArgb(45, 45, 75) }
        $script:dataGrid.Rows.Add($rec.Date, $numsStr, $jollyStr, $starStr, $rec.Sum)
        $script:dataGrid.Rows[$count].DefaultCellStyle.BackColor = $bgColor
        $script:dataGrid.Rows[$count].DefaultCellStyle.ForeColor = [System.Drawing.Color]::White
        $count++
    }
}

function Update-PlayStatus {
    $played = Get-PlayCountToday
    $remaining = 2 - $played
    if ($remaining -gt 0) {
        $script:lblPlayStatus.Text = "Schedine oggi: $played / 2 (restano: $remaining)"
        $script:lblPlayStatus.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
    } else {
        $script:lblPlayStatus.Text = "LIMITE RAGGIUNTO (2/2 oggi)"
        $script:lblPlayStatus.ForeColor = [System.Drawing.Color]::FromArgb(255, 68, 68)
    }
    $today = (Get-Date).DayOfWeek.ToString()
    $nextDraw = "Martedi"
    switch ($today) {
        "Monday" { $nextDraw = "Martedi" }
        "Tuesday" { $nextDraw = "Giovedi" }
        "Wednesday" { $nextDraw = "Giovedi" }
        "Thursday" { $nextDraw = "Venerdi" }
        "Friday" { $nextDraw = "Sabato" }
        "Saturday" { $nextDraw = "Martedi" }
        "Sunday" { $nextDraw = "Martedi" }
    }
    $script:lblNextDraw.Text = "Prossima estrazione: $nextDraw"
}
# === GUI CREATION ===
$form = New-Object System.Windows.Forms.Form
$form.Text = "SuperEnalotto - Algoritmo Sniper v4"
$form.Size = New-Object System.Drawing.Size(1100, 800)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(26, 26, 46)

$panelHeader = New-Object System.Windows.Forms.Panel
$panelHeader.Location = New-Object System.Drawing.Point(0, 0)
$panelHeader.Size = New-Object System.Drawing.Size(1080, 60)
$panelHeader.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
$panelHeader.Parent = $form

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Location = New-Object System.Drawing.Point(20, 15)
$lblTitle.Size = New-Object System.Drawing.Size(500, 30)
$lblTitle.Text = "SUPERENALOTTO - ALGORITMO SNIPER v4"
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblTitle.Parent = $panelHeader

$script:jackpotLabel = New-Object System.Windows.Forms.Label
$script:jackpotLabel.Location = New-Object System.Drawing.Point(700, 20)
$script:jackpotLabel.Size = New-Object System.Drawing.Size(360, 25)
$script:jackpotLabel.Text = "Jackpot: N/D"
$script:jackpotLabel.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$script:jackpotLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
$script:jackpotLabel.TextAlign = [System.Drawing.ContentAlignment]::TopRight
$script:jackpotLabel.Parent = $panelHeader

$panelStats = New-Object System.Windows.Forms.Panel
$panelStats.Location = New-Object System.Drawing.Point(20, 75)
$panelStats.Size = New-Object System.Drawing.Size(320, 470)
$panelStats.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
$panelStats.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$panelStats.Parent = $form

$lblStatsTitle = New-Object System.Windows.Forms.Label
$lblStatsTitle.Location = New-Object System.Drawing.Point(10, 10)
$lblStatsTitle.Size = New-Object System.Drawing.Size(300, 25)
$lblStatsTitle.Text = "STATISTICHE STORICHE"
$lblStatsTitle.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$lblStatsTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblStatsTitle.Parent = $panelStats

$script:lblTotEstrazioni = New-Object System.Windows.Forms.Label
$script:lblTotEstrazioni.Location = New-Object System.Drawing.Point(10, 45)
$script:lblTotEstrazioni.Size = New-Object System.Drawing.Size(300, 20)
$script:lblTotEstrazioni.ForeColor = [System.Drawing.Color]::White
$script:lblTotEstrazioni.Parent = $panelStats

$script:lblDateRange = New-Object System.Windows.Forms.Label
$script:lblDateRange.Location = New-Object System.Drawing.Point(10, 65)
$script:lblDateRange.Size = New-Object System.Drawing.Size(300, 20)
$script:lblDateRange.ForeColor = [System.Drawing.Color]::White
$script:lblDateRange.Parent = $panelStats

$script:lblMedia = New-Object System.Windows.Forms.Label
$script:lblMedia.Location = New-Object System.Drawing.Point(10, 95)
$script:lblMedia.Size = New-Object System.Drawing.Size(300, 20)
$script:lblMedia.ForeColor = [System.Drawing.Color]::White
$script:lblMedia.Parent = $panelStats

$script:lblMediana = New-Object System.Windows.Forms.Label
$script:lblMediana.Location = New-Object System.Drawing.Point(10, 115)
$script:lblMediana.Size = New-Object System.Drawing.Size(300, 20)
$script:lblMediana.ForeColor = [System.Drawing.Color]::White
$script:lblMediana.Parent = $panelStats

$script:lblStdDev = New-Object System.Windows.Forms.Label
$script:lblStdDev.Location = New-Object System.Drawing.Point(10, 135)
$script:lblStdDev.Size = New-Object System.Drawing.Size(300, 20)
$script:lblStdDev.ForeColor = [System.Drawing.Color]::White
$script:lblStdDev.Parent = $panelStats

$script:lblQ1Q3 = New-Object System.Windows.Forms.Label
$script:lblQ1Q3.Location = New-Object System.Drawing.Point(10, 155)
$script:lblQ1Q3.Size = New-Object System.Drawing.Size(300, 20)
$script:lblQ1Q3.ForeColor = [System.Drawing.Color]::White
$script:lblQ1Q3.Parent = $panelStats

$script:lblSommaRange = New-Object System.Windows.Forms.Label
$script:lblSommaRange.Location = New-Object System.Drawing.Point(10, 175)
$script:lblSommaRange.Size = New-Object System.Drawing.Size(300, 20)
$script:lblSommaRange.ForeColor = [System.Drawing.Color]::White
$script:lblSommaRange.Parent = $panelStats

$script:lblPrimes = New-Object System.Windows.Forms.Label
$script:lblPrimes.Location = New-Object System.Drawing.Point(10, 205)
$script:lblPrimes.Size = New-Object System.Drawing.Size(300, 20)
$script:lblPrimes.ForeColor = [System.Drawing.Color]::White
$script:lblPrimes.Parent = $panelStats

$script:lblExtremes = New-Object System.Windows.Forms.Label
$script:lblExtremes.Location = New-Object System.Drawing.Point(10, 225)
$script:lblExtremes.Size = New-Object System.Drawing.Size(300, 20)
$script:lblExtremes.ForeColor = [System.Drawing.Color]::White
$script:lblExtremes.Parent = $panelStats

$script:lblGt80 = New-Object System.Windows.Forms.Label
$script:lblGt80.Location = New-Object System.Drawing.Point(10, 245)
$script:lblGt80.Size = New-Object System.Drawing.Size(300, 20)
$script:lblGt80.ForeColor = [System.Drawing.Color]::White
$script:lblGt80.Parent = $panelStats

$script:lblEvenOdd = New-Object System.Windows.Forms.Label
$script:lblEvenOdd.Location = New-Object System.Drawing.Point(10, 265)
$script:lblEvenOdd.Size = New-Object System.Drawing.Size(300, 20)
$script:lblEvenOdd.ForeColor = [System.Drawing.Color]::White
$script:lblEvenOdd.Parent = $panelStats

$script:lblTop10 = New-Object System.Windows.Forms.Label
$script:lblTop10.Location = New-Object System.Drawing.Point(10, 300)
$script:lblTop10.Size = New-Object System.Drawing.Size(300, 160)
$script:lblTop10.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
$script:lblTop10.Font = New-Object System.Drawing.Font("Consolas", 9)
$script:lblTop10.Parent = $panelStats

$panelResults = New-Object System.Windows.Forms.Panel
$panelResults.Location = New-Object System.Drawing.Point(355, 75)
$panelResults.Size = New-Object System.Drawing.Size(410, 470)
$panelResults.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
$panelResults.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$panelResults.Parent = $form

$lblResultsTitle = New-Object System.Windows.Forms.Label
$lblResultsTitle.Location = New-Object System.Drawing.Point(10, 10)
$lblResultsTitle.Size = New-Object System.Drawing.Size(390, 25)
$lblResultsTitle.Text = "ULTIME ESTRAZIONI"
$lblResultsTitle.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$lblResultsTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblResultsTitle.Parent = $panelResults

$script:dataGrid = New-Object System.Windows.Forms.DataGridView
$script:dataGrid.Location = New-Object System.Drawing.Point(10, 45)
$script:dataGrid.Size = New-Object System.Drawing.Size(390, 415)
$script:dataGrid.BackgroundColor = [System.Drawing.Color]::FromArgb(30, 30, 60)
$script:dataGrid.RowHeadersVisible = $false
$script:dataGrid.ColumnCount = 5
$script:dataGrid.Columns[0].Name = "Data"
$script:dataGrid.Columns[1].Name = "Numeri"
$script:dataGrid.Columns[2].Name = "Jolly"
$script:dataGrid.Columns[3].Name = "Star"
$script:dataGrid.Columns[4].Name = "Somma"
$script:dataGrid.Columns[0].Width = 85
$script:dataGrid.Columns[1].Width = 170
$script:dataGrid.Columns[2].Width = 50
$script:dataGrid.Columns[3].Width = 50
$script:dataGrid.Columns[4].Width = 55
$script:dataGrid.AllowUserToAddRows = $false
$script:dataGrid.AllowUserToDeleteRows = $false
$script:dataGrid.ReadOnly = $true
$script:dataGrid.Parent = $panelResults

$panelActions = New-Object System.Windows.Forms.Panel
$panelActions.Location = New-Object System.Drawing.Point(780, 75)
$panelActions.Size = New-Object System.Drawing.Size(300, 470)
$panelActions.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
$panelActions.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$panelActions.Parent = $form

$lblActionsTitle = New-Object System.Windows.Forms.Label
$lblActionsTitle.Location = New-Object System.Drawing.Point(10, 10)
$lblActionsTitle.Size = New-Object System.Drawing.Size(280, 25)
$lblActionsTitle.Text = "AZIONI"
$lblActionsTitle.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$lblActionsTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblActionsTitle.Parent = $panelActions

$btnUpdate = New-Object System.Windows.Forms.Button
$btnUpdate.Location = New-Object System.Drawing.Point(10, 45)
$btnUpdate.Size = New-Object System.Drawing.Size(280, 35)
$btnUpdate.Text = "AGGIORNA CSV (API)"
$btnUpdate.BackColor = [System.Drawing.Color]::FromArgb(0, 150, 200)
$btnUpdate.ForeColor = [System.Drawing.Color]::White
$btnUpdate.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnUpdate.Add_Click({ Update-CSV })
$btnUpdate.Parent = $panelActions

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Location = New-Object System.Drawing.Point(10, 90)
$btnRefresh.Size = New-Object System.Drawing.Size(280, 35)
$btnRefresh.Text = "RICALCOLA STATS"
$btnRefresh.BackColor = [System.Drawing.Color]::FromArgb(100, 100, 150)
$btnRefresh.ForeColor = [System.Drawing.Color]::White
$btnRefresh.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnRefresh.Add_Click({ Load-Data; $script:statusLabel.Text = "Dati ricaricati!" })
$btnRefresh.Parent = $panelActions

$btnGenerate = New-Object System.Windows.Forms.Button
$btnGenerate.Location = New-Object System.Drawing.Point(10, 135)
$btnGenerate.Size = New-Object System.Drawing.Size(280, 35)
$btnGenerate.Text = "GENERA NUMERI"
$btnGenerate.BackColor = [System.Drawing.Color]::FromArgb(0, 180, 100)
$btnGenerate.ForeColor = [System.Drawing.Color]::White
$btnGenerate.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnGenerate.Add_Click({ Generate-Numbers })
$btnGenerate.Parent = $panelActions

$btnVerify = New-Object System.Windows.Forms.Button
$btnVerify.Location = New-Object System.Drawing.Point(10, 180)
$btnVerify.Size = New-Object System.Drawing.Size(280, 35)
$btnVerify.Text = "VERIFICA VINCITE"
$btnVerify.BackColor = [System.Drawing.Color]::FromArgb(200, 150, 0)
$btnVerify.ForeColor = [System.Drawing.Color]::White
$btnVerify.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnVerify.Add_Click({ Verify-Wins })
$btnVerify.Parent = $panelActions

$btnExport = New-Object System.Windows.Forms.Button
$btnExport.Location = New-Object System.Drawing.Point(10, 225)
$btnExport.Size = New-Object System.Drawing.Size(280, 35)
$btnExport.Text = "ESPORTA TRACKING"
$btnExport.BackColor = [System.Drawing.Color]::FromArgb(150, 100, 50)
$btnExport.ForeColor = [System.Drawing.Color]::White
$btnExport.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnExport.Add_Click({ Export-Tracking })
$btnExport.Parent = $panelActions

$lblPlayTitle = New-Object System.Windows.Forms.Label
$lblPlayTitle.Location = New-Object System.Drawing.Point(10, 280)
$lblPlayTitle.Size = New-Object System.Drawing.Size(280, 20)
$lblPlayTitle.Text = "STATO GIOCATA"
$lblPlayTitle.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$lblPlayTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblPlayTitle.Parent = $panelActions

$script:lblPlayStatus = New-Object System.Windows.Forms.Label
$script:lblPlayStatus.Location = New-Object System.Drawing.Point(10, 305)
$script:lblPlayStatus.Size = New-Object System.Drawing.Size(280, 20)
$script:lblPlayStatus.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
$script:lblPlayStatus.Parent = $panelActions

$script:lblNextDraw = New-Object System.Windows.Forms.Label
$script:lblNextDraw.Location = New-Object System.Drawing.Point(10, 330)
$script:lblNextDraw.Size = New-Object System.Drawing.Size(280, 20)
$script:lblNextDraw.ForeColor = [System.Drawing.Color]::White
$script:lblNextDraw.Parent = $panelActions

$lblNumeriTitle = New-Object System.Windows.Forms.Label
$lblNumeriTitle.Location = New-Object System.Drawing.Point(10, 360)
$lblNumeriTitle.Size = New-Object System.Drawing.Size(280, 20)
$lblNumeriTitle.Text = "NUMERI GENERATI"
$lblNumeriTitle.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$lblNumeriTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 255)
$lblNumeriTitle.Parent = $panelActions

$script:txtNumeri = New-Object System.Windows.Forms.TextBox
$script:txtNumeri.Location = New-Object System.Drawing.Point(10, 385)
$script:txtNumeri.Size = New-Object System.Drawing.Size(280, 80)
$script:txtNumeri.Multiline = $true
$script:txtNumeri.ReadOnly = $true
$script:txtNumeri.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 60)
$script:txtNumeri.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
$script:txtNumeri.Font = New-Object System.Drawing.Font("Consolas", 9)
$script:txtNumeri.Text = "Clicca 'GENERA NUMERI' per iniziare"
$script:txtNumeri.Parent = $panelActions

$script:statusLabel = New-Object System.Windows.Forms.Label
$script:statusLabel.Location = New-Object System.Drawing.Point(0, 555)
$script:statusLabel.Size = New-Object System.Drawing.Size(1080, 25)
$script:statusLabel.Text = "Pronto. Clicca 'AGGIORNA CSV' per iniziare."
$script:statusLabel.BackColor = [System.Drawing.Color]::FromArgb(20, 20, 40)
$script:statusLabel.ForeColor = [System.Drawing.Color]::White
$script:statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$script:statusLabel.Parent = $form

Load-Data
Get-Jackpot

$today = (Get-Date).DayOfWeek.ToString()
$drawDays = @("Tuesday", "Thursday", "Friday", "Saturday")
if ($today -in $drawDays) {
    $script:statusLabel.Text = "OGGI E' $today - GIORNO DI ESTRAZIONE!"
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
}

$form.ShowDialog()
