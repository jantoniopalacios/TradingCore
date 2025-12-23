# Referencia API: Motor Central

Este módulo contiene las funciones de coordinación y toma de decisiones del motor.

## Lógica de Trading

::: trading_engine.core.Logica_Trading
    options:
      members:
        - check_buy_signal
        - manage_existing_position
        - _log_trade_action_sl_update
        - _actualizar_estados_indicadores

## Coordinación de Señales y Logs
El motor central actúa como el cerebro del sistema, evaluando secuencialmente las condiciones técnicas de cada indicador habilitado. La arquitectura permite que cada filtro contribuya con una "razón" específica al proceso de decisión, garantizando la trazabilidad total en el backtesting.

## El Diccionario technical_reasons
Una de las características clave de Logica_Trading.py es el uso del diccionario technical_reasons. Este objeto recolecta los argumentos de cada indicador que valida la entrada:

Persistencia: Si múltiples indicadores validan la entrada, el log final incluirá todas las claves (ej. BB, RSI, EMA).

Transparencia: Almacena valores reales del mercado en el momento de la señal (ej. Precio 124.46 < Banda 133.87), lo cual es crítico para la depuración post-operación.

## Flujo de Decisión
Actualización de Estados: Se invocan las funciones update_xxx_state para sincronizar los indicadores con la vela actual.

Evaluación Técnica: Se verifica si los filtros activos (EMA, RSI, BB, etc.) cumplen sus condiciones.

Gestión de Posición: Si ya existe una posición abierta, el motor delega el control a manage_existing_position para evaluar salidas por Stop Loss, Take Profit o señales contrarias.

::: trading_engine.core.Logica_Trading 
  options: 
    members: 
      - check_buy_signal 
      - manage_existing_position 
      - _log_trade_action_sl_update 
      - _actualizar_estados_indicadores