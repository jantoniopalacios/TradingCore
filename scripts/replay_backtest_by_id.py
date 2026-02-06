#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproduce a historical ResultadoBacktest by ID using its params_tecnicos
and re-run the backtest to compare trade descriptions (looking for 'Descendente').
"""

import sys
from pathlib import Path
import json
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('replay_backtest')

def main(backtest_id=888):
    try:
        from scenarios.BacktestWeb.app import create_app
        from scenarios.BacktestWeb.database import ResultadoBacktest, Usuario
        from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
        from scenarios.BacktestWeb.estrategia_system import System
    except Exception as e:
        print('[✗] Error importing app/models:', e)
        return

    app = create_app(user_mode='admin')
    with app.app_context():
        bt = ResultadoBacktest.query.get(backtest_id)
        if not bt:
            print(f'[✗] ResultadoBacktest id={backtest_id} no encontrado')
            return

        print(f"[✓] Cargando backtest id={bt.id} | símbolo={getattr(bt,'symbol',None)} | fecha={getattr(bt,'fecha_ejecucion',None)}")

        # Load params_tecnicos
        raw = getattr(bt, 'params_tecnicos', None)
        if not raw:
            print('[!] params_tecnicos vacío')
            params = {}
        else:
            try:
                params = json.loads(raw) if isinstance(raw, str) else raw
            except Exception as e:
                print('[✗] Error parsing params_tecnicos:', e)
                params = {}

        print('\nParametros (excerpt):')
        for k in list(params.keys())[:20]:
            print(' -', k, ':', params[k])

        # Determine symbol and CSV path
        symbol = getattr(bt, 'symbol', None) or params.get('symbol') or 'NKE'
        csv_candidate = PROJECT_ROOT / 'Data_files' / f"{symbol}_1d_MAX.csv"
        if not csv_candidate.exists():
            # try to find any file starting with symbol
            files = list((PROJECT_ROOT / 'Data_files').glob(f"{symbol}*"))
            csv_candidate = files[0] if files else None

        if not csv_candidate or not csv_candidate.exists():
            print('[✗] CSV para símbolo no encontrado:', symbol)
            return

        df = pd.read_csv(csv_candidate)
        # set datetime index if possible
        date_col = None
        for c in ['Date','date','Fecha','fecha','datetime']:
            if c in df.columns:
                date_col = c; break
        if date_col:
            try:
                df.index = pd.to_datetime(df[date_col])
            except Exception:
                df.index = pd.date_range(end=pd.Timestamp.today(), periods=len(df))
        else:
            df.index = pd.date_range(end=pd.Timestamp.today(), periods=len(df))

        # filter by fecha_inicio_datos / fecha_fin_datos if present in bt
        inicio = getattr(bt, 'fecha_inicio_datos', None) or params.get('fecha_inicio_datos')
        fin = getattr(bt, 'fecha_fin_datos', None) or params.get('fecha_fin_datos')
        try:
            if inicio:
                df = df[df.index >= pd.to_datetime(inicio)]
            if fin:
                df = df[df.index <= pd.to_datetime(fin)]
        except Exception:
            pass

        # Ensure required columns
        for c in ['Open','High','Low','Close','Volume']:
            if c not in df.columns:
                print('[✗] Missing column in CSV:', c)
                return

        # Prepare System class attributes from params
        # Only set simple attributes; complex nested configs may require manual mapping
        for k, v in params.items():
            try:
                # sanitize boolean-like strings
                if isinstance(v, str) and v.lower() in ('true','false'):
                    val = True if v.lower()=='true' else False
                else:
                    val = v
                setattr(System, k, val)
            except Exception:
                # ignore attributes that can't be set
                pass

        # Fallback sensible defaults if not provided
        cash = params.get('cash', 10000)
        commission = params.get('commission', 0.0)
        stoploss = params.get('stoploss_percentage_below_close', params.get('stoploss_percentage', 0.05))

        # Truncate data for speed (use same window as original if available)
        if len(df) > 800:
            df = df.tail(800).copy()

        from trading_engine.core.Backtest_Runner import run_backtest_for_symbol

        print('\nRe-ejecutando backtest... (esto puede tardar)')
        try:
            stats, trades_log, bt_obj = run_backtest_for_symbol(df[['Open','High','Low','Close','Volume']], System, symbol, cash, commission, stoploss, logger)
        except Exception as e:
            print('[✗] Error during run_backtest_for_symbol:', e)
            import traceback; traceback.print_exc()
            return

        trades_df = pd.DataFrame(trades_log)
        print('\nTrades DataFrame (head):')
        print(trades_df.head(30))

        # Search for 'descendente' in descriptions
        found = False
        if not trades_df.empty and 'Descripcion' in trades_df.columns:
            mask = trades_df['Descripcion'].astype(str).str.lower().str.contains('descendente')
            count = int(mask.sum())
            print(f"\nVentas con 'descendente' en descripcion: {count}")
            if count > 0:
                print(trades_df[mask][['Tipo','Descripcion']])
                found = True

        # Also inspect strategy trades_list if available
        try:
            strat = bt_obj._strategy
            trades_list = getattr(strat, 'trades_list', [])
            if trades_list:
                print('\nTrades_list entries sample:')
                for t in trades_list[:20]:
                    print(t)
        except Exception:
            pass

        if not found:
            print('\nNo se encontraron ventas etiquetadas con "Descendente" en la re-ejecución.')

if __name__ == '__main__':
    main(888)
