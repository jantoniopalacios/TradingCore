import os
import threading
import csv
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, jsonify, Response, send_from_directory, abort
)
from collections import deque

# --- IMPORTACIONES ORIGINALES ---
from ..file_handler import read_symbols_raw, write_symbols_raw, get_directory_tree
from ..configuracion import (
    guardar_parametros_a_env, inicializar_configuracion_usuario,
    cargar_y_asignar_configuracion, System, BACKTESTING_BASE_DIR
) 
from trading_engine.core.constants import VARIABLE_COMMENTS
from ..Backtest import ejecutar_backtest 

main_bp = Blueprint('main', __name__) 

# --- FUNCIONES DE SOPORTE (Manteniendo tu lógica de usuarios) ---
def obtener_usuarios_registrados():
    usuarios = {}
    ruta_usuarios = BACKTESTING_BASE_DIR / "users.csv"
    if not ruta_usuarios.exists(): return {"admin": "trading"} 
    try:
        with open(ruta_usuarios, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                usuarios[row['username'].strip().lower()] = row['password'].strip()
    except: pass
    return usuarios

def get_user_paths(username):
    rutas = inicializar_configuracion_usuario(username)
    return {
        'results_dir': rutas['results_dir'],
        'graph_dir': rutas['graph_dir'],
        'logs_dir': BACKTESTING_BASE_DIR / "logs",
        'fichero_simbolos': rutas['fichero_simbolos']
    }

# --- RUTA PRINCIPAL (INDEX) ---
@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))

    user_mode = session.get('user_mode')
    rutas = inicializar_configuracion_usuario(user_mode)

    if request.method == 'POST':
        form_data = request.form.to_dict()
        
        # 1. Guardar Símbolos (symbols_content)
        if 'symbols_content' in form_data:
            write_symbols_raw(form_data['symbols_content'], rutas['fichero_simbolos'])
        
        # 2. Configuración (.env)
        env_config = {k: v for k, v in form_data.items() if k != 'symbols_content'}

        # GESTIÓN DE SWITCHES (Booleanos)
        for attr in dir(System):
            if not attr.startswith("__"):
                val_original = getattr(System, attr)
                if isinstance(val_original, bool):
                    # En Flask/HTML, si el checkbox no se marca, no llega en form_data
                    env_config[attr] = "True" if attr in form_data else "False"

        guardar_parametros_a_env(env_config, user_mode)
        cargar_y_asignar_configuracion(user_mode)
        
        flash("✅ Configuración guardada correctamente.", "success")
        return redirect(url_for('main.index'))

    # --- FLUJO GET (Renderizado de pestañas) ---
    cargar_y_asignar_configuracion(user_mode)
    
    # NORMALIZACIÓN PARA HTML:
    config_web = {}
    for attr in dir(System):
        if not attr.startswith("__"):
            val = getattr(System, attr)
            config_web[attr] = str(val).strip() if val is not None else "None"

    # --- CONSTRUCCIÓN DEL ÁRBOL DE ARCHIVOS (Formato Diccionario) ---
    file_tree = []
    
    # 1. Carpeta de Resultados
    if rutas['results_dir'].exists():
        file_tree.append({
            "name": "Resultados",
            "is_dir": True,
            "children": get_directory_tree(rutas['results_dir'], user_mode == 'admin'),
            "type": "Folder",
            "path": "Resultados"
        })

    # 2. Carpeta de Gráficos
    if rutas['graph_dir'].exists():
        file_tree.append({
            "name": "Gráficos",
            "is_dir": True,
            "children": get_directory_tree(rutas['graph_dir'], user_mode == 'admin'),
            "type": "Folder",
            "path": "Gráficos"
        })
    
    # 3. Logs de Sistema (Solo para Admin)
    if user_mode == 'admin':
        logs_p = BACKTESTING_BASE_DIR / "logs"
        if logs_p.exists():
            file_tree.append({
                "name": "Logs Sistema",
                "is_dir": True,
                "children": get_directory_tree(logs_p, True),
                "type": "Folder",
                "path": "Logs"
            })

    # Historial de Resultados (Base de Datos)
    registros = []
    try:
        from ..database import Usuario, ResultadoBacktest
        u = Usuario.query.filter_by(username=user_mode).first()
        if u:
            registros = ResultadoBacktest.query.filter_by(usuario_id=u.id).order_by(ResultadoBacktest.fecha_ejecucion.desc()).limit(20).all()
    except Exception as e:
        print(f"Error al cargar historial SQL: {e}")

    return render_template(
        'index.html',
        system=System,
        strategy=System,
        config=config_web,
        symbols_content=read_symbols_raw(rutas['fichero_simbolos']) if rutas['fichero_simbolos'].exists() else "",
        file_tree=file_tree,
        registros=registros,
        comments=VARIABLE_COMMENTS
    )

# --- ACCIONES Y VISOR (Todas las funciones restauradas) ---

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    if not session.get('logged_in'): return jsonify({"status": "error"}), 401
    config_web = request.form.to_dict()
    config_web['user_mode'] = session.get('user_mode')
    # Ejecutar el motor de backtest en segundo plano
    threading.Thread(target=ejecutar_backtest, args=(config_web,)).start()
    return jsonify({"status": "success", "message": "Backtest iniciado."})

@main_bp.route('/file/<path:path>')
def view_file(path):
    if not session.get('logged_in'): abort(401)
    user_mode = session.get('user_mode')
    paths = get_user_paths(user_mode)
    filename = os.path.basename(path)
    
    # Búsqueda recursiva para encontrar archivos en subcarpetas de resultados/gráficos
    target = None
    search_dirs = [paths['results_dir'], paths['graph_dir']]
    if user_mode == 'admin': search_dirs.append(paths['logs_dir'])

    for folder in search_dirs:
        for p in folder.rglob(filename):
            if p.is_file():
                target = p; break
        if target: break

    if not target: abort(404)
    
    if target.suffix.lower() == '.html':
        return send_from_directory(target.parent, target.name)
    
    # Lectura de archivos de texto / logs (últimas 2000 líneas para logs)
    with open(target, 'r', encoding='utf-8', errors='replace') as f:
        contenido = "".join(deque(f, maxlen=2000)) if target.suffix.lower() == '.log' else f.read()
    return Response(contenido, mimetype='text/plain')

@main_bp.route('/delete-file/<path:path>', methods=['POST'])
def delete_file(path):
    if not session.get('logged_in'): abort(401)
    user_mode = session.get('user_mode')
    paths = get_user_paths(user_mode)
    filename = os.path.basename(path)
    
    for folder in [paths['results_dir'], paths['graph_dir']]:
        target = folder / filename
        if target.exists():
            os.remove(target)
            flash(f"Archivo {filename} eliminado.", "info")
            break
    return redirect(url_for('main.index'))

# --- AUTENTICACIÓN ---

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').lower().strip()
        pwd = request.form.get('password', '').strip()
        users = obtener_usuarios_registrados()
        
        if user in users and users[user] == pwd:
            session.clear()
            session['logged_in'] = True
            session['user_mode'] = user
            return redirect(url_for('main.index'))
        flash("❌ Usuario o contraseña incorrectos", "danger")
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))