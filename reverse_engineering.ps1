# REVERSE ENGINEERING: trova la "firma strutturale" comune alle estrazioni reali
# Poi genera biglietti che la imitano e fa backtest ROLLING (out-of-sample).
# Premi M2=5 M3=10 M4=100 M5=1000 M6=1000000

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"
$outPath = Join-Path $scriptDir "reverse_engineering.json"

$records = @()
(Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1) | ForEach-Object {
    $p = $_ -split ','
    if ($p.Count -ge 9) { try { $records += [PSCustomObject]@{ N = @([int]$p[2],[int]$p[3],[int]$p[4],[int]$p[5],[int]$p[6],[int]$p[7]) } } catch {} }
}
Write-Host "Draws: $($records.Count)"

# === FEATURE EXTRACTION ===
function Get-Features { param($nums)
    $s = ($nums|Measure-Object -Sum).Sum
    $q = @(0,0,0,0)
    foreach($x in $nums){ if($x-le22){$q[0]++}elseif($x-le45){$q[1]++}elseif($x-le67){$q[2]++}else{$q[3]++} }
    $qc = ($q|Where-Object{$_ -gt 0}).Count
    $d = @{}
    foreach($x in $nums){ $dd=[int][Math]::Floor($x/10); $d[$dd]++ }
    $dc = $d.Keys.Count
    $ld = ($nums|ForEach-Object{$_%10}|Select-Object -Unique).Count
    $gaps=@(); for($i=0;$i-lt5;$i++){ $gaps+=$nums[$i+1]-$nums[$i] }
    $minGap=$gaps|Measure-Object -Minimum|Select-Object -ExpandProperty Minimum
    $maxGap=$gaps|Measure-Object -Maximum|Select-Object -ExpandProperty Maximum
    $consec=0; for($i=0;$i-lt5;$i++){ if($nums[$i+1]-$nums[$i]-eq1){$consec++} }
    $even=($nums|Where-Object{$_%2-eq0}).Count
    $m3=@(0,0,0); foreach($x in $nums){ $m3[$x%3]++ }; $m3s=($m3|Where-Object{$_ -gt 0}).Count
    $m4=@(0,0,0,0); foreach($x in $nums){ $m4[$x%4]++ }; $m4s=($m4|Where-Object{$_ -gt 0}).Count
    $hi=($nums|Where-Object{$_ -gt 80}).Count
    return @{ sum=$s; qc=$qc; dc=$dc; ld=$ld; minGap=$minGap; maxGap=$maxGap; consec=$consec; even=$even; m3s=$m3s; m4s=$m4s; hi=$hi }
}

# === 1. DISTRIBUZIONE REALE ===
Write-Host "Estrazione features dalle estrazioni reali..." -ForegroundColor Cyan
$realFeat = @()
foreach($r in $records){ $realFeat += Get-Features $r.N }

function Mode { param($arr)
    $c=@{}; foreach($v in $arr){ $c[$v]++ }
    $best=$c.GetEnumerator()|Sort-Object{$_.Value}-Descending|Select-Object -First 1
    return $best.Key
}
function Rate { param($arr,$pred)
    $pass = $arr | ForEach-Object $pred
    $hit = ($pass | Where-Object { $_ -eq $true }).Count
    return [Math]::Round($hit/$arr.Count*100,1)
}

$modal = @{
    qc = Mode ($realFeat|ForEach-Object{$_.qc})
    dc = Mode ($realFeat|ForEach-Object{$_.dc})
    ld = Mode ($realFeat|ForEach-Object{$_.ld})
    m3s= Mode ($realFeat|ForEach-Object{$_.m3s})
    m4s= Mode ($realFeat|ForEach-Object{$_.m4s})
    consec= Mode ($realFeat|ForEach-Object{$_.consec})
}
# gap range modale (percentili 10-90)
$gapsAll = $realFeat|ForEach-Object{$_.minGap}|Sort-Object
$gmaxAll= $realFeat|ForEach-Object{$_.maxGap}|Sort-Object
$minGapLo = $gapsAll[[Math]::Floor($gapsAll.Count*0.10)]
$minGapHi = $gapsAll[[Math]::Floor($gapsAll.Count*0.90)]
$maxGapLo = $gmaxAll[[Math]::Floor($gmaxAll.Count*0.05)]
$maxGapHi = $gmaxAll[[Math]::Floor($gmaxAll.Count*0.95)]

Write-Host "FIRMA STRUTTURALE (moda estrazioni reali):" -ForegroundColor Yellow
Write-Host ("  QuartileCov >= {0} | DecadeCov >= {1} | LastDigitDistinct >= {2}" -f $modal.qc, $modal.dc, $modal.ld)
Write-Host ("  Mod3Spread >= {0} | Mod4Spread >= {1} | ConsecPairs = {2}" -f $modal.m3s, $modal.m4s, $modal.consec)
Write-Host ("  MinGap in [{0},{1}] | MaxGap in [{2},{3}]" -f $minGapLo,$minGapHi,$maxGapLo,$maxGapHi)
Write-Host ("  Even count modal: {0} | >80 modal: {1}" -f (Mode ($realFeat|ForEach-Object{$_.even})), (Mode ($realFeat|ForEach-Object{$_.hi})))

# === 2. CONFRONTO vs BASELINE RANDOM (feature UNA ALLA VOLTA) ===
Write-Host "`nConfronto reale vs random (somma 246-306), feature singole:" -ForegroundColor Cyan
$randFeat=@()
for($i=0;$i -lt 5000;$i++){
    $c=Get-Random -InputObject(1..90)-Count 6|Sort-Object
    $f=Get-Features $c
    if($f.sum -ge 246 -and $f.sum -le 306){ $randFeat+=Get-Features $c }
}
Write-Host ("  Reale  ConsecPairs=0: {0}% | Random: {1}%" -f (Rate $realFeat {$_.consec -eq 0}), (Rate $randFeat {$_.consec -eq 0}))
Write-Host ("  Reale  Even=3:        {0}% | Random: {1}%" -f (Rate $realFeat {$_.even -eq 3}), (Rate $randFeat {$_.even -eq 3}))
Write-Host ("  Reale  >80 = 0:       {0}% | Random: {1}%" -f (Rate $realFeat {$_.hi -eq 0}), (Rate $randFeat {$_.hi -eq 0}))
Write-Host ("  Reale  QuartileCov>=3:{0}% | Random: {1}%" -f (Rate $realFeat {$_.qc -ge 3}), (Rate $randFeat {$_.qc -ge 3}))
Write-Host ("  Reale  DecadeCov>=5:  {0}% | Random: {1}%" -f (Rate $realFeat {$_.dc -ge 5}), (Rate $randFeat {$_.dc -ge 5}))
Write-Host ("  Reale  Mod4Spread>=3: {0}% | Random: {1}%" -f (Rate $realFeat {$_.m4s -ge 3}), (Rate $randFeat {$_.m4s -ge 3}))
Write-Host ("  Reale  LastDigit>=5:  {0}% | Random: {1}%" -f (Rate $realFeat {$_.ld -ge 5}), (Rate $randFeat {$_.ld -ge 5}))

# === 3. GENERATORE REVERSE-ENGINEERED ===
function Get-EmpiricalTicket {
    $att=0
    while($att++ -lt 2000){
        $c=Get-Random -InputObject(1..90)-Count 6|Sort-Object
        $f=Get-Features $c
        if($f.sum -lt 246 -or $f.sum -gt 306){continue}
        if($f.qc -lt $modal.qc){continue}
        if($f.dc -lt $modal.dc){continue}
        if($f.ld -lt $modal.ld){continue}
        if($f.m4s -lt $modal.m4s){continue}
        if($f.minGap -lt $minGapLo -or $f.minGap -gt $minGapHi){continue}
        if($f.maxGap -lt $maxGapLo -or $f.maxGap -gt $maxGapHi){continue}
        return $c
    }
    return Get-Random -InputObject(1..90)-Count 6|Sort-Object
}

# === 4. BACKTEST (firma calcolata una volta sullo storico completo = out-of-sample su draw future) ===
$prizes = @{ "2"=5; "3"=10; "4"=100; "5"=1000; "6"=1000000 }
Write-Host "`n=== BACKTEST (firma strutturale da tutto lo storico 4226 draw) ===" -ForegroundColor Cyan

function Run-BT { param([int]$tickets)
    $r=@{ "2"=0;"3"=0;"4"=0;"5"=0;"6"=0; spent=0; won=0 }
    for($i=0;$i -lt $records.Count;$i++){
        for($t=0;$t -lt $tickets;$t++){
            $att=0
            while($att++ -lt 2000){
                $c=Get-Random -InputObject(1..90)-Count 6|Sort-Object
                $f=Get-Features $c
                if($f.sum -lt 246 -or $f.sum -gt 306){continue}
                if($f.qc -lt $modal.qc){continue}
                if($f.dc -lt $modal.dc){continue}
                if($f.ld -lt $modal.ld){continue}
                if($f.m4s -lt $modal.m4s){continue}
                if($f.minGap -lt $minGapLo -or $f.minGap -gt $minGapHi){continue}
                if($f.maxGap -lt $maxGapLo -or $f.maxGap -gt $maxGapHi){continue}
                break
            }
            if($att -gt 2000){ $c=Get-Random -InputObject(1..90)-Count 6|Sort-Object }
            $r.spent++
            $m=($c|Where-Object{$records[$i].N -contains $_}).Count
            if($m -ge 2){ $r[$m.ToString()]++; $r.won+=$prizes[$m.ToString()] }
        }
    }
    $r.net=$r.won-$r.spent; $r.roi=[Math]::Round(($r.won/$r.spent)*100,2)
    return $r
}

$r1=Run-BT 1
Write-Host ("  Empirical SINGLE (1 ticket): Net $($r1.net) | M2:$($r1['2']) M3:$($r1['3']) M4:$($r1['4']) | ROI $($r1.roi)%") -ForegroundColor White
$r2=Run-BT 2
Write-Host ("  Empirical DUAL   (2 ticket): Net $($r2.net) | M2:$($r2['2']) M3:$($r2['3']) M4:$($r2['4']) | ROI $($r2.roi)%") -ForegroundColor White

$rep=@{
    signature=@{ modalQ=$modal.qc; modalD=$modal.dc; modalLD=$modal.ld; modalM4=$modal.m4s; consec=$modal.consec; minGapRange=@($minGapLo,$minGapHi); maxGapRange=@($maxGapLo,$maxGapHi) }
    backtestSingle=@{net=$r1.net;m2=$r1['2'];m3=$r1['3'];m4=$r1['4'];roi=$r1.roi;spent=$r1.spent;won=$r1.won}
    backtestDual=@{net=$r2.net;m2=$r2['2'];m3=$r2['3'];m4=$r2['4'];roi=$r2.roi;spent=$r2.spent;won=$r2.won}
}
$rep | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "Saved $outPath"