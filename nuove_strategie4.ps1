# Quarta tornata - filtri avanzati (1 o 2 biglietti, 4226 draw)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "nuove_strategie4.json"
$records = @()
(Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1) | ForEach-Object {
    $p = $_ -split ','
    if ($p.Count -ge 9) { try { $records += [PSCustomObject]@{ N = @([int]$p[2],[int]$p[3],[int]$p[4],[int]$p[5],[int]$p[6],[int]$p[7]) } } catch {} }
}
Write-Host "Draws: $($records.Count)"
$prizes = @{ "2"=5; "3"=10; "4"=100; "5"=1000; "6"=1000000 }
function Test-Cons { param($nums)
    $s=($nums|Measure-Object -Sum).Sum
    if ($s-lt246 -or $s-gt306){return $false}
    $dd=@{}; foreach($n in $nums){$d=[int][Math]::Floor($n/10); $dd[$d]++; if($dd[$d]-gt2){return $false}}
    if (($nums|Where-Object{$_-gt80}).Count -gt1){return $false}
    return $true
}
function Build-Pool { param([scriptblock]$filter, [int]$size=500)
    $pool=@(); $att=0
    while ($pool.Count -lt $size -and $att++ -lt 400000) {
        $c = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
        if (& $filter $c) { $pool += ,@($c) }
    }
    return $pool
}
$fSupQ={param($n);if(-not(Test-Cons $n)){return $false}
    $q=@(0,0,0,0)
    foreach($x in $n){ if($x-le22){$q[0]++ }elseif($x-le45){$q[1]++}elseif($x-le67){$q[2]++}else{$q[3]++} }
    return ($q[0] -ge 1 -and $q[1] -ge 1 -and $q[2] -ge 1 -and $q[3] -ge 1)
}
$fAnti={param($n);if(-not(Test-Cons $n)){return $false}
    $q=@(0,0,0,0)
    foreach($x in $n){ if($x-le22){$q[0]++ }elseif($x-le45){$q[1]++}elseif($x-le67){$q[2]++}else{$q[3]++} }
    return ($q[0] -le 2 -and $q[1] -le 2 -and $q[2] -le 2 -and $q[3] -le 2)
}
$fSplit={param($n);if(-not(Test-Cons $n)){return $false}
    $lo=($n|Where-Object{$_ -le 30}).Count; $hi=($n|Where-Object{$_ -ge 61}).Count
    return ($lo -eq 3 -and $hi -eq 3)
}
$fWcen={param($n);if(-not(Test-Cons $n)){return $false}
    # pesce gaussiana: almeno 4 numeri in 25-65
    return (($n|Where-Object{$_ -ge 25 -and $_ -le 65}).Count -ge 4)
}
$fPgap={param($n);if(-not(Test-Cons $n)){return $false}
    $pr=@(2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89)
    $gaps=@()
    for($i=0;$i-lt5;$i++){ if($pr -contains $n[$i] -and $pr -contains $n[$i+1]){ $gaps+=$n[$i+1]-$n[$i] } }
    return ($gaps.Count -ge 1)
}
$fMod4={param($n);if(-not(Test-Cons $n)){return $false}
    $r=@(0,0,0,0)
    foreach($x in $n){ $r[$x%4]++ }
    return ($r[0] -ge 1 -and $r[1] -ge 1 -and $r[2] -ge 1 -and $r[3] -ge 1)
}
$poolSupQ=Build-Pool $fSupQ; $poolAnti=Build-Pool $fAnti; $poolSplit=Build-Pool $fSplit
$poolWcen=Build-Pool $fWcen; $poolPgap=Build-Pool $fPgap; $poolMod4=Build-Pool $fMod4
Write-Host "Pools: SupQ=$($poolSupQ.Count) Anti=$($poolAnti.Count) Split=$($poolSplit.Count) Wcen=$($poolWcen.Count) Pgap=$($poolPgap.Count) Mod4=$($poolMod4.Count)"
$GEN = @{
    "SuperQuartile"={param($i)$poolSupQ[$i%$poolSupQ.Count]}
    "AntiCluster"={param($i)$poolAnti[$i%$poolAnti.Count]}
    "SplitHighLow"={param($i)$poolSplit[$i%$poolSplit.Count]}
    "WeightedCenter"={param($i)$poolWcen[$i%$poolWcen.Count]}
    "PrimeGap"={param($i)$poolPgap[$i%$poolPgap.Count]}
    "Mod4Spread"={param($i)$poolMod4[$i%$poolMod4.Count]}
}
$names = $GEN.Keys | Sort-Object
$single=@{}
Write-Host "`n--- SINGOLE (1 biglietto) ---" -ForegroundColor Cyan
foreach($nm in $names){
    $r=@{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
    for($i=0;$i -lt $records.Count;$i++){
        $r.spent++; $t=& $GEN[$nm] $i
        $m=($t|Where-Object{$records[$i].N -contains $_}).Count
        if($m -ge 2){ $r[$m.ToString()]++; $r.won+=$prizes[$m.ToString()] }
    }
    $r.net=$r.won-$r.spent; $r.roi=[Math]::Round(($r.won/$r.spent)*100,2)
    $single[$nm]=$r
    Write-Host ("  $nm : Net $($r.net) | M2:$($r['2']) M3:$($r['3']) M4:$($r['4']) | ROI $($r.roi)%") -ForegroundColor White
}
$dual=@{}
Write-Host "`n--- DUALI (2 biglietti) ---" -ForegroundColor Cyan
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
$bestS=($single.GetEnumerator()|Sort-Object{$_.Value.net}-Descending|Select-Object -First 1)
$bestD=($dual.GetEnumerator()|Sort-Object{$_.Value.net}-Descending|Select-Object -First 1)
Write-Host "`nBEST SINGLE: $($bestS.Key) (Net $($bestS.Value.net), ROI $($bestS.Value.roi)%)" -ForegroundColor Green
Write-Host "BEST DUAL:  $($bestD.Key) (Net $($bestD.Value.net), ROI $($bestD.Value.roi)%)" -ForegroundColor Green
$rep=@{ metadata=@{draws=$records.Count;singleCount=$names.Count;dualCount=$dual.Count}
    bestSingle=$bestS.Key; bestDual=$bestD.Key; single=@{}; dual=@{} }
foreach($k in $single.Keys){$rr=$single[$k];$rep.single[$k]=@{net=$rr.net;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];roi=$rr.roi}}
foreach($k in $dual.Keys){$rr=$dual[$k];$rep.dual[$k]=@{net=$rr.net;spent=$rr.spent;won=$rr.won;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];roi=$rr.roi}}
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Saved $outPath"