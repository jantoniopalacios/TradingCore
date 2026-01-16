"""Script para transferir datos desde una base de datos SQLite antigua a una nueva,
adaptándose a posibles cambios en la estructura de las tablas.
Esto es útil cuando se han añadido o modificado columnas en la nueva versión de la base de datos.

El script conecta ambas bases de datos, lee los datos de la antigua y los inserta en la nueva,
asegurándose de mapear correctamente las columnas que existen en ambas. 
Solo se migran las columnas que coinciden entre ambas tablas.
Uso:
    python trasvase_db.py

    
Notas:- Asegúrate de que las rutas a las bases de datos son correctas.
- La base de datos nueva debe tener las tablas ya creadas con la estructura actualizada.


"""


import sqlite3
from scenarios.BacktestWeb.configuracion import BACKTESTING_BASE_DIR

def copiar_tabla(cursor, tabla_origen, tabla_destino):
    """Copia datos entre tablas emparejando automáticamente las columnas que existen en ambas"""
    try:
        # 1. Obtener columnas de la tabla origen (vieja)
        cursor.execute(f"PRAGMA vieja.table_info({tabla_origen})")
        cols_origen = [row[1] for row in cursor.fetchall()]
        
        # 2. Obtener columnas de la tabla destino (nueva)
        cursor.execute(f"PRAGMA table_info({tabla_destino})")
        cols_destino = [row[1] for row in cursor.fetchall()]
        
        # 3. Encontrar la intersección (columnas que están en las dos)
        cols_comunes = [c for c in cols_origen if c in cols_destino]
        
        if not cols_comunes:
            print(f"⚠️ No hay columnas comunes entre {tabla_origen} y {tabla_destino}")
            return

        columnas_sql = ", ".join(cols_comunes)
        print(f"🔄 Migrando {tabla_origen} -> {tabla_destino} (Columnas: {len(cols_comunes)})")
        
        # 4. Ejecutar la inserción
        cursor.execute(f"""
            INSERT OR IGNORE INTO {tabla_destino} ({columnas_sql})
            SELECT {columnas_sql} FROM vieja.{tabla_origen}
        """)
        return True
    except Exception as e:
        print(f"❌ Error migrando {tabla_origen}: {e}")
        return False

def realizar_trasvase():
    db_nueva_path = BACKTESTING_BASE_DIR / "tradingcore.db"
    db_vieja_path = BACKTESTING_BASE_DIR / "tradingcorecopy.db"

    if not db_vieja_path.exists():
        print(f"❌ No se encuentra la DB vieja en: {db_vieja_path}")
        return

    conn = sqlite3.connect(str(db_nueva_path))
    cursor = conn.cursor()

    try:
        print(f"🔗 Conectando con: {db_vieja_path.name}")
        cursor.execute(f"ATTACH DATABASE '{str(db_vieja_path)}' AS vieja")

        # Mapeo de nombres (Origen -> Destino)
        # Aquí ponemos los nombres que me confirmaste que tiene la vieja
        mapas = [
            ("usuarios", "usuarios"),
            ("resultados_backtest", "resultados_backtest"),
            ("trades", "trades")
        ]

        for origen, destino in mapas:
            copiar_tabla(cursor, origen, destino)

        conn.commit()
        print(f"\n✅ PROCESO FINALIZADO. Datos migrados con éxito.")

    except sqlite3.Error as e:
        print(f"❌ Error crítico de SQL: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    realizar_trasvase()