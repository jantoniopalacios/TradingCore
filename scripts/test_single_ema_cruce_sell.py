#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run a single backtest for a symbol with explicit System params to validate EMA cross sell.
"""
import sys
from pathlib import Path
import pandas as pd
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System
import logging

def run(symbol='NKE', interval='1wk', ema_fast=5, ema_slow=50, stoploss_pct=0.25):
    csv_candidate = PROJECT_ROOT / 'Data_files' / f"{symbol}_1wk_MAX.csv"
    if not csv_candidate.exists():
        files = list((PROJECT_ROOT / 'Data_files').glob(f"{symbol}*"))
        csv_candidate = files[0] if files else None
    if not csv_candidate or not csv_candidate.exists():
        print('CSV not found for', symbol); return

    df = pd.read_csv(csv_candidate)
    # set datetime index
    date_col = None
    for c in ['Date','date','Fecha','fecha','datetime']:
        if c in df.columns:
            date_col = c; break
    if date_col:
        df.index = pd.to_datetime(df[date_col])
    else:
        df.index = pd.date_range(end=pd.Timestamp.today(), periods=len(df))

    # ensure OHLCV
    for c in ['Open','High','Low','Close','Volume']:
        if c not in df.columns:
            print('Missing', c); return

    # Set System attributes
    System.ema_cruce_signal = True
    System.ema_fast_period = ema_fast
    System.ema_slow_period = ema_slow
    # ensure sell by cross is enabled via ema_cruce_signal; do not enable ema_slow_descendente or maximo
    System.ema_slow_descendente = False
    System.ema_slow_maximo = False

    System.stoploss_percentage_below_close = stoploss_pct
    System.cash = 10000
    System.commission = 0.0

    # trim data for speed
    if len(df) > 800:
        df = df.tail(800).copy()

    print(f"Running backtest {symbol} {interval} EMA {ema_fast}/{ema_slow} stop={stoploss_pct}")
    logger = logging.getLogger('test_single_ema')
    stats, trades_log, bt_obj = run_backtest_for_symbol(df[['Open','High','Low','Close','Volume']], System, symbol, System.cash, System.commission, System.stoploss_percentage_below_close, logger)

    trades_df = pd.DataFrame(trades_log)
    print('\nTrades:')
    print(trades_df[['Tipo','Descripcion','Precio_Entrada','Precio_Salida']].head(50))
    if 'Descripcion' in trades_df.columns:
        mask = trades_df['Descripcion'].astype(str).str.lower().str.contains('cross')
        print('\nSells with "cross" in description:', int(mask.sum()))

if __name__ == '__main__':
    run()
