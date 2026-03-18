# Analisis de coherencia y plan de pruebas de validacion

> Documento historico de planificacion (febrero 2026).
> La arquitectura vigente esta documentada en `docs/ARCHITECTURE.md`.

## 1. Hallazgos principales

### Inconsistencia EMA detectada
**Problema:** EMA aparece inactivo en configuración pero **todos los backtests incluyen trades con "EMA Lenta Ascendente"**

---

## 2. Pruebas de validacion propuestas para NKE

### Test 1: Verificar aislamiento de RSI (RSI solo, sin EMA)
```
Objetivo:    Confirmar que RSI genera trades incluso cuando EMA está desactivado
Parámetros:  rsi=True, rsi_ascendente=True, ema_cruce_signal=False, ema_slow_ascendente=False
Activos:     NKE únicamente
Período:     2024-01-01 to 2024-12-31 (1 año, cubre caída)
Expectativa: Mínimo 20+ trades con SOLO "RSI Ascendente" (sin EMA)
```

---

## 3. Matriz de ejecucion

| Test | Prioridad | Esfuerzo | Resultado esperado |
|------|-----------|----------|-------------------|
| Test 1 (RSI Aislado) | 🔴 ALTA | 5 min | Confirma RSI funciona solo |
| Test 2 (Flags RSI) | 🔴 ALTA | 15 min | Valida lógica OR de flags |

---

## 4. Codigo de referencia

Ver: `scripts/tests/test_rsi_isolated.py`
