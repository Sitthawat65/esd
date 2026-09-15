@echo off
title ITH - Prisoft diagnostic part 2 (read-only)
color 0B
echo ==================================================
echo    ITH  -  PRISOFT DIAGNOSTIC  PART 2
echo    read-only: this changes NOTHING on the PC
echo ==================================================
echo.
echo Run as administrator for the power-event section.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0diag_prisoft2.ps1"
echo.
echo Done. The report ITH_diag2.txt is on the Desktop (Notepad opened it).
pause
