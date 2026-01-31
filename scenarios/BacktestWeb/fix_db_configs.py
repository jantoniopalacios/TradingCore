import json
import os
import sys

# 1. CONFIGURACIÓN DE RUTAS (Basado en tus logs)
# Añadimos la carpeta raíz del proyecto al path de Python
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.abspath(os.path.join(ruta_actual, "..", "..")) # Sube a TradingCore
sys.path.append(ruta_raiz)

try:
    # Intentamos importar desde la estructura de paquetes detectada en tus logs
    # Si tu carpeta principal se llama 'webapp', cámbialo aquí:
    from BacktestWeb import app
    from BacktestWeb.database import Usuario, db
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("👉 Intenta ejecutar el script desde: C:\\Users\\juant\\Proyectos\\Python\\TradingCore\\scenarios\\BacktestWeb")
    sys.exit(1)

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

def migrate_configs():
    with app.app_context():
        print("--- 🔄 Iniciando normalización de tipos para HTML ---")
        
        # Backup rápido
        try:
            db.session.execute(text("CREATE TABLE IF NOT EXISTS usuarios_backup_config AS SELECT * FROM usuario"))
            db.session.commit()
            print("💾 Backup creado en 'usuarios_backup_config'.")
        except:
            db.session.rollback()

        usuarios = Usuario.query.all()
        
        # Extraído de tus logs de INSPECCIÓN DE CONFIGURACIÓN
        switches = [
            'macd', 'rsi', 'ema_active', 'bb_active', 'bb_buy_crossover', 
            'bb_sell_crossover', 'filtro_fundamental', 'enviar_mail', 
            'margen_seguridad_active', 'volume_active', 'stoch_fast', 
            'stoch_mid', 'stoch_slow', 'ema_cruce_signal'
        ]

        count = 0
        for u in usuarios:
            if not u.config_actual: continue
            
            try:
                # Cargamos la config (maneja si es ya un dict o un string JSON)
                config = json.loads(u.config_actual) if isinstance(u.config_actual, str) else u.config_actual 
                
                cambio = False
                for s in switches:
                    if s in config:
                        # Forzamos a String 'True'/'False' para que Jinja2 lo entienda
                        if isinstance(config[s], bool):
                            config[s] = "True" if config[s] else "False"
                            cambio = True
                
                if cambio:
                    u.config_actual = json.dumps(config)
                    flag_modified(u, "config_actual")
                    count += 1
                    print(f"✅ Usuario {u.username} sincronizado.")
            except Exception as ex:
                print(f"⚠️ Error en {u.username}: {ex}")

        db.session.commit()
        print(f"--- ✨ Proceso completado. {count} perfiles actualizados. ---")

if __name__ == "__main__":
    migrate_configs()