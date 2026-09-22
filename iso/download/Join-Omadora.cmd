@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Join-Omadora.ps1"
if errorlevel 1 echo Failed. Read the error above before continuing.
pause
