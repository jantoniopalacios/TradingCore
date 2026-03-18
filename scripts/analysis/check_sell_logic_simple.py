#!/usr/bin/env python3
"""
Script simple: Obtiene los Ãºltimos 3 backtests del admin desde la DB y analiza su lÃ³gica de venta
"""

import sys
import os
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

print("[*] Iniciando script de anÃ¡lisis de backtests...")

try:
    # ConexiÃ³n directa a BD
    import psycopg2
    import json
    from datetime import datetime
    
    # ParÃ¡metros de conexiÃ³n (desde .env o por defecto)
    conn = psycopg2.connect(
        host="localhost",
        database="trading_core",
        user="postgres",
        password="postgres",
        port=5432
    )
    
    cursor = conn.cursor()
    
    print("[âœ“] Conectado a la base de datos")
    
    # Obtener user_id del admin
    cursor.execute("SELECT id FROM usuario WHERE username = 'admin'")
    admin_id_row = cursor.fetchone()
    
    if not admin_id_row:
        print("[âœ—] Usuario admin no encontrado")
        sys.exit(1)
    
    admin_id = admin_id_row[0]
    print(f"[âœ“] Admin ID: {admin_id}")
    
    # Obtener los Ãºltimos 3 backtests
    cursor.execute("""
        SELECT id, symbol, created_at, start_date, end_date, config, status
        FROM backtest
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 3
    """, (admin_id,))
    
    backtests = cursor.fetchall()
    
    if not backtests:
        print("[!] No hay backtests del usuario admin")
        sys.exit(0)
    
    print(f"[âœ“] Encontrados {len(backtests)} backtests recientes\n")
    
    print("=" * 120)
    print("ANÃLISIS DE LÃ“GICA DE VENTA - ÃšLTIMAS 3 BACKTESTS DEL USUARIO ADMIN")
    print("=" * 120)
    
    for idx, (bt_id, symbol, created_at, start_date, end_date, config_json, status) in enumerate(backtests, 1):
        
        print(f"\n[BACKTEST #{idx}]")
        print(f"  ID: {bt_id}")
        print(f"  SÃ­mbolo: {symbol}")
        print(f"  Fecha: {created_at}")
        print(f"  PerÃ­odo: {start_date} a {end_date}")
        print(f"  Estado: {status}")
        
        # Parsear config
        try:
            if config_json:
                config = json.loads(config_json) if isinstance(config_json, str) else config_json
            else:
                config = {}
        except:
            config = {}
        
        print(f"\n  ðŸ“‹ CONFIGURACIÃ“N DE VENTA:")
        ema_descendente = config.get('ema_slow_descendente', False)
        ema_maximo = config.get('ema_slow_maximo', False)
        rsi = config.get('rsi', False)
        macd = config.get('macd', False)
        
        print(f"    - EMA Descendente: {'âœ“ ACTIVO' if ema_descendente else 'âœ— Inactivo'}")
        print(f"    - EMA MÃ¡ximo: {'âœ“ ACTIVO' if ema_maximo else 'âœ— Inactivo'}")
        print(f"    - RSI Venta: {'âœ“ ACTIVO' if rsi else 'âœ— Inactivo'}")
        print(f"    - MACD: {'âœ“ ACTIVO' if macd else 'âœ— Inactivo'}")
        
        # Obtener trades de este backtest
        cursor.execute("""
            SELECT id, tipo, descripcion, fecha
            FROM trade
            WHERE backtest_id = %s
            ORDER BY fecha
        """, (bt_id,))
        
        trades = cursor.fetchall()
        
        if not trades:
            print(f"\n  âš ï¸  No hay trades registrados")
            continue
        
        # AnÃ¡lisis de trades
        compras = [t for t in trades if t[1] == 'COMPRA']
        ventas = [t for t in trades if t[1] == 'VENTA']
        
        print(f"\n  ðŸ“Š TRADES: {len(trades)} total ({len(compras)} compras, {len(ventas)} ventas)")
        
        # Contar por descripciÃ³n
        descripciones = {}
        for trade_id, tipo, descripcion, fecha in trades:
            desc_key = descripcion or 'SIN DESCRIPCIÃ“N'
            descripciones[desc_key] = descripciones.get(desc_key, 0) + 1
        
        print(f"\n  ðŸ” DESGLOSE POR MOTIVO:")
        for desc, count in sorted(descripciones.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(trades) * 100)
            print(f"    â€¢ {desc:50s}: {count:3d} ({pct:5.1f}%)")
        
        # ValidaciÃ³n especÃ­fica de lÃ³gica de venta
        print(f"\n  âœ“ VALIDACIÃ“N DE SELL LOGIC:")
        
        ema_desc_closes = sum(1 for t in ventas if "Descendente" in (t[2] or ""))
        ema_max_closes = sum(1 for t in ventas if "MÃ¡ximo" in (t[2] or ""))
        sl_closes = sum(1 for t in ventas if "StopLoss" in (t[2] or ""))
        
        if ema_descendente:
            if ema_desc_closes > 0:
                print(f"    âœ… EMA Descendente: {ema_desc_closes}/{len(ventas)} ventas ({ema_desc_closes/len(ventas)*100:.1f}%) - FUNCIONA")
            else:
                print(f"    âŒ EMA Descendente: ACTIVO pero 0/{len(ventas)} ventas - PROBLEMA!")
        else:
            if ema_desc_closes == 0:
                print(f"    âŠ˜  EMA Descendente: desactivado (sin ventas esperadas) - OK")
            else:
                print(f"    âš ï¸  EMA Descendente: desactivado pero hay {ema_desc_closes} ventas - INCONSISTENCIA")
        
        if ema_maximo:
            if ema_max_closes > 0:
                print(f"    âœ… EMA MÃ¡ximo: {ema_max_closes}/{len(ventas)} ventas ({ema_max_closes/len(ventas)*100:.1f}%) - FUNCIONA")
            else:
                print(f"    âŒ EMA MÃ¡ximo: ACTIVO pero 0/{len(ventas)} ventas - PROBLEMA!")
        else:
            if ema_max_closes == 0:
                print(f"    âŠ˜  EMA MÃ¡ximo: desactivado (sin ventas esperadas) - OK")
            else:
                print(f"    âš ï¸  EMA MÃ¡ximo: desactivado pero hay {ema_max_closes} ventas - INCONSISTENCIA")
        
        if sl_closes > 0:
            print(f"    â„¹ï¸  StopLoss: {sl_closes}/{len(ventas)} ventas ({sl_closes/len(ventas)*100:.1f}%) - activo")
        
        # ConclusiÃ³n
        print(f"\n  CONCLUSIÃ“N:", end=" ")
        if ema_descendente and ema_desc_closes == 0:
            print("âŒ EMA Descendente configurado pero NO funciona")
        elif (ema_descendente or ema_maximo) and (ema_desc_closes + ema_max_closes) > 0:
            print("âœ… LÃ³gica de venta EMA funcionando")
        else:
            print("âš ï¸  Resultados parciales o sin venta por EMA")
        
        print("-" * 120)
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 120)
    print("FIN DEL ANÃLISIS")
    print("=" * 120 + "\n")

except ImportError as e:
    print(f"[âœ—] Error de importaciÃ³n: {e}")
    print("[*] Intentando alternativa con ORM...")
    
    try:
        from scenarios.BacktestWeb.app import create_app
        from scenarios.BacktestWeb.database import Backtest, Trade, Usuario
        
        app = create_app(user_mode='admin')
        with app.app_context():
            admin = Usuario.query.filter_by(username='admin').first()
            if admin:
                backtests = Backtest.query.filter_by(user_id=admin.id).order_by(Backtest.id.desc()).limit(3).all()
                print(f"[âœ“] Encontrados {len(backtests)} backtests (usando ORM)")
                for bt in backtests:
                    print(f"  - Backtest {bt.id}: {bt.symbol} ({len(bt.trades)} trades)")
    except Exception as e2:
        print(f"[âœ—] Error en alternativa: {e2}")

except Exception as e:
    print(f"[âœ—] Error: {e}")
    import traceback
    traceback.print_exc()


