@echo off
chcp 65001 >nul
echo ================================================================================
echo SimpleAST 环境安装脚本
echo ================================================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 创建虚拟环境...
if exist "venv" (
    echo 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    if errorlevel 1 (
        echo 错误：创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✓ 虚拟环境创建成功
)

echo.
echo [2/3] 安装依赖包...
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo 错误：安装依赖失败
    pause
    exit /b 1
)
echo ✓ 依赖安装成功

echo.
echo [3/3] 运行测试...
venv\Scripts\python.exe test_analyzer.py
if errorlevel 1 (
    echo 警告：测试运行出现问题，但环境已安装完成
) else (
    echo ✓ 测试通过
)

echo.
echo ================================================================================
echo 安装完成！
echo.
echo 使用方法：
echo   1. 双击 run.bat 进入交互模式
echo   2. 或执行: run.bat [项目目录] [目标文件]
echo.
echo 示例：
echo   run.bat .\example_project .\example_project\src\main.cpp
echo ================================================================================

pause
