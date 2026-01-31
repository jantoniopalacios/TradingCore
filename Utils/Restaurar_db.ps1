$ruta_pg = "C:\Program Files\PostgreSQL\16\bin\psql.exe" 
$db_name = "trading_db"
$env:PGPASSWORD = "admin" # Evita que el script se bloquee pidiendo pass

# Listar los archivos .sql
$backups = Get-ChildItem "G:\Mi unidad\Backup\backup_trading_*.sql" | Sort-Object LastWriteTime -Descending

if ($backups.Count -eq 0) {
    Write-Host "❌ No se encontraron archivos de backup." -ForegroundColor Red
    exit
}

Write-Host "`n--- 📥 RESTAURACIÓN DE BASE DE DATOS ---" -ForegroundColor Cyan
Write-Host "Seleccione el backup (0 = más reciente):"

for ($i=0; $i -lt $backups.Count; $i++) {
    Write-Host "[$i] $($backups[$i].Name) ($($backups[$i].LastWriteTime))"
}

$index = Read-Host "Introduzca el número"
$archivo_final = $backups[[int]$index].FullName

Write-Host "`n⚠️ ADVERTENCIA: Se borrarán los datos actuales en '$db_name'." -ForegroundColor Yellow
$confirmar = Read-Host "¿Confirmar restauración? (S/N)"

if ($confirmar -match "S|s") {
    Write-Host "⏳ Restaurando desde: $archivo_final..." -ForegroundColor Cyan
    
    # 1. Intentar limpiar la base de datos (Opcional pero recomendado)
    # & $ruta_pg -U postgres -d postgres -c "DROP DATABASE IF EXISTS $db_name; CREATE DATABASE $db_name;"
    
    # 2. Ejecutar restauración
    & $ruta_pg -U postgres -p 5433 -d $db_name -f $archivo_final
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Base de datos restaurada con éxito!" -ForegroundColor Green
    } else {
        Write-Host "❌ Hubo un error en la restauración." -ForegroundColor Red
    }
} else {
    Write-Host "🚫 Operación cancelada." -ForegroundColor Gray
}

# Limpiar password de la memoria por seguridad
$env:PGPASSWORD = $null