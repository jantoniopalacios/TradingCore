# Referencia API: Indicadores Técnicos

Este módulo contiene la implementación y la lógica de filtrado específica para cada indicador técnico.

## Filtro EMA (Exponential Moving Average)

::: trading_engine.indicators.Filtro_EMA
    options:
      members:
        - update_ema_state
        - check_ema_buy_signal
        - apply_ema_global_filter
        - check_ema_sell_signal

## Filtro RSI (Relative Strength Index)

::: trading_engine.indicators.Filtro_RSI
    options:
      members:
        - update_rsi_state
        - check_rsi_buy_signal
        - check_rsi_sell_signal

## Filtro MACD (Moving Average Convergence Divergence)

::: trading_engine.indicators.Filtro_MACD
    options:
      members:
        - update_macd_state
        - check_macd_buy_signal
        - check_macd_sell_signal

## Filtro MACD (Moving Average Convergence Divergence)
Este módulo contiene las funciones genéricas que se aplican a las diferentes versiones del oscilador Estocástico 
(Rápido, Medio y Lento) que la estrategia utilice. Se utilizan prefijos dinámicos (e.g., `stoch_fast`) para 
manejar los múltiples estados y configuraciones del oscilador.

::: trading_engine.indicators.Filtro_Stochastic
    options:
      members:
        - StochHelper
        - update_oscillator_state
        - check_oscillator_buy_signal
        - check_oscillator_sell_signal