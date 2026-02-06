#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscar backtests recientes donde `ema_slow_descendente` esté activado
y verificar si aparecen ventas etiquetadas como "Descendente".
"""

import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def main(limit=500):
    try:
        from scenarios.BacktestWeb.app import create_app
        from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario
    except Exception as e:
        print(f"[✗] Error importing app or models: {e}")
        return

    app = create_app(user_mode='admin')
    with app.app_context():
        print(f"[*] Buscando hasta {limit} backtests más recientes con ema_slow_descendente=True...")
        cand = ResultadoBacktest.query.order_by(ResultadoBacktest.id.desc()).limit(limit).all()
        matches = []

        for bt in cand:
            raw = getattr(bt, 'params_tecnicos', None)
            if not raw:
                continue
            try:
                cfg = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue

            if cfg.get('ema_slow_descendente', False):
                # get usuario
                usuario = None
                try:
                    usuario = Usuario.query.get(bt.usuario_id)
                except Exception:
                    usuario = None

                trades = Trade.query.filter_by(backtest_id=bt.id).all()
                ventas = [t for t in trades if (t.tipo or '').upper() == 'VENTA']
                ema_desc_sells = sum(1 for t in ventas if 'descendente' in ((t.descripcion or '').lower()))

                matches.append({
                    'id': bt.id,
                    'symbol': getattr(bt, 'symbol', None),
                    'fecha': getattr(bt, 'fecha_ejecucion', None),
                    'usuario_id': getattr(bt, 'usuario_id', None),
                    'usuario': getattr(usuario, 'username', None) if usuario else None,
                    'total_trades': len(trades),
                    'total_sells': len(ventas),
                    'ema_desc_sells': ema_desc_sells,
                })

        if not matches:
            print("[✓] No se encontraron backtests con ema_slow_descendente=True en el rango buscado.")
            return

        print(f"[✓] Encontrados {len(matches)} backtests con ema_slow_descendente=True:\n")
        for m in matches:
            print(f"- ID: {m['id']} | Usuario: {m['usuario'] or m['usuario_id']} | Símbolo: {m['symbol']} | Fecha: {m['fecha']}")
            print(f"  Trades: {m['total_trades']} | Sells: {m['total_sells']} | Sells con 'Descendente' en descripción: {m['ema_desc_sells']}")
            if m['ema_desc_sells'] > 0:
                print("  → EMA Descendente: APARECE en las ventas ✅")
            else:
                print("  → EMA Descendente: NO aparece en las ventas ❌")
            print("")

if __name__ == '__main__':
    main()
