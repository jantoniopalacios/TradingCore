# ----------------------------------------------------------------------
# --- app.py ---
# ----------------------------------------------------------------------
# Descripción       : Factory para crear la aplicación Flask con configuración dinámica
#                  según el modo de usuario (admin/usuario)
#                 
# Fecha de modificación : 2026-02-01
# ----------------------------------------------------------------------

import os
import sys
import logging
from flask import Flask, send_from_directory
from logging.handlers import RotatingFileHandler
from trading_engine.core.database_pg import db

# IMPORTACIONES DE RUTAS (Sin lógica de DB)
from .configuracion import BACKTESTING_BASE_DIR, DB_URI

def setup_logging(app):
    log_folder = BACKTESTING_BASE_DIR / "logs" 
    log_folder.mkdir(parents=True, exist_ok=True)
    # 🎯 Usamos el mismo nombre que en configuracion.py
    log_path = log_folder / "trading_app.log" 
    
    logging.root.handlers = []
    # Rotación: 500KB por archivo, guarda hasta 3 archivos viejos
    handler = RotatingFileHandler(log_path, maxBytes=500 * 1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    handler.setFormatter(formatter)
    
    # Añadimos el handler al logger de Flask Y al logger raíz de Python
    app.logger.addHandler(handler)
    logging.getLogger().addHandler(handler) # Esto captura logs de otros módulos
    app.logger.setLevel(logging.INFO)

def create_app(user_mode="admin"):
    app = Flask(__name__)
    
    # Configuración básica
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_TradingCore")
    app.config['USER_MODE'] = user_mode

    setup_logging(app)
    db.init_app(app)

    # 2. CARGA DE MÓDULOS DENTRO DEL CONTEXTO
    with app.app_context():
        try:
            # Importamos aquí para romper el ciclo de importación
            from .database import Usuario 
            from .configuracion import cargar_y_asignar_configuracion
            from .routes.main_bp import main_bp 
            
            db.create_all()
            
            # Cargamos la config del usuario
            app.logger.info(f"Cargando parámetros para {user_mode}...")
            config_data = cargar_y_asignar_configuracion(user_mode)
            app.config.update(config_data)
            
            # Registramos rutas
            app.register_blueprint(main_bp)
            
        except Exception as e:
            print(f"❌ ERROR CRÍTICO AL INICIAR: {e}")
            sys.exit(1)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

    return app

if __name__ == '__main__':
    app = create_app(user_mode="admin")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)