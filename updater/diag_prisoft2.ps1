# ITH - Prisoft diagnostic part 2  (READ-ONLY: changes nothing)
# Finds HOW Primus-task-control starts "Operation / Database / Backend" when ON is pressed,
# so they can be started automatically after a reboot.
# Never reads .env / credential files. Secrets in matched lines are masked.

$ErrorActionPreference = 'SilentlyContinue'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) 'ITH_diag2.txt'
$lines = New-Object System.Collections.Generic.List[string]
function W($s) { $lines.Add([string]$s) }
function Section($s) { W ''; W ('=' * 70); W "  $s"; W ('=' * 70) }
function Mask($s) {
  if (-not $s) { return $s }
  $s = $s -replace '(?i)(pass(word)?|pwd|token|secret|apikey|api_key)(\s*[=:]\s*|\s+)("[^"]*"|''[^'']*''|\S+)', '$1$3***'
  $s -replace '(?i)(mongodb(\+srv)?://)[^@\s"'']+@', '$1***@'
}
function Clip($s, $n) { if ($s.Length -gt $n) { $s.Substring(0, $n) + ' ...' } else { $s } }
$skipName = '(?i)^\.env|credential|secret|\.pem$|\.key$|cookies'
$pattern = '(?i)spawn|execFile|exec\(|fork\(|child_process|cwd|server\.js|mongod|operation|database|backend|autostart|auto_start|autoStart|taskkill|tree-kill|\.kill\(|pm2|npm (run|start)'

$app = 'C:\Primus\Prisoft\Primus-task-control-win32-x64\resources'
Section "TASK-CONTROL APP FILES ($app)"
Get-ChildItem $app | ForEach-Object { W ("   {0,-40} {1,10}" -f $_.Name, $_.Length) }
$appDir = Join-Path $app 'app'
if (Test-Path $appDir) {
  W "[resources\app  (top 2 levels, no node_modules)]"
  Get-ChildItem $appDir -Recurse -Depth 1 | Where-Object { $_.FullName -notmatch 'node_modules' } |
    ForEach-Object { W ("   " + $_.FullName.Substring($appDir.Length)) }
}

Section "HOW ON/OFF IS IMPLEMENTED (matching lines in the app code)"
$files = @()
if (Test-Path $appDir) {
  $files = Get-ChildItem $appDir -Recurse -Include *.js, *.json, *.html |
    Where-Object { $_.FullName -notmatch 'node_modules' -and $_.Name -notmatch $skipName -and $_.Length -lt 3MB }
}
$count = 0
foreach ($f in $files) {
  $hits = Select-String -Path $f.FullName -Pattern $pattern
  if ($hits) {
    W ("--- " + $f.FullName.Substring($appDir.Length))
    foreach ($h in ($hits | Select-Object -First 60)) {
      W ("  {0,5}: {1}" -f $h.LineNumber, (Clip (Mask $h.Line.Trim()) 300))
      $count++
    }
  }
  if ($count -gt 400) { W "(stopped at 400 lines)"; break }
}
$asar = Join-Path $app 'app.asar'
if (Test-Path $asar) {
  W "--- app.asar (packed; showing text around matches)"
  $txt = [IO.File]::ReadAllText($asar, [Text.Encoding]::GetEncoding(28591))
  $ms = [regex]::Matches($txt, '.{0,140}(spawn|execFile|child_process|server\.js|mongod|autoStart|auto_start|taskkill).{0,160}')
  $n = 0
  foreach ($m in $ms) {
    W ("  " + (Clip (Mask ($m.Value -replace '\s+', ' ')) 320)); $n++
    if ($n -ge 120) { W "(stopped at 120 matches)"; break }
  }
}

Section "WHERE IS backend\server.js  (and siblings)"
Get-ChildItem 'C:\Primus' -Recurse -Filter server.js -Depth 4 | Where-Object { $_.FullName -notmatch 'node_modules' } | ForEach-Object {
  W ("[" + $_.FullName + "]")
  $root = Split-Path (Split-Path $_.FullName)
  W ("   project folder: " + $root)
  Get-ChildItem $root | Where-Object { $_.Name -notmatch $skipName } | ForEach-Object { W ("      " + $_.Name) }
  $pkg = Join-Path $root 'package.json'
  if (Test-Path $pkg) {
    W "   package.json scripts:"
    $j = Get-Content $pkg -Raw | ConvertFrom-Json
    $j.scripts.PSObject.Properties | ForEach-Object { W ("      {0} = {1}" -f $_.Name, (Mask $_.Value)) }
  }
}

Section "TASK-CONTROL SETTINGS (small json files in AppData, secrets masked)"
foreach ($d in @("$env:APPDATA\Primus-task-manager", "$env:APPDATA\Primus-task-control", "$env:APPDATA\primus-task-control")) {
  if (Test-Path $d) {
    W "[$d]"
    Get-ChildItem $d -Recurse -Depth 2 -File | Where-Object { $_.Name -notmatch $skipName } | ForEach-Object {
      W ("   {0}  ({1} bytes)" -f $_.FullName.Substring($d.Length), $_.Length)
      if ($_.Extension -eq '.json' -and $_.Length -lt 4000) {
        W ("      " + (Clip (Mask ((Get-Content $_.FullName -Raw) -replace '\s+', ' ')) 800))
      }
    }
  }
}

Section "ITH TASK SETTINGS"
foreach ($tn in @('ITH_Bearing_Temp_Update')) {
  $t = Get-ScheduledTask -TaskName $tn
  if ($t) {
    W ("{0}: LogonType={1} RunLevel={2} StartWhenAvailable={3} DisallowOnBatteries={4}" -f $tn, $t.Principal.LogonType, $t.Principal.RunLevel, $t.Settings.StartWhenAvailable, $t.Settings.DisallowStartIfOnBatteries)
  }
}

Section "BIOS / POWER-LOSS HINTS"
$bios = Get-CimInstance Win32_BIOS
$cs = Get-CimInstance Win32_ComputerSystem
W ("Maker/Model: " + $cs.Manufacturer + " / " + $cs.Model + "   BIOS: " + $bios.SMBIOSBIOSVersion)
W ("UPS / battery devices: " + ((Get-CimInstance Win32_Battery | ForEach-Object { $_.Name }) -join ', '))
$pb = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 60
foreach ($e in ($pb | Where-Object { $_.Id -in 41, 42, 109, 506, 507 } | Sort-Object TimeCreated)) {
  W ("{0}  id={1,-4} {2}" -f $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'), $e.Id, (Clip ($e.Message -replace '\s+', ' ') 160))
}
W "id=109 = kernel power transition started (shutdown/power off)  -  press of power button shows as 'power button' in event 506/507/41 details"
$btn = Get-WinEvent -FilterHashtable @{LogName='System'; Id=1074; StartTime=(Get-Date).AddDays(-30)} | Where-Object { $_.Message -match '0x500ff' }
foreach ($e in $btn) {
  $x = [xml]$e.ToXml()
  W ("{0}  1074 power off 0x500ff  data: {1}" -f $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'), (($x.Event.EventData.Data | ForEach-Object { $_.'#text' }) -join ' | '))
}

$lines | Out-File -FilePath $out -Encoding utf8
Write-Host ""
Write-Host "Saved: $out"
Start-Process notepad.exe $out
