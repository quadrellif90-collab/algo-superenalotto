# Run-Backtest.ps1
# Script di test per generare dati backtest
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "backtest_results.txt"

$records = @()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $nums = @([int]($parts[2].Trim()), [int]($parts[3].Trim()), [int]($parts[4].Trim()),
                       [int]($parts[5].Trim()), [int]($parts[6].Trim()), [int]($parts[7].Trim()))
            if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                $sum = ($nums | Measure-Object -Sum).Sum
                $records += [PSCustomObject]@{
                    Date = $parts[0]
                    Nums = $nums
                    Sum = $sum
                }
            }
        } catch {}
    }
}

Write-Host "Dataset: $($records.Count) estrazioni"

function Test-Prime($n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) { if ($n % $i -eq 0) { return $false } }
    return $true
}

function Generate-Schedina {
    $sums = $records | ForEach-Object { $_.Sum }
    $mean = ($sums | Measure-Object -Average).Average
    while ($true) {
        $nums = @()
        while ($nums.Count -lt 2) {
            $n = Get-Random -Minimum 1 -Maximum 91
            if ($n -notin $nums) { $nums += $n }
        }
        $nums = $nums | Sort-Object
        $decades = @{}
        foreach ($nn in $nums) { $decades[[math]::Floor($nn / 10)]++ }
        $maxDecade = ($decades.Values | Measure-Object -Maximum).Maximum
        if ($nums.All({Test-Prime $_}) -or $nums.All({$_ % 2 -ne 0})) { continue }
    }
    return $nums
}

$sums = $records | ForEach-Object { $_.Sum }
$mean = ($sums | Measure-Object -Average).Average
$targetLow = [int]($mean - 20)
$targetHigh = [int]($mean + 20)

Write-Host "Mean: $mean | TargetRange: $targetLow-$targetHigh"

# Backtest: 800 estrazioni, 2 schedine
$results = @{
    drawsTested = 0
    totalTickets = 0
    match2 = 0; match3 = 0; match4 = 0; match5 = 0; match6 = 0
    totalPrizeWon = 0
    totalSpent = 0
    netProfit = 0
}

for ($i = $records.Count - 1; $i -ge 0; $i--) {
    if ($results.drawsTested -ge 800) { break }
    $draw = $records[$i]
    $totalSpent++
    $ticket = Generate-Schedina
    $matches = ($ticket | Where-Object { $_ -in $draw.Nums }).Count
    switch ($matches) {
        2 { $results.match2++ }
        3 { $results.match3++; $totalPrizeWon += 10 }
        4 { $results.match4++; $totalPrizeWon += 100 }
        5 { $results.match5++; $totalPrizeWon += 10000 }
        6 { $results.match6++; $totalPrizeWon += 10000000 }
    }
    $results.totalTickets++
    $results.drawsTested++
}

$results.netProfit = $results.totalPrizeWon - $results.totalSpent
$results.avgMatches = if ($results.drawsTested -gt 0) { [math]::Round(($results.match2+$results.match3+$results.match4+$results.match5+$results.match6)/$results.drawsTested, 4) } else { 0 }

Write-Host "`n=== BACKTEST CONCLUSIVO (2 schedine al giorno) ===" -ForegroundColor Green
Write-Host "Estrazioni testate: $($results.drawsTested)"
Write-Host "Biglietti: $($results.totalTickets)"
Write-Host "Speso: EUR $($results.totalSpent)"
Write-Host "Vinto: EUR $($results.totalPrizeWon)"
Write-Host "Netto: EUR $($results.netProfit)"
Write-Host "Match 2: $($results.match2)"
Write-Host "Match 3: $($results.match3)"
Write-Host "Match 4: $($results.match4)"
Write-Host "Match 5: $($results.match5)"
Write-Host "Match 6: $($results.match6)"
Write-Host "Media match/estrazione: $($results.avgMatches)"

# Salva risultato in JSON per l'app
$resultJson = $results | ConvertTo-Json
Set-Content -Path (Join-Path $scriptDir "backtest_result.json") -Value $resultJson