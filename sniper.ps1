$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$lotteryId = 712
$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
$trackingPath = "C:\Users\Siviglino\Desktop\Superenalotto\tracking.csv"
$apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=$lotteryId"

$today = Get-Date -Format "yyyy-MM-dd"
$dayOfWeekName = (Get-Date).DayOfWeek

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUPERENALOTTO - PROTOCOLLO SNIPER" -ForegroundColor Cyan
Write-Host "  Data: $today ($dayOfWeekName)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$drawDays = @("Tuesday", "Thursday", "Friday", "Saturday")
if ($dayOfWeekName -notin $drawDays) {
    Write-Host "NESSUNA GIOCATA: Oggi non e giorno di estrazione" -ForegroundColor Yellow
    Write-Host "Giorni di estrazione: Mar, Gio, Ven, Sab" -ForegroundColor Gray
    exit 0
}

Write-Host "[1] Fetching jackpot..." -ForegroundColor Green
try {
    $headers = @{ "X-API-KEY" = $apiKey }
    $response = Invoke-RestMethod -Uri "$apiUrl?lottery_id=$lotteryId" -Headers $headers -TimeoutSec 10
    $latestResult = $response.results[0]
    $jackpot = $latestResult.jackpot
    $lastDrawDate = $latestResult.draw_date
    $lastDrawBalls = $latestResult.balls
    $lastJolly = if ($latestResult.ball_bonus) { $latestResult.ball_bonus[0] } else { 0 }
    $lastSuperstar = if ($latestResult.ball_bonus -and $latestResult.ball_bonus.Count -gt 1) { $latestResult.ball_bonus[1] } else { 0 }
    Write-Host "  Ultima estrazione: $lastDrawDate" -ForegroundColor White
    Write-Host "  Numeri: $($lastDrawBalls -join ', ')" -ForegroundColor White
    Write-Host "  Jolly: $lastJolly | Superstar: $lastSuperstar" -ForegroundColor White
    Write-Host "  Jackpot: EUR $jackpot" -ForegroundColor Yellow
} catch {
    Write-Host "  ERRORE API: $($_.Exception.Message)" -ForegroundColor Red
    $jackpot = 0
}

$budgetDaily = 2.00
$numSchedine = 1

if ($jackpot -ge 100000000) {
    $numSchedine = 2
    Write-Host "[TRIGGER] Jackpot >= 100M - Giocata aumentata" -ForegroundColor Magenta
} elseif ($jackpot -ge 50000000) {
    $numSchedine = 2
} elseif ($jackpot -ge 10000000) {
    $numSchedine = 2
}

Write-Host ""
Write-Host "[2] Generazione numeri..." -ForegroundColor Green

$csvContent = Get-Content $csvPath
$records = @()
foreach ($line in ($csvContent | Select-Object -Skip 1)) {
    $parts = $line -split ','
    if ($parts.Count -ge 7) {
        $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
        $sum = ($nums | Measure-Object -Sum).Sum
        $records += [PSCustomObject]@{
            Date = $parts[0]
            N1 = $nums[0]; N2 = $nums[1]; N3 = $nums[2]
            N4 = $nums[3]; N5 = $nums[4]; N6 = $nums[5]
            Sum = $sum
        }
    }
}

$sums = $records | Select-Object -ExpandProperty Sum
$mean = ($sums | Measure-Object -Average).Average
$targetLow = [int]($mean - 30)
$targetHigh = [int]($mean + 30)

$generatedSchedine = @()
for ($s = 0; $s -lt $numSchedine; $s++) {
    $attempts = 0
    do {
        $nums = @()
        while ($nums.Count -lt 6) {
            $n = Get-Random -Minimum 1 -Maximum 91
            if ($n -notin $nums) { $nums += $n }
        }
        $sum = ($nums | Measure-Object -Sum).Sum
        
        $decades = @{}
        foreach ($n in $nums) {
            $d = [math]::Floor($n / 10)
            $decades[$d] = ++$decades[$d]
        }
        $maxDecade = ($decades.Values | Measure-Object -Maximum).Maximum
        
        $highCount = ($nums | Where-Object { $_ -gt 31 }).Count
        $veryHighCount = ($nums | Where-Object { $_ -gt 80 }).Count
        
        $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and ($maxDecade -le 2) -and ($veryHighCount -le 1)
        $attempts++
    } while (-not $valid -and $attempts -lt 1000)
    
    if ($valid) {
        $sortedNums = $nums | Sort-Object
        $generatedSchedine += [PSCustomObject]@{
            Schedina = $s + 1
            Numeri = $sortedNums -join '-'
            Somma = $sum
        }
    }
}

Write-Host "  Target somma: $targetLow - $targetHigh (media: $([math]::Round($mean, 0)))"
Write-Host ""
foreach ($sched in $generatedSchedine) {
    Write-Host "  SCHEDINA $($sched.Schedina): $($sched.Numeri) [somma: $($sched.Somma)]" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "[3] Prossime estrazioni:" -ForegroundColor Green
$drawDaysMap = @{
    "Sunday" = 0; "Monday" = 0; "Tuesday" = 1; "Wednesday" = 0
    "Thursday" = 1; "Friday" = 1; "Saturday" = 1
}
$drawDayNames = @("Tuesday", "Thursday", "Friday", "Saturday")
$todayDow = $dayOfWeekName.ToString()
$todayIdx = $drawDayNames.IndexOf($todayDow)

for ($i = 1; $i -le 4; $i++) {
    $nextIdx = ($todayIdx + $i) % 4
    $daysToAdd = 1
    $checkDate = (Get-Date).AddDays($daysToAdd)
    while ($checkDate.DayOfWeek.ToString() -ne $drawDayNames[$nextIdx]) {
        $daysToAdd++
        $checkDate = (Get-Date).AddDays($daysToAdd)
        if ($daysToAdd -gt 14) { break }
    }
    $dateStr = $checkDate.ToString("yyyy-MM-dd")
    Write-Host "  - $dateStr ($($checkDate.DayOfWeek))" -ForegroundColor Gray
}

if ($generatedSchedine.Count -gt 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ISTRUZIONI DI GIOCATA" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Gioca $($generatedSchedine.Count) schedina/e per un totale di EUR $($generatedSchedine.Count).00" -ForegroundColor White
    Write-Host "  Jackpot attuale: EUR $jackpot" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    
    if (-not (Test-Path $trackingPath)) {
        "data,giornata,budget_speso,schede,numeri,somma,jackpot" | Out-File -FilePath $trackingPath -Encoding UTF8
    }
    
    $numsStr = $generatedSchedine.Numeri -join ";"
    $trackingLine = "$today,$dayOfWeekName,$($generatedSchedine.Count).00,$($generatedSchedine.Count),$numsStr,$($generatedSchedine[0].Somma),$jackpot"
    Add-Content -Path $trackingPath -Value $trackingLine
    Write-Host "  Tracking aggiornato." -ForegroundColor Gray
} else {
    Write-Host "  ERRORE: Impossibile generare schedine valide" -ForegroundColor Red
}

Write-Host ""
Write-Host "Fine protocollo sniper - $today" -ForegroundColor DarkGray
