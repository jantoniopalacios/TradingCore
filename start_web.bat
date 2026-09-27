@echo off
setlocal EnableExtensions
title Gestor TradingCore

:: --- CONFIGURACION ---
set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"

set "PG_BIN=%PROJECT_ROOT%pgsql\bin\pg_ctl.exe"
set "PG_DATA=%PROJECT_ROOT%data_pg"
set "LOG_PG=%PROJECT_ROOT%logfile.txt"
set "TASK_NAME=BacktestWeb"
set "APP_PATH=scenarios.BacktestWeb.app"

cd /d "%PROJECT_ROOT%"

echo ==========================================
echo    INICIANDO INFRAESTRUCTURA TRADING
echo ==========================================

:: 1. ARRANCAR POSTGRESQL SI NO ESTA ACTIVO
echo [*] Comprobando PostgreSQL en puerto 5433...
powershell -NoProfile -Command "if (Test-NetConnection -ComputerName 127.0.0.1 -Port 5433 -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [!] PostgreSQL no detectado. Intentando arrancar...
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
if not "%PG_READY%"=="1" (
    echo [ERROR] PostgreSQL no responde en 5433 tras 30 segundos.
    echo Revisa logfile.txt y el estado del servicio.
    timeout /t 5
    exit /b 1
)

:: 2. COMPROBAR PROPIETARIO REAL DEL PUERTO 5000
echo [*] Comprobando servidor web en puerto 5000...

set "WEB_PID="
for /f "delims=" %%P in ('powershell -NoProfile -Command "$c = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue); if ($c.Count -gt 0) { $c[0].OwningProcess }"') do (
    set "WEB_PID=%%P"
)

if defined WEB_PID (
    echo.
    echo [ADVERTENCIA] El puerto 5000 ya esta ocupado.
    echo [*] Proceso propietario:
    powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter 'ProcessId = %WEB_PID%' -ErrorAction SilentlyContinue; if ($p) { Write-Host ('    PID:     ' + $p.ProcessId); Write-Host ('    Proceso: ' + $p.Name); Write-Host ('    Comando: ' + $p.CommandLine) } else { Write-Host '    No se pudo consultar el proceso.' }"
    echo.
    echo No se lanzara otra instancia de %TASK_NAME%.
    timeout /t 5
    exit /b 2
)

:: Comprobacion adicional: proceso TradingCore existente pero sin listener
set "ORPHAN_PID="
for /f "delims=" %%P in ('powershell -NoProfile -Command "$p = @(Get-CimInstance Win32_Process -Filter 'Name = ''python.exe''' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'scenarios\.BacktestWeb\.app' }); if ($p.Count -gt 0) { $p[0].ProcessId }"') do (
    set "ORPHAN_PID=%%P"
)

if defined ORPHAN_PID (
    echo.
    echo [ADVERTENCIA] Existe un proceso TradingCore Web sin listener detectado en puerto 5000.
    powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter 'ProcessId = %ORPHAN_PID%' -ErrorAction SilentlyContinue; if ($p) { Write-Host ('    PID:     ' + $p.ProcessId); Write-Host ('    Proceso: ' + $p.Name); Write-Host ('    Comando: ' + $p.CommandLine) }"
    echo.
    echo Revisalo o detenlo antes de lanzar una nueva instancia.
    timeout /t 5
    exit /b 3
)

:: 3. LANZAR SERVIDOR EN SEGUNDO PLANO
echo [*] Lanzando servidor TradingCore Web en segundo plano...

powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '-m %APP_PATH% --host=0.0.0.0 --port=5000 --no-debug --no-reloader' -WorkingDirectory '%PROJECT_ROOT%' -WindowStyle Hidden"

timeout /t 2 >nul

:: Verificar arranque HTTP
set "WEB_READY=0"

for /L %%i in (1,1,12) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/login -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "WEB_READY=1"
        goto :web_ready
    )
    timeout /t 1 >nul
)

:web_ready

:: Fallback: listener activo aunque /login aun no responda
if not "%WEB_READY%"=="1" (
    powershell -NoProfile -Command "if (Test-NetConnection -ComputerName 127.0.0.1 -Port 5000 -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>&1

    if not errorlevel 1 (
        set "WEB_READY=1"
        echo [ADVERTENCIA] El puerto 5000 esta activo, pero /login aun no responde. Puede estar iniciando.
    )
)

if "%WEB_READY%"=="1" (
    set "WEB_PID="
    for /f "delims=" %%P in ('powershell -NoProfile -Command "$c = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue); if ($c.Count -gt 0) { $c[0].OwningProcess }"') do (
        set "WEB_PID=%%P"
        echo PID servidor web: %%P
    )

    echo.
    echo [EXITO] Infraestructura lista.
    echo Acceso local:          http://127.0.0.1:5000
    echo Acceso via Tailscale:  http://tradingcore:5000
    echo ==========================================
    timeout /t 5
    exit /b 0
)

echo.
echo [ERROR] El servidor no respondio en puerto 5000 tras varios intentos.
echo Revisa: Backtesting\logs\trading_app.log
echo ==========================================
timeout /t 5
exit /b 1
