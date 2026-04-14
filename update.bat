@echo off
REM Update MTConnect Alarm Monitor from GitHub
REM This script calls update_helper.py to do the actual work

echo ==========================================
echo  MTConnect Alarm Monitor Updater
echo ==========================================
echo.

setlocal enabledelayedexpansion

set BRANCH=%1
if "%BRANCH%"=="" set BRANCH=master

echo Updating from branch: %BRANCH%
echo.

REM Check for Python
echo Checking for Python...
python --version >nul 2>nul
if errorlevel 1 (
    echo Python not found! Cannot update.
    pause
    exit /b 1
)

REM Create backup of current config
echo Backing up config_local.py...
if exist "config_local.py" (
    copy /Y "config_local.py" "config_local.py.bak" >nul
    echo Config backed up to config_local.py.bak
) else (
    echo No config_local.py to backup
)

REM Run Python update helper
echo.
echo Downloading and updating...
python update_helper.py %BRANCH%

if errorlevel 1 (
    echo.
    echo Update failed!
    pause
    exit /b 1
)

REM Restore config if backup exists
if exist "config_local.py.bak" (
    echo.
    if not exist "config_local.py" (
        echo Restoring config_local.py from backup...
        copy /Y "config_local.py.bak" "config_local.py" >nul
    ) else (
        echo config_local.py preserved
    )
    del /F /Q "config_local.py.bak" >nul 2>&1
)

echo.
echo ==========================================
echo  Update complete!
echo ==========================================
echo.
echo Restart your alarm monitor to use the new version.
echo.
pause
