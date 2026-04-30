@echo off
REM MTConnect Alarm Monitor — System Tray Launcher
REM Installs dependencies on first run, then starts the tray app

echo [%date% %time%] MTConnect Alarm Monitor — Starting...
cd /d "%~dp0"

REM Install dependencies (quiet, skip if already installed)
pip install -r requirements.txt -q 2>nul

REM Launch tray app (pythonw = no console window)
pythonw tray_app.py

if %errorlevel% neq 0 (
    echo [%date% %time%] Error: tray_app.py exited with code %errorlevel%
    echo Trying with console for debug output...
    python tray_app.py
    pause
)