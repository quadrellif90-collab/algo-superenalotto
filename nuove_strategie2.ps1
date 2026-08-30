# NUOVE STRATEGIE - filtri aggiuntivi (1 o 2 biglietti, 4226 draw)
# Premi M2=5 M3=10 M4=100 M5=1000 M6=1000000

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "nuove_strategie2.json"

$records = @()
(Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1) | ForEach-Object {
    $p = $_ -split ','
    if ($p.Count -ge 9) {
        try { $records += [PSCustomObject]@{ N = @([int]$p[2],[int]$p[3],[int]$p[4],[int]$p[5],[int]$p[6],[int]$p[7]) } } catch {}
    }
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

$fLDS={param($n);if(-not(Test-Cons $n)){return $false};return (($n|ForEach-Object{$_%10}|Select-Object -Unique).Count -eq 6)}
$fSum={param($n);$s=($n|Measure-Object -Sum).Sum;return ($s -ge 270 -and $s -le 282)}
$fNoCon={param($n);if(-not(Test-Cons $n)){return $false};for($i=0;$i-lt5;$i++){if($n[$i+1]-$n[$i]-eq1){return $false}};return $true}
$fTri={param($n);if(-not(Test-Cons $n)){return $false};$g=90;for($i=0;$i-lt5;$i++){$gp=$n[$i+1]-$n[$i];if($gp-lt$g){$g=$gp}};return $g-ge15}
$fLow={param($n);if(-not(Test-Cons $n)){return $false};$lo=($n|Where-Object{$_-le45}).Count;return ($lo -eq 4)}
$fMod={param($n);if(-not(Test-Cons $n)){return $false};$r0=($n|Where-Object{$_%3-eq0}).Count;$r1=($n|Where-Object{$_%3-eq1}).Count;$r2=($n|Where-Object{$_%3-eq2}).Count;return ($r0 -ge 1 -and $r1 -ge 1 -and $r2 -ge 1)}
$fQuart={param($n);if(-not(Test-Cons $n)){return $false}
    $q1=($n|Where-Object{$_-le22}).Count
    $q2=($n|Where-Object{$_ -ge23 -and $_ -le45}).Count
    $q3=($n|Where-Object{$_ -ge46 -and $_ -le67}).Count
    $q4=($n|Where-Object{$_ -ge68}).Count
    return ($q1 -ge 1 -and $q2 -ge 1 -and $q3 -ge 1 -and $q4 -ge 1)
}

$poolLDS=Build-Pool $fLDS; $poolSum=Build-Pool $fSum; $poolNoCon=Build-Pool $fNoCon
$poolTri=Build-Pool $fTri; $poolLow=Build-Pool $fLow; $poolMod=Build-Pool $fMod; $poolQuart=Build-Pool $fQuart
Write-Host "Pools: LDS=$($poolLDS.Count) Sum=$($poolSum.Count) NoCon=$($poolNoCon.Count) Tri=$($poolTri.Count) Low=$($poolLow.Count) Mod=$($poolMod.Count) Quart=$($poolQuart.Count)"

$GEN = @{
    "LastDigitSpread"  = { param($i) $poolLDS[$i % $poolLDS.Count] }
    "SumBandTight"     = { param($i) $poolSum[$i % $poolSum.Count] }
    "NoConsecutive"    = { param($i) $poolNoCon[$i % $poolNoCon.Count] }
    "TripleGap"        = { param($i) $poolTri[$i % $poolTri.Count] }
    "LowHalfBias"      = { param($i) $poolLow[$i % $poolLow.Count] }
    "Mod3Balanced"     = { param($i) $poolMod[$i % $poolMod.Count] }
    "QuartileSpread"   = { param($i) $poolQuart[$i % $poolQuart.Count] }
}

$names = $GEN.Keys | Sort-Object
Write-Host "Strategie nuove: $($names.Count) | Combos dual: $(($names.Count*($names.Count+1))/2)"

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

$rep=@{ metadata=@{draws=$records.Count; singleCount=$names.Count; dualCount=$dual.Count}
    bestSingle=$bestS.Key; bestDual=$bestD.Key; single=@{}; dual=@{} }
foreach($k in $single.Keys){$rr=$single[$k];$rep.single[$k]=@{net=$rr.net;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];roi=$rr.roi}}
foreach($k in $dual.Keys){$rr=$dual[$k];$rep.dual[$k]=@{net=$rr.net;spent=$rr.spent;won=$rr.won;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];roi=$rr.roi}}
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Saved $outPath"