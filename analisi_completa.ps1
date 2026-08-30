# analisi_completa.ps1 - Analisi statistica completa su superenalotto.csv
# PowerShell 5.1 - versione corretta con path relativi

$ErrorActionPreference = "Stop"

# Percorsi relativi
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outputPath = Join-Path $scriptDir "analisi_completa.json"

# --- Caricamento dati ---
$records = [System.Collections.Generic.List[PSCustomObject]]@()
$lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split ','
    if ($parts.Count -lt 9) { continue }
    try {
        $n1 = [int]$parts[2]
        $n2 = [int]$parts[3]
        $n3 = [int]$parts[4]
        $n4 = [int]$parts[5]
        $n5 = [int]$parts[6]
        $n6 = [int]$parts[7]
        if ($n1 -lt 1 -or $n1 -gt 90 -or $n2 -lt 1 -or $n2 -gt 90 -or $n3 -lt 1 -or $n3 -gt 90 -or $n4 -lt 1 -or $n4 -gt 90 -or $n5 -lt 1 -or $n5 -gt 90 -or $n6 -lt 1 -or $n6 -gt 90) {
            continue
        }
        $nums = @($n1, $n2, $n3, $n4, $n5, $n6)
        $jolly = 0
        if ($parts[8].Trim() -ne "") { $jolly = [int]$parts[8] }
        $star = 0
        if ($parts.Count -gt 9 -and $parts[9].Trim() -ne "") {
            $star = [int]$parts[9]
        }
        $sum = $n1 + $n2 + $n3 + $n4 + $n5 + $n6
        $records.Add([PSCustomObject]@{
            Date  = [string]$parts[0]
            Conc  = [string]$parts[1]
            N1    = $nums[0]
            N2    = $nums[1]
            N3    = $nums[2]
            N4    = $nums[3]
            N5    = $nums[4]
            N6    = $nums[5]
            Nums  = $nums
            Sum   = $sum
            Jolly = $jolly
            Star  = $star
        })
    } catch {
        # salta righe malformate
    }
}

Write-Host "Caricati $($records.Count) record validi" -ForegroundColor Cyan

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

# --- Calcolo metriche (lavoro direttamente su $records.List) ---
$sums      = @()
$allNums   = [System.Collections.Generic.List[int]]@()
foreach ($r in $records) {
    $sums += $r.Sum
    foreach ($nn in $r.Nums) { $allNums.Add($nn) }
}
$sumsSorted = $sums | Sort-Object
$n         = $sumsSorted.Count
$totalNums = $n * 6

# Somme
$mean    = ($sums | Measure-Object -Average).Average
$median  = $sumsSorted[[int]($n / 2)]
$min     = ($sums | Measure-Object -Minimum).Minimum
$max     = ($sums | Measure-Object -Maximum).Maximum
$sumSq   = 0
foreach ($s in $sums) { $sumSq += [Math]::Pow($s - $mean, 2) }
$std     = [Math]::Sqrt($sumSq / $n)
$q1      = $sumsSorted[[int]($n * 0.25)]
$q3      = $sumsSorted[[int]($n * 0.75)]

# Frequenze numeri
$numFreq  = @{}
foreach ($nn in $allNums) {
    if ($numFreq.ContainsKey($nn)) {
        $numFreq[$nn]++
    } else {
        $numFreq[$nn] = 1
    }
}
$topNums  = $numFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20

# Frequenze somme
$sumFreq  = @{}
foreach ($s in $sums) {
    if ($sumFreq.ContainsKey($s)) {
        $sumFreq[$s]++
    } else {
        $sumFreq[$s] = 1
    }
}
$topSums  = $sumFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10

# Prime
$primeCount = ($allNums | Where-Object { Test-Prime $_ }).Count

# Categorie
$extremeCount = ($allNums | Where-Object { $_ -ge 76 }).Count
$gt31Count    = ($allNums | Where-Object { $_ -gt 31 }).Count
$gt80Count    = ($allNums | Where-Object { $_ -gt 80 }).Count
$evenCount    = ($allNums | Where-Object { $_ % 2 -eq 0 }).Count

# Percentuali
$primePct    = [Math]::Round($primeCount / $totalNums * 100, 2)
$extremePct  = [Math]::Round($extremeCount / $totalNums * 100, 2)
$gt31Pct     = [Math]::Round($gt31Count / $totalNums * 100, 2)
$gt80Pct     = [Math]::Round($gt80Count / $totalNums * 100, 2)
$evenPct     = [Math]::Round($evenCount / $totalNums * 100, 2)

# Cifra finale
$finalDigit  = @{}
foreach ($nn in $allNums) {
    $digit = $nn % 10
    if ($finalDigit.ContainsKey($digit)) {
        $finalDigit[$digit]++
    } else {
        $finalDigit[$digit] = 1
    }
}
$finalDigitPct = @{}
foreach ($d in 0..9) {
    $count = 0
    if ($finalDigit.ContainsKey($d)) { $count = $finalDigit[$d] }
    $finalDigitPct[[string]$d] = [Math]::Round($count / $totalNums * 100, 2)
}

# Decade
$decadeDist  = @{}
foreach ($nn in $allNums) {
    $dec = [int][Math]::Floor($nn / 10)
    if ($decadeDist.ContainsKey($dec)) {
        $decadeDist[$dec]++
    } else {
        $decadeDist[$dec] = 1
    }
}
$decadePct = @{}
foreach ($d in 0..9) {
    $count = 0
    if ($decadeDist.ContainsKey($d)) { $count = $decadeDist[$d] }
    $decadePct[[string]$d] = [Math]::Round($count / $totalNums * 100, 2)
}

# Jolly
$jollyFreq = @{}
$jollyTotal = 0
foreach ($r in $records) {
    if ($r.Jolly -gt 0) {
        if ($jollyFreq.ContainsKey($r.Jolly)) {
            $jollyFreq[$r.Jolly]++
        } else {
            $jollyFreq[$r.Jolly] = 1
        }
        $jollyTotal++
    }
}

# Superstar
$starFreq = @{}
$starTotal = 0
foreach ($r in $records) {
    if ($r.Star -gt 0) {
        if ($starFreq.ContainsKey($r.Star)) {
            $starFreq[$r.Star]++
        } else {
            $starFreq[$r.Star] = 1
        }
        $starTotal++
    }
}

# Anno
$yearDist = @{}
foreach ($r in $records) {
    if ($r.Date.Length -ge 4) {
        $year = [int]$r.Date.Substring(0, 4)
        if ($yearDist.ContainsKey($year)) {
            $yearDist[$year]++
        } else {
            $yearDist[$year] = 1
        }
    }
}

# --- Costruzione oggetti JSON-safe (chiavi sempre stringa) ---
# Hot/Cold Numbers Analysis
$hotThreshold = [Math]::Max(1, [int](($totalNums / 90) * 1.1))  # ~10% above average
$coldThreshold = [Math]::Max(1, [int](($totalNums / 90) * 0.8))  # ~10% below average

$hotColdObj = @{
    hot = @($numFreq.GetEnumerator() | Where-Object { $_.Value -ge $hotThreshold } | ForEach-Object { [int]$_.Key } | Sort-Object)
    cold = @($numFreq.GetEnumerator() | Where-Object { $_.Value -le $coldThreshold } | ForEach-Object { [int]$_.Key } | Sort-Object)
    threshold = @{
        average = [Math]::Round($totalNums / 90, 2)
        hotMin = $hotThreshold
        coldMax = $coldThreshold
    }
}

# Decade Distribution (already computed above)
$decadeDistSafe = @{}
for ($d = 0; $d -le 9; $d++) {
    $decadeDistSafe[[string]$d] = if ($decadeDist.ContainsKey($d)) { $decadeDist[$d] } else { 0 }
}

$jollyFreqObj = @{}
foreach ($kv in $jollyFreq.GetEnumerator()) {
    $jollyFreqObj[[string]$kv.Key] = $kv.Value
}

$starFreqObj = @{}
foreach ($kv in $starFreq.GetEnumerator()) {
    $starFreqObj[[string]$kv.Key] = $kv.Value
}

$yearDistObj = @{}
foreach ($kv in $yearDist.GetEnumerator()) {
    $yearDistObj[[string]$kv.Key] = $kv.Value
}

$topNumsObj = @{}
foreach ($kv in $topNums) {
    $topNumsObj[[string]$kv.Key] = $kv.Value
}

$topSumsObj = @{}
foreach ($kv in $topSums) {
    $topSumsObj[[string]$kv.Key] = $kv.Value
}

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
    topNumbers       = $topNumsObj
    topSums          = $topSumsObj
    jollyFreq        = $jollyFreqObj
    starFreq         = $starFreqObj
    jollyTotal       = $jollyTotal
    starTotal        = $starTotal
    yearDist         = $yearDistObj
    hotCold          = $hotColdObj
    decadeDist       = $decadeDistSafe
    firstDate        = $records[0].Date
    lastDate         = $records[$records.Count - 1].Date
}

$analysisJson = $analysis | ConvertTo-Json -Depth 5
Set-Content -Path $outputPath -Value $analysisJson -Encoding UTF8

# --- Output formattato ---
Write-Host "`n=== ANALISI COMPLETA - SUPERENALOTTO ===" -ForegroundColor Cyan
Write-Host "Dataset: $n estrazioni ($($records[0].Date) - $($records[$records.Count - 1].Date))" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "--- SOMME 6 NUMERI ---" -ForegroundColor Yellow
Write-Host "Media: $($analysis.mean) | Mediana: $($analysis.median)" -ForegroundColor White
Write-Host "Std Dev: $($analysis.stddev)" -ForegroundColor White
Write-Host "Q1: $($analysis.q1) | Q3: $($analysis.q3)" -ForegroundColor White
Write-Host "Min: $($analysis.min) | Max: $($analysis.max) | Range: $($analysis.range) | IQR: $($analysis.iqr)" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "--- NUMERI ---" -ForegroundColor Yellow
Write-Host "Primi: $($analysis.primePct)% ($($analysis.primeCount) su $($analysis.totalNumbers))" -ForegroundColor White
Write-Host "Estremi (>75): $($analysis.extremePct)% ($($analysis.extremeCount) su $($analysis.totalNumbers))" -ForegroundColor White
Write-Host ">31: $($analysis.gt31Pct)% ($($analysis.gt31Count) su $($analysis.totalNumbers))" -ForegroundColor White
Write-Host ">80: $($analysis.gt80Pct)% ($($analysis.gt80Count) su $($analysis.totalNumbers))" -ForegroundColor White
Write-Host "Pari: $($analysis.evenPct)% ($($analysis.evenCount) su $($analysis.totalNumbers))" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "--- CIFRA FINALE ---" -ForegroundColor Yellow
foreach ($d in 0..9) {
    $key = [string]$d
    Write-Host "  Digit $d : $($analysis.finalDigitPct[$key])%" -ForegroundColor White
}
Write-Host "" -ForegroundColor White
Write-Host "--- DECADE ---" -ForegroundColor Yellow
foreach ($d in 0..9) {
    $start = $d * 10 + 1
    $end   = $start + 9
    if ($d -eq 0) { $start = 1; $end = 9 }
    if ($d -eq 9) { $start = 81; $end = 90 }
    $key = [string]$d
    Write-Host "  $start-$end : $($analysis.decadePct[$key])%" -ForegroundColor White
}
Write-Host "" -ForegroundColor White
Write-Host "--- TOP 20 NUMERI PIU FREQUENTI ---" -ForegroundColor Yellow
foreach ($num in $topNums) {
    $numPct = [Math]::Round($num.Value / $totalNums * 100, 2)
    Write-Host "  Numero $($num.Key): $($num.Value) volte ($($numPct)%)" -ForegroundColor White
}
Write-Host "" -ForegroundColor White
Write-Host "--- TOP 10 SOMME PIU FREQUENTI ---" -ForegroundColor Yellow
foreach ($sum in $topSums) { Write-Host "  Somma $($sum.Key): $($sum.Value) volte" -ForegroundColor White }
Write-Host "" -ForegroundColor White
Write-Host "--- JOLLY (totale: $($analysis.jollyTotal)) ---" -ForegroundColor Yellow
$jollySorted = $jollyFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10
foreach ($j in $jollySorted) { Write-Host "  Jolly $($j.Key): $($j.Value) volte" -ForegroundColor White }
Write-Host "" -ForegroundColor White
Write-Host "--- SUPERSTAR (totale: $($analysis.starTotal)) ---" -ForegroundColor Yellow
$starSorted = $starFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10
foreach ($s in $starSorted) { Write-Host "  Superstar $($s.Key): $($s.Value) volte" -ForegroundColor White }
Write-Host "" -ForegroundColor White
Write-Host "--- DISTRIBUZIONE ANNI ---" -ForegroundColor Yellow
foreach ($y in $yearDist.GetEnumerator() | Sort-Object Key) {
    Write-Host "  Year $($y.Key): $($y.Value) estrazioni" -ForegroundColor White
}
Write-Host "" -ForegroundColor White
Write-Host "Analisi salvata in: $outputPath" -ForegroundColor Yellow