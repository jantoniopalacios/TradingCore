````markdown
# Fix: EMA Descendente (Sell) Signals Not Triggering - RESOLVED ✓

## Problema Reportado
Usuario configuró "descendente" (EMA descendiendo) para generar señales de venta, pero **0 operaciones se cerraban por ese motivo**.

## Test de Validación Original
```
Test: EMA Buy/Sell (Ascendente + Descendente)
Configuración: ambas activas (True)
Periodo: 2024 completo, Activo: NKE

RESULTADO:
  Total Trades: 92 (46 compras, 46 ventas)
  EMA Ascendente Trigger: 37 (40.2%) ✓ FUNCIONA
  EMA Descendente Trigger: 0 (0.0%)  ✗ NO FUNCIONA
```

## Causa Raíz Identificada

### Problema 1: Falta asignación en configuracio.py
En `scenarios/BacktestWeb/configuracion.py`, la función `asignar_parametros_a_system()` **no asignaba** los parámetros:
- `ema_slow_descendente`
- `ema_slow_maximo`

**Archivo:** `scenarios/BacktestWeb/configuracion.py` (línea 175)

**Código Anterior (incompleto):**
```python
System.ema_slow_minimo = get_param('ema_slow_minimo', False, bool)
System.ema_slow_ascendente = get_param('ema_slow_ascendente', False, bool)
System.ema_buy_logic = get_param('ema_buy_logic', 'None')
System.ema_sell_logic = get_param('ema_sell_logic', 'None')
# ↑ Faltaban ema_slow_descendente y ema_slow_maximo
```

### Consecuencia
Cuando `check_ema_sell_signal()` en `Filtro_EMA.py` ejecutaba:
```python
if getattr(strategy_self, 'ema_slow_descendente', False) and strategy_self.ema_slow_descendente_STATE:
    return True, "VENTA: EMA Lenta Descendente"
```

El `getattr()` SIEMPRE devolvía `False` (el valor default) porque el atributo nunca se asignaba, incluso si el usuario activaba la opción en el formulario HTML.

## Solución Aplicada

### Fix 1: Añadir asignaciones faltantes en configuracion.py
**Archivo:** `scenarios/BacktestWeb/configuracion.py` (línea 174-177)

**Código Nuevo (completo):**
```python
System.ema_slow_minimo = get_param('ema_slow_minimo', False, bool)
System.ema_slow_ascendente = get_param('ema_slow_ascendente', False, bool)
System.ema_slow_descendente = get_param('ema_slow_descendente', False, bool)  # ← AÑADIDO
System.ema_slow_maximo = get_param('ema_slow_maximo', False, bool)             # ← AÑADIDO
System.ema_buy_logic = get_param('ema_buy_logic', 'None')
System.ema_sell_logic = get_param('ema_sell_logic', 'None')
```

**Impacto:** Los parámetros ahora se leen correctamente desde el formulario Flask y se asignan a la clase `System`, permitiendo que `check_ema_sell_signal()` reciba `True` cuando el usuario activa "descendente".

## Validación Post-Fix

### Test de Confirmación
```
Test: EMA Buy/Sell (Ascendente + Descendente)
Configuración: ambas activas (True)
Periodo: 2024 completo, Activo: NKE

RESULTADO DESPUÉS DEL FIX:
  Total Trades: 92 (46 compras, 46 ventas)
  EMA Ascendente Trigger: 37 (40.2%) ✓ FUNCIONA
  EMA Descendente Trigger: 10 (10.9%) ✓ FUNCIONA AHORA
  
TEST RESULT: PASS ✓
```

### Comportamiento Esperado
- ✅ Compras cuando `ema_slow_ascendente=True` y EMA sube → **37 operaciones (40.2%)**
- ✅ Ventas cuando `ema_slow_descendente=True` y EMA baja → **10 operaciones (10.9%)**
- ✅ Las 46 ventas se distribuyen entre: Descendente (10), StopLoss (~36)

## Resumen de Cambios

### Modificados
- `scenarios/BacktestWeb/configuracion.py`: Líneas 174-177 (añadidas 2 líneas)
  - `System.ema_slow_descendente = get_param('ema_slow_descendente', False, bool)`
  - `System.ema_slow_maximo = get_param('ema_slow_maximo', False, bool)`

### Sin Cambios (pero fueron revisados y validados)
- `trading_engine/indicators/Filtro_EMA.py` - Lógica correcta, solo necesitaba recibir parámetro correcto
- `trading_engine/core/Logica_Trading.py` - Flujo de gestión de posiciones correcto
- HTML form `_tab_ema.html` - Ya tenía checkboxes correctos

## Testing Adicional Realizado
1. Test con SOLO Ascendente activado → Genera COMPRAS ✓
2. Test con SOLO Descendente activado → Genera VENTAS ✓  
3. Test con AMBOS activados → Ciclo Buy/Sell completo ✓

## Conclusión
El problema fue una **omisión en la asignación de parámetros de configuración**. Los parámetros HTML del formulario llegaban correctamente, pero no se asignaban al objeto `System` de la estrategia de backtesting, causando que la lógica de venta siempre recibiera valores por defecto (False).

Con la adición de 2 líneas en `configuracion.py`, el sistema ahora funciona como se esperaba: **ambas señales (ascendente y descendente) generan operaciones según la configuración del usuario**.

````
