# Arquitectura de TradingCore

Documento canónico de arquitectura funcional y técnica de la aplicación.

Última actualización: 29/09/2026

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
- `manage_existing_position(strategy_self)`: gestiona cierres técnicos por indicador y, si no aplica ninguno, el stop dinámico (stop base, break-even, swing stop y trailing por RSI cuando está configurado).

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

`trading_engine/fundamentals/`
- Capa normalizada de fundamentales, acumulativa por símbolo e integrada con el backtest web mediante un adaptador de compatibilidad.
- `FundamentalRecord` conserva `symbol`, `fiscal_date`, `reported_date`, `metric`, `value`, `provider`, `source_type` y `updated_at`.
- `FundamentalStore` fusiona registros por símbolo sin eliminar la procedencia; `fiscal_date` identifica el trimestre y `reported_date` indica desde cuándo podía conocerse el dato.
- `providers/yahoo.py` y `updater.py` mantienen la actualización operativa de los datos recientes.
- `providers/alpha_vantage.py` y `bootstrap.py` construyen el histórico inicial consultando el endpoint EARNINGS una vez por símbolo. El bootstrap persiste su estado en `<fundamentals_path>/bootstrap_state.json`.
- `FundamentalService` coordina actualización Yahoo y bootstrap, y devuelve cobertura/estado por símbolo.
- `legacy_adapter.py` convierte EPS normalizado al DataFrame legacy-compatible que consume Full Ratio.

Almacenamiento fundamental:

- `Data_Files/Fundamentals/` es la caché normalizada: un CSV por símbolo exacto (por ejemplo, `AAPL.csv`) con columnas `symbol`, `fiscal_date`, `reported_date`, `metric`, `value`, `provider`, `source_type` y `updated_at`; también guarda `bootstrap_state.json`. No debe contener archivos `Q*`.
- `Data_Files/Fundamentals_Legacy/` contiene exclusivamente la caché de compatibilidad/fallback (`Q0_*`, `Q1_*`, etc.). No pertenece al modelo normalizado.

### 2.2 Escenario web (`scenarios/BacktestWeb/`)

`scenarios/BacktestWeb/app.py`
- Factory Flask (`create_app`), configuración de DB y logging.

`scenarios/BacktestWeb/routes/main_bp.py`
- Endpoints web de configuración, lanzamiento de backtest, consulta de resultados y logs.
- `launch_strategy()` lanza ejecución asíncrona en hilo.
- `backtest_status()` devuelve estado en vivo de la ejecución para la UI (fase, mensaje, eventos, estado final).
- El guardado de configuración soporta modo AJAX para persistir sin redirección completa.

`scenarios/BacktestWeb/routes/backtest_status.py`
- Estado en memoria de ejecuciones de backtest por usuario (`queued`, `running`, `completed`, `error`).

`scenarios/BacktestWeb/routes/config_helpers.py`
- Helpers de construcción y normalización de parámetros de configuración desde el formulario web.

`scenarios/BacktestWeb/routes/graph_cache.py`
- Gestión de caché de artefactos de gráficos (snapshots HTML) y limpieza de expirados.

`scenarios/BacktestWeb/routes/graph_render.py`
- Renderizado del gráfico nativo del motor y fallback desde snapshot cuando no está disponible.

`scenarios/BacktestWeb/routes/scheduler_helpers.py`
- Lectura de estado y validación de PID del scheduler.

`scenarios/BacktestWeb/file_handler.py`
- Lectura/escritura de configuración `.env`, generación del árbol del explorador de ficheros (`get_directory_tree`) y control de acceso a documentación por rol (`is_docs_path_allowed`).

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

## 3. Fases de ejecución (orquestador)

`ejecutar_backtest()` reporta el progreso en 11 fases mediante `progress_callback`:

```
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
```

## 4. Contratos entre módulos

Contrato de decisión en cada vela:

1. `System.next()`
2. Si hay posición: `manage_existing_position(self)`
3. Si no hay posición: `check_buy_signal(self)`

Contrato de indicadores:

- `update_*_state()` actualiza flags `*_STATE`.
- `check_*_buy_signal()` y `check_*_sell_signal()` retornan señal + motivo.
- `apply_*_filter()` aplica veto/permiso global cuando corresponde.

Contrato de la capa HTTP (`main_bp.py`):

- Expone `GET /backtest_status` para polling de progreso desde la UI.
- Gestiona estado de ejecución en memoria por usuario (`queued`, `running`, `completed`, `error`).
- En guardado de configuración, devuelve JSON cuando el request es AJAX (`X-Requested-With: XMLHttpRequest`).
- El visor web de ficheros restringe lectura a rutas controladas (`logs/`, `docs/`) y evita path traversal fuera de esas raíces.
- `logs/` solo es accesible para el rol admin.
- `docs/` se filtra por rol: el árbol mostrado y la apertura de ficheros usan la misma regla de autorización.
  - Usuario normal: solo puede ver/abrir la documentación funcional permitida.
  - Admin: puede ver/abrir todo `docs/`.
  - La autorización se valida también en backend (`view_file`), no solo ocultando elementos en el árbol de la UI.

## 5. Flujo End-to-End

1. El usuario guarda parámetros en la web.
2. Se persiste configuración en `usuarios.config_actual` (JSON), excepto parámetros operativos no persistentes (por ejemplo `end_date`).
3. `launch_strategy()` prepara `config_web` y abre hilo de ejecución.
4. `launch_strategy()` inicializa estado de ejecución en memoria (run_id/tanda/status inicial).
5. La UI consulta `GET /backtest_status` en polling para mostrar progreso por fases en el modal de lanzamiento.
6. `ejecutar_backtest()` mezcla configuración guardada y enviada, y reporta hitos con callback.
7. Obtiene símbolos del usuario (`simbolos`).
8. Descarga datos de mercado y, si `filtro_fundamental` está activo, envía exactamente los símbolos configurados a la actualización fundamental.
9. La capa normalizada intenta actualizar Yahoo y solicita bootstrap Alpha Vantage solo si existe `ALPHA_VANTAGE_KEY`. Se usa la caché normalizada para los símbolos cubiertos; `manage_fundamental_data(...)` atiende únicamente los símbolos faltantes en `Fundamentals_Legacy/`.
10. Full Ratio calcula y propaga los valores trimestrales desde `reportedDate`; después se aplica la selección fundamental y continúa el backtest.
11. Ejecuta `run_multi_symbol_backtest(...)` con `System`.
12. `System.next()` delega en `Logica_Trading` para decidir compra/venta por vela.
13. Se guardan métricas, trades y gráficos en BD/HTML y se exponen en la UI.
14. Al finalizar, se marca estado `completed` o `error`; el usuario confirma con `OK` y se recarga la vista para ver historial actualizado.

### Fundamentales: actualización, estado y fallback

El flujo mantiene el modelo normalizado como fuente principal y un fallback legacy aislado:

```text
símbolos configurados
  -> Yahoo / FundamentalUpdater
  -> Alpha Vantage / bootstrap histórico cuando procede
  -> FundamentalStore (Data_Files/Fundamentals/, CSV normalizado por símbolo)
  -> legacy_adapter.py y EPS utilizable por símbolo
  -> fallback legacy solo para símbolos faltantes (Data_Files/Fundamentals_Legacy/)
  -> combinación en memoria; ante duplicados símbolo/periodo, prevalece normalizado
  -> Full Ratio y selección fundamental
```

La lista de entrada es exactamente el universo configurado; no se añaden activos. Yahoo mantiene la actualización operativa. Alpha Vantage construye histórico mediante el endpoint EARNINGS, con una llamada por símbolo y clave leída de `ALPHA_VANTAGE_KEY`; si falta la variable, no se solicita bootstrap, Yahoo continúa y la ausencia de clave no es un error.

Yahoo obtiene `fiscal_date` del EPS trimestral y asocia `reported_date` con eventos de resultados posteriores mediante una heurística de ingestión con ventana máxima configurable (120 días por defecto). El origen queda reflejado en `source_type`; no se inventa la fecha de publicación a partir del cierre fiscal.

Los estados persistidos del bootstrap son `pending`, `in_progress`, `completed`, `partial`, `quota_blocked`, `no_data` y `error`: `pending` está pendiente de procesar; `in_progress` indica una petición en curso; `completed` requiere al menos 20 periodos EPS únicos; `partial` indica de 1 a 19; `quota_blocked` indica cuota AV agotada; `no_data` indica que no se obtuvo EPS utilizable; `error` indica un fallo de petición o procesamiento. `completed` y `no_data` se omiten en ejecuciones posteriores; `no_data` solo vuelve a intentarse tras un reset explícito. `partial`, `quota_blocked` y `error` son reintentables. Si se agota la cuota AV, se conserva lo ya almacenado, se persiste el estado y se detiene el resto del lote.

Entre 1 y 19 periodos el estado es `partial`; la cobertura por proveedor y símbolo se conserva para diagnóstico. `load_fundamental_data_with_fallback(...)` calcula los símbolos no cubiertos por EPS normalizado utilizable, consulta el mecanismo legacy solo para ese subconjunto y combina ambos resultados en memoria. Un símbolo ya cubierto no se vuelve a descargar por legacy. Ante un error al preparar el adaptador, no hay símbolos normalizados utilizables y se aplica el fallback al universo solicitado.

El dashboard `/fundamentals` y el detalle `/fundamentals/<symbol>` muestran exclusivamente símbolos configurados por el usuario y datos almacenados. Son vistas de solo lectura: no descargan proveedores ni recalculan ratios.

La columna **Cobertura** mide periodos EPS en la caché normalizada, no disponibilidad de valoración: 0 = `Sin datos`; 1–3 = `Cobertura insuficiente`; 4–19 = `Cobertura parcial`; 20 o más = `Cobertura suficiente`. LTM EPS, PER M5Y y disponibilidad de métricas Full Ratio se muestran por separado. LTM EPS requiere cuatro periodos válidos; PER M5Y requiere 20 PER trimestrales válidos. `No calculado` no implica necesariamente un error.

El resumen muestra registros, periodos EPS, primer y último periodo fiscal, último `reportedDate`, proveedores, cobertura, LTM EPS, PER M5Y, disponibilidad Full Ratio y bootstrap. El detalle muestra el histórico normalizado, el gráfico EPS con sus fechas de disponibilidad y métricas de valoración solo si ya están guardadas.

### Métricas y disponibilidad temporal

Para EPS diluido, el cálculo conserva la secuencia trimestral por `fiscalDateEnding`, pero el backtest solo dispone cada resultado desde `reportedDate`, inclusive. Una fecha de publicación ausente o inválida no se reemplaza por la fecha fiscal ni por un desplazamiento estimado.

- `LTM EPS`: suma móvil de cuatro trimestres completos; antes de cuatro, queda NaN.
- `LTM EPS %`: variación porcentual de LTM EPS, sin rellenar NaN de forma implícita.
- `PER`: precio dividido por LTM EPS; EPS no positivo invalida el PER.
- `PER M5Y`: media móvil de 20 observaciones trimestrales válidas de PER; antes de 20 queda NaN.
- `% PER vs PER M5Y`: `100 * (PER - PER_M5Y) / PER_M5Y`; si el baseline PER M5Y es inválido o `<= 0`, el resultado es NaN. Negativo indica PER inferior a su media y positivo, superior.
- `Margen de seguridad`: `LTM EPS % - % PER vs PER M5Y`. Es una métrica propia de TradingCore y no necesariamente el concepto clásico de margen de seguridad.
- `Full Ratio`: `Margen de seguridad / PER`.

En una única fecha global de mercado (no una fecha distinta por símbolo), la selección devuelve `Mantener (Atractivo)` solo cuando LTM EPS %, Margen de seguridad y Full Ratio son positivos (AND). Con métricas requeridas disponibles que no cumplen alguna condición devuelve `Desestimar (No cumple criterios)`; si falta una métrica requerida devuelve `No evaluable (Datos insuficientes)`. Desestimar y no evaluable son resultados distintos.

Notas de UX del formulario:

- Navegar entre sub-pestañas de `Configuracion` no persiste automáticamente en base de datos.
- `Guardar Config` es la acción explícita de persistencia de parámetros (ejecutada por AJAX, sin recarga de página).
- Los cambios no guardados permanecen en memoria del formulario mientras no exista recarga de página.

## 6. Patrón de Decisión de Señales

En cada vela:

1. `Logica_Trading` actualiza estados dinámicos de indicadores (`*_STATE`).
2. Evalúa señales de entrada con lógica OR (EMA/RSI/MACD/Stoch/BB).
3. Aplica filtros globales con lógica AND (EMA global, RSI fuerza, ATR, volumen, MoS).
4. Si cumple, ejecuta compra y registra trazabilidad (`technical_reasons`).
5. Si hay posición, evalúa cierres técnicos OR y luego trailing/stop.

## 7. Modelo de Datos (PostgreSQL)

`usuarios`
- Credenciales y `config_actual` JSON.
- `config_actual` guarda la configuración funcional por usuario y omite campos operativos temporales (como `end_date`).

`simbolos`
- Universo de activos por usuario.

`resultados_backtest`
- Métricas agregadas por símbolo y tanda.

`trades`
- Registro detallado de operaciones (entrada/salida/PnL).

## 8. Persistencia y trazabilidad

- `end_date`: parámetro operativo no persistente en `config_actual`; se define por defecto como `ayer` y puede sobreescribirse por ejecución.
- Logging estructurado del ciclo completo en `logs/`.
- El estado persistente del bootstrap fundamental se guarda en `<fundamentals_path>/bootstrap_state.json`, separado de los CSV normalizados por símbolo.
- Motivos técnicos consolidados en los registros de trade (`technical_reasons`).
- Estado operativo visible en la UI durante la ejecución (fase actual, mensaje y eventos recientes).
- Estado de pestañas (`activeTabKey` y `activeSubTabKey`) persistido en `localStorage` para mantener contexto visual entre recargas.
- El estado/PID del scheduler en `logs/` (`backtest_scheduler_status.json`, `backtest_scheduler.pid`) es distinto de su log persistente, guardado en `Backtesting/logs/backtest_scheduler.log`.

## 9. Reglas de Extensión

Para añadir un nuevo indicador o filtro:

1. Crear módulo en `trading_engine/indicators/` con funciones de estado/senal/filtro.
2. Inicializar sus series y atributos en `scenarios/BacktestWeb/estrategia_system.py` (`init`).
3. Integrarlo en `trading_engine/core/Logica_Trading.py` en compra/venta/filtros.
4. Exponer parámetros en formulario web y persistencia (`main_bp.py`, `config_actual`).
5. Verificar trazabilidad en `trades` y estabilidad del flujo de backtest.

## 10. Principios de Diseño

- El motor central concentra la lógica de decisión.
- El escenario web orquesta, no duplica reglas de trading.
- La trazabilidad de decisiones es parte del diseño (logs y razones técnicas).
- La configuración funcional se trata como dato persistente por usuario.
- Parámetros operativos de ejecución puntual pueden ser no persistentes (ejemplo: `end_date` con valor por defecto dinámico `ayer`).
