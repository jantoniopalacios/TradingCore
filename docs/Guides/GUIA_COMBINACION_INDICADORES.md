# Guia de combinacion de indicadores

Ultima actualizacion: 20/09/2026

## Objetivo
Definir como se combinan las senales tecnicas y los filtros de entrada con el comportamiento validado actualmente en TradingCore.

## Regla general
Las senales tecnicas de compra se combinan por logica OR. Despues, los filtros globales activos deben autorizar la entrada mediante logica AND. Un filtro inactivo no bloquea la compra.

## Combinaciones recomendadas

Estas combinaciones son puntos de partida para backtest, no reglas universales:

- `EMA + RSI`: tendencia y momentum.
- `EMA + MACD`: tendencia y confirmacion de impulso.
- `EMA + RSI + ATR`: senal tecnica con control adicional de volatilidad.
- Cualquiera de las anteriores puede endurecerse con Volumen y/o MoS como filtros de entrada.

## Contratos validados

- `MACD`: `macd_cruce_up` cruza MACD sobre Signal; `macd_histogram_buy` cruza histograma de no positivo a positivo. En venta, `macd_cruce_down` y `macd_histogram_sell` aplican los cruces inversos. `None` desactiva ese lado.
- `Stochastic`: cada familia Fast/Mid/Slow consume directamente su opcion de compra (`minimo`, `ascendente`, `None`) y venta (`maximo`, `descendente`, `None`). `None` no genera senal.
- `Bollinger`: la compra solo existe cuando `bb_active` y `bb_buy_crossover` estan activos y se produce un cruce alcista de la banda inferior. Desactivar el crossover no equivale a una compra por toque.
- `ATR`: filtro AND de volatilidad dentro del rango configurado.
- `MoS`: exige superar el umbral y, si se activan, cumplir `margen_seguridad_minimo` y/o `margen_seguridad_ascendente`; las confirmaciones activas son AND.
- `Volumen`: usa una SMA de volumen. El volumen actual debe superar `V-SMA * volume_avg_multiplier`. `volume_minimo` y `volume_ascendente` son estados de la V-SMA; los estados seleccionados se combinan por OR entre ellos, manteniendose el umbral de nivel como condicion obligatoria.

## Buy & Hold de respaldo
La via B&H solo debe considerarse desplazada por una condicion tecnica de compra realmente utilizable. Tener un indicador activo sin una logica de compra seleccionada no debe bastar por si solo para anular el respaldo.

## Filtro ATR por perfil de activo
Los siguientes rangos son orientativos y no valores canonicos del motor.

| Perfil | ATR Min | ATR Max | Ejemplos |
| :--- | ---: | ---: | :--- |
| Baja volatilidad | 0.5 | 3.5 | NKE, WMT, JNJ |
| Media volatilidad | 1.5 | 5.0 | AAPL, MSFT, COST |
| Alta volatilidad | 2.0 | 7.0 | NVDA, TSLA, AMD |
| Especulativo | 3.0 | 15.0 | BTC, MEME |

## Flujo operativo recomendado
1. Definir primero las vias tecnicas de entrada.
2. Activar filtros globales de uno en uno.
3. Verificar que cada filtro reduce o conserva operaciones por el motivo esperado.
4. Comparar `Return`, `Win Rate`, `Max Drawdown` y `Total Trades`.
5. Guardar la configuracion validada antes de recargar o cerrar la sesion.

## Referencias

- Manual de usuario: `docs/User/MANUAL_USUARIO_TRADINGCORE.md`
- Guia de prueba NKE: `docs/Guides/GUIDE_TEST_NKE.md`
- Quick Start Web: `docs/Guides/QUICK_START_BACKTEST_WEB.md`
- Guia de stops: `docs/Guides/GUIA_STOPS_Y_PROTECCION.md`
- Referencia tecnica: `docs/api/motor_indicators.md`
