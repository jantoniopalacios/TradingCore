# Flujo de Arquitectura del Backtest Web

Este documento describe el flujo operativo actual de `scenarios/BacktestWeb` y su comunicación con `trading_engine`.

## 1. Flujo de ejecución

```text
Usuario (UI Flask)
  -> POST /launch_strategy
  -> main_bp.launch_strategy()
  -> crea config_web + metadatos (user_id, tanda_id)
  -> lanza hilo run_backtest_and_save(...)

Hilo de ejecución
  -> Backtest.ejecutar_backtest(config_web)
     [1/9] Cargar configuración base de usuario
     [2/9] Sincronizar atributos de System
     [3/9] Cargar símbolos del usuario desde PostgreSQL
     [4/9] Descargar OHLCV (Yahoo Finance)
     [5/9] Procesar fundamentales (opcional)
     [6/9] Calcular ratios OHLCV (opcional)
     [7/9] Aplicar filtro fundamental (opcional)
     [8/9] Ejecutar run_multi_symbol_backtest(...)
     [9/9] Generar gráficos HTML por símbolo
  -> Persistir resultados/trades con save_backtest_run(...)
  -> db.session.remove()
```

## 2. Comunicación entre módulos

`main_bp.py`
- Capa HTTP y sesión de usuario.
- Normaliza formulario y construye `config_web`.
- Aplica política de fecha operativa: `end_date` por defecto a `ayer` y no persistente en `config_actual`.

`Backtest.py`
- Orquestador de proceso.
- Adapta datos para el motor y controla errores/logs.

`estrategia_system.py`
- Adaptador `System(Strategy)`.
- Expone atributos de configuración y estados para lógica técnica.

`Logica_Trading.py`
- Coordinador de señales y gestión de posición.
- Delega en módulos de `trading_engine/indicators/`.

`Backtest_Runner.py`
- Ejecuta motor por símbolo y agrega resultados multi-símbolo.

`database.py` + `DBStore.py`
- Persistencia de `ResultadoBacktest` y `Trade`.

## 3. Contratos clave

Contrato de decisión en cada vela:

1. `System.next()`
2. Si hay posición: `manage_existing_position(self)`
3. Si no hay posición: `check_buy_signal(self)`

Contrato de indicadores:

- `update_*_state()` actualiza flags `*_STATE`.
- `check_*_buy_signal()` y `check_*_sell_signal()` retornan señal + motivo.
- `apply_*_filter()` aplica veto/permiso global cuando corresponde.

## 4. Persistencia y trazabilidad

Persistencia principal:

- `usuarios.config_actual`: configuración viva por usuario.
- `end_date`: parámetro operativo no persistente en `config_actual`; se define por defecto como `ayer` en UI/backend y puede sobreescribirse por ejecución.
- `simbolos`: universo de activos.
- `resultados_backtest`: métricas por símbolo/tanda.
- `trades`: detalle de operaciones.

Trazabilidad:

- Logging estructurado del ciclo completo.
- Motivos técnicos consolidados en los registros de trade.
