$jsonPath = "C:\Users\Siviglino\Desktop\Superenalotto\all_results.json"
$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"

$allResults = Get-Content $jsonPath -Raw | ConvertFrom-Json
$results = $allResults.results

Write-Host "Estrazioni API recenti: $($results.Count)"
Write-Host ""

$newLines = @()
foreach ($r in $results) {
    $date = $r.draw_date
    $balls = $r.balls
    $jolly = if ($r.ball_bonus -and $r.ball_bonus.Count -gt 0) { $r.ball_bonus[0] } else { 0 }
    $superstar = if ($r.ball_bonus -and $r.ball_bonus.Count -gt 1) { $r.ball_bonus[1] } else { 0 }
    $concorso = $r.id
    
    $line = "$date,$concorso,$($balls[0]),$($balls[1]),$($balls[2]),$($balls[3]),$($balls[4]),$($balls[5]),$jolly,$superstar"
    $newLines += $line
}

$csvContent = Get-Content $csvPath
$lastDate = ($csvContent[-1] -split ',')[0]
Write-Host "Ultima data nel CSV: $lastDate"

$toAdd = $newLines | Where-Object { ($_ -split ',')[0] -gt $lastDate }
Write-Host "Estrazioni da aggiungere: $($toAdd.Count)"

if ($toAdd.Count -gt 0) {
    Write-Host ""
    Write-Host "Nuove estrazioni:"
    foreach ($line in $toAdd) {
        Write-Host "  $line"
    }
    
    $toAdd | ForEach-Object { Add-Content -Path $csvPath -Value $_ }
    Write-Host ""
    Write-Host "CSV aggiornato con $($toAdd.Count) nuove estrazioni!"
    
    $newCount = (Get-Content $csvPath).Count - 1
    Write-Host "Nuovo totale: $newCount estrazioni"
} else {
    Write-Host "Nessuna nuova estrazione da aggiungere."
}
