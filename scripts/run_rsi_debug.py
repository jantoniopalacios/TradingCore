from pathlib import Path
import sys
project_root = Path(__file__).parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from trading_engine.core.Backtest_Runner import run_multi_symbol_backtest
from trading_engine.core.constants import COLUMNAS_HISTORICO
from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from trading_engine.core.constants import REQUIRED_COLS
from scenarios.BacktestWeb.estrategia_system import System
import logging
logger = logging.getLogger('rsi_debug')
logging.basicConfig(level=logging.DEBUG)

# Load CSV
csv_path = project_root / 'Data_files' / 'NKE_1d_MAX.csv'
if not csv_path.exists():
    print('CSV not found:', csv_path)
    sys.exit(1)

df = pd.read_csv(csv_path)
# Try to normalize columns expected by runner
required = ['Open','High','Low','Close','Volume']
for c in required:
    if c not in df.columns:
        print('Missing column in CSV:', c)
        sys.exit(1)

# Add Symbol column if missing
if 'Symbol' not in df.columns:
    df['Symbol'] = 'NKE'

# Ensure optional columns required by runner exist
for opt in ['Margen de seguridad', 'LTM EPS']:
    if opt not in df.columns:
        df[opt] = 0

stocks_data = {'NKE': df}

# Build config enabling RSI
config_final = {
    'rsi': True,
    'rsi_period': 14,
    'rsi_low_level': 30,
    'rsi_high_level': 70,
    'rsi_strength_threshold': 50,
    'cash': 10000,
    'commission': 0.0,
    'stoploss_percentage_below_close': 0.05,
    'data_files_path': str(project_root / 'Data_files'),
    'graph_dir': str(project_root / 'Backtesting' / 'Graphics'),
}

# Run
print('Running debug backtest for NKE with RSI enabled...')
res_df, trades_df, bts = run_multi_symbol_backtest(stocks_data, System, config_final, ['NKE'], 20, logger)
print('Resultados DF:\n', res_df)
print('Trades DF:\n', trades_df)
