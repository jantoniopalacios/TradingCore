````markdown
# 🎯 Arquitectura de Señales EMA - Explicación Completa

## 1️⃣ CÓMO FUNCIONA EL SISTEMA

### Flujo General (Next → Decisión → Ejecución)

El backtest ejecuta un ciclo por cada barra (día/semana/mes según intervalo):

```
┌─────────────────────────────────────────────────────────────────────┐
│ CICLO POR BARRA (next)                                              │
├─────────────────────────────────────────────────────────────────────┤
│ 1️⃣ ACTUALIZAR ESTADOS (update_ema_state)                            │
│    └─ Calcula si EMA Lenta está: mínimo, máximo, ascendente, descendente
│                                                                      │
│ 2️⃣ EVALUAR COMPRA (check_buy_signal) - SI NO HAY POSICIÓN          │
│    ├─ Genera señal OR: ✓ si EMA cruce,  mínimo,  ascendente        │
│    ├─ Aplica filtro AND: ✗ deniega si máximo/descendente           │
│    ├─ Aplica filtros adicionales: volumen, margen seguridad         │
│    └─ COMPRA si todo se cumple                                      │
│                                                                      │
│ 3️⃣ GESTIONAR POSICIÓN (manage_existing_position) - SI HAY POSICIÓN  │
│    ├─ Evalúa cierre técnico: ✓ vende por cambio EMA tendencia      │
│    ├─ Actualiza Trailing Stop Loss dinámico                         │
│    └─ VENDE si cierre técnico O precio toca Stop Loss               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ PARÁMETROS EMA DISPONIBLES EN LA WEB

La web UI proporciona estos parámetros al usuario:

### A. **Parámetros de Configuración Básica**
```python
ema_fast_period      # Período EMA Rápida (ej: 10, 20)
ema_slow_period      # Período EMA Lenta (ej: 50, 100, 200)
ema_cruce_signal     # Activar cruce EMA Rápida > EMA Lenta (True/False)
```

### B. **Parámetros de COMPRA (Qué condiciones ACTIVAN la compra)**
```python
ema_slow_minimo        # Compra si EMA Lenta está en MÍNIMO (local)
ema_slow_ascendente    # Compra si EMA Lenta está ASCENDENTE
ema_slow_maximo        # NO COMPRA si EMA Lenta está en MÁXIMO (filtro AND)
ema_slow_descendente   # NO COMPRA si EMA Lenta está DESCENDENTE (filtro AND)
```

### C. **Parámetros de VENTA (Cuándo CERRAR una posición abierta)**
```python
ema_sell_logic  # Puede ser: 'ema_slow_descendente' o 'ema_slow_maximo'
                # Solo cierra si la tendencia cambia al estado seleccionado
```

**IMPORTANTE**: Estos parámetros son booleanos (True/False) excepto `ema_sell_logic` que es string.

---

## 3️⃣ LÓGICA DE DECISIÓN DE COMPRA

### Paso 1: Cálculo de Estados (CADA BARRA)

```
Estado actual de EMA Lenta = Derivada de los últimos 4 datos:

✓ MÍNIMO       → Precio ca en locales recientes (punto bajo)
✓ MÁXIMO       → Precio está en locales recientes (punto alto)  
✓ ASCENDENTE   → Pendiente positiva (EMA subiendo)
✓ DESCENDENTE  → Pendiente negativa (EMA bajando)
```

Ejemplo con datos reales (NKE 2025):
```
Fecha       EMA200   Estados calculados
─────────────────────────────────────
2025-10-01  $70.50   minimo=False, maximo=False, ascendente=False, descendente=False (estable)
2025-10-02  $68.45   minimo=True,  maximo=False, ascendente=False, descendente=False (alcanzó mínimo)
2025-10-03  $69.20   minimo=False, maximo=False, ascendente=True,  descendente=False (empezó a subir)
2025-10-04  $70.10   minimo=False, maximo=False, ascendente=True,  descendente=False (sigue subiendo)
2025-10-05  $71.20   minimo=False, maximo=True,  ascendente=False, descendente=False (alcanzó máximo)
2025-10-06  $70.80   minimo=False, maximo=False, ascendente=False, descendente=True  (empezó a bajar)
```

### Paso 2: Lógica de Señal (Condición OR)

**Se ACTIVA compra si CUALQUIERA de estas es cierta:**

```python
condicion_compra = (
    (ema_cruce_signal AND EMA_Rápida cruza EMA_Lenta)     # OR
    OR
    (ema_slow_minimo AND estado_actual == MÍNIMO)          # OR
    OR
    (ema_slow_ascendente AND estado_actual == ASCENDENTE)  # OR
    OR
    (Otras señales RSI/MACD/etc)                           # OR
)
```

---

## 4️⃣ LÓGICA DE CIERRE (VENTA)

### Cierre Técnico

```python
if ema_sell_logic == 'ema_slow_descendente':
    if EMA_actual_estado == DESCENDENTE:
        VENDER  # Cierra cuando tendencia cambia a baja

if ema_sell_logic == 'ema_slow_maximo':
    if EMA_actual_estado == MÁXIMO:
        VENDER  # Cierra cuando alcanza pico
```

---

## 5️⃣ ¿QUÉ TAN FLEXIBLE ES?

### ✅ SÍ, MUY FLEXIBLE

Puedes combinar parámetros libremente:
- ✓ Comprar solo en mínimos
- ✓ Comprar si EMA sube O si está en mínimo
- ✓ Comprar por cruce únicamente
- ✓ Combinar EMA con RSI, MACD, Bandas Bollinger
- ✓ Usar filtros fundamentales (Margen de Seguridad)
- ✓ Volumen mínimo requerido
- ✓ Trailing Stop Loss personalizado

### ⚠️ PERO CON LÍMITES LÓGICOS INTELIGENTES

El sistema NO permite ciertas combinaciones incoherentes:

---

## 9️⃣ CONCLUSIÓN: ARQUITECTURA FINAL

```
ENTRADA (Web Form)
    ├─ ema_fast_period (int)
    ├─ ema_slow_period (int)
    ├─ ema_cruce_signal (bool)
    ├─ ema_slow_minimo (bool) ← Genera señal
    ├─ ema_slow_ascendente (bool) ← Genera señal
    ├─ ema_slow_maximo (bool) ← Deniega compra
    ├─ ema_slow_descendente (bool) ← Deniega compra
    └─ ema_sell_logic ('ema_slow_descendente' | 'ema_slow_maximo')
                ↓
        Cargar en System.ema_*
                ↓
        BACKTEST (Next)
                ├─ update_ema_state() → Calcula estados minimo/maximo/ascendente/descendente
                │
                ├─ check_buy_signal()
                │   ├─ Genera señal (OR): si ema_cruce O ema_slow_minimo O ema_slow_ascendente
                │   ├─ Aplica filtro (AND): deniega si ema_slow_maximo O ema_slow_descendente
                │   └─ COMPRA si (señal AND filtro) AND (volumen OK) AND (MoS OK)
                │
                └─ manage_existing_position()
                    ├─ Cierre técnico: vende si ema_sell_logic alcanzado
                    └─ Stop Loss: cierra si precio baja X%
                        ↓
                    SALIDA (Trade, PnL, Registro DB)
```

---

## Recomendación

Agregar validaciones en la web UI para advertir configuraciones contradictorias (ej. comprar en mínimo y denegar si está descendente).

````
