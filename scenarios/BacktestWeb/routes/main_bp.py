import os
import threading
import csv
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, send_from_directory, current_app, abort, session, jsonify, Response
)
from collections import deque

# --- IMPORTACIONES DE LA ARQUITECTURA ---
from ..file_handler import ( 
    read_symbols_raw, write_symbols_raw,
    get_directory_tree
)

from ..configuracion import (
    guardar_parametros_a_env,
    inicializar_configuracion_usuario,
    cargar_y_asignar_configuracion,
    System,
    BACKTESTING_BASE_DIR
) 

from trading_engine.core.constants import VARIABLE_COMMENTS
from ..Backtest import ejecutar_backtest 

# --- CONFIGURACIÓN Y BLUEPRINT ---
main_bp = Blueprint('main', __name__) 

# --- HELPERS ---

def obtener_usuarios_registrados():
    """Lee la lista de usuarios desde Backtesting/users.csv"""
    usuarios = {}
    ruta_usuarios = BACKTESTING_BASE_DIR / "users.csv"
    
    if not ruta_usuarios.exists():
        current_app.logger.warning(f"⚠️ users.csv no encontrado en {ruta_usuarios}")
        return {"admin": "trading"} # Backup de emergencia
        
    try:
        with open(ruta_usuarios, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = row['username'].strip().lower()
                pwd = row['password'].strip()
                usuarios[user] = pwd
    except Exception as e:
        current_app.logger.error(f"Error leyendo users.csv: {e}")
        
    return usuarios

def get_user_paths(username):
    """Calcula las rutas físicas usando la lógica maestra"""
    rutas = inicializar_configuracion_usuario(username)
    
    return {
        'fichero_variables': rutas['fichero_variables'],
        'fichero_simbolos': rutas['fichero_simbolos'],
        'results_dir': rutas['results_dir'],
        'graph_dir': rutas['graph_dir'],
        'logs_dir': BACKTESTING_BASE_DIR / "logs"  # Ruta centralizada solicitada
    }

# --- RUTAS DE AUTENTICACIÓN ---

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').lower().strip()
        password = request.form.get('password', '').strip()

        usuarios_permitidos = obtener_usuarios_registrados()

        if user in usuarios_permitidos and usuarios_permitidos[user] == password:
            session.clear()
            session['logged_in'] = True
            session['user_mode'] = user
            
            inicializar_configuracion_usuario(user)
            flash(f"✅ Bienvenido, {user.capitalize()}", "success")
            return redirect(url_for('main.index'))
        
        flash("❌ Usuario o contraseña incorrectos", "danger")
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for('main.login'))

# --- RUTA PRINCIPAL ---

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))
    
    user_mode = session.get('user_mode')
    paths = get_user_paths(user_mode)

    # --- 1. MANEJO DEL POST (GUARDAR CONFIGURACIÓN) ---
    if request.method == 'POST':
        form_data = dict(request.form)
        symbols_content = form_data.pop('symbols_content', None) 
        
        try:
            if symbols_content is not None:
                write_symbols_raw(symbols_content, str(paths['fichero_simbolos']))
            
            guardar_parametros_a_env(form_data, user_mode) 
            cargar_y_asignar_configuracion(user_mode)
            flash(f"✅ Configuración actualizada con éxito.", 'success')
        except Exception as e:
            flash(f"❌ Error al guardar: {e}", 'danger')
            
        return redirect(url_for('main.index'))

    # --- 2. MANEJO DEL GET (VISUALIZAR) ---
    config_completa = cargar_y_asignar_configuracion(user_mode)

    # Normalización de booleanos para la UI
    if isinstance(config_completa, dict):
        for key, value in config_completa.items():
            if isinstance(value, bool):
                config_completa[key] = "True" if value else "False"

    symbols_content_data = read_symbols_raw(str(paths['fichero_simbolos']))

    # --- CONSTRUCCIÓN DEL ÁRBOL DE ARCHIVOS ---
    file_tree = []
    
    # Determinamos si es admin una sola vez para pasarlo
    es_administrador = (user_mode == 'admin')

    # Logs (Solo Admin)
    if es_administrador and paths['logs_dir'].exists():
        # Pasamos True a get_directory_tree
        file_tree.append(("Sistema Logs 🛡️", True, get_directory_tree(paths['logs_dir'], is_admin=True), "Folder"))

    # Resultados y Gráficos
    if paths['results_dir'].exists():
        file_tree.append(("Resultados", True, get_directory_tree(paths['results_dir'], is_admin=es_administrador), "Folder"))
    
    if paths['graph_dir'].exists():
        file_tree.append(("Gráficos", True, get_directory_tree(paths['graph_dir'], is_admin=es_administrador), "Folder"))

    return render_template(
        'index.html', 
        config=config_completa, 
        comments=VARIABLE_COMMENTS, 
        symbols_content=symbols_content_data,
        file_tree=file_tree,
        backtesting_dir_name=user_mode,
        strategy=System
    )

# --- RUTAS DE ARCHIVOS Y EJECUCIÓN ---

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    config_web = request.form.to_dict()
    config_web['user_mode'] = session.get('user_mode')
    
    # Iniciamos el hilo del backtest
    thread = threading.Thread(target=ejecutar_backtest, args=(config_web,))
    thread.start()
    
    # --- CAMBIO CRÍTICO: Esperamos a que el proceso termine ---
    thread.join() 
    
    # --- TIEMPO DE CORTESÍA ---
    # Esperamos 2 segundos extra para asegurar que el explorador de archivos
    # de Windows vea los nuevos ficheros antes de recargar la web.
    import time
    time.sleep(2) 
    
    return jsonify({
        "status": "success", 
        "message": "Backtest finalizado. Los archivos han sido actualizados."
    })

@main_bp.route('/file/<path:path>')
def view_file(path):
    if not session.get('logged_in'): abort(401)
    user_mode = session.get('user_mode')
    paths = get_user_paths(user_mode)
    
    # Seguridad: Bloqueo de logs para no-admins
    if "logs" in path.lower() and user_mode != 'admin':
        abort(403)

    # Definir carpetas de búsqueda
    search_folders = [paths['results_dir'], paths['graph_dir']]
    if user_mode == 'admin':
        search_folders.append(paths['logs_dir'])

    target = None
    filename = path.split('/')[-1]

    for base in search_folders:
        # Intentar ruta completa o nombre de archivo directo
        posible = base / filename
        if posible.exists() and not posible.is_dir():
            target = posible
            break

    if not target: abort(404)

    if target.suffix.lower() == '.html':
        return send_from_directory(target.parent, target.name)
    
    try:
        # Tratamiento especial para logs (últimas 2000 líneas)
        if target.suffix.lower() == '.log':
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                contenido = "".join(deque(f, maxlen=2000))
        else:
            with open(target, 'r', encoding='utf-8', errors='replace') as f:
                contenido = f.read()
        
        return Response(contenido, mimetype='text/plain')
    except Exception as e:
        return f"Error leyendo archivo: {e}", 500

@main_bp.route('/delete-file/<path:path>', methods=['POST'])
def delete_file(path):
    if not session.get('logged_in'): abort(401)
    
    user_mode = session.get('user_mode')
    paths = get_user_paths(user_mode)
    filename = os.path.basename(path)
    
    # No permitir que nadie (ni admin por accidente) borre el log activo fácilmente
    if "trading_app.log" in filename and request.form.get('confirm') != 'true':
        flash("El log del sistema no debe borrarse mientras el servidor está activo.", "warning")
        return redirect(url_for('main.index'))

    target = None
    search_folders = [paths['results_dir'], paths['graph_dir']]
    if user_mode == 'admin': search_folders.append(paths['logs_dir'])

    for base in search_folders:
        posible = base / filename
        if posible.exists():
            target = posible
            break

    if target and target.exists():
        try:
            os.remove(target)
            flash(f"🗑️ '{filename}' eliminado.", "success")
        except Exception as e:
            flash(f"❌ Error al eliminar: {e}", "danger")
    
    return redirect(url_for('main.index'))