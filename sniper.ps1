# sniper.ps1 - Sniper Protocol Daily v3 (CORRETTO)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$trackingPath = Join-Path $scriptDir "tracking.csv"
$configPath = Join-Path $scriptDir "config.json"

# Carica configurazione da file o usa default
$apiKey = "170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d"
$lotteryId = 712
$apiUrl = "https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=$lotteryId"

if (Test-Path $configPath) {
    try {
        $jsonConfig = Get-Content $configPath -Raw | ConvertFrom-Json
        if ($jsonConfig.apiKey) { $apiKey = $jsonConfig.apiKey }
        if ($jsonConfig.lotteryId) { $lotteryId = $jsonConfig.lotteryId }
        if ($jsonConfig.apiUrl) { $apiUrl = $jsonConfig.apiUrl }
    } catch { Write-Host "Warning: config.json parsing failed, using defaults" }
}

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
    $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 10 -ErrorAction Stop
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
    Write-Host "  Usando CSV locale..." -ForegroundColor Yellow
    $jackpot = 0
    $lastDrawDate = ""
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

# Carica dati dal CSV
$csvContent = Get-Content $csvPath
$records = @()
foreach ($line in ($csvContent | Select-Object -Skip 1)) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], 
                       [int]$parts[5], [int]$parts[6], [int]$parts[7])
            if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                $records += [PSCustomObject]@{
                    Date = $parts[0]
                    N1 = $nums[0]; N2 = $nums[1]; N3 = $nums[2]
                    N4 = $nums[3]; N5 = $nums[4]; N6 = $nums[5]
                    Sum = ($nums | Measure-Object -Sum).Sum
                }
            }
        } catch {}
    }
}

if ($records.Count -eq 0) {
    Write-Host "ERRORE: Nessun record nel CSV" -ForegroundColor Red
    exit 1
}

$sums = $records | Select-Object -ExpandProperty Sum
$mean = ($sums | Measure-Object -Average).Average
$targetLow = [int]($mean - 30)
$targetHigh = [int]($mean + 30)

Write-Host "  Media: $([math]::Round($mean, 1))" -ForegroundColor Gray
Write-Host "  Target somma: $targetLow - $targetHigh" -ForegroundColor Gray
Write-Host ""

$generatedSchedine = @()

# Funzione generazione
function Generate-Schedina-Internal {
    param($mean, $targetLow, $targetHigh)
    
    for ($attempts = 0; $attempts -lt 1000; $attempts++) {
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
        
        $valid = ($sum -ge $targetLow -and $sum -le $targetHigh) -and 
                 ($maxDecade -le 2) -and 
                 ($veryHigh -le 1)
        
        if ($valid) {
            return @{
                Nums = $nums
                Sum = $sum
            }
        }
    }
    return $null
}

# Generazione schedine
for ($s = 0; $s -lt $numSchedine; $s++) {
    $result = Generate-Schedina-Internal -mean $mean -targetLow $targetLow -targetHigh $targetHigh
    if ($result) {
        $generatedSchedine += [PSCustomObject]@{
            Schedina = $s + 1
            Numeri = ($result.Nums -join '-')
            Somma = $result.Sum
            Nums = $result.Nums
        }
    }
}

Write-Host "[3] Schedine generate:" -ForegroundColor Green
foreach ($sched in $generatedSchedine) {
    $color = if ($sched.Somma -ge 240 -and $sched.Somma -le 320) { "Cyan" } else { "Red" }
    Write-Host "  SCHEDINA $($sched.Schedina): $($sched.Numeri) [somma: $($sched.Somma)]" -ForegroundColor $color
}

Write-Host ""
Write-Host "[4] Prossime estrazioni:" -ForegroundColor Green
$drawDaysMap = @{ 'Sunday' = 0; 'Monday' = 0; 'Tuesday' = 1; 'Wednesday' = 0
                  'Thursday' = 1; 'Friday' = 1; 'Saturday' = 1 }
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
    Write-Host "  Jackpot attuale: EUR $([math]::Round($jackpot / 1000000, 1))M" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Inizializza tracking se necessario
    if (-not (Test-Path $trackingPath)) {
        "data,giornata,budget,schedine,numeri,somma,jackpot,verificato" | Out-File -FilePath $trackingPath -Encoding UTF8
    }
    
    # Aggiungi al tracking
    foreach ($sched in $generatedSchedine) {
        $trackingLine = "$today,$dayOfWeekName,1.00,1,$($sched.Numeri),$($sched.Somma),$jackpot,no"
        Add-Content -Path $trackingPath -Value $trackingLine
    }
    Write-Host "  Tracking aggiornato." -ForegroundColor Gray
    
    # Aggiorna contatore giornaliero
    $todayDate = Get-Date -Format "yyyy-MM-dd"
    $dailyLines = @()
    if (Test-Path $dailyLimitPath) { $dailyLines = Get-Content $dailyLimitPath -Encoding UTF8 }
    $found = $false
    $newDailyLines = @()
    foreach ($line in $dailyLines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split ','
        if ($parts[0] -eq $todayDate) {
            $count = 1
            if ($parts.Count -ge 2) { [void][int]::TryParse($parts[1], [ref]$count); $count++ }
            $newDailyLines += "$todayDate,$count"
            $found = $true
        } else { $newDailyLines += $line }
    }
    if (-not $found) { $newDailyLines += "$todayDate,1" }
    $newDailyLines | Out-File -FilePath $dailyLimitPath -Encoding UTF8
    
} else {
    Write-Host "  ERRORE: Impossibile generare schedine valide" -ForegroundColor Red
}

Write-Host ""
Write-Host "Fine protocollo sniper - $today" -ForegroundColor DarkGray