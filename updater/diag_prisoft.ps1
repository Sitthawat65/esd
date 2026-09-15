# ITH - Prisoft / PC restart diagnostic  (READ-ONLY: changes nothing)
# Collects why the PC restarts, how Prisoft is started, and the state of the ITH tasks.
# Output: ITH_diag.txt on the Desktop. Passwords/tokens in command lines are masked.

$ErrorActionPreference = 'SilentlyContinue'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) 'ITH_diag.txt'
$lines = New-Object System.Collections.Generic.List[string]
function W($s) { $lines.Add([string]$s) }
function Section($s) { W ''; W ('=' * 70); W "  $s"; W ('=' * 70) }
function Mask($s) {
  if (-not $s) { return $s }
  $s -replace '(?i)(pass(word)?|pwd|token|secret|apikey|api_key)(\s*[=:]\s*|\s+)("[^"]*"|\S+)', '$1$3***'
}

Section "BASIC"
W ("Computer   : " + $env:COMPUTERNAME + "   User: " + $env:USERNAME)
W ("Now        : " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$os = Get-CimInstance Win32_OperatingSystem
W ("OS         : " + $os.Caption + " build " + $os.BuildNumber)
W ("Last boot  : " + $os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss'))
W ("Uptime     : " + ((Get-Date) - $os.LastBootUpTime).ToString('d\.hh\:mm') + "  (days.hh:mm)")
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
W ("Run as admin: " + $admin)

Section "SHUTDOWN / RESTART HISTORY (last 30 days)"
W "1074 = restart/shutdown requested (shows WHO and WHY)   6008 = unexpected shutdown"
W "41   = Kernel-Power (power loss / hard reset)           6005/6006 = event log start/stop"
W "1076 = reason typed after unexpected shutdown           19/43/44 = Windows Update"
$since = (Get-Date).AddDays(-30)
$ev = Get-WinEvent -FilterHashtable @{LogName='System'; Id=1074,1076,6005,6006,6008,41; StartTime=$since} -MaxEvents 80
foreach ($e in ($ev | Sort-Object TimeCreated)) {
  $msg = ($e.Message -replace '\s+', ' ')
  if ($msg.Length -gt 260) { $msg = $msg.Substring(0, 260) + '...' }
  W ("{0}  id={1,-5} {2}" -f $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'), $e.Id, $msg)
}
if (-not $ev) { W "(no events found - try running as Administrator)" }

Section "WINDOWS UPDATE (installs in last 30 days)"
$wu = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WindowsUpdateClient'; Id=19,20,43,44; StartTime=$since} -MaxEvents 40
foreach ($e in ($wu | Sort-Object TimeCreated)) {
  $msg = ($e.Message -replace '\s+', ' ')
  if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + '...' }
  W ("{0}  id={1,-3} {2}" -f $e.TimeCreated.ToString('yyyy-MM-dd HH:mm'), $e.Id, $msg)
}
$au = Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
W ("Policy AU  : AUOptions=" + $au.AUOptions + " NoAutoUpdate=" + $au.NoAutoUpdate + " NoAutoRebootWithLoggedOnUsers=" + $au.NoAutoRebootWithLoggedOnUsers)
$ux = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'
W ("Active hours: " + $ux.ActiveHoursStart + " - " + $ux.ActiveHoursEnd)

Section "SCHEDULED TASKS that restart/shutdown the PC"
Get-ScheduledTask | ForEach-Object {
  $t = $_
  foreach ($a in $t.Actions) {
    $cmd = "$($a.Execute) $($a.Arguments)"
    if ($cmd -match '(?i)shutdown|restart-computer|reboot') {
      W ("{0}{1}  ->  {2}  [{3}]" -f $t.TaskPath, $t.TaskName, (Mask $cmd), $t.State)
    }
  }
}

Section "POWER"
W ((powercfg /getactivescheme) -join ' ')
W ("Last wake  : " + ((powercfg /lastwake) -join ' | '))

Section "AUTO-LOGON (needed for GUI apps to start after an unattended reboot)"
$wl = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
W ("AutoAdminLogon=" + $wl.AutoAdminLogon + "  DefaultUserName=" + $wl.DefaultUserName + "  (password value NOT read)")

Section "PRISOFT / PRIMUS PROCESSES (running now)"
$procs = Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match '(?i)prisoft|primus|node|mongo|java|redis|postgres|mysql|nginx|python|electron|pm2') -or
  ($_.ExecutablePath -match '(?i)prisoft|primus')
}
foreach ($p in $procs) {
  W ("PID {0,-6} parent {1,-6} {2}" -f $p.ProcessId, $p.ParentProcessId, $p.Name)
  W ("   exe : " + $p.ExecutablePath)
  W ("   cmd : " + (Mask $p.CommandLine))
  $ports = (Get-NetTCPConnection -OwningProcess $p.ProcessId -State Listen | Select-Object -ExpandProperty LocalPort | Sort-Object -Unique) -join ','
  if ($ports) { W ("   listening ports: " + $ports) }
}

Section "SERVICES (prisoft / primus / mongo / node / database-like)"
Get-CimInstance Win32_Service | Where-Object { $_.Name -match '(?i)prisoft|primus|mongo|node|redis|postgres|mysql|nginx|pm2' -or $_.DisplayName -match '(?i)prisoft|primus|database' -or $_.PathName -match '(?i)prisoft|primus' } | ForEach-Object {
  W ("{0,-28} {1,-8} start={2,-9} {3}" -f $_.Name, $_.State, $_.StartMode, (Mask $_.PathName))
}

Section "SCHEDULED TASKS (prisoft / primus / ITH)"
Get-ScheduledTask | Where-Object { $_.TaskName -match '(?i)prisoft|primus|^ITH_' -or (($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join ' ') -match '(?i)prisoft|primus' } | ForEach-Object {
  $i = $_ | Get-ScheduledTaskInfo
  W ("{0}{1}   state={2}  user={3}  logon={4}" -f $_.TaskPath, $_.TaskName, $_.State, $_.Principal.UserId, $_.Principal.LogonType)
  W ("   last run={0}  result=0x{1:X}  next={2}" -f $i.LastRunTime, $i.LastTaskResult, $i.NextRunTime)
  foreach ($a in $_.Actions) { W ("   action: " + (Mask "$($a.Execute) $($a.Arguments)")) }
  foreach ($tr in $_.Triggers) { W ("   trigger: " + $tr.CimClass.CimClassName) }
}

Section "STARTUP FOLDERS"
foreach ($d in @([Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('CommonStartup'))) {
  W "[$d]"
  Get-ChildItem $d | ForEach-Object { W ("   " + $_.Name) }
}
foreach ($k in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run')) {
  W "[$k]"
  $r = Get-ItemProperty $k
  $r.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object { W ("   {0} = {1}" -f $_.Name, (Mask $_.Value)) }
}

Section "DESKTOP SHORTCUTS (targets)"
$sh = New-Object -ComObject WScript.Shell
foreach ($d in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'))) {
  Get-ChildItem $d -Filter *.lnk | ForEach-Object {
    $l = $sh.CreateShortcut($_.FullName)
    W ("{0}" -f $_.Name)
    W ("   -> {0} {1}" -f $l.TargetPath, (Mask $l.Arguments))
    W ("   in {0}" -f $l.WorkingDirectory)
  }
}

Section "PRISOFT INSTALL FOLDERS (top level)"
$roots = @("$env:ProgramFiles", "${env:ProgramFiles(x86)}", "C:\", "$env:LOCALAPPDATA\Programs", "$env:APPDATA", "$env:USERPROFILE")
foreach ($r in $roots) {
  Get-ChildItem $r -Directory | Where-Object { $_.Name -match '(?i)prisoft|primus' } | ForEach-Object {
    W ("[" + $_.FullName + "]")
    Get-ChildItem $_.FullName | Select-Object -First 40 | ForEach-Object { W ("   " + $_.Name) }
  }
}

$lines | Out-File -FilePath $out -Encoding utf8
Write-Host ""
Write-Host "Saved: $out"
Start-Process notepad.exe $out
