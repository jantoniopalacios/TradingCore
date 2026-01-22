import json
from datetime import datetime, timezone  # Añadimos timezone
from sqlalchemy import text
from trading_engine.core.database_pg import engine_pg # Asegúrate de que este import esté arriba

def guardar_resultado_ejemplo(user_id):
    print("\n--- 📥 GUARDANDO RESULTADO DE BACKTEST ---")
    
    # 1. Usamos el método moderno para la fecha UTC
    ahora_utc = datetime.now(timezone.utc)

    resultado_data = {
        "usuario_id": user_id,
        "id_estrategia": 101,
        "symbol": "ZTS",
        "sharpe_ratio": 1.45,
        "max_drawdown": -0.12,
        "profit_factor": 2.1,
        "return_pct": 25.5,
        "total_trades": 45,
        "win_rate": 0.62,
        "fecha_inicio_datos": "2023-01-01",
        "fecha_fin_datos": "2024-01-01",
        "intervalo": "1d",
        "cash_inicial": 10000.0,
        "comision": 0.001,
        "params_tecnicos": json.dumps({"rsi_period": 14, "ema_fast": 50}),
        "notas": "Prueba tras migración exitosa",
        "fecha_ejecucion": ahora_utc
    }

    # Usamos el engine_pg que viene del import global
    with engine_pg.connect() as conn:
        query = text("""
            INSERT INTO resultados_backtest 
            (usuario_id, id_estrategia, symbol, sharpe_ratio, max_drawdown, profit_factor, 
             return_pct, total_trades, win_rate, fecha_inicio_datos, fecha_fin_datos, 
             intervalo, cash_inicial, comision, params_tecnicos, notas, fecha_ejecucion)
            VALUES 
            (:usuario_id, :id_estrategia, :symbol, :sharpe_ratio, :max_drawdown, :profit_factor, 
             :return_pct, :total_trades, :win_rate, :fecha_inicio_datos, :fecha_fin_datos, 
             :intervalo, :cash_inicial, :comision, :params_tecnicos, :notas, :fecha_ejecucion)
            RETURNING id
        """)
        
        res = conn.execute(query, resultado_data)
        backtest_id = res.fetchone()[0]
        
        # Insertar un trade vinculado
        conn.execute(text("""
            INSERT INTO trades (backtest_id, tipo, descripcion, fecha, precio_entrada, precio_salida, pnl_absoluto)
            VALUES (:bid, 'COMPRA', 'Entrada RSI', '2023-03-15', 160.50, 175.20, 14.70)
        """), {"bid": backtest_id})
        
        conn.commit()
        print(f"✅ Resultado guardado con ID: {backtest_id}")

# Llamada al final del script
if __name__ == "__main__":
    # Suponiendo que el usuario con ID 1 ya existe por el test anterior
    try:
        guardar_resultado_ejemplo(1)
    except Exception as e:
        print(f"❌ Error: {e}")