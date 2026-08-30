# CONFRONTO TOTALE: tutte le strategie (singola 1 biglietto + dual 2 biglietti)
# Incluso nuove: DecadeBalanced, SumLocked276, DelayedNumbers, PrimeFocus
# Premi: M2=5 M3=10 M4=100 M5=1000 M6=1000000

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "total_confronto.json"

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

# Filtri nuove strategie
$fLDS={param($n);if(-not(Test-Cons $n)){return $false};$ld=$n|ForEach-Object{$_%10};return (($ld|Select-Object -Unique).Count -eq 6)}
$fMid={param($n);if(-not(Test-Cons $n)){return $false};foreach($x in $n){if($freq[$x]-lt$midLo -or $freq[$x]-gt$midHi){return $false}};return $true}
$fOne={param($n);if(-not(Test-Cons $n)){return $false};$pp=0;for($i=0;$i-lt5;$i++){if($n[$i+1]-$n[$i]-eq1){$pp++}};return $pp-eq1}
$fGap={param($n);if(-not(Test-Cons $n)){return $false};$g=90;for($i=0;$i-lt5;$i++){$gp=$n[$i+1]-$n[$i];if($gp-lt$g){$g=$gp}};return $g-ge11}
$fDec={param($n);if(-not(Test-Cons $n)){return $false};$dmax=@{};foreach($x in $n){$d=[int][Math]::Floor($x/10);$dmax[$d]++};return ($dmax.Keys.Count -eq 6)}  # 6 decadi diverse
$fSum={param($n);$s=($n|Measure-Object -Sum).Sum;return ($s -eq 276 -or $s -eq 277)}  # somma ~media esatta
$fPri={param($n);if(-not(Test-Cons $n)){return $false};$pr=@(2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89);$pc=($n|Where-Object{$pr -contains $_}).Count;return $pc -ge 3}
$fDel={param($n);if(-not(Test-Cons $n)){return $false};return $true}  # filtro applicato per indice draw sotto

$wheel = @(
    @(5,17,28,41,59,83),@(3,14,33,47,62,88),@(9,22,35,51,70,85),
    @(2,19,30,44,66,79),@(11,24,38,52,73,90),@(6,20,36,49,64,81),
    @(8,16,29,46,60,87),@(1,25,37,53,68,84),@(13,27,40,55,71,89),@(4,18,31,48,63,82)
)

$poolLDS=Build-Pool $fLDS; $poolMid=Build-Pool $fMid; $poolOne=Build-Pool $fOne; $poolGap=Build-Pool $fGap
$poolDec=Build-Pool $fDec; $poolSum=Build-Pool $fSum; $poolPri=Build-Pool $fPri
Write-Host "Pools: LDS=$($poolLDS.Count) Mid=$($poolMid.Count) One=$($poolOne.Count) Gap=$($poolGap.Count) Dec=$($poolDec.Count) Sum=$($poolSum.Count) Pri=$($poolPri.Count)"

# Generatori con supporto "delayed" (usa ultimi 20 draw per evitare numeri recenti)
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
    "DecadeBalanced"    = { param($i) $poolDec[$i % $poolDec.Count] }
    "SumLocked276"      = { param($i) $poolSum[$i % $poolSum.Count] }
    "PrimeFocus"        = { param($i) $poolPri[$i % $poolPri.Count] }
    "DelayedNumbers"    = { param($i)
        $recent=@{}
        for($k=[Math]::Max(0,$i-20);$k-lt$i;$k++){ $records[$k].N | ForEach-Object { $recent[$_]=1 } }
        $pool=@()
        $att=0
        while($pool.Count -lt 6 -and $att++ -lt 10000){ $x=Get-Random -InputObject(1..90); if(-not $recent.ContainsKey($x)){ $pool+=$x } }
        if($pool.Count -eq 6 -and (Test-Cons $pool)){ return $pool|Sort-Object }
        return Get-Random -InputObject(1..90)-Count 6|Sort-Object
    }
}

$names = $GEN.Keys | Sort-Object
Write-Host "Strategie: $($names.Count) | Combos dual: $(($names.Count*($names.Count+1))/2)" -ForegroundColor Yellow

# === SINGOLE (1 biglietto) ===
$single = @{}
Write-Host "`n--- SINGOLE (1 biglietto/estrazione) ---" -ForegroundColor Cyan
foreach ($nm in $names) {
    $r=@{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
    for($i=0;$i -lt $records.Count;$i++){
        $r.spent++
        $t=& $GEN[$nm] $i
        $m=($t|Where-Object{$records[$i].N -contains $_}).Count
        if($m -ge 2){ $r[$m.ToString()]++; $r.won+=$prizes[$m.ToString()] }
    }
    $r.net=$r.won-$r.spent; $r.roi=[Math]::Round(($r.won/$r.spent)*100,2)
    $single[$nm]=$r
    Write-Host ("  $nm : Net $($r.net) | M2:$($r['2']) M3:$($r['3']) M4:$($r['4']) | ROI $($r.roi)%") -ForegroundColor White
}

# === DUALI (2 biglietti) ===
$dual=@{}
Write-Host "`n--- DUALI (2 biglietti/estrazione) ---" -ForegroundColor Cyan
for($a=0;$a -lt $names.Count;$a++){
    for($b=$a;$b -lt $names.Count;$b++){
        $n1=$names[$a]; $n2=$names[$b]
        $key = if($n1 -eq $n2){"$n1 x2"}else{"$n1 + $n2"}
        $r=@{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
        for($i=0;$i -lt $records.Count;$i++){
            $t1=& $GEN[$n1] $i; $r.spent++
            $m1=($t1|Where-Object{$records[$i].N -contains $_}).Count
            if($m1 -ge 2){ $r[$m1.ToString()]++; $r.won+=$prizes[$m1.ToString()] }
            $t2=& $GEN[$n2] $i; $r.spent++
            $m2=($t2|Where-Object{$records[$i].N -contains $_}).Count
            if($m2 -ge 2){ $r[$m2.ToString()]++; $r.won+=$prizes[$m2.ToString()] }
        }
        $r.net=$r.won-$r.spent; $r.roi=[Math]::Round(($r.won/$r.spent)*100,2)
        $dual[$key]=$r
    }
}

$bestSingle = ($single.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1)
$bestDual = ($dual.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1)
$worstDual = ($dual.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -Last 1)

Write-Host "`n=== BEST SINGLE: $($bestSingle.Key) (Net $($bestSingle.Value.net), ROI $($bestSingle.Value.roi)%) ===" -ForegroundColor Green
Write-Host "=== BEST DUAL:  $($bestDual.Key) (Net $($bestDual.Value.net), ROI $($bestDual.Value.roi)%) ===" -ForegroundColor Green
Write-Host "=== WORST DUAL: $($worstDual.Key) (Net $($worstDual.Value.net), ROI $($worstDual.Value.roi)%) ===" -ForegroundColor Red

# Salva JSON
$rep=@{
    metadata=@{ draws=$records.Count; singleCount=$names.Count; dualCount=$dual.Count }
    bestSingle=$bestSingle.Key; bestDual=$bestDual.Key; worstDual=$worstDual.Key
    single=@{}; dual=@{}
}
foreach($k in $single.Keys){ $rr=$single[$k]; $rep.single[$k]=@{net=$rr.net;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];m5=$rr['5'];m6=$rr['6'];roi=$rr.roi} }
foreach($k in $dual.Keys){ $rr=$dual[$k]; $rep.dual[$k]=@{net=$rr.net;spent=$rr.spent;won=$rr.won;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];m5=$rr['5'];m6=$rr['6'];roi=$rr.roi} }
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Saved $outPath"