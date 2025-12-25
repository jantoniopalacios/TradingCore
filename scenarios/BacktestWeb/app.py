import socket
from flask import Flask
import os
import logging
from pathlib import Path

# ----------------------------------------------------------------------
# --- Ejecutar en modo debug ---
# Si deseas activar el modo debug, descomenta la siguiente línea:
# os.environ['FLASK_ENV'] = 'development'
# o tambien la siguiente línea:
# os.environ['FLASK_DEBUG'] = '1'
# o bien, establece la variable de entorno FLASK_ENV a 'development' en tu sistema.
# Esto hará que Flask recargue automáticamente la aplicación al detectar cambios en el código.
# ----------------------------------------------------------------------
# Para depuración avanzada, puedes usar:
# import debugpy
# debugpy.listen(("5678"))
# print("Esperando a que el depurador se conecte...")
# debugpy.wait_for_client()
# ----------------------------------------------------------------------
# --- Instrucciones para ejecutar ---
# copilot-debug python -m scenarios.BaktestWeb.app "&" C:/Users/juant/Proyectos/Python/TradingCore/.venv/Scripts/Activate.ps1
# Luego abre tu navegador en http://localhost:5000
# o http://localhost:5000/quien_soy para ver el modo de usuario actual.
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# --- IMPORTACIONES DE LA ESTRUCTURA ---
# ----------------------------------------------------------------------
# Importamos la función maestra de configuración
from .configuracion import cargar_y_asignar_configuracion, BACKTESTING_BASE_DIR

# Importamos la función de limpieza modular
try:
    from .file_handler import clean_run_results_dir 
except ImportError:
    def clean_run_results_dir(results_path=None):
        logging.warning("No se encontró file_handler.py.")

# Importar el Blueprint
from .routes.main_bp import main_bp 

# ----------------------------------------------------------------------
# --- CONFIGURACIÓN DE LA APLICACIÓN FLASK ---
# ----------------------------------------------------------------------
def create_app(user_mode="invitado"):
    """Función de factoría para crear y configurar la aplicación Flask."""
    
    app = Flask(__name__)

    app.config['USER_MODE'] = user_mode # Guardamos el nombre exacto del modo de usuario
    
    # 🌟 PASO CLAVE: Inicializamos el entorno del usuario (Clonación + Carga de variables)
    # Esta función ya crea las carpetas, copia las plantillas y configura la clase System.
    config_usuario = cargar_y_asignar_configuracion(user_mode)
    
    # Pasamos todas las rutas y parámetros cargados al objeto app.config de Flask
    app.config.update(config_usuario)

    @app.route('/quien_soy')
    def debug_user():
        return f"Usuario: {app.config.get('user_mode')} | Carpeta: {app.config.get('results_dir')}"
    
    # Clave Secreta
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "JuanBautistaGamiz_EraUnFrailePoeta")
    
# --- Configuración de Logging ---
    log_format = '%%(asctime)s - %%(levelname)s - %%(message)s'
    
    # Configuramos el logging para que escriba en consola Y en el archivo
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("trading_app.log"), # 👈 Esto crea el archivo
            logging.StreamHandler()                # 👈 Esto mantiene los logs en VS Code
        ]
    )
    
    app.logger.info(f"Modo de usuario activado: {user_mode}")
    app.logger.info(f"Ruta de resultados: {app.config['results_dir']}")

    ## 1. REGISTRAR EL BLUEPRINT
    app.register_blueprint(main_bp, url_prefix='/') 

    return app

# ----------------------------------------------------------------------
# --- INICIO DEL SERVIDOR ---
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # Por defecto, si se lanza este archivo directamente, usamos 'invitado_web'
    app = create_app(user_mode="invitado_web")
    
    # Limpieza inicial de la carpeta de este usuario específico
    clean_run_results_dir(app.config['results_dir'])

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "0.0.0.0"

    print("\n" + "="*60)
    print(f"🚀 SERVIDOR ACTIVO EN TU RED LOCAL (Modo: {app.config['user_mode']})")
    print(f"🔗 Enlace para otros equipos: http://{local_ip}:5000")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)