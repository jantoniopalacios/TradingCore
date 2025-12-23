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

## Filtro Margen de Seguridad (MoS)

Este módulo gestiona la lógica de filtrado basada en el Margen de Seguridad (Margin of Safety),
que es un filtro fundamental opcional para asegurar que el precio del activo está por debajo de su valor intrínseco.

::: trading_engine.indicators.Filtro_MoS
    options:
      members:
        - update_mos_state
        - apply_mos_filter

## Filtro de Volumen (V-MA y Overshoot)

Este filtro de Volumen evalúa la actividad de la oferta/demanda no solo en base a la Media Móvil (V-MA), 
sino también mediante un concepto de **Umbral de Overshoot** que mide la persistencia de la fuerza.
Actúa como una condición AND para la entrada.

::: trading_engine.indicators.Filtro_Volume
    options:
      members:
        - calculate_volume_ma
        - update_volume_state
        - apply_volume_filter

## Filtro de Bandas de Bollinger (BB)
Este filtro identifica condiciones de volatilidad y niveles de sobreventa/sobrecompra. A diferencia de otros indicadores, este módulo admite una lógica flexible definida por el parámetro bb_buy_crossover:

Lógica de Toque (False): Activa la señal si el precio de cierre es inferior a la banda baja (ideal para capturar suelos en desplomes verticales).

Lógica de Cruce (True): Requiere que el precio cruce de fuera hacia dentro de la banda para confirmar la reversión.

::: trading_engine.indicators.Filtro_BollingerBands 
  options: 
    members: 
      - calculate_bollinger_bands 
      - update_bb_state 
      - check_bb_buy_signal 
      - check_bb_sell_signal