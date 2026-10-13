@echo off
title Stop Growtopia Discord Bot
echo ========================================================
echo         STOPPING GROWTOPIA DATAMINER BOT
echo ========================================================
echo.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*growtopia_bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[Stopped] PID: ' + $_.ProcessId) }"
echo.
echo Growtopia Dataminer Bot stopped successfully!
timeout /t 3
