@echo off
echo Levantando Laboratorio PostgreSQL...
.\pgsql\bin\pg_ctl.exe -D data_pg -l logfile.txt start
timeout /t 2 >nul
netstat -an | findstr 5432
if %errorlevel%==0 (
    echo.
    echo [OK] PostgreSQL esta funcionando en el puerto 5432.
) else (
    echo [ERROR] No se pudo arrancar el servidor. Revisa logfile.txt.
)
pause