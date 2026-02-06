````markdown
# 🔴 DIAGNÓSTICO: Problemas Críticos del Filtro RSI

## Problema #1: Parámetros Faltantes en Configuración Web

### ¿Qué espera el código RSI?

```python
# En Filtro_RSI.py, línea 76-78:
cond_min_detect = strategy_self.rsi_minimo  # ← Espera este parámetro
if hasattr(strategy_self, 'rsi_maximo') and strategy_self.rsi_maximo:  # ← Y este
```

### ¿Qué proporciona la web?

Revisando `configuracion.py` líneas 175-183:
```python
System.rsi = get_param('rsi', False, bool)
System.rsi_period = get_param('rsi_period', 14, int)
System.rsi_low_level = get_param('rsi_low_level', 30, int)
System.rsi_high_level = get_param('rsi_high_level', 70, int)
System.rsi_strength_threshold = get_param('rsi_strength_threshold', 50, int)
System.rsi_buy_logic = get_param('rsi_buy_logic', 'None')
System.rsi_sell_logic = get_param('rsi_sell_logic', 'None')

# ❌ FALTA: rsi_minimo, rsi_maximo, rsi_ascendente, rsi_descendente
```

### Resultado:
```
En estrategia_system.py (línea 54):
    rsi_minimo = False  # ← SIEMPRE False de clase
    rsi_maximo = False  # ← SIEMPRE False de clase
    rsi_ascendente = False
    rsi_descendente = False

En check_rsi_buy_signal (línea 76):
    cond_min_detect = strategy_self.rsi_minimo  # ← SIEMPRE False
    
    cond_rsi_giro = cond_min_detect and cond_crossover_confirm
                    # False AND anything = False → NUNCA se activa

    cond_rsi_pure_force = (rsi_ind[-1] > rsi_strength_threshold)
                          # Esta SÍ puede activarse
```

---

## Problema #2: Confusión de Variables

### Estado de Clase vs Estado Dinámico

```
En estrategia_system.py:
┌─────────────────────────────────────────────────┐
│ Atributos de CLASE (siempre False):            │
├─────────────────────────────────────────────────┤
│ rsi_minimo = False            # Placeholder     │
│ rsi_maximo = False            # Placeholder     │
│ rsi_ascendente = False        # Placeholder     │
├─────────────────────────────────────────────────┤
│ Atributos de INSTANCIA (calculados cada barra) │
├─────────────────────────────────────────────────┤
│ self.rsi_minimo_STATE = False     # Init en init()
│ self.rsi_maximo_STATE = False     # Init en init()
│ self.rsi_ascendente_STATE = False # Init en init()
│ self.rsi_descendente_STATE = False # Init en init()
└─────────────────────────────────────────────────┘
```

### ¿Cuál usa el Filtro RSI?

```python
# Filtro_RSI.py línea 76:
cond_min_detect = strategy_self.rsi_minimo  # ← USA: rsi_minimo (clase, SIEMPRE False)

# Debería usar:
cond_min_detect = strategy_self.rsi_minimo_STATE  # ← ESTADO calculado
```

---

## Problema #3: Lógica Defectudosa de Cruce (Threshold)

### En estrategia_system.py línea 274:

```python
if self.rsi and self.rsi_period:
    self.rsi_ind = self.I(ta.momentum.rsi, self.data.Close.s, int(self.rsi_period), name='RSI')
    self.rsi_threshold_ind = self.I(
        lambda x: pd.Series([float(self.rsi_low_level)] * len(x), index=x.index), 
        self.data.Close.s, name='RSI_Threshold'
    )
```

### Problema:
```
1. rsi_threshold_ind es una LÍNEA CONSTANTE (siempre 30)
2. Se pasa self.data.Close.s como argumento (pero lambda no lo usa)
3. El crossover compara:
   - RSI dinámico (oscila entre 0-100)
   - Threshold estático (siempre 30)

Esto DEBERÍA funcionar pero hay un problema:

crossover(strategy_self.rsi_ind, strategy_self.rsi_threshold_ind)

¿Pero qué si rsi_threshold_ind es None?
→ Causa AttributeError
→ La función devuelve False silenciosamente
```

---

## Problema #4: Lógica de Compra SIN Activación Correcta

### Flujo actual (INEFECTIVO):

```python
# En Filtro_RSI.py, check_rsi_buy_signal()

if strategy_self.rsi and strategy_self.rsi_ind is not None:
    
    if hasattr(strategy_self, 'rsi_threshold_ind') and strategy_self.rsi_threshold_ind is not None:
        
        # Paso 1: Detectar mínimo (PROBLEMA)
        cond_min_detect = strategy_self.rsi_minimo  # ← SIEMPRE False
        
        # Paso 2: Detectar cruce (Podría funcionar)
        cond_crossover_confirm = crossover(rsi_ind, threshold_ind)
        
        # Paso 3: Combinar (NUNCA se activa)
        cond_rsi_giro = cond_min_detect and cond_crossover_confirm
                        # False and anything = False
        
        # Paso 4: "Fuerza Pura" (ÚNICA QUE FUNCIONA)
        cond_rsi_pure_force = (rsi_ind[-1] > rsi_strength_threshold)
                              # Esto SÍ puede ser True
```

### Resultado:
```
✓ RSI > 50 (threshold) → Puede generar compra
✗ RSI cruza 30 desde abajo → NO funciona (porque cond_min_detect es False)
```

---

## Problema #5: Configuración Web NO Tiene Parámetros RSI Booleanos

### Lo que la web DEBERÍA proporcionar:

```python
# En _tab_rsi.html (o similar), debería haber:

<input type="checkbox" name="rsi_minimo" value="true">
<label>Compra cuando RSI toca mínimo</label>

<input type="checkbox" name="rsi_maximo" value="true">
<label>⚠️ Rechaza compra cuando RSI toca máximo</label>

<input type="checkbox" name="rsi_ascendente" value="true">
<label>Compra cuando RSI está aumentando</label>

<input type="checkbox" name="rsi_descendente" value="true">
<label>⚠️ Rechaza compra cuando RSI baja</label>
```

---

## RESUMEN DE PROBLEMAS

```
┌────────────────────────────────────────────────────────────────┐
│ PROBLEMA                    │ SEVERIDAD │ IMPACTO             │
├─────────────────────────────┼───────────┼─────────────────────┤
│ #1: Parámetros faltantes    │ 🔴 CRÍTICA│ RSI NO funciona     │
│     (rsi_minimo etc)        │           │ en absoluto          │
├─────────────────────────────┼───────────┼─────────────────────┤
│ #2: Variable equivocada     │ 🔴 CRÍTICA│ Siempre False       │
│     (clase vs STATE)        │           │                     │
├─────────────────────────────┼───────────┼─────────────────────┤
│ #3: Threshold defectudoso   │ 🟠 ALTO   │ Cruce parcialmente  │
│     (lambda incorrecto)     │           │ no funciona         │
├─────────────────────────────┼───────────┼─────────────────────┤
│ #4: Lógica AND siempre False│ 🔴 CRÍTICA│ Giro desde SV nunca │
│     (depends on #1+#2)      │           │ se activa           │
├─────────────────────────────┼───────────┼─────────────────────┤
│ #5: Web sin UI para RSI flags│ 🔴 CRÍTICA│ Usuario no puede    │
│     (checkboxes)            │           │ configurar          │
└────────────────────────────────────────────────────────────────┘
```

---

## SOLUCIÓN NECESARIA (Para que funcione)

### Opción A: Agregar parámetros booleanos a web (Recomendado)

1. En `scenarios/BacktestWeb/configuracion.py`:
```python
# RSI Flags (Señales y Deniegos)
System.rsi_minimo = get_param('rsi_minimo', False, bool)
System.rsi_maximo = get_param('rsi_maximo', False, bool)
System.rsi_ascendente = get_param('rsi_ascendente', False, bool)
System.rsi_descendente = get_param('rsi_descendente', False, bool)
```

2. En formulario web (HTML):
```html
<label><input type="checkbox" name="rsi_minimo"> Compra si RSI toca mínimo</label>
<label><input type="checkbox" name="rsi_maximo"> Rechaza si RSI está en pico</label>
<label><input type="checkbox" name="rsi_ascendente"> Compra si RSI sube</label>
<label><input type="checkbox" name="rsi_descendente"> Rechaza si RSI baja</label>
```

### Opción B: Simplificar Filtro_RSI.py (Más rápido)

Cambiar lógica para usar solo:
- `rsi_strength_threshold` (ÚNICO parámetro que funciona ahora)
- `rsi_low_level` para detección de sobreventa
- `rsi_high_level` para detección de sobrecompra

```
# Simplificado (sin dependencias de parámetros faltantes)
if strategy_self.rsi_ind[-1] > strategy_self.rsi_strength_threshold:
    → COMPRA (fuerza pura)
    
# ADEMÁS: Si está en sobreventa
if strategy_self.rsi_ind[-1] < strategy_self.rsi_low_level:
    → Detectar mínimo (usar rsi_minimo_STATE)
    → Si cruza arriba del low_level, COMPRA por giro
```

---

## PRÓXIMOS PASOS

```
1. ¿Quieres usar Opción A (completa) o Opción B (rápida)?
2. Necesito corregir:
   - Filtro_RSI.py
   - estrategia_system.py
   - configuracion.py
   - formulario web

3. Después: Testear con datos reales
```

¿Por cuál opción prefieres ir?

````
