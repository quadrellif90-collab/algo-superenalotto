# ALL COMBINATIONS - 2 tickets/draw, every strategy pair
# Premi: M2=5 M3=10 M4=100 M5=1000 M6=1000000

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "all_combos_backtest.json"

$records = @()
(Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1) | ForEach-Object {
    $p = $_ -split ','
    if ($p.Count -ge 9) {
        try { $records += [PSCustomObject]@{ N = @([int]$p[2],[int]$p[3],[int]$p[4],[int]$p[5],[int]$p[6],[int]$p[7]) } } catch {}
    }
}
Write-Host "Draws: $($records.Count)"
$prizes = @{ "2"=5; "3"=10; "4"=100; "5"=1000; "6"=1000000 }

# Frequenze
$freq = @{}; 1..90 | ForEach-Object { $freq[$_] = 0 }
$records | ForEach-Object { $_.N | ForEach-Object { $freq[$_]++ } }
$midLo = ($freq.Values | Measure-Object -Average).Average * 0.85
$midHi = ($freq.Values | Measure-Object -Average).Average * 1.15

function Test-Cons { param($nums)
    $s=($nums|Measure-Object -Sum).Sum
    if ($s-lt246 -or $s-gt306){return $false}
    $dd=@{}; foreach($n in $nums){$d=[int][Math]::Floor($n/10); $dd[$d]++; if($dd[$d]-gt2){return $false}}
    if (($nums|Where-Object{$_-gt80}).Count -gt1){return $false}
    return $true
}
function Build-Pool { param([scriptblock]$filter, [int]$size=500)
    $pool=@(); $att=0
    while ($pool.Count -lt $size -and $att++ -lt 300000) {
        $c = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
        if (& $filter $c) { $pool += ,@($c) }
    }
    return $pool
}

$fCon={param($n);(Test-Cons $n)}
$fMid={param($n);if(-not(Test-Cons $n)){return $false};foreach($x in $n){if($freq[$x]-lt$midLo -or $freq[$x]-gt$midHi){return $false}};return $true}
$fOne={param($n);if(-not(Test-Cons $n)){return $false};$pp=0;for($i=0;$i-lt5;$i++){if($n[$i+1]-$n[$i]-eq1){$pp++}};return $pp-eq1}
$fGap={param($n);if(-not(Test-Cons $n)){return $false};$g=90;for($i=0;$i-lt5;$i++){$gp=$n[$i+1]-$n[$i];if($gp-lt$g){$g=$gp}};return $g-ge11}
$fLDS={param($n);if(-not(Test-Cons $n)){return $false};$ld=$n|ForEach-Object{$_%10};return (($ld|Select-Object -Unique).Count -eq 6)}

$wheel = @(
    @(5,17,28,41,59,83),@(3,14,33,47,62,88),@(9,22,35,51,70,85),
    @(2,19,30,44,66,79),@(11,24,38,52,73,90),@(6,20,36,49,64,81),
    @(8,16,29,46,60,87),@(1,25,37,53,68,84),@(13,27,40,55,71,89),@(4,18,31,48,63,82)
)

# Generatori (ogniuno ritorna un ticket dato l'indice estrazione)
$poolMid=Build-Pool $fMid; $poolOne=Build-Pool $fOne; $poolGap=Build-Pool $fGap; $poolLDS=Build-Pool $fLDS
Write-Host "Pools built: Mid=$($poolMid.Count) One=$($poolOne.Count) Gap=$($poolGap.Count) LDS=$($poolLDS.Count)"

$GEN = @{
    "Random"            = { param($i) Get-Random -InputObject (1..90) -Count 6 | Sort-Object }
    "SameNumbers"       = { @(1,2,3,4,5,6) }
    "90NumberCycle"     = { param($i) $wheel[$i % 10] | Sort-Object }
    "LastDigitSpread"   = { param($i) $poolLDS[$i % $poolLDS.Count] }
    "OddEvenBalanced"   = { param($i)
        $o=1..90|Where-Object{$_%2-eq1}; $e=1..90|Where-Object{$_%2-eq0}
        $c=(Get-Random -InputObject $o -Count 3)+(Get-Random -InputObject $e -Count 3)|Sort-Object
        if(Test-Cons $c){$c}else{Get-Random -InputObject(1..90)-Count 6|Sort-Object}
    }
    "ComplementMirror"  = { $a=Get-Random -InputObject (1..45) -Count 3|Sort-Object; ($a+($a|ForEach-Object{91-$_}))|Sort-Object }
    "MiddleFrequency"   = { param($i) $poolMid[$i % $poolMid.Count] }
    "OneConsecutivePair"= { param($i) $poolOne[$i % $poolOne.Count] }
    "GapSpread"         = { param($i) $poolGap[$i % $poolGap.Count] }
}

$names = $GEN.Keys | Sort-Object
$comboCount = 0
$results = @{}
Write-Host "Combos: $(($names.Count*($names.Count+1))/2)" -ForegroundColor Yellow

for ($a=0; $a -lt $names.Count; $a++) {
    for ($b=$a; $b -lt $names.Count; $b++) {
        $n1=$names[$a]; $n2=$names[$b]
        $key = if ($n1 -eq $n2) { "$n1 x2" } else { "$n1 + $n2" }
        $r = @{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
        for ($i=0; $i -lt $records.Count; $i++) {
            # ticket 1
            $t1 = & $GEN[$n1] $i; $r.spent++
            $m1 = ($t1 | Where-Object { $records[$i].N -contains $_ }).Count
            if ($m1 -ge 2) { $r[$m1.ToString()]++; $r.won += $prizes[$m1.ToString()] }
            # ticket 2
            $t2 = & $GEN[$n2] $i; $r.spent++
            $m2 = ($t2 | Where-Object { $records[$i].N -contains $_ }).Count
            if ($m2 -ge 2) { $r[$m2.ToString()]++; $r.won += $prizes[$m2.ToString()] }
        }
        $r.net = $r.won - $r.spent
        $r.roi = [Math]::Round(($r.won/$r.spent)*100,2)
        $results[$key] = $r
        $comboCount++
        if ($comboCount % 10 -eq 0) { Write-Host "  [$comboCount] $key : Net $($r.net) ROI $($r.roi)%" -ForegroundColor DarkGray }
    }
}

# Ordina per net (migliore in alto = minor perdita)
$sorted = $results.GetEnumerator() | Sort-Object { $_.Value.net } -Descending
$best = $sorted | Select-Object -First 1
$worst = $sorted | Select-Object -Last 1

Write-Host "`n=== TOP 10 (minore perdita netta) ===" -ForegroundColor Cyan
$sorted | Select-Object -First 10 | ForEach-Object {
    Write-Host ("  {0,-32} Net {1,7} | M2:{2} M3:{3} M4:{4} M5:{5} M6:{6} | ROI {7}%" -f $_.Key, $_.Value.net, $_.Value['2'], $_.Value['3'], $_.Value['4'], $_.Value['5'], $_.Value['6'], $_.Value.roi) -ForegroundColor Green
}
Write-Host "`n=== BOTTOM 5 (peggiori) ===" -ForegroundColor Cyan
$sorted | Select-Object -Last 5 | ForEach-Object {
    Write-Host ("  {0,-32} Net {1,7} | ROI {2}%" -f $_.Key, $_.Value.net, $_.Value.roi) -ForegroundColor Red
}

# Salva JSON
$rep = @{
    metadata = @{ draws=$records.Count; ticketsPerDraw=2; totalCombos=$comboCount; strategies=$names.Count }
    best = $best.Key
    worst = $worst.Key
    all = @{}
}
foreach ($k in $results.Keys) {
    $rr=$results[$k]
    $rep.all[$k]=@{net=$rr.net;spent=$rr.spent;won=$rr.won;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];m5=$rr['5'];m6=$rr['6'];roi=$rr.roi}
}
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "`nBEST COMBO: $($best.Key) (Net $($best.Value.net), ROI $($best.Value.roi)%)" -ForegroundColor Green
Write-Host "Saved $outPath"