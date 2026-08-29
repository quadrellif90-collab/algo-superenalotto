$line = "1997-12-03,87,20,36,39,41,72,76,88,"
$parts = $line -split ','
Write-Host "Numero parti: $($parts.Count)"
Write-Host "Part[0]: $($parts[0])"
Write-Host "Part[1]: $($parts[1])"
Write-Host "Part[2]: $($parts[2])"
Write-Host "Part[3]: $($parts[3])"
$nums = @([int]($parts[2].Trim()), [int]($parts[3].Trim()), [int]($parts[4].Trim()), [int]($parts[5].Trim()), [int]($parts[6].Trim()), [int]($parts[7].Trim()))
Write-Host "Nums: $($nums -join ', ')"
$sum = ($nums | Measure-Object -Sum).Sum
Write-Host "Sum: $sum"
