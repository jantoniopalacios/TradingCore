# Referencia API: Indicadores Tecnicos

Ultima actualizacion: 20/09/2026

Este documento resume la implementacion y los contratos funcionales validados de los indicadores. La combinacion general de senales y filtros se describe en `docs/ARCHITECTURE.md` y `docs/Guides/GUIA_COMBINACION_INDICADORES.md`.

## Filtro EMA

::: trading_engine.indicators.Filtro_EMA
    options:
      members:
        - update_ema_state
        - check_ema_buy_signal
        - apply_ema_global_filter
        - check_ema_sell_signal

## Filtro RSI

::: trading_engine.indicators.Filtro_RSI
    options:
      members:
        - update_rsi_state
        - check_rsi_buy_signal
        - check_rsi_sell_signal

`rsi_strength_threshold` actua como filtro global cuando corresponde.

## Filtro MACD

::: trading_engine.indicators.Filtro_MACD
    options:
      members:
        - update_macd_state
        - check_macd_buy_signal
        - check_macd_sell_signal

Contrato UI -> motor validado:

- compra `macd_cruce_up`: cruce alcista MACD/Signal;
- compra `macd_histogram_buy`: histograma de no positivo a positivo;
- venta `macd_cruce_down`: cruce bajista MACD/Signal;
- venta `macd_histogram_sell`: histograma de no negativo a negativo;
- `None`: desactiva la senal de ese lado.

## Filtro Stochastic

::: trading_engine.indicators.Filtro_Stochastic
    options:
      members:
        - StochHelper
        - update_oscillator_state
        - check_oscillator_buy_signal
        - check_oscillator_sell_signal

Fast, Mid y Slow consumen directamente sus opciones de compra (`minimo`, `ascendente`, `None`) y venta (`maximo`, `descendente`, `None`). `None` no habilita una senal base.

## Filtro Margen de Seguridad (MoS)

::: trading_engine.indicators.Filtro_MoS
    options:
      members:
        - update_mos_state
        - apply_mos_filter

Cuando esta activo, exige superar `margen_seguridad_threshold`. Las confirmaciones `margen_seguridad_minimo` y `margen_seguridad_ascendente` son opcionales y se combinan mediante AND cuando se activan.

## Filtro de Volumen

::: trading_engine.indicators.Filtro_Volume
    options:
      members:
        - calculate_volume_ma
        - update_volume_state
        - apply_volume_filter

La referencia es una SMA de volumen (V-SMA). `volume_ascendente_STATE` representa la tendencia real de esa V-SMA; ya no se deriva de un contador interno de overshoots. El filtro exige nivel (`volumen > V-SMA * multiplicador`) y, si hay estados seleccionados, al menos uno de esos estados.

## Filtro ATR

::: trading_engine.indicators.Filtro_ATR
    options:
      members:
        - apply_atr_range_filter

ATR actua como filtro de entrada dentro del rango minimo/maximo configurado.

## Filtro de Bandas de Bollinger

::: trading_engine.indicators.Filtro_BollingerBands
    options:
      members:
        - calculate_bollinger_bands
        - update_bb_state
        - check_bb_buy_signal
        - check_bb_sell_signal

La compra Bollinger solo se considera cuando `bb_active` y `bb_buy_crossover` estan activos. En ese caso se exige un cruce alcista del precio sobre la banda inferior. Desactivar `bb_buy_crossover` no habilita una compra alternativa por toque o permanencia fuera de banda.

La salida Bollinger se activa con `bb_sell_crossover` cuando el precio cruza a la baja la banda superior o la SMA central. `bb_window_state` se conserva únicamente por compatibilidad de configuración y no participa actualmente en la lógica de señales o estados.

## Referencias

- Arquitectura canonica: `docs/ARCHITECTURE.md`
- Manual de usuario: `docs/User/MANUAL_USUARIO_TRADINGCORE.md`
- Guia de combinacion: `docs/Guides/GUIA_COMBINACION_INDICADORES.md`
