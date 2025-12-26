import socket
import logging
import os
from flask import Flask, send_from_directory
from .configuracion import cargar_y_asignar_configuracion, PROJECT_ROOT
from .routes.main_bp import main_bp

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

def create_app(user_mode="invitado"):
    app = Flask(__name__)
    
    # 1. SOLUCIÓN AL ERROR 404 (Favicon)
    # Buscamos el icono en la carpeta static del proyecto
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico', 
            mimetype='image/vnd.microsoft.icon'
        )

    # 2. CONFIGURACIÓN DE USUARIO
    # Cargamos la configuración técnica (tipada) y las rutas del sandbox
    app.config['USER_MODE'] = user_mode
    config_usuario = cargar_y_asignar_configuracion(user_mode)
    app.config.update(config_usuario)

    # 3. SEGURIDAD Y SESIONES
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "JuanBautistaGamiz_EraUnFrailePoeta")

    # 4. CONFIGURACIÓN DE LOGGING REFINADA
    log_path = PROJECT_ROOT / "trading_app.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    app.logger.info(f"🚀 Entorno inicializado para: {user_mode}")
    app.logger.info(f"📂 Raíz del proyecto: {PROJECT_ROOT}")

    # 5. REGISTRO DE RUTAS
    app.register_blueprint(main_bp, url_prefix='/') 

    return app

if __name__ == '__main__':
    # Lanzamiento inicial en modo invitado_web para depuración
    app = create_app(user_mode="invitado_web")
    
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "127.0.0.1"

    print(f"\n✅ SERVIDOR ACTIVO: http://{local_ip}:5000")
   
    app.run(host='0.0.0.0', port=5000, debug=True)
