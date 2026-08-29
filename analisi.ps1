Add-Type -AssemblyName System.Numerics

function Get-Factorial([int]$n) {
    if ($n -lt 0) { return $null }
    if ($n -le 1) { return [System.Numerics.BigInteger]1 }
    $result = [System.Numerics.BigInteger]1
    for ([int]$i = 2; $i -le $n; $i++) {
        $result = $result * $i
    }
    return $result
}

function Get-Combination([int]$n, [int]$k) {
    if ($k -lt 0 -or $k -gt $n) { return 0 }
    $num = Get-Factorial($n)
    $denom = Get-Factorial($k) * Get-Factorial($n - $k)
    return $num / $denom
}

$csv = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
$allLines = Get-Content $csv | Select-Object -Skip 1
$records = @()

foreach ($line in $allLines) {
    $parts = $line -split ','
    if ($parts.Count -ge 9) {
        try {
            $n1 = [int]($parts[2].Trim())
            $n2 = [int]($parts[3].Trim())
            $n3 = [int]($parts[4].Trim())
            $n4 = [int]($parts[5].Trim())
            $n5 = [int]($parts[6].Trim())
            $n6 = [int]($parts[7].Trim())
            $jolly = [int]($parts[8].Trim())
            $superstar = 0
            if ($parts.Count -gt 9 -and $parts[9].Trim() -ne "") {
                $superstar = [int]($parts[9].Trim())
            }
            $nums = @($n1, $n2, $n3, $n4, $n5, $n6)
            if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                $records += ,@{
                    data = $parts[0]
                    n1 = $n1
                    n2 = $n2
                    n3 = $n3
                    n4 = $n4
                    n5 = $n5
                    n6 = $n6
                    nums = $nums
                    sum = ($nums | Measure-Object -Sum).Sum
                    jolly = $jolly
                    superstar = $superstar
                }
            }
        } catch {}
    }
}

Write-Host "=== ANALISI COMPLETA SUPERENALOTTO ===" -ForegroundColor Cyan
Write-Host "Totale estrazioni: $($records.Count)"
Write-Host ""

$sommaValues = @()
$triggerSums = @()
$decades = @{}
$finalDigits = @{}
$primes = 0; $extremes = 0; $gt31 = 0; $gt80 = 0

foreach ($r in $records) {
    $nums = @($r.n1, $r.n2, $r.n3, $r.n4, $r.n5, $r.n6)
    $sum = ($nums | Measure-Object -Sum).Sum
    $sommaValues += $sum
    
    if ($r.data -match '^\d{4}-\d{2}-\d{2}$') {
        $dayOfWeek = (Get-Date $r.data).DayOfWeek.Value__
        if ($dayOfWeek -eq 'Saturday') { $triggerSums += $sum }
    }
    
    foreach ($n in $nums) {
        $d = [math]::Floor($n / 10)
        $decades[$d] = ++$decades[$d]
        $fd = $n % 10
        $finalDigits[$fd] = ++$finalDigits[$fd]
        if ($n -gt 31) { $gt31++ }
        if ($n -gt 80) { $gt80++ }
        if ($n -le 32 -or ($n % 2 -eq 1 -and $n -gt 1)) {
            $isPrime = $true
            if ($n -lt 2) { $isPrime = $false }
            elseif ($n -gt 3 -and $n % 2 -eq 0) { $isPrime = $false }
            elseif ($n -gt 3) {
                for ($i = 3; $i -le [math]::Sqrt($n); $i += 2) {
                    if ($n % $i -eq 0) { $isPrime = $false; break }
                }
            }
            if ($isPrime) { $primes++ }
        }
        if ($n -ge 76) { $extremes++ }
    }
}

$count = $records.Count
$media = ($sommaValues | Measure-Object -Average).Average
$sorted = $sommaValues | Sort-Object
$count_odd = ($records | Where-Object { $_.n1 % 2 -eq 1 }).Count
$count_even = $count - $count_odd

$sumSq = 0
foreach ($v in $sommaValues) { $sumSq += [math]::Pow($v - $media, 2) }
$stdDev = [math]::Sqrt($sumSq / $sommaValues.Count)

$median = $sorted[[int]($sorted.Count / 2)]
$q1 = $sorted[[int]($sorted.Count * 0.25)]
$q3 = $sorted[[int]($sorted.Count * 0.75)]
$min = ($sorted | Measure-Object -Minimum).Minimum
$max = ($sorted | Measure-Object -Maximum).Maximum
$triggerAvg = if ($triggerSums.Count -gt 0) { ($triggerSums | Measure-Object -Average).Average } else { 0 }

$entropy = 0
foreach ($key in $finalDigits.Keys) {
    $p = $finalDigits[$key] / ($count * 6)
    if ($p -gt 0) { $entropy -= $p * [math]::Log($p, 2) }
}
$entropy = [math]::Round($entropy, 4)

$meanDecade = 0
foreach ($key in $decades.Keys) { $meanDecade += $key * $decades[$key] }
$meanDecade = $meanDecade / ($count * 6)
$meanDecade = [math]::Round($meanDecade, 2)

Write-Host "=== STATISTICHE SOMMA ===" -ForegroundColor Yellow
Write-Host "Media: $([math]::Round($media, 2))"
Write-Host "Mediana: $median"
Write-Host "Std Dev: $([math]::Round($stdDev, 2))"
Write-Host "Min: $min | Max: $max"
Write-Host "Q1: $q1 | Q3: $q3"
Write-Host "Trigger (Sabato) Avg: $([math]::Round($triggerAvg, 2)) ($($triggerSums.Count) estrazioni)"
Write-Host ""

Write-Host "=== DISTRIBUZIONE NUMERI ===" -ForegroundColor Yellow
Write-Host "Primi (calcolati): $primes ($([math]::Round($primes/($count*6)*100, 2))%)"
Write-Host "Estremi (76-90): $extremes ($([math]::Round($extremes/($count*6)*100, 2))%)"
Write-Host ">31: $gt31 ($([math]::Round($gt31/($count*6)*100, 2))%)"
Write-Host ">80: $gt80 ($([math]::Round($gt80/($count*6)*100, 2))%)"
Write-Host "Dispari: $count_odd | Pari: $count_even"
Write-Host ""

Write-Host "=== DISTRIBUZIONE DECINE ===" -ForegroundColor Yellow
$decKeys = ($decades.Keys | Sort-Object)
foreach ($k in $decKeys) {
    $pct = [math]::Round($decades[$k] / ($count * 6) * 100, 2)
    Write-Host "Decina $k ( $($k*10)-$($k*10+9) ): $pct%"
}
Write-Host "Media decina: $meanDecade"
Write-Host ""

Write-Host "=== ENTROPIA CIFRE FINALI ===" -ForegroundColor Yellow
Write-Host "Entropia Shannon: $entropy bits (max teorico: 3.3219)"
$fdKeys = ($finalDigits.Keys | Sort-Object)
foreach ($k in $fdKeys) {
    $pct = [math]::Round($finalDigits[$k] / ($count * 6) * 100, 2)
    Write-Host "  Cifra $k : $pct%"
}
Write-Host ""

$range = $max - $min
$within1sd = (($sommaValues | Where-Object { $_ -ge ($media - $stdDev) -and $_ -le ($media + $stdDev) }).Count / $sommaValues.Count) * 100
$within2sd = (($sommaValues | Where-Object { $_ -ge ($media - 2*$stdDev) -and $_ -le ($media + 2*$stdDev) }).Count / $sommaValues.Count) * 100

Write-Host "=== DISTRIBUZIONE GAUSSIANA ===" -ForegroundColor Yellow
Write-Host "Range: $range"
Write-Host "Within 1σ: $([math]::Round($within1sd, 2))%"
Write-Host "Within 2σ: $([math]::Round($within2sd, 2))%"

$histogram = @{}
foreach ($s in $sommaValues) {
    $bucket = [math]::Floor($s / 20) * 20
    $histogram[$bucket] = ++$histogram[$bucket]
}
Write-Host ""
Write-Host "=== TOP 10 FASCE SOMMA (bucket 20) ===" -ForegroundColor Yellow
$sortedHist = $histogram.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10
foreach ($h in $sortedHist) {
    $hKey = $h.Key
    $hVal = $h.Value
    Write-Host "  " $hKey "-" ($hKey + 19) ": " $hVal " estrazioni"
}
