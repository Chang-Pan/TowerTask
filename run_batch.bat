@echo off
setlocal enabledelayedexpansion

:: ================= 配置区域 =================

:: 1. Blender 可执行文件的路径 (包含 blender.exe)
set "BLENDER_EXE=F:\YXP\PhD\BlockTower\blender\blender.exe"

:: 2. 你的 Python 脚本路径 (.py 文件)
set "PYTHON_SCRIPT=F:\YXP\PhD\BlockTower\TowerTask\obvious_script.py"

:: 3. Config 文件所在的文件夹路径
set "CONFIG_DIR=F:\YXP\PhD\BlockTower\TowerTask\configs"

:: ===========================================

echo ========================================================
echo 开始批量生成任务...
echo Blender: !BLENDER_EXE!
echo Script:  !PYTHON_SCRIPT!
echo Configs: !CONFIG_DIR!\config_green_{17..31}.yml
echo ========================================================
echo.

:: 循环从 17 到 31
for /L %%i in (17, 1, 31) do (
    set "CURRENT_CONFIG=!CONFIG_DIR!\config_green_%%i.yml"
    
    echo --------------------------------------------------------
    echo [正在处理] 场景配置: config_green_%%i.yml
    echo --------------------------------------------------------

    :: 调用 Blender
    :: -b : 后台运行 (不打开界面，速度更快)
    :: -P : 运行 Python 脚本
    :: -- : 之后的所有参数都会传给 Python 脚本的 sys.argv
    
    "%BLENDER_EXE%" -b -P "%PYTHON_SCRIPT%" -- "!CURRENT_CONFIG!"
    
    :: 检查上一个命令是否成功
    if !errorlevel! neq 0 (
        echo [错误] 处理 config_green_%%i.yml 时发生错误！
    ) else (
        echo [完成] config_green_%%i.yml 处理完毕。
    )
    echo.
)

echo ========================================================
echo 所有任务已完成。
echo ========================================================
pause