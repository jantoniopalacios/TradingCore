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
4. Revisar parametros globales y usar el boton `Ayuda` de la pestaña Global para consultar ejemplos de stop loss, swing y break-even.
5. Activar indicadores de prueba (por ejemplo, EMA y MACD).
6. Pulsar `Lanzar Backtest`.

## Paso 5: Seguir el progreso por fases (sin refresco manual)

Al pulsar `Lanzar Backtest`, se abre un modal de progreso con:

- Fase actual del proceso (por ejemplo: descarga de datos, motor, persistencia).
- Barra de progreso porcentual.
- Bitacora de eventos en tiempo real.
- Boton `OK` bloqueado hasta que el proceso termine o falle.

Comportamiento esperado:

- Ya no es necesario refrescar la pantalla manualmente para saber si el backtest ha terminado.
- Cuando el estado pasa a `completed` o `error`, el boton `OK` se habilita.
- Al cerrar el modal (`OK`), la pagina se recarga para reflejar el historial SQL actualizado.

Nota sobre fechas:
- `end_date` se inicializa por defecto en `ayer`.
- `end_date` no se persiste en `config_actual` del usuario.
- Si se modifica manualmente para una ejecución, ese valor aplica a la ejecución actual y queda trazado en los resultados guardados.

Nota tecnica de seguimiento:

- El frontend consulta periodicamente el estado en `GET /backtest_status`.
- El backend reporta fases desde el orquestador `ejecutar_backtest(..., progress_callback=...)`.

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
