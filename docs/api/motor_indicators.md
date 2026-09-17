# Referencia API: Indicadores Tecnicos

Ultima actualizacion: 17/09/2026

Este documento resume la implementacion y la logica de filtrado especifica de los indicadores tecnicos. La combinacion funcional de senales y filtros se describe en `docs/ARCHITECTURE.md`.

## Filtro EMA (Exponential Moving Average)

::: trading_engine.indicators.Filtro_EMA
    options:
      members:
        - update_ema_state
        - check_ema_buy_signal
        - apply_ema_global_filter
        - check_ema_sell_signal

EMA puede participar tanto como senal tecnica como filtro global, segun la configuracion activa.

## Filtro RSI (Relative Strength Index)

::: trading_engine.indicators.Filtro_RSI
    options:
      members:
        - update_rsi_state
        - check_rsi_buy_signal
        - check_rsi_sell_signal

RSI puede aportar senales tecnicas y tambien intervenir como filtro global de fuerza cuando esa condicion esta configurada. El valor por defecto actual de `rsi_strength_threshold` es `50`.

## Filtro MACD (Moving Average Convergence Divergence)

::: trading_engine.indicators.Filtro_MACD
    options:
      members:
        - update_macd_state
        - check_macd_buy_signal
        - check_macd_sell_signal

La interfaz usa `macd_buy_logic` y `macd_sell_logic` para seleccionar la logica de compra y venta. Las opciones basadas en histograma estan pendientes de revision funcional respecto a su integracion con la logica interna; no debe asumirse comportamiento no validado para esas opciones.

## Filtro Stochastic (Fast, Mid, Slow)

Este modulo contiene funciones genericas aplicables a las distintas variantes del oscilador estocastico (rapido, medio y lento). Se utilizan prefijos dinamicos, por ejemplo `stoch_fast`, para manejar sus estados y configuraciones.

::: trading_engine.indicators.Filtro_Stochastic
    options:
      members:
        - StochHelper
        - update_oscillator_state
        - check_oscillator_buy_signal
        - check_oscillator_sell_signal

## Filtro Margen de Seguridad (MoS)

MoS es un filtro fundamental opcional que puede condicionar la entrada cuando esta activado.

::: trading_engine.indicators.Filtro_MoS
    options:
      members:
        - update_mos_state
        - apply_mos_filter

## Filtro de Volumen

El filtro de volumen actua como condicion global de entrada cuando esta activado.

::: trading_engine.indicators.Filtro_Volume
    options:
      members:
        - update_volume_state
        - apply_volume_filter

## Filtro de Volatilidad ATR

ATR filtra entradas segun el rango de volatilidad configurado mediante sus limites minimo y maximo cuando el filtro esta activo.

::: trading_engine.indicators.Filtro_ATR
    options:
      members:
        - apply_atr_range_filter

## Filtro de Bandas de Bollinger (BB)

Bollinger Bands puede aportar senales tecnicas de compra y venta. El parametro `bb_buy_crossover` permite distinguir entre la logica configurada de toque y la de cruce.

::: trading_engine.indicators.Filtro_BollingerBands
    options:
      members:
        - calculate_bollinger_bands
        - update_bb_state
        - check_bb_buy_signal
        - check_bb_sell_signal

## Referencias

- Arquitectura canonica: `docs/ARCHITECTURE.md`
- Guia de combinacion: `docs/Guides/GUIA_COMBINACION_INDICADORES.md`
