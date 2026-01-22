import sys
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from trading_engine.core.database_pg import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME

SQLITE_PATH = r'C:\Users\juant\Proyectos\Python\TradingCore\scenarios\BacktestLocal\tradingcore.db'
SQLITE_URL = f'sqlite:///{SQLITE_PATH}'
POSTGRES_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def migrar():
    print("Iniciando migracion jerarquica...")
    
    engine_sqlite = create_engine(SQLITE_URL)
    engine_pg = create_engine(POSTGRES_URL)
    metadata = MetaData()
    metadata.reflect(bind=engine_sqlite)

    SessionPg = sessionmaker(bind=engine_pg)
    session_pg = SessionPg()

    # ORDEN DE MIGRACION: Primero el padre (usuarios), luego los hijos
    # Si tienes mas tablas con dependencias, añadelas aqui en orden
    lista_tablas = list(metadata.tables.keys())
    if 'usuarios' in lista_tablas:
        lista_tablas.remove('usuarios')
        lista_tablas.insert(0, 'usuarios') # Forzamos que 'usuarios' sea la primera

    for table_name in lista_tablas:
        if table_name == 'sqlite_sequence': continue
        
        print(f"Migrando tabla: {table_name}...")
        table_pg = metadata.tables[table_name]

        # 1. Limpiamos datos previos en Postgres para evitar conflictos de IDs
        session_pg.execute(table_pg.delete())

        # 2. Leemos de SQLite
        with engine_sqlite.connect() as conn_sq:
            registros = conn_sq.execute(table_pg.select()).fetchall()
            
            if not registros:
                print(f"  - Sin datos.")
                continue

            for row in registros:
                data = dict(row._mapping)
                session_pg.execute(table_pg.insert().values(**data))
        
        print(f"  - OK: {len(registros)} registros preparados.")

    try:
        session_pg.commit()
        print("\n¡MIGRACION EXITOSA!")
    except Exception as e:
        session_pg.rollback()
        print(f"\nERROR: {e}")
    finally:
        session_pg.close()

if __name__ == "__main__":
    migrar()