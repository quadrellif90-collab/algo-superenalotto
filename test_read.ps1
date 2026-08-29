$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
$lines = Get-Content $csvPath | Select-Object -Skip 1
$count = 0
foreach ($l in $lines) {
    $p = $l -split ','
    if ($p.Count -ge 9) { $count++ }
}
Write-Host "Record validi: $count"
