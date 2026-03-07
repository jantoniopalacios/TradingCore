# Guia de combinacion de indicadores

## Objetivo
Definir combinaciones de indicadores que reduzcan falsos positivos y mejoren la calidad de entrada en backtest.

## Problema tipico
Usar un unico indicador (por ejemplo, solo cruce EMA) puede producir sobre-trading en mercados laterales.

## Combinaciones recomendadas
- `EMA + RSI`: confirmacion de tendencia y momentum.
- `EMA + MACD`: confirmacion de tendencia con sesgo mas fuerte.
- `EMA + RSI + ATR`: añade control de volatilidad para filtrar extremos.

## Regla base sugerida
Entrada si se cumple:
1. señal tecnica principal (EMA/RSI/MACD, logica OR).
2. filtros globales (logica AND): tendencia, momentum, volatilidad, volumen, MoS.

## Filtro ATR por perfil de activo
El ATR debe calibrarse por tipo de volatilidad.

| Perfil | ATR Min | ATR Max | Ejemplos |
| :--- | ---: | ---: | :--- |
| Baja volatilidad | 0.5 | 3.5 | NKE, WMT, JNJ |
| Media volatilidad | 1.5 | 5.0 | AAPL, MSFT, COST |
| Alta volatilidad | 2.0 | 7.0 | NVDA, TSLA, AMD |
| Especulativo | 3.0 | 15.0 | BTC, MEME |

## Caso NKE
Diagnostico historico: el rango `2.0-5.0` bloquea exceso de oportunidades para NKE.

Configuracion orientativa:
```python
ema_fast_period = 10
ema_slow_period = 30
rsi_period = 14
rsi_strength_threshold = 54
atr_enabled = True
atr_period = 14
atr_min = 0.5
atr_max = 4.0
volume_active = True
volume_avg_multiplier = 1.0
```

## Flujo operativo recomendado
1. Ejecutar baseline sin ATR.
2. Probar ATR amplio (`0.1-20.0`) para validar logica.
3. Ajustar ATR por activo.
4. Comparar `Return`, `Win Rate`, `Max Drawdown` y `Total Trades`.

## Referencias
- [Diagnóstico Filtro ATR](../Diagnosis/DIAGNOSTICO_FILTRO_ATR_VOLATILIDAD.md)
- [Guía de prueba NKE](./GUIDE_TEST_NKE.md)
- [Quick Start Web](./QUICK_START_BACKTEST_WEB.md)
