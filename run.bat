@echo off
chcp 65001 >nul
echo ================================================================================
echo SimpleAST - C++ 静态代码分析工具
echo ================================================================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo 错误：虚拟环境不存在，请先运行 setup.bat
    pause
    exit /b 1
)

REM 运行分析脚本
venv\Scripts\python.exe analyze.py %*

pause
