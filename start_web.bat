@echo off
setlocal
title Gestor TradingCore

:: --- CONFIGURACIÓN (Rutas ajustadas a tu laboratorio) ---
set "PG_BIN=.\pgsql\bin\pg_ctl.exe"
set "PG_DATA=data_pg"
set "LOG_PG=logfile.txt"
set "TASK_NAME=BacktestWeb"
set "APP_PATH=scenarios.BacktestWeb.app"

echo ==========================================
echo    INICIANDO INFRAESTRUCTURA TRADING
echo ==========================================

:: 1. ARRANCAR POSTGRESQL (Si no está activo)
echo [*] Comprobando PostgreSQL en puerto 5433...
netstat -an | findstr 5433 >nul
if %errorlevel% neq 0 (
    echo [!] PostgreSQL no detectado. Intentando arrancar...
    :: Usamos la ruta relativa de tu pg_start.bat
    "%PG_BIN%" -D "%PG_DATA%" -l "%LOG_PG%" start
    timeout /t 3 >nul
) else (
    echo [OK] PostgreSQL ya esta en ejecucion.
)

:: Espera activa hasta que PostgreSQL responda en 5433 (max 30s)
echo [*] Esperando a que PostgreSQL este listo...
set "PG_READY=0"
for /L %%i in (1,1,30) do (
    powershell -NoProfile -Command "if (Test-NetConnection -ComputerName 127.0.0.1 -Port 5433 -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "PG_READY=1"
        goto :pg_ready
    )
    timeout /t 1 >nul
)

:pg_ready
if "%PG_READY%" neq "1" (
    echo [ERROR] PostgreSQL no responde en 5433 tras 30 segundos.
    echo Revisa logfile.txt y el estado del servicio.
    timeout /t 5
    exit /b 1
)

:: 2. COMPROBAR SI LA WEB YA ESTÁ CORRIENDO (detección robusta)
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'scenarios.BacktestWeb.app' }; if ($p) { exit 0 } else { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [ADVERTENCIA] El servidor %TASK_NAME% ya esta activo.
    echo No se lanzara otra instancia.
    timeout /t 5
    exit /b
)

:: 3. LANZAR SERVIDOR WAITRESS (Modo Oculto, sobrevive al cierre de terminal/SSH)
echo [*] Lanzando servidor con Waitress en segundo plano...
powershell -windowstyle hidden -command "Start-Process -FilePath 'C:\Users\juant\Proyectos\Python\TradingCore\.venv\Scripts\python.exe' -ArgumentList '-m %APP_PATH% --host=0.0.0.0 --port=5000 --no-debug --no-reloader' -WorkingDirectory 'C:\Users\juant\Proyectos\Python\TradingCore' -WindowStyle Hidden"

timeout /t 4 >nul

:: Verificar que arrancó (comprobación HTTP real)
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/login -TimeoutSec 6; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo [EXITO] Infraestructura lista y segura.
    echo Acceso via Tailscale: http://tradingcore:5000
    echo ==========================================
) else (
    echo.
    echo [ERROR] El servidor no respondio en puerto 5000. Revisa los logs.
    echo Logs: Backtesting\logs\trading_app.log
    echo ==========================================
)
timeout /t 5