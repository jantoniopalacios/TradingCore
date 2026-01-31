import os
import threading
import csv
import io
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

from ..database import db, ResultadoBacktest, Trade, Usuario, Simbolo # Importa tus modelos
from sqlalchemy import func
from datetime import datetime

main_bp = Blueprint('main', __name__) 

def obtener_usuarios_registrados():
    
    try:
        usuarios = {u.username.lower(): u.password for u in Usuario.query.all()}
        return usuarios
    except:
        return {"admin": "admin"} # Fallback de emergencia

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

    import json
    user_mode = session.get('user_mode')
    u = Usuario.query.filter_by(username=user_mode).first()

    # ================================================================
    # --- LÓGICA POST (Guardado de Configuración en DB) ---
    # ================================================================
    if request.method == 'POST' and request.form.get('action') == 'save_config':
        form_data = request.form.to_dict()
        
        # 1. Guardar Símbolos (Tu lógica actual en DB que ya funciona)
        if 'symbols_content' in form_data:
            contenido = form_data['symbols_content']
            raw_activos = contenido.replace(';', ',').replace('\n', ',').replace('\r', ',')
            lista_nombres_simbolos = [s.strip().upper() for s in raw_activos.split(',') if s.strip()]
            lista_nombres_simbolos = list(dict.fromkeys(lista_nombres_simbolos))
            
            try:
                Simbolo.query.filter_by(usuario_id=u.id).delete()
                for sym_name in lista_nombres_simbolos:
                    nuevo_simbolo = Simbolo(symbol=sym_name, name=sym_name, usuario_id=u.id)
                    db.session.add(nuevo_simbolo)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f"Error símbolos: {e}", "danger")

        # 2. Guardar Parámetros Técnicos en Usuario.config_actual
        config_params = {k: v for k, v in form_data.items() if k not in ['symbols_content', 'action']}

        # --- LISTA MAESTRA DE SWITCHES (Basada en tus .html) ---
        lista_switches = [
            'macd', 'rsi', 'ema_cruce_signal', 'bb_active', 'bb_buy_crossover', 'bb_sell_crossover',
            'filtro_fundamental', 'enviar_mail', 'margen_seguridad_active', 
            'margen_seguridad_ascendente', 'volume_active', 'volume_ascendente',
            'stoch_fast', 'stoch_mid', 'stoch_slow' # Si estos son switches en tu UI
        ]

        for s in lista_switches:
            # FORZAMOS EL TEXTO 'True' o 'False' para que el HTML lo reconozca
            if s in form_data:
                config_params[s] = 'True'
            else:
                config_params[s] = 'False'

        try:
            u.config_actual = json.dumps(config_params) # Guardamos como JSON
            db.session.commit()
            flash("✅ Configuración guardada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar config: {e}", "danger")

        return redirect(url_for('main.index'))

    # ================================================================
    # --- LÓGICA GET (Carga de la página desde DB) ---
    # ================================================================
    
    # Intentamos cargar la configuración guardada del usuario
    config_para_web = {}
    if u and u.config_actual:
        try:
            config_para_web = json.loads(u.config_actual) if isinstance(u.config_actual, str) else u.config_actual
        
            # --- NORMALIZADOR PARA EL HTML ---
            # Esto convierte cualquier True booleano en "True" texto al vuelo
            for key, value in config_para_web.items():
                if value is True:
                    config_para_web[key] = 'True'
                elif value is False:
                    config_para_web[key] = 'False'
        except:
            config_para_web = {}

    # Si el usuario no tiene nada guardado, usamos los valores por defecto de la clase System
    if not config_para_web:
        for attr in dir(System):
            if not attr.startswith("__"):
                val = getattr(System, attr)
                if not callable(val):
                    config_para_web[attr] = str(val)

    # Preparar símbolos para el textarea
    simbolos_db = Simbolo.query.filter_by(usuario_id=u.id).all() if u else []
    symbols_text = ", ".join([s.symbol for s in simbolos_db]) if simbolos_db else "AAPL, MSFT"

    # Historial de resultados (Ordenado por fecha descendente)
    registros_agrupados = {}
    try:
        # 1. Traemos los registros ordenados por fecha desde la base de datos
        query_base = ResultadoBacktest.query.order_by(ResultadoBacktest.fecha_ejecucion.desc())
        
        if user_mode == 'admin':
            todos = query_base.all()
        else:
            todos = query_base.filter_by(usuario_id=u.id).all()
        
        # 2. Agrupamos manteniendo el orden de aparición (que ya viene ordenado por fecha)
        for r in todos:
            # La tanda_key identifica el grupo (por id_estrategia)
            tanda_key = f"{r.usuario_id}_{r.id_estrategia}" if user_mode == 'admin' else r.id_estrategia
            
            if tanda_key not in registros_agrupados:
                registros_agrupados[tanda_key] = {
                    'id_tanda': r.id_estrategia,
                    'usuario_id': r.usuario_id,
                    'fecha_raw': r.fecha_ejecucion, # Guardamos el objeto datetime para ordenar
                    'fecha': r.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
                    'usuario_nombre': r.propietario.username,
                    'activos': []
                }
            registros_agrupados[tanda_key]['activos'].append(r)
            
    except Exception as e:
        print(f"Error historial: {e}")

    # 3. EL CAMBIO FINAL: Ordenar el diccionario de tandas por la fecha del primer elemento de cada tanda
    # Esto garantiza que la Tanda #10 aparezca antes que la #9 si se hizo después.
    tandas_ordenadas = dict(sorted(
        registros_agrupados.items(), 
        key=lambda x: x[1]['fecha_raw'], 
        reverse=True
    ))

# Inicializamos vacío por seguridad
    arbol_ficheros = []

    # SOLO escaneamos si el usuario es admin
    if user_mode == 'admin':
        logs_dir = BACKTESTING_BASE_DIR / "logs"
        if logs_dir.exists():
            arbol_ficheros = get_directory_tree(logs_dir, is_admin=True)

    return render_template(
        'index.html',
        system=System,
        strategy=System,
        config=config_para_web,
        symbols_content=symbols_text,
        file_tree=arbol_ficheros, 
        registros=tandas_ordenadas, # Enviamos las tandas ya ordenadas
        comments=VARIABLE_COMMENTS
    )

# --- ACCIONES Y VISOR (Todas las funciones restauradas) ---

#-- RUTA PARA OBTENER PARÁMETROS DE LA ESTRATEGIA EN FORMATO JSON --
@main_bp.route('/get_strategy_params/<int:reg_id>')
def get_strategy_params(reg_id):
    from ..database import ResultadoBacktest
    import json
    
    res = ResultadoBacktest.query.get_or_404(reg_id)
    if not res.params_tecnicos:
        return jsonify({"error": "Sin parámetros"}), 404
    
    try:
        raw_data = json.loads(res.params_tecnicos)
        # Filtramos solo lo que sea legible (números, texto, booleanos)
        clean_params = {k: v for k, v in raw_data.items() 
                        if isinstance(v, (str, int, float, bool)) or v is None}
        
        # Añadimos los valores fijos de la tabla para que la vista sea completa
        clean_params.update({
            "Cash_Inicial": res.cash_inicial,
            "Comision": res.comision,
            "Fecha_Inicio": res.fecha_inicio_datos,
            "Fecha_Fin": res.fecha_fin_datos,
            "Intervalo": res.intervalo
        })
        return jsonify(clean_params)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#-- FUNCIÓN PARA EJECUTAR BACKTEST EN HILO SEPARADO --
def run_backtest_and_save(app_instance, config_web, user_mode):
    """Ejecuta el motor. El guardado en SQL (incluyendo el gráfico) ya ocurre dentro de Backtest.py"""
    # En Postgres, es vital que cada hilo gestione su propia limpieza de sesión
    with app_instance.app_context():
        try:
            # 1. Llamada al motor. 
            resultados_df, trades_df, graficos_dict = ejecutar_backtest(config_web)
            # El motor ya hace el commit, pero cerramos explícitamente al final del hilo
            db.session.remove()  # Limpieza de sesión tras ejecución
            if resultados_df is not None and not resultados_df.empty:
                print(f"✅ Backtest finalizado para {user_mode}. Datos y gráficos procesados por el motor.")
            else:
                print(f"⚠️ El backtest para {user_mode} no generó resultados.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR en hilo local: {e}")
        finally:
            db.session.remove()

#-- RUTA PARA LANZAR BACKTEST (POST) --
import logging
import traceback

# Obtenemos el logger configurado en tu app
logger = logging.getLogger(__name__)

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    
    try:
        if not session.get('logged_in'): 
            return jsonify({"status": "error"}), 401
        
        user_mode = session.get('user_mode')
        u = Usuario.query.filter_by(username=user_mode).first()
        if not u:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        # 1. Cargamos configuración base del disco
        cargar_y_asignar_configuracion(user_mode)
        
        # 2. Capturamos el formulario
        form_data = request.form.to_dict()
        config_web = {}

        # 1. Cargar valores por defecto de la clase System
        for attr in dir(System):
            if not attr.startswith("__"):
                val = getattr(System, attr)
                if not callable(val):
                    config_web[attr] = val

        # 2. LISTA MAESTRA DE BOOLEANOS (Switches de tu UI)
        # Asegúrate de que los nombres coincidan exactamente con el 'name' en tu HTML
        switches = [
            'macd', 'rsi', 'ema_cruce_signal', 'bb_active', 'bb_buy_crossover', 
            'bb_sell_crossover', 'filtro_fundamental', 'enviar_mail', 
            'margen_seguridad_active', 'volume_active', 'stoch_fast', 'stoch_mid', 'stoch_slow'
        ]

        # 3. PROCESAR EL FORMULARIO
        for key, value in form_data.items():
            if key in switches:
                config_web[key] = True  # Si llegó en el POST, es que estaba ON
            elif value == "" or value.lower() == 'none':
                config_web[key] = None
            else:
                # Intentar convertir a número para el motor
                try:
                    config_web[key] = float(value) if '.' in value else int(value)
                except:
                    config_web[key] = value

        # 4. EL PASO CRUCIAL: Si un switch NO vino en el form_data, forzarlo a False
        for s in switches:
            if s not in form_data:
                config_web[s] = False

        # 6. Metadatos cruciales para el motor
        config_web['user_id'] = u.id 
        config_web['user_mode'] = user_mode # <--- FUNDAMENTAL para que Backtest.py sepa quién es
        
        ultima_tanda = db.session.query(func.max(ResultadoBacktest.id_estrategia)).filter_by(usuario_id=u.id).scalar()
        config_web['tanda_id'] = (ultima_tanda + 1) if ultima_tanda is not None else 1
        
        logger.info(f"🚀 LANZANDO HILO: Usuario={user_mode} (ID={u.id}) Tanda #{config_web['tanda_id']}")

        # 7. Lanzar el hilo con el contexto de la app
        from flask import current_app
        app_instance = current_app._get_current_object()

        threading.Thread(
            target=run_backtest_and_save, 
            args=(app_instance, config_web, user_mode)
        ).start()

        return jsonify({"status": "success", "message": "Iniciado correctamente"})

    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN LAUNCH:\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

#-- RUTA PARA VER ARCHIVOS DE LOGS --
@main_bp.route('/view_file/<path:path>')
def view_file(path):
    if not session.get('logged_in'):
        return "No autorizado", 401
    
    # Usamos la constante global para evitar errores de ruta relativa
    # Como el explorador lista desde la carpeta "logs", concatenamos adecuadamente
    logs_dir = BACKTESTING_BASE_DIR / "logs"
    full_path = logs_dir / os.path.basename(path) # Evitamos saltos de directorio por seguridad

    if not full_path.exists():
        return f"Archivo no encontrado en: {full_path}", 404

    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            # Mandamos las últimas 1000 líneas
            content = "".join(deque(f, maxlen=1000))
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return f"Error: {str(e)}", 500

#-- RUTA PARA ELIMINAR ARCHIVOS DE LOGS --
@main_bp.route('/delete-file/<path:path>', methods=['POST'])
def delete_file(path):
    if not session.get('logged_in'): abort(401)
    user_mode = session.get('user_mode')
    
    # Solo permitimos borrar archivos de la carpeta Logs y solo si es Admin
    if user_mode != 'admin':
        flash("No tienes permiso para eliminar archivos del servidor.", "danger")
        return redirect(url_for('main.index'))

    filename = os.path.basename(path)
    logs_dir = BACKTESTING_BASE_DIR / "logs"
    target = logs_dir / filename

    if target.exists() and target.is_file():
        try:
            os.remove(target)
            flash(f"Archivo de log {filename} eliminado.", "info")
        except Exception as e:
            flash(f"Error al eliminar: {e}", "danger")
    else:
        flash("El archivo no existe o no es un log.", "warning")

    return redirect(url_for('main.index'))

# Fecha y hora: 2026-01-31 13:47
# En main_bp.py

@main_bp.route('/admin/visor_logs')
def visor_logs():
    if not session.get('logged_in') or session.get('user_mode') != 'admin':
        abort(403)

    logs_dir = BACKTESTING_BASE_DIR / "logs"
    target = logs_dir / "trading_app.log"
    
    if not target.exists():
        return "El archivo de log no existe aún.", 404

    lista_logs = []
    with open(target, 'r', encoding='utf-8', errors='replace') as f:
        # Leemos las últimas 500 líneas
        for linea in deque(f, maxlen=500):
            # El formato en app.py es: '%(asctime)s - %(levelname)s - %(message)s'
            # Dividimos por el guion con espacios para extraer las partes
            partes = linea.split(' - ')
            if len(partes) >= 3:
                lista_logs.append({
                    'timestamp': partes[0],
                    'nivel': partes[1],
                    'mensaje': " - ".join(partes[2:]) # Por si el mensaje contiene guiones
                })

    return render_template('admin_logs.html', logs=reversed(lista_logs))

# Fecha y hora: 2026-01-31 14:18
# En main_bp.py

@main_bp.route('/get_log_json/<path:path>')
def get_log_json(path):
    if not session.get('logged_in') or session.get('user_mode') != 'admin':
        abort(403)
    
    filename = os.path.basename(path)
    logs_dir = BACKTESTING_BASE_DIR / "logs"
    target = logs_dir / filename

    if not target.exists(): abort(404)

    logs_parsed = []
    with open(target, 'r', encoding='utf-8', errors='replace') as f:
        for linea in deque(f, maxlen=1000): # Últimas 1000 líneas
            # Ajustamos al formato: 2026-01-30 23:21:19,388 - INFO - Mensaje
            try:
                partes = linea.split(' - ', 2)
                if len(partes) >= 3:
                    logs_parsed.append({
                        'timestamp': partes[0],
                        'level': partes[1].strip(),
                        'message': partes[2].strip()
                    })
                else:
                    logs_parsed.append({'timestamp': '', 'level': 'DEBUG', 'message': linea})
            except:
                continue

    return jsonify(logs_parsed)

#-- RUTA PARA OBTENER TRADES EN FORMATO JSON --
@main_bp.route('/get_trades/<int:backtest_id>')
def get_trades(backtest_id):
    """Devuelve los trades de un activo específico en formato JSON para el modal."""
    if not session.get('logged_in'):
        return jsonify([]), 401
    
    try:
        # Buscamos los trades asociados al ID único del ResultadoBacktest
        trades = Trade.query.filter_by(backtest_id=backtest_id).all()

        # TIP: Si ves ceros en la web, mira este log:
        print(f"DEBUG: Enviando {len(trades)} trades para el ID {backtest_id}")
        
        return jsonify([{
            'tipo': t.tipo,
            'descripcion': t.descripcion,
            'fecha': t.fecha,
            'entrada': float(t.precio_entrada),
            'salida': float(t.precio_salida),
            'pnl': float(t.pnl_absoluto),
            'retorno': float(t.retorno_pct)
        } for t in trades])
    except Exception as e:
        print(f"Error al obtener trades: {e}")
        return jsonify([]), 500

# -- EXPORTAR TANDA A CSV --
@main_bp.route('/export_tanda/<int:tanda_id>')
def export_tanda(tanda_id):
    if not session.get('logged_in'): return "No autorizado", 401
    user_mode = session.get('user_mode')
    
    try:
        # 1. Buscamos al usuario de la sesión
        u = Usuario.query.filter_by(username=user_mode).first()
        
        # 2. Filtramos la tanda SOLO para este usuario
        resultados = ResultadoBacktest.query.filter_by(id_estrategia=tanda_id, usuario_id=u.id).all()
        ids_resultados = [r.id for r in resultados]
        
        trades = Trade.query.filter(Trade.backtest_id.in_(ids_resultados)).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Usuario', 'Tanda', 'Activo', 'Tipo', 'Fecha', 'Entrada', 'Salida', 'PnL_Abs', 'Retorno_Pct'])

        for t in trades:
            writer.writerow([
                user_mode, tanda_id, t.backtest.symbol, t.tipo, t.fecha, 
                t.precio_entrada, t.precio_salida, t.pnl_absoluto, t.retorno_pct
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=Mi_Tanda_{tanda_id}.csv"}
        )
    except Exception as e:
        return f"Error: {e}", 500

# -- EXPORTAR TODOS LOS TRADES (ADMIN) --
@main_bp.route('/export_todo_admin')
def export_todo_admin():
    if session.get('user_mode') != 'admin':
        return "Acceso denegado", 403
    
    try:
        # El admin descarga TODOS los trades de la base de datos
        trades = Trade.query.all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Usuario Propietario', 'ID Tanda', 'Activo', 'Tipo', 'Fecha', 'Entrada', 'Salida', 'PnL_Abs', 'Retorno_Pct'])

        for t in trades:
            writer.writerow([
                t.backtest.propietario.username,
                t.backtest.id_estrategia,
                t.backtest.symbol,
                t.tipo, t.fecha, t.precio_entrada, 
                t.precio_salida, t.pnl_absoluto, t.retorno_pct
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=HISTORIAL_GLOBAL_SISTEMA.csv"}
        )
    except Exception as e:
        return f"Error en exportación global: {e}", 500
    
# -- RUTA PARA ELIMINAR BACKTESTS DE UNA TANDA --
@main_bp.route('/eliminar_backtest/<int:id_estrategia>/<int:usuario_id>', methods=['POST'])
def eliminar_backtest(id_estrategia, usuario_id):
    try:
        user_mode = session.get('user_mode')
        
        # Filtro de seguridad para el Admin
        if user_mode == 'admin':
            activos = ResultadoBacktest.query.filter_by(
                id_estrategia=id_estrategia, 
                usuario_id=usuario_id
            ).all()
        else:
            # Usuario normal solo borra lo suyo
            u = Usuario.query.filter_by(username=user_mode).first()
            if u.id != usuario_id:
                flash("No tienes permiso.", "danger")
                return redirect(url_for('main.index'))
            activos = ResultadoBacktest.query.filter_by(id_estrategia=id_estrategia, usuario_id=u.id).all()

        if activos:
            for activo in activos:
                Trade.query.filter_by(backtest_id=activo.id).delete()
                db.session.delete(activo)
            db.session.commit()
            flash(f"✅ Tanda #{id_estrategia} eliminada.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "danger")
    return redirect(url_for('main.index'))

# --- RUTA PARA VER EL GRÁFICO EN PESTAÑA NUEVA ---
@main_bp.route('/backtest/ver_grafico/<int:reg_id>')
def ver_grafico_completo(reg_id):
    try:
        # 1. Buscamos en la DB (Asegúrate de que reg_id coincida con el nombre del argumento)
        resultado = ResultadoBacktest.query.get_or_404(reg_id)
        
        # 2. Validar contenido
        if not resultado.grafico_html or not resultado.grafico_html.strip():
            return "<h3>No hay datos gráficos guardados para este backtest.</h3>", 404
        
        # 3. Devolver como HTML completo para que el navegador lo renderice solo
        # Usamos Response para asegurar el mimetype correcto
        return Response(resultado.grafico_html, mimetype='text/html')
    
    except Exception as e:
        return f"<h3>Error al recuperar gráfico: {str(e)}</h3>", 500
    
# --- AUTENTICACIÓN ---

#-- RUTA DE LOGIN --
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

#-- RUTA DE LOGOUT --
@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))