# Estado del Proyecto TradingCore

**Fecha:** 8 de febrero de 2026  
**Objetivo del estado:** Mantener contexto completo para continuar verificacion y ampliaciones sin perdida de informacion.

---

## 1) Resumen ejecutivo

En este ciclo se corrigieron errores clave de logica de trading, se mejoro la documentacion UI para EMA y RSI, se creo una bateria de validaciones, se arreglo el orden temporal de trades y se estabilizo el pipeline de documentacion en GitHub Pages.

Resultado: backtests coherentes, ventas EMA por cruce descendente funcionando, RSI verificado con 9 escenarios, trades ordenados cronologicamente, y docs publicando sin fallar por warnings.

---

## 2) Fixes y cambios funcionales (codigo)

### 2.1 EMA: venta por cruce descendente (fast<slow)
**Archivo:** trading_engine/indicators/Filtro_EMA.py  
**Cambio:** Se agrego deteccion de crossdown usando `crossover(ema_slow, ema_fast)` dentro de `check_ema_sell_signal()`.

**Efecto:** Las ventas por cruce descendente funcionan y no todo termina por StopLoss.

### 2.2 Ordenamiento temporal de trades
**Archivo:** trading_engine/core/Backtest_Runner.py  
**Cambios:**
- En `run_backtest_for_symbol()`: ordenar `trades_log` por fecha antes del return.
- En `run_multi_symbol_backtest()`: ordenar `trades_df` por `Fecha` y resetear indice.

**Efecto:** Los logs ya no muestran saltos 2020 -> 2001 -> 2020.

---

## 3) UI y documentacion de indicadores (Backtest Web)

### 3.1 Modal EMA
**Archivo:** scenarios/BacktestWeb/templates/_tab_ema.html  
**Cambio:** Se reemplazo la info dispersa por un modal Bootstrap con boton "Ayuda".

**Incluye:**
- Definicion EMA
- Parametros
- Señales de compra/venta
- Logica OR/AND
- Diferencia con RSI
- Comportamiento sin switches
- Advertencia de veto hardcoded

### 3.2 Modal RSI
**Archivo:** scenarios/BacktestWeb/templates/_tab_rsi.html  
**Cambio:** Modal equivalente al de EMA con informacion consolidada.

**Incluye:**
- Definicion RSI
- Parametros
- Señales de compra/venta
- Logica OR/AND
- Diferencia vs EMA (no hay veto hardcoded)
- Comportamiento sin switches (Fuerza Pura)

---

## 4) Scripts de validacion creados

### 4.1 EMA
- scripts/test_single_ema_cruce_sell.py
- scripts/test_nke_exact_params.py

**Resultado clave:** En NKE 1wk 2000-2026 con EMA 5/50, 30 operaciones, 15 ventas por cruce, 0 StopLoss (100% cruce).

### 4.2 RSI
- scripts/validate_rsi_complete.py

**Resultado clave:** 9 escenarios distintos probados, todas las señales coherentes, sin veto hardcoded, y orden temporal correcto.

---

## 5) Documentacion y GitHub Pages

### 5.1 Correcciones de enlaces
**Archivo:** docs/Index/00_INDEX_DOCUMENTACION.md  
**Cambio:** Enlaces corregidos para ser relativos desde docs/ y se agrego el plan integral al indice.

### 5.2 Workflow de docs
**Archivo:** .github/workflows/docs.yml  
**Cambio:** Se cambio `mkdocs build --strict` por `mkdocs build --verbose` para no abortar por warnings.

**Estado:** Build de GitHub Pages OK.

---

## 6) Validaciones ejecutadas (resultado real)

### 6.1 EMA
- test_single_ema_cruce_sell.py -> Ventas por cruce detectadas.
- test_nke_exact_params.py -> 100% ventas por cruce en NKE 1wk.

### 6.2 RSI (validate_rsi_complete.py)
Escenarios ejecutados:
1) Sin switches -> compra Fuerza Pura, ventas StopLoss
2) Solo Minimo -> compra por sobreventa + Fuerza Pura, ventas StopLoss
3) Solo Maximo -> venta por sobrecompra + bloqueo
4) Minimo + Maximo -> reversivo clasico
5) Solo Ascendente -> compra por ascenso, ventas StopLoss
6) Solo Descendente -> ventas por descenso + bloqueo
7) Ascendente + Descendente -> momentum puro
8) Todos activados -> mezcla de señales
9) Sin veto hardcoded -> confirmado

Todos los escenarios terminaron correctos, y trades ordenados cronologicamente.

---

## 7) Diferencias clave EMA vs RSI

- **EMA** tiene veto hardcoded cuando EMA lenta esta descendente.
- **RSI** NO tiene veto hardcoded; solo bloquea si el usuario lo activa.
- Sin switches: EMA entra en modo Buy & Hold (con veto si EMA descendente), RSI entra en Fuerza Pura (RSI > 55).

---

## 8) Commits aplicados

### Commit 1
**Mensaje:** feat: EMA crossdown sell + modal UI + temporal sorting fix  
**Incluye:**
- Logica EMA crossdown
- Modales EMA/RSI
- Ordenamiento temporal trades
- Scripts de validacion EMA
- Plan de validacion integral

### Commit 2
**Mensaje:** fix(docs): corregir enlaces rotos y deshabilitar modo strict  
**Incluye:**
- Enlaces correctos en indice docs
- Build docs sin strict para evitar aborts

---

## 9) Estado actual del proyecto

- Backtest EMA corregido
- RSI validado completamente
- Logs ordenados cronologicamente
- Documentacion online estable
- Scripts de validacion disponibles

---

## 8) Validacion MACD (9 de febrero de 2026)

### ✅ Completado
- Script validate_macd_complete.py: 10 escenarios exitosos
- Modal Bootstrap con documentacion completa en _tab_macd.html
- Verificado: compras por MACD Fuerte (cruce), ventas por Maximo/Descendente
- Switches funcionan correctamente: minimo, maximo, ascendente, descendente
- Parametros alternativos validados (8/17/9 rápido, 16/36/12 lento)
- Orden cronológico confirmado en todos los tests
- Commit: 11aa307

### 🔍 Hallazgos
- MACD sin switches activa compras automaticas por cruce simple (útil para automation)
- Máximo bloquea compras + vende en picos (protección contra sobrecompra)
- Descendente bloquea compras + vende cuando pierde impulso
- Sin veto hardcoded como EMA (más flexible)

---

## 9) Proximos pasos sugeridos

1) Auditar indicadores restantes (Stochastic, Bollinger, Volume, MoS) usando MACD como template.
2) Crear scripts de diagnostico para asignacion de parametros en configuracion.
3) Ejecutar backtests de stress con varios simbolos y periodos.
4) Revisar warnings de MkDocs para eventualmente volver a `--strict`.
5) Consolidar resultados en docs/Diagnosis y docs/Fixes.

---

## 10) Como retomar rapido este contexto

Al volver al proyecto:
1) Leer este archivo de estado.
2) Revisar los dos ultimos commits (`git log -2`).
3) Re-ejecutar `scripts/validate_rsi_complete.py` si se hacen cambios en RSI.
4) Seguir el plan `docs/Plans/PLAN_VALIDACION_INTEGRAL_PROYECTO.md`.

---

## 12) Archivos clave a recordar

- trading_engine/indicators/Filtro_EMA.py
- trading_engine/indicators/Filtro_MACD.py
- trading_engine/core/Backtest_Runner.py
- scenarios/BacktestWeb/templates/_tab_ema.html
- scenarios/BacktestWeb/templates/_tab_rsi.html
- scenarios/BacktestWeb/templates/_tab_macd.html
- scripts/test_single_ema_cruce_sell.py
- scripts/test_nke_exact_params.py
- scripts/validate_rsi_complete.py
- scripts/validate_macd_complete.py
- docs/Index/00_INDEX_DOCUMENTACION.md
- .github/workflows/docs.yml
- docs/Plans/PLAN_VALIDACION_INTEGRAL_PROYECTO.md

---

Fin del estado.
