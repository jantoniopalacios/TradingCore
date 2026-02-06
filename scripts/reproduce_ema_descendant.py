#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run a short backtest for NKE with ema_slow_descendente enabled to trace sell descriptions.
"""

from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_multi_symbol_backtest
from scenarios.BacktestWeb.estrategia_system import System
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('reproduce_ema_descendant')

def main():
    csv_path = PROJECT_ROOT / 'Data_files' / 'NKE_1d_MAX.csv'
    if not csv_path.exists():
        print('CSV not found:', csv_path)
        return

    df = pd.read_csv(csv_path)
    # Keep last 400 rows for speed
    if len(df) > 400:
        df = df.tail(400).copy()

    # Ensure required columns
    for c in ['Open','High','Low','Close','Volume']:
        if c not in df.columns:
            print('Missing column in CSV:', c)
            return

    # Ensure datetime index expected by backtesting.py
    date_col = None
    for candidate in ['Date', 'date', 'Fecha', 'fecha', 'datetime']:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col:
        try:
            df.index = pd.to_datetime(df[date_col])
        except Exception:
            df.index = pd.RangeIndex(start=0, stop=len(df), step=1)
    else:
        # If no date column, create a datetime index from a range (avoids .strftime errors)
        df.index = pd.date_range(end=pd.Timestamp.today(), periods=len(df))

    for opt in ['Margen de seguridad', 'LTM EPS']:
        if opt not in df.columns:
            df[opt] = 0

    stocks_data = {'NKE': df}

    # Configure System class flags
    System.ema_slow_period = 50
    System.ema_fast_period = 20
    System.ema_cruce_signal = False
    System.ema_slow_minimo = False
    System.ema_slow_maximo = False
    System.ema_slow_ascendente = False
    System.ema_slow_descendente = True

    params = {
        'cash': 10000,
        'commission': 0.0,
        'stoploss_percentage_below_close': 0.05,
    }

    print('Running short backtest for NKE with ema_slow_descendente=True...')
    res_df, trades_df, bts = run_multi_symbol_backtest(stocks_data, System, params, ['NKE'], 20, logger)

    print('\nResults summary:')
    print(res_df)
    print('\nTrades log (DataFrame):')
    print(trades_df)
    print('\nTrades DataFrame columns:', list(trades_df.columns))

    # Search for 'descendente' in any string column
    found = False
    for col in trades_df.columns:
        if trades_df[col].dtype == object:
            mask = trades_df[col].astype(str).str.lower().str.contains('descendente')
            if mask.any():
                print(f"\nRows with 'descendente' in column {col}:")
                print(trades_df[mask])
                found = True
    if not found:
        print('\nNo occurrences of "descendente" found in trades_df.')

    # Also print detailed trades_list from strategy instance if available
    bt_obj = bts.get('NKE')
    if bt_obj is not None:
        try:
            strat = bt_obj._strategy
            trades_list = getattr(strat, 'trades_list', [])
            print('\nTrades list entries:')
            for t in trades_list:
                print(t)
        except Exception as e:
            print('Could not extract trades_list from backtest object:', e)

if __name__ == '__main__':
    main()
