@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dev.ps1" %*
endlocal
