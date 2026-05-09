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
import argparse
from flask import Flask, send_from_directory
from logging.handlers import RotatingFileHandler
from trading_engine.core.database_pg import db, ENGINE_OPTIONS

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
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = ENGINE_OPTIONS.copy()
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
            
            # Registramos rutas
            app.register_blueprint(main_bp)

            # Cargamos la config del usuario (no crítico si BD no disponible aún)
            app.logger.info(f"Cargando parámetros para {user_mode}...")
            try:
                config_data = cargar_y_asignar_configuracion(user_mode)
                app.config.update(config_data)
            except Exception as e_cfg:
                app.logger.warning(f"No se pudo cargar configuración de BD al iniciar: {e_cfg}")
            
        except Exception as e:
            app.logger.error(f"ERROR CRÍTICO AL INICIAR: {e}")
            sys.exit(1)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

    return app


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def run_app(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--host', dest='host')
    parser.add_argument('--port', dest='port', type=int)
    parser.add_argument('--user-mode', dest='user_mode')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--no-debug', dest='no_debug', action='store_true')
    parser.add_argument('--reloader', dest='reloader', action='store_true')
    parser.add_argument('--no-reloader', dest='no_reloader', action='store_true')

    args, _ = parser.parse_known_args(argv)

    user_mode = args.user_mode or os.environ.get('TRADINGCORE_USER_MODE', 'admin')
    host = args.host or os.environ.get('TRADINGCORE_WEB_HOST', '127.0.0.1')
    port = args.port if args.port is not None else int(os.environ.get('TRADINGCORE_WEB_PORT', '5000'))

    env_debug_default = host not in {'0.0.0.0', '::'}
    debug = _env_flag('TRADINGCORE_WEB_DEBUG', env_debug_default)
    if args.debug:
        debug = True
    if args.no_debug:
        debug = False

    use_reloader = _env_flag('TRADINGCORE_WEB_RELOADER', debug)
    if args.reloader:
        use_reloader = True
    if args.no_reloader:
        use_reloader = False

    app = create_app(user_mode=user_mode)
    if debug:
        app.run(host=host, port=port, debug=True, use_reloader=use_reloader)
    else:
        from waitress import serve
        threads = int(os.environ.get('TRADINGCORE_WEB_THREADS', '8'))
        logging.getLogger(__name__).info("Starting waitress server on %s:%s with %d threads", host, port, threads)
        serve(app, host=host, port=port, threads=threads)

if __name__ == '__main__':
    run_app()