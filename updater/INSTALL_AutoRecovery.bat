@echo off
title ITH - Prisoft AUTO RECOVERY - install
color 0B
echo ==================================================================
echo    ITH  -  PRISOFT AUTO RECOVERY  (always ready, no one needs to press ON)
echo ==================================================================
echo.
echo  This will:
echo   1. Sign in to Windows automatically after a restart (account has no password)
echo   2. Never sleep; the power button on the case does nothing
echo   3. Add task ITH_Prisoft_Guard - checks Prisoft every minute, turns it ON
echo   4. Make the temperature updater task robust
echo   5. Restart the Telegram bot so the new /prisoft buttons work
echo.
echo  Undo any time with UNINSTALL_AutoRecovery.bat
echo.
echo  Must be started with right-click - Run as administrator.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_autorecovery.ps1"
echo.
pause
