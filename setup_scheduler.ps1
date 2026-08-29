# setup_scheduler.ps1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$taskName = "SuperEnalotto_Sniper_Full"
$scriptDir = "C:\Users\Siviglino\Desktop\Superenalotto"
$scriptPath = Join-Path $scriptDir "sniper_full.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday, Thursday, Friday, Saturday -At "08:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Disattivazione scheduler esistente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "SuperEnalotto Sniper Completo: Update + Backtest + Verifica + Generazione + Export" | Out-Null

Write-Host "Scheduler attivato: $taskName" -ForegroundColor Green
Write-Host "Esecuzione automatica: Mar, Gio, Ven, Sab ore 08:00" -ForegroundColor Green
Write-Host "Altre esecuzioni manuali: lanciarli come powershell -File '$scriptPath'" -ForegroundColor Gray
[System.Windows.Forms.MessageBox]::Show("Scheduler attivo!`nEsecuzione: Mar/Gio/Ven/Sab 08:00`n`n" +
    "Il protocollo esegue automaticamente:`n" +
    "1. Aggiornamento CSV da API`n" +
    "2. Backtest con i dati aggiornati`n" +
    "3. Verifica vincite (se presenti)`n" +
    "4. Generazione nuove schedine (max 2/giorno)`n" +
    "5. Salvataggio tracking e limiti`n" +
    "6. Report settimanale`n",
    "Scheduler Configurato",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information)
