import os
import threading
import csv
import io
import json
import html
import sys
import signal
import subprocess
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, jsonify, Response, send_from_directory, abort
)
from collections import deque
from datetime import date, timedelta, datetime, timezone
import logging
import traceback

# --- IMPORTACIONES ORIGINALES ---
from ..file_handler import read_symbols_raw, write_symbols_raw, get_directory_tree
from ..configuracion import (
    inicializar_configuracion_usuario,
    cargar_y_asignar_configuracion, System, BACKTESTING_BASE_DIR, PROJECT_ROOT
) 
from trading_engine.core.constants import VARIABLE_COMMENTS
from ..Backtest import ejecutar_backtest 

from ..database import db, ResultadoBacktest, Trade, Usuario, Simbolo # Importa tus modelos
from sqlalchemy import func
from sqlalchemy.orm import joinedload

main_bp = Blueprint('main', __name__) 

# Estado de ejecucion en memoria para mostrar progreso en UI sin refrescar.
# Clave: username | Valor: dict de estado de la ultima ejecucion lanzada.
BACKTEST_STATUS_BY_USER = {}
BACKTEST_STATUS_LOCK = threading.Lock()

SCHEDULER_SCRIPT_PATH = PROJECT_ROOT / 'Utils' / 'backtest_scheduler.py'
SCHEDULER_STATUS_PATH = PROJECT_ROOT / 'logs' / 'backtest_scheduler_status.json'
SCHEDULER_PID_PATH = PROJECT_ROOT / 'logs' / 'backtest_scheduler.pid'


def _is_enabled(value):
    """Normaliza flags bool que pueden venir como bool, numero o texto."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'on', 'yes', 'si', 'sí'}
    return bool(value)


def _build_strategy_short_title(result_row):
    """Genera un titulo corto y legible para el historial SQL a partir de params_tecnicos."""
    try:
        params = json.loads(result_row.params_tecnicos) if result_row.params_tecnicos else {}
    except Exception:
        params = {}

    indicators = []
    if _is_enabled(params.get('ema_cruce_signal')) or any(_is_enabled(params.get(k)) for k in ('ema_slow_minimo', 'ema_slow_maximo', 'ema_slow_ascendente', 'ema_slow_descendente')):
        indicators.append('EMA')
    if _is_enabled(params.get('rsi')):
        indicators.append('RSI')
    if _is_enabled(params.get('macd')):
        indicators.append('MACD')
    if any(_is_enabled(params.get(k)) for k in ('stoch_fast', 'stoch_mid', 'stoch_slow')):
        indicators.append('STOCH')
    if _is_enabled(params.get('bb_active')):
        indicators.append('BB')

    risk_flags = []
    if _is_enabled(params.get('breakeven_enabled')):
        risk_flags.append('BE')
    if _is_enabled(params.get('stoploss_swing_enabled')):
        risk_flags.append('SWING')
    if _is_enabled(params.get('rsi')) and params.get('rsi_trailing_limit') is not None and (
        params.get('trailing_pct_below') is not None or params.get('trailing_pct_above') is not None
    ):
        risk_flags.append('TSL-RSI')

    core = '+'.join(indicators) if indicators else 'BASE'
    risk = f" | {'/'.join(risk_flags)}" if risk_flags else ''
    interval_value = (
        params.get('INTERVAL')
        or params.get('interval')
        or params.get('intervalo')
        or getattr(result_row, 'intervalo', None)
    )
    interval = f" ({interval_value})" if interval_value else ''

    title = f"{core}{risk}{interval}"
    return title[:56] + '...' if len(title) > 59 else title


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _is_scheduler_running_from_pid() -> bool:
    if not SCHEDULER_PID_PATH.exists():
        return False
    try:
        pid = int(SCHEDULER_PID_PATH.read_text(encoding='utf-8').strip())
    except Exception:
        return False

    if os.name == 'nt':
        # Use tasklist on Windows because OpenProcess/GetExitCodeProcess can fail
        # with permission/flag combinations for detached processes.
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}"],
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            return str(pid) in out and "No tasks are running" not in out
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False


def _read_scheduler_status_file() -> dict:
    if not SCHEDULER_STATUS_PATH.exists():
        return {}
    try:
        return json.loads(SCHEDULER_STATUS_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _scheduler_trigger_label(intervalo: str) -> str:
    """Etiqueta legible de trigger para el dashboard sin depender del proceso scheduler."""
    v = str(intervalo or '').strip().lower()
    minute_map = {
        '1m': 1,
        '2m': 2,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '60m': 60,
        '1h': 60,
        '90m': 90,
    }
    if v in minute_map:
        mins = minute_map[v]
        hours = mins // 60
        rem = mins % 60
        if rem == 0:
            return f"interval[{hours}:00:00]"
        return f"interval[0:{rem:02d}:00]"
    if v == '1d':
        return "cron[mon-fri 22:00 Europe/Madrid]"
    if v == '1wk':
        return "cron[mon 09:00 Europe/Madrid]"
    if v == '1mo':
        return "cron[day=1 09:00 Europe/Madrid]"
    return "cron[mon-fri 22:00 Europe/Madrid]"


def _build_expected_scheduler_jobs_from_db() -> list:
    """Reconstruye jobs esperados (solo usuarios) desde config en BD."""
    jobs = []
    usuarios = Usuario.query.all()
    for usuario in usuarios:
        cfg = {}
        if usuario.config_actual:
            try:
                cfg = json.loads(usuario.config_actual)
            except Exception:
                cfg = {}

        enviar_mail = _is_enabled(cfg.get('enviar_mail', False))
        destinatario = str(cfg.get('destinatario_email', '') or '').strip()
        if not (enviar_mail and destinatario):
            continue

        intervalo = str(cfg.get('intervalo', '1d') or '1d')
        jobs.append({
            'id': f"backtest_{usuario.username}",
            'name': f"Backtest {usuario.username} ({intervalo})",
            'trigger': _scheduler_trigger_label(intervalo),
            'next_run_time': None,
        })

    jobs.sort(key=lambda j: j.get('id', ''))
    return jobs


def _init_backtest_status(user_mode, run_id, tanda_id):
    with BACKTEST_STATUS_LOCK:
        BACKTEST_STATUS_BY_USER[user_mode] = {
            'run_id': run_id,
            'tanda_id': tanda_id,
            'status': 'queued',
            'phase_index': 0,
            'phase_total': 0,
            'phase': 'En cola',
            'message': 'Backtest en cola de ejecucion',
            'events': [{
                'timestamp': _utc_now_iso(),
                'phase': 'En cola',
                'message': 'Backtest en cola de ejecucion'
            }],
            'started_at': _utc_now_iso(),
            'updated_at': _utc_now_iso(),
            'finished_at': None,
            'result_count': 0,
            'error': None,
        }


def _append_backtest_event(user_mode, phase, message):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['events'].append({
            'timestamp': _utc_now_iso(),
            'phase': str(phase),
            'message': str(message),
        })
        state['events'] = state['events'][-120:]
        state['updated_at'] = _utc_now_iso()


def _set_backtest_progress(user_mode, phase_index, phase_total, phase, message, status='running'):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['status'] = status
        state['phase_index'] = int(phase_index)
        state['phase_total'] = int(phase_total)
        state['phase'] = str(phase)
        state['message'] = str(message)
        state['updated_at'] = _utc_now_iso()
    _append_backtest_event(user_mode, phase, message)


def _finish_backtest_status(user_mode, status, message, result_count=0, error=None):
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return
        state['status'] = status
        state['message'] = str(message)
        state['result_count'] = int(result_count or 0)
        state['error'] = str(error) if error else None
        state['finished_at'] = _utc_now_iso()
        state['updated_at'] = _utc_now_iso()
        state['events'].append({
            'timestamp': _utc_now_iso(),
            'phase': 'Finalizado' if status == 'completed' else 'Error',
            'message': str(message),
        })
        state['events'] = state['events'][-120:]

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

    user_mode = session.get('user_mode')
    u = Usuario.query.filter_by(username=user_mode).first()

    # ================================================================
    # --- LÓGICA POST (Guardado de Configuración en DB) ---
    # ================================================================
    if request.method == 'POST' and request.form.get('action') == 'save_config':
        form_data = request.form.to_dict()
        if 'fecha_fin' in form_data and 'end_date' not in form_data:
            form_data['end_date'] = form_data['fecha_fin']
        
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
        config_params = {k: v for k, v in form_data.items() if k not in ['symbols_content', 'action', 'end_date', 'fecha_fin']}

        # --- LISTA MAESTRA DE SWITCHES (Basada en tus .html) ---
        lista_switches = [
            # Indicadores principales
            'macd', 'rsi', 'ema_cruce_signal', 'bb_active', 'bb_buy_crossover', 'bb_sell_crossover',
            # Parámetros RSI (nuevos)
            'rsi_minimo', 'rsi_ascendente', 'rsi_maximo', 'rsi_descendente',
            # Parámetros EMA (existentes)
            'ema_slow_minimo', 'ema_slow_ascendente', 'ema_slow_maximo', 'ema_slow_descendente',
            # Filtros globales
            'filtro_fundamental', 'enviar_mail', 'margen_seguridad_active', 
            'margen_seguridad_ascendente', 'volume_active', 'volume_ascendente',
            'stoch_fast', 'stoch_mid', 'stoch_slow',
            # Protección de entrada
            'breakeven_enabled'
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
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "success", "message": "✅ Configuración guardada correctamente."})
            flash("✅ Configuración guardada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "message": f"Error al guardar: {e}"})
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

    # Fecha fin operativa por defecto: siempre ayer en UI.
    # No se persiste en config_actual para evitar arrastrar fechas historicas entre sesiones.
    ayer = date.today() - timedelta(days=1)
    config_para_web['end_date'] = ayer.isoformat()

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
                    'titulo_estrategia': _build_strategy_short_title(r),
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

    # docs visible para todos los usuarios autenticados
    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.exists():
        arbol_ficheros.append({
            "name": "docs",
            "is_dir": True,
            "children": get_directory_tree(docs_dir, is_admin=(user_mode == 'admin')),
            "type": "Folder",
            "path": "docs"
        })

    # logs solo para admin
    if user_mode == 'admin':
        logs_dir = BACKTESTING_BASE_DIR / "logs"
        if logs_dir.exists():
            arbol_ficheros.append({
                "name": "logs",
                "is_dir": True,
                "children": get_directory_tree(logs_dir, is_admin=True),
                "type": "Folder",
                "path": "logs"
            })

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
    """
    Ejecuta el motor de backtest en hilo separado.
    El guardado en SQL (incluyendo gráfico) ocurre dentro de Backtest.py
    """
    # Obtenemos el logger de la app
    logger = logging.getLogger("BacktestExecution")
    
    # En Postgres, cada hilo debe gestionar su propia sesión
    with app_instance.app_context():
        try:
            _set_backtest_progress(
                user_mode=user_mode,
                phase_index=0,
                phase_total=11,
                phase='Inicializando',
                message='Preparando recursos y contexto de base de datos',
                status='running'
            )

            logger.info(f"\n{'='*70}")
            logger.info(f"🚀 INICIANDO BACKTEST | Usuario: {user_mode} | Tanda: {config_web.get('tanda_id', 'N/A')}")
            logger.info(f"{'='*70}")
            
            # 1. Llamada al motor
            logger.info("Ejecutando motor de backtest...")
            resultados_df, trades_df, graficos_dict = ejecutar_backtest(
                config_web,
                progress_callback=lambda i, total, phase, msg: _set_backtest_progress(
                    user_mode=user_mode,
                    phase_index=i,
                    phase_total=total,
                    phase=phase,
                    message=msg,
                    status='running'
                )
            )
            
            # El motor hace el commit, pero limpiamos la sesión explícitamente
            db.session.remove()
            
            # 2. Validar resultados
            if resultados_df is not None and not resultados_df.empty:
                _finish_backtest_status(
                    user_mode=user_mode,
                    status='completed',
                    message=f"Backtest finalizado. {len(resultados_df)} resultados guardados.",
                    result_count=len(resultados_df)
                )
                logger.info(f"✅ ÉXITO | {len(resultados_df)} resultados procesados")
                logger.info(f"✅ Gráficos generados: {len(graficos_dict)}")
                logger.info(f"{'='*70}\n")
                print(f"✅ Backtest finalizado para {user_mode}. {len(resultados_df)} resultados guardados.")
            else:
                _finish_backtest_status(
                    user_mode=user_mode,
                    status='completed',
                    message='Backtest finalizado sin resultados para guardar.',
                    result_count=0
                )
                logger.warning(f"⚠️  ADVERTENCIA | El backtest no generó resultados")
                logger.warning(f"{'='*70}\n")
                print(f"⚠️ El backtest para {user_mode} no generó resultados.")

        except Exception as e:
            _finish_backtest_status(
                user_mode=user_mode,
                status='error',
                message='Backtest interrumpido por error.',
                error=e
            )
            logger.error(f"\n{'='*70}")
            logger.error(f"❌ ERROR CRÍTICO EN BACKTEST | Usuario: {user_mode}")
            logger.error(f"Excepción: {type(e).__name__}: {str(e)}")
            logger.error(f"{'='*70}")
            logger.error(traceback.format_exc())
            db.session.rollback()
            print(f"❌ ERROR en backtest para {user_mode}: {str(e)}")
        
        finally:
            try:
                db.session.remove()
            except Exception as e:
                logger.error(f"Error al limpiar sesión DB: {e}")

#-- RUTA PARA LANZAR BACKTEST (POST) --
# Obtenemos el logger configurado en tu app
logger = logging.getLogger(__name__)

@main_bp.route('/launch_strategy', methods=['POST'])
def launch_strategy():
    """
    Lanza el backtest en hilo separado y retorna confirmación inmediata.
    El progreso se puede ver en los logs en tiempo real.
    """
    logger = logging.getLogger("LaunchStrategy")
    
    try:
        if not session.get('logged_in'): 
            logger.warning("Intento de acceso sin autenticación a /launch_strategy")
            return jsonify({"status": "error", "message": "No autenticado"}), 401
        
        user_mode = session.get('user_mode')
        logger.info(f"[LAUNCH] Usuario {user_mode} lanzando backtest...")
        
        u = Usuario.query.filter_by(username=user_mode).first()
        if not u:
            logger.error(f"[LAUNCH] Usuario {user_mode} no encontrado en BD")
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        # 1. Cargamos configuración base del disco
        logger.info(f"[LAUNCH] Cargando configuración base para {user_mode}")
        cargar_y_asignar_configuracion(user_mode)
        
        # 2. Capturamos el formulario
        form_data = request.form.to_dict()
        if 'fecha_fin' in form_data and 'end_date' not in form_data:
            logger.warning("[LAUNCH] Se recibió 'fecha_fin' en POST legado; se normaliza a 'end_date'")
            form_data['end_date'] = form_data['fecha_fin']
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
            'margen_seguridad_active', 'volume_active', 'stoch_fast', 'stoch_mid', 'stoch_slow',
            'breakeven_enabled'
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

        # 5. Fallback backend obligatorio para end_date (ayer)
        end_date_raw = (form_data.get('end_date') or '').strip()
        if not end_date_raw or end_date_raw.lower() == 'none':
            config_web['end_date'] = (date.today() - timedelta(days=1)).isoformat()
        else:
            try:
                datetime.strptime(end_date_raw, "%Y-%m-%d")
                config_web['end_date'] = end_date_raw
            except ValueError:
                return jsonify({"status": "error", "message": "end_date inválida. Formato esperado: YYYY-MM-DD"}), 400

        # 6. Metadatos cruciales para el motor
        config_web['user_id'] = u.id 
        config_web['user_mode'] = user_mode # <--- FUNDAMENTAL para que Backtest.py sepa quién es
        
        ultima_tanda = db.session.query(func.max(ResultadoBacktest.id_estrategia)).filter_by(usuario_id=u.id).scalar()
        config_web['tanda_id'] = (ultima_tanda + 1) if ultima_tanda is not None else 1
        
        logger.info(f"[LAUNCH] Configuración preparada:")
        logger.info(f"  - Usuario: {user_mode} (ID={u.id})")
        logger.info(f"  - Tanda: #{config_web['tanda_id']}")
        logger.info(f"  - Indicadores activos: {len([k for k,v in config_web.items() if v == True])}")
        logger.info(f"  - Símbolos: {Simbolo.query.filter_by(usuario_id=u.id).count()}")

        # 7. Lanzar el hilo con el contexto de la app
        from flask import current_app
        app_instance = current_app._get_current_object()

        logger.info(f"[LAUNCH] ✅ Iniciando hilo de backtest...")
        run_id = f"{u.id}-{config_web['tanda_id']}-{int(datetime.now(timezone.utc).timestamp())}"
        _init_backtest_status(user_mode=user_mode, run_id=run_id, tanda_id=config_web['tanda_id'])
        threading.Thread(
            target=run_backtest_and_save, 
            args=(app_instance, config_web, user_mode),
            daemon=False  # Permitir que la app espere si es necesario
        ).start()

        logger.info(f"[LAUNCH] Hilo iniciado correctamente")
        return jsonify({
            "status": "success",
            "message": "Backtest iniciado.",
            "run_id": run_id,
            "tanda_id": config_web['tanda_id']
        })

    except Exception as e:
        error_msg = f"ERROR CRÍTICO EN LAUNCH: {traceback.format_exc()}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/backtest_status', methods=['GET'])
def backtest_status():
    """Devuelve el estado de la ultima ejecucion de backtest del usuario en sesion."""
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autenticado"}), 401

    user_mode = session.get('user_mode')
    with BACKTEST_STATUS_LOCK:
        state = BACKTEST_STATUS_BY_USER.get(user_mode)
        if not state:
            return jsonify({"status": "idle", "message": "Sin ejecuciones recientes."})
        return jsonify(state)


@main_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autenticado"}), 401
    if session.get('user_mode') != 'admin':
        return jsonify({"status": "error", "message": "No autorizado"}), 403

    status_data = _read_scheduler_status_file()
    if not isinstance(status_data, dict):
        status_data = {}
    status_data.setdefault('scheduler', {})
    status_data.setdefault('jobs', [])
    status_data.setdefault('runs', {})

    # No mostrar jobs internos de mantenimiento en dashboard (_refresh_jobs, etc.)
    runtime_jobs = [
        j for j in status_data.get('jobs', [])
        if not str((j or {}).get('id', '')).startswith('_')
    ]

    pid_is_running = _is_scheduler_running_from_pid()

    # El JSON sigue siendo la referencia principal, pero si el PID está vivo
    # y el JSON quedó stale por una ejecución inmediata, reconciliamos a running.
    json_status = status_data.get('scheduler', {}).get('status', 'unknown')

    if json_status == 'stopped':
        if pid_is_running:
            is_running = True
            status_data['scheduler']['status'] = 'running'
            status_data['scheduler']['message'] = 'Proceso activo detectado'
        else:
            is_running = False
    elif json_status in ('running', 'starting'):
        is_running = pid_is_running
        if not is_running:
            status_data['scheduler']['status'] = 'crashed'
            status_data['scheduler']['message'] = 'El proceso terminó inesperadamente'
    else:
        is_running = pid_is_running
        if is_running:
            status_data['scheduler']['status'] = 'running'
            status_data['scheduler']['message'] = 'Proceso activo detectado'

    # Siempre mostrar los jobs esperados (usuarios en BD con enviar_mail=true)
    # Si está running: mostrar con next_run_time real
    # Si está stopped: mostrar jobs que se crearían (sin next_run_time)
    try:
        expected_jobs = _build_expected_scheduler_jobs_from_db()
    except Exception:
        expected_jobs = []

    if is_running:
        runtime_by_id = {
            str((j or {}).get('id', '')): j
            for j in runtime_jobs
            if str((j or {}).get('id', ''))
        }

        merged_jobs = []
        for ej in expected_jobs:
            job_id = str(ej.get('id', ''))
            rj = runtime_by_id.get(job_id, {})
            merged_jobs.append({
                'id': ej.get('id'),
                'name': ej.get('name'),
                'trigger': ej.get('trigger') or rj.get('trigger'),
                'next_run_time': rj.get('next_run_time'),
            })

        status_data['jobs'] = merged_jobs if merged_jobs else runtime_jobs
    else:
        # Scheduler stopped: mostrar los jobs que se crearían (sin next_run_time)
        status_data['jobs'] = [
            {
                'id': j.get('id'),
                'name': j.get('name'),
                'trigger': j.get('trigger'),
                'next_run_time': None,
            }
            for j in expected_jobs
        ]

    # Reconcile: if the process is dead but the JSON still says "running",
    # report it as "crashed" so the UI stays consistent.
    if not is_running and isinstance(status_data.get('scheduler'), dict):
        sched_status = status_data['scheduler'].get('status', '')
        if sched_status in ('running', 'starting'):
            status_data['scheduler']['status'] = 'crashed'
            status_data['scheduler']['message'] = 'El proceso terminó inesperadamente'

    return jsonify({
        "status": "success",
        "running": is_running,
        "status_file": status_data,
        "pid_file": str(SCHEDULER_PID_PATH),
        "status_path": str(SCHEDULER_STATUS_PATH),
    })


@main_bp.route('/scheduler/start', methods=['POST'])
def scheduler_start():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autenticado"}), 401
    if session.get('user_mode') != 'admin':
        return jsonify({"status": "error", "message": "No autorizado"}), 403

    immediate = request.json.get('immediate', False) if request.is_json else request.args.get('immediate', False)

    # Chequear por PID para saber si estaba corriendo
    was_running = _is_scheduler_running_from_pid()
    
    if was_running:
        # Ya hay un proceso: si se solicita inmediato, simplemente ejecutar --ahora
        if immediate:
            try:
                log_path = PROJECT_ROOT / 'logs' / 'backtest_scheduler_web.log'
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    subprocess.Popen(
                        [sys.executable, str(SCHEDULER_SCRIPT_PATH), '--ahora'],
                        cwd=str(PROJECT_ROOT),
                        stdout=log_file,
                        stderr=log_file,
                        stdin=subprocess.DEVNULL,
                        close_fds=False,
                    )
                return jsonify({"status": "success", "message": "Scheduler ya estaba en ejecución. Ejecución inmediata lanzada."})
            except Exception as e:
                return jsonify({"status": "error", "message": f"Scheduler estaba corriendo pero no se pudo ejecutar --ahora: {e}"}), 500
        else:
            return jsonify({"status": "ok", "message": "Scheduler ya estaba en ejecución."})

    if not SCHEDULER_SCRIPT_PATH.exists():
        return jsonify({"status": "error", "message": f"No existe script: {SCHEDULER_SCRIPT_PATH}"}), 500

    try:
        status_data = _read_scheduler_status_file()
        if not isinstance(status_data, dict):
            status_data = {}
        status_data.setdefault('scheduler', {})
        status_data.setdefault('jobs', [])
        status_data.setdefault('runs', {})
        status_data['scheduler']['status'] = 'starting'
        status_data['scheduler']['message'] = 'Arrancando scheduler desde web'
        status_data['scheduler']['updated_at'] = datetime.now(timezone.utc).isoformat()
        SCHEDULER_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULER_STATUS_PATH.write_text(
            json.dumps(status_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

        log_path = PROJECT_ROOT / 'logs' / 'backtest_scheduler_web.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as log_file:
            subprocess.Popen(
                [sys.executable, str(SCHEDULER_SCRIPT_PATH)],
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                close_fds=False,
                creationflags=creationflags,
            )

            # Si se solicita ejecución inmediata, lanzar --ahora en paralelo.
            if immediate:
                subprocess.Popen(
                    [sys.executable, str(SCHEDULER_SCRIPT_PATH), '--ahora'],
                    cwd=str(PROJECT_ROOT),
                    stdout=log_file,
                    stderr=log_file,
                    stdin=subprocess.DEVNULL,
                    close_fds=False,
                    creationflags=creationflags,
                )

        return jsonify({"status": "success", "message": "Scheduler arrancado." + (" Ejecución inmediata lanzada." if immediate else "")})
    except Exception as e:
        return jsonify({"status": "error", "message": f"No se pudo arrancar el scheduler: {e}"}), 500


@main_bp.route('/scheduler/stop', methods=['POST'])
def scheduler_stop():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autenticado"}), 401
    if session.get('user_mode') != 'admin':
        return jsonify({"status": "error", "message": "No autorizado"}), 403

    if not SCHEDULER_PID_PATH.exists():
        # No hay PID file: marcar JSON como stopped por si acaso estaba corriendo
        try:
            status_data = _read_scheduler_status_file()
            if isinstance(status_data, dict):
                status_data.setdefault('scheduler', {})
                status_data['scheduler']['status'] = 'stopped'
                status_data['scheduler']['message'] = 'Detenido manualmente desde web'
                status_data['scheduler']['updated_at'] = datetime.now(timezone.utc).isoformat()
                SCHEDULER_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
                SCHEDULER_STATUS_PATH.write_text(
                    json.dumps(status_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
        except Exception:
            pass
        return jsonify({"status": "ok", "message": "Scheduler no estaba en ejecución."})

    try:
        pid = int(SCHEDULER_PID_PATH.read_text(encoding='utf-8').strip())
    except Exception:
        return jsonify({"status": "error", "message": "PID inválido en fichero."}), 500

    try:
        if os.name == 'nt':
            subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                check=False,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            # Esperar brevemente a que el proceso muera
            import time
            time.sleep(0.5)
        else:
            os.kill(pid, signal.SIGTERM)
            import time
            time.sleep(0.5)
    except Exception as e:
        return jsonify({"status": "error", "message": f"No se pudo detener el scheduler: {e}"}), 500

    try:
        if SCHEDULER_PID_PATH.exists():
            SCHEDULER_PID_PATH.unlink()
    except Exception:
        pass

    # Marcar el JSON como stopped
    try:
        status_data = _read_scheduler_status_file()
        if isinstance(status_data, dict):
            status_data.setdefault('scheduler', {})
            status_data['scheduler']['status'] = 'stopped'
            status_data['scheduler']['message'] = 'Detenido manualmente desde web'
            status_data['scheduler']['updated_at'] = datetime.now(timezone.utc).isoformat()
            SCHEDULER_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SCHEDULER_STATUS_PATH.write_text(
                json.dumps(status_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Scheduler detenido."})

#-- RUTA PARA VER ARCHIVOS DE LOGS --
@main_bp.route('/view_file/<path:path>')
def view_file(path):
    if not session.get('logged_in'):
        return "No autorizado", 401
    user_mode = session.get('user_mode')

    # Permitir lectura solo desde raíces controladas del explorador.
    # Normalizamos separadores por robustez (URLs usan '/', pero protegemos casos mixtos)
    normalized_path = str(path).replace('\\', '/')
    path_obj = Path(normalized_path)
    allowed_roots = {
        "logs": (BACKTESTING_BASE_DIR / "logs").resolve(),
        "docs": (PROJECT_ROOT / "docs").resolve(),
    }

    if not path_obj.parts:
        return "Ruta inválida.", 400

    root_key = path_obj.parts[0]
    root_path = allowed_roots.get(root_key)
    if root_path is None:
        return "Ruta no permitida.", 403

    # Permisos por raíz: docs para todos, logs solo admin.
    if root_key == 'logs' and user_mode != 'admin':
        return "No autorizado para acceder a logs.", 403

    relative_path = Path(*path_obj.parts[1:]) if len(path_obj.parts) > 1 else Path()
    full_path = (root_path / relative_path).resolve()

    # Evitar traversal fuera de la raíz permitida.
    try:
        full_path.relative_to(root_path)
    except ValueError:
        return "Ruta no permitida.", 403

    if not full_path.exists():
        return f"Archivo no encontrado en: {full_path}", 404

    if full_path.is_dir():
        return "La ruta seleccionada es un directorio.", 400

    try:
        # 2. IMPORTANTE: Usamos 'errors='replace' para caracteres extraños
        # y leemos el archivo aunque esté siendo escrito por otro proceso (Flask)
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            # Leemos las últimas 1000 líneas para no colapsar el modal si el log es enorme
            content = "".join(deque(f, maxlen=1000))
            
        if not content:
            return "El archivo está vacío.", 200
            
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 500

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
    if not session.get('logged_in'):
        return "No autorizado", 401
    if session.get('user_mode') != 'admin':
        return "Acceso denegado", 403
    
    try:
        # El admin descarga TODOS los trades + relaciones en una sola carga
        trades = Trade.query.options(
            joinedload(Trade.backtest).joinedload(ResultadoBacktest.propietario)
        ).all()

        def _to_scalar_csv(v):
            if v is None:
                return ''
            if isinstance(v, (str, int, float, bool)):
                return v
            return json.dumps(v, ensure_ascii=False)

        params_by_backtest = {}
        param_keys = set()

        for t in trades:
            bt = t.backtest
            if bt is None:
                continue
            bt_id = bt.id
            if bt_id in params_by_backtest:
                continue

            params = {}
            if bt.params_tecnicos:
                try:
                    raw_params = json.loads(bt.params_tecnicos)
                    if isinstance(raw_params, dict):
                        params = raw_params
                except Exception:
                    params = {}

            scalar_params = {str(k): _to_scalar_csv(v) for k, v in params.items()}
            params_by_backtest[bt_id] = scalar_params
            param_keys.update(scalar_params.keys())

        ordered_param_keys = sorted(param_keys)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Usuario Propietario',
            'ID Tanda',
            'Activo',
            'Tipo',
            'Fecha',
            'Entrada',
            'Salida',
            'PnL_Abs',
            'Retorno_Pct',
            *ordered_param_keys,
        ])

        for t in trades:
            bt = t.backtest
            params_row = params_by_backtest.get(bt.id, {}) if bt is not None else {}
            writer.writerow([
                bt.propietario.username if bt and bt.propietario else '',
                bt.id_estrategia if bt else '',
                bt.symbol if bt else '',
                t.tipo, t.fecha, t.precio_entrada, 
                t.precio_salida, t.pnl_absoluto, t.retorno_pct,
                *[params_row.get(k, '') for k in ordered_param_keys],
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
        
        # 3. Inyectar un bloque informativo arriba del gráfico (sin alterar lo persistido en BD)
        strategy_title = _build_strategy_short_title(resultado)
        fecha_txt = resultado.fecha_ejecucion.strftime('%Y-%m-%d %H:%M') if resultado.fecha_ejecucion else 'N/A'

        try:
            params = json.loads(resultado.params_tecnicos) if resultado.params_tecnicos else {}
        except Exception:
            params = {}

        def _p(*keys, default='N/A'):
            for k in keys:
                if params.get(k) is not None and str(params.get(k)).strip() != '':
                    return params.get(k)
            return default

        ema_slow_period_txt = str(_p('ema_slow_period'))

        active_indicators = []
        if _is_enabled(_p('rsi', default=False)):
            active_indicators.append(f"RSI({_p('rsi_period')})")
        if _is_enabled(_p('macd', default=False)):
            active_indicators.append(f"MACD({_p('macd_fast')}/{_p('macd_slow')}/{_p('macd_signal')})")
        if _is_enabled(_p('stoch_fast', default=False)):
            active_indicators.append(f"StochFast({_p('stoch_fast_period')}/{_p('stoch_fast_smooth')})")
        if _is_enabled(_p('stoch_mid', default=False)):
            active_indicators.append(f"StochMid({_p('stoch_mid_period')}/{_p('stoch_mid_smooth')})")
        if _is_enabled(_p('stoch_slow', default=False)):
            active_indicators.append(f"StochSlow({_p('stoch_slow_period')}/{_p('stoch_slow_smooth')})")
        if _is_enabled(_p('bb_active', default=False)):
            active_indicators.append(f"BB({_p('bb_window')},{_p('bb_num_std')})")

        indicators_txt = ' | '.join(active_indicators) if active_indicators else 'Ninguno'

        info_block = f"""
<style>
    .chart-info-box {{
        margin: 12px 16px 8px 16px;
        padding: 10px 12px;
        border: 1px solid #dbe4ff;
        border-left: 4px solid #2f6fed;
        background: #f7faff;
        font-family: Arial, sans-serif;
        font-size: 13px;
        color: #1f2a44;
        border-radius: 6px;
    }}
    .chart-info-box strong {{ color: #0f3ea3; }}
</style>
<div class=\"chart-info-box\">
    <strong>Info estrategia:</strong>
    {html.escape(strategy_title)}
    <br>
    <strong>Símbolo:</strong> {html.escape(str(resultado.symbol or 'N/A'))}
    | <strong>Intervalo:</strong> {html.escape(str(resultado.intervalo or 'N/A'))}
    | <strong>Fecha:</strong> {html.escape(fecha_txt)}
    <br>
    <strong>EMA Lenta (periodo):</strong> {html.escape(ema_slow_period_txt)}
    <br>
    <strong>Indicadores activos (periodos):</strong> {html.escape(indicators_txt)}
</div>
"""

        page_html = resultado.grafico_html
        if '<body>' in page_html:
            page_html = page_html.replace('<body>', f'<body>{info_block}', 1)
        elif '<body ' in page_html:
            body_pos = page_html.lower().find('<body ')
            body_end = page_html.find('>', body_pos)
            if body_end != -1:
                page_html = page_html[:body_end+1] + info_block + page_html[body_end+1:]
            else:
                page_html = info_block + page_html
        else:
            page_html = info_block + page_html

        # 4. Devolver como HTML completo para que el navegador lo renderice solo
        # Usamos Response para asegurar el mimetype correcto
        return Response(page_html, mimetype='text/html')
    
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