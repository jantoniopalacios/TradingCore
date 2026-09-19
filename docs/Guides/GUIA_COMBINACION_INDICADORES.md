# Guia de combinacion de indicadores

Ultima actualizacion: 19/09/2026

## Objetivo
Definir combinaciones de indicadores que reduzcan falsos positivos y mejoren la calidad de entrada en backtest.

## Problema tipico
Usar un unico indicador (por ejemplo, solo cruce EMA) puede producir sobre-trading en mercados laterales.

## Combinaciones recomendadas
- `EMA + RSI`: confirmacion de tendencia y momentum.
- `EMA + MACD`: confirmacion de tendencia con sesgo mas fuerte. MACD consume directamente `macd_buy_logic` (`macd_cruce_up`, `macd_histogram_buy`, `None`) y `macd_sell_logic` (`macd_cruce_down`, `macd_histogram_sell`, `None`). Las opciones de histograma disparan al cruzar el nivel cero y `None` desactiva la señal MACD de ese lado.
- `EMA + RSI + ATR`: añade control de volatilidad para filtrar extremos.

## Regla base sugerida
Entrada si se cumple:
1. señal tecnica principal (EMA/RSI/MACD, logica OR).
2. filtros globales activos (logica AND): tendencia, momentum, volatilidad, volumen, MoS. Cada filtro solo interviene en la decision si esta activado explicitamente en la configuracion; un filtro inactivo no bloquea ni condiciona la entrada.

## Filtro ATR por perfil de activo
El ATR debe calibrarse por tipo de volatilidad. Los siguientes rangos son orientativos, no valores canonicos del motor.

| Perfil | ATR Min | ATR Max | Ejemplos |
| :--- | ---: | ---: | :--- |
| Baja volatilidad | 0.5 | 3.5 | NKE, WMT, JNJ |
| Media volatilidad | 1.5 | 5.0 | AAPL, MSFT, COST |
| Alta volatilidad | 2.0 | 7.0 | NVDA, TSLA, AMD |
| Especulativo | 3.0 | 15.0 | BTC, MEME |

## Flujo operativo recomendado
1. Ejecutar baseline sin ATR.
2. Probar ATR amplio (`0.1-20.0`) para validar logica.
3. Ajustar ATR por activo.
4. Comparar `Return`, `Win Rate`, `Max Drawdown` y `Total Trades`.

Para un caso concreto de calibracion sobre un activo especifico, ver la guia tecnica [GUIDE_TEST_NKE.md](./GUIDE_TEST_NKE.md).

## Referencias
- [Guía de prueba NKE](./GUIDE_TEST_NKE.md)
- [Quick Start Web](./QUICK_START_BACKTEST_WEB.md)
- [Guia de Stops y Proteccion](./GUIA_STOPS_Y_PROTECCION.md)
