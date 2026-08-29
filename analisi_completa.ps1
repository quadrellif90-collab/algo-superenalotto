# analisi_completa.ps1
# PowerShell 5.1 - analisi statistica completa su superenalotto.csv

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
foreach ($n in $allNums) { $numFreq[$n] = $numFreq[$n] + 1 }
$topNums  = $numFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20

# Frequenze somme
$sumFreq  = @{}
foreach ($s in $sums) { $sumFreq[$s] = $sumFreq[$s] + 1 }
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
foreach ($n in $allNums) { $finalDigit[$n % 10] = $finalDigit[$n % 10] + 1 }
$finalDigitPct = @{}
foreach ($d in 0..9) { $finalDigitPct[$d] = [Math]::Round($finalDigit[$d] / $totalNums * 100, 2) }

# Decade
$decadeDist  = @{}
foreach ($n in $allNums) { $decadeDist[[Math]::Floor($n / 10)] = $decadeDist[[Math]::Floor($n / 10)] + 1 }
$decadePct   = @{}
foreach ($d in 0..8) { $decadePct[$d] = [Math]::Round($decadeDist[$d] / $totalNums * 100, 2) }

# Jolly
$jollyFreq = @{}
$jollyTotal = 0
foreach ($r in $records) {
    if ($r.Jolly -gt 0) {
        $jollyFreq[$r.Jolly] = $jollyFreq[$r.Jolly] + 1
        $jollyTotal++
    }
}

# Superstar
$starFreq = @{}
$starTotal = 0
foreach ($r in $records) {
    if ($r.Star -gt 0) {
        $starFreq[$r.Star] = $starFreq[$r.Star] + 1
        $starTotal++
    }
}

# Anno
$yearDist = @{}
foreach ($r in $records) {
    $year = [int]$r.Date.Substring(0, 4)
    $yearDist[$year] = $yearDist[$year] + 1
}

# --- Costruzione oggetto JSON ---
# Converti hashtable con chiavi numeriche in oggetti con chiavi stringa per JSON
$finalDigitPctObj = [PSCustomObject]([ordered]@{})
foreach ($d in 0..9) { $finalDigitPctObj | Add-Member -NotePropertyName "$d" -NotePropertyValue $finalDigitPct[$d] }

$decadePctObj = [PSCustomObject]([ordered]@{})
foreach ($d in 0..8) { $decadePctObj | Add-Member -NotePropertyName "$d" -NotePropertyValue $decadePct[$d] }

$jollyFreqObj = [PSCustomObject]([ordered]@{})
foreach ($kv in $jollyFreq.GetEnumerator()) { $jollyFreqObj | Add-Member -NotePropertyName "$($kv.Name)" -NotePropertyValue $kv.Value }

$starFreqObj = [PSCustomObject]([ordered]@{})
foreach ($kv in $starFreq.GetEnumerator()) { $starFreqObj | Add-Member -NotePropertyName "$($kv.Name)" -NotePropertyValue $kv.Value }

$yearDistObj = [PSCustomObject]([ordered]@{})
foreach ($kv in $yearDist.GetEnumerator()) { $yearDistObj | Add-Member -NotePropertyName "$($kv.Name)" -NotePropertyValue $kv.Value }

$topNumsObj = [PSCustomObject]([ordered]@{})
foreach ($kv in $topNums) { $topNumsObj | Add-Member -NotePropertyName "$($kv.Name)" -NotePropertyValue $kv.Value }

$topSumsObj = [PSCustomObject]([ordered]@{})
foreach ($kv in $topSums) { $topSumsObj | Add-Member -NotePropertyName "$($kv.Name)" -NotePropertyValue $kv.Value }

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
    finalDigitPct    = $finalDigitPctObj
    decadePct        = $decadePctObj
    topNumbers       = $topNumsObj
    topSums          = $topSumsObj
    jollyFreq        = $jollyFreqObj
    starFreq         = $starFreqObj
    jollyTotal       = $jollyTotal
    starTotal        = $starTotal
    yearDist         = $yearDistObj
    firstDate        = $records[0].Date
    lastDate         = $records[-1].Date
}

$analysisJson = $analysis | ConvertTo-Json -Depth 5
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
foreach ($num in $topNums) {
    $numPct = [Math]::Round($num.Value / $totalNums * 100, 2)
    Write-Host "  Numero " $num.Name ": " $num.Value " volte (" $numPct "%)"
}
Write-Host ""
Write-Host "--- TOP 10 SOMME PIU FREQUENTI ---"
foreach ($sum in $topSums) { Write-Host "  Somma $($sum.Name): $($sum.Value) volte" }
Write-Host ""
Write-Host "--- JOLLY (totale: $($analysis.jollyTotal)) ---"
$jollySorted = $jollyFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10
foreach ($j in $jollySorted) { Write-Host "  Jolly $($j.Name): $($j.Value) volte" }
Write-Host ""
Write-Host "--- SUPERSTAR (totale: $($analysis.starTotal)) ---"
$starSorted = $starFreq.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10
foreach ($s in $starSorted) { Write-Host "  Superstar $($s.Name): $($s.Value) volte" }
Write-Host ""
Write-Host "--- DISTRIBUZIONE ANNI ---"
foreach ($y in $yearDist.GetEnumerator() | Sort-Object Name) {
    Write-Host "  Year $($y.Key): $($y.Value) estrazioni"
}
Write-Host ""
Write-Host "Analisi salvata in: $outputPath" -ForegroundColor Yellow
