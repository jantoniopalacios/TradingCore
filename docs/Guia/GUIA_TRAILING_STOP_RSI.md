# Trailing Stop Loss Dinámico por RSI

## ¿Qué hace esta función?
Permite definir dos porcentajes de trailing stop loss dinámico según el valor del RSI:
- Si el RSI es menor o igual al límite configurado, se aplica el primer % de trailing stop loss.
- Si el RSI es mayor que el límite, se aplica el segundo % de trailing stop loss.

## ¿Cómo se configura?
1. Elige un **límite de RSI** (por ejemplo, 40).
2. Define el **% de trailing stop** para cuando el RSI esté por debajo o igual a ese límite.
3. Define el **% de trailing stop** para cuando el RSI esté por encima de ese límite.

## Ejemplo práctico
- Límite RSI: 40
- % Trailing si RSI ≤ 40: 2%
- % Trailing si RSI > 40: 0.8%

**Resultado:**
- Si el RSI está en 35, el trailing SL será 2% bajo el máximo alcanzado.
- Si el RSI está en 55, el trailing SL será 0.8% bajo el máximo alcanzado.

## ¿Por qué es útil?
- Permite proteger más agresivamente cuando el RSI indica debilidad.
- Permite dejar correr la posición cuando el momentum es fuerte.
- El stop loss se recalcula automáticamente en cada vela según el valor actual del RSI.

## Notas
- El trailing stop loss por RSI sustituye al trailing global solo si los parámetros están configurados.
- No requiere intervención manual una vez configurado.

---

Actualizado: 17/02/2026
