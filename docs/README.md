# TradingCore: Motor Central y Arquitectura Modular

Última actualización: 19/09/2026

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

### 🟡 Datos históricos (`Data_files/`)

Ficheros CSV con datos OHLCV descargados principalmente mediante Yahoo Finance, organizados por símbolo y temporalidad.

```text
Data_files/
├── SYMBOL_1d_MAX.csv          Datos diarios
├── SYMBOL_1wk_MAX.csv         Datos semanales
├── SYMBOL_1h_MAX.csv          Datos horarios para los símbolos disponibles
├── SYMBOL_1mo_MAX.csv         Datos mensuales para los símbolos disponibles
├── Backtest_config/           Configuraciones locales de backtest
└── Fundamentals/              Caché de datos fundamentales
```

El motor reutiliza estos ficheros para reducir descargas y acelerar los backtests.

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
└── logs/                      🟡 Logs persistentes de la aplicación y backtesting
```

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
├── diagnostics/                 Diagnóstico manual de rutas, login y estado
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

La batería incluye cobertura específica de señales y filtros técnicos para EMA, RSI, MACD, Stochastic, ATR, Volumen y Bollinger Bands.

La verificación habitual del proyecto puede ejecutarse mediante:

```powershell
.\scripts\verify.ps1
```

Este script comprueba sintaxis Python, tests baseline y estado de Git.

---

### 🟡 Escenario Datos Fundamentales (`scenarios/Fundamental_Data/`)

Conjunto de utilidades auxiliares para la descarga, actualización, migración y mantenimiento de datos fundamentales.

Actualmente, el flujo productivo utilizado por el backtest web obtiene los datos fundamentales mediante Alpha Vantage:

```text
scenarios/BacktestWeb/Backtest.py
        ↓
trading_engine/utils/Data_download.py
        ↓
manage_fundamental_data()
        ↓
download_fundamentals_AlphaV()
```

El directorio `scenarios/Fundamental_Data/` contiene utilidades standalone y de mantenimiento y no constituye actualmente la ruta principal utilizada por el backtest web.

```text
scenarios/Fundamental_Data/
├── manager.py               Utilidades standalone de actualización y migración
├── Fundamental_Manager.py   Utilidades auxiliares de sincronización
└── database.py              Persistencia para estas utilidades
```

#### Revisión pendiente de fundamentales

La arquitectura de datos fundamentales está pendiente de una revisión más profunda.

La evolución prevista es:

- estudiar las métricas fundamentales disponibles mediante Yahoo Finance;
- utilizar Yahoo Finance como fuente principal cuando proporcione los datos e histórico necesarios;
- utilizar Alpha Vantage como fuente complementaria para ampliar el histórico cuando sea necesario;
- determinar exactamente qué métricas fundamentales necesita cada estrategia;
- desacoplar el motor de backtest del proveedor concreto de datos;
- unificar el formato de datos procedentes de distintos proveedores;
- mejorar la lógica de caché, antigüedad y actualización incremental;
- evitar que el número de trimestre de un fichero sea el único criterio para determinar si una caché está actualizada.

No debe asumirse una profundidad histórica fija de Yahoo Finance hasta que esta parte sea revisada y comprobada específicamente.

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
├── Manual_operativo_TradingCore_PowerShell_Git_Copilot.docx  Manual operativo del administrador
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

`start_web.bat` comprueba previamente si el puerto web ya está ocupado para evitar lanzar instancias duplicadas.

---

## Documentación Detallada

- Manual de Usuario: **[User/MANUAL_USUARIO_TRADINGCORE.md](User/MANUAL_USUARIO_TRADINGCORE.md)**
- Arquitectura canónica: **[ARCHITECTURE.md](ARCHITECTURE.md)**
- Índice general: **[Index/00_INDEX_DOCUMENTACION.md](Index/00_INDEX_DOCUMENTACION.md)**
