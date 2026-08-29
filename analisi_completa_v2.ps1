# analisi_completa.ps1
# PowerShell 5.1 - analisi statistica completa su superenalotto.csv
# Genera analisi_completa.json

$ErrorActionPreference = "Stop"

$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
$outputPath = "C:\Users\Siviglino\Desktop\Superenalotto\analisi_completa.json"

# --- Caricamento dati ---
$records = @()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    $parts = $line -split ','
    if ($parts.Count -lt 9) { continue }
    try {
        $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4],
                   [int]$parts[5], [int]$parts[6], [int]$parts[7])
        foreach ($n in $nums) {
            if ($n -lt 1 -or $n -gt 90) { continue }
        }
        $jolly = [int]$parts[8]
        $star = 0
        if ($parts.Count -gt 9 -and $parts[9].Trim() -ne "") {
            $star = [int]$parts[9]
        }
        $records += [PSCustomObject]@{
            Date  = [string]$parts[0]
            Conc  = [string]$parts[1]
            N1    = $nums[0]
            N2    = $nums[1]
            N3    = $nums[2]
            N4    = $nums[3]
            N5    = $nums[4]
            N6    = $nums[5]
            Nums  = $nums
            Sum   = ($nums | Measure-Object -Sum).Sum
            Jolly = $jolly
            Star  = $star
        }
    } catch {
        # salta righe malformate
    }
}

Write-Host "Caricati $($records.Count) record validi"

# --- Helper ---
function Test-Prime([int]$n) {
    if ($n -lt 2) { return $false }
    if ($n -eq 2) { return $true }
    if ($n % 2 -eq 0) { return $false }
    for ([int]$i = 3; $i -le [int][Math]::Sqrt($n); $i += 2) {
        if ($n % $i -eq 0) { return $false }
    }
    return $true
}

# --- Calcolo metriche ---
$sums      = $records | ForEach-Object { $_.Sum }
$allNums   = $records | ForEach-Object { $_.Nums } | ForEach-Object { $_ }
$sumsSorted = $sums | Sort-Object
$n         = $sumsSorted.Count
$totalNums = $n * 6

$mean    = ($sums | Measure-Object -Average).Average
$median  = $sumsSorted[[int]($n / 2)]
$min     = ($sums | Measure-Object -Minimum).Minimum
$max     = ($sums | Measure-Object -Maximum).Maximum
$sumSq   = 0
foreach ($s in $sums) { $sumSq += [Math]::Pow($s - $mean, 2) }
$std     = [Math]::Sqrt($sumSq / $n)
$q1      = $sumsSorted[[int]($n * 0.25)]
$q3      = $sumsSorted[[int]($n * 0.75)]

$numFreq  = @{}
foreach ($n in $allNums) { $numFreq[$n] = $numFreq[$n] + 1 }
$topNums  = $numFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20

$sumFreq  = @{}
foreach ($s in $sums) { $sumFreq[$s] = $sumFreq[$s] + 1 }
$topSums  = $sumFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10

$primeCount = ($allNums | Where-Object { Test-Prime $_ }).Count

$extremeCount = ($allNums | Where-Object { $_ -ge 76 }).Count
$gt31Count    = ($allNums | Where-Object { $_ -gt 31 }).Count
$gt80Count    = ($allNums | Where-Object { $_ -gt 80 }).Count
$evenCount    = ($allNums | Where-Object { $_ % 2 -eq 0 }).Count

$primePct    = [Math]::Round($primeCount / $totalNums * 100, 2)
$extremePct  = [Math]::Round($extremeCount / $totalNums * 100, 2)
$gt31Pct     = [Math]::Round($gt31Count / $totalNums * 100, 2)
$gt80Pct     = [Math]::Round($gt80Count / $totalNums * 100, 2)
$evenPct     = [Math]::Round($evenCount / $totalNums * 100, 2)

$finalDigit  = @{}
foreach ($n in $allNums) { $finalDigit[$n % 10] = $finalDigit[$n % 10] + 1 }
$finalDigitPct = @{}
foreach ($d in 0..9) { $finalDigitPct[$d] = [Math]::Round($finalDigit[$d] / $totalNums * 100, 2) }

$decadeDist  = @{}
foreach ($n in $allNums) { $decadeDist[[Math]::Floor($n / 10)] = $decadeDist[[Math]::Floor($n / 10)] + 1 }
$decadePct   = @{}
foreach ($d in 0..8) { $decadePct[$d] = [Math]::Round($decadeDist[$d] / $totalNums * 100, 2) }

$jollyFreq = @{}; $jollyTotal = 0
foreach ($r in $records) {
    if ($r.Jolly -gt 0) { $jollyFreq[$r.Jolly] = $jollyFreq[$r.Jolly] + 1; $jollyTotal++ }
}

$starFreq = @{}; $starTotal = 0
foreach ($r in $records) {
    if ($r.Star -gt 0) { $starFreq[$r.Star] = $starFreq[$r.Star] + 1; $starTotal++ }
}

$yearDist = @{}
foreach ($r in $records) {
    $year = [int]$r.Date.Substring(0, 4)
    $yearDist[$year] = $yearDist[$year] + 1
}

# --- Costruzione JSON con chiavi stringa (PowerShell 5.1 compatibile) ---
$analysis = [PSCustomObject]@{
    n                = $n
    mean             = [Math]::Round($mean, 2)
    median           = $median
    stddev           = [Math]::Round($std, 2)
    q1               = $q1
    q3               = $q3
    min              = $min
    max              = $max
    range            = $max - $min
    iqr              = $q3 - $q1
    primePct         = $primePct
    extremePct       = $extremePct
    gt31Pct          = $gt31Pct
    gt80Pct          = $gt80Pct
    evenPct          = $evenPct
    primeCount       = $primeCount
    extremeCount     = $extremeCount
    gt31Count        = $gt31Count
    gt80Count        = $gt80Count
    evenCount        = $evenCount
    totalNumbers     = $totalNums
    finalDigitPct    = $finalDigitPct
    decadePct        = $decadePct
    topNumbers       = $topNums
    topSums          = $topSums
    jollyFreq        = $jollyFreq
    starFreq         = $starFreq
    jollyTotal       = $jollyTotal
    starTotal        = $starTotal
    yearDist         = $yearDist
    firstDate        = $records[0].Date
    lastDate         = $records[-1].Date
}

# Converti hashtable con chiavi non-stringa in stringhe per JSON compatibile
$fdHashStr = @{}
foreach ($kv in $analysis.finalDigitPct.GetEnumerator()) { $fdHashStr["$($kv.Name)"] = $kv.Value }

$deHashStr = @{}
foreach ($kv in $analysis.decadePct.GetEnumerator()) { $deHashStr["$($kv.Name)"] = $kv.Value }

$tnHashStr = @{}
foreach ($kv in $analysis.topNumbers.GetEnumerator()) { $tnHashStr["$($kv.Name)"] = $kv.Value }

$tsHashStr = @{}
foreach ($kv in $analysis.topSums.GetEnumerator()) { $tsHashStr["$($kv.Name)"] = $kv.Value }

$jfHashStr = @{}
foreach ($kv in $analysis.jollyFreq.GetEnumerator()) { $jfHashStr["$($kv.Name)"] = $kv.Value }

$sfHashStr = @{}
foreach ($kv in $analysis.starFreq.GetEnumerator()) { $sfHashStr["$($kv.Name)"] = $kv.Value }

$ydHashStr = @{}
foreach ($kv in $analysis.yearDist.GetEnumerator()) { $ydHashStr["$($kv.Name)"] = $kv.Value }

# Ricostruisci oggetto con hashtable stringhe
$analysisJson = [PSCustomObject]@{
    n                = $analysis.n
    mean             = $analysis.mean
    median           = $analysis.median
    stddev           = $analysis.stddev
    q1               = $analysis.q1
    q3               = $analysis.q3
    min              = $analysis.min
    max              = $analysis.max
    range            = $analysis.range
    iqr              = $analysis.iqr
    primePct         = $analysis.primePct
    extremePct       = $analysis.extremePct
    gt31Pct          = $analysis.gt31Pct
    gt80Pct          = $analysis.gt80Pct
    evenPct          = $analysis.evenPct
    primeCount       = $analysis.primeCount
    extremeCount     = $analysis.extremeCount
    gt31Count        = $analysis.gt31Count
    gt80Count        = $analysis.gt80Count
    evenCount        = $analysis.evenCount
    totalNumbers     = $analysis.totalNumbers
    finalDigitPct    = $fdHashStr
    decadePct        = $deHashStr
    topNumbers       = $tnHashStr
    topSums          = $tsHashStr
    jollyFreq        = $jfHashStr
    starFreq         = $sfHashStr
    jollyTotal       = $analysis.jollyTotal
    starTotal        = $analysis.starTotal
    yearDist         = $ydHashStr
    firstDate        = $analysis.firstDate
    lastDate         = $analysis.lastDate
} | ConvertTo-Json -Depth 5

Set-Content -Path $outputPath -Value $analysisJson -Encoding UTF8

# --- Output formattato ---
Write-Host "`n=== ANALISI COMPLETA - SUPERENALOTTO ===" -ForegroundColor Cyan
Write-Host "Dataset: $n estrazioni ($($records[0].Date) - $($records[-1].Date))"
Write-Host ""
Write-Host "--- SOMME 6 NUMERI ---"
Write-Host "Media: $($analysis.mean) | Mediana: $($analysis.median)"
Write-Host "Std Dev: $($analysis.stddev)"
Write-Host "Q1: $($analysis.q1) | Q3: $($analysis.q3)"
Write-Host "Min: $($analysis.min) | Max: $($analysis.max) | Range: $($analysis.range) | IQR: $($analysis.iqr)"
Write-Host ""
Write-Host "--- NUMERI ---"
Write-Host "Primi: ${analysis.primePct}% ($($analysis.primeCount) su $($analysis.totalNumbers))"
Write-Host "Estremi (>75): ${analysis.extremePct}% ($($analysis.extremeCount) su $($analysis.totalNumbers))"
Write-Host ">31: ${analysis.gt31Pct}% ($($analysis.gt31Count) su $($analysis.totalNumbers))"
Write-Host ">80: ${analysis.gt80Pct}% ($($analysis.gt80Count) su $($analysis.totalNumbers))"
Write-Host "Pari: ${analysis.evenPct}% ($($analysis.evenCount) su $($analysis.totalNumbers))"
Write-Host ""
Write-Host "--- CIFRA FINALE ---"
foreach ($d in 0..9) { Write-Host "  Digit " $d ": " $analysis.finalDigitPct[$d] "%" }
Write-Host ""
Write-Host "--- DECADE ---"
foreach ($d in 0..8) {
    $start = $d * 10 + 1
    $end   = $start + 9
    Write-Host "  " $start "-" $end ": " $analysis.decadePct[$d] "%"
}
Write-Host ""
Write-Host "--- TOP 20 NUMERI PIU FREQUENTI ---"
foreach ($num in $analysis.topNumbers.GetEnumerator() | Sort-Object Value -Descending) {
    $numPct = [Math]::Round($num.Value / $totalNums * 100, 2)
    Write-Host "  Numero " $num.Name ": " $num.Value " volte (" $numPct "%)"
}
Write-Host ""
Write-Host "--- TOP 10 SOMME PIU FREQUENTI ---"
foreach ($sum in $analysis.topSums.GetEnumerator() | Sort-Object Value -Descending) {
    Write-Host "  Somma " $sum.Name ": " $sum.Value " volte"
}
Write-Host ""
Write-Host "--- JOLLY (totale: $($analysis.jollyTotal)) ---"
foreach ($j in $analysis.jollyFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10) {
    Write-Host "  Jolly " $j.Name ": " $j.Value " volte"
}
Write-Host ""
Write-Host "--- SUPERSTAR (totale: $($analysis.starTotal)) ---"
foreach ($s in $analysis.starFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10) {
    Write-Host "  Superstar " $s.Name ": " $s.Value " volte"
}
Write-Host ""
Write-Host "--- DISTRIBUZIONE ANNI ---"
foreach ($y in $analysis.yearDist.GetEnumerator() | Sort-Object Name) {
    Write-Host "  Year " $y.Key ": " $y.Value " estrazioni"
}
Write-Host ""
Write-Host "Analisi salvata in: $outputPath" -ForegroundColor Yellow
