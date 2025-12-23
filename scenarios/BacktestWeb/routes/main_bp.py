# scenarios/BacktestWeb/routes/main_bp.py

import os
import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, send_from_directory, current_app, abort
)
from pathlib import Path
from multiprocessing import Process

# ----------------------------------------------------------------------
# --- IMPORTACIONES DE LA ARQUITECTURA ---
# ----------------------------------------------------------------------

# 1. Importamos la lógica de I/O modularizada
from ..file_handler import ( 
    read_config_with_metadata, 
    read_symbols_raw, write_symbols_raw,
    get_directory_tree
)

# 2. Importamos las FUNCIONES (ya no las variables estáticas)
from ..configuracion import (
    guardar_parametros_a_env,
    System 
) 

# 3. Importamos los COMENTARIOS (Ruta absoluta desde la raíz)
from trading_engine.core.constants import VARIABLE_COMMENTS

# 4. Importamos la función de orquestación del backtest
from ..Backtest import ejecutar_backtest 

# ----------------------------------------------------------------------
# --- CREAR BLUEPRINT ---
# ----------------------------------------------------------------------
main_bp = Blueprint('main', __name__) 

# ----------------------------------------------------------------------
# --- RUTAS DE CONFIGURACIÓN Y EJECUCIÓN ---
# ----------------------------------------------------------------------

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    """Muestra el formulario de configuración y maneja el guardado."""
    
    # 🌟 Obtención de rutas desde la configuración inyectada
    f_var = current_app.config.get('fichero_variables')
    f_sym = current_app.config.get('fichero_simbolos')
    user_mode = current_app.config.get('user_mode')
    
    # Capturamos ambas rutas como objetos Path
    results_path = Path(current_app.config.get('results_dir'))
    graphics_path = Path(current_app.config.get('graph_dir'))

    # 🎯 CONSTRUCCIÓN DEL ÁRBOL VIRTUAL
    # Combinamos ambas ramas en una sola lista para la pestaña "Ficheros"
    file_tree = []
    if results_path.exists():
        # Añadimos la carpeta física de resultados al árbol
        file_tree.append(("Resultados", True, get_directory_tree(results_path),""))
    
    if graphics_path.exists():
        # Añadimos la carpeta física de gráficos al árbol
        file_tree.append(("Graphics", True, get_directory_tree(graphics_path),""))

    # Cargar datos técnicos
    config_data, _ = read_config_with_metadata(f_var)
    if config_data is None: config_data = {} 
    symbols_content_data = read_symbols_raw(f_sym)

    # Lógica de guardado (POST)
    if request.method == 'POST':

        form_data = dict(request.form)

        # 2. AHORA ya podemos hacer los prints de debug
        print("--- DEBUG POST ---")
        print(f"Campos recibidos: {list(form_data.keys())}")

        symbols_content_to_save = form_data.pop('symbols_content', None) 
        if symbols_content_to_save is not None:
            write_symbols_raw(symbols_content_to_save, f_sym)

        try:
            guardar_parametros_a_env(form_data, user_mode) 
            flash(f"✅ Configuración guardada para {user_mode}.", 'success')
        except Exception as e:
            flash(f"❌ Error al guardar: {e}", 'danger')
            
        return redirect(url_for('main.index'))

    # ⚠️ CORRECCIÓN AQUÍ: 
    # 'b_dir.name' fallaría porque b_dir no existe. Usamos 'user_mode' para el título.
    return render_template(
        'index.html', 
        config=config_data,
        comments=VARIABLE_COMMENTS, 
        symbols_content=symbols_content_data,
        file_tree=file_tree,
        backtesting_dir_name=user_mode, # Identificador del entorno actual
        strategy=System
    )

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    """Ejecuta el backtest en un proceso separado inyectando el contexto de usuario."""
    f_var = current_app.config.get('fichero_variables')
    
    try:
        # 1. Obtenemos los parámetros técnicos (.env)
        config_data, _ = read_config_with_metadata(f_var)
        if not config_data:
            flash("❌ Error al cargar configuración técnica.", 'danger')
            return redirect(url_for('main.index'))
            
        # 2. 🎯 EL PASO CLAVE: Inyectamos la identidad y rutas de Flask en config_data
        # Esto asegura que el proceso hijo sepa quién es y dónde escribir.
        config_data['user_mode'] = current_app.config.get('user_mode')
        config_data['graph_dir'] = current_app.config.get('graph_dir')
        config_data['results_dir'] = current_app.config.get('results_dir')
        config_data['fichero_simbolos'] = current_app.config.get('fichero_simbolos')

    except Exception as e:
        flash(f"❌ Error al preparar configuración: {e}", 'danger')
        return redirect(url_for('main.index'))

    try:
        current_app.logger.info(f"🚀 Lanzando motor para: {config_data['user_mode']}")
        
        # 3. Ahora config_data lleva TODO lo necesario para que Backtest.py trabaje en la carpeta correcta
        p = Process(target=ejecutar_backtest, args=(config_data,))
        p.start() 
        
        flash(f"✅ Backtest iniciado para {config_data['user_mode']}. Revisa la pestaña 'Ficheros' en unos segundos.", 'success')
    except Exception as e:
        flash(f"❌ Error crítico al lanzar el proceso: {e}", 'danger')

    return redirect(url_for('main.index'))

@main_bp.route('/file/<path:path>')
def view_file(path):
    """Busca el archivo solo dentro de las carpetas del usuario actual."""
    from ..configuracion import PROJECT_ROOT
    
    # 1. Obtenemos el usuario actual desde la configuración de la app
    user_mode = current_app.config.get('user_mode', 'invitado')
    filename = os.path.basename(path)
    
    # 2. Definimos la base de búsqueda: La carpeta Backtesting
    base_dir = Path(PROJECT_ROOT) / "Backtesting"
    
    # 3. BÚSQUEDA RESTRINGIDA AL USUARIO
    target_file = None
    for root, dirs, files in os.walk(base_dir):
        # 🎯 LA CLAVE: Solo aceptamos el archivo si en su ruta está el nombre del usuario
        if filename in files and user_mode in root:
            target_file = Path(root) / filename
            break

    if not target_file:
        # Si no lo encuentra con el nombre de usuario, buscamos en Config (que es común)
        config_path = base_dir / "Config" / filename
        if config_path.exists():
            target_file = config_path

    if not target_file or not target_file.exists():
        current_app.logger.error(f"❌ Archivo {filename} no encontrado para el usuario {user_mode}")
        abort(404)

    current_app.logger.info(f"✅ Archivo CORRECTO localizado: {target_file}")
    
    return send_from_directory(target_file.parent, target_file.name, as_attachment=False)



@main_bp.route('/delete-file/<path:path>', methods=['POST'])
def delete_file(path):
    """Borra un archivo de forma segura dentro de la carpeta del usuario."""
    from ..configuracion import PROJECT_ROOT
    
    user_mode = current_app.config.get('user_mode', 'invitado')
    base_dir = Path(PROJECT_ROOT) / "Backtesting"
    
    # Buscamos el archivo físicamente asegurándonos de que pertenece al usuario
    filename = os.path.basename(path)
    target_file = None
    
    for root, dirs, files in os.walk(base_dir):
        if filename in files and user_mode in root:
            target_file = Path(root) / filename
            break

    if target_file and target_file.exists():
        try:
            os.remove(target_file)
            flash(f"🗑️ Archivo '{filename}' eliminado correctamente.", "success")
        except Exception as e:
            flash(f"❌ Error al eliminar el archivo: {e}", "danger")
    else:
        flash("❌ No se encontró el archivo o no tienes permisos para borrarlo.", "danger")

    return redirect(url_for('main.index'))

@main_bp.route('/get_logs')
def get_logs():
    """Devuelve las últimas líneas del archivo de log para la consola web."""
    # Buscamos el archivo en la raíz del proyecto
    from ..configuracion import PROJECT_ROOT
    log_path = Path(PROJECT_ROOT) / "trading_app.log"
    
    if log_path.exists():
        try:
            # Abrimos con 'errors="ignore"' para evitar fallos por caracteres especiales
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Leemos las últimas 30 líneas para dar contexto
                lines = f.readlines()
                return "".join(lines[-30:])
        except Exception as e:
            return f"Error al leer logs: {str(e)}"
    
    return "Esperando logs del sistema..."

@main_bp.route('/console')
def console():
    """Renderiza la página de la consola dedicada."""
    return render_template('_tab_console.html')