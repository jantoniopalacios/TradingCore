# Registro de Cambios - 2026-02-23

## Corrección: Backtest para símbolos sin columnas fundamentales

- Se modificó la función `run_multi_symbol_backtest` en `trading_engine/core/Backtest_Runner.py`.
- Ahora solo se requieren las columnas fundamentales (`Margen de seguridad`, `LTM EPS`) si el filtro fundamental está activo.
- Para símbolos normales (sin filtro fundamental), solo se requieren las columnas OHLCV: `Open`, `High`, `Low`, `Close`, `Volume`.
- Esto soluciona el problema donde símbolos como SAN.MC eran descartados por "datos insuficientes" aunque el CSV estuviera completo.
- Se realizó un commit de respaldo antes de aplicar el cambio para permitir revertir fácilmente si es necesario.

## Pasos para revertir
- Si algo falla, puedes usar `git log` y `git checkout <commit>` o `git revert` para volver al estado anterior.

---

_Actualizado por GitHub Copilot, 2026-02-23._
