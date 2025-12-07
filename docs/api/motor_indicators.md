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