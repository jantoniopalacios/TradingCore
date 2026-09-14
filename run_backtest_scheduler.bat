@echo off
setlocal

cd /d "%~dp0"

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%PROJECT_ROOT%..\..\TradingCore\.venv\Scripts\python.exe"
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encuentra el entorno virtual del proyecto:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%PROJECT_ROOT%scripts\scheduler\backtest_scheduler.py"

pause