#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Análisis simple de últimas 3 backtests - versión Flask ORM
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("\n[*] Analizando últimas 3 backtests del admin...")
    
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
            
            print(f"[✓] Admin encontrado (ID: {admin.id})\n")
            
            # Últimos 3 backtests
            backtests = ResultadoBacktest.query.filter_by(usuario_id=admin.id).order_by(ResultadoBacktest.id.desc()).limit(3).all()
            
            if not backtests:
                print("[!] No hay backtests")
                return
            
            print("="*110)
            print("ANÁLISIS DE LÓGICA DE VENTA - ÚLTIMAS 3 BACKTESTS")
            print("="*110)
            
            for idx, bt in enumerate(backtests, 1):
                print(f"\n[BACKTEST #{idx}]")
                print(f"  ID: {bt.id} | Símbolo: {bt.symbol} | Fecha: {bt.fecha_ejecucion}")
                print(f"  Período: {bt.fecha_inicio_datos} a {bt.fecha_fin_datos}")
                
                # Config
                config = {}
                try:
                    raw = bt.params_tecnicos if hasattr(bt, 'params_tecnicos') else None
                    if raw:
                        config = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    config = {}
                
                print(f"\n  📋 CONFIG VENTA:")
                ema_desc = config.get('ema_slow_descendente', False)
                ema_max = config.get('ema_slow_maximo', False)
                print(f"    • EMA Descendente: {('✅' if ema_desc else '⊘')}")
                print(f"    • EMA Máximo: {('✅' if ema_max else '⊘')}")
                
                # Trades
                trades = Trade.query.filter_by(backtest_id=bt.id).all()
                if not trades:
                    print(f"  ⚠️  Sin trades")
                    continue
                
                compras = [t for t in trades if t.tipo == 'COMPRA']
                ventas = [t for t in trades if t.tipo == 'VENTA']
                
                print(f"\n  📊 TRADES: {len(trades)} total ({len(compras)} buy, {len(ventas)} sell)")
                
                # Desglose
                by_desc = {}
                for t in trades:
                    key = (t.descripcion or 'SIN DESC.')
                    by_desc[key] = by_desc.get(key, 0) + 1
                
                for desc, count in sorted(by_desc.items(), key=lambda x: -x[1]):
                    pct = 100.0 * count / len(trades)
                    print(f"    → {desc[:50]:50s}: {count:3d} ({pct:5.1f}%)")
                
                # Validación
                ema_desc_sells = sum(1 for t in ventas if "Descendente" in (t.descripcion or ""))
                
                print(f"\n  ✓ RESULTADO:")
                if ema_desc and ema_desc_sells > 0:
                    print(f"    ✅ EMA Descendente: {ema_desc_sells} sells - FUNCIONA")
                elif ema_desc and ema_desc_sells == 0:
                    print(f"    ❌ EMA Descendente: ACTIVO pero 0 sells - ERROR")
                else:
                    print(f"    ⊘  EMA Descendente: desactivado")
                
                print("-"*110)
            
            print("\n" + "="*110 + "\n")
    
    except Exception as e:
        print(f"[✗] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
