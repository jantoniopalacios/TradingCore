@echo off
echo Apagando Laboratorio PostgreSQL...
.\pgsql\bin\pg_ctl.exe -D data_pg stop
echo.
echo [INFO] Servidor detenido.
pause