@echo off
title Growtopia Interactive Discord Bot
cd /d "%~dp0"

:loop
cls
echo ========================================================
echo         GROWTOPIA INTERACTIVE DISCORD BOT
echo ========================================================
echo.
echo Starting bot and connecting to Discord...
python growtopia_bot.py
echo.
echo [Notice] Bot disconnected or stopped. Restarting in 5 seconds...
timeout /t 5
goto loop
