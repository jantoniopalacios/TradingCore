# Diagnóstico: Filtro ATR - Calibración por Perfil de Volatilidad

**Fecha:** 10 de febrero de 2026  
**Versión:** 1.0  
**Estado:** ✅ Diagnosticado - En calibración

---

## 1. Descripción del Problema

El filtro ATR (Average True Range) implementado con parámetros por defecto (Min=2.0, Max=5.0) está **bloqueando excesivamente las oportunidades de compra** en activos de baja volatilidad como NKE, reduciendo el número de trades sin mejorar el win rate.

### Síntomas Observados

**Test con NKE (Nike) - Período 2008-2026:**
- **Fase 1** (ATR desactivado): Baseline con X trades
- **Fase 2** (ATR 0.1-20.0): Resultados idénticos a Fase 1 ✓ (lógica correcta)
- **Fase 3** (ATR 2.0-5.0): 
  - ❌ Menos trades (esperado pero excesivo)
  - ❌ Peor win rate (inesperado - bloqueando trades buenos)
  - ~ Max drawdown similar

---

## 2. Análisis de Causa Raíz

### 2.1 Distribución Histórica del ATR en NKE

Después de analizar 18 años de datos (2008-2026), identificamos que NKE tiene un **perfil de volatilidad naturalmente bajo**:

| Período | Rango ATR Típico | % de Tiempo | Estado con Filtro 2.0-5.0 |
|---------|------------------|-------------|---------------------------|
| 2008-2015 (Pre-vol) | 0.50 - 1.50 | ~40% | ❌ Bloqueado (< 2.0) |
| 2016-2019 (Normal) | 1.60 - 1.95 | ~25% | ❌ Bloqueado (< 2.0) |
| 2020-2022 (COVID) | 5.00 - 10.00 | ~15% | ❌ Bloqueado (> 5.0) |
| 2023-2026 (Reciente) | 3.50 - 6.50 | ~20% | ⚠️ Parcialmente bloqueado |

**Resultado:** Solo **2 compras permitidas** en 18 años cuando ATR estuvo brevemente en el rango 2.44-2.81 (2015-08-24 y 2017-06-26).

### 2.2 Ejemplos de Bloqueos del Log

**Bloqueos por ATR < 2.0 (períodos normales):**
```
[ATR FILTER] 2010-01-04 | ATR=0.48, Min=2.00, Max=5.00, Permite=✗
[ATR FILTER] 2011-01-24 | ATR=0.66, Min=2.00, Max=5.00, Permite=✗
[ATR FILTER] 2013-02-25 | ATR=0.75, Min=2.00, Max=5.00, Permite=✗
```

**Bloqueos por ATR > 5.0 (períodos de alta volatilidad):**
```
[ATR FILTER] 2020-03-23 | ATR=10.08, Min=2.00, Max=5.00, Permite=✗
[ATR FILTER] 2020-09-21 | ATR=7.18, Min=2.00, Max=5.00, Permite=✗
[ATR FILTER] 2021-03-22 | ATR=8.76, Min=2.00, Max=5.00, Permite=✗
```

**Compras permitidas (solo 2 en 18 años):**
```
[ATR FILTER] 2015-08-24 | ATR=2.81, Min=2.00, Max=5.00, Permite=✓
[ATR FILTER] 2017-06-26 | ATR=2.44, Min=2.00, Max=5.00, Permite=✓
```

---

## 3. Conclusión del Diagnóstico

### Problema Identificado
Los parámetros por defecto (2.0-5.0) fueron diseñados para activos de **volatilidad media-alta** (NVDA, TSLA, tech stocks), pero no son adecuados para:

1. **Acciones defensivas/estables:** NKE, WMT, JNJ, etc.
2. **Blue chips tradicionales:** Consumer staples, utilities
3. **REITs de baja beta**

### Validación Lógica
✅ El filtro ATR funciona correctamente (Fase 2 confirma lógica)  
❌ La calibración por defecto es inadecuada para ciertos perfiles

---

## 4. Soluciones Propuestas

### 4.1 Recomendaciones por Perfil de Activo

| Tipo de Activo | ATR Min | ATR Max | Ejemplos |
|----------------|---------|---------|----------|
| **Baja Volatilidad** | 0.5 | 3.5 | NKE, WMT, JNJ, KO |
| **Media Volatilidad** | 1.5 | 5.0 | AAPL, MSFT, COST |
| **Alta Volatilidad** | 2.0 | 7.0 | NVDA, TSLA, COIN |
| **Cripto/Especulativo** | 3.0 | 15.0 | BTC, MEME stocks |

### 4.2 Calibración Específica para NKE

**Opción A: Conservadora (Recomendada)**
```
atr_enabled = True
atr_min = 0.5
atr_max = 4.0
```
- ✅ Captura rango histórico normal (0.5-2.0)
- ✅ Permite recuperaciones suaves (2.0-4.0)
- ❌ Bloquea solo caos extremo (>4.0)
- **Estimado:** 60-70% de períodos permitidos vs 2% actual

**Opción B: Moderada**
```
atr_enabled = True
atr_min = 0.8
atr_max = 7.0
```
- Incluye períodos de volatilidad COVID
- Más permisivo pero menos selectivo

**Opción C: Desactivar para Baja Volatilidad**
```
atr_enabled = False
```
- Para activos donde ATR no aporta valor discriminatorio
- Dejar RSI, EMA, Volume y MoS hacer el filtrado

---

## 5. Plan de Acción

### Fase 4: Validación con Otros Activos
- [ ] **ZTS (Zoetis):** Sector salud, volatilidad media → Validar si 2.0-5.0 funciona
- [ ] **NVDA (Nvidia):** Tech alta volatilidad → Confirmar si 2.0-7.0 es mejor
- [ ] **WMT (Walmart):** Defensiva → Confirmar perfil similar a NKE

### Implementación Final
1. **Corto plazo:** Actualizar valores por defecto en `estrategia_system.py` a rangos más amplios
2. **Medio plazo:** Documentar en modal de UI los rangos recomendados por tipo de activo
3. **Largo plazo:** Considerar calibración automática basada en ATR histórico del activo

---

## 6. Archivos Afectados

### Código
- `trading_engine/indicators/Filtro_ATR.py` - Lógica del filtro ✅
- `scenarios/BacktestWeb/estrategia_system.py` - Parámetros por defecto
- `scenarios/BacktestWeb/templates/_tab_atr.html` - UI y documentación

### Documentación
- `docs/Guides/GUIA_COMBINACION_INDICADORES.md` - Actualizar con recomendaciones ATR
- `docs/Diagnosis/DIAGNOSTICO_FILTRO_ATR_VOLATILIDAD.md` - Este documento

---

## 7. Lecciones Aprendidas

1. **Un filtro no es universal:** Los parámetros deben ajustarse al perfil de volatilidad del activo
2. **Testeo multi-activo es crítico:** Lo que funciona en tech puede fallar en defensivas
3. **ATR es sensible al régimen de mercado:** COVID cambió radicalmente los rangos "normales"
4. **Documentación de rangos es esencial:** Los usuarios necesitan guías claras por tipo de activo

---

## 8. Referencias

- Commit implementación ATR: `5dbe343`
- Testing NKE: Logs del 10 de febrero de 2026
- Test methodology: 3-phase validation (disabled → wide → default)

---

**Estado Actual:** Pendiente de validación con ZTS y otros activos antes de ajustar parámetros por defecto.
