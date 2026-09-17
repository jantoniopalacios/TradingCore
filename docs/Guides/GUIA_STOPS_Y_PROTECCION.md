# Guia: Stops y Proteccion de Capital

Ultima actualizacion: 17/09/2026

## Objetivo

Definir como configurar los mecanismos de stop loss, trailing stop y filtros de calidad de entrada disponibles en `BacktestWeb` para minimizar drawdown y proteger el capital inicial.

---

## 1. Principios

1. Defender primero, rentabilizar despues: priorizar estabilidad sobre retorno maximo puntual.
2. Evitar perdidas grandes: toda entrada debe nacer con una salida de riesgo definida.
3. Menos trades, mejores trades: filtrar ruido suele proteger mejor el capital.
4. Regla de comparacion consistente: optimizar con el mismo universo, fechas, comision y capital.

El motor combina varias protecciones sobre la misma posicion (stop base, break-even, swing y trailing RSI cuando estan activados). El stop efectivo conserva siempre el nivel mas protector entre las protecciones aplicables y nunca retrocede una vez endurecido (ver seccion 6 para el comportamiento actual de break-even).

---

## 2. Capas de control

### 2.1 Stop loss base (obligatorio)

Parametro: `stoploss_percentage_below_close`

Valores orientativos (no son reglas canonicas del motor, son puntos de partida para calibrar):

| Perfil | Valor orientativo |
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

Permite definir dos porcentajes de trailing en funcion del valor actual del RSI:
- Si RSI <= limite, se aplica el primer porcentaje configurado (`trailing_pct_below`).
- Si RSI > limite, se aplica el segundo porcentaje configurado (`trailing_pct_above`).

El efecto practico de cada porcentaje (mas o menos protector) depende de los valores que el usuario configure en cada caso; esta guia no asume una relacion fija de "mas proteccion" o "menos proteccion" mas alla de la comparacion aritmetica entre ambos porcentajes.

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


### 2.4 Filtros de calidad de entrada

Activar para reducir entradas de baja calidad:

- **Volatilidad ATR:** `atr_enabled=True`, rango calibrado por perfil de activo (ver tabla en seccion 4).
- **Volumen:** `volume_active=True`, `volume_avg_multiplier` ajustado.
- **Tendencia:** veto de compra en escenarios de debilidad estructural (ejemplo `ema_slow_descendente=True`).

---

## 3. Configuraciones semilla

Las siguientes semillas son puntos de partida orientativos/experimentales para calibrar, no reglas canonicas del motor.

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

El ATR debe calibrarse segun la volatilidad historica del activo. Los rangos siguientes son orientativos, no valores canonicos del motor; los valores por defecto de la aplicacion (`atr_min=2.0`, `atr_max=5.0`) pueden ser inadecuados para activos de baja volatilidad y requerir ajuste.

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

## 6. Comportamiento actual: Break-Even

El break-even es una proteccion ya implementada en el motor, activable por configuracion.

**Parametros:**
- `breakeven_enabled` (bool): activa esta proteccion.
- `breakeven_trigger_pct` (float): NO es una ganancia minima que deba alcanzarse para activar el break-even. Es el porcentaje usado para calcular el suelo de proteccion respecto al precio de entrada.

**Calculo del suelo:**
```
be_floor = entry_price * (1 - breakeven_trigger_pct)
```

**Comportamiento:**
1. Si `breakeven_enabled=True`, el suelo se calcula en cada vela a partir del precio de entrada y `breakeven_trigger_pct`.
2. El stop efectivo aplicado a la posicion conserva siempre el nivel mas protector entre las protecciones activas (stop base/trailing, break-even y swing).
3. El stop no retrocede una vez endurecido: solo puede mantenerse o subir.

Esta proteccion no rompe el comportamiento existente cuando `breakeven_enabled=False`.

---

## Referencias

- [Guia de combinacion de indicadores](./GUIA_COMBINACION_INDICADORES.md)
- [Arquitectura del motor](../ARCHITECTURE.md)
