@echo off
title ITH - Prisoft / restart diagnostic (read-only)
color 0B
echo ==================================================
echo    ITH  -  PRISOFT / PC RESTART DIAGNOSTIC
echo    read-only: this changes NOTHING on the PC
echo ==================================================
echo.
echo Tip: right-click this file and "Run as administrator"
echo      so the restart history can be read.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0diag_prisoft.ps1"
echo.
echo Done. The report ITH_diag.txt is on the Desktop (Notepad opened it).
pause
