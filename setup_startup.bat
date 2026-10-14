@echo off
title Setup Auto-Start on Windows Boot
cd /d "%~dp0"
echo ========================================================
echo     GROWTOPIA BOT - AUTO-START ON WINDOWS BOOT SETUP
echo ========================================================
echo.
powershell -NoProfile -Command "$ws=New-Object -COM WScript.Shell; $startup=[Environment]::GetFolderPath('Startup'); $target=(Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source; if(-not $target){$target=[System.IO.Path]::Combine($env:LOCALAPPDATA, 'Programs\Python\Python312\pythonw.exe')}; $s=$ws.CreateShortcut((Join-Path $startup 'GrowtopiaDiscordBot.lnk')); $s.TargetPath=$target; $s.Arguments='\"%~dp0growtopia_bot.py\"'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Description='Growtopia Discord Dataminer Bot'; $s.Save(); Write-Host '[SUCCESS] Direct pythonw shortcut created in Windows Startup:' -ForegroundColor Green; Write-Host ('  ' + $startup + '\GrowtopiaDiscordBot.lnk') -ForegroundColor Cyan; Write-Host ('  Target: ' + $target) -ForegroundColor Gray"
echo.
echo The bot will now automatically launch silently whenever your PC turns on!
echo.
pause
