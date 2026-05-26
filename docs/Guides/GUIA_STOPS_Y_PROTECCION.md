# Guia: Stops y Proteccion de Capital

## Objetivo

Definir como configurar los mecanismos de stop loss, trailing stop y filtros de calidad de entrada disponibles en `BacktestWeb` para minimizar drawdown y proteger el capital inicial.

---

## 1. Principios

1. Defender primero, rentabilizar despues: priorizar estabilidad sobre retorno maximo puntual.
2. Evitar perdidas grandes: toda entrada debe nacer con una salida de riesgo definida.
3. Menos trades, mejores trades: filtrar ruido suele proteger mejor el capital.
4. Regla de comparacion consistente: optimizar con el mismo universo, fechas, comision y capital.

**Limitacion estructural del motor actual:** el stop loss y el trailing se recalculan sobre el maximo de precio y no existe una fase explicita de break-even. Esta tension entre proteccion temprana y captura de beneficio es estructural y no se resuelve solo con ajuste de parametros (ver seccion 5 para propuesta de evolucion).

---

## 2. Capas de control

### 2.1 Stop loss base (obligatorio)

Parametro: `stoploss_percentage_below_close`

| Perfil | Valor recomendado |
| :--- | :--- |
| Conservador | `0.03` a `0.05` |
| Balanceado | `0.05` a `0.07` |
| Agresivo | `0.07` a `0.10` |

### 2.2 Stop loss por estructura de precio (swing)

Parametros:
- `stoploss_swing_enabled` (bool)
- `stoploss_swing_lookback` (int): numero de velas hacia atras para detectar minimo local.
- `stoploss_swing_buffer` (float): buffer adicional en porcentaje sobre el minimo.

Recomendacion inicial:
```
stoploss_swing_enabled = True
stoploss_swing_lookback = 10
stoploss_swing_buffer = 1.0
```

### 2.3 Trailing stop dinamico por RSI

Permite definir dos porcentajes de trailing segun el estado del RSI:
- Si RSI <= limite → se aplica trailing mas amplio (mayor proteccion).
- Si RSI > limite → se aplica trailing mas ajustado (deja correr la posicion).

Parametros:
- `rsi_trailing_limit` (int): nivel de RSI que separa los dos regimenes.
- `trailing_pct_below` (float): % trailing cuando RSI <= limite.
- `trailing_pct_above` (float): % trailing cuando RSI > limite.

Ejemplo practico:
```
rsi_trailing_limit = 40
trailing_pct_below = 2.0    # RSI en 35: trailing 2% bajo el maximo
trailing_pct_above = 0.8    # RSI en 55: trailing 0.8% bajo el maximo
```

**Nota:** el motor acepta el porcentaje en formato decimal o entero; para homogeneidad usar formato porcentaje (ejemplo `2.0`, `0.8`).

### 2.4 Filtros de calidad de entrada

Activar para reducir entradas de baja calidad:

- **Volatilidad ATR:** `atr_enabled=True`, rango calibrado por perfil de activo (ver tabla en seccion 4).
- **Volumen:** `volume_active=True`, `volume_avg_multiplier` ajustado.
- **Tendencia:** veto de compra en escenarios de debilidad estructural (ejemplo `ema_slow_descendente=True`).

---

## 3. Configuraciones semilla

### Semilla A — Conservadora

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

### Semilla B — Balanceada

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

### Semilla C — Control agresivo

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

---

## 4. Calibracion ATR por perfil de activo

El ATR debe calibrarse segun la volatilidad historica del activo. Los valores por defecto (2.0-5.0) son inadecuados para activos de baja volatilidad como NKE, ya que bloquean la mayoria de entradas.

| Perfil | ATR Min | ATR Max | Ejemplos |
| :--- | ---: | ---: | :--- |
| Baja volatilidad | 0.5 | 3.5 | NKE, WMT, JNJ |
| Media volatilidad | 1.5 | 5.0 | AAPL, MSFT, COST |
| Alta volatilidad | 2.0 | 7.0 | NVDA, TSLA, AMD |
| Especulativo | 3.0 | 15.0 | BTC |

**Flujo de calibracion recomendado:**
1. Ejecutar baseline sin ATR para obtener referencia.
2. Activar ATR con rango amplio (`0.1-20.0`) para validar que la logica no bloquea nada.
3. Ajustar rango por perfil del activo hasta equilibrar numero de trades y calidad.
4. Comparar `Return`, `Win Rate`, `Max Drawdown` y `Total Trades`.

---

## 5. Matriz de validacion de optimizacion

Usar el mismo universo de simbolos, rango temporal, comision y capital para todos los casos.

| Caso | Objetivo | Cambios vs baseline | Criterio de exito |
| :--- | :--- | :--- | :--- |
| M0 Baseline | Medir punto de partida | Config actual sin ajustes extra | Registrar `Return`, `Max Drawdown`, `# Trades`, `Win Rate`, `Profit Factor` |
| M1 Stop fijo estricto | Reducir perdidas maximas | `stoploss_percentage_below_close=0.04` | `Max Drawdown` menor que M0 |
| M2 Stop fijo balanceado | Mantener control con mas holgura | `stoploss_percentage_below_close=0.06` | Mejor ratio `Return/Drawdown` que M1 |
| M3 Swing ON | Proteger por estructura | M2 + `stoploss_swing_enabled=True` | `Max Drawdown` menor que M2 |
| M4 Trailing RSI ON | Proteger beneficios | M3 + trailing RSI | Mejora `Profit Factor` o `Win Rate` |
| M5 ATR ON | Evitar entradas en ruido extremo | M4 + ATR calibrado | Menor # trades de baja calidad |
| M6 Volumen ON | Filtrar liquidez debil | M5 + `volume_active=True` | Caida de trades con deterioro limitado de retorno |

---

## 6. Propuesta de evolucion: Break-Even

**Objetivo:** separar la gestion de riesgo en dos fases:
1. Proteccion del capital hasta blindar la entrada.
2. Captura de beneficio con trailing.

**Parametros propuestos:**
- `breakeven_enabled` (bool): activa la logica break-even.
- `breakeven_trigger_pct` (float): ganancia minima para activar break-even (ejemplo `0.02` = 2%).

**Comportamiento esperado:**
1. Al abrir posicion, se mantiene el stop inicial.
2. Si el precio alcanza `entry_price * (1 + breakeven_trigger_pct)`, el stop sube al precio de entrada.
3. El trailing continua normalmente, pero nunca baja del umbral de entrada.

**Puntos de integracion:**
- `scenarios/BacktestWeb/configuracion.py`
- `scenarios/BacktestWeb/estrategia_system.py`
- `trading_engine/core/Logica_Trading.py`
- `scenarios/BacktestWeb/templates/_tab_global.html`

Esta evolucion es acotada y no rompe la estrategia actual cuando `breakeven_enabled=False`.

---

## Referencias

- [Guia de combinacion de indicadores](./GUIA_COMBINACION_INDICADORES.md)
- [Arquitectura del motor](../ARCHITECTURE.md)
