# scenarios/BacktestWeb/routes/main_bp.py

import os
import threading
import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, send_from_directory, current_app, abort, session, jsonify
)
from pathlib import Path

# ----------------------------------------------------------------------
# --- IMPORTACIONES DE LA ARQUITECTURA ---
# ----------------------------------------------------------------------

from ..file_handler import ( 
    read_config_with_metadata, 
    read_symbols_raw, write_symbols_raw,
    get_directory_tree
)

from ..configuracion import (
    guardar_parametros_a_env,
    inicializar_configuracion_usuario,
    System 
) 

from trading_engine.core.constants import VARIABLE_COMMENTS
from ..Backtest import ejecutar_backtest 

# ----------------------------------------------------------------------
# --- CONFIGURACIÓN Y BLUEPRINT ---
# ----------------------------------------------------------------------

main_bp = Blueprint('main', __name__) 


# ----------------------------------------------------------------------
# --- USUARIOS PERMITIDOS (SIMPLIFICADO) ---
# ----------------------------------------------------------------------
USUARIOS_PERMITIDOS = {
    "juan": "trading",
    "pedro": "trading",
    "fernando": "trading",
    "invitado": "trading"
}

# ----------------------------------------------------------------------
# --- RUTAS DE AUTENTICACIÓN ---
# ----------------------------------------------------------------------

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username').lower()
        password = request.form.get('password')

        if user in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[user] == password:
            session['logged_in'] = True
            session['user_mode'] = user
            
            rutas = inicializar_configuracion_usuario(user)
            for key, value in rutas.items():
                current_app.config[key] = value
            current_app.config['user_mode'] = user

            flash(f"✅ Bienvenido, {user.capitalize()}", "success")
            return redirect(url_for('main.index'))
        
        flash("❌ Usuario o contraseña incorrectos", "danger")
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for('main.login'))

# ----------------------------------------------------------------------
# --- RUTA PRINCIPAL ---
# ----------------------------------------------------------------------

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))
    
    f_var = current_app.config.get('fichero_variables')
    f_sym = current_app.config.get('fichero_simbolos')
    user_mode = session.get('user_mode')
    
    results_path = Path(current_app.config.get('results_dir'))
    graphics_path = Path(current_app.config.get('graph_dir'))

    file_tree = []
    if results_path.exists():
        file_tree.append(("Resultados", True, get_directory_tree(results_path), ""))
    if graphics_path.exists():
        file_tree.append(("Gráficos", True, get_directory_tree(graphics_path), ""))

    config_data, _ = read_config_with_metadata(f_var)
    if config_data is None: config_data = {} 
    symbols_content_data = read_symbols_raw(f_sym)

    if request.method == 'POST':
        form_data = dict(request.form)
        symbols_content_to_save = form_data.pop('symbols_content', None) 
        if symbols_content_to_save is not None:
            write_symbols_raw(symbols_content_to_save, f_sym)

        try:
            guardar_parametros_a_env(form_data, user_mode) 
            flash(f"✅ Configuración guardada para {user_mode}.", 'success')
        except Exception as e:
            flash(f"❌ Error al guardar: {e}", 'danger')
            
        return redirect(url_for('main.index'))

    return render_template(
        'index.html', 
        config=config_data,
        comments=VARIABLE_COMMENTS, 
        symbols_content=symbols_content_data,
        file_tree=file_tree,
        backtesting_dir_name=user_mode,
        strategy=System
    )

# ----------------------------------------------------------------------
# --- RUTAS DE EJECUCIÓN ---
# ----------------------------------------------------------------------

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    config_web = request.form.to_dict()
    config_web['user_mode'] = session.get('user_mode')
    
    thread = threading.Thread(target=ejecutar_backtest, args=(config_web,))
    thread.start()
    
    return jsonify({"status": "success", "message": f"Backtest iniciado para {config_web['user_mode']}"})

@main_bp.route('/file/<path:path>')
def view_file(path):
    if not session.get('logged_in'): abort(401)
    
    results_dir = Path(current_app.config.get('results_dir'))
    graph_dir = Path(current_app.config.get('graph_dir'))
    filename = os.path.basename(path)
    
    target_file = None
    if (results_dir / filename).exists():
        target_file = results_dir / filename
    elif (graph_dir / filename).exists():
        target_file = graph_dir / filename

    if not target_file or not target_file.is_file():
        abort(404)

    return send_from_directory(target_file.parent, target_file.name, as_attachment=False)

@main_bp.route('/delete-file/<path:path>', methods=['POST'])
def delete_file(path):
    if not session.get('logged_in'): abort(401)
    
    results_dir = Path(current_app.config.get('results_dir'))
    graph_dir = Path(current_app.config.get('graph_dir'))
    filename = os.path.basename(path)
    
    target_file = None
    if (results_dir / filename).exists():
        target_file = results_dir / filename
    elif (graph_dir / filename).exists():
        target_file = graph_dir / filename

    if target_file and target_file.exists():
        try:
            os.remove(target_file)
            flash(f"🗑️ '{filename}' eliminado.", "success")
        except Exception as e:
            flash(f"❌ Error al eliminar: {e}", "danger")
    
    return redirect(url_for('main.index'))

# ----------------------------------------------------------------------
# --- CONSOLA Y LOGS ---
# ----------------------------------------------------------------------

@main_bp.route('/get_logs')
def get_logs():
    if not session.get('logged_in'): return "No autorizado"

    from ..configuracion import PROJECT_ROOT
    log_path = Path(PROJECT_ROOT) / "trading_app.log"
    
    if log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                return "".join(lines[-35:])
        except Exception as e:
            return f"Error leyendo logs: {str(e)}"
    
    return "Iniciando sistema de logs..."

@main_bp.route('/console')
def console(): # CAMBIO: Nombre restaurado a 'console' para coincidir con url_for('main.console')
    if not session.get('logged_in'): return redirect(url_for('main.login'))
    return render_template('_tab_console.html')