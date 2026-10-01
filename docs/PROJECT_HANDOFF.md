# TradingCore - Handoff de continuidad

## Cómo reanudar
Al retomar el proyecto:
1. leer este documento completo;
2. revisar `docs/ARCHITECTURE.md`;
3. ejecutar `git status`;
4. revisar `git log --oneline -5`;
5. ejecutar `python -m pytest -q`;
6. preservar el stash antiguo del scheduler hasta revisarlo de forma separada.

## Punto de control
- Commit: 836b839
- Suite: 261 passed
- Estado: funcionalmente validado
- Rama: main
- En el momento del handoff, `origin/main` estaba en `cdaff2a` antes del push final.

## Arquitectura fundamental vigente
- `Data_Files/Fundamentals` = caché normalizada global.
- `Backtesting/Run_Results/Global/FullRatio/FR_diario.csv` = valoración fundamental global.
- Lista de símbolos = por usuario.
- Parámetros MoS = por usuario.
- Resultados backtest = por usuario.
- Si la caché global aún no existe, se puede migrar desde FR legacy por usuario de forma determinista y deduplicada.
- Los FR legacy por usuario no se borran automáticamente.

## Flujo de proveedores
- Yahoo = actualización operativa.
- Alpha Vantage = bootstrap histórico.
- Estados: `completed`, `partial`, `quota_blocked`, `no_data`, `error`.
- `completed` no se vuelve a descargar.
- `quota_blocked` es reintentable.
- `partial` y `error` son reintentables.
- `no_data` es terminal hasta reset explícito.
- SAN.MC probado con Yahoo solamente.
- RTX probado con `quota_blocked`.
- AAPL / ABBV / AVGO / GOOG / NVDA completados.

## Dashboard fundamentales
- carga ligera < 1 s.
- sidebar compartido.
- selección de activos.
- actualizar.
- evaluar.
- actualizar y evaluar.
- valoración compartida entre usuarios.
- prueba multiusuario validada: un segundo usuario ve las métricas globales ya calculadas para los símbolos que tenga configurados, sin reevaluar.

## Decisiones importantes
- no recalcular FR por usuario.
- no duplicar caché fundamental.
- MoS calculado globalmente.
- MoS usado por estrategia como filtro configurable.
- Mantener/Desestimar no equivale a orden de trading.
- `reportedDate` obligatorio para uso histórico.
- no inventar fechas.

## Operativa servidor
- PostgreSQL: puerto 5433.
- Flask: puerto 5000.
- launchers de escritorio para arrancar/parar.
- `ALPHA_VANTAGE_KEY` debe estar disponible al proceso web.
- los `.bat` de escritorio pueden contener la clave real, pero están fuera del repo.
- no guardar secretos en Git.
- si una clave real ha sido expuesta fuera de un entorno seguro, rotarla.

## Tests relevantes
- `tests/web/test_fundamentals_dashboard.py`
- `tests/unit/test_fundamentals_full_ratio.py`
- `tests/unit/test_data_download_full_ohlcv.py`
- suite completa: 261 passed.

## Pendientes
1. simplificar botones: dejar `Actualizar y evaluar` como principal.
2. mejorar mensajes singular/plural.
3. explicar mejor `Sí / Parcial / No`.
4. revisar ayudas/tooltips finales.
5. revisar legacy Q0/Q3.
6. decidir retirada de `FR_diario.csv` legacy por usuario.
7. revisar stash antiguo scheduler por separado.

## No tocar sin revisar
- fórmulas PER / LTM / PER M5Y / MoS / Full Ratio.
- anti-look-ahead.
- bootstrap/provider flow.
- stash antiguo scheduler.

## Stash a preservar
- `WIP cambios inesperados rutas scheduler`

## Primera tarea recomendada al retomar
- revisar UX final del dashboard fundamental y simplificar acciones.

## Comandos de reanudación

```powershell
git status
git log --oneline -5
python -m pytest -q