$csvPath = "C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv"
$newDraws = @(
    "2026-08-25,,15,36,62,67,69,70,32,15",
    "2026-08-22,,2,16,23,31,72,85,82,14",
    "2026-08-21,,12,25,27,28,39,57,42,13"
)
foreach ($draw in $newDraws) {
    Add-Content -Path $csvPath -Value $draw -Encoding UTF8
}
Write-Host "Aggiunte 3 estrazioni. Ultime righe:"
Get-Content $csvPath | Select-Object -Last 5
