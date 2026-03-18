#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: AnÃ¡lisis simple de Ãºltimas 3 backtests - versiÃ³n Flask ORM
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("\n[*] Analizando Ãºltimas 3 backtests del admin...")
    
    try:
        from scenarios.BacktestWeb.app import create_app
        from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario
        import json
        
        app = create_app(user_mode='admin')
        
        with app.app_context():
            # Buscar admin
            admin = Usuario.query.filter_by(username='admin').first()
            if not admin:
                print("[!] Admin no encontrado")
                return
            
            print(f"[âœ“] Admin encontrado (ID: {admin.id})\n")
            
            # Ãšltimos 3 backtests
            backtests = ResultadoBacktest.query.filter_by(usuario_id=admin.id).order_by(ResultadoBacktest.id.desc()).limit(3).all()
            
            if not backtests:
                print("[!] No hay backtests")
                return
            
            print("="*110)
            print("ANÃLISIS DE LÃ“GICA DE VENTA - ÃšLTIMAS 3 BACKTESTS")
            print("="*110)
            
            for idx, bt in enumerate(backtests, 1):
                print(f"\n[BACKTEST #{idx}]")
                print(f"  ID: {bt.id} | SÃ­mbolo: {bt.symbol} | Fecha: {bt.fecha_ejecucion}")
                print(f"  PerÃ­odo: {bt.fecha_inicio_datos} a {bt.fecha_fin_datos}")
                
                # Config
                config = {}
                try:
                    raw = bt.params_tecnicos if hasattr(bt, 'params_tecnicos') else None
                    if raw:
                        config = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    config = {}
                
                print(f"\n  ðŸ“‹ CONFIG VENTA:")
                ema_desc = config.get('ema_slow_descendente', False)
                ema_max = config.get('ema_slow_maximo', False)
                print(f"    â€¢ EMA Descendente: {('âœ…' if ema_desc else 'âŠ˜')}")
                print(f"    â€¢ EMA MÃ¡ximo: {('âœ…' if ema_max else 'âŠ˜')}")
                
                # Trades
                trades = Trade.query.filter_by(backtest_id=bt.id).all()
                if not trades:
                    print(f"  âš ï¸  Sin trades")
                    continue
                
                compras = [t for t in trades if t.tipo == 'COMPRA']
                ventas = [t for t in trades if t.tipo == 'VENTA']
                
                print(f"\n  ðŸ“Š TRADES: {len(trades)} total ({len(compras)} buy, {len(ventas)} sell)")
                
                # Desglose
                by_desc = {}
                for t in trades:
                    key = (t.descripcion or 'SIN DESC.')
                    by_desc[key] = by_desc.get(key, 0) + 1
                
                for desc, count in sorted(by_desc.items(), key=lambda x: -x[1]):
                    pct = 100.0 * count / len(trades)
                    print(f"    â†’ {desc[:50]:50s}: {count:3d} ({pct:5.1f}%)")
                
                # ValidaciÃ³n
                ema_desc_sells = sum(1 for t in ventas if "Descendente" in (t.descripcion or ""))
                
                print(f"\n  âœ“ RESULTADO:")
                if ema_desc and ema_desc_sells > 0:
                    print(f"    âœ… EMA Descendente: {ema_desc_sells} sells - FUNCIONA")
                elif ema_desc and ema_desc_sells == 0:
                    print(f"    âŒ EMA Descendente: ACTIVO pero 0 sells - ERROR")
                else:
                    print(f"    âŠ˜  EMA Descendente: desactivado")
                
                print("-"*110)
            
            print("\n" + "="*110 + "\n")
    
    except Exception as e:
        print(f"[âœ—] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()


