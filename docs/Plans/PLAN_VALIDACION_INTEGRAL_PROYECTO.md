# Plan de Validación Integral del Proyecto TradingCore

**Fecha:** 6 de febrero de 2026  
**Filosofía:** Reproduce-Diagnóstica-Valida-Documenta (RDVD)  
**Basado en:** Metodología exitosa aplicada a EMA y RSI

---

## 0. Metodología Base (RDVD)

Para cada componente/indicador:

1. **Reproduce:** Identifica un caso fallido o sospechoso en producción/DB
2. **Diagnostica:** Crea script que inspecciona logs, parámetros, estado interno
3. **Valida:** Re-ejecuta localmente con params conocidos; verifica que el behavior sea esperado
4. **Documenta:** Crea resumen con hallazgos, fixes aplicados, resultados

---

## I. AUDIT DE INDICADORES (Prioridad 1)

### 1.1 MACD
- **Estado:** Implementado en `trading_engine/indicators/Filtro_MACD.py`
- **Riesgo:** Posibilidad de flags no asignados en `configuracion.py` (como pasó con EMA)
- **Pasos:**
  1. Verificar que MACD flags están asignados en `asignar_parametros_a_system()`:
     - `macd_buy_logic`, `macd_sell_logic` (strings)
     - Parámetros: `macd_fast`, `macd_slow`, `macd_signal`
  2. Script diagnóstico: `scripts/check_macd_assignment.py`
  3. Reproducir backtest con MACD=True, inspeccionar señales
  4. Documento: `docs/Diagnosis/DIAGNOSTICO_MACD.md` + `docs/Fixes/FIX_MACD_*.md` si aplica

### 1.2 Estocásticos (Stochastic)
- **Estado:** `Filtro_Stochastic.py` (backup eliminado, revisar si está activo)
- **Acciones:**
  1. Verificar que está en `asignar_parametros_a_system()` (parámetros: `stochastic_period`, `stochastic_smoothing`, etc.)
  2. Script: `scripts/check_stochastic_assignment.py`
  3. Backtests de prueba con Stochastic activado

### 1.3 Bollinger Bands
- **Estado:** `Filtro_BollingerBands.py` (backup eliminado)
- **Pasos:** Ídem a Estocásticos

### 1.4 Volume / Money of Supply (MoS)
- **Estado:** `Filtro_Volume.py` y `Filtro_MoS.py` (backups eliminados)
- **Check:** ¿Están realmente funcionando o solo partially integrados?
- **Script:** `scripts/check_volume_logic.py`

---

## II. AUDIT DE LÓGICA DE TRADING (Prioridad 1)

### 2.1 Sistema de Buy Signals
- **Componentes:** `Logica_Trading.py`, combinaciones de indicadores
- **Riesgo:** ¿Se respetan todas las lógicas AND/OR criadas en frontend?
- **Pasos:**
  1. Revisar `check_buy_signal()` - ¿integra todos los flags?
  2. Script: `scripts/audit_buy_logic.py`
     - Simula 100 escenarios aleatorios de indicadores
     - Verifica que la lógica coincide con parámetros técnicos
  3. Backtest con diferentes combinaciones (EMA+RSI, EMA+MACD, etc.)

### 2.2 Sistema de Sell Signals
- **Componentes:** `check_ema_sell_signal()`, `check_rsi_sell_signal()`, etc.
- **Riesgo:** Algunos sells pueden no etiquetarse correctamente (como pasó con EMA descendente)
- **Pasos:**
  1. Verificar cada `check_*_sell_signal()` genera descripción correcta
  2. Script: `scripts/validate_sell_descriptions.py`
     - Busca backtests recientes
     - Inspecciona que `Descripcion` en trades coincida con flags activados
  3. Documento: `docs/Diagnosis/DIAGNOSTICO_SELL_LOGIC_COMPLETO.md`

### 2.3 Stop Loss y Take Profit
- **Riesgo:** ¿Se aplican correctamente? ¿Se etiquetan en trades?
- **Script:** `scripts/validate_stoploss_tp.py`

---

## III. AUDIT DE DATOS Y CONFIGURACIÓN (Prioridad 1)

### 3.1 Parámetros Técnicos en DB
- **Problema potencial:** Parámetros guardados en DB pero no asignados a System
- **Script:** `scripts/audit_params_db_vs_system.py`
  - Busca todos los backtests
  - Para cada uno, compara `params_tecnicos` (JSON) con lo que System tiene
  - Reporta discrepancias
- **Salida:** CSV con `backtest_id | param | db_value | system_value | match?`

### 3.2 Datos Históricos (CSV Data Files)
- **Check:** ¿Todos los CSVs tienen las columnas esperadas (OHLCV)?
- **Script:** `scripts/validate_csv_structure.py`
  - Carga cada CSV en `Data_files/`
  - Verifica: Date, Open, High, Low, Close, Volume (y variantes)
  - Reporte: qué CSVs tienen problemas

### 3.3 Filtro Fundamental
- **Riesgo:** Si está activado, ¿funciona o falla silenciosamente?
- **Script:** `scripts/test_fundamental_filter.py`
  - Backtest con `filtro_fundamental=True` y `False`
  - Compara resultados (número de trades, P&L)

---

## IV. AUDIT DE RUTAS Y FRONTEND (Prioridad 2)

### 4.1 Rutas `/launch_strategy`, `/backtest_results`, etc.
- **Pasos:**
  1. Revisar `scenarios/BacktestWeb/routes/main_bp.py`
  2. Script: `scripts/test_routes_basic.py`
     - Simula POSTs a `/launch_strategy` con diferentes parámetros
     - Verifica que las respuestas sean válidas (status 200, JSON válido)

### 4.2 Templates HTML (forms, tabs de indicadores)
- **Check:** ¿Todos los switches/inputs mapean correctamente a `params_tecnicos`?
- **Script:** Manual - revisar que cada `_tab_*.html`:
  - `_tab_ema.html` tiene inputs para: `ema_cruce_signal`, `ema_fast_period`, `ema_slow_period`, `ema_slow_descendente`, etc.
  - `_tab_rsi.html`, `_tab_macd.html`, etc. similares
  - Todos mapean a nombres que `configuracion.py` entiende

---

## V. AUDIT DE BASE DE DATOS (Prioridad 2)

### 5.1 Integridad de Tablas
- **Script:** `scripts/audit_db_integrity.py`
  - Verifica `ResultadoBacktest`, `Trade`, `Usuario`
  - Busca NULL indeseados, referencias rotas
  - Reporte: filas con problemas

### 5.2 Índices y Performance
- **Check:** ¿Las queries son rápidas? ¿Hay índices en columnas frecuentes (`usuario_id`, `fecha_ejecucion`)?
- **Script simple:** Ejecutar un backtest, medir tiempo de lectura/escritura en DB

---

## VI. AUDIT DE LOGGING Y OBSERVABILIDAD (Prioridad 2)

### 6.1 Coverage de Logs
- **Script:** `scripts/audit_logging_coverage.py`
  - Ejecuta un backtest completo
  - Verifica que hay logs en todos los 9 pasos descritos en `FLUJO_ARQUITECTURA_MEJORADO.md`
  - Reporta gaps

### 6.2 Formato de Logs
- **Check:** ¿Los logs siguen el patrón `[ETAPA] Mensaje`?
- **Manual review:** `logs/trading_app.log` después de un backtest

---

## VII. AUDIT DE CACHÉ Y ESTADO (Prioridad 3)

### 7.1 `System` Class State
- **Riesgo:** ¿El objeto `System` pierde valores entre backtests?
- **Script:** `scripts/test_system_state_persistence.py`
  - Ejecuta 3 backtests consecutivos con parámetros diferentes
  - Verifica que `System` toma valores frescos cada vez

### 7.2 Trade List
- **Check:** ¿El `trades_list` en estrategia se limpia entre ejecuciones?

---

## VIII. PLAN DE EJECUCIÓN

### Fase 1: Auditoría Rápida (2-3 horas)
1. Crear scripts de check para Indicadores (MACD, Stochastic, BB, Volume)
2. Correr `audit_params_db_vs_system.py` y revisar discrepancias
3. Validar estructura de CSVs
4. Documento resumen: `docs/Summaries/RESUMEN_AUDITORIA_FASE1.md`

### Fase 2: Validación de Lógica (3-4 horas)
1. Scripts para buy/sell logic validation
2. Re-ejecutar 20-30 backtests variados (diferentes combinaciones de indicadores)
3. Inspeccionar que todas las señales se etiquetan correctamente
4. Fixes aplicados si encuentra problemas (seguir patrón EMA/RSI)
5. Documento: `docs/Diagnosis/AUDITORIA_LOGICA_TRADING_COMPLETA.md`

### Fase 3: DB y Observabilidad (2 horas)
1. Auditoría de DB (integridad, índices)
2. Revisión de logs
3. Documento: `docs/Diagnosis/AUDITORIA_DB_Y_LOGGING.md`

### Fase 4: Optimización y Documentación (1-2 horas)
1. Documentar hallazgos consolidados
2. Crear guías de debugging para cada componente
3. Actualizar `00_INDEX_DOCUMENTACION.md`

---

## IX. CRITERIOS DE ÉXITO

✅ **Completada la auditoría cuando:**
- Todos los indicadores tienen asignación verificada en `configuracion.py`
- BD tiene integridad comprobada
- 100% de backtests replay produce etiquetas correctas en trades
- Logs cubren todos los pasos del flujo
- Documentación actualizada en `docs/`
- CSV resumen de auditoría generado

---

## X. RIESGOS IDENTIFICABLES

| Riesgo | Probabilidad | Impacto |
|--------|--------------|--------|
| Parámetros no asignados (como EMA) | **Alta** | Alto → revisión sistemática MACD, Stochastic, BB |
| Descripciones de trades inconsistentes | **Media** | Medio → validación de todas las funciones `check_*_sell_signal()` |
| DB con datos inconsistentes | **Baja** | Alto → auditoría completa requerida |
| Logs insuficientes para debugging | **Media** | Medio → mejora de logging donde falte |

---

## XI. PRÓXIMOS PASOS

1. **Ya ejecutado:**
   - ✅ Fix EMA descendente + validación
   - ✅ Análisis 58 backtests

2. **Siguiente (Esta semana):**
   - ⏳ Scripts fase 1 (MACD, Stochastic, BB, params audit)
   - ⏳ Re-ejecución batch 20-30 backtests variados

3. **Siguiente (Semana 2):**
   - ⏳ Auditoría DB, logging, optimizaciones
   - ⏳ Documento resumen final

---

**Responsable:** AI Agent + Usuario  
**Última revisión:** 6 Feb 2026
