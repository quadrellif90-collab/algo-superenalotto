# Terza tornata strategie - filtri aggiuntivi (1 o 2 biglietti, 4226 draw)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "nuove_strategie3.json"
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
$fEven={param($n);if(-not(Test-Cons $n)){return $false};return (($n|Measure-Object -Sum).Sum)%2 -eq 0}
$fCen={param($n);if(-not(Test-Cons $n)){return $false};return (($n|Where-Object{$_ -ge 30 -and $_ -le 60}).Count -ge 4)}
$fHar={param($n);if(-not(Test-Cons $n)){return $false}
    # almeno 3 numeri in rapporto 2:3 (ovvero diff multipli di 3 o coppie con gap *1.5)
    $ok=$false
    for($i=0;$i-lt5;$i++){for($j=$i+1;$j-lt6;$j++){ if(($n[$j]-$n[$i]) -eq 3 -or ($n[$j]-$n[$i]) -eq 6){ $ok=$true } }}
    return $ok
}
$fFib={param($n);if(-not(Test-Cons $n)){return $false}
    $fib=@(1,2,3,5,8,13,21,34,55,89)
    return (($n|Where-Object{$fib -contains $_}).Count -ge 2)
}
$f6Dec={param($n);if(-not(Test-Cons $n)){return $false}
    $dmax=@{};foreach($x in $n){$d=[int][Math]::Floor($x/10);$dmax[$d]++};return ($dmax.Keys.Count -eq 6)
}
$fFix={param($n);if(-not(Test-Cons $n)){return $false}
    # distanza minima esattamente 10-16
    $g=90;for($i=0;$i-lt5;$i++){$gp=$n[$i+1]-$n[$i];if($gp-lt$g){$g=$gp}};return ($g -ge 10 -and $g -le 16)
}
$poolEven=Build-Pool $fEven; $poolCen=Build-Pool $fCen; $poolHar=Build-Pool $fHar
$poolFib=Build-Pool $fFib; $pool6Dec=Build-Pool $f6Dec; $poolFix=Build-Pool $fFix
Write-Host "Pools: Even=$($poolEven.Count) Cen=$($poolCen.Count) Har=$($poolHar.Count) Fib=$($poolFib.Count) 6Dec=$($pool6Dec.Count) Fix=$($poolFix.Count)"
$GEN = @{
    "EvenSum"={param($i)$poolEven[$i%$poolEven.Count]}
    "CenterBias"={param($i)$poolCen[$i%$poolCen.Count]}
    "HarmonicGap"={param($i)$poolHar[$i%$poolHar.Count]}
    "Fibonacci"={param($i)$poolFib[$i%$poolFib.Count]}
    "SixDecades"={param($i)$pool6Dec[$i%$pool6Dec.Count]}
    "FixedGap"={param($i)$poolFix[$i%$poolFix.Count]}
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