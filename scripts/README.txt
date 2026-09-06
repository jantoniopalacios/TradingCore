Scripts folder map (TradingCore)
================================

Última actualización: 06/09/2026

Objective
---------
Keep scripts discoverable and avoid a flat folder with too many one-off files.
Operational scripts stay in scripts/ root. Analysis, debugging, experiments,
maintenance tasks and scheduler logic are grouped into dedicated subfolders.

Current structure
-----------------

scripts/ (root, operational)
- apply_config_preset.py          -> Aplica un bloque preset en Usuario.config_actual (DB).
- audit_stops_combinations.py     -> Audita combinaciones (Trailing/BE/Swing/RSI) y fugas de fuente.
- audit_stops_zts.py              -> Audita coherencia de trailing stop por trade.
- backfill_trade_signal_context.py -> Completa contexto de señales en registros existentes.
- batch_replay_by_ids.py          -> Re-ejecucion por lote de IDs.
- compare_trailing_model.py       -> A/B Close/Close vs High/Close.
- migrate_add_signal_context.sql  -> Migracion SQL para contexto de señales.
- optimize_rsi.py                 -> Optimizacion de RSI con Backtest.optimize().
- query_backtest_results.py       -> Consultas de resultados de backtests.
- sweep_rsi_filter.py             -> Barrido manual RSI vs baseline fijo.
- validate_macd_complete.py       -> Validacion completa MACD.
- validate_rsi_complete.py        -> Validacion completa RSI.
- verificar_backtest_web.py       -> Validacion del flujo web/backtest.
- verify.ps1                      -> Verificacion baseline del repositorio.

scripts/analysis/
- analyze_backtests_v2.py
- analyze_coherence.py
- analyze_sell_logic.py
- check_sell_logic_simple.py
- find_backtests_with_ema_desc.py
- inspect_last_three.py

scripts/debug/
- check_admin_current_config.py
- compare_trailing_rsi_toggle.py
- debug_test.py
- reproduce_ema_descendant.py
- run_launch_direct.py
- run_rsi_debug.py

scripts/diagnostics/
- check_cargando_route.py
- check_login_flow.py
- check_tandas_html.py
- inspect_blueprint_routes.py
- list_app_routes.py
- list_routes.py

scripts/experiments/
- check_yfinance_symbols.py
- ejecutar_bollinger.py
- inyectar_graficos_test.py
- test_backtest_nke_debug.py
- test_backtest_nke_final.py
- test_backtest_nke_interactive.py
- test_ema_buy_sell.py
- test_ema_descendente_debug.py
- test_ema_descendente_simple.py
- test_ema_fix_validation.py
- test_ema_simple.py
- test_nke_exact_params.py
- test_rsi_fix.py
- test_rsi_isolated.py
- test_single_ema_cruce_sell.py

scripts/maintenance/
- fix_sequences.py
- hacer_backup.ps1
- limpiar_grafico_html.ps1
- Restaurar_db.ps1

scripts/presets/
- rsi_minimo.json
- rsi_minimo_35_sin_ema_gate.json
- rsi_minimo_trailing_agresivo.json
- rsi_minimo_trailing_conservador.json

scripts/scheduler/
- backtest_scheduler.py          -> Scheduler automatico de backtests por usuario.

How to run
----------
From repo root:

  .venv\Scripts\python.exe scripts\optimize_rsi.py --symbols ZTS SAN.MC --mode gate
  .venv\Scripts\python.exe scripts\optimize_rsi.py --symbols ZTS SAN.MC --mode minimo
  .venv\Scripts\python.exe scripts\apply_config_preset.py --preset rsi_minimo --user admin
  .venv\Scripts\python.exe scripts\apply_config_preset.py --list-presets

  .venv\Scripts\python.exe scripts\sweep_rsi_filter.py --symbols ZTS SAN.MC

  .venv\Scripts\python.exe scripts\scheduler\backtest_scheduler.py
  .venv\Scripts\python.exe scripts\scheduler\backtest_scheduler.py --ahora

Outputs from optimize_rsi.py
----------------------------
By default, CSV files are generated under:

  Backtesting\Run_Results\optimizations\

Per symbol execution:
- optimize_rsi_best_<SYMBOL>_<MODE>_<TIMESTAMP>.csv
- optimize_rsi_top_<SYMBOL>_<MODE>_<TIMESTAMP>.csv

Disable export when needed:

  .venv\Scripts\python.exe scripts\optimize_rsi.py --symbols ZTS --mode gate --no-export-csv

Notes
-----
- Baseline agreed for current research: EMA lenta ascendente + trailing 10% + break-even 3%.
- Single-rule RSI setup in app (recommended):
  rsi=True, rsi_minimo=True, rsi_period=10, rsi_low_level=20,
  rsi_ascendente=False, rsi_maximo=False, rsi_descendente=False,
  and rsi_strength_threshold=0.
- Files under scripts/experiments/ are exploratory and are not part of the baseline automated test suite.
- Files under scripts/diagnostics/ and scripts/debug/ are intended for manual diagnosis.
- Maintenance scripts can modify persistent data or database state; review them before execution.
- If any external automation still points to old Utils/ or scripts/tests/ paths, update it to the current location.
