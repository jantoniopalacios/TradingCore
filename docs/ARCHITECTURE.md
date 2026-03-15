# Arquitectura de TradingCore

Documento canónico de arquitectura funcional y técnica de la aplicación.

## 1. Visión General

TradingCore está organizado en tres capas:

1. `trading_engine/`: motor de trading reutilizable (lógica técnica, ejecución de backtests, utilidades).
2. `scenarios/BacktestWeb/`: escenario web Flask que orquesta configuración, ejecución y persistencia.
3. PostgreSQL: almacenamiento de configuración de usuario, resultados y detalle de trades.

La comunicación es directa por importaciones Python y por base de datos. No se usa cola de mensajes.

## 2. Módulos Principales y Función

### 2.1 Motor (`trading_engine/`)

`trading_engine/core/Logica_Trading.py`
- Coordina la lógica de entrada/salida.
- `check_buy_signal(strategy_self)`: aplica señales OR, filtros AND y ejecuta compra.
- `manage_existing_position(strategy_self)`: gestiona cierre técnico y trailing stop.

`trading_engine/core/Backtest_Runner.py`
- Ejecuta backtest por símbolo y multi-símbolo sobre `backtesting.py`.
- `run_backtest_for_symbol(...)`: corre una estrategia para un ticker.
- `run_multi_symbol_backtest(...)`: consolida métricas, trades y objetos de backtest.

`trading_engine/indicators/`
- Implementación por indicador/filtro: EMA, RSI, MACD, Stochastic, Bollinger, ATR, MoS, Volume.
- Patrón funcional usado por el motor:
  - `update_*_state(...)`
  - `check_*_buy_signal(...)`
  - `check_*_sell_signal(...)`
  - `apply_*_filter(...)` (cuando aplica)

`trading_engine/utils/`
- Descarga de datos (`Data_download.py`), cálculo de ratios/fundamentales (`Calculos_Financieros.py`), correo (`utils_mail.py`) y utilidades técnicas.

### 2.2 Escenario web (`scenarios/BacktestWeb/`)

`scenarios/BacktestWeb/app.py`
- Factory Flask (`create_app`), configuración de DB y logging.

`scenarios/BacktestWeb/routes/main_bp.py`
- Endpoints web de configuración, lanzamiento de backtest, consulta de resultados y logs.
- `launch_strategy()` lanza ejecución asíncrona en hilo.
- `backtest_status()` devuelve estado en vivo de la ejecución para la UI (fase, mensaje, eventos, estado final).

`scenarios/BacktestWeb/Backtest.py`
- `ejecutar_backtest(config_dict, progress_callback=None)`: orquestador operativo con reporte de progreso por fases.
- Carga configuración, obtiene símbolos, descarga datos, ejecuta motor, genera gráficos y persiste resultados.

`scenarios/BacktestWeb/estrategia_system.py`
- Clase `System(Strategy)` como adaptador entre `backtesting.py` y motor.
- `init()`: inicializa indicadores y estados.
- `next()`: delega en wrappers que llaman a `check_buy_signal` y `manage_existing_position`.

`scenarios/BacktestWeb/database.py`
- Modelos SQLAlchemy: `Usuario`, `ResultadoBacktest`, `Trade`, `Simbolo`.

`scenarios/BacktestWeb/DBStore.py`
- Persistencia transaccional de resultados y trades (`save_backtest_run`).

## 3. Flujo End-to-End

1. El usuario guarda parámetros en la web.
2. Se persiste configuración en `usuarios.config_actual` (JSON), excepto parámetros operativos no persistentes (por ejemplo `end_date`).
3. `launch_strategy()` prepara `config_web` y abre hilo de ejecución.
4. `launch_strategy()` inicializa estado de ejecución en memoria (run_id/tanda/status inicial).
5. La UI consulta `GET /backtest_status` en polling para mostrar progreso por fases en el modal de lanzamiento.
6. `ejecutar_backtest()` mezcla configuración guardada y enviada, y reporta hitos con callback.
5. Obtiene símbolos del usuario (`simbolos`).
6. Descarga datos de mercado (Yahoo Finance) y opcionalmente fundamentales/ratios.
7. Ejecuta `run_multi_symbol_backtest(...)` con `System`.
8. `System.next()` delega en `Logica_Trading` para decidir compra/venta por vela.
9. Se guardan métricas, trades y gráficos en BD/HTML y se exponen en la UI.
10. Al finalizar, se marca estado `completed` o `error`; el usuario confirma con `OK` y se recarga la vista para ver historial actualizado.

## 4. Patrón de Decisión de Señales

En cada vela:

1. `Logica_Trading` actualiza estados dinámicos de indicadores (`*_STATE`).
2. Evalúa señales de entrada con lógica OR (EMA/RSI/MACD/Stoch/BB).
3. Aplica filtros globales con lógica AND (EMA global, RSI fuerza, ATR, volumen, MoS).
4. Si cumple, ejecuta compra y registra trazabilidad (`technical_reasons`).
5. Si hay posición, evalúa cierres técnicos OR y luego trailing/stop.

## 5. Modelo de Datos (PostgreSQL)

`usuarios`
- Credenciales y `config_actual` JSON.
- `config_actual` guarda la configuración funcional por usuario y omite campos operativos temporales (como `end_date`).

`simbolos`
- Universo de activos por usuario.

`resultados_backtest`
- Métricas agregadas por símbolo y tanda.

`trades`
- Registro detallado de operaciones (entrada/salida/PnL).

## 6. Reglas de Extensión

Para añadir un nuevo indicador o filtro:

1. Crear módulo en `trading_engine/indicators/` con funciones de estado/senal/filtro.
2. Inicializar sus series y atributos en `scenarios/BacktestWeb/estrategia_system.py` (`init`).
3. Integrarlo en `trading_engine/core/Logica_Trading.py` en compra/venta/filtros.
4. Exponer parámetros en formulario web y persistencia (`main_bp.py`, `config_actual`).
5. Verificar trazabilidad en `trades` y estabilidad del flujo de backtest.

## 7. Principios de Diseño

- El motor central concentra la lógica de decisión.
- El escenario web orquesta, no duplica reglas de trading.
- La trazabilidad de decisiones es parte del diseño (logs y razones técnicas).
- La configuración funcional se trata como dato persistente por usuario.
- Parámetros operativos de ejecución puntual pueden ser no persistentes (ejemplo: `end_date` con valor por defecto dinámico `ayer`).