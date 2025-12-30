@echo off
schtasks /create /tn "BacktestWeb" /tr "powershell.exe -windowstyle hidden -command env:PYTHONUTF8=1; cd C:\Users\juant\Proyectos\Python\TradingCore; .\.venv\Scripts\python.exe -m scenarios.BacktestWeb.app --host=0.0.0.0" /sc once /st 00:00 /f
schtasks /run /tn "BacktestWeb"
schtasks /delete /tn "BacktestWeb" /f
echo Servidor lanzado independientemente.
timeout /t 5
