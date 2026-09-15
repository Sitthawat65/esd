@echo off
title ITH - Prisoft AUTO RECOVERY - UNINSTALL
color 0E
echo ==================================================================
echo    UNINSTALL Prisoft auto recovery
echo ==================================================================
echo.
echo  Removes task ITH_Prisoft_Guard, turns OFF automatic sign-in and
echo  sets the power button back to Shut down.
echo  (Run as administrator.)
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_autorecovery.ps1" -Uninstall
echo.
pause
