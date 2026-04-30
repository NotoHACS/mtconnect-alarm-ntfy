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
echo Backing up config_defaults.py...
if exist "config_defaults.py" (
    copy /Y "config_defaults.py" "config_defaults.py.bak" >nul
    echo Config backed up to config_defaults.py.bak
) else (
    echo No config_defaults.py to backup
)

REM Also keep a legacy config_local.py backup if it still exists
if exist "config_local.py" (
    echo Backing up config_local.py...
    copy /Y "config_local.py" "config_local.py.bak" >nul
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

REM Restore config from backup if update failed (no new config written)
if exist "config_defaults.py.bak" (
    echo.
    if not exist "config_defaults.py" (
        echo Restoring config_defaults.py from backup...
        copy /Y "config_defaults.py.bak" "config_defaults.py" >nul
    ) else (
        echo config_defaults.py preserved
    )
    del /F /Q "config_defaults.py.bak" >nul 2>&1
)

REM Clean up legacy config_local.py backup
if exist "config_local.py.bak" (
    del /F /Q "config_local.py.bak" >nul 2>&1
)

echo.
echo ==========================================
echo  Update complete!
echo ==========================================
echo.
echo Run 'python config_gui.py' to adjust settings if needed.
echo Restart your alarm monitor to use the new version.
echo.
pause
