````markdown
# 📊 ANÁLISIS DE COHERENCIA Y PLAN DE PRUEBAS VALIDACIÓN

## I. HALLAZGOS PRINCIPALES

### A. Inconsistencia EMA Detectada ⚠️
**Problema:** EMA aparece inactivo en configuración pero **todos los backtests incluyen trades con "EMA Lenta Ascendente"**

---

## II. PRUEBAS DE VALIDACIÓN PROPUESTAS PARA NKE

### Test 1: Verificar Aislamiento de RSI (RSI Solo, Sin EMA)
```
Objetivo:    Confirmar que RSI genera trades incluso cuando EMA está desactivado
Parámetros:  rsi=True, rsi_ascendente=True, ema_cruce_signal=False, ema_slow_ascendente=False
Activos:     NKE únicamente
Período:     2024-01-01 to 2024-12-31 (1 año, cubre caída)
Expectativa: Mínimo 20+ trades con SOLO "RSI Ascendente" (sin EMA)
```

---

## V. MATRIZ DE EJECUCIÓN (Recomendado)

| Test | Prioridad | Esfuerzo | Resultado Esperado |
|------|-----------|----------|-------------------|
| Test 1 (RSI Aislado) | 🔴 ALTA | 5 min | Confirma RSI funciona solo |
| Test 2 (Flags RSI) | 🔴 ALTA | 15 min | Valida lógica OR de flags |

---

## IV. CÓDIGO TEST 1 READY (Ejecutar primero)

Ver: `scripts/test_rsi_isolated.py`

````
