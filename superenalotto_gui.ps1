Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$apiUrl = "https://www.lotteryresultsfeed.com"
$lotteryId = 712
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$trackingPath = Join-Path $scriptDir "tracking.csv"
$configPath = Join-Path $scriptDir "config.json"
$dailyLimitPath = Join-Path $scriptDir "daily_limit.csv"
$drawDays = @("Tuesday", "Thursday", "Friday", "Saturday")
$script:DailyMaxSchedines = 2

$script:records = @()
$script:stats = @{}
$script:lastDrawDate = ""

# Load configuration
function Load-Config {
    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath -Raw | ConvertFrom-Json
            if ($config.apiKey) { $script:apiKey = $config.apiKey }
            if ($config.apiUrl) { $script:apiUrl = $config.apiUrl }
            if ($config.lotteryId) { $script:lotteryId = $config.lotteryId }
        } catch {
            # If config is corrupted, use defaults
        }
    }
}

# Save configuration
function Save-Config {
    $config = @{
        apiKey = $script:apiKey
        apiUrl = $script:apiUrl
        lotteryId = $script:lotteryId
    }
    $config | ConvertTo-Json -Depth 3 | Set-Content $configPath
}

# Load config at startup
Load-Config

function Load-Data {
    if (Test-Path $csvPath) {
        $script:records = @()
        $lines = Get-Content $csvPath | Select-Object -Skip 1
        foreach ($line in $lines) {
            $parts = $line -split ','
            if ($parts.Count -ge 9) {
                try {
                    $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], 
                              [int]$parts[5], [int]$parts[6], [int]$parts[7])
                    if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                        $script:records += [PSCustomObject]@{
                            Date = $parts[0]
                            Conc = $parts[1]
                            N1 = $nums[0]; $N2 = $nums[1]; $N3 = $nums[2]
                            N4 = $nums[3]; $N5 = $nums[4]; $N6 = $nums[5]
                            Nums = $nums
                            Sum = ($nums | Measure-Object -Sum).Sum
                            Jolly = [int]$parts[8]
                            Star = if ($parts.Count -gt 9) { [int]$parts[9] } else { 0 }
                        }
                    }
                } catch {}
            }
        }
        Calculate-Stats
        $script:lastDrawDate = $script:records[-1].Date
        Update-StatsUI
        Update-ResultsUI
    }
}

function Calculate-Stats {
    if ($script:records.Count -eq 0) { return }
    
    $sums = $script:records | ForEach-Object { $_.Sum }
    $allNums = $script:records | ForEach-Object { $_.Nums } | ForEach-Object { $_ }
    $sumsSorted = $sums | Sort-Object
    $n = $sumsSorted.Count
    $mean = ($sums | Measure-Object -Average).Average
    $median = $sumsSorted[[int]($n / 2)]
    
    $sumSq = 0
    foreach ($s in $sums) { $sumSq += [math]::Pow($s - $mean, 2) }
    $std = [math]::Sqrt($sumSq / $n)
    
    $script:stats = @{
        Count = $n
        Mean = [math]::Round($mean, 2)
        Median = $median
        Std = [math]::Round($std, 2)
        Q1 = $sumsSorted[[int]($n * 0.25)]
        Q3 = $sumsSorted[[int]($n * 0.75)]
        Min = ($sums | Measure-Object -Minimum).Minimum
        Max = ($sums | Measure-Object -Maximum).Maximum
        Primes = [math]::Round(($allNums | Where-Object { Test-Prime $_ }).Count / $allNums.Count * 100, 2)
        Extremes = [math]::Round(($allNums | Where-Object { $_ -ge 76 }).Count / $allNums.Count * 100, 2)
    }
}

function Test-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) {
        if ($n % $i -eq 0) { return $false }
    }
    return $true
}

function Update-CSV {
    $script:statusLabel.Text = "Tentativo con API..."
    $script:form.Refresh()
    
    # Usa la stessa API di sniper_full.ps1 (lotteryresultsfeed.com)
    $apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=$lotteryId"
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
            $script:statusLabel.Text = "Aggiunti $newCount estrazioni!"
            Load-Data
        } else {
            $script:statusLabel.Text = "Dati gia aggiornati."
        }
    } catch {
        $script:statusLabel.Text = "API non disponibile`nUsa dati locali"
        
        # Fallback: usa l'ultima estrazione dal CSV per non perdere le stats
        if (Test-Path $csvPath) {
            $lines = Get-Content $csvPath | Select-Object -Skip 1
            $latestDate = "1997-12-03"
            foreach ($l in $lines) {
                $p = $l -split ','
                if ($p.Count -ge 2 -and $p[0] -gt $latestDate) { $latestDate = $p[0] }
            }
            $script:lastDrawDate = $latestDate
        }
    }
}

function Get-Jackpot {
    # Usa la stessa API di sniper_full.ps1
    $apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=$lotteryId"
    try {
        $headers = @{ "X-API-KEY" = $apiKey }
        $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        if ($response.results -ne $null -and $response.results.Count -gt 0) {
            $jp = $response.results[0].jackpot
            $script:jackpot = if ($jp -gt 1000000) { [math]::Round($jp / 1000000, 1) } else { $jp }
            if ($script:jackpotLabel) {
                $script:jackpotLabel.Text = "Jackpot: EUR " + $script:jackpot + "M"
            }
        } else {
            $script:jackpot = 0
            if ($script:jackpotLabel) { $script:jackpotLabel.Text = "Jackpot: N/D" }
        }
    } catch {
        $script:jackpot = 0
        if ($script:jackpotLabel) { $script:jackpotLabel.Text = "Jackpot: N/D" }
    }
}

function Can-PlayToday {
    $today = Get-Date -Format "yyyy-MM-dd"
    if (-not (Test-Path $dailyLimitPath)) {
        return $true
    }
    try {
        $limits = Import-Csv -Path $dailyLimitPath | Where-Object { $_.data -eq $today }
        if ($limits.Count -eq 0) { return $true }
        $played = [int]$limits[0].schedine_giocate
        return $played -lt $script:DailyMaxSchedines
    } catch {
        return $true
    }
}

function Generate-Numbers {
    if (-not (Can-PlayToday)) {
        [System.Windows.Forms.MessageBox]::Show(
            "Hai raggiunto il limite massimo di 2 schedine per oggi.`n`n" +
            "Gioca domani o aspetta la prossima estrazione.",
            "Limite Giornaliero",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
        return
    }
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Carica prima i dati! Clicca 'AGGIORNA CSV' o usa i dati locali.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    # Usa la media storica del manuale (276.64) come fallback se le stats non sono calcolate
    $meanValue = if ($script:stats.Mean -ne $null) { $script:stats.Mean } else { 276.64 }
    $targetLow = [int]($meanValue - 30)
    $targetHigh = [int]($meanValue + 30)
    
    $script:generatedNumbers = @()
    
    for ($s = 0; $s -lt 2; $s++) {
        $attempts = 0
        do {
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
            
            $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($veryHigh -le 1)
            $attempts++
        } while (-not $valid -and $attempts -lt 1000)
        
        if ($valid) {
            $script:generatedNumbers += [PSCustomObject]@{
                Nums = $nums
                Sum = $sum
            }
        }
    }
    
    if ($script:generatedNumbers.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Impossibile generare numeri validi. Riprova.", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    Display-Generated
    Save-Tracking
}

function Display-Generated {
    $numbersPanel.Controls.Clear()
    
    foreach ($i in 0..($script:generatedNumbers.Count - 1)) {
        $sched = $script:generatedNumbers[$i]
        $panel = New-Object System.Windows.Forms.Panel
        $panel.Location = New-Object System.Drawing.Point(10, ($i * 90))
        $panel.Size = New-Object System.Drawing.Size(350, 80)
        $panel.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 50)
        $panel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
        
        $header = New-Object System.Windows.Forms.Label
        $header.Text = "SCHEDINA $($i + 1)"
        $header.Location = New-Object System.Drawing.Point(10, 10)
        $header.Size = New-Object System.Drawing.Size(100, 20)
        $header.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
        $header.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
        $panel.Controls.Add($header)
        
        $sumLabel = New-Object System.Windows.Forms.Label
        $sumLabel.Text = "Somma: $($sched.Sum)"
        $sumLabel.Location = New-Object System.Drawing.Point(250, 10)
        $sumLabel.Size = New-Object System.Drawing.Size(90, 20)
        $sumLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
        $panel.Controls.Add($sumLabel)
        
        $x = 10
        foreach ($n in $sched.Nums) {
            $ball = New-Object System.Windows.Forms.Label
            $ball.Text = $n
            $ball.Location = New-Object System.Drawing.Point($x, 35)
            $ball.Size = New-Object System.Drawing.Size(50, 40)
            $ball.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
            $ball.BackColor = [System.Drawing.Color]::FromArgb(0, 150, 200)
            $ball.ForeColor = [System.Drawing.Color]::White
            $ball.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
            $ball.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
            $panel.Controls.Add($ball)
            $x += 55
        }
        
        $numbersPanel.Controls.Add($panel)
    }
}

function Save-Tracking {
    if (-not $script:generatedNumbers) { return }
    
    $today = Get-Date -Format "yyyy-MM-dd"
    $dayName = (Get-Date).DayOfWeek.ToString()
    
    if (-not (Test-Path $trackingPath)) {
        "data,giornata,budget,schedine,numeri,somma,jackpot,verificato" | Out-File -Path $trackingPath -Encoding UTF8
    }
    
    foreach ($sched in $script:generatedNumbers) {
        $numsStr = $sched.Nums -join "-"
        $line = "$today,$dayName,1.00,1,$numsStr,$($sched.Sum),$script:jackpot,no"
        Add-Content -Path $trackingPath -Value $line
    }
    
    # Aggiorna il file di limitazione giornaliero
    $todayStr = $today
    $played = 0
    if (Test-Path $dailyLimitPath) {
        $limits = Import-Csv -Path $dailyLimitPath
        $existing = $limits | Where-Object { $_.data -eq $todayStr }
        if ($existing.Count -gt 0) {
            $played = [int]$existing[0].schedine_giocate
        }
    }
    if ($played -lt 2) {
        $played++
        $entry = [PSCustomObject]@{
            data = $todayStr
            schedine_giocate = $played
        }
        $existingAll = @()
        if (Test-Path $dailyLimitPath) {
            $existingAll = @(Import-Csv -Path $dailyLimitPath | Where-Object { $_.data -ne $todayStr })
        }
        $existingAll += $entry
        $existingAll | Export-Csv -Path $dailyLimitPath -NoTypeInformation -Encoding UTF8
    }
    
    $script:statusLabel.Text = "Tracking salvato! ($($script:generatedNumbers.Count) schedine)"
}

function Check-Win {
    if (-not $script:generatedNumbers) {
        [System.Windows.Forms.MessageBox]::Show("Genera prima i numeri!", "Verifica", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Nessun dato disponibile!", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    $lastDraw = $script:records[-1]
    $msg = "Ultima estrazione ($($lastDraw.Date)):`n$($lastDraw.Nums -join ' - ')`n`n"
    $msg += "I tuoi numeri:`n"
    
    foreach ($i in 0..($script:generatedNumbers.Count - 1)) {
        $sched = $script:generatedNumbers[$i]
        $matches = ($sched.Nums | Where-Object { $_ -in $lastDraw.Nums }).Count
        $msg += "Schedina $($i+1): $matches numeri indovinati"
        if ($matches -ge 3) { $msg += " [VINCITA!]" }
        $msg += "`n"
    }
    
    [System.Windows.Forms.MessageBox]::Show($msg, "Verifica Vincita", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
}

function Update-StatsUI {
    if (-not $script:stats -or $script:stats.Count -eq 0) { return }
    $s = $script:stats
    
    if (-not $script:statCount) { return }
    $script:statCount.Text = "Estrazioni: $($s.Count)"
    $script:statMean.Text = "Media: $($s.Mean)"
    $script:statMedian.Text = "Mediana: $($s.Median)"
    $script:statStd.Text = "Std Dev: $($s.Std)"
    $script:statQ1Q3.Text = "Q1/Q3: $($s.Q1)/$($s.Q3)"
    $script:statRange.Text = "Range: $($s.Min)-$($s.Max)"
    $script:statPrimes.Text = "Primi: $($s.Primes)%"
    $script:statExtremes.Text = "Estremi: $($s.Extremes)%"
}

function Update-ResultsUI {
    if (-not $script:resultsListbox) { return }
    $script:resultsListbox.Items.Clear()
    foreach ($r in ($script:records | Select-Object -Last 15 | Sort-Object Date -Descending)) {
        $numsStr = $r.Nums -join "  "
        $script:resultsListbox.Items.Add("$($r.Date)  |  $numsStr")
    }
}

function Setup-Scheduler {
    $taskName = "SuperEnalotto_Sniper"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\\sniper_full.ps1`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday, Thursday, Friday, Saturday -At "19:00"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "SuperEnalotto Sniper - Auto aggiornamento e generazione numeri" | Out-Null
    
    [System.Windows.Forms.MessageBox]::Show("Scheduler attivato!`nEsecuzione ogni Mar, Gio, Ven, Sab alle 19:00", "Scheduler", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
}

function Create-Form {
    $script:form = New-Object System.Windows.Forms.Form
    $script:form.Text = "SuperEnalotto - Protocollo Sniper"
    $script:form.Size = New-Object System.Drawing.Size(900, 750)
    $script:form.StartPosition = "CenterScreen"
    $script:form.BackColor = [System.Drawing.Color]::FromArgb(26, 26, 46)
    $script:form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
    $script:form.MaximizeBox = $false
    
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Text = "SUPERENALOTTO"
    $titleLabel.Location = New-Object System.Drawing.Point(350, 15)
    $titleLabel.Size = New-Object System.Drawing.Size(200, 35)
    $titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
    $script:form.Controls.Add($titleLabel)
    
    $subtitleLabel = New-Object System.Windows.Forms.Label
    $subtitleLabel.Text = "Protocollo Sniper Quantitativo"
    $subtitleLabel.Location = New-Object System.Drawing.Point(350, 50)
    $subtitleLabel.Size = New-Object System.Drawing.Size(200, 20)
    $subtitleLabel.ForeColor = [System.Drawing.Color]::FromArgb(233, 69, 96)
    $subtitleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
    $script:form.Controls.Add($subtitleLabel)
    
    $script:statusLabel = New-Object System.Windows.Forms.Label
    $script:statusLabel.Location = New-Object System.Drawing.Point(10, 80)
    $script:statusLabel.Size = New-Object System.Drawing.Size(880, 25)
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
    $script:statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $script:statusLabel.Text = "Pronto"
    $script:form.Controls.Add($script:statusLabel)
    
    $leftPanel = New-Object System.Windows.Forms.Panel
    $leftPanel.Location = New-Object System.Drawing.Point(10, 110)
    $leftPanel.Size = New-Object System.Drawing.Size(420, 590)
    $leftPanel.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
    $leftPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
    $script:form.Controls.Add($leftPanel)
    
    $statsHeader = New-Object System.Windows.Forms.Label
    $statsHeader.Text = "STATISTICHE STORICHE"
    $statsHeader.Location = New-Object System.Drawing.Point(10, 10)
    $statsHeader.Size = New-Object System.Drawing.Size(200, 20)
    $statsHeader.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $statsHeader.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $leftPanel.Controls.Add($statsHeader)
    
    $script:statCount = New-Object System.Windows.Forms.Label
    $script:statCount.Location = New-Object System.Drawing.Point(20, 40)
    $script:statCount.Size = New-Object System.Drawing.Size(180, 20)
    $script:statCount.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statCount)
    
    $script:statMean = New-Object System.Windows.Forms.Label
    $script:statMean.Location = New-Object System.Drawing.Point(210, 40)
    $script:statMean.Size = New-Object System.Drawing.Size(180, 20)
    $script:statMean.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statMean)
    
    $script:statMedian = New-Object System.Windows.Forms.Label
    $script:statMedian.Location = New-Object System.Drawing.Point(20, 65)
    $script:statMedian.Size = New-Object System.Drawing.Size(180, 20)
    $script:statMedian.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statMedian)
    
    $script:statStd = New-Object System.Windows.Forms.Label
    $script:statStd.Location = New-Object System.Drawing.Point(210, 65)
    $script:statStd.Size = New-Object System.Drawing.Size(180, 20)
    $script:statStd.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statStd)
    
    $script:statQ1Q3 = New-Object System.Windows.Forms.Label
    $script:statQ1Q3.Location = New-Object System.Drawing.Point(20, 90)
    $script:statQ1Q3.Size = New-Object System.Drawing.Size(180, 20)
    $script:statQ1Q3.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statQ1Q3)
    
    $script:statRange = New-Object System.Windows.Forms.Label
    $script:statRange.Location = New-Object System.Drawing.Point(210, 90)
    $script:statRange.Size = New-Object System.Drawing.Size(180, 20)
    $script:statRange.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statRange)
    
    $script:statPrimes = New-Object System.Windows.Forms.Label
    $script:statPrimes.Location = New-Object System.Drawing.Point(20, 115)
    $script:statPrimes.Size = New-Object System.Drawing.Size(180, 20)
    $script:statPrimes.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statPrimes)
    
    $script:statExtremes = New-Object System.Windows.Forms.Label
    $script:statExtremes.Location = New-Object System.Drawing.Point(210, 115)
    $script:statExtremes.Size = New-Object System.Drawing.Size(180, 20)
    $script:statExtremes.ForeColor = [System.Drawing.Color]::White
    $leftPanel.Controls.Add($script:statExtremes)
    
    $genHeader = New-Object System.Windows.Forms.Label
    $genHeader.Text = "GENERATORE NUMERI"
    $genHeader.Location = New-Object System.Drawing.Point(10, 150)
    $genHeader.Size = New-Object System.Drawing.Size(200, 20)
    $genHeader.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $genHeader.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $leftPanel.Controls.Add($genHeader)
    
    $script:jackpotLabel = New-Object System.Windows.Forms.Label
    $script:jackpotLabel.Text = "Jackpot: N/D"
    $script:jackpotLabel.Location = New-Object System.Drawing.Point(10, 175)
    $script:jackpotLabel.Size = New-Object System.Drawing.Size(200, 25)
    $script:jackpotLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
    $script:jackpotLabel.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
    $leftPanel.Controls.Add($script:jackpotLabel)
    
    $btnGenerate = New-Object System.Windows.Forms.Button
    $btnGenerate.Text = "GENERA NUMERI"
    $btnGenerate.Location = New-Object System.Drawing.Point(10, 210)
    $btnGenerate.Size = New-Object System.Drawing.Size(395, 40)
    $btnGenerate.BackColor = [System.Drawing.Color]::FromArgb(233, 69, 96)
    $btnGenerate.ForeColor = [System.Drawing.Color]::White
    $btnGenerate.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnGenerate.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
    $btnGenerate.Add_Click({ Generate-Numbers })
    $leftPanel.Controls.Add($btnGenerate)
    
    $btnCheck = New-Object System.Windows.Forms.Button
    $btnCheck.Text = "VERIFICA VINCITA"
    $btnCheck.Location = New-Object System.Drawing.Point(10, 260)
    $btnCheck.Size = New-Object System.Drawing.Size(190, 35)
    $btnCheck.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
    $btnCheck.ForeColor = [System.Drawing.Color]::White
    $btnCheck.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnCheck.Add_Click({ Check-Win })
    $leftPanel.Controls.Add($btnCheck)
    
    $btnExport = New-Object System.Windows.Forms.Button
    $btnExport.Text = "ESPORTA REPORT"
    $btnExport.Location = New-Object System.Drawing.Point(215, 260)
    $btnExport.Size = New-Object System.Drawing.Size(190, 35)
    $btnExport.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
    $btnExport.ForeColor = [System.Drawing.Color]::White
    $btnExport.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnExport.Add_Click({ Export-Report })
    $leftPanel.Controls.Add($btnExport)
    
    $numbersHeader = New-Object System.Windows.Forms.Label
    $numbersHeader.Text = "SCHEDINE GENERATE"
    $numbersHeader.Location = New-Object System.Drawing.Point(10, 310)
    $numbersHeader.Size = New-Object System.Drawing.Size(200, 20)
    $numbersHeader.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $numbersHeader.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $leftPanel.Controls.Add($numbersHeader)
    
    $script:numbersPanel = New-Object System.Windows.Forms.Panel
    $script:numbersPanel.Location = New-Object System.Drawing.Point(10, 335)
    $script:numbersPanel.Size = New-Object System.Drawing.Size(395, 240)
    $script:numbersPanel.AutoScroll = $true
    $leftPanel.Controls.Add($script:numbersPanel)
    
    $rightPanel = New-Object System.Windows.Forms.Panel
    $rightPanel.Location = New-Object System.Drawing.Point(445, 110)
    $rightPanel.Size = New-Object System.Drawing.Size(435, 590)
    $rightPanel.BackColor = [System.Drawing.Color]::FromArgb(22, 33, 62)
    $rightPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
    $script:form.Controls.Add($rightPanel)
    
    $resultsHeader = New-Object System.Windows.Forms.Label
    $resultsHeader.Text = "ULTIME ESTRAZIONI"
    $resultsHeader.Location = New-Object System.Drawing.Point(10, 10)
    $resultsHeader.Size = New-Object System.Drawing.Size(200, 20)
    $resultsHeader.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $resultsHeader.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $rightPanel.Controls.Add($resultsHeader)
    
    $script:resultsListbox = New-Object System.Windows.Forms.ListBox
    $script:resultsListbox.Location = New-Object System.Drawing.Point(10, 35)
    $script:resultsListbox.Size = New-Object System.Drawing.Size(415, 250)
    $script:resultsListbox.BackColor = [System.Drawing.Color]::FromArgb(26, 26, 46)
    $script:resultsListbox.ForeColor = [System.Drawing.Color]::White
    $script:resultsListbox.Font = New-Object System.Drawing.Font("Consolas", 9)
    $rightPanel.Controls.Add($script:resultsListbox)
    
    $actionsHeader = New-Object System.Windows.Forms.Label
    $actionsHeader.Text = "AZIONI"
    $actionsHeader.Location = New-Object System.Drawing.Point(10, 300)
    $actionsHeader.Size = New-Object System.Drawing.Size(200, 20)
    $actionsHeader.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $actionsHeader.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $rightPanel.Controls.Add($actionsHeader)
    
    $btnUpdate = New-Object System.Windows.Forms.Button
    $btnUpdate.Text = "AGGIORNA CSV (API)"
    $btnUpdate.Location = New-Object System.Drawing.Point(10, 325)
    $btnUpdate.Size = New-Object System.Drawing.Size(200, 35)
    $btnUpdate.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
    $btnUpdate.ForeColor = [System.Drawing.Color]::White
    $btnUpdate.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnUpdate.Add_Click({ Update-CSV })
    $rightPanel.Controls.Add($btnUpdate)
    
    $btnRefresh = New-Object System.Windows.Forms.Button
    $btnRefresh.Text = "RICALCOLA STATS"
    $btnRefresh.Location = New-Object System.Drawing.Point(220, 325)
    $btnRefresh.Size = New-Object System.Drawing.Size(200, 35)
    $btnRefresh.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
    $btnRefresh.ForeColor = [System.Drawing.Color]::White
    $btnRefresh.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnRefresh.Add_Click({ Load-Data; $script:statusLabel.Text = "Dati ricaricati!" })
    $rightPanel.Controls.Add($btnRefresh)
    
$btnScheduler = New-Object System.Windows.Forms.Button
$btnScheduler.Text = "ATTIVA SCHEDULER"
$btnScheduler.Location = New-Object System.Drawing.Point(10, 370)
$btnScheduler.Size = New-Object System.Drawing.Size(200, 35)
$btnScheduler.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
$btnScheduler.ForeColor = [System.Drawing.Color]::White
$btnScheduler.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
$btnScheduler.Add_Click({ Setup-Scheduler })
$rightPanel.Controls.Add($btnScheduler)

$btnSettings = New-Object System.Windows.Forms.Button
$btnSettings.Text = "IMPOSTAZIONI API"
$btnSettings.Location = New-Object System.Drawing.Point(220, 370)
$btnSettings.Size = New-Object System.Drawing.Size(200, 35)
$btnSettings.BackColor = [System.Drawing.Color]::FromArgb(15, 52, 96)
$btnSettings.ForeColor = [System.Drawing.Color]::White
$btnSettings.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
$btnSettings.Add_Click({ Show-Settings })
$rightPanel.Controls.Add($btnSettings)
    
    $infoPanel = New-Object System.Windows.Forms.Panel
    $infoPanel.Location = New-Object System.Drawing.Point(10, 420)
    $infoPanel.Size = New-Object System.Drawing.Size(415, 160)
    $infoPanel.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 50)
    $infoPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
    $rightPanel.Controls.Add($infoPanel)
    
    $infoText = New-Object System.Windows.Forms.Label
    $infoText.Text = "ISTRUZIONI`n`n" +
                    "1. Clicca 'AGGIORNA CSV' per scaricare nuove estrazioni`n" +
                    "2. Clicca 'GENERA NUMERI' per creare schedine`n" +
                    "3. Gioca le schedine il giorno dell'estrazione`n" +
                    "4. Usa 'VERIFICA VINCITA' per controllare i risultati`n" +
                    "5. 'IMPOSTAZIONI API' per configurare la chiave`n" +
                    "6. 'ATTIVA SCHEDULER' per esecuzione automatica"
    $infoText.Location = New-Object System.Drawing.Point(10, 10)
    $infoText.Size = New-Object System.Drawing.Size(395, 140)
    $infoText.ForeColor = [System.Drawing.Color]::FromArgb(180, 180, 180)
    $infoText.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $infoPanel.Controls.Add($infoText)
    
    $script:form.Controls.Add($rightPanel)
}

function Show-Settings {
    $settingsForm = New-Object System.Windows.Forms.Form
    $settingsForm.Text = "Impostazioni API"
    $settingsForm.Size = New-Object System.Drawing.Size(450, 280)
    $settingsForm.StartPosition = "CenterParent"
    $settingsForm.TopMost = $true
    $settingsForm.BackColor = [System.Drawing.Color]::FromArgb(26, 26, 46)
    
    $lblTitle = New-Object System.Windows.Forms.Label
    $lblTitle.Text = "CONFIGURAZIONE API"
    $lblTitle.Location = New-Object System.Drawing.Point(120, 15)
    $lblTitle.Size = New-Object System.Drawing.Size(200, 25)
    $lblTitle.ForeColor = [System.Drawing.Color]::FromArgb(0, 217, 255)
    $lblTitle.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
    $settingsForm.Controls.Add($lblTitle)
    
    $lblUrl = New-Object System.Windows.Forms.Label
    $lblUrl.Text = "URL API:"
    $lblUrl.Location = New-Object System.Drawing.Point(20, 55)
    $lblUrl.Size = New-Object System.Drawing.Size(80, 20)
    $lblUrl.ForeColor = [System.Drawing.Color]::White
    $settingsForm.Controls.Add($lblUrl)
    
    $txtUrl = New-Object System.Windows.Forms.TextBox
    $txtUrl.Text = $script:apiUrl
    $txtUrl.Location = New-Object System.Drawing.Point(110, 55)
    $txtUrl.Size = New-Object System.Drawing.Size(300, 25)
    $txtUrl.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 60)
    $txtUrl.ForeColor = [System.Drawing.Color]::White
    $settingsForm.Controls.Add($txtUrl)
    
    $lblKey = New-Object System.Windows.Forms.Label
    $lblKey.Text = "API Key:"
    $lblKey.Location = New-Object System.Drawing.Point(20, 90)
    $lblKey.Size = New-Object System.Drawing.Size(80, 20)
    $lblKey.ForeColor = [System.Drawing.Color]::White
    $settingsForm.Controls.Add($lblKey)
    
    $txtKey = New-Object System.Windows.Forms.TextBox
    $txtKey.Text = $script:apiKey
    $txtKey.Location = New-Object System.Drawing.Point(110, 90)
    $txtKey.Size = New-Object System.Drawing.Size(300, 25)
    $txtKey.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 60)
    $txtKey.ForeColor = [System.Drawing.Color]::White
    $txtKey.UseSystemPasswordChar = $true
    $settingsForm.Controls.Add($txtKey)
    
    $lblLottery = New-Object System.Windows.Forms.Label
    $lblLottery.Text = "Lottery ID:"
    $lblLottery.Location = New-Object System.Drawing.Point(20, 125)
    $lblLottery.Size = New-Object System.Drawing.Size(80, 20)
    $lblLottery.ForeColor = [System.Drawing.Color]::White
    $settingsForm.Controls.Add($lblLottery)
    
    $txtLottery = New-Object System.Windows.Forms.TextBox
    $txtLottery.Text = $script:lotteryId
    $txtLottery.Location = New-Object System.Drawing.Point(110, 125)
    $txtLottery.Size = New-Object System.Drawing.Size(100, 25)
    $txtLottery.BackColor = [System.Drawing.Color]::FromArgb(40, 40, 60)
    $txtLottery.ForeColor = [System.Drawing.Color]::White
    $settingsForm.Controls.Add($txtLottery)
    
    $btnSave = New-Object System.Windows.Forms.Button
    $btnSave.Text = "SALVA"
    $btnSave.Location = New-Object System.Drawing.Point(110, 170)
    $btnSave.Size = New-Object System.Drawing.Size(100, 35)
    $btnSave.BackColor = [System.Drawing.Color]::FromArgb(0, 180, 0)
    $btnSave.ForeColor = [System.Drawing.Color]::White
    $btnSave.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnSave.Add_Click({
        $script:apiUrl = $txtUrl.Text
        $script:apiKey = $txtKey.Text
        $script:lotteryId = [int]$txtLottery.Text
        Save-Config
        $settingsForm.Close()
        $script:statusLabel.Text = "Configurazione salvata!"
    })
    $settingsForm.Controls.Add($btnSave)
    
    $btnCancel = New-Object System.Windows.Forms.Button
    $btnCancel.Text = "ANNULLA"
    $btnCancel.Location = New-Object System.Drawing.Point(220, 170)
    $btnCancel.Size = New-Object System.Drawing.Size(100, 35)
    $btnCancel.BackColor = [System.Drawing.Color]::FromArgb(180, 50, 50)
    $btnCancel.ForeColor = [System.Drawing.Color]::White
    $btnCancel.FlatStyle = [System.Windows.Forms.FlatStyle]::Popup
    $btnCancel.Add_Click({ $settingsForm.Close() })
    $settingsForm.Controls.Add($btnCancel)
    
    $lblInfo = New-Object System.Windows.Forms.Label
    $lblInfo.Text = "L'API Key viene salvata localmente in config.json"
    $lblInfo.Location = New-Object System.Drawing.Point(20, 215)
    $lblInfo.Size = New-Object System.Drawing.Size(400, 20)
    $lblInfo.ForeColor = [System.Drawing.Color]::FromArgb(150, 150, 150)
    $lblInfo.Font = New-Object System.Drawing.Font("Segoe UI", 8)
    $settingsForm.Controls.Add($lblInfo)
    
    $settingsForm.ShowDialog()
}

function Export-Report {
    if ($script:records.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Nessun dato da esportare!", "Errore", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        return
    }
    
    $s = $script:stats
    $report = @"
========================================
SUPERENALOTTO - REPORT
Generato: $(Get-Date -Format "dd/MM/yyyy HH:mm")
========================================

DATI STORICI
Estrazioni: $($s.Count)
Periodo: $($script:records[0].Date) - $($script:records[-1].Date)

STATISTICHE SOMMA
Media: $($s.Mean)
Mediana: $($s.Median)
Std Dev: $($s.Std)
Q1: $($s.Q1) | Q3: $($s.Q3)
Range: $($s.Min) - $($s.Max)

DISTRIBUZIONE NUMERI
Primi: $($s.Primes)%
Estremi (76-90): $($s.Extremes)%

ULTIME 10 ESTRAZIONI
"@
    
    foreach ($r in ($script:records | Select-Object -Last 10)) {
        $report += "`n$($r.Date): $($r.Nums -join ' ')"
    }
    
    $report += @"

========================================
NOTE OPERATIVE
Target somma: $([int]($s.Mean - 30)) - $([int]($s.Mean + 30))
Fascia ottimale: 260-299
Giorni estrazione: Martedi, Giovedi, Venerdi, Sabato
Budget consigliato: EUR 1-2/estrazione
========================================
"@
    
    $filename = "report_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    $report | Out-File -FilePath (Join-Path $scriptDir $filename) -Encoding UTF8
    
    [System.Windows.Forms.MessageBox]::Show("Report salvato in:`n$filename", "Esportazione", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
}

Load-Data
Create-Form
Update-StatsUI
Update-ResultsUI
Get-Jackpot

$today = (Get-Date).DayOfWeek.ToString()
if ($today -in $drawDays) {
    $script:statusLabel.Text = "OGGI E' $today - GIORNO DI ESTRAZIONE!"
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 136)
} else {
    $script:statusLabel.Text = "Prossima estrazione: "
    $script:statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 204, 0)
}

$script:form.ShowDialog()
