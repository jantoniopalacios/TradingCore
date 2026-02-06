#!/usr/bin/env python3
"""
Script para consultar últimos resultados de backtest desde PostgreSQL
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Configuración de conexión
conn_params = {
    'host': 'localhost',
    'port': '5433',
    'database': 'trading_db',
    'user': 'postgres',
    'password': 'admin'
}

try:
    # Conectar a PostgreSQL
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 100)
    print("🔍 ÚLTIMOS 10 BACKTESTS EJECUTADOS")
    print("=" * 100)
    
    # Consulta: últimos backtests
    query = """
    SELECT 
        id, 
        usuario_id, 
        symbol, 
        fecha_ejecucion,
        total_trades,
        return_pct,
        sharpe_ratio,
        max_drawdown,
        profit_factor,
        win_rate,
        params_tecnicos
    FROM resultados_backtest 
    ORDER BY fecha_ejecucion DESC 
    LIMIT 10
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    if not results:
        print("❌ No se encontraron resultados de backtest en la BD.")
    else:
        print(f"\n✅ Se encontraron {len(results)} registros:\n")
        
        for i, row in enumerate(results, 1):
            print(f"\n{'─' * 100}")
            print(f"📊 Backtest #{i}")
            print(f"{'─' * 100}")
            print(f"  ID                    : {row['id']}")
            print(f"  Usuario               : {row['usuario_id']}")
            print(f"  Símbolo               : {row['symbol']}")
            print(f"  Fecha ejecución       : {row['fecha_ejecucion']}")
            print(f"  Total Trades          : {row['total_trades']}")
            print(f"  Retorno (%)           : {row['return_pct']:.2f}%" if row['return_pct'] else f"  Retorno (%)           : N/A")
            print(f"  Sharpe Ratio          : {row['sharpe_ratio']:.4f}" if row['sharpe_ratio'] else f"  Sharpe Ratio          : N/A")
            print(f"  Max Drawdown (%)      : {row['max_drawdown']:.2f}%" if row['max_drawdown'] else f"  Max Drawdown (%)      : N/A")
            print(f"  Profit Factor         : {row['profit_factor']:.2f}" if row['profit_factor'] else f"  Profit Factor         : N/A")
            print(f"  Win Rate (%)          : {row['win_rate']:.2f}%" if row['win_rate'] else f"  Win Rate (%)          : N/A")
            
            # Parse params_tecnicos JSON
            if row['params_tecnicos']:
                try:
                    params = json.loads(row['params_tecnicos'])
                    print(f"\n  🔧 PARÁMETROS TÉCNICOS:")
                    for key, val in list(params.items())[:15]:  # Mostrar primeros 15
                        print(f"     • {key}: {val}")
                    if len(params) > 15:
                        print(f"     ... y {len(params) - 15} más")
                except:
                    print(f"  Parámetros: {row['params_tecnicos'][:200]}...")
    
    # Consulta: últimos trades
    print(f"\n\n{'=' * 100}")
    print("🎯 ÚLTIMOS 20 TRADES EJECUTADOS")
    print(f"{'=' * 100}")
    
    query_trades = """
    SELECT 
        t.id,
        t.backtest_id,
        r.symbol,
        r.fecha_ejecucion,
        t.tipo,
        t.descripcion,
        t.fecha,
        t.precio_entrada,
        t.precio_salida,
        t.pnl_absoluto,
        t.retorno_pct
    FROM trades t
    LEFT JOIN resultados_backtest r ON t.backtest_id = r.id
    ORDER BY t.fecha DESC, t.id DESC
    LIMIT 20
    """
    
    cur.execute(query_trades)
    trades = cur.fetchall()
    
    if not trades:
        print("\n❌ No se encontraron trades en la BD.")
    else:
        print(f"\n✅ Se encontraron {len(trades)} trades:\n")
        
        for i, trade in enumerate(trades, 1):
            pnl_status = "✅ WIN" if trade['pnl_absoluto'] and trade['pnl_absoluto'] >= 0 else "❌ LOSS"
            print(f"\n[{i}] {pnl_status} | {trade['symbol']} | {trade['fecha']}")
            print(f"    Tipo              : {trade['tipo']}")
            print(f"    Descripción       : {trade['descripcion']}")
            print(f"    Entrada           : ${trade['precio_entrada']:.2f}" if trade['precio_entrada'] else f"    Entrada           : N/A")
            print(f"    Salida            : ${trade['precio_salida']:.2f}" if trade['precio_salida'] else f"    Salida            : N/A")
            print(f"    PnL Absoluto      : ${trade['pnl_absoluto']:.2f}" if trade['pnl_absoluto'] else f"    PnL Absoluto      : N/A")
            print(f"    Retorno (%)       : {trade['retorno_pct']:.2f}%" if trade['retorno_pct'] else f"    Retorno (%)       : N/A")
    
    print(f"\n{'=' * 100}\n")
    
    cur.close()
    conn.close()
    print("✅ Consulta completada exitosamente.")

except Exception as e:
    print(f"❌ Error conectando o consultando BD: {e}")
    import traceback
    traceback.print_exc()
