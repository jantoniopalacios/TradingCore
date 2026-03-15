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

## Paso 6: Entender guardado y navegacion de pestañas

Comportamiento actual de UX en `Configuracion`:

- El cambio entre sub-pestañas (`Global`, `EMA`, `RSI`, etc.) es instantaneo y no debe mostrar pantallazo intermedio de `Global`.
- Cambiar de sub-pestaña no guarda automaticamente en base de datos.
- No hace falta pulsar `Guardar Config` al cambiar de una sub-pestaña a otra: los valores editados siguen en el formulario mientras no haya recarga.

Cuando SI guardar:

- Antes de una accion que recargue pantalla.
- Antes de cerrar sesion o salir de la pagina.

Importante:

- `Guardar Config` se ejecuta por AJAX y ya no provoca recarga completa de la pagina.
- Si ocurre una recarga, los cambios no guardados en BD pueden perderse.

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

## Paso 7: Entender el Stop Loss combinado (trailing + RSI + break-even + swing)

Esta aplicacion combina varias protecciones sobre la misma posicion. No se excluyen entre si: se solapan para endurecer el stop.

Regla practica para usuario:

- En cada vela, el sistema calcula varios niveles candidatos de stop.
- Se queda con el nivel mas alto (el mas protector).
- El stop final solo puede subir o quedarse igual; nunca baja.

Orden de intervencion habitual:

1. Stop trailing base (o trailing dinamico segun RSI, si ese ajuste esta activado).
2. Suelo de break-even (si esta activado): evita que el stop quede por debajo del nivel de proteccion definido por ese porcentaje.
3. Stop por swing (si esta activado): si propone un nivel mas alto, aprieta aun mas el stop.

Ejemplo conceptual:

- Si compras a 100 y usas break-even 2%, el suelo de proteccion es 98.
- Si ademas usas trailing 10%, el trailing no puede dejar el stop por debajo de ese suelo mientras break-even este activo.
- Si el swing calcula un stop en 99, mandara swing (por ser mas protector que 98).

### Analisis critico (comportamiento real)

Puntos importantes para interpretar resultados en la UI:

1. La salida por stop se valida con cierre de vela.
Si durante la vela el precio perfora el stop y luego recupera al cierre, puede que no salga en esa vela.

2. El motivo mostrado en "Operaciones Detalladas" para una venta por stop puede reflejar la logica dominante de esa vela, no siempre el origen historico exacto del nivel que venia aplicandose.

3. En mercado con gap, la ejecucion real puede salir por debajo del nivel de stop esperado (slippage), incluso con break-even o suelo activo.

### Recomendacion de uso

- Si buscas menos ruido, combina trailing mas holgado con swing.
- Si priorizas proteger capital, usa break-even con porcentaje conservador y revisa que el trailing no sea excesivamente amplio.
- Interpreta el motivo de salida como "causa operativa de esa vela", no como auditoria historica perfecta de todo el trayecto del stop.

## Paso 8: Revisar documentacion desde el explorador web

En modo Admin, la pestaña `Ficheros` ya incluye tambien la carpeta `docs` (ademas de `logs`).

Comportamiento esperado:

- Puedes navegar subcarpetas de documentacion (`docs/...`) desde la propia UI.
- Puedes abrir y descargar archivos de documentacion sin salir de la aplicacion.
- El borrado de archivos se mantiene restringido a `logs` (en `docs` no aparece papelera).

Nota de seguridad:

- El visor solo permite lectura dentro de rutas controladas del explorador (`logs` y `docs`).
- No se permite navegar fuera de esas raices mediante rutas manuales.

## Validacion de exito
- En logs se completan los pasos del orquestador.
- En web aparecen resultados y graficos.
- En base de datos se insertan filas en `resultados_backtest` y `trades`.

## Problema frecuente
Si aparece `Sin datos historicos descargados`, revisar:
- existencia de CSV en `Data_files/`.
- rango de fechas e intervalo configurados.
- conectividad con la fuente de datos.
