# TradingCore: Motor Central y Arquitectura Modular

Última actualización: 29/09/2026

Este repositorio contiene la arquitectura central (Motor) para múltiples escenarios de trading (Backtesting, Live Trading, Web Apps).

---

## Inicio Rápido (Backtest Web)

Para ejecutar la aplicación web de backtesting desde la raíz del repo:

1. **Activar entorno virtual:**

   ```bash
   .\.venv\Scripts\activate
   ```

2. **Instalar dependencias (si aplica):**

   ```bash
   pip install -r requirements.txt
   ```

3. **Iniciar PostgreSQL embebido:**

   ```bat
   pg_start.bat
   ```

4. **Iniciar servidor Flask:**

   ```bash
   python scenarios/BacktestWeb/app.py
   ```

5. **Abrir la aplicación:**

   ```text
   http://localhost:5000
   ```

---

## Estructura del Repositorio

Las leyendas indican la criticidad de cada componente:

- 🔴 **Crítico** — imprescindible para el funcionamiento del sistema
- 🟡 **Importante** — soporte operacional, datos o infraestructura
- 🟢 **Auxiliar** — utilidades, experimentos, documentación

---

### 🔴 Motor de Trading (`trading_engine/`)

Núcleo reutilizable con toda la lógica de negocio. No tiene dependencia de ningún escenario concreto.

```text
trading_engine/
├── core/                         🔴 Núcleo de ejecución
│   ├── Logica_Trading.py             Gestión de señales de entrada/salida, stops y trailing
│   ├── Backtest_Runner.py            Orquestador del ciclo de backtesting
│   ├── database_pg.py                Configuración y acceso compartido a PostgreSQL
│   └── constants.py                  Constantes globales del motor
├── fundamentals/                 🔴 Datos fundamentales normalizados
│   ├── models.py                      Modelo normalizado de observación fundamental
│   ├── store.py                       Almacenamiento acumulativo por símbolo
│   ├── providers/                     Yahoo reciente y Alpha Vantage histórico
│   ├── updater.py                      Actualización Yahoo
│   ├── bootstrap.py                    Histórico y estado persistente
│   ├── service.py                      Orquestación por símbolo
│   └── legacy_adapter.py               Conversión temporal al formato EPS anterior
├── indicators/                   🔴 Filtros técnicos
│   ├── Filtro_EMA.py                 Cruce de medias / precio vs EMA
│   ├── Filtro_RSI.py                 Relative Strength Index
│   ├── Filtro_MACD.py                MACD y señal
│   ├── Filtro_ATR.py                 Average True Range
│   ├── Filtro_BollingerBands.py      Bandas de Bollinger
│   ├── Filtro_Stochastic.py          Oscilador Estocástico
│   ├── Filtro_MoS.py                 Margin of Safety
│   └── Filtro_Volume.py              Filtro de volumen relativo
└── utils/                        🔴 Utilidades compartidas
    ├── Calculos_Financieros.py       Cálculos y ratios financieros
    ├── Calculos_Tecnicos.py          Cálculos técnicos sobre series y DataFrames
    ├── Data_download.py              Descarga y gestión de datos de mercado y fundamentales
    ├── Graficos_financieros.py       Generación de gráficos Bokeh interactivos
    ├── Historico_manager.py          Lectura y cacheo de históricos
    ├── setup.py                      Configuración de entorno del motor
    ├── utils_mail.py                 Envío de alertas por correo electrónico
    └── Config/
        └── setup_mail.env             Configuración local de correo (no versionar credenciales)
```

---

### 🔴 Aplicación Web BacktestWeb (`scenarios/BacktestWeb/`)

Aplicación Flask que expone el motor de trading como interfaz web multiusuario.

```text
scenarios/BacktestWeb/
├── app.py                       🔴 Punto de entrada Flask
├── Backtest.py                  🔴 Orquestación de backtests y persistencia
├── estrategia_system.py         🔴 Sistema de parámetros de estrategia
├── configuracion.py             🟡 Carga y validación de configuración
├── database.py                  🟡 Modelos SQLAlchemy de la aplicación
├── DBStore.py                   🟡 Persistencia de resultados y snapshots
├── file_handler.py              🟡  Gestión de ficheros y control de acceso a docs
├── routes/
│   ├── main_bp.py               🔴 Blueprint principal
│   ├── backtest_status.py       🟡 Estado en memoria de ejecuciones de backtest
│   ├── config_helpers.py        🟡 Helpers de configuración
│   ├── graph_cache.py           🟡 Caché de artefactos de gráficos
│   ├── graph_data.py            🟡 Carga y ejecución para gráficos
│   ├── graph_render.py          🟡 Renderizado y fallback de gráficos
│   └── scheduler_helpers.py     🟡 Estado y PID del scheduler
└── templates/                   🔴 Plantillas HTML Jinja2
    ├── index.html                   Layout principal
    ├── login.html                   Pantalla de autenticación
    ├── cargando.html                Página de espera durante ejecución
    ├── _tab_global.html             Parámetros globales
    ├── _tab_ema.html                Parámetros EMA
    ├── _tab_rsi.html                Parámetros RSI
    ├── _tab_macd.html               Parámetros MACD
    ├── _tab_atr.html                Parámetros ATR / stops
    ├── _tab_bb.html                 Parámetros Bollinger Bands
    ├── _tab_stoch.html              Parámetros Estocástico
    ├── _tab_mos_volume.html         Parámetros MoS y Volumen
    ├── _tab_symbols.html            Símbolos y temporalidad
    ├── _tab_historial.html          Historial de resultados
    ├── _tab_charts_viewer.html      Visor de gráficos
    ├── _tab_scheduler.html          Programación automática
    ├── _tab_ficheros.html           Gestión de ficheros
    └── _tab_user_management.html    Administración de usuarios
```

---

### 🟡 Datos históricos (`Data_Files/`)

Ficheros CSV con datos OHLCV descargados principalmente mediante Yahoo Finance, organizados por símbolo y temporalidad.

```text
Data_Files/
├── SYMBOL_1d_MAX.csv          Datos diarios
├── SYMBOL_1wk_MAX.csv         Datos semanales
├── SYMBOL_1h_MAX.csv          Datos horarios para los símbolos disponibles
├── SYMBOL_1mo_MAX.csv         Datos mensuales para los símbolos disponibles
├── Backtest_config/           Configuraciones locales de backtest
├── Fundamentals/              Caché normalizada y estado de bootstrap
└── Fundamentals_Legacy/       Caché Q separada para fallback compatible
```

La caché normalizada guarda un CSV acumulativo por símbolo exacto (por ejemplo, `AAPL.csv`) con el esquema `symbol, fiscal_date, reported_date, metric, value, provider, source_type, updated_at`, además de `bootstrap_state.json`. `Fundamentals_Legacy/` contiene exclusivamente ficheros Q (`Q0_*`, `Q1_*`, etc.) para compatibilidad; no forma parte del modelo normalizado.

---

### 🟡 Base de datos PostgreSQL embebida (`data_pg/` + `pgsql/`)

```text
data_pg/                       🟡 Directorio de datos de PostgreSQL
pgsql/                         🟡 Binarios del servidor PostgreSQL portable
pg_start.bat                   🟡 Arranque del servidor PostgreSQL
pg_stop.bat                    🟡 Parada del servidor PostgreSQL
```

La BD PostgreSQL almacena usuarios, estrategias, resultados de backtests, trades, configuraciones y snapshots necesarios para la aplicación web.

---

### 🟡 Resultados y artefactos de backtesting (`Backtesting/`)

Directorio de salida y de artefactos generados por las ejecuciones.

```text
Backtesting/
├── Graphics/                  🟡 Caché de gráficos HTML por usuario
├── Run_Results/               🟡 Resultados CSV de ejecuciones históricas
├── diagnostics/                🟢 Salidas generadas de análisis y comparación
└── logs/                      🟡 Logs persistentes de la aplicación y backtesting
```

`Backtesting/diagnostics/` contiene artefactos de diagnóstico; no es una caché productiva ni una fuente de datos para el motor.

El log persistente específico del scheduler se guarda en:

```text
Backtesting/logs/backtest_scheduler.log
```

---

### 🟡 Logs y estado operativo (`logs/`)

El directorio raíz `logs/` contiene principalmente información de estado necesaria para controlar procesos de la aplicación.

```text
logs/
├── backtest_scheduler_status.json   Estado actual del scheduler
├── backtest_scheduler.pid           PID del scheduler en ejecución
├── server_local.log                 Log local del servidor, cuando se utiliza
└── batch_*.log                      Logs de ejecuciones batch, cuando se generan
```

El fichero PID puede quedar temporalmente huérfano si el proceso es finalizado de forma forzada. La aplicación comprueba que el PID corresponda realmente al scheduler y elimina automáticamente los PID inválidos detectados.

---

### 🟡 Scripts operativos y auxiliares (`scripts/`)

Los scripts auxiliares se agrupan por finalidad. No forman parte del núcleo del motor de trading, aunque algunos tienen funciones operativas de apoyo a la aplicación.

```text
scripts/
├── analysis/                    Análisis de resultados de backtests
├── diagnostics/                 Diagnóstico manual; incluye comparación de proveedores fundamentales
├── experiments/                 Experimentos de estrategias e indicadores
├── maintenance/                 Administración y mantenimiento
├── presets/                     Configuraciones predefinidas
├── scheduler/                   Scheduler de backtests periódicos
│   └── backtest_scheduler.py
├── optimize_rsi.py              Barrido de parámetros RSI
├── sweep_rsi_filter.py          Optimización por grilla del filtro RSI
├── audit_stops_combinations.py  Auditoría de combinaciones de stops
├── batch_replay_by_ids.py       Re-ejecución batch por ID
├── query_backtest_results.py    Consulta y exportación de resultados
└── verificar_backtest_web.py    Verificación de integridad de la app web
```

`scripts/diagnostics/compare_fundamental_providers.py` compara cobertura de EPS y fechas de publicación de Yahoo, Alpha Vantage y, opcionalmente, la caché CSV. Es una herramienta manual de diagnóstico, no forma parte del flujo normal del backtest. Puede escribir sus resultados bajo `Backtesting/diagnostics/`.

El scheduler utiliza APScheduler y mantiene su estado mediante los ficheros de `logs/`. Su log persistente se almacena en `Backtesting/logs/backtest_scheduler.log`.

---

### 🟢 Tests automatizados (`tests/`)

Los tests se mantienen separados de los scripts auxiliares:

```text
tests/
├── unit/                       Pruebas unitarias del motor y señales técnicas
├── integration/                Pruebas de integración y persistencia
└── web/                        Pruebas de rutas y comportamiento web
```

La batería incluye pruebas offline para store, Yahoo, updater, proveedor Alpha Vantage, bootstrap, servicio, integración del backtest, adaptador legado, alineación por `reportedDate`, profundidad histórica, desviación PER, margen de seguridad, Full Ratio, selección fundamental e histórico insuficiente.

`pytest.ini` limita la colección a `tests/`, por lo que no se recogen suites internas de pgAdmin ni de otros componentes externos.

La verificación habitual del proyecto puede ejecutarse mediante:

```powershell
.\scripts\verify.ps1
```

Este script ejecuta cuatro pasos: sintaxis Python, tests base, estado del servidor web y estado de Git. En el paso `[3/4] Web server state` muestra PID, proceso y línea de comandos del listener del puerto 5000 y confirma si corresponde a TradingCore Web.

---

### 🟡 Datos Fundamentales y compatibilidad legado

La capa activa de negocio es `trading_engine/fundamentals/`, implementada en `models.py`, `store.py`, `providers/yahoo.py`, `providers/alpha_vantage.py`, `updater.py`, `bootstrap.py`, `service.py` y `legacy_adapter.py`. El flujo productivo es:

```text
símbolos configurados, sin ampliar el universo
  -> Yahoo para fundamentales recientes
  -> bootstrap histórico Alpha Vantage cuando corresponde
  -> caché normalizada acumulativa por símbolo
   -> EPS normalizado para símbolos cubiertos, adaptado al formato requerido por Full Ratio
   -> fallback Q únicamente para símbolos sin cobertura normalizada utilizable
   -> Fundamentals_Legacy/ y combinación en memoria (normalizado prevalece en duplicados)
```

Yahoo mantiene la actualización operativa. Alpha Vantage construye histórico con el endpoint EARNINGS, una llamada por símbolo, y no se repite para símbolos `completed`. La clave se obtiene de `ALPHA_VANTAGE_KEY`; sin ella Yahoo continúa y no se solicita bootstrap, sin que esa ausencia sea un error. `partial`, `quota_blocked` y `error` son reintentables; `no_data` es terminal hasta reset explícito. Al agotarse cuota se detiene el lote y se persiste estado.

Cada CSV normalizado conserva `symbol`, `fiscal_date`, `reported_date`, `metric`, `value`, `provider`, `source_type` y `updated_at`. `fiscal_date` identifica el periodo fiscal; `reported_date` es la fecha de publicación y determina desde cuándo el dato está disponible, evitando look-ahead. El dashboard `/fundamentals` y el detalle `/fundamentals/<symbol>` muestran solo símbolos configurados y son de solo lectura.

La cobertura EPS del dashboard es independiente de las métricas de valoración: 0 periodos = sin datos; 1–3 = insuficiente; 4–19 = parcial; 20 o más = suficiente. LTM EPS requiere 4 periodos válidos y PER M5Y, 20 PER trimestrales válidos. Fórmulas, estados de bootstrap, selección e integración están descritos en [ARCHITECTURE.md](ARCHITECTURE.md).

El directorio `scenarios/Fundamental_Data/` conserva utilidades standalone y de mantenimiento; no es el flujo productivo del backtest web.

```text
scenarios/Fundamental_Data/
├── manager.py               Utilidades standalone de actualización y migración
├── Fundamental_Manager.py   Utilidades auxiliares de sincronización
└── database.py              Persistencia para estas utilidades
```

El flujo normalizado, bootstrap, actualización Yahoo, anti-look-ahead, integración del backtest, fallback parcial separado, dashboard y ayudas contextuales están implementados. La retirada de `manage_fundamental_data()` y `download_fundamentals_AlphaV()` sigue pendiente hasta que Full Ratio consuma directamente el nuevo formato y se cierre la compatibilidad.

---

### 🟢 Laboratorio (`Laboratorio/`)

Espacio de experimentación y prototipos. Código no productivo.

```text
Laboratorio/
└── test_yfinance_symbols.py     Experimentos con la API de yfinance
```

---

### 🟢 Documentación (`docs/`)

```text
docs/
├── README.md                                              Este fichero técnico
├── ARCHITECTURE.md                                        Arquitectura canónica del sistema
├── Manual_operativo_TradingCore_PowerShell_Git_Copilot.md  Manual operativo del administrador
├── User/                                                  Documentación de usuario final
│   └── MANUAL_USUARIO_TRADINGCORE.md                     Manual completo de la interfaz web
├── api/                                                   Documentación de la API interna (MkDocs)
├── Guides/                                                Guías funcionales y técnicas de referencia
├── Plans/                                                 Planificación viva y hojas de ruta
└── Index/                                                 Índice general y convenciones de documentación
```

El acceso a `docs/` desde el explorador web está filtrado por rol:

- **Usuario normal:** solo puede ver `docs/User/MANUAL_USUARIO_TRADINGCORE.md` y las ayudas contextuales integradas en la interfaz.
- **Admin:** puede ver y abrir toda la documentación válida situada bajo `docs/`.
- La autorización se valida en backend mediante `scenarios/BacktestWeb/file_handler.py`; no depende únicamente de ocultar elementos en la interfaz.

La auditoría de contratos UI -> configuración -> motor de los indicadores principales se completó el 20/09/2026. MACD, Stochastic, compra Bollinger, MoS y Volumen disponen de correcciones y tests de regresión específicos.

### Ayuda contextual en configuración

Las pestañas de configuración incorporan ayuda contextual mediante el botón **Ayuda**. Está disponible en Global, EMA, RSI, MACD, ATR, Estocástico, Bollinger y Volumen/MoS. Las ayudas describen el uso real de TradingCore, parámetros, condiciones de compra y venta/bloqueo, relación con otros filtros, ejemplos y advertencias de comportamiento actual.

---

### 🟢 Ficheros raíz relevantes

| Fichero | Descripción |
| :--- | :--- |
| `requirements.txt` | Dependencias Python del proyecto |
| `run_backtest_scheduler.bat` | Lanza el scheduler utilizando el entorno virtual del repositorio principal |
| `start_web.bat` / `stop_web.bat` | Arranque y parada rápida de la aplicación web |
| `backup_trading_db_20260227.dump` | Backup puntual de la BD PostgreSQL |
| `mkdocs.yml` | Configuración de MkDocs |

`start_web.bat` identifica el PID y proceso que ocupan el puerto 5000 y evita lanzar instancias duplicadas. `stop_web.bat` verifica que el listener corresponda a TradingCore antes de terminarlo, y `scripts/verify.ps1` muestra el estado operativo del servidor web.

---

## Documentación Detallada

- Manual de Usuario: **[User/MANUAL_USUARIO_TRADINGCORE.md](User/MANUAL_USUARIO_TRADINGCORE.md)**
- Arquitectura canónica: **[ARCHITECTURE.md](ARCHITECTURE.md)**
- Índice general: **[Index/00_INDEX_DOCUMENTACION.md](Index/00_INDEX_DOCUMENTACION.md)**
- Manual operativo: **[Manual_operativo_TradingCore_PowerShell_Git_Copilot.md](Manual_operativo_TradingCore_PowerShell_Git_Copilot.md)**
