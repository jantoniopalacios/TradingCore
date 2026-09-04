#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test NKE 1wk with exact date range and params"""
import sys
from pathlib import Path
import pandas as pd
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System

csv_file = PROJECT_ROOT / 'Data_files' / 'NKE_1wk_MAX.csv'
if not csv_file.exists():
    print(f'CSV not found: {csv_file}')
    sys.exit(1)

df = pd.read_csv(csv_file)
# Set datetime index
date_col = None
for c in ['Date','date','Fecha','fecha','datetime']:
    if c in df.columns:
        date_col = c
        break
if date_col:
    df.index = pd.to_datetime(df[date_col])
else:
    df.index = pd.date_range(end=pd.Timestamp.today(), periods=len(df))

# Filter date range: 24/1/2000 to 24/1/2026
start_date = pd.to_datetime('2000-01-24')
end_date = pd.to_datetime('2026-01-24')
df = df[(df.index >= start_date) & (df.index <= end_date)]

print(f'Data range: {df.index[0]} to {df.index[-1]}')
print(f'Total bars: {len(df)}')

# Set System params
System.ema_cruce_signal = True  # EMA cross enabled
System.ema_fast_period = 5
System.ema_slow_period = 50
System.ema_slow_descendente = False
System.ema_slow_maximo = False
System.ema_slow_minimo = False
System.ema_slow_ascendente = False

System.rsi = False  # RSI disabled
System.macd = False
System.stoch_fast = False
System.stoch_mid = False
System.stoch_slow = False
System.bb_active = False

System.stoploss_percentage_below_close = 0.25
System.cash = 10000
System.commission = 0.0

logger = logging.getLogger('test_nke')
stats, trades_log, bt_obj = run_backtest_for_symbol(
    df[['Open','High','Low','Close','Volume']], 
    System, 
    'NKE', 
    System.cash, 
    System.commission, 
    System.stoploss_percentage_below_close, 
    logger
)

trades_df = pd.DataFrame(trades_log)
print('\n=== RESULTADOS ===')
print(f'Total operaciones: {len(trades_df)}')

if len(trades_df) > 0:
    compras = len(trades_df[trades_df['Tipo'] == 'COMPRA'])
    ventas = len(trades_df[trades_df['Tipo'] == 'VENTA'])
    print(f'Compras: {compras}')
    print(f'Ventas: {ventas}')
    
    if 'Descripcion' in trades_df.columns:
        ventas_df = trades_df[trades_df['Tipo'] == 'VENTA']
        stoploss = len(ventas_df[ventas_df['Descripcion'].astype(str).str.contains('StopLoss', case=False)])
        crossdown = len(ventas_df[ventas_df['Descripcion'].astype(str).str.contains('Cross', case=False)])
        other = len(ventas_df) - stoploss - crossdown
        
        print(f'\nDesglose ventas:')
        print(f'  - Por StopLoss: {stoploss}')
        print(f'  - Por Cruce descendente: {crossdown}')
        print(f'  - Otras: {other}')

print('\nTrades sample:')
print(trades_df[['Tipo','Descripcion','Precio_Entrada','Precio_Salida']].head(20))
