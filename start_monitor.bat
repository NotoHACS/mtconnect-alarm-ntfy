@echo off
REM MTConnect Alarm Monitor Startup Script
REM Waits 5 minutes (300 seconds) before starting the monitor

echo [%date% %time%] Waiting 5 minutes before starting MTConnect Alarm Monitor...
timeout /t 300 /nobreak

echo [%date% %time%] Starting MTConnect Alarm Monitor...
cd /d "%~dp0"
python main.py

REM If the script exits, pause to see any error messages
if %errorlevel% neq 0 (
    echo [%date% %time%] Error: MTConnect Alarm Monitor exited with code %errorlevel%
    pause
)
