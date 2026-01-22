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

from ..database import db, ResultadoBacktest, Trade, Usuario # Importa tus modelos
from sqlalchemy import func
from datetime import datetime

main_bp = Blueprint('main', __name__) 

# --- FUNCIONES DE SOPORTE (Manteniendo tu lógica de usuarios) ---
def obtener_usuarios_registrados():
    usuarios = {}
    ruta_usuarios = BACKTESTING_BASE_DIR / "users.csv"
    if not ruta_usuarios.exists(): return {"admin": "admin"} 
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

    # --- LÓGICA POST (Guardado de Configuración) ---
    # CAMBIO CRÍTICO: Solo guardamos si el formulario NO es de otra acción (como borrar o lanzar)
    # Para esto, tu botón de guardar en el HTML debe tener name="action" value="save_config"
    if request.method == 'POST' and request.form.get('action') == 'save_config':
        form_data = request.form.to_dict()
        
        # 1. Guardar Símbolos
        # --- NUEVA LÓGICA DE GUARDADO EN BASE DE DATOS (Sustituye al CSV) ---
        if 'symbols_content' in form_data:
            contenido = form_data['symbols_content']
            # IMPORTANTE: Importamos ambos modelos aquí para evitar el error de "local variable"
            from ..database import Simbolo, Usuario
            
            # 1. Limpieza y preparación de la lista
            raw_activos = contenido.replace(';', ',').replace('\n', ',').replace('\r', ',')
            lista_nombres_simbolos = [s.strip().upper() for s in raw_activos.split(',') if s.strip()]
            lista_nombres_simbolos = list(dict.fromkeys(lista_nombres_simbolos)) # Sin duplicados
            
            try:
                # 2. Buscamos al usuario actual
                u = Usuario.query.filter_by(username=user_mode).first()
                
                if u:
                    # 3. Limpiamos sus símbolos antiguos (Borrado previo)
                    Simbolo.query.filter_by(usuario_id=u.id).delete()
                    
                    # 4. Insertamos los nuevos
                    for sym_name in lista_nombres_simbolos:
                        nuevo_simbolo = Simbolo(
                            symbol=sym_name,
                            name=sym_name, # Por ahora igual al símbolo
                            usar_full_ratio=True,     # Valor por defecto P1
                            tiene_fundamentales=True,  # Valor por defecto P1
                            usuario_id=u.id
                        )
                        db.session.add(nuevo_simbolo)
                    
                    db.session.commit()
                    print(f"✅ {len(lista_nombres_simbolos)} símbolos guardados en DB para {user_mode}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error al guardar símbolos en DB: {e}")
                flash("Error al guardar en la base de datos", "danger")
        
        # 2. Configuración (.env)
        env_config = {k: v for k, v in form_data.items() if k not in ['symbols_content', 'action']}

        # GESTIÓN DE SWITCHES
        for attr in dir(System):
            if not attr.startswith("__"):
                val_original = getattr(System, attr)
                if isinstance(val_original, bool):
                    env_config[attr] = "True" if attr in form_data else "False"

        guardar_parametros_a_env(env_config, user_mode)
        cargar_y_asignar_configuracion(user_mode)
        
        flash("✅ Configuración guardada correctamente.", "success")
        return redirect(url_for('main.index'))

    # ================================================================
    # --- FLUJO GET (Carga normal de la página) ---
    # ================================================================
    cargar_y_asignar_configuracion(user_mode)
    
    config_web = {}
    for attr in dir(System):
        if not attr.startswith("__"):
            val = getattr(System, attr)
            config_web[attr] = str(val).strip() if val is not None else "None"

    # --- CONSTRUCCIÓN DEL ÁRBOL DE ARCHIVOS (En EXPLORADOR ) ---

    file_tree = []
    
    # 1. Logs de Sistema (SOLO PARA ADMIN)
    # Ya no mostramos Resultados ni Gráficos porque están en la DB
    if user_mode == 'admin':
        logs_p = BACKTESTING_BASE_DIR / "logs"
        if logs_p.exists():
            file_tree.append({
                "name": "Logs del Servidor",
                "is_dir": True,
                "children": get_directory_tree(logs_p, True),
                "type": "Folder",
                "path": "Logs"
            })

    # 2. Datos de Usuario (Opcional)
    # Si quieres que el usuario vea sus archivos de configuración o caché OHLCV
    # podrías añadirlo aquí, de lo contrario, deja el file_tree vacío para usuarios.

    # --- Historial de Resultados (Agrupado por Tanda) ---
    registros_agrupados = {}
    try:
        from ..database import Usuario, ResultadoBacktest
        user_mode = session.get('user_mode')

        # CAMBIO AQUÍ: Si es admin, traemos TODOS los registros de la DB
        if user_mode == 'admin':
            todos = ResultadoBacktest.query.order_by(ResultadoBacktest.fecha_ejecucion.desc()).all()
        else:
            # Si no es admin, mantenemos tu lógica actual de filtrado
            u = Usuario.query.filter_by(username=user_mode).first()
            todos = ResultadoBacktest.query.filter_by(usuario_id=u.id)\
                    .order_by(ResultadoBacktest.fecha_ejecucion.desc()).all() if u else []
        
        for r in todos:
            # Mantenemos tu clave para agrupar en la interfaz
            tanda_key = f"{r.usuario_id}_{r.id_estrategia}" if user_mode == 'admin' else r.id_estrategia
            
            if tanda_key not in registros_agrupados:
                registros_agrupados[tanda_key] = {
                    'id_tanda': r.id_estrategia,  # El número 1, 2 o 3
                    'usuario_id': r.usuario_id,   # El ID numérico del dueño (ej: 2)
                    'fecha': r.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
                    'usuario_nombre': r.propietario.username,
                    'activos': []
                }
            registros_agrupados[tanda_key]['activos'].append(r)
    except Exception as e:
        print(f"Error al cargar historial SQL: {e}")

    # ================================================================
    # --- NUEVA LÓGICA PARA LEER SÍMBOLOS DE LA DB (MODIFICACIÓN AQUÍ) ---
    # ================================================================
    from ..database import Simbolo, Usuario
    u_actual = Usuario.query.filter_by(username=user_mode).first()
    
    # Consultamos los símbolos del usuario en la base de datos
    simbolos_db = Simbolo.query.filter_by(usuario_id=u_actual.id).all() if u_actual else []
    
    # Convertimos la lista de objetos en un string separado por comas: "AAPL, MSFT, TSLA"
    symbols_text = ", ".join([s.symbol for s in simbolos_db])
    
    # Si la base de datos está vacía y quieres mostrar los encabezados por defecto:
    if not symbols_text:
        symbols_text = "Symbol,Name"

    registros_final = dict(sorted(registros_agrupados.items(), key=lambda x: x[0], reverse=True))

    return render_template(
        'index.html',
        system=System,
        strategy=System,
        config=config_web,
        # CAMBIO CLAVE: Ahora enviamos symbols_text (de la DB) en lugar de leer el CSV
        symbols_content=symbols_text, 
        file_tree=file_tree,
        registros=registros_final,
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
    with app_instance.app_context():
        try:
            # 1. Llamada al motor. 
            # IMPORTANTE: Ahora recibimos 3 valores.
            # El motor ya realiza el db.session.add y db.session.commit internamente.
            resultados_df, trades_df, graficos_dict = ejecutar_backtest(config_web)

            if resultados_df is not None and not resultados_df.empty:
                print(f"✅ Backtest finalizado para {user_mode}. Datos y gráficos procesados por el motor.")
            else:
                print(f"⚠️ El backtest para {user_mode} no generó resultados.")

        except Exception as e:
            print(f"❌ ERROR en run_backtest_and_save: {e}")
            import traceback
            traceback.print_exc()

#-- RUTA PARA LANZAR BACKTEST (POST) --
@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    if not session.get('logged_in'): 
        return jsonify({"status": "error"}), 401
    
    config_web = request.form.to_dict()
    user_mode = session.get('user_mode')
    config_web['user_mode'] = user_mode

    # 1. Buscamos el usuario y su ID
    from ..database import Usuario
    u = Usuario.query.filter_by(username=user_mode).first()
    
    if not u:
        return jsonify({"status": "error", "message": "Usuario no encontrado en la DB"}), 404
        
    config_web['user_id'] = u.id 

    # 2. Calculamos la tanda (1, 2, 3...)
    ultima_tanda = db.session.query(func.max(ResultadoBacktest.id_estrategia)).filter_by(usuario_id=u.id).scalar()
    config_web['tanda_id'] = (ultima_tanda + 1) if ultima_tanda is not None else 1

    # 3. Lanzamiento del hilo
    from flask import current_app
    app_instance = current_app._get_current_object()

    threading.Thread(
        target=run_backtest_and_save, 
        args=(app_instance, config_web, user_mode)
    ).start()

    return jsonify({"status": "success", "message": f"Tanda #{config_web['tanda_id']} iniciada para {user_mode}."})

#-- RUTA PARA VER ARCHIVOS DE LOGS --
@main_bp.route('/file/<path:path>')
def view_file(path):
    if not session.get('logged_in'): abort(401)
    user_mode = session.get('user_mode')
    
    # Los resultados y gráficos ahora se ven vía /backtest/ver_grafico/ 
    # Esta ruta queda solo para visualizar Logs del sistema (Admin)
    if user_mode != 'admin': abort(403)

    filename = os.path.basename(path)
    logs_dir = BACKTESTING_BASE_DIR / "logs"
    target = logs_dir / filename

    if not target.exists(): abort(404)
    
    # Lectura segura de logs (últimas 2000 líneas)
    with open(target, 'r', encoding='utf-8', errors='replace') as f:
        contenido = "".join(deque(f, maxlen=2000))
    return Response(contenido, mimetype='text/plain')

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