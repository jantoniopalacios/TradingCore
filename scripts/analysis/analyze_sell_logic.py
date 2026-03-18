#!/usr/bin/env python3
"""
Script: Analiza los Ãºltimos 3 backtests del usuario admin
Verifica si la lÃ³gica de venta se estÃ¡ ejecutando correctamente
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

def analyze_last_three_backtests():
    print("[INFO] Iniciando anÃ¡lisis...")
    
    from scenarios.BacktestWeb.app import create_app
    from scenarios.BacktestWeb.database import db, Backtest, Trade, Usuario
    
    print("[INFO] Importes completados, creando app...")
    app = create_app(user_mode='admin')
    
    print("[INFO] App creada, entrando en contexto...")
    with app.app_context():
        # Obtener usuario admin
        admin = Usuario.query.filter_by(username='admin').first()
        
        if not admin:
            print("âŒ Usuario admin no encontrado")
            return
        
        # Obtener los Ãºltimos 3 backtests
        backtests = Backtest.query.filter_by(user_id=admin.id).order_by(Backtest.id.desc()).limit(3).all()
        
        if not backtests:
            print("âŒ No hay backtests del usuario admin")
            return
        
        print("\n" + "="*100)
        print("ANÃLISIS DE LOS ÃšLTIMOS 3 BACKTESTS - USUARIO ADMIN")
        print("="*100)
        
        for idx, backtest in enumerate(backtests, 1):
            print(f"\n[BACKTEST #{idx}] ID: {backtest.id}")
            print(f"  Fecha: {backtest.created_at}")
            print(f"  Activo: {backtest.symbol}")
            print(f"  Estado: {backtest.status}")
            print(f"  PerÃ­odo: {backtest.start_date} a {backtest.end_date}")
            
            # Obtener configuraciÃ³n
            if backtest.config:
                import json
                try:
                    config = json.loads(backtest.config) if isinstance(backtest.config, str) else backtest.config
                    print(f"\n  ðŸ“‹ CONFIGURACIÃ“N:")
                    print(f"    - EMA Ascendente (BUY): {config.get('ema_slow_ascendente', False)}")
                    print(f"    - EMA Descendente (SELL): {config.get('ema_slow_descendente', False)}")
                    print(f"    - EMA MÃ¡ximo (SELL): {config.get('ema_slow_maximo', False)}")
                    print(f"    - RSI (BUY): {config.get('rsi', False)}")
                    print(f"    - MACD (BUY): {config.get('macd', False)}")
                except:
                    pass
            
            # Obtener trades
            trades = Trade.query.filter_by(backtest_id=backtest.id).all()
            
            if not trades:
                print(f"  âš ï¸  No hay trades registrados")
                continue
            
            # Analizar trades
            compras = [t for t in trades if t.tipo == 'COMPRA']
            ventas = [t for t in trades if t.tipo == 'VENTA']
            
            print(f"\n  ðŸ“Š TRADES TOTALES: {len(trades)} (Compras: {len(compras)}, Ventas: {len(ventas)})")
            
            # Analizar por motivo
            motivos = {}
            for trade in trades:
                motivo = trade.descripcion or 'SIN DESCRIPCIÃ“N'
                motivos[motivo] = motivos.get(motivo, 0) + 1
            
            print(f"\n  ðŸ” ANÃLISIS DE MOTIVOS:")
            for motivo, count in sorted(motivos.items(), key=lambda x: x[1], reverse=True):
                tipo = "BUY" if "Ascendente" in motivo or "MÃ­nimo" in motivo or "Cruce" in motivo else "SELL"
                pct = (count / len(trades) * 100)
                print(f"    {tipo:4s} - {motivo:40s}: {count:3d} ({pct:5.1f}%)")
            
            # Verificar si se cumple lÃ³gica de venta
            print(f"\n  âœ“ VALIDACIÃ“N DE LÃ“GICA DE VENTA:")
            
            ema_descendente_count = sum(1 for t in ventas if "Descendente" in (t.descripcion or ""))
            ema_maximo_count = sum(1 for t in ventas if "MÃ¡ximo" in (t.descripcion or ""))
            stoploss_count = sum(1 for t in ventas if "StopLoss" in (t.descripcion or ""))
            
            config_descendente = False
            config_maximo = False
            try:
                if backtest.config:
                    config = json.loads(backtest.config) if isinstance(backtest.config, str) else backtest.config
                    config_descendente = config.get('ema_slow_descendente', False)
                    config_maximo = config.get('ema_slow_maximo', False)
            except:
                pass
            
            if config_descendente:
                if ema_descendente_count > 0:
                    print(f"    âœ… EMA Descendente ACTIVO â†’ {ema_descendente_count} ventas ({ema_descendente_count/len(ventas)*100:.1f}%)")
                else:
                    print(f"    âŒ EMA Descendente ACTIVO pero 0 ventas (posible error)")
            else:
                print(f"    âŠ˜ EMA Descendente desactivado")
            
            if config_maximo:
                if ema_maximo_count > 0:
                    print(f"    âœ… EMA MÃ¡ximo ACTIVO â†’ {ema_maximo_count} ventas ({ema_maximo_count/len(ventas)*100:.1f}%)")
                else:
                    print(f"    âŒ EMA MÃ¡ximo ACTIVO pero 0 ventas (posible error)")
            else:
                print(f"    âŠ˜ EMA MÃ¡ximo desactivado")
            
            if stoploss_count > 0:
                print(f"    â„¹ï¸  StopLoss tambiÃ©n activo â†’ {stoploss_count} ventas ({stoploss_count/len(ventas)*100:.1f}%)")
            
            print("\n" + "-"*100)
        
        print("\n" + "="*100)
        print("FIN DEL ANÃLISIS")
        print("="*100 + "\n")

if __name__ == '__main__':
    analyze_last_three_backtests()


