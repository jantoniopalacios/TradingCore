# Flujo de Arquitectura del Backtest Web

Este documento describe el flujo operativo actual de `scenarios/BacktestWeb` y su comunicación con `trading_engine`.

## 1. Flujo de ejecución

```text
Usuario (UI Flask)
  -> POST /launch_strategy
  -> main_bp.launch_strategy()
  -> crea config_web + metadatos (user_id, tanda_id, run_id)
  -> inicializa estado en memoria (queued/running)
  -> lanza hilo run_backtest_and_save(...)
  -> abre modal de progreso en UI

UI (polling)
  -> GET /backtest_status (cada ~1.5s)
  -> renderiza fase actual + barra + eventos
  -> habilita boton OK cuando status=completed/error

UI (configuracion)
  -> cambio de sub-pestaña instantaneo (sin transicion `fade` en sub-panes)
  -> no hay guardado automatico al navegar entre sub-pestañas
  -> `Guardar Config` usa POST AJAX para persistir sin recarga completa

UI (explorador de ficheros, solo admin)
  -> muestra arbol combinado de `logs` y `docs`
  -> permite abrir/descargar archivos de ambas rutas
  -> borrado habilitado solo para archivos de `logs`

Hilo de ejecución
  -> Backtest.ejecutar_backtest(config_web, progress_callback)
     [1/11] Configuracion
     [2/11] System
     [3/11] Base de datos
     [4/11] Datos de mercado
     [5/11] Fundamentales (opcional)
     [6/11] Filtros
     [7/11] Motor
     [8/11] Graficos
     [9/11] Persistencia SQL
     [10/11] Cierre
     [11/11] Notificacion
  -> actualiza estado en memoria por cada fase
  -> Persistir resultados/trades con save_backtest_run(...)
  -> marcar estado final completed/error
  -> db.session.remove()
```

## 2. Comunicación entre módulos

`main_bp.py`
- Capa HTTP y sesión de usuario.
- Normaliza formulario y construye `config_web`.
- Aplica política de fecha operativa: `end_date` por defecto a `ayer` y no persistente en `config_actual`.
- Expone `GET /backtest_status` para seguimiento de ejecución en tiempo real desde la UI.
- Gestiona estado de ejecución en memoria por usuario (`queued`, `running`, `completed`, `error`).
- En guardado de configuración, devuelve JSON cuando el request es AJAX (`X-Requested-With: XMLHttpRequest`).
- En el visor web de archivos, restringe lectura a raíces controladas (`logs`, `docs`) y evita traversal fuera de esas rutas.

`Backtest.py`
- Orquestador de proceso.
- Adapta datos para el motor y controla errores/logs.
- Publica hitos de progreso de cada fase mediante callback opcional (`progress_callback`).

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
- Estado operativo visible en la UI durante la ejecución (fase actual, mensaje y eventos recientes).
- Estado de pestañas (`activeTabKey` y `activeSubTabKey`) persistido en `localStorage` para mantener contexto visual.
