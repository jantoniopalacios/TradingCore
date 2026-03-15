# Plan de Proteccion del Capital Inicial

## Objetivo
Definir una estrategia practica para minimizar la perdida del capital inicial en `BacktestWeb`, aprovechando las capacidades actuales de stop loss, trailing stop y filtros de calidad de entrada.

## Alcance
Este plan aplica a ejecuciones desde `scenarios/BacktestWeb/` y se centra en:
- limitar drawdown.
- reducir entradas de baja calidad.
- mantener trazabilidad de decisiones para iterar parametros.

## Principios de proteccion de capital
1. Defender primero, rentabilizar despues: priorizar estabilidad sobre retorno maximo puntual.
2. Evitar perdidas grandes: toda entrada debe nacer con una salida de riesgo definida.
3. Menos trades, mejores trades: filtrar ruido suele proteger mejor el capital.
4. Regla de comparacion consistente: optimizar con el mismo universo, fechas, comision y capital.

## Capas de control recomendadas

## Limitacion detectada en el motor actual
Con la logica actual, el stop loss y el trailing se recalculan en todo momento sobre el maximo y no existe una fase explicita de proteccion del precio de entrada (break-even).

Impacto practico observado:
- si el stop es agresivo, protege capital pero corta ganadores pronto.
- si el stop es amplio, deja correr beneficio pero tolera mas retrocesos sobre capital.

Esta tension es estructural y no siempre se resuelve solo con ajuste de parametros.

### 1. Stop loss base (obligatorio)
Parametro principal:
- `stoploss_percentage_below_close`

Recomendacion inicial por perfil:
- conservador: `0.03` a `0.05`
- balanceado: `0.05` a `0.07`
- agresivo: `0.07` a `0.10`

### 2. Stop loss por estructura (swing)
Parametros:
- `stoploss_swing_enabled`
- `stoploss_swing_lookback`
- `stoploss_swing_buffer`

Recomendacion inicial:
- `stoploss_swing_enabled=True`
- `stoploss_swing_lookback=10` o `12`
- `stoploss_swing_buffer=1.0`

### 3. Trailing stop dinamico por RSI
Parametros:
- `rsi_trailing_limit`
- `trailing_pct_below`
- `trailing_pct_above`

Recomendacion inicial:
- `rsi_trailing_limit=40`
- `trailing_pct_below=2.0`
- `trailing_pct_above=0.8`

Nota:
- el motor acepta tanto porcentaje en escala `0-1` como `0-100`; para homogeneidad de pruebas usar formato porcentaje (por ejemplo `2.0`, `0.8`).

### 4. Reduccion de entradas con perdida
Activar filtros globales para reducir entradas de baja calidad:
- volatilidad: `atr_enabled=True`, `atr_period=14`, rango calibrado por activo (`atr_min`, `atr_max`).
- volumen: `volume_active=True` y umbral de calidad (`volume_avg_multiplier`).
- tendencia: veto de compra en escenarios de debilidad estructural (por ejemplo `ema_slow_descendente`).

## Evolucion minima propuesta: fase Break-Even

### Objetivo
Separar la gestion de riesgo en dos fases:
1. fase de proteccion del capital hasta blindar la entrada.
2. fase de captura de beneficio con trailing.

### Parametros nuevos propuestos
- `breakeven_enabled` (bool): activa la logica break-even.
- `breakeven_trigger_pct` (float): ganancia minima para armar break-even (ejemplo `0.02` = 2%).

### Comportamiento esperado
1. al abrir posicion, se mantiene el esquema actual de stop inicial.
2. si el precio alcanza `entry_price * (1 + breakeven_trigger_pct)`, el stop sube al menos a:
   - `entry_price`
3. una vez armado break-even, el trailing continua normalmente, pero nunca baja de ese umbral.

### Integracion tecnica sugerida
- Carga/configuracion:
   - `scenarios/BacktestWeb/configuracion.py`
   - `scenarios/BacktestWeb/estrategia_system.py`
- Tooltips en UI:
   - `trading_engine/core/constants.py`
- Lado estrategia (campos en formulario global de riesgo):
   - `scenarios/BacktestWeb/templates/_tab_global.html`
- Logica de ejecucion:
   - `trading_engine/core/Logica_Trading.py`

Nota:
- Esta evolucion es acotada y no rompe la estrategia actual cuando `breakeven_enabled=False`.

## Configuraciones semilla

### Semilla A (conservadora)
```text
stoploss_percentage_below_close = 0.04
stoploss_swing_enabled = True
stoploss_swing_lookback = 12
stoploss_swing_buffer = 1.0
rsi_trailing_limit = 40
trailing_pct_below = 2.0
trailing_pct_above = 0.8
atr_enabled = True
atr_period = 14
atr_min = 0.5
atr_max = 4.0
volume_active = True
```

### Semilla B (balanceada)
```text
stoploss_percentage_below_close = 0.06
stoploss_swing_enabled = True
stoploss_swing_lookback = 10
stoploss_swing_buffer = 0.8
rsi_trailing_limit = 40
trailing_pct_below = 2.2
trailing_pct_above = 1.0
atr_enabled = True
atr_period = 14
atr_min = 0.8
atr_max = 5.0
volume_active = True
```

### Semilla C (control agresivo)
```text
stoploss_percentage_below_close = 0.08
stoploss_swing_enabled = False
rsi_trailing_limit = 45
trailing_pct_below = 2.5
trailing_pct_above = 1.2
atr_enabled = True
atr_period = 14
atr_min = 1.0
atr_max = 6.0
volume_active = True
```

## Matriz de validacion para optimizacion

Usar el mismo set de simbolos, rango temporal, comision y capital para todos los casos.

| Caso | Objetivo | Cambios vs baseline | Criterio de exito |
| :--- | :--- | :--- | :--- |
| M0 Baseline | Medir punto de partida | Config actual sin ajustes extra | Registrar `Return`, `Max Drawdown`, `# Trades`, `Win Rate`, `Profit Factor` |
| M1 Stop fijo estricto | Reducir perdidas maximas | `stoploss_percentage_below_close=0.04` | `Max Drawdown` menor que M0 |
| M2 Stop fijo balanceado | Mantener control con mas holgura | `stoploss_percentage_below_close=0.06` | Mejor ratio `Return/Drawdown` que M1 |
| M3 Swing ON | Proteger por estructura | M2 + `stoploss_swing_enabled=True`, `lookback=10`, `buffer=1.0` | `Max Drawdown` menor que M2 sin desplome fuerte de `Return` |
| M4 Trailing RSI ON | Proteger beneficios | M3 + `rsi_trailing_limit=40`, `trailing_pct_below=2.0`, `trailing_pct_above=0.8` | Mejora `Profit Factor` o `Win Rate` vs M3 |
| M5 ATR ON | Evitar entradas en ruido extremo | M4 + `atr_enabled=True`, rango calibrado | Menor # de trades de baja calidad y drawdown mas estable |
| M6 Volumen ON | Filtrar liquidez debil | M5 + `volume_active=True` | Caida de trades con deterioro limitado de retorno |
| M7 Comparativa final | Elegir preset candidato | Comparar Semilla A/B/C | Seleccionar la menor `Max Drawdown` con `Return` aceptable |
| M8 Break-Even ON | Proteger entrada sin matar tendencia | M4 + `breakeven_enabled=True`, `trigger=0.02` | Menos operaciones perdedoras despues de ganancias iniciales |

## Reglas de decision (pass/fail)
1. Rechazar configuraciones con `Max Drawdown` peor que baseline M0.
2. Rechazar configuraciones con mejora minima de drawdown pero fuerte deterioro de retorno.
3. Priorizar configuraciones con mejor equilibrio entre:
   - `Max Drawdown` bajo
   - `Profit Factor` >= baseline
   - `Win Rate` estable o mejor
4. En empate, elegir la que tenga menor varianza de resultados entre simbolos.

## Plantilla de registro de resultados

```text
Fecha:
Dataset / Periodo:
Simbolos:
Capital inicial:
Comision:

Caso:
Parametros modificados:
Return [%]:
Max Drawdown [%]:
# Trades:
Win Rate [%]:
Profit Factor:
Observaciones:
Decision (Pass/Fail):
```

## Plan de ejecucion sugerido
1. Ejecutar M0 y congelar baseline.
2. Ejecutar M1-M4 para calibrar bloque de stop/trailing.
3. Ejecutar M5-M6 para calibrar filtros de entrada.
4. Ejecutar M7 (A/B/C) y elegir preset candidato por equilibrio retorno-riesgo.
5. Ejecutar M8 para validar mejora estructural de proteccion de entrada.
6. Documentar preset ganador y aplicarlo como configuracion recomendada por perfil.

## Riesgos conocidos
- Sobreajuste por activo si solo se valida con un simbolo.
- Parametros de ATR no transferibles entre perfiles de volatilidad.
- Exceso de filtros puede reducir demasiado el numero de oportunidades.

## Estado de implementacion
Cambios aplicados en codigo para version minima Break-Even (sin offset):
- UI: `breakeven_enabled`, `breakeven_trigger_pct` en `scenarios/BacktestWeb/templates/_tab_global.html`.
- Carga de configuracion: `scenarios/BacktestWeb/configuracion.py`.
- Parametros de estrategia: `scenarios/BacktestWeb/estrategia_system.py`.
- Procesamiento de formulario booleano: `scenarios/BacktestWeb/routes/main_bp.py`.
- Logica de stop en runtime: `trading_engine/core/Logica_Trading.py`.
- Tooltips/documentacion de parametros: `trading_engine/core/constants.py`.

## Referencias
- [Guia Trailing Stop RSI](../Guia/GUIA_TRAILING_STOP_RSI.md)
- [Guia de combinacion de indicadores](../Guides/GUIA_COMBINACION_INDICADORES.md)
- [Diagnostico filtro ATR](../Diagnosis/DIAGNOSTICO_FILTRO_ATR_VOLATILIDAD.md)
- [Arquitectura canónica](../ARCHITECTURE.md)
