@echo off
cd /d C:\Users\juant\Proyectos\Python\TradingCore
REM Activar entorno virtual
call .venv\Scripts\activate.bat
REM Ejecutar el script de backtest scheduler
python Utils\backtest_scheduler.py
pause
