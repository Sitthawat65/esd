@echo off
title PLC read-only test
color 0B
echo ==================================================================
echo    PLC READ-ONLY TEST  (reads only - never writes to the PLC)
echo ==================================================================
echo.
echo  Tests network + reads CPU model, RUN/STOP, block list from:
echo     PLC 192.168.0.50    HMI 192.168.0.52
echo  Other IPs:  PLC_TEST.bat 192.168.0.60 192.168.0.62
echo.
pause
cd /d "%~dp0"

python -c "import snap7" 1>nul 2>nul
if errorlevel 1 (
  echo [setup] Installing python-snap7 ^(S7 reader, small, one time^)...
  python -m pip install --user python-snap7 --trusted-host pypi.org --trusted-host files.pythonhosted.org
)

set "IPS=%*"
if "%IPS%"=="" set "IPS=192.168.0.50 192.168.0.52"
python plc_probe.py %IPS%
if exist "%USERPROFILE%\Desktop\PLC_probe.txt" start "" notepad "%USERPROFILE%\Desktop\PLC_probe.txt"
echo.
pause
