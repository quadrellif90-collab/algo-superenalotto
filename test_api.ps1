$headers = @{ 'X-API-KEY' = '170961|hANG0dLIQx1exfP7UHLxfx8lwlg8FGQMmxHRQ1CO0117787d' }
$uri = 'https://api.lotteryresultsfeed.com/v1/results/latest?lottery_id=712'
try {
    $r = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 15 -ErrorAction Stop
    Write-Host "API OK"
    $r | ConvertTo-Json -Depth 3 | Out-File "C:\Users\Siviglino\Desktop\Superenalotto\api_test_result.json" -Encoding UTF8
    Write-Host "Salvato in api_test_result.json"
} catch {
    Write-Host "ERRORE: $($_.Exception.Message)"
}
