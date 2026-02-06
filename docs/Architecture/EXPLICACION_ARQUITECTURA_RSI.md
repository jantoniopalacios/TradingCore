````markdown
# 🎯 Arquitectura del Filtro RSI (Índice de Fuerza Relativa) - Guía Completa

## 1️⃣ ¿QUÉ ES EL RSI?

**RSI** (Relative Strength Index) es un oscilador de momentum que mide la **fuerza de los movimientos** de precios.

```
Rango: 0 - 100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
|   0 ────────────── 50 ────────────── 100
|  (Sobreventa)     (Neutral)      (Sobrecompra)
| 
| Valor < 30 → Muy bajo, posible rebote (compra)
| Valor 30-70 → Rango normal (neutral)
| Valor > 70 → Muy alto, posible caída (venta)
```

---

## 2️⃣ PARÁMETROS RSI DISPONIBLES EN LA WEB

### A. **Parámetros Básicos**
```python
rsi                    # ¿RSI activo? (True/False)
rsi_period             # Período de cálculo (default: 14)
rsi_low_level          # Umbral de sobreventa (default: 30)
rsi_high_level         # Umbral de sobrecompra (default: 70)
```

### B. **Parámetros Avanzados**
```python
rsi_strength_threshold # Nivel mínimo de "fuerza" (default: 50)
                       # RSI > 50 = tendencia alcista

rsi_buy_logic          # Estrategia de COMPRA (string)
rsi_sell_logic         # Estrategia de VENTA (string)
```

---

## 3️⃣ FLUJO DE DECISIÓN (LÓGICA RSI)

### Paso 1: Cálculo de Estados (CADA BARRA)

```
RSI actual = ta.momentum.rsi(Close, período=14)

Estados derivados:
┌─────────────────────────────────────────────┐
│ 1. minimo_STATE    → RSI en valle reciente  │
│ 2. maximo_STATE    → RSI en pico reciente   │
│ 3. ascendente_STATE → RSI subiendo          │
│ 4. descendente_STATE → RSI bajando          │
└─────────────────────────────────────────────┘
```

---

## 4️⃣ LÓGICA DE CIERRE (VENTA)

```python
def check_rsi_sell_signal(strategy_self):
    if (strategy_self.rsi_maximo and 
        strategy_self.rsi_maximo_STATE) or \
       (strategy_self.rsi_descendente and 
        strategy_self.rsi_descendente_STATE):
        return True, "VENTA RSI Máximo/Descendente"
```

---

## 9️⃣ CASO DE USO REAL: NKE CON RSI

Si comparamos la config actual de NKE (-44%) con RSI mejorado:

### Config ACTUAL (Sin RSI):
```
ema_cruce_signal: True
ema_slow_minimo: True
```

### Config MEJORADA (Con RSI):
```yaml
# EMA como tendencia
ema_cruce_signal: True
ema_slow_period: 50      # Cambio: 26 → 50 (más suavizado)

# RSI como confirmación
rsi: True
rsi_period: 14
rsi_low_level: 28        # Cambio: 30 → 28 (más sensible)
rsi_high_level: 75
rsi_strength_threshold: 55  # Cambio: 50 → 55 (menos agresivo)

# COMPRA solo si:
# • EMA Rápida cruza EMA Lenta
# • AND RSI > 55 OR RSI cruza 28
```

---

## Recomendaciones

1. Implementar detección de divergencias RSI
2. Añadir confirmación multi-timeframe

````
