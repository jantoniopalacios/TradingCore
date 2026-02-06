#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch re-run of ResultadoBacktest entries whose `params_tecnicos` contain
`ema_slow_descendente=True`. Produces a CSV summary with counts and whether
re-execution produced sales labeled 'descendente'.

Usage: python scripts/batch_replay_by_ids.py [limit]
"""
import sys
from pathlib import Path
import json
import csv
import time
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main(limit=1000, out='results_ema_descendants_summary.csv'):
    try:
        from scenarios.BacktestWeb.app import create_app
        from scenarios.BacktestWeb.database import ResultadoBacktest, Usuario
        from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
        from scenarios.BacktestWeb.estrategia_system import System
    except Exception as e:
        print('[✗] Import error:', e)
        return

    app = create_app(user_mode='admin')
    logger = logging.getLogger('batch_replay')
    results = []
    started = time.time()
    with app.app_context():
        cand = ResultadoBacktest.query.order_by(ResultadoBacktest.id.desc()).limit(limit).all()
        print(f"[*] Candidatos cargados: {len(cand)}")

        for bt in cand:
            raw = getattr(bt, 'params_tecnicos', None)
            if not raw:
                continue

            try:
                cfg = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue

            if not cfg.get('ema_slow_descendente', False):
                continue

            row = {
                'id': bt.id,
                'symbol': getattr(bt, 'symbol', None) or cfg.get('symbol'),
                'usuario_id': getattr(bt, 'usuario_id', None),
                'fecha': getattr(bt, 'fecha_ejecucion', None),
                'orig_total_trades': None,
                'orig_total_sells': None,
                'orig_ema_desc_sells': None,
                'replay_total_trades': None,
                'replay_total_sells': None,
                'replay_ema_desc_sells': None,
                'error': None,
            }

            # original counts if available
            try:
                from scenarios.BacktestWeb.database import Trade
                trades = Trade.query.filter_by(backtest_id=bt.id).all()
                ventas = [t for t in trades if (t.tipo or '').upper() == 'VENTA']
                ema_desc_sells = sum(1 for t in ventas if 'descendente' in ((t.descripcion or '').lower()))
                row['orig_total_trades'] = len(trades)
                row['orig_total_sells'] = len(ventas)
                row['orig_ema_desc_sells'] = ema_desc_sells
            except Exception:
                pass

            # do replay (lightweight, tolerant)
            try:
                import pandas as pd
                symbol = row['symbol'] or 'NKE'
                csv_candidate = PROJECT_ROOT / 'Data_files' / f"{symbol}_1d_MAX.csv"
                if not csv_candidate.exists():
                    files = list((PROJECT_ROOT / 'Data_files').glob(f"{symbol}*"))
                    csv_candidate = files[0] if files else None
                if not csv_candidate or not csv_candidate.exists():
                    row['error'] = 'CSV not found'
                    results.append(row)
                    print(f"[!] {bt.id} - CSV not found for {symbol}")
                    continue

                df = pd.read_csv(csv_candidate)
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

                for k, v in cfg.items():
                    try:
                        if isinstance(v, str) and v.lower() in ('true','false'):
                            val = True if v.lower()=='true' else False
                        else:
                            val = v
                        setattr(System, k, val)
                    except Exception:
                        pass

                cash = cfg.get('cash', 10000)
                commission = cfg.get('commission', 0.0)
                stoploss = cfg.get('stoploss_percentage_below_close', cfg.get('stoploss_percentage', 0.05))

                if len(df) > 800:
                    df = df.tail(800).copy()

                stats, trades_log, bt_obj = run_backtest_for_symbol(df[['Open','High','Low','Close','Volume']], System, symbol, cash, commission, stoploss, logger)

                trades_df = pd.DataFrame(trades_log)
                total_trades = len(trades_df)
                total_sells = int((trades_df['Tipo'].astype(str).str.upper()=='VENTA').sum()) if 'Tipo' in trades_df.columns else None
                replay_ema_desc = 0
                if not trades_df.empty and 'Descripcion' in trades_df.columns:
                    mask = trades_df['Descripcion'].astype(str).str.lower().str.contains('descendente')
                    replay_ema_desc = int(mask.sum())

                row['replay_total_trades'] = total_trades
                row['replay_total_sells'] = total_sells
                row['replay_ema_desc_sells'] = replay_ema_desc
                results.append(row)
                print(f"[+] Replayed {bt.id} ({symbol}): trades={total_trades} desc_sells={replay_ema_desc}")

            except Exception as e:
                row['error'] = str(e)
                results.append(row)
                print(f"[X] Error replaying {bt.id}: {e}")

            # flush partial results each iteration
            try:
                with open(out, 'w', newline='', encoding='utf-8') as fh:
                    writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
                    writer.writeheader()
                    for r in results:
                        writer.writerow(r)
            except Exception:
                pass

    duration = time.time() - started
    print(f"[*] Batch completed in {duration:.1f}s. Results: {len(results)} rows. CSV: {out}")

if __name__ == '__main__':
    arg = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    main(arg)
