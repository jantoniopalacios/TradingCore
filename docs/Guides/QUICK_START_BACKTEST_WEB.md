# Quick Start: Backtest Web

## Objetivo
Validar en pocos minutos que el flujo web de backtest funciona, genera resultados y guarda datos en base de datos.

## Requisitos
- Entorno virtual activo.
- Dependencias instaladas (`requirements.txt`).
- PostgreSQL y configuración del proyecto operativos.

## Paso 1: Verificar sistema
```powershell
python scripts/verificar_backtest_web.py
```

Resultado esperado:
```text
VERIFICACION COMPLETA - Sistema listo para backtest desde web
```

## Paso 2: Monitorear logs en tiempo real
```powershell
Get-Content -Path ".\logs\trading_app.log" -Wait
```

## Paso 3: Iniciar servidor web
```powershell
python scenarios/BacktestWeb/app.py
```

## Paso 4: Ejecutar backtest desde la UI
1. Abrir `http://localhost:5000`.
2. Iniciar sesion con un usuario registrado.
3. Seleccionar simbolos (por ejemplo, `NKE`).
4. Activar indicadores de prueba (por ejemplo, EMA y MACD).
5. Pulsar `Lanzar Backtest`.

Nota sobre fechas:
- `end_date` se inicializa por defecto en `ayer`.
- `end_date` no se persiste en `config_actual` del usuario.
- Si se modifica manualmente para una ejecución, ese valor aplica a la ejecución actual y queda trazado en los resultados guardados.

Logs esperados (resumen):
```text
[LAUNCH] Usuario ... lanzando backtest
[1/9] Cargando configuracion
[8/9] Ejecutando motor de backtest multi-simbolo
Backtest completado
```

## Validacion de exito
- En logs se completan los pasos del orquestador.
- En web aparecen resultados y graficos.
- En base de datos se insertan filas en `resultados_backtest` y `trades`.

## Problema frecuente
Si aparece `Sin datos historicos descargados`, revisar:
- existencia de CSV en `Data_files/`.
- rango de fechas e intervalo configurados.
- conectividad con la fuente de datos.
