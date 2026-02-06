from sqlalchemy import text
from trading_engine.core import database_pg

def main():
    try:
        conn = database_pg.engine_pg.connect()
        q = text("SELECT id, symbol, fecha_ejecucion, total_trades, params_tecnicos FROM resultados_backtest ORDER BY fecha_ejecucion DESC LIMIT 10;")
        res = conn.execute(q)
        rows = res.fetchall()
        if not rows:
            print('No hay registros en resultados_backtest')
            return
        for r in rows:
            print(dict(r))
    except Exception as e:
        print('ERROR:', e)
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == '__main__':
    main()
