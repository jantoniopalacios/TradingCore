import sys
import os
from pathlib import Path

# 1. Ajuste de rutas para que Python encuentre tus archivos
root_path = Path(__file__).parent.absolute()
sys.path.append(str(root_path))
sys.path.append(str(root_path / "scenarios" / "BacktestWeb"))

try:
    # 2. Intentamos importar desde la nueva ruta
    from app import create_app
    print("✅ create_app importado con éxito.")

    # 3. Creamos la app y probamos el contexto
    app = create_app()
    with app.app_context():
        print("✅ Contexto de Flask iniciado.")
        
        # 4. Verificamos que las rutas del Blueprint existen
        rutas = [str(p) for p in app.url_map.iter_rules()]
        main_ok = any('main.index' in r for r in rutas)
        
        if main_ok:
            print("✅ Blueprint 'main' registrado correctamente.")
        else:
            print("⚠️ El Blueprint 'main' no parece estar registrado.")

        # 5. Prueba de conexión a DB
        from trading_engine.core.database_pg import db
        db.engine.connect()
        print("✅ Conexión a PostgreSQL: OK")

except Exception as e:
    print(f"❌ Error durante la prueba: {e}")
    import traceback
    traceback.print_exc()
