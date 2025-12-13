@echo off
:: Force the console to use UTF-8 just in case
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ================= CONFIGURATION =================

:: 1. Path to blender.exe
set "BLENDER_EXE=F:\YXP\PhD\BlockTower\blender\blender.exe"

:: 2. Path to your python script
set "PYTHON_SCRIPT=F:\YXP\PhD\BlockTower\TowerTask\obvious_script.py"

:: 3. Path to the config folder
set "CONFIG_DIR=F:\YXP\PhD\BlockTower\TowerTask\configs"

:: =================================================

echo ========================================================
echo Starting Batch Process...
echo Blender: !BLENDER_EXE!
echo Script:  !PYTHON_SCRIPT!
echo Configs: !CONFIG_DIR!\config_green_{17..31}.yml
echo ========================================================
echo.

:: Loop from 17 to 31
for /L %%i in (17, 1, 31) do (
    set "CURRENT_CONFIG=!CONFIG_DIR!\config_green_%%i.yml"
    
    echo --------------------------------------------------------
    echo [Processing] Scene Config: config_green_%%i.yml
    echo --------------------------------------------------------

    :: Run Blender
    :: -b : Background mode
    :: -P : Run Python script
    :: -- : Pass arguments to Python
    "%BLENDER_EXE%" -b -P "%PYTHON_SCRIPT%" -- "!CURRENT_CONFIG!"
    
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to process config_green_%%i.yml
    ) else (
        echo [SUCCESS] Finished config_green_%%i.yml
    )
    echo.
)

echo ========================================================
echo All tasks completed.
echo ========================================================
pause