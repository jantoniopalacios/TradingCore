import socket
import logging
import os
from flask import Flask, send_from_directory
from logging.handlers import RotatingFileHandler
from .configuracion import cargar_y_asignar_configuracion, PROJECT_ROOT, BACKTESTING_BASE_DIR
from .routes.main_bp import main_bp

def create_app(user_mode="invitado"):
    app = Flask(__name__)

    # --- 1. CONFIGURACIÓN DE LOGGING ÚNICA Y DEFINITIVA ---
    # Definimos la ruta: Backtesting/logs/
    log_folder = BACKTESTING_BASE_DIR / "logs" 
    log_folder.mkdir(parents=True, exist_ok=True)
    log_path = log_folder / "trading_app.log"

    # Limpieza absoluta de handlers previos para evitar archivos duplicados
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # Creamos el handler rotativo
    rotating_handler = RotatingFileHandler(
        log_path, 
        maxBytes=500 * 1024, 
        backupCount=3, 
        encoding='utf-8'
    )
    
    # Formato de los mensajes
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)

    # Configuración del logger raíz
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(rotating_handler)
    logging.root.addHandler(logging.StreamHandler()) # Consola

    # Sincronizar el logger de Flask con nuestra configuración
    app.logger.handlers = []
    app.logger.addHandler(rotating_handler)
    
    app.logger.info(f"💾 LOG ACTIVADO EN: {log_path}")

    # --- 2. SOLUCIÓN AL FAVICON ---
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico', 
            mimetype='image/vnd.microsoft.icon'
        )

    # --- 3. CONFIGURACIÓN DE USUARIO ---
    app.config['USER_MODE'] = user_mode
    config_usuario = cargar_y_asignar_configuracion(user_mode)
    app.config.update(config_usuario)

    # --- 4. SEGURIDAD ---
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "JuanBautistaGamiz_EraUnFrailePoeta")

    app.logger.info(f"🚀 Entorno inicializado para: {user_mode}")
    app.logger.info(f"📂 Raíz del proyecto: {PROJECT_ROOT}")

    # --- 5. REGISTRO DE RUTAS ---
    app.register_blueprint(main_bp, url_prefix='/') 

    return app

if __name__ == '__main__':
    app = create_app(user_mode="invitado")
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "127.0.0.1"

    print(f"\n✅ SERVIDOR ACTIVO: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)