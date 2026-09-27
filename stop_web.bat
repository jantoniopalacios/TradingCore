@echo off
setlocal EnableExtensions
title Finalizador TradingCore

:: --- CONFIGURACION ---
set "PROJECT_ROOT=%~dp0"
set "PG_BIN=%PROJECT_ROOT%pgsql\bin\pg_ctl.exe"
set "PG_DATA=%PROJECT_ROOT%data_pg"
set "APP_PATH=scenarios.BacktestWeb.app"

cd /d "%PROJECT_ROOT%"

echo ==========================================
echo    DETENIENDO INFRAESTRUCTURA TRADING
echo ==========================================

:: 1. LOCALIZAR EL PROPIETARIO REAL DEL PUERTO 5000
echo [*] Comprobando servidor web en puerto 5000...

set "WEB_PID="
for /f "delims=" %%P in ('powershell -NoProfile -Command "$c = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue); if ($c.Count -gt 0) { $c[0].OwningProcess }"') do (
    set "WEB_PID=%%P"
)

if not defined WEB_PID (
    echo [OK] No hay ningun proceso escuchando en el puerto 5000.
    goto :stop_postgres
)

echo [*] Proceso propietario del puerto 5000:
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter 'ProcessId = %WEB_PID%' -ErrorAction SilentlyContinue; if ($p) { Write-Host ('    PID:     ' + $p.ProcessId); Write-Host ('    Proceso: ' + $p.Name); Write-Host ('    Comando: ' + $p.CommandLine) }"

:: Verificar que el listener es realmente TradingCore
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter 'ProcessId = %WEB_PID%' -ErrorAction SilentlyContinue; if ($p -and $p.CommandLine -match 'scenarios\.BacktestWeb\.app' -and $p.CommandLine -match '--port(?:=|\s+)5000') { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] El puerto 5000 esta ocupado por un proceso que no se ha identificado
    echo como el servidor TradingCore esperado.
    echo Por seguridad NO se terminara ese proceso.
    echo Tampoco se detendra PostgreSQL.
    timeout /t 5
    exit /b 2
)

echo [*] Deteniendo TradingCore Web PID %WEB_PID%...

powershell -NoProfile -Command "Stop-Process -Id %WEB_PID% -Force -ErrorAction Stop"

if errorlevel 1 (
    echo [ERROR] No se pudo terminar el proceso PID %WEB_PID%.
    timeout /t 5
    exit /b 1
)

:: Esperar hasta que el puerto quede libre
set "WEB_STOPPED=0"

for /L %%i in (1,1,10) do (
    set "CURRENT_PID="
    for /f "delims=" %%P in ('powershell -NoProfile -Command "$c = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue); if ($c.Count -gt 0) { $c[0].OwningProcess }"') do (
        set "CURRENT_PID=%%P"
    )

    if not defined CURRENT_PID (
        set "WEB_STOPPED=1"
        goto :web_stopped
    )

    timeout /t 1 >nul
)

:web_stopped

if not "%WEB_STOPPED%"=="1" (
    echo [ERROR] El puerto 5000 sigue ocupado despues de detener el servidor.
    timeout /t 5
    exit /b 1
)

echo [OK] Servidor TradingCore Web detenido. Puerto 5000 libre.

:stop_postgres

:: 2. DETENER POSTGRESQL
echo [*] Comprobando PostgreSQL en puerto 5433...

powershell -NoProfile -Command "if (Test-NetConnection -ComputerName 127.0.0.1 -Port 5433 -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [OK] PostgreSQL ya estaba fuera de linea.
) else (
    echo [*] Cerrando PostgreSQL de forma segura...
    "%PG_BIN%" stop -D "%PG_DATA%" -m fast

    if errorlevel 1 (
        echo [ERROR] PostgreSQL no pudo detenerse correctamente.
        timeout /t 5
        exit /b 1
    )

    echo [OK] PostgreSQL detenido.
)

echo ==========================================
echo [EXITO] Infraestructura detenida.
echo ==========================================
timeout /t 3
exit /b 0
