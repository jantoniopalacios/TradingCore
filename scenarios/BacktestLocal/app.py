import socket
import logging
import os
import csv  # Necesario para leer el CSV
from flask import Flask, send_from_directory
from logging.handlers import RotatingFileHandler
from .configuracion import cargar_y_asignar_configuracion, PROJECT_ROOT, BACKTESTING_BASE_DIR
from .routes.main_bp import main_bp

# --- IMPORTACIONES DE BASE DE DATOS ---
from .database import db, Usuario

def create_app(user_mode="invitado"):
    app = Flask(__name__)

    # --- 1. CONFIGURACIÓN DE LOGGING ---
    log_folder = BACKTESTING_BASE_DIR / "logs" 
    log_folder.mkdir(parents=True, exist_ok=True)
    log_path = log_folder / "trading_app.log"

    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    rotating_handler = RotatingFileHandler(log_path, maxBytes=500 * 1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(rotating_handler)
    
    app.logger.handlers = []
    app.logger.addHandler(rotating_handler)
    app.logger.info(f"💾 LOG ACTIVADO EN: {log_path}")

    # --- 2. CONFIGURACIÓN DE BASE DE DATOS ---
    db_path = BACKTESTING_BASE_DIR / "tradingcore.db"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "JuanBautistaGamiz_EraUnFrailePoeta")
    
    db.init_app(app)

    # --- 3. CREACIÓN DE TABLAS Y MIGRACIÓN INICIAL ---
    with app.app_context():
        db.create_all()
        
        # Lógica de migración de users.csv a la BD
        ruta_users_csv = BACKTESTING_BASE_DIR / "users.csv"
        
        # Solo actuamos si la tabla de usuarios está vacía
        if Usuario.query.count() == 0 and ruta_users_csv.exists():
            app.logger.info("Detectada base de datos vacía. Iniciando migración desde users.csv...")
            try:
                with open(ruta_users_csv, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Creamos el objeto usuario
                        nuevo_usuario = Usuario(
                            username=row['username'],
                            password=row['password']
                        )
                        db.session.add(nuevo_usuario)
                
                db.session.commit()
                app.logger.info("✅ Migración completada: Usuarios insertados en la BD.")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"❌ Error durante la migración: {e}")

    # --- 4. CONFIGURACIÓN DE USUARIO Y RUTAS ---
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

    app.config['USER_MODE'] = user_mode
    config_usuario = cargar_y_asignar_configuracion(user_mode)
    app.config.update(config_usuario)

    app.register_blueprint(main_bp)

    app.logger.info(f"🚀 Entorno inicializado para: {user_mode}")
    return app

if __name__ == '__main__':
    app = create_app(user_mode="invitado")
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "127.0.0.1"

    print(f"\n✅ SERVIDOR ACTIVO: http://{local_ip}:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)