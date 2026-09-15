# ITH - Prisoft auto-recovery installer (run as Administrator on PRISOFT-SERVER)
# What it changes (undo with UNINSTALL_AutoRecovery.bat):
#   1. Windows signs in to this account automatically after a restart (account has no password)
#   2. Never sleep / hibernate; the case power button does nothing (Start > Shut down still works;
#      holding the button 4+ seconds still forces power off)
#   3. Scheduled task ITH_Prisoft_Guard: runs prisoft_guard.py every minute
#   4. ITH_Bearing_Temp_Update: allowed on battery/UPS, restarts if missed
#   5. Restarts the Telegram listener so the new Prisoft buttons work
param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'

$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$guard = Join-Path $here 'prisoft_guard.py'
$wl    = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
# the account Windows signs in to (ith_p on PRISOFT-SERVER) - not whoever elevated this window
$user  = (Get-ItemProperty $wl -ErrorAction SilentlyContinue).DefaultUserName
if (-not $user) { $user = $env:USERNAME }

function Step($n, $t) { Write-Host ""; Write-Host "[$n] $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "    OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "    !!  $t" -ForegroundColor Yellow }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "Please right-click the .bat and choose 'Run as administrator'." -ForegroundColor Red; exit 1 }

# ------------------------------------------------------------------ UNINSTALL
if ($Uninstall) {
  Step 1 "Remove scheduled task ITH_Prisoft_Guard"
  try { Unregister-ScheduledTask -TaskName 'ITH_Prisoft_Guard' -Confirm:$false; Ok "removed" } catch { Warn "task not found" }
  Step 2 "Turn off automatic sign-in"
  Set-ItemProperty $wl -Name AutoAdminLogon -Value '0'
  Remove-ItemProperty $wl -Name DefaultPassword -ErrorAction SilentlyContinue
  Ok "AutoAdminLogon=0"
  Step 3 "Power button back to 'Shut down'"
  powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 3 | Out-Null
  powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 3 | Out-Null
  powercfg /setactive SCHEME_CURRENT | Out-Null
  Ok "done (never-sleep setting is left as is)"
  exit 0
}

# ------------------------------------------------------------------ 0) checks
Step 0 "Checks"
if (-not (Test-Path $guard)) { Write-Host "prisoft_guard.py not found next to this script. Run: git pull --rebase origin main" -ForegroundColor Red; exit 1 }
$pyw = $null
foreach ($c in @((Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source, 'C:\Python314\pythonw.exe')) {
  if ($c -and (Test-Path $c)) { $pyw = $c; break }
}
if (-not $pyw) { Write-Host "pythonw.exe not found" -ForegroundColor Red; exit 1 }
$py = Join-Path (Split-Path $pyw) 'python.exe'
Ok "user=$user  python=$pyw"
$gui = 'C:\Primus\Prisoft\Primus-task-control-win32-x64\Primus-task-control.exe'
if (Test-Path $gui) { Ok "Prisoft found" } else { Warn "Prisoft not found at $gui (guard settings may need editing)" }
$startup = [Environment]::GetFolderPath('Startup')
if (Get-ChildItem $startup -Filter 'Primus-task-control*' -ErrorAction SilentlyContinue) { Ok "Prisoft is in the Startup folder" }
else { Warn "Prisoft is NOT in the Startup folder - the guard will start it instead" }

# ------------------------------------------------------------------ 1) auto sign-in
Step 1 "Automatic sign-in as '$user' after restart"
Set-ItemProperty $wl -Name AutoAdminLogon    -Value '1'
Set-ItemProperty $wl -Name DefaultUserName   -Value $user
Set-ItemProperty $wl -Name DefaultDomainName -Value $env:COMPUTERNAME
Set-ItemProperty $wl -Name DefaultPassword   -Value ''
Remove-ItemProperty $wl -Name AutoLogonCount -ErrorAction SilentlyContinue
$pl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device'
if (-not (Test-Path $pl)) { New-Item $pl -Force | Out-Null }
Set-ItemProperty $pl -Name DevicePasswordLessBuildVersion -Value 0 -Type DWord
Ok "AutoAdminLogon=1 (works because this account has no password)"

# ------------------------------------------------------------------ 2) power
Step 2 "Never sleep, power button does nothing"
powercfg /change standby-timeout-ac 0   | Out-Null
powercfg /change hibernate-timeout-ac 0 | Out-Null
powercfg /change standby-timeout-dc 0   | Out-Null
powercfg /change hibernate-timeout-dc 0 | Out-Null
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 0 | Out-Null
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 0 | Out-Null
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS SBUTTONACTION 0 | Out-Null
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS SBUTTONACTION 0 | Out-Null
powercfg /setactive SCHEME_CURRENT | Out-Null
Ok "done"

# ------------------------------------------------------------------ 3) guard task
Step 3 "Scheduled task ITH_Prisoft_Guard (every 1 minute)"
$action    = New-ScheduledTaskAction -Execute $pyw -Argument "`"$guard`"" -WorkingDirectory $here
$tRepeat   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$tLogon    = New-ScheduledTaskTrigger -AtLogOn -User "$env:COMPUTERNAME\$user"
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$user" -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName 'ITH_Prisoft_Guard' -Action $action -Trigger @($tRepeat, $tLogon) -Principal $principal -Settings $settings -Force | Out-Null
& $py $guard --init
Ok "registered"

# ------------------------------------------------------------------ 4) updater task settings
Step 4 "Make ITH_Bearing_Temp_Update robust"
try {
  $t = Get-ScheduledTask -TaskName 'ITH_Bearing_Temp_Update'
  $s = $t.Settings
  $s.DisallowStartIfOnBatteries = $false
  $s.StopIfGoingOnBatteries = $false
  $s.StartWhenAvailable = $true
  $s.ExecutionTimeLimit = 'PT1H'
  $s.MultipleInstances = 'IgnoreNew'
  Set-ScheduledTask -TaskName 'ITH_Bearing_Temp_Update' -Settings $s | Out-Null
  if ($t.State -eq 'Disabled') { Enable-ScheduledTask -TaskName 'ITH_Bearing_Temp_Update' | Out-Null }
  Ok "done"
} catch { Warn "ITH_Bearing_Temp_Update not found - run RESET_Dashboard.bat first" }

# ------------------------------------------------------------------ 5) restart listener
Step 5 "Restart Telegram listener (loads the new Prisoft buttons)"
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' or Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'telegram_listener\.py' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Ok "stopped old listener pid $($_.ProcessId)" }
$vbs = Join-Path $startup 'ITH_Telegram_Listener.vbs'
if (Test-Path $vbs) { Start-Process wscript.exe -ArgumentList "`"$vbs`""; Ok "listener started" }
else { Warn "listener startup entry missing - run INSTALL_Telegram_Listener.bat" }

# ------------------------------------------------------------------ status
Step 6 "Current status"
& $py $guard --status

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " INSTALLED. From now on after any restart:" -ForegroundColor Green
Write-Host "  - Windows signs in by itself, Prisoft + updater + Telegram bot start" -ForegroundColor Green
Write-Host "  - the guard checks every minute and turns Prisoft ON if needed" -ForegroundColor Green
Write-Host "  - no data for 15 min -> Telegram asks: Reset / PM / Ignore" -ForegroundColor Green
Write-Host "  - in Telegram, send /prisoft any time for the Reset / PM buttons" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "ONE THING SOFTWARE CANNOT DO: power the PC back on after a power cut." -ForegroundColor Yellow
Write-Host "Set it once in the BIOS (press DEL while the PC starts):" -ForegroundColor Yellow
Write-Host "   Advanced > APM Configuration > Restore AC Power Loss = Power On" -ForegroundColor Yellow
Write-Host ""
