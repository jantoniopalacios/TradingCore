@echo off
setlocal
title Finalizador TradingCore

:: --- CONFIGURACIÓN ---
set "PG_BIN=.\pgsql\bin\pg_ctl.exe"
set "PG_DATA=data_pg"
set "APP_KEY=BacktestWeb"

echo ==========================================
echo    DETENIENDO INFRAESTRUCTURA TRADING
echo ==========================================

:: 1. DETENER SERVIDOR FLASK (Usando PowerShell para precisión absoluta)
echo [*] Buscando proceso Flask con clave: %APP_KEY%...

powershell -command "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe' and CommandLine like '%%%APP_KEY%%%'\" | Invoke-CimMethod -MethodName Terminate" >nul 2>&1

if %errorlevel% equ 0 (
    echo [!] Instruccion de cierre enviada al servidor Python.
) else (
    echo [OK] No se detectaron procesos activos para %APP_KEY%.
)

:: 2. DETENER POSTGRESQL
echo [*] Comprobando PostgreSQL en puerto 5433...
netstat -an | findstr 5433 >nul
if %errorlevel% equ 0 (
    echo [!] Cerrando motor PostgreSQL de forma segura...
    "%PG_BIN%" stop -D "%PG_DATA%" -m fast
) else (
    echo [OK] PostgreSQL ya estaba fuera de linea.
)

echo ==========================================
echo [EXITO] Infraestructura detenida.
echo ==========================================
timeout /t 3