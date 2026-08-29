$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$csvPath = Join-Path $scriptDir "superenalotto.csv"
function Get-Stats {
    $lines = Get-Content $csvPath | Select-Object -Skip 1
    $records = @()
    foreach ($line in $lines) {
        $parts = $line -split ','
        if ($parts.Count -ge 9) {
            try {
                $nums = @([int]($parts[2].Trim()), [int]($parts[3].Trim()), [int]($parts[4].Trim()),
                           [int]($parts[5].Trim()), [int]($parts[6].Trim()), [int]($parts[7].Trim()))
                if ($nums.All({$_ -ge 1 -and $_ -le 90})) {
                    $records += [PSCustomObject]@{
                        Date = $parts[0]
                        Nums = $nums
                        Sum = ($nums | Measure-Object -Sum).Sum
                    }
                }
            } catch {}
        }
    }
    return $records
}
$records = Get-Stats
Write-Host "Record: $($records.Count)"
if ($records.Count -gt 0) {
    Write-Host "Primo: $($records[0].Date) - $($records[0].Nums)"
}