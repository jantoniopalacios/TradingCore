from sqlalchemy import text
from trading_engine.core.database_pg import engine_pg

def fix_all_sequences():
    tablas = ['usuarios', 'resultados_backtest', 'trades', 'simbolos', 'fundamental_data']
    
    with engine_pg.connect() as conn:
        print("🔧 Iniciando sincronización de secuencias en PostgreSQL...")
        for tabla in tablas:
            try:
                # 1. Buscamos el nombre de la secuencia (usualmente tabla_id_seq)
                seq_query = text(f"SELECT pg_get_serial_sequence('{tabla}', 'id')")
                seq_name = conn.execute(seq_query).scalar()
                
                if seq_name:
                    # 2. Sincronizamos el valor al MAX(id)
                    fix_query = text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {tabla}), 0) + 1, false)")
                    new_val = conn.execute(fix_query).scalar()
                    print(f"✅ Tabla '{tabla}': Secuencia '{seq_name}' ajustada a {new_val}")
                else:
                    print(f"⚠️ No se encontró secuencia para la tabla {tabla}")
            except Exception as e:
                print(f"❌ Error en tabla {tabla}: {e}")
        
        conn.commit()
        print("\n🚀 Todas las secuencias están ahora sincronizadas.")

if __name__ == "__main__":
    fix_all_sequences()