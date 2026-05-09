$fecha = Get-Date -Format "yyyyMMdd_HHmm"
$ruta_pg = "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" # Confirma tu versión
$ruta_backup = "G:\Mi unidad\Backup"
$archivo_salida = "$ruta_backup\backup_trading_db_$fecha.sql"

# Crear directorio de backup si no existe
if (-not (Test-Path $ruta_backup)) {
    New-Item -ItemType Directory -Path $ruta_backup -Force | Out-Null
    Write-Host "Directorio de backup creado: $ruta_backup" -ForegroundColor Yellow
}

Write-Host "Generando backup robusto (UTF-8) en $archivo_salida..." -ForegroundColor Cyan

# Ejecución con el parámetro -f (file)
& $ruta_pg -U postgres -p 5433 -d trading_db --clean --if-exists -f "$archivo_salida"

if ($LASTEXITCODE -eq 0) {
    Write-Host "¡Backup generado correctamente sin errores de codificación!" -ForegroundColor Green
} else {
    Write-Host "Hubo un error al generar el backup." -ForegroundColor Red
}