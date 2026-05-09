# Script para limpiar datos legacy de grafico_html en trading_db
$ruta_pg = "C:\Program Files\PostgreSQL\16\bin\"
$db_name = "trading_db"
$env:PGPASSWORD = "admin"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "[LIMPIEZA DE DATOS LEGACY]" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Mostrar tamaño actual
Write-Host "[ANALISIS] Tamaño actual..." -ForegroundColor Yellow

$sql_size = "SELECT pg_size_pretty(pg_database_size('$db_name')) as tamaño_BD, pg_size_pretty(pg_total_relation_size('resultados_backtest')) as tamaño_tabla;"

& "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_size

# 2. Contar registros con grafico_html
Write-Host "`n[INFO] Registros con grafico_html:" -ForegroundColor Yellow

$sql_count = "SELECT COUNT(*) as total, COUNT(CASE WHEN grafico_html IS NOT NULL THEN 1 END) as con_grafico, COUNT(CASE WHEN grafico_html IS NULL THEN 1 END) as sin_grafico FROM resultados_backtest;"

& "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_count

# 3. Mostrar opciones de limpieza
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "[OPCIONES DE LIMPIEZA]" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[1] Limpiar TODOS los grafico_html (LIBERA MAXIMO ESPACIO)" -ForegroundColor Red
Write-Host "[2] Limpiar solo registros con mayor antiguedad" -ForegroundColor Yellow
Write-Host "[3] Ver estadisticas por fecha y cancelar" -ForegroundColor Gray
Write-Host "[0] Cancelar sin hacer nada" -ForegroundColor Gray

$opcion = Read-Host "`nSeleccione opcion"

switch ($opcion) {
    "1" {
        Write-Host "`n[ADVERTENCIA] Se eliminaran TODOS los grafico_html." -ForegroundColor Red
        $confirmar = Read-Host "Confirmar? (S/N)"
        
        if ($confirmar -match "S|s") {
            Write-Host "`n[PROCESO] Limpiando grafico_html..." -ForegroundColor Cyan
            
            $sql_clean_all = "UPDATE resultados_backtest SET grafico_html = NULL WHERE grafico_html IS NOT NULL;"
            
            & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_clean_all
            
            Write-Host "`n[PROCESO] Ejecutando VACUUM FULL (puede tardar)..." -ForegroundColor Cyan
            & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c "VACUUM FULL ANALYZE;"
            
            Write-Host "`n[EXITO] Limpieza completada. Nuevo tamaño:" -ForegroundColor Green
            & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_size
        }
    }
    
    "2" {
        $dias = Read-Host "Cuantos dias de antiguedad? (ej: 30)"
        
        if ($dias -match '^\d+$') {
            Write-Host "`n[BUSQUEDA] Registros con mas de $dias dias..." -ForegroundColor Yellow
            
            $sql_check = "SELECT COUNT(*) as registros_antiguos, MIN(fecha_ejecucion) as mas_antiguo FROM resultados_backtest WHERE grafico_html IS NOT NULL AND fecha_ejecucion < NOW() - INTERVAL '$dias days';"
            
            & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_check
            
            $confirmar = Read-Host "`nProceder con limpieza? (S/N)"
            
            if ($confirmar -match "S|s") {
                Write-Host "`n[PROCESO] Limpiando registros mas antiguos de $dias dias..." -ForegroundColor Cyan
                
                $sql_clean_old = "UPDATE resultados_backtest SET grafico_html = NULL WHERE grafico_html IS NOT NULL AND fecha_ejecucion < NOW() - INTERVAL '$dias days';"
                
                & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_clean_old
                
                Write-Host "`n[PROCESO] Ejecutando VACUUM FULL (puede tardar)..." -ForegroundColor Cyan
                & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c "VACUUM FULL ANALYZE;"
                
                Write-Host "`n[EXITO] Limpieza completada. Nuevo tamaño:" -ForegroundColor Green
                & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_size
            }
        } else {
            Write-Host "`n[ERROR] Valor invalido." -ForegroundColor Red
        }
    }
    
    "3" {
        Write-Host "`n[ESTADISTICAS] Distribucion por antiguedad:" -ForegroundColor Yellow
        
        $sql_stats = "SELECT CASE WHEN fecha_ejecucion >= NOW() - INTERVAL '7 days' THEN '0-7 dias' WHEN fecha_ejecucion >= NOW() - INTERVAL '30 days' THEN '8-30 dias' ELSE '30+ dias' END as rango, COUNT(*) as registros, COUNT(CASE WHEN grafico_html IS NOT NULL THEN 1 END) as con_grafico FROM resultados_backtest GROUP BY rango ORDER BY rango;"
        
        & "$ruta_pg\psql.exe" -U postgres -p 5433 -d $db_name -c $sql_stats
    }
    
    "0" {
        Write-Host "`n[CANCELADO]" -ForegroundColor Gray
    }
    
    default {
        Write-Host "`n[ERROR] Opcion no valida." -ForegroundColor Red
    }
}

# Limpiar password
$env:PGPASSWORD = $null

Write-Host "`n========================================`n" -ForegroundColor Cyan
