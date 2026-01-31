import socket
import logging
import os
import csv
import sys
from flask import Flask, send_from_directory
from logging.handlers import RotatingFileHandler

# Importaciones de tu estructura
from .configuracion import cargar_y_asignar_configuracion, PROJECT_ROOT, BACKTESTING_BASE_DIR
# Importamos el objeto main_bp desde la subcarpeta routes
from .routes.main_bp import main_bp 
# Importamos db y el modelo Usuario (ajustado a tu nueva base de datos pg)
from trading_engine.core.database_pg import db
from .database import Usuario 

# Forzar UTF-8 para evitar el error de la cruz roja en Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def create_app(user_mode="admin"):
    app = Flask(__name__)

    # --- 1. CONFIGURACIÓN DE LOGGING (Sin emojis para evitar errores) ---
    log_folder = BACKTESTING_BASE_DIR / "logs" 
    log_folder.mkdir(parents=True, exist_ok=True)
    log_path = log_folder / "trading_app.log"

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    rotating_handler = RotatingFileHandler(log_path, maxBytes=500 * 1024, backupCount=3, encoding='utf-8')
    # Nuevo formato: separador '|' para facilitar el parseo posterior
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    rotating_handler.setFormatter(formatter)
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(rotating_handler)
    
    app.logger.addHandler(rotating_handler)
    app.logger.info(f"LOG ACTIVADO EN: {log_path}")

    # --- 2. CONFIGURACIÓN DE BASE DE DATOS (POSTGRESQL) ---
    # Usamos la conexión que ya probamos que funciona
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+pg8000://postgres:admin@localhost:5433/trading_db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "JuanBautistaGamiz_EraUnFrailePoeta")
    
    db.init_app(app)

    # --- 3. CREACIÓN DE TABLAS Y MIGRACIÓN ---
    with app.app_context():
        try:
            db.create_all()
            
            ruta_users_csv = BACKTESTING_BASE_DIR / "users.csv"
            if Usuario.query.count() == 0 and ruta_users_csv.exists():
                app.logger.info("Migrando usuarios desde users.csv a Postgres...")
                with open(ruta_users_csv, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        nuevo_usuario = Usuario(
                            username=row['username'],
                            password=row['password']
                        )
                        db.session.add(nuevo_usuario)
                db.session.commit()
                app.logger.info("Migracion completada exitosamente.")
        except Exception as e:
            app.logger.error(f"Error en base de datos: {e}")

    # --- 4. RUTAS Y BLUEPRINTS ---
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

    app.config['USER_MODE'] = user_mode
    config_usuario = cargar_y_asignar_configuracion(user_mode)
    app.config.update(config_usuario)

    # Registramos el blueprint que Flask ahora sí encontrará
    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    # Creamos la aplicación
    app = create_app(user_mode="admin")
    
    # Intentamos detectar la IP para el mensaje de bienvenida
    try:
        # Esto obtendrá la IP principal, si Tailscale está activo suele ser la mejor
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "0.0.0.0"

    print(f"\n==========================================")
    print(f" SERVIDOR TRADINGCORE ACTIVO")
    print(f" Acceso local: http://localhost:5000")
    print(f" Acceso Tailscale: http://{local_ip}:5000")
    print(f"==========================================\n")

    # Ejecución: 
    # debug=False es más estable para el modo 'hidden' del .bat
    app.run(host='0.0.0.0', port=5000, debug=True)