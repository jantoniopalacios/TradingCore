````markdown
# 🔀 Combinación de Indicadores: EMA + RSI + MACD - Guía Estratégica

## 1️⃣ EL PROBLEMA: Indicadores Individuales vs Combinados

### Sin Confirmación (1 indicador):
```
EMA SOLO:
╔═══════════════════════════════════════════════════════════════╗
║ Compra en cada cruce → MUCHOS FALSOS POSITIVOS               ║
║ Ejemplo: NKE con ema_cruce_signal = True                     ║
║ Cruces: 18 en 3 meses = 6 por mes = SOBRE-TRADING           ║
║ Resultado: -44% (como vimos)                                 ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 2️⃣ MATRIZ DE COMBINACIONES

```
┌─────────────┬──────────────┬────────────────┬──────────────┐
│ Combo       │ Señal        │ Confirmación   │ Resultado    │
├─────────────┼──────────────┼────────────────┼──────────────┤
│ EMA + RSI   │ EMA cruza    │ RSI > 50       │ ⭐⭐⭐⭐      │
│             │              │ (momentum)     │ RECOMENDADO  │
├─────────────┼──────────────┼────────────────┼──────────────┤
│ EMA + MACD  │ EMA cruza    │ MACD en cruz   │ ⭐⭐⭐⭐⭐    │
│             │              │ (tendencia)    │ MÁS FUERTE   │
└─────────────┴──────────────┴────────────────┴──────────────┘
```

---

## 3️⃣ COMBO RECOMENDADA #1: EMA + RSI (Para NKE)

### Lógica:
```
COMPRA si:
1. EMA Rápida > EMA Lenta        (tendencia)
   AND                                          
2. RSI > 50 O RSI cruza 30       (momentum)
```

---

## 4️⃣ FILTROS DE CALIDAD: ATR (Volatilidad)

### ¿Qué es ATR?
**Average True Range** mide la volatilidad promedio del activo. Sirve como **filtro de calidad** para evitar:
- ❌ Mercados estancados (ATR muy bajo)
- ❌ Mercados caóticos (ATR muy alto)

### Calibración por Perfil de Activo

```
┌─────────────────────┬──────────┬──────────┬────────────────────┐
│ Tipo de Activo      │ ATR Min  │ ATR Max  │ Ejemplos           │
├─────────────────────┼──────────┼──────────┼────────────────────┤
│ Baja Volatilidad    │   0.5    │   3.5    │ NKE, WMT, JNJ, KO  │
│ Media Volatilidad   │   1.5    │   5.0    │ AAPL, MSFT, COST   │
│ Alta Volatilidad    │   2.0    │   7.0    │ NVDA, TSLA, AMD    │
│ Cripto/Especulativo │   3.0    │  15.0    │ BTC, MEME stocks   │
└─────────────────────┴──────────┴──────────┴────────────────────┘
```

### ⚠️ IMPORTANTE: Caso NKE

**Problema detectado (Feb 2026):**
- Parámetros por defecto (2.0-5.0) bloqueaban **98% de oportunidades** en NKE
- Solo 2 compras permitidas en 18 años
- Rango histórico real de NKE: **0.5-2.0** (bajo), con picos COVID en 7.0-10.0

**Solución para activos de baja volatilidad:**
```python
# Configuración NKE/WMT/JNJ:
atr_enabled = True
atr_min = 0.5
atr_max = 4.0
```

### Cómo Usar ATR en la Estrategia

**Paso 1:** Analiza el ATR histórico del activo
- Ejecuta backtest con ATR desactivado
- Revisa logs para ver rango típico de ATR
- Clasifica activo: bajo/medio/alto

**Paso 2:** Configura rangos apropiados
- Bajo: 0.5-4.0
- Medio: 1.5-5.0
- Alto: 2.0-7.0

**Paso 3:** Valida con 3-phase testing
1. ATR desactivado (baseline)
2. ATR muy amplio 0.1-20.0 (validar lógica)
3. ATR calibrado (evaluar efectividad)

---

## 5️⃣ ESTRATEGIA COMPLETA: EMA + RSI + ATR

### Configuración Multi-Filtro

```
┌────────────────────────────────────────────────────────┐
│                   FLUJO DE DECISIÓN                    │
└────────────────────────────────────────────────────────┘

1. SEÑAL DE ENTRADA (OR logic):
   ✓ EMA cruza arriba
   ✓ RSI rebota desde sobreventa
   ✓ MACD cruza positivo
   → Si alguno = TRUE → Continuar

2. FILTRO DE TENDENCIA (AND logic):
   ✓ EMA rápida > EMA lenta
   → Si FALSE → BLOCK

3. FILTRO DE MOMENTUM (AND logic):
   ✓ RSI > umbral (ej: 54)
   → Si FALSE → BLOCK

4. FILTRO DE VOLATILIDAD (AND logic):
   ✓ atr_min ≤ ATR ≤ atr_max
   → Si FALSE → BLOCK

5. FILTROS ADICIONALES:
   ✓ Volume > mínimo
   ✓ Margin of Safety
   → Si todos OK → COMPRA
```

### Ejemplo Práctico: NKE

**Parámetros recomendados:**
```python
# EMAs
ema_rapida = 10
ema_lenta = 30

# RSI
rsi_periodo = 14
rsi_umbral = 54.0

# ATR (CALIBRADO PARA NKE)
atr_enabled = True
atr_periodo = 14
atr_min = 0.5    # ← Ajustado para baja volatilidad
atr_max = 4.0    # ← Captura rango normal + recuperaciones

# Volume
volume_enabled = True
volume_min_ratio = 1.0
```

**Resultado esperado:**
- Menos trades que solo EMA (filtros funcionando)
- Win rate mejorado (mejor calidad de entradas)
- Drawdown controlado (evita mercados caóticos)

---

## 6️⃣ REFERENCIAS

- [Diagnóstico Filtro ATR](../Diagnosis/DIAGNOSTICO_FILTRO_ATR_VOLATILIDAD.md)
- [Test NKE](./TEST_NKE_README.md)
- [Quick Start BacktestWeb](./QUICK_START_BACKTEST_WEB.md)

````
