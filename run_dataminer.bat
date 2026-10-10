@echo off
title Growtopia Real-Time Dataminer to Discord
cd /d "%~dp0"

echo ========================================================
echo         GROWTOPIA REAL-TIME DISCORD DATAMINER          
echo ========================================================
echo.
echo  [1] Start 24/7 Auto-Watcher (Detects updates in the 1st second!)
echo  [2] Check Current Database and Test Webhook
echo.
echo ========================================================
set /p choice="Enter choice (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo Starting 24/7 Watcher mode...
    python growtopia_miner.py watch
) else (
    echo.
    python growtopia_miner.py
)

pause
