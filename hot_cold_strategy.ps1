# Hot-Cold Optimization Strategy
# Statistical analysis based on 4226 historical draws
# Combined hot + cold numbers to maximize probability

$ErrorActionPreference = "Stop"

# Load hot-cold configuration from file
$hotColdConfigPath = Join-Path $PSScriptRoot "hot_cold_config.json"
if (-not (Test-Path $hotColdConfigPath)) {
    Write-Error "Hot-cold configuration file not found: $hotColdConfigPath"
    exit 1
}

$hotColdConfig = Get-Content $hotColdConfigPath -Encoding UTF8 | ConvertFrom-Json

# Statistical Analysis Functions
function Calculate-HotColdStats {
    param([string]$csvPath)
    
    $records = @()
    $lines = Get-Content $csvPath -Encoding UTF8 | Select-Object -Skip 1
    foreach ($line in $lines) {
        $parts = $line -split ','
        if ($parts.Count -ge 9) {
            try {
                $nums = @([int]$parts[2], [int]$parts[3], [int]$parts[4], [int]$parts[5], [int]$parts[6], [int]$parts[7])
                $records += [PSCustomObject]@{ Numbers = $nums }
            } catch { continue }
        }
    }
    
    # Analyze frequency
    $allNumbers = @()
    foreach ($r in $records) { $allNumbers += $r.Numbers }
    
    $frequency = @{}
    foreach ($n in $allNumbers) {
        if ($frequency.ContainsKey($n)) {
            $frequency[$n]++
        } else {
            $frequency[$n] = 1
        }
    }
    
    # Calculate hot/cold thresholds (Top 10% = hot, Bottom 20% = cold)
    $thresholdHot = [Math]::Max(1, [int](($frequency.Values | Measure-Object -Maximum).Maximum * 0.1))
    $thresholdCold = [Math]::Max(1, [int](($frequency.Values | Measure-Object -Minimum).Minimum * 0.2))
    
    $hotNumbers = @($frequency.GetEnumerator() | Where-Object { $_.Value -ge $thresholdHot } | ForEach-Object { $_.Name } | Sort-Object)
    $coldNumbers = @($frequency.GetEnumerator() | Where-Object { $_.Value -le $thresholdCold } | ForEach-Object { $_.Name } | Sort-Object)
    
    return @{ 
        Hot = $hotNumbers 
        Cold = $coldNumbers 
        HotCount = $hotNumbers.Count 
        ColdCount = $coldNumbers.Count 
        FrequencyTable = $frequency
    }
}

# Generate optimized ticket
function Generate-HotColdTicket {
    param(
        [hashtable]$hotColdStats,
        [hashtable]$config,
        [hashtable]$constraints
    )
    
    $attempts = 0
    $maxAttempts = 1000
    
    while ($attempts -lt $maxAttempts) {
        $attempts++
        
        # Build ticket: mix hot and cold numbers
        $hotToUse = if ($config.HotUsage) { [int]($config.HotUsage.MaxSelected * (Get-Random -Maximum 100) / 100) } else { 3 }
        $coldToUse = if ($config.HotUsage) { 6 - $hotToUse } else { 3 }
        
        $selectedHot = @()
        if ($hotColdStats.Hot.Count -gt 0 -and $hotToUse -gt 0) {
            $selectedHot = Get-Random -InputObject ($hotColdStats.Hot | Select-Object -First ($hotToUse))
        }
        
        $selectedCold = @()
        if ($hotColdStats.Cold.Count -gt 0 -and $coldToUse -gt 0) {
            $selectedCold = Get-Random -InputObject ($hotColdStats.Cold | Select-Object -First ($coldToUse))
        }
        
        $ticketNumbers = $selectedHot + $selectedCold
        $ticketNumbers = $ticketNumbers | Sort-Object
        
        # Apply constraints
        $sum = $ticketNumbers | Measure-Object -Sum | ForEach-Object { $_.Sum }
        
        # Constraint: Sum between mean ± 30
        if (-not ($sum -ge $constraints.Mean - 30 -and $sum -le $constraints.Mean + 30)) {
            continue
        }
        
        # Constraint: Max 2 numbers per decade
        $decadeDist = @{}
        foreach ($n in $ticketNumbers) {
            $decade = [int][Math]::Floor($n / 10)
            if ($decadeDist.ContainsKey($decade)) {
                $decadeDist[$decade]++
            } else {
                $decadeDist[$decade] = 1
            }
        }
        if ($decadeDist.Values -contains 3) { continue }
        
        # Constraint: Max 1 number > 80
        $highCount = ($ticketNumbers | Where-Object { $_ -gt 80 }).Count
        if ($highCount -gt 1) { continue }
        
        # Statistical balance check
        $gt31Ratio = ($ticketNumbers | Where-Object { $_ -gt 31 }).Count / 6.0
        $expectedGt31Ratio = $hotColdConfig.Expected.gt31Ratio
        if ([Math]::Abs($gt31Ratio - $expectedGt31Ratio) -gt 0.15) { continue }
        
        # Age balance (evita numeri recentissimi ripetuti troppe volte)
        $consecutiveIssues = $true
        if ($global:TicketHistory) {
            $recentDraws = $global:TicketHistory[-5..-1]
            foreach ($num in $ticketNumbers) {
                $occurrences = ($recentDraws | Where-Object { $_.Numbers -contains $num }).Count
                if ($occurrences -gt 2) {
                    $consecutiveIssues = $false
                    break
                }
            }
        }
        if (-not $consecutiveIssues) { continue }
        
        return $ticketNumbers
    }
    
    return $null
}

# Main execution
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csvPath = Join-Path $scriptDir "superenalotto.csv"

Write-Host "=== Hot-Cold Optimization Strategy ===" -ForegroundColor Cyan
Write-Host "Loading 4226 historical draws..." -ForegroundColor White

# Calculate statistics
$hotColdStats = Calculate-HotColdStats -csvPath $csvPath

Write-Host "Hot numbers (top 10% frequency): $($hotColdStats.Hot.Count)" -ForegroundColor Yellow
Write-Host "Cold numbers (bottom 20% frequency): $($hotColdStats.Cold.Count)" -ForegroundColor Yellow

# Load constraints
$constraints = @{ 
    Mean = 276 
}

# Generate tickets
$tickets = @()
$ticketCount = if ($hotColdConfig.Strategy.TicketCount) { $hotColdConfig.Strategy.TicketCount } else { 5 }

for ($i = 0; $i -lt $ticketCount; $i++) {
    Write-Host "Generating ticket $($i + 1) of $ticketCount..." -ForegroundColor White
    $ticket = Generate-HotColdTicket -hotColdStats $hotColdStats -config $hotColdConfig -constraints $constraints
    
    if ($ticket) {
        $tickets += @{ Index = ($i + 1); Numbers = $ticket; Sum = ($ticket | Measure-Object -Sum).Sum }
        Write-Host "  Ticket $($i + 1): $($ticket -join ', ') (Sum: $(($ticket | Measure-Object -Sum).Sum))" -ForegroundColor Green
    } else {
        Write-Host "  Failed to generate valid ticket" -ForegroundColor Red
    }
}

# Save tickets
$hotColdOutputPath = Join-Path $scriptDir "hot_cold_tickets.json"
$hotColdOutput = @{ 
    Strategy = "Hot-Cold Optimization" 
    Statistics = $hotColdStats 
    Tickets = $tickets 
    Configuration = $hotColdConfig 
}
$hotColdOutput | ConvertTo-Json -Depth 10 | Set-Content -Path $hotColdOutputPath -Encoding UTF8

Write-Host "`n=== Hot-Cold Strategy Complete ===" -ForegroundColor Cyan
Write-Host "Tickets saved to: $hotColdOutputPath" -ForegroundColor Yellow
Write-Host "Total tickets generated: $($tickets.Count)" -ForegroundColor White