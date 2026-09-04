# TradingCore: Motor Central y Arquitectura Modular

Última actualización: 04/09/2026

Este repositorio contiene la arquitectura central (Motor) para múltiples escenarios de trading (Backtesting, Live Trading, Web Apps).

---

## Inicio Rapido (Backtest Web)

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
   ```
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

```
trading_engine/
├── core/                    🔴 Núcleo de ejecución
│   ├── Logica_Trading.py        Gestión de señales de entrada/salida, stops y trailing
│   ├── Backtest_Runner.py       Orquestador del ciclo de backtesting (barra a barra)
│   ├── database_pg.py           Capa de acceso a PostgreSQL (ORM ligero, queries, modelos)
│   └── constants.py             Constantes globales del motor (nombres de columnas, estados)
├── indicators/              🔴 Filtros técnicos (uno por indicador)
│   ├── Filtro_EMA.py            Cruce de medias / precio vs EMA
│   ├── Filtro_RSI.py            Relative Strength Index
│   ├── Filtro_MACD.py           MACD y señal
│   ├── Filtro_ATR.py            Average True Range (volatilidad, stops dinámicos)
│   ├── Filtro_BollingerBands.py Bandas de Bollinger
│   ├── Filtro_Stochastic.py     Oscilador Estocástico
│   ├── Filtro_MoS.py            Margin of Safety (filtro de precio justo)
│   └── Filtro_Volume.py         Filtro de volumen relativo
└── utils/                   🔴 Utilidades compartidas del motor
    ├── Calculos_Financieros.py  Cálculos de rentabilidad, métricas de cartera
    ├── Calculos_Tecnicos.py     Cálculo de indicadores técnicos sobre DataFrames
    ├── Data_download.py         Descarga de datos OHLCV vía yfinance
    ├── Graficos_financieros.py  Generación de gráficos Bokeh interactivos
    ├── Historico_manager.py     Lectura y cacheo de CSVs históricos de Data_files/
    ├── setup.py                 Configuración de entorno del motor
    ├── utils_mail.py            Envío de alertas por correo electrónico
    └── Config/
        └── setup_mail.env       Credenciales de correo (no versionar en producción)
```

---

### 🔴 Aplicación Web BacktestWeb (`scenarios/BacktestWeb/`)

Aplicación Flask que expone el motor de trading como interfaz web multiusuario.

```
scenarios/BacktestWeb/
├── app.py                   🔴 Punto de entrada Flask, registro de blueprints, login
├── Backtest.py              🔴 Capa de orquestación: lanza backtests, persiste resultados
├── estrategia_system.py     🔴 Sistema de parámetros de estrategia (preset/config dinámica)
├── configuracion.py         🟡 Carga y validación de configuración de usuario (JSON)
├── database.py              🟡 Modelos SQLAlchemy y sesión de BD (PostgreSQL)
├── DBStore.py               🟡 Persistencia de resultados, snapshots y gráficos
├── file_handler.py          🟡 Gestión de ficheros de configuración y caché en disco
├── routes/
│   └── main_bp.py           🔴 Blueprint principal: todas las rutas HTTP de la app
└── templates/               🔴 Plantillas HTML Jinja2
    ├── index.html               Layout principal (tabs de configuración)
    ├── login.html               Pantalla de autenticación
    ├── cargando.html            Página de espera durante ejecución
    ├── _tab_global.html         Tab: parámetros globales de estrategia
    ├── _tab_ema.html            Tab: parámetros EMA
    ├── _tab_rsi.html            Tab: parámetros RSI
    ├── _tab_macd.html           Tab: parámetros MACD
    ├── _tab_atr.html            Tab: parámetros ATR / stops dinámicos
    ├── _tab_bb.html             Tab: parámetros Bollinger Bands
    ├── _tab_stoch.html          Tab: parámetros Estocástico
    ├── _tab_mos_volume.html     Tab: parámetros MoS y Volumen
    ├── _tab_symbols.html        Tab: selección de símbolos y temporalidad
    ├── _tab_historial.html      Tab: historial de resultados con paginación por tandas
    ├── _tab_charts_viewer.html  Tab: visor de gráficos Bokeh
    ├── _tab_scheduler.html      Tab: programación de backtests automáticos
    ├── _tab_ficheros.html       Tab: gestión de ficheros de configuración
    └── _tab_user_management.html Tab: administración de usuarios
```

---

### 🟡 Datos históricos (`Data_files/`)

Ficheros CSV con datos OHLCV descargados de yfinance, organizados por símbolo y temporalidad (`SYMBOL_INTERVAL_MAX.csv`). El motor los lee directamente sin BD para el backtesting. Contiene cientos de activos de S&P 500, Ibex 35, eurostoxx y otros índices globales.

```
Data_files/
├── SYMBOL_1d_MAX.csv        Datos diarios (ej. AAPL_1d_MAX.csv)
├── SYMBOL_1wk_MAX.csv       Datos semanales
├── SYMBOL_1h_MAX.csv        Datos horarios (solo algunos símbolos)
├── SYMBOL_1mo_MAX.csv       Datos mensuales (solo algunos símbolos)
├── Backtest_config/         Configuraciones de backtest guardadas por el usuario
└── Fundamentals/            Datos fundamentales descargados (ratios, métricas)
```

---

### 🟡 Base de datos PostgreSQL embebida (`data_pg/` + `pgsql/`)

```
data_pg/                     🟡 Directorio de datos del servidor PostgreSQL
pgsql/                       🟡 Binarios del servidor PostgreSQL portable (Windows)
pg_start.bat                 🟡 Script de arranque del servidor PostgreSQL
pg_stop.bat                  🟡 Script de parada del servidor PostgreSQL
```

La BD PostgreSQL almacena: usuarios, estrategias, resultados de backtests, trades, snapshots de gráficos y configuraciones. Es la fuente de verdad de la aplicación web.

---

### 🟡 Resultados y artefactos de backtesting (`Backtesting/`)

Directorio de salida y legado de ejecuciones anteriores.

```
Backtesting/
├── Graphics/                🟡 Caché de gráficos HTML generados por Bokeh, por usuario
│   ├── juan/                    Gráficos del usuario juan
│   ├── pedro/                   Gráficos del usuario pedro
│   ├── invitado/                Gráficos del usuario invitado
│   └── semana/                  Gráficos de ejecuciones programadas semanales
├── Run_Results/             🟡 Resultados en CSV de ejecuciones batch históricas
└── logs/                    🟡 Logs de backtesting (errores, trazas de ejecución)

```

---

### 🟡 Logs de la aplicación (`logs/`)

```
logs/
├── backtest_scheduler_web.log   Log del scheduler de backtests periódicos
├── server_local.log             Log del servidor Flask
└── batch_*.log                  Logs de ejecuciones batch
```

---

### 🟡 Scripts operativos y auxiliares (`scripts/`)

Los scripts auxiliares se agrupan por finalidad. No forman parte del núcleo del motor de trading, aunque algunos tienen funciones operativas de apoyo a la aplicación.

```
scripts/
├── analysis/                Análisis de resultados de backtests
├── diagnostics/             Diagnóstico manual de rutas, login y estado de la app
├── experiments/             Pruebas puntuales y experimentos de estrategias e indicadores
├── maintenance/             Utilidades de administración y mantenimiento
├── presets/                 Configuraciones predefinidas de estrategias
├── scheduler/               Scheduler de backtests periódicos
│   └── backtest_scheduler.py
├── optimize_rsi.py          Barrido de parámetros RSI
├── sweep_rsi_filter.py      Optimización por grilla del filtro RSI
├── audit_stops_combinations.py  Auditoría de combinaciones de stops
├── batch_replay_by_ids.py   Re-ejecución batch de estrategias por ID
├── query_backtest_results.py    Consulta y exportación de resultados
└── verificar_backtest_web.py    Verificación de integridad de la app web
```

Los tests automatizados se mantienen separados del resto de scripts auxiliares:

```
tests/
├── unit/                    Pruebas unitarias del motor
├── integration/             Pruebas de integración, incluida la persistencia
└── web/                     Pruebas de rutas y comportamiento de la aplicación web
```

---

### 🟡 Escenario Datos Fundamentales (`scenarios/Fundamental_Data/`)

Módulo para la descarga y gestión de datos fundamentales (ratios financieros, métricas de empresa).

```
scenarios/Fundamental_Data/
├── manager.py               Descarga y actualiza datos fundamentales vía yfinance
├── Fundamental_Manager.py   Lógica de acceso y consulta de fundamentales
└── database.py              Capa de persistencia de datos fundamentales
```

---

### 🟢 Laboratorio (`Laboratorio/`)

Espacio de experimentación y prototipos. Código no productivo.

```
Laboratorio/
└── test_yfinance_symbols.py     Experimentos con la API de yfinance
```

---

### 🟢 Documentación (`docs/`)

```
docs/
├── README.md                Este fichero
├── ARCHITECTURE.md          Arquitectura canónica del sistema
├── Architecture/            Diagramas y flujos de arquitectura detallados
├── Index/                   Índice general de toda la documentación
├── Guides/                  Guías de uso y configuración
├── Guia/                    Guías operacionales
├── Plans/                   Planes de desarrollo y mejoras pendientes
├── Summaries/               Resúmenes de cambios y decisiones técnicas
├── Fixes/                   Registro de correcciones importantes
├── Diagnosis/               Diagnósticos de problemas resueltos
└── api/                     Documentación de la API interna
```

---

### 🟢 Ficheros raíz relevantes

| Fichero | Descripción |
| :--- | :--- |
| `requirements.txt` | Dependencias Python del proyecto |
| `run_backtest_scheduler.bat` | Lanza el scheduler de backtests en segundo plano |
| `start_web.bat` / `stop_web.bat` | Arranque y parada rápida de la app web |
| `backup_trading_db_20260227.dump` | Backup puntual de la BD PostgreSQL |
| `mkdocs.yml` | Configuración de MkDocs para generar documentación estática |
| `OPTIMIZACIONES_IMPLEMENTADAS.md` | Registro de optimizaciones de rendimiento aplicadas |

---

## Documentacion Detallada

- Arquitectura canónica: **[ARCHITECTURE.md](ARCHITECTURE.md)**
- Flujo web de ejecución: **[Architecture/FLUJO_ARQUITECTURA_MEJORADO.md](Architecture/FLUJO_ARQUITECTURA_MEJORADO.md)**
- Índice general: **[Index/00_INDEX_DOCUMENTACION.md](Index/00_INDEX_DOCUMENTACION.md)**