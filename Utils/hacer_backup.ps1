$fecha = Get-Date -Format "yyyyMMdd_HHmm"
$ruta_pg = "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" # Confirma tu versión
$archivo_salida = "G:\Mi unidad\Backup\backup_trading_$fecha.sql"

Write-Host "Generando backup robusto (UTF-8) en $archivo_salida..." -ForegroundColor Cyan

# Ejecución con el parámetro -f (file)
& $ruta_pg -U postgres -d trading_db --clean --if-exists -f "$archivo_salida"

if ($LASTEXITCODE -eq 0) {
    Write-Host "¡Backup generado correctamente sin errores de codificación!" -ForegroundColor Green
} else {
    Write-Host "Hubo un error al generar el backup." -ForegroundColor Red
}