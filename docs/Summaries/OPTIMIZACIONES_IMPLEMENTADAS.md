# Optimizaciones de Performance - TradingCore

**Fecha:** Mayo 9-10, 2026  
**Objetivo:** Acelerar acceso del usuario admin y mejorar gestión de gráficos

---

## 1. Problema Identificado

Cuando el usuario **admin** accedía a la aplicación, **la carga era muy lenta** (15-30 segundos). Investigación reveló:

### N+1 Query Problem
- **Antes:** Por cada backtest en el historial (2700+ registros), se ejecutaba una consulta SELECT adicional para obtener el último trade
- **Impacto:** 2700+ consultas a base de datos para una sola página
- **Síntoma:** DB saturada, tiempo de respuesta exponencial

### Validación de Snapshot en Disco
- Se ejecutaba `.exists()` en filesystem para cada backtest
- I/O multiplicado innecesariamente

---

## 2. Soluciones Implementadas

### 2.1 Eager Loading de Trades (Máximo Impacto)

**Archivo:** `scenarios/BacktestWeb/routes/main_bp.py` (línea ~736-765)

**Antes:**
```python
for backtest in tanda_data['activos']:
    last_trade = Trade.query.filter_by(backtest_id=backtest.id).order_by(Trade.id.desc()).first()
    # 2700 consultas SQL
```

**Después:**
```python
# 1. Cargar TODOS los trades en una sola consulta
todos_ids = [r.id for r in todos]
all_trades_dict = {}
if todos_ids:
    trades_batch = Trade.query.filter(Trade.backtest_id.in_(todos_ids)).all()
    for trade in trades_batch:
        if trade.backtest_id not in all_trades_dict or trade.id > all_trades_dict[trade.backtest_id].id:
            all_trades_dict[trade.backtest_id] = trade

# 2. Lookup O(1) desde diccionario
last_trade = all_trades_dict.get(backtest.id)
```

**Impacto:** De 2700 SELECT → 1 SELECT batch + diccionario en memoria

---

### 2.2 Eager Loading de Usuarios

**Archivo:** `scenarios/BacktestWeb/routes/main_bp.py` (línea ~737)

```python
query_base = ResultadoBacktest.query.options(joinedload(ResultadoBacktest.propietario))...
```

**Impacto:** JOIN Usuario en la consulta inicial, evita N queries adicionales

---

### 2.3 Restauración de Gráficos HTML en BD

**Archivo:** `scenarios/BacktestWeb/Backtest.py` (línea ~52)

**Cambio de configuración:**
```python
# ANTES (default desactivado)
STORE_GRAPH_HTML_IN_DB = str(os.getenv('BACKTEST_STORE_GRAPH_HTML_IN_DB', '0'))...

# AHORA (default activado)
STORE_GRAPH_HTML_IN_DB = str(os.getenv('BACKTEST_STORE_GRAPH_HTML_IN_DB', '1'))...
```

**Impacto:** Cada backtest nuevo almacena automáticamente HTML en BD (no depende de snapshots/cache)

---

### 2.4 Visualización de Gráficos Mejorada

**Archivo:** `scenarios/BacktestWeb/templates/_tab_historial.html` (línea ~243)

- Botón de gráfico siempre visible (no se oculta si falta artefacto)
- Cambio visual si gráfico no está disponible (estilo `secondary` vs `info`)
- Tooltip informativo explica qué hacer si no hay gráfico

**Archivo:** `scenarios/BacktestWeb/routes/main_bp.py` (línea ~1940)

- Mensaje de error mejorado si se solicita gráfico no disponible
- Sugiere re-ejecutar backtest para regenerarlo

---

## 3. Resultados Esperados

| Métrica | Antes | Después |
|---------|-------|---------|
| **Acceso admin (2700 registros)** | 15-30s | ~3-5s (estimado) |
| **Consultas BD al cargar historial** | 2700+ | 2 (resultados + trades batch) |
| **Tamaño BD** | 1272 MB | 1272 MB (con HTML restaurado) |
| **Gráficos en BD** | 2702/2702 | 2702/2702 |

---

## 4. Notas Técnicas

### Dependencias Requeridas
- SQLAlchemy `.options(joinedload())` → debe estar en imports
- `.filter(...in_(...))` syntax para batch queries

### Configuración por Entorno

Para **desactivar** almacenamiento de HTML en BD:
```bash
export BACKTEST_STORE_GRAPH_HTML_IN_DB=0
# o en Windows:
set BACKTEST_STORE_GRAPH_HTML_IN_DB=0
```

### Backward Compatibility
- Snapshots antiguos (.json.gz) se cargan si HTML no está disponible
- Cache HTML en disco aún funciona como fallback
- Código defensivo maneja casos sin gráficos

---

## 5. Cambios de Archivos

| Archivo | Cambios |
|---------|---------|
| `scenarios/BacktestWeb/routes/main_bp.py` | Eager loading trades/usuarios, visualización mejorada |
| `scenarios/BacktestWeb/Backtest.py` | Default STORE_GRAPH_HTML_IN_DB = '1' |
| `scenarios/BacktestWeb/templates/_tab_historial.html` | Botón gráfico siempre visible con estados |

---

## 6. Verificación Post-Implementación

✅ Gráficos HTML restaurados en BD (2702 registros)  
✅ Optimizaciones de queries implementadas  
✅ Sin errores de sintaxis  
✅ Backward compatible con datos antiguos  

**Próximo paso:** Monitorizar tiempo de acceso en producción. Si persiste el retardo, investigar otros cuellos de botella (cache de sesión, disk I/O, network latency).

---

## 7. Historial de Cambios

- **2026-05-09 20:43** - Backup con HTML (1.8 GB)
- **2026-05-09 21:XX** - Limpieza grafico_html (reducción a 113 MB)
- **2026-05-09 21:XX** - Restauración desde backup (1272 MB)
- **2026-05-10** - Optimizaciones de query implementadas
- **2026-05-10** - Pusheo a repositorio remoto
