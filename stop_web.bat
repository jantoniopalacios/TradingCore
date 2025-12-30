@echo off
echo Deteniendo el servidor Backtest...
taskkill /f /im python.exe /t
echo Servidor detenido correctamente.
timeout /t 3
