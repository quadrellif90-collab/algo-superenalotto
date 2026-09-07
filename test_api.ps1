$apiKey = if ($env:SUPERENALOTTO_API_KEY) { $env:SUPERENALOTTO_API_KEY } else { (Get-Content config.json -Raw | ConvertFrom-Json).apiKey }
if (-not $apiKey) { Write-Host "ERRORE: imposta SUPERENALOTTO_API_KEY o config.json"; exit 1 }
$headers = @{ 'X-API-KEY' = $apiKey }
$uri = 'https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=712'
try {
    $r = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 15 -ErrorAction Stop
    Write-Host "API OK"
    $r | ConvertTo-Json -Depth 3 | Out-File "C:\Users\Siviglino\Desktop\Superenalotto\api_test_result.json" -Encoding UTF8
    Write-Host "Salvato in api_test_result.json"
} catch {
    Write-Host "ERRORE: $($_.Exception.Message)"
}
