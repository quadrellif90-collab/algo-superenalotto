$csv = Import-Csv 'C:\Users\Siviglino\Desktop\Superenalotto\superenalotto.csv'
Write-Host "Total records: $($csv.Count)"
Write-Host "First: $($csv[0] | ConvertTo-Json -Compress)"
Write-Host "Last: $($csv[-1] | ConvertTo-Json -Compress)"
