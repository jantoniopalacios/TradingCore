

$ruta_pg = "C:\Program Files\PostgreSQL\16\bin\psql.exe" 
$db_name = "trading_db"

# Listar los archivos .sql disponibles
$backups = Get-ChildItem "G:\Mi unidad\Backup\backup_trading_*.sql" | Sort-Object LastWriteTime -Descending

if ($backups.Count -eq 0) {
    Write-Host "No se encontraron archivos de backup." -ForegroundColor Red
    exit
}

Write-Host "--- RESTAURACION DE BASE DE DATOS ---" -ForegroundColor Cyan
Write-Host "Seleccione el backup que desea restaurar (el primero es el mas reciente):"

for ($i=0; $i -lt $backups.Count; $i++) {
    Write-Host "[$i] $($backups[$i].Name)"
}

$seleccion = Read-Host "Introduzca el numero de backup"
$archivo_final = $backups[$seleccion].FullName

Write-Host "ADVERTENCIA: Esto sobrescribira los datos actuales en $db_name." -ForegroundColor Yellow
$confirmar = Read-Host "Confirmar restauracion? (S/N)"

if ($confirmar -eq "S" -or $confirmar -eq "s") {
    Write-Host "Restaurando $archivo_final..." -ForegroundColor Cyan
    # Comando de restauracion
    & $ruta_pg -U postgres -d $db_name -f $archivo_final
    Write-Host "Base de datos restaurada con exito!" -ForegroundColor Green
} else {
    Write-Host "Operacion cancelada." -ForegroundColor Gray
}