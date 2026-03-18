Scripts folder map (TradingCore)
================================

Objective
---------
Keep scripts discoverable and avoid a flat folder with too many one-off files.
Operational scripts stay in scripts/ root. Less frequent analysis/debug/testing
scripts are grouped into subfolders.

Current structure
-----------------

scripts/ (root, operational)
- audit_stops_zts.py              -> Audita coherencia de trailing stop por trade.
- audit_stops_combinations.py     -> Audita combinaciones (Trailing/BE/Swing/RSI) y fugas de fuente.
- compare_trailing_model.py       -> A/B Close/Close vs High/Close.
- sweep_rsi_filter.py             -> Barrido manual RSI vs baseline fijo.
- optimize_rsi.py                 -> Optimizacion de RSI con Backtest.optimize().
- apply_config_preset.py          -> Aplica un bloque preset en Usuario.config_actual (DB).
- replay_backtest_by_id.py        -> Re-ejecuta un backtest por ID.
- batch_replay_by_ids.py          -> Re-ejecucion por lote de IDs.
- query_backtest_results.py       -> Consultas de resultados de backtests.
- query_db.py                     -> Utilidades de consulta BD.
- verificar_backtest_web.py       -> Validacion flujo web/backtest.
- validate_rsi_complete.py        -> Validacion completa RSI.
- validate_macd_complete.py       -> Validacion completa MACD.
- test_backtest_nke.py            -> Test operativo NKE principal.
- test_nke_exact_params.py        -> Reproduccion NKE con parametros exactos.
- test_single_ema_cruce_sell.py   -> Verificacion puntual de salida EMA cruce.

scripts/analysis/
- analyze_backtests_v2.py
- analyze_coherence.py
- analyze_sell_logic.py
- check_sell_logic_simple.py
- find_backtests_with_ema_desc.py
- inspect_last_three.py

scripts/debug/
- debug_test.py
- reproduce_ema_descendant.py
- run_launch_direct.py
- run_rsi_debug.py

scripts/tests/
- test_backtest_nke_debug.py
- test_backtest_nke_final.py
- test_backtest_nke_interactive.py
- test_ema_buy_sell.py
- test_ema_descendente_debug.py
- test_ema_descendente_simple.py
- test_ema_fix_validation.py
- test_ema_simple.py
- test_routes.py
- test_rsi_fix.py
- test_rsi_isolated.py

scripts/presets/
- rsi_minimo.json               -> Preset JSON reutilizable para config_actual.

How to run
----------
From repo root:

  .venv\Scripts\python.exe scripts\optimize_rsi.py --symbols ZTS SAN.MC --mode gate
  .venv\Scripts\python.exe scripts\optimize_rsi.py --symbols ZTS SAN.MC --mode minimo
  .venv\Scripts\python.exe scripts\apply_config_preset.py --preset rsi_minimo --user admin
  .venv\Scripts\python.exe scripts\apply_config_preset.py --list-presets

  .venv\Scripts\python.exe scripts\sweep_rsi_filter.py --symbols ZTS SAN.MC

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
  and rsi_strength_threshold=0 (important: avoids mixing with gate mode).
- If any external automation still points to moved files, update those paths to
  scripts/analysis/, scripts/debug/ or scripts/tests/.
