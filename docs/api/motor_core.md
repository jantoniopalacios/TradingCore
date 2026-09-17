# Referencia API: Motor Central

Ultima actualizacion: 17/09/2026

Este documento resume las funciones de coordinacion y toma de decisiones del motor. La arquitectura funcional vigente se documenta en `docs/ARCHITECTURE.md`.

## Logica de Trading

::: trading_engine.core.Logica_Trading
    options:
      members:
        - check_buy_signal
        - manage_existing_position
        - _log_trade_action_sl_update
        - _actualizar_estados_indicadores

## Coordinacion de senales y filtros

`check_buy_signal()` coordina las condiciones de entrada del motor:

- las senales tecnicas habilitadas aportan vias de entrada con logica OR;
- los filtros globales activos se aplican como condiciones AND y pueden bloquear la entrada;
- cuando no hay senales tecnicas activas, puede actuar la entrada de fallback B&H si la EMA lenta cumple las condiciones previstas por el motor;
- los filtros globales activos siguen aplicando tambien sobre esa entrada de fallback.

## Trazabilidad con `technical_reasons`

El motor recopila motivos tecnicos asociados a las decisiones de trading para facilitar la trazabilidad de cada operacion.

Cuando varias condiciones participan en una entrada o salida, los motivos disponibles se consolidan para su registro junto con la operacion. Estos datos ayudan a revisar posteriormente que indicadores o filtros intervinieron y con que valores de mercado.

La trazabilidad registrada describe la decision operativa disponible en ese momento; no debe interpretarse como una reconstruccion historica completa de todos los estados internos previos.

## Flujo de decision

1. Se actualizan los estados dinamicos de los indicadores para la vela actual.
2. Si no hay posicion abierta, se evaluan senales tecnicas y filtros globales mediante `check_buy_signal()`.
3. Si existe una posicion abierta, `manage_existing_position()` evalua cierres tecnicos y las protecciones de riesgo aplicables.
4. La gestion del stop puede combinar stop base/trailing, break-even, swing stop y trailing por RSI cuando estan configurados.
5. El stop efectivo conserva el nivel mas protector y no retrocede una vez endurecido.

## Referencias

- Arquitectura canonica: `docs/ARCHITECTURE.md`
- Indicadores: `docs/api/motor_indicators.md`
- Utilidades: `docs/api/motor_utils.md`
