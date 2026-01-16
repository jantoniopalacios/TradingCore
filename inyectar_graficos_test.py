import os
import random
import sys

# 1. Aseguramos que Python encuentre tus módulos
sys.path.append(os.getcwd())

# 2. Importamos la fábrica y la base de datos
try:
    from scenarios.BacktestWeb.app import create_app, db
    from scenarios.BacktestWeb.database import ResultadoBacktest
    
    # Creamos la instancia de la aplicación
    app = create_app(user_mode="admin") 
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Asegúrate de ejecutar este script desde la carpeta raíz 'TradingCore'.")
    sys.exit(1)

# CONFIGURACIÓN
CARPETA_GRAFICOS = 'test_charts' 

def cargar_graficos_aleatorios():
    if not os.path.exists(CARPETA_GRAFICOS):
        os.makedirs(CARPETA_GRAFICOS)
        print(f"📁 Se ha creado la carpeta '{CARPETA_GRAFICOS}'.")
        print("Mete tus archivos .html ahí y vuelve a ejecutar.")
        return

    archivos_html = [f for f in os.listdir(CARPETA_GRAFICOS) if f.endswith('.html')]
    
    if not archivos_html:
        print(f"❌ No hay archivos .html en '{CARPETA_GRAFICOS}'.")
        return

    # 3. Entramos en el contexto de la aplicación para usar la DB
    with app.app_context():
        registros = ResultadoBacktest.query.all()
        
        if not registros:
            print("❌ La tabla 'resultado_backtest' está vacía.")
            return

        print(f"🔄 Inyectando gráficos aleatorios en {len(registros)} registros...")

        for reg in registros:
            archivo_random = random.choice(archivos_html)
            ruta_completa = os.path.join(CARPETA_GRAFICOS, archivo_random)
            
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    reg.grafico_html = f.read()
            except Exception as e:
                print(f"⚠️ Error leyendo {archivo_random}: {e}")
        
        try:
            db.session.commit()
            print("✅ ¡Éxito! Gráficos inyectados correctamente.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al guardar en la DB: {e}")

if __name__ == "__main__":
    cargar_graficos_aleatorios()