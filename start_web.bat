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

:: 2. COMPROBAR SI LA WEB YA ESTÁ CORRIENDO
wmic process where "name='python.exe'" get commandline 2>nul | findstr /i "%APP_PATH%" >nul
if %errorlevel% equ 0 (
    echo.
    echo [ADVERTENCIA] El servidor %TASK_NAME% ya esta activo.
    echo No se lanzara otra instancia.
    timeout /t 5
    exit /b
)

:: 3. LANZAR SERVIDOR FLASK (Modo Oculto)
echo [*] Lanzando servidor Flask en segundo plano...
:: IMPORTANTE: Cambiamos a la ruta absoluta de tu proyecto para schtasks
schtasks /create /tn "%TASK_NAME%" /tr "powershell.exe -windowstyle hidden -command $env:PYTHONUTF8=1; cd C:\Users\juant\Proyectos\Python\TradingCore; .\.venv\Scripts\python.exe -m %APP_PATH% --host=0.0.0.0" /sc once /st 00:00 /f >nul 2>&1

schtasks /run /tn "%TASK_NAME%" >nul 2>&1
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

echo.
echo ==========================================
echo [EXITO] Infraestructura lista y segura.
echo Acceso via Tailscale: Puerto 5000
echo ==========================================
timeout /t 5