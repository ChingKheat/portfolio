@echo off
title Setup Auto-Start on Windows Boot
cd /d "%~dp0"
echo ========================================================
echo     GROWTOPIA BOT - AUTO-START ON WINDOWS BOOT SETUP
echo ========================================================
echo.
powershell -NoProfile -Command "$ws=New-Object -COM WScript.Shell; $startup=[Environment]::GetFolderPath('Startup'); $s=$ws.CreateShortcut($startup + '\GrowtopiaDiscordBot.lnk'); $s.TargetPath='wscript.exe'; $s.Arguments='\"%~dp0run_silent_bot.vbs\"'; $s.WorkingDirectory='%~dp0'; $s.Save(); Write-Host '[SUCCESS] Growtopia Bot shortcut added to Windows Startup folder:' -ForegroundColor Green; Write-Host ('  ' + $startup + '\GrowtopiaDiscordBot.lnk') -ForegroundColor Cyan"
echo.
echo The bot will now automatically launch silently whenever your PC turns on!
echo.
pause
