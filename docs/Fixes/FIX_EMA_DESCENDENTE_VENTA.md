# Fix EMA Descendente: Señales de venta no disparaban

## Problema reportado
Con `ema_slow_descendente=True`, no se cerraban operaciones por señal descendente.

## Validacion inicial
```
Test: EMA Buy/Sell (Ascendente + Descendente)
Configuración: ambas activas (True)
Periodo: 2024 completo, Activo: NKE

RESULTADO:
  Total Trades: 92 (46 compras, 46 ventas)
  EMA Ascendente Trigger: 37 (40.2%) ✓ FUNCIONA
  EMA Descendente Trigger: 0 (0.0%)  ✗ NO FUNCIONA
```

## Causa raiz

En `scenarios/BacktestWeb/configuracion.py`, la funcion `asignar_parametros_a_system()` no asignaba:
- `ema_slow_descendente`
- `ema_slow_maximo`

Archivo: `scenarios/BacktestWeb/configuracion.py`.

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

## Solucion aplicada

Se añadieron asignaciones faltantes en `scenarios/BacktestWeb/configuracion.py`.

**Código Nuevo (completo):**
```python
System.ema_slow_minimo = get_param('ema_slow_minimo', False, bool)
System.ema_slow_ascendente = get_param('ema_slow_ascendente', False, bool)
System.ema_slow_descendente = get_param('ema_slow_descendente', False, bool)  # ← AÑADIDO
System.ema_slow_maximo = get_param('ema_slow_maximo', False, bool)             # ← AÑADIDO
System.ema_buy_logic = get_param('ema_buy_logic', 'None')
System.ema_sell_logic = get_param('ema_sell_logic', 'None')
```

Impacto: los parametros del formulario Flask llegan correctamente a `System` y `check_ema_sell_signal()` puede evaluar la condicion real.

## Validacion post-fix

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

### Comportamiento esperado
- ✅ Compras cuando `ema_slow_ascendente=True` y EMA sube → **37 operaciones (40.2%)**
- ✅ Ventas cuando `ema_slow_descendente=True` y EMA baja → **10 operaciones (10.9%)**
- ✅ Las 46 ventas se distribuyen entre: Descendente (10), StopLoss (~36)

## Resumen de cambios

### Modificado
- `scenarios/BacktestWeb/configuracion.py`: Líneas 174-177 (añadidas 2 líneas)
  - `System.ema_slow_descendente = get_param('ema_slow_descendente', False, bool)`
  - `System.ema_slow_maximo = get_param('ema_slow_maximo', False, bool)`

### Revisado sin cambios
- `trading_engine/indicators/Filtro_EMA.py` - Lógica correcta, solo necesitaba recibir parámetro correcto
- `trading_engine/core/Logica_Trading.py` - Flujo de gestión de posiciones correcto
- HTML form `_tab_ema.html` - Ya tenía checkboxes correctos

## Testing adicional
1. Test con SOLO Ascendente activado → Genera COMPRAS ✓
2. Test con SOLO Descendente activado → Genera VENTAS ✓  
3. Test con AMBOS activados → Ciclo Buy/Sell completo ✓

## Conclusión
El fallo fue una omision de mapeo de parametros de configuracion. Tras añadir las asignaciones en `configuracion.py`, las señales de venta descendente funcionan segun configuracion del usuario.
