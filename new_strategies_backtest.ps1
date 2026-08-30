# Nuove strategie "outside the box" - backtest 4226 estrazioni (versione veloce)
# Pool pre-calcolati una volta sola, poi solo lookup. Premi M2=5..M6=1000000

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "new_strategies_backtest.json"

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

# Costruttore di pool vincolato (generato una volta)
function Build-Pool { param([scriptblock]$filter, [int]$size=400)
    $pool = @()
    $att = 0
    while ($pool.Count -lt $size -and $att++ -lt 200000) {
        $c = Get-Random -InputObject (1..90) -Count 6 | Sort-Object
        if (& $filter $c) { $pool += ,@($c) }
    }
    return $pool
}

$fCon = { param($nums)
    $s=($nums|Measure-Object -Sum).Sum
    if ($s-lt246 -or $s-gt306){return $false}
    $dd=@{}; foreach($n in $nums){$d=[int][Math]::Floor($n/10); $dd[$d]++; if($dd[$d]-gt2){return $false}}
    if (($nums|Where-Object{$_-gt80}).Count -gt1){return $false}
    return $true
}
$fMid = { param($nums)
    if (-not (Test-Cons $nums)) { return $false }
    foreach ($n in $nums) { if ($freq[$n] -lt $midLo -or $freq[$n] -gt $midHi) { return $false } }
    return $true
}
$fOnePair = { param($nums)
    if (-not (Test-Cons $nums)) { return $false }
    $pairs=0; for($i=0;$i-lt5;$i++){ if($nums[$i+1]-$nums[$i]-eq1){$pairs++} }
    return $pairs -eq 1
}
$fGap = { param($nums)
    if (-not (Test-Cons $nums)) { return $false }
    $g=90; for($i=0;$i-lt5;$i++){ $gap=$nums[$i+1]-$nums[$i]; if($gap-lt$g){$g=$gap} }
    return $g -ge 11
}

function Test-Cons { param($nums)
    $s=($nums|Measure-Object -Sum).Sum
    if ($s-lt246 -or $s-gt306){return $false}
    $dd=@{}; foreach($n in $nums){$d=[int][Math]::Floor($n/10); $dd[$d]++; if($dd[$d]-gt2){return $false}}
    if (($nums|Where-Object{$_-gt80}).Count -gt1){return $false}
    return $true
}

Write-Host "Building pools..." -ForegroundColor Yellow
$wheel = @(
    @(5,17,28,41,59,83),@(3,14,33,47,62,88),@(9,22,35,51,70,85),
    @(2,19,30,44,66,79),@(11,24,38,52,73,90),@(6,20,36,49,64,81),
    @(8,16,29,46,60,87),@(1,25,37,53,68,84),@(13,27,40,55,71,89),@(4,18,31,48,63,82)
)
$poolMid = Build-Pool $fMid
$poolOne = Build-Pool $fOnePair
$poolGap = Build-Pool $fGap
Write-Host "Pools: Mid=$($poolMid.Count) OnePair=$($poolOne.Count) Gap=$($poolGap.Count)"

$strats = @{
    "TemporalRotation"    = { param($i) $wheel[$i % 10] | Sort-Object }
    "ComplementMirror"    = { $a=Get-Random -InputObject (1..45) -Count 3 | Sort-Object; ($a + ($a|ForEach-Object{91-$_})) | Sort-Object }
    "MiddleFrequency"     = { param($i) $poolMid[$i % $poolMid.Count] }
    "OneConsecutivePair"  = { param($i) $poolOne[$i % $poolOne.Count] }
    "GapSpread"           = { param($i) $poolGap[$i % $poolGap.Count] }
}

$res = @{}
Write-Host "`n=== NEW STRATEGIES (1 ticket/draw, 4226 draws) ==="
foreach ($name in $strats.Keys) {
    $r = @{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
    for ($i=0;$i -lt $records.Count;$i++) {
        $r.spent++
        $t = & $strats[$name] $i
        $m = ($t | Where-Object { $records[$i].N -contains $_ }).Count
        if ($m -ge 2) { $r[$m.ToString()]++; $r.won += $prizes[$m.ToString()] }
    }
    $r.net = $r.won - $r.spent
    $r.roi = [Math]::Round(($r.won/$r.spent)*100,2)
    $res[$name] = $r
    Write-Host ("  $name : Net $($r.net) | M2:$($r['2']) M3:$($r['3']) M4:$($r['4']) M5:$($r['5']) M6:$($r['6']) | ROI $($r.roi)%") -ForegroundColor White
}
$best = ($res.GetEnumerator() | Sort-Object { $_.Value.net } -Descending | Select-Object -First 1)
Write-Host "`nBEST: $($best.Key) (Net $($best.Value.net), ROI $($best.Value.roi)%)" -ForegroundColor Green

$rep = @{ metadata=@{draws=$records.Count;ticketsPerDraw=1}; best=$best.Key; strategies=@{} }
foreach ($k in $res.Keys) {
    $rr=$res[$k]
    $rep.strategies[$k]=@{spent=$rr.spent;won=$rr.won;net=$rr.net;m2=$rr['2'];m3=$rr['3'];m4=$rr['4'];m5=$rr['5'];m6=$rr['6'];roi=$rr.roi}
}
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Saved $outPath"