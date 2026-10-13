@echo off
title Remove from Windows Startup
echo ========================================================
echo     REMOVE GROWTOPIA BOT FROM WINDOWS STARTUP
echo ========================================================
echo.
powershell -NoProfile -Command "$startup=[Environment]::GetFolderPath('Startup'); Remove-Item ($startup + '\GrowtopiaDiscordBot.lnk') -ErrorAction SilentlyContinue; Write-Host '[SUCCESS] Growtopia Bot shortcut removed from Windows Startup.' -ForegroundColor Yellow"
echo.
pause
