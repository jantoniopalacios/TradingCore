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

## Paso 9: Tabla de parametros y efecto operativo

Esta tabla resume los parametros visibles en UI y su efecto practico.
Regla clave para interpretar B&H:

- B&H solo entra cuando no hay posicion abierta, no hay senales tecnicas activas y EMA lenta esta favorable.
- Si activas una senal tecnica (por ejemplo EMA cruce, RSI compra, MACD, Stoch o BB), B&H deja de ser el camino principal de entrada.

| Grupo | Parametro | Efecto operativo | Impacto sobre B&H / Compra |
|---|---|---|---|
| Global | `cash` | Capital inicial del backtest | No activa/bloquea senal |
| Global | `commission` | Comision por operacion | No activa/bloquea senal |
| Global | `intervalo` | Marco temporal (`1d`, `1wk`, etc.) | Cambia la serie de datos usada por todas las senales |
| Global | `stoploss_percentage_below_close` | Trailing stop base | Gestion de salida, no de entrada |
| Global | `enviar_mail` / `destinatario_email` | Notificacion al finalizar | Sin impacto en logica de trading |
| Stop | `breakeven_enabled` | Activa suelo de proteccion por entrada | Solo salida (riesgo) |
| Stop | `breakeven_trigger_pct` | Umbral para break-even | Solo salida (riesgo) |
| Stop | `stoploss_swing_enabled` | Activa stop por swing low | Solo salida (riesgo) |
| Stop | `stoploss_swing_lookback` | Ventana para swing low | Solo salida (riesgo) |
| Stop | `stoploss_swing_buffer` | Buffer bajo swing low | Solo salida (riesgo) |
| Stop | `rsi_trailing_limit` | Umbral RSI para trailing dinamico | Solo aplica si RSI esta ON |
| Stop | `trailing_pct_below` / `trailing_pct_above` | % trailing segun RSI bajo/alto | Solo aplica si RSI esta ON |
| EMA | `ema_slow_period` | Periodo de EMA lenta | Base para tendencia/filtro/B&H |
| EMA | `ema_fast_period` | Periodo de EMA rapida | Relevante en cruce EMA |
| EMA | `ema_cruce_signal` | Activa senal OR por cruce EMA | Si esta ON, B&H deja de actuar como entrada por defecto |
| EMA | `ema_slow_minimo` | Senal OR por estado minimo de EMA lenta | Si esta ON, ya hay via tecnica de compra |
| EMA | `ema_slow_ascendente` | Senal OR por EMA lenta ascendente | Si esta ON, ya hay via tecnica de compra |
| EMA | `ema_slow_maximo` | Condicion de venta tecnica EMA | Salida tecnica |
| EMA | `ema_slow_descendente` | Condicion de venta tecnica EMA | Salida tecnica |
| RSI | `rsi` | Activa calculo/uso de RSI | Permite filtros y senales RSI |
| RSI | `rsi_period` | Periodo RSI | Ajusta sensibilidad RSI |
| RSI | `rsi_low_level` | Nivel sobreventa compra | Usado por logica RSI compra |
| RSI | `rsi_high_level` | Nivel sobrecompra venta | Usado por logica RSI venta |
| RSI | `rsi_minimo` | Senal OR de compra RSI en minimo | Si ON, B&H queda desplazado por via tecnica |
| RSI | `rsi_ascendente` | Senal OR de compra RSI ascendente | Si ON, B&H queda desplazado por via tecnica |
| RSI | `rsi_maximo` | Senal de venta RSI | Salida tecnica |
| RSI | `rsi_descendente` | Senal de venta RSI descendente | Salida tecnica |
| RSI | `rsi_strength_threshold` | Filtro global de fuerza RSI | Puede bloquear compras, incluso B&H, cuando RSI esta ON |
| MACD | `macd` | Activa MACD | Si ON, hay via tecnica de compra/venta |
| MACD | `macd_fast` / `macd_slow` / `macd_signal` | Parametros de calculo MACD | Ajustan sensibilidad |
| MACD | `macd_maximo` / `macd_descendente` | Cierre tecnico MACD | Salida tecnica |
| STOCH | `stoch_fast` / `stoch_mid` / `stoch_slow` | Activa familia estocastica | Si ON, hay via tecnica de compra/venta |
| STOCH | `*_period` / `*_smooth` | Parametros de calculo Stoch | Ajustan sensibilidad |
| STOCH | `*_low_level` / `*_high_level` | Umbrales sobreventa/sobrecompra | Definen disparadores |
| STOCH | `*_minimo` / `*_ascendente` | Compra tecnica Stoch | Si ON, B&H queda desplazado por via tecnica |
| STOCH | `*_maximo` / `*_descendente` | Venta tecnica Stoch | Salida tecnica |
| BB | `bb_active` | Activa Bollinger Bands | Si ON, hay via tecnica de compra/venta |
| BB | `bb_window` / `bb_num_std` | Parametros de bandas | Ajustan ancho/sensibilidad |
| BB | `bb_buy_crossover` | Compra BB por cruce (o toque segun modo) | Si ON, B&H queda desplazado por via tecnica |
| BB | `bb_sell_crossover` | Cierre tecnico BB | Salida tecnica |
| Filtros | `atr_enabled` | Activa filtro de volatilidad ATR | Puede bloquear compras |
| Filtros | `atr_period` / `atr_min` / `atr_max` | Parametros de filtro ATR | Control de calidad de entrada |
| Fundamentales | `Margen_Seguridad_Active` | Activa filtro MoS | Puede bloquear compras |
| Fundamentales | `Margen_Seguridad_Threshold` | Umbral minimo MoS | Puede bloquear compras |
| Volumen | `volume_active` | Activa filtro/estado de volumen | Puede bloquear compras |
| Volumen | `volume_period` / `volume_avg_multiplier` | Parametros volumen | Ajustan filtro |

Notas rapidas de interpretacion:

1. `ON` en un indicador no implica compra inmediata; implica que esa familia puede aportar senal OR o filtro.
2. Si hay posicion abierta, no se abre una compra nueva hasta que se cierre la posicion actual.
3. El titulo corto del historial (`ESTRATEGIA`) es un resumen automatico, no reemplaza el detalle completo de configuracion.

## Validacion de exito
- En logs se completan los pasos del orquestador.
- En web aparecen resultados y graficos.
- En base de datos se insertan filas en `resultados_backtest` y `trades`.

## Problema frecuente
Si aparece `Sin datos historicos descargados`, revisar:
- existencia de CSV en `Data_files/`.
- rango de fechas e intervalo configurados.
- conectividad con la fuente de datos.

## Paso 10: Auditoria de Stops (pruebas realizadas y repeticion)

En esta fase se audito la logica de stops con scripts independientes, sin modificar codigo de produccion.

Scripts usados:

- `scripts/audit_stops_zts.py`: valida coherencia de TrailingBase por trade.
- `scripts/audit_stops_combinations.py`: valida combinaciones y ausencia de fugas de fuente (`TrailingBase`, `BreakEven`, `Swing`, `TrailingRSI...`).

### Configuracion comun de las pruebas

- Intervalo: `1d`
- Rango: `2023-01-01` a `2026-03-16`
- EMA lenta: `200`
- En escenarios base: indicadores tecnicos desactivados salvo donde se pruebe explicitamente RSI trailing.

### Pruebas realizadas

1. Auditoria TrailingBase por activo (`audit_stops_zts.py`)

- ZTS con stops `0.05`, `0.10`, `0.15`: sin hallazgos de logica de stop.
- SAN.MC con stops `0.05`, `0.10`, `0.15`: tras ajustar el modelo del auditor para reflejar exactamente el motor (stop inicial en cierre de compra y actualizacion con `High` desde la vela siguiente), sin hallazgos.

2. Auditoria de combinaciones (`audit_stops_combinations.py`) con stop `0.10`

- ZTS: sin fugas de fuente entre escenarios.
- SAN.MC: resultado reproducible, sin fugas de fuente entre escenarios.

Resumen operativo observado en SAN.MC (0.10):

- `trailing_base`: solo `TrailingBase`.
- `breakeven_only`: `BreakEven` y `TrailingBase`.
- `swing_only`: `TrailingBase` en este rango/parametros (Swing no llego a dominar).
- `breakeven_and_swing`: `BreakEven` y `TrailingBase`.
- `rsi_trailing_guard_off`: sin fuentes RSI (correcto).
- `rsi_trailing_on`: aparece `TrailingRSI<=Limite` (correcto).

### Conclusiones

- Validacion funcional satisfactoria para TrailingBase, BreakEven, Swing y trailing RSI en los escenarios auditados.
- No se detectaron bugs de logica de stop en los casos ejecutados.
- Queda pendiente solo una regresion de cobertura amplia (mas activos, otros intervalos y casos extremos de datos) si se requiere cierre al 100%.

### Hallazgos practicos adicionales

- Configuracion comun recomendada (perfil equilibrado):
	- `intervalo=1d`, `ema_slow_period=200`
	- `stoploss_percentage_below_close=0.10`
	- `breakeven_enabled=True`, `breakeven_trigger_pct=0.02`
	- `stoploss_swing_enabled=False` (activar solo en pruebas especificas)
	- `rsi_trailing` desactivado en baseline.
- Perfil alternativo defensivo para comparativa: `stoploss_percentage_below_close=0.08` con el resto igual.
- Buffer Swing conservador orientativo en `1d`: `0.3` a `0.8` (valor inicial sugerido: `0.5`).
- El modelo de stop actualizado usa politica **Close/Close**:
	- El trailing se actualiza con el maximo de cierres (`Close`).
	- La salida por stop se confirma por cierre (`Close < stop`).
	- Ventaja principal: semantica homogénea y mas facil de auditar/interpetar en pruebas EOD.

### Como repetir las pruebas

Desde la raiz del proyecto, con el entorno virtual activo:

```powershell
c:/Users/juant/Proyectos/Python/TradingCore/.venv/Scripts/python.exe scripts/audit_stops_zts.py --symbol ZTS --interval 1d --start 2023-01-01 --end 2026-03-16 --ema-slow 200 --stops 0.05 0.10 0.15

c:/Users/juant/Proyectos/Python/TradingCore/.venv/Scripts/python.exe scripts/audit_stops_zts.py --symbol SAN.MC --interval 1d --start 2023-01-01 --end 2026-03-16 --ema-slow 200 --stops 0.05 0.10 0.15

c:/Users/juant/Proyectos/Python/TradingCore/.venv/Scripts/python.exe scripts/audit_stops_combinations.py --symbol ZTS --interval 1d --start 2023-01-01 --end 2026-03-16 --ema-slow 200 --stop 0.10

c:/Users/juant/Proyectos/Python/TradingCore/.venv/Scripts/python.exe scripts/audit_stops_combinations.py --symbol SAN.MC --interval 1d --start 2023-01-01 --end 2026-03-16 --ema-slow 200 --stop 0.10
```

Resultado esperado de exito:

- `audit_stops_zts.py`: mensaje `No stop logic issues detected in audited scenario.`
- `audit_stops_combinations.py`: mensaje `No source-leak issues detected in stop combination scenarios.`
