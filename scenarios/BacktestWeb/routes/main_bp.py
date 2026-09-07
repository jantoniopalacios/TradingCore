import os
import threading
import csv
import io
import json
import html
import time
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
from ..Backtest import ejecutar_backtest, format_position_state
from .helpers import (
    _is_enabled,
    _build_strategy_short_title,
    _build_strategy_short_title_from_params,
    _sanitize_filename_component,
    _normalize_symbol_token,
    _scheduler_trigger_label,
)
from .config_helpers import (
    _extract_symbols_from_form_data,
    _build_config_params_from_form_data,
    _build_default_snapshot_filename,
)
from .backtest_status import (
    BACKTEST_STATUS_BY_USER,
    BACKTEST_STATUS_LOCK,
    _init_backtest_status,
    _set_backtest_progress,
    _finish_backtest_status,
)
from .scheduler_helpers import (
    _is_scheduler_running_from_pid,
    _read_scheduler_status_file,
)
from .graph_cache import (
    _remove_graph_artifacts_for_result,
    _prune_expired_graph_cache,
)
from .graph_render import (
    GRAPH_SNAPSHOT_PREFIX,
    _render_native_backtest_html,
    _render_bokeh_html_from_snapshot,
    _read_graph_html_with_cache,
)

from ..database import db, ResultadoBacktest, Trade, Usuario, Simbolo # Importa tus modelos
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import ResourceClosedError

from werkzeug.exceptions import HTTPException

main_bp = Blueprint('main', __name__) 

SCHEDULER_SCRIPT_PATH = PROJECT_ROOT / 'scripts' / 'scheduler' / 'backtest_scheduler.py'
SCHEDULER_STATUS_PATH = PROJECT_ROOT / 'logs' / 'backtest_scheduler_status.json'
SCHEDULER_PID_PATH = PROJECT_ROOT / 'logs' / 'backtest_scheduler.pid'
CONFIG_SNAPSHOT_BASE_DIR = PROJECT_ROOT / 'Data_files' / 'Backtest_config'

SAVEABLE_BOOLEAN_FIELDS = [
    'macd', 'rsi', 'ema_cruce_signal', 'bb_active', 'bb_buy_crossover', 'bb_sell_crossover',
    'rsi_minimo', 'rsi_ascendente', 'rsi_maximo', 'rsi_descendente',
    'ema_slow_minimo', 'ema_slow_ascendente', 'ema_slow_maximo', 'ema_slow_descendente',
    'filtro_fundamental', 'enviar_mail', 'margen_seguridad_active', 'margen_seguridad_ascendente',
    'volume_active', 'volume_ascendente', 'stoch_fast', 'stoch_mid', 'stoch_slow',
    'breakeven_enabled', 'stoploss_swing_enabled'
]


def _user_config_snapshot_dir(username):
    return CONFIG_SNAPSHOT_BASE_DIR / str(username)


def _persist_user_runtime_config(user, form_data):
    symbol_names = _extract_symbols_from_form_data(form_data)
    config_params = _build_config_params_from_form_data(
        form_data,
        SAVEABLE_BOOLEAN_FIELDS,
        include_dates=False,
    )

    Simbolo.query.filter_by(usuario_id=user.id).delete()
    for sym_name in symbol_names:
        db.session.add(Simbolo(symbol=sym_name, name=sym_name, usuario_id=user.id))

    # Guardar JSON en formato ASCII-safe evita errores de codificacion del driver/entorno (charmap)
    user.config_actual = json.dumps(config_params, ensure_ascii=True)
    return config_params, symbol_names


def _write_config_snapshot(username, file_name, config_payload):
    user_dir = _user_config_snapshot_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = str(file_name or '').strip()
    if not safe_name:
        raise ValueError('Debes indicar un nombre de fichero')
    if not safe_name.lower().endswith('.json'):
        safe_name = f"{safe_name}.json"
    safe_name = _sanitize_filename_component(Path(safe_name).stem) + '.json'

    file_path = user_dir / safe_name
    file_path.write_text(json.dumps(config_payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return file_path


def _regenerate_graph_html_on_demand(resultado, requester_user_mode):
    """Regenera el grafico para un unico activo en el momento de visualizarlo."""
    symbol = (resultado.symbol or '').strip()
    if not symbol:
        return None

    owner_username = requester_user_mode
    try:
        if resultado.propietario and resultado.propietario.username:
            owner_username = resultado.propietario.username
    except Exception:
        pass

    try:
        from pandas import DataFrame
        from trading_engine.core.Backtest_Runner import run_multi_symbol_backtest
        from trading_engine.utils.Data_download import descargar_datos_YF
        from ..estrategia_system import System
        from ..configuracion import cargar_y_asignar_configuracion, asignar_parametros_a_system
        from ..Backtest import _build_graph_snapshot_payload
    except Exception as import_err:
        logging.getLogger(__name__).warning("No se pudo importar motor de regeneracion de grafico: %s", import_err)
        return None

    try:
        params = json.loads(resultado.params_tecnicos) if resultado.params_tecnicos else {}
        if not isinstance(params, dict):
            params = {}
    except Exception:
        params = {}

    try:
        base_config = cargar_y_asignar_configuracion(owner_username)
    except Exception as cfg_err:
        logging.getLogger(__name__).warning("No se pudo cargar configuracion para regenerar grafico (%s): %s", owner_username, cfg_err)
        return None

    config_final = {**base_config, **params}

    start_date = resultado.fecha_inicio_datos or config_final.get('start_date') or config_final.get('START_DATE')
    end_date = resultado.fecha_fin_datos or config_final.get('end_date') or config_final.get('END_DATE')
    intervalo = resultado.intervalo or config_final.get('intervalo') or config_final.get('INTERVAL') or '1d'

    if not start_date or not end_date:
        logging.getLogger(__name__).warning("No hay rango de fechas para regenerar grafico de %s (resultado %s)", symbol, resultado.id)
        return None

    config_final['start_date'] = start_date
    config_final['START_DATE'] = start_date
    config_final['end_date'] = end_date
    config_final['END_DATE'] = end_date
    config_final['intervalo'] = intervalo
    config_final['INTERVAL'] = intervalo

    try:
        asignar_parametros_a_system(config_final, config_final)
    except Exception as sys_err:
        logging.getLogger(__name__).warning("No se pudo sincronizar System para regenerar grafico: %s", sys_err)
        return None

    data_files_path = Path(config_final.get('data_files_path') or (PROJECT_ROOT / 'Data_files'))
    simbolos_df = DataFrame([{'Symbol': symbol, 'Name': symbol}])

    try:
        stocks_data = descargar_datos_YF(simbolos_df, start_date, end_date, intervalo, data_files_path)
    except Exception as dl_err:
        logging.getLogger(__name__).warning("Error descargando datos para regenerar grafico %s: %s", symbol, dl_err)
        return None

    if stocks_data is None or stocks_data.empty:
        return None

    stocks_data_dict = {symbol: stocks_data[stocks_data['Symbol'] == symbol]}
    if symbol not in stocks_data_dict or stocks_data_dict[symbol].empty:
        return None

    try:
        _, _, backtest_objects = run_multi_symbol_backtest(
            stocks_data_dict,
            System,
            config_final,
            [symbol],
            20,
            logging.getLogger(__name__),
        )
    except Exception as bt_err:
        logging.getLogger(__name__).warning("Error en backtest on-demand para grafico %s: %s", symbol, bt_err)
        return None

    bt_result = (backtest_objects or {}).get(symbol)
    if bt_result is None:
        return None

    try:
        # 1) Generar el HTML nativo del motor (mismo look & feel que antes)
        html = _render_native_backtest_html(bt_result, resultado.id)

        # 2) Persistir snapshot estructurado como respaldo (sin guardar HTML pesado)
        payload = _build_graph_snapshot_payload(symbol, intervalo, stocks_data_dict[symbol], bt_result)
        resultado.grafico_html = GRAPH_SNAPSHOT_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        db.session.commit()

        # 3) Devolver HTML del motor; si no se pudo, fallback al render desde snapshot
        if html:
            return html
        return _render_bokeh_html_from_snapshot(payload, resultado)
    except Exception as regen_err:
        db.session.rollback()
        logging.getLogger(__name__).warning("No se pudo persistir grafico regenerado para %s (id=%s): %s", symbol, resultado.id, regen_err)
        return None


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


def obtener_usuarios_registrados():
    
    try:
        usuarios = {u.username.lower(): u.password for u in Usuario.query.all()}
        return usuarios
    except Exception as exc:
        db.session.rollback()
        logging.getLogger(__name__).warning("Fallo recuperando usuarios registrados: %s", exc)
        return {"admin": "admin"} # Fallback de emergencia

# --- RUTA PRINCIPAL (INDEX) ---
@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))

    user_mode = session.get('user_mode')

    try:
        u = Usuario.query.filter_by(username=user_mode).first()
    except Exception as exc:
        db.session.rollback()
        logging.getLogger(__name__).warning("Fallo recuperando usuario de sesion '%s': %s", user_mode, exc)
        u = None

    # ================================================================
    # --- LÓGICA POST (Guardado de Configuración en DB) ---
    # ================================================================
    if request.method == 'POST' and request.form.get('action') == 'save_config':
        form_data = request.form.to_dict()
        if 'fecha_fin' in form_data and 'end_date' not in form_data:
            form_data['end_date'] = form_data['fecha_fin']

        try:
            _persist_user_runtime_config(u, form_data)
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

    # Carga de configuración desde DB
    config_para_web = {}
    if u and u.config_actual:
        try:
            config_para_web = json.loads(u.config_actual) if isinstance(u.config_actual, str) else u.config_actual
            for key, value in config_para_web.items():
                if value is True:
                    config_para_web[key] = 'True'
                elif value is False:
                    config_para_web[key] = 'False'
        except:
            config_para_web = {}

    if not config_para_web:
        for attr in dir(System):
            if not attr.startswith("__"):
                val = getattr(System, attr)
                if not callable(val):
                    config_para_web[attr] = str(val)

    ayer = date.today() - timedelta(days=1)
    config_para_web['end_date'] = ayer.isoformat()

    simbolos_db = Simbolo.query.filter_by(usuario_id=u.id).all() if u else []
    symbols_text = ", ".join([s.symbol for s in simbolos_db]) if simbolos_db else "AAPL, MSFT"

    # Historial de resultados (Ordenado por fecha descendente)
    # Las queries se hacen siempre desde la BD (los objetos SQLAlchemy no se cachean).
    # Si el thread de background los cargó previamente, el pg buffer cache los acelera.
    registros_agrupados = {}
    try:
        # 1. OPTIMIZACION + PAGINACION POR TANDAS
        # Importante: limitar por filas puede ocultar tandas antiguas cuando una tanda nueva
        # genera muchos activos. Para evitar "desapariciones" visuales, primero limitamos
        # las tandas recientes y luego cargamos todos sus registros.
        tandas_limit = 50

        tandas_query = db.session.query(
            ResultadoBacktest.usuario_id,
            ResultadoBacktest.id_estrategia,
            func.max(ResultadoBacktest.fecha_ejecucion).label('max_fecha')
        )

        if user_mode != 'admin' and u:
            tandas_query = tandas_query.filter(ResultadoBacktest.usuario_id == u.id)
        elif user_mode != 'admin' and not u:
            tandas_query = tandas_query.filter(False)

        tandas_rows = tandas_query.group_by(
            ResultadoBacktest.usuario_id,
            ResultadoBacktest.id_estrategia
        ).order_by(
            func.max(ResultadoBacktest.fecha_ejecucion).desc()
        ).limit(tandas_limit).all()

        todos = []
        if user_mode == 'admin':
            for tanda in tandas_rows:
                tanda_rows = ResultadoBacktest.query.options(
                    joinedload(ResultadoBacktest.propietario)
                ).filter(
                    ResultadoBacktest.usuario_id == tanda.usuario_id,
                    ResultadoBacktest.id_estrategia == tanda.id_estrategia,
                ).order_by(
                    ResultadoBacktest.fecha_ejecucion.desc()
                ).all()
                todos.extend(tanda_rows)
        else:
            if u:
                for tanda in tandas_rows:
                    tanda_rows = ResultadoBacktest.query.options(
                        joinedload(ResultadoBacktest.propietario)
                    ).filter(
                        ResultadoBacktest.usuario_id == u.id,
                        ResultadoBacktest.id_estrategia == tanda.id_estrategia,
                    ).order_by(
                        ResultadoBacktest.fecha_ejecucion.desc()
                    ).all()
                    todos.extend(tanda_rows)

        # Para todos: cargar trades en una sola consulta
        todos_ids = [r.id for r in todos]
        all_trades_dict = {}
        if todos_ids:
            trades_batch = Trade.query.filter(Trade.backtest_id.in_(todos_ids)).all()
            for trade in trades_batch:
                if trade.backtest_id not in all_trades_dict or trade.id > all_trades_dict[trade.backtest_id].id:
                    all_trades_dict[trade.backtest_id] = trade

        # 2. Agrupamos manteniendo el orden de aparición (que ya viene ordenado por fecha)
        for r in todos:
            tanda_key = f"{r.usuario_id}_{r.id_estrategia}" if user_mode == 'admin' else r.id_estrategia

            if tanda_key not in registros_agrupados:
                registros_agrupados[tanda_key] = {
                    'id_tanda': r.id_estrategia,
                    'usuario_id': r.usuario_id,
                    'fecha_raw': r.fecha_ejecucion,
                    'fecha': r.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
                    'usuario_nombre': r.propietario.username,
                    'titulo_estrategia': _build_strategy_short_title(r),
                    'diagnostico_lote': r.notas,
                    'activos': []
                }
            registros_agrupados[tanda_key]['activos'].append(r)

        # 3. Enriquecer cada backtest con el último trade
        for tanda_key, tanda_data in registros_agrupados.items():
            for backtest in tanda_data['activos']:
                last_trade = all_trades_dict.get(backtest.id)
                if last_trade:
                    backtest.ultima_operacion_fecha = last_trade.fecha
                    backtest.ultima_operacion_tipo = format_position_state(last_trade.tipo)
                else:
                    backtest.ultima_operacion_fecha = '-'
                    backtest.ultima_operacion_tipo = '-'

                # El boton de grafico debe estar siempre disponible para regeneracion on-demand.
                backtest.graph_available = True
                backtest.has_graph = True

    except Exception as e:
        print(f"Error historial: {e}")

    # 4. Ordenar tandas por fecha descendente
    tandas_ordenadas = dict(sorted(
        registros_agrupados.items(),
        key=lambda x: x[1]['fecha_raw'],
        reverse=True
    ))

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

    usuarios_gestion = []
    if user_mode == 'admin':
        try:
            usuarios_gestion = Usuario.query.order_by(Usuario.username.asc()).all()
        except Exception as exc:
            db.session.rollback()
            logging.getLogger(__name__).warning("Fallo recuperando lista de usuarios para gestion: %s", exc)
            usuarios_gestion = []

    return render_template(
        'index.html',
        system=System,
        strategy=System,
        config=config_para_web,
        symbols_content=symbols_text,
        file_tree=arbol_ficheros, 
        registros=tandas_ordenadas, # Enviamos las tandas ya ordenadas
        comments=VARIABLE_COMMENTS,
        usuarios_gestion=usuarios_gestion,
        usuarios=usuarios_gestion
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
            skipped_count = int((resultados_df.attrs.get('skipped_symbols_count', 0) if resultados_df is not None else 0) or 0)
            if resultados_df is not None and not resultados_df.empty:
                completion_message = f"Backtest finalizado. {len(resultados_df)} resultados guardados."
                if skipped_count:
                    completion_message += f" {skipped_count} activos omitidos por falta de datos suficientes o válidos."
                _finish_backtest_status(
                    user_mode=user_mode,
                    status='completed',
                    message=completion_message,
                    result_count=len(resultados_df)
                )
                logger.info(f"✅ ÉXITO | {len(resultados_df)} resultados procesados")
                logger.info(f"✅ Gráficos generados: {len(graficos_dict)}")
                logger.info(f"{'='*70}\n")
                print(f"✅ Backtest finalizado para {user_mode}. {len(resultados_df)} resultados guardados.")
            else:
                completion_message = 'Backtest finalizado sin resultados para guardar.'
                if skipped_count:
                    completion_message += f" {skipped_count} activos omitidos por falta de datos suficientes o válidos."
                _finish_backtest_status(
                    user_mode=user_mode,
                    status='completed',
                    message=completion_message,
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
        
        # Reset defensivo de sesion DB por si hubo un cursor cerrado en request previa.
        try:
            db.session.rollback()
        except Exception:
            pass

        user_mode = session.get('user_mode')
        logger.info(f"[LAUNCH] Usuario {user_mode} lanzando backtest...")

        try:
            u = Usuario.query.filter_by(username=user_mode).first()
        except ResourceClosedError:
            db.session.rollback()
            db.session.remove()
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

        try:
            _persist_user_runtime_config(u, form_data)
            db.session.commit()
        except Exception as persist_error:
            db.session.rollback()
            logger.error(f"[LAUNCH] No se pudo guardar configuración previa al lanzamiento: {persist_error}")
            return jsonify({"status": "error", "message": f"No se pudo guardar la configuración antes del lanzamiento: {persist_error}"}), 500

        config_web = {}

        # 1. Cargar valores por defecto de la clase System
        for attr in dir(System):
            if not attr.startswith("__"):
                val = getattr(System, attr)
                if not callable(val):
                    config_web[attr] = val

        # 2. LISTA MAESTRA DE BOOLEANOS (Switches de tu UI)
        # Asegúrate de que los nombres coincidan exactamente con el 'name' en tu HTML
        switches = SAVEABLE_BOOLEAN_FIELDS

        # 3. PROCESAR EL FORMULARIO
        for key, value in form_data.items():
            if key in switches:
                config_web[key] = True  # Si llegó en el POST, es que estaba ON
            elif value == "" or value.lower() == 'none':
                config_web[key] = None
            else:
                # Intentar convertir a numero para el motor (acepta coma decimal)
                raw_value = str(value).strip()
                numeric_value = raw_value.replace(',', '.')
                try:
                    if any(ch in numeric_value for ch in ('.', 'e', 'E')):
                        config_web[key] = float(numeric_value)
                    else:
                        config_web[key] = int(numeric_value)
                except Exception:
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

    status_data = _read_scheduler_status_file(SCHEDULER_STATUS_PATH)
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

    pid_is_running = _is_scheduler_running_from_pid(SCHEDULER_PID_PATH)

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
    was_running = _is_scheduler_running_from_pid(SCHEDULER_PID_PATH)
    
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
        status_data = _read_scheduler_status_file(SCHEDULER_STATUS_PATH)
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
            status_data = _read_scheduler_status_file(SCHEDULER_STATUS_PATH)
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
        status_data = _read_scheduler_status_file(SCHEDULER_STATUS_PATH)
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

        def _to_number(value):
            try:
                if value is None:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        def _parse_signal_context(raw_value):
            if not raw_value:
                return None
            try:
                parsed = json.loads(raw_value)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None

        return jsonify([{
            'tipo': t.tipo,
            'descripcion': t.descripcion,
            'fecha': t.fecha,
            'entrada': _to_number(t.precio_entrada),
            'salida': _to_number(t.precio_salida),
            'pnl': _to_number(t.pnl_absoluto),
            'retorno': _to_number(t.retorno_pct),
            'trigger': (_parse_signal_context(t.signal_context) or {}).get('trigger'),
            'signal_context': _parse_signal_context(t.signal_context),
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
        # 1. Determinamos el usuario propietario de la tanda.
        # Si se pasa usuario_id como query param (admin descargando tanda ajena), lo usamos.
        # En caso contrario usamos el usuario de la sesión.
        usuario_id_param = request.args.get('usuario_id', type=int)
        if usuario_id_param is not None:
            u = Usuario.query.get(usuario_id_param)
        else:
            u = Usuario.query.filter_by(username=user_mode).first()

        if u is None:
            return "Usuario no encontrado", 404

        # 2. Filtramos la tanda para el usuario correcto
        resultados = ResultadoBacktest.query.filter_by(id_estrategia=tanda_id, usuario_id=u.id).all()
        ids_resultados = [r.id for r in resultados]
        
        trades = Trade.query.filter(Trade.backtest_id.in_(ids_resultados)).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            'Usuario',
            'Tanda',
            'Activo',
            'Tipo',
            'Fecha',
            'Entrada',
            'Salida',
            'PnL_Abs',
            'Retorno_Pct',
            'Trigger',
            'Signal_Context',
        ])

        for t in trades:
            signal_context = {}
            if t.signal_context:
                try:
                    parsed_signal_context = json.loads(t.signal_context)
                    if isinstance(parsed_signal_context, dict):
                        signal_context = parsed_signal_context
                except Exception:
                    signal_context = {}

            writer.writerow([
                user_mode,
                tanda_id,
                t.backtest.symbol,
                t.tipo,
                t.fecha,
                t.precio_entrada,
                t.precio_salida,
                t.pnl_absoluto,
                t.retorno_pct,
                signal_context.get('trigger', ''),
                t.signal_context or '',
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
            'Trigger',
            'Signal_Context',
            *ordered_param_keys,
        ])

        for t in trades:
            bt = t.backtest
            params_row = params_by_backtest.get(bt.id, {}) if bt is not None else {}
            signal_context = {}
            if t.signal_context:
                try:
                    parsed_signal_context = json.loads(t.signal_context)
                    if isinstance(parsed_signal_context, dict):
                        signal_context = parsed_signal_context
                except Exception:
                    signal_context = {}
            writer.writerow([
                bt.propietario.username if bt and bt.propietario else '',
                bt.id_estrategia if bt else '',
                bt.symbol if bt else '',
                t.tipo, t.fecha, t.precio_entrada, 
                t.precio_salida, t.pnl_absoluto, t.retorno_pct,
                signal_context.get('trigger', ''),
                t.signal_context or '',
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

# -- LIMPIAR DATOS ADMIN --
@main_bp.route('/limpiar_datos_admin', methods=['POST'])
def limpiar_datos_admin():
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    if session.get('user_mode') != 'admin':
        return jsonify({"success": False, "message": "Acceso denegado"}), 403
    
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        fecha_limite_str = data.get('fecha_limite')
        
        if not usuario_id or not fecha_limite_str:
            return jsonify({"success": False, "message": "Parámetros incompletos"}), 400
        
        # Convertir string de fecha a objeto datetime
        fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
        
        # Verificar que el usuario existe
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Obtener todos los backtests del usuario que sean anteriores a la fecha límite
        backtests_a_eliminar = ResultadoBacktest.query.filter(
            ResultadoBacktest.usuario_id == usuario_id,
            ResultadoBacktest.fecha_ejecucion < datetime.combine(fecha_limite, datetime.min.time())
        ).all()
        
        # Contar los trades que serán eliminados
        trades_count = 0
        for backtest in backtests_a_eliminar:
            trades_count += Trade.query.filter(Trade.backtest_id == backtest.id).count()
        
        # Eliminar todos los trades asociados a esos backtests
        for backtest in backtests_a_eliminar:
            Trade.query.filter(Trade.backtest_id == backtest.id).delete()
        
        # Eliminar los backtests
        backtests_eliminados = len(backtests_a_eliminar)
        for backtest in backtests_a_eliminar:
            db.session.delete(backtest)
        
        # Confirmar cambios
        db.session.commit()
        
        mensaje = f"Limpieza completada: Se eliminaron {backtests_eliminados} tandas y {trades_count} operaciones del usuario '{usuario.username}' anteriores a {fecha_limite_str}."
        
        return jsonify({
            "success": True, 
            "message": mensaje
        }), 200
        
    except ValueError as e:
        return jsonify({"success": False, "message": f"Formato de fecha inválido: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error al limpiar datos: {str(e)}"}), 500

# -- GUARDAR CONFIGURACIÓN EN FICHERO DEL USUARIO --
@main_bp.route('/save_config_file', methods=['POST'])
def save_config_file():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        user_mode = session.get('user_mode')
        u = Usuario.query.filter_by(username=user_mode).first()
        if not u:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        form_data = request.form.to_dict()
        if 'fecha_fin' in form_data and 'end_date' not in form_data:
            form_data['end_date'] = form_data['fecha_fin']

        config_params = _build_config_params_from_form_data(
            form_data,
            SAVEABLE_BOOLEAN_FIELDS,
            include_dates=False,
        )
        symbols_list = _extract_symbols_from_form_data(form_data)
        requested_name = form_data.get('config_file_name') or _build_default_snapshot_filename(user_mode, config_params)

        payload = {
            "usuario": user_mode,
            "fecha_guardado": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "configuracion": config_params,
            "activos": symbols_list,
        }
        file_path = _write_config_snapshot(user_mode, requested_name, payload)

        return jsonify({
            "status": "success",
            "message": f"Configuración guardada en {file_path.name}",
            "filename": file_path.name,
            "suggested_filename": _build_default_snapshot_filename(user_mode, config_params),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/list_config_files')
def list_config_files():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        user_mode = session.get('user_mode')
        user_dir = _user_config_snapshot_dir(user_mode)
        if not user_dir.exists():
            return jsonify({"status": "success", "files": []})

        files = []
        for file_path in sorted(user_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            stats = file_path.stat()
            files.append({
                "name": file_path.name,
                "modified_at": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M'),
                "size": stats.st_size,
            })
        return jsonify({"status": "success", "files": files})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/load_config_file', methods=['POST'])
def load_config_file():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        payload = request.get_json(silent=True) or {}
        filename = payload.get('filename', '')
        if not filename:
            return jsonify({"status": "error", "message": "Debes seleccionar un fichero"}), 400

        user_mode = session.get('user_mode')
        u = Usuario.query.filter_by(username=user_mode).first()
        if not u:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        safe_name = _sanitize_filename_component(Path(filename).stem) + '.json'
        file_path = _user_config_snapshot_dir(user_mode) / safe_name
        if not file_path.exists():
            return jsonify({"status": "error", "message": "El fichero no existe"}), 404

        data = json.loads(file_path.read_text(encoding='utf-8'))
        config_data = data.get('configuracion') or {}
        activos = data.get('activos') or []

        runtime_config = dict(config_data)
        runtime_config.pop('end_date', None)
        u.config_actual = json.dumps(runtime_config, ensure_ascii=True)
        Simbolo.query.filter_by(usuario_id=u.id).delete()
        for sym_name in activos:
            normalized = _normalize_symbol_token(sym_name)
            if normalized:
                db.session.add(Simbolo(symbol=normalized, name=normalized, usuario_id=u.id))
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"Configuración cargada desde {safe_name}",
            "configuracion": config_data,
            "activos": activos,
            "filename": safe_name,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

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
                _remove_graph_artifacts_for_result(activo)
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
        if not session.get('logged_in'):
            return redirect(url_for('main.login'))

        user_mode = session.get('user_mode')

        # 1. Buscamos en la DB (Asegúrate de que reg_id coincida con el nombre del argumento)
        resultado = ResultadoBacktest.query.get_or_404(reg_id)

        # 1.1 Control de acceso: admin ve todo; usuario normal solo sus registros
        if user_mode != 'admin':
            usuario = Usuario.query.filter_by(username=user_mode).first()
            if not usuario:
                return redirect(url_for('main.login'))
            if resultado.usuario_id != usuario.id:
                return "<h3>No tienes permiso para visualizar este gráfico.</h3>", 403
        
        # 2. Regenerar on-demand para mantener el look original de gráficos.
        #    Si falla, usar respaldo desde snapshot/legacy DB.
        graph_html = _regenerate_graph_html_on_demand(resultado, user_mode)
        if not graph_html:
            graph_html = _read_graph_html_with_cache(resultado)

        if not graph_html:
            return (
                "<html><body style='font-family:Segoe UI,Arial,sans-serif;padding:24px;'>"
                "<h3>Grafico no disponible para este backtest</h3>"
                "<p>No se pudo regenerar el grafico para este activo en este momento.</p>"
                "<p>Revisa que haya datos de mercado para el rango configurado y vuelve a intentarlo.</p>"
                "</body></html>",
                200,
            )
        
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

        page_html = graph_html
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
    
    except HTTPException:
        raise
    except Exception as e:
        return f"<h3>Error al recuperar gráfico: {str(e)}</h3>", 500
    
# --- AUTENTICACIÓN ---

def _require_admin_session():
    if not session.get('logged_in'):
        return False, redirect(url_for('main.login'))
    if session.get('user_mode') != 'admin':
        flash("❌ Acceso restringido a administradores", "danger")
        return False, redirect(url_for('main.index'))
    return True, None


@main_bp.route('/admin/users/create', methods=['POST'])
def admin_users_create():
    ok, resp = _require_admin_session()
    if not ok:
        return resp

    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()

    if not username or not password:
        flash("❌ Usuario y contraseña son obligatorios", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    exists = Usuario.query.filter(func.lower(Usuario.username) == username).first()
    if exists:
        flash(f"❌ El usuario '{username}' ya existe", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    try:
        nuevo = Usuario(username=username, password=password)
        db.session.add(nuevo)
        db.session.commit()
        flash(f"✅ Usuario '{username}' creado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al crear usuario: {e}", "danger")

    return redirect(url_for('main.index', _anchor='pane-users'))


@main_bp.route('/admin/users/update/<int:user_id>', methods=['POST'])
def admin_users_update(user_id):
    ok, resp = _require_admin_session()
    if not ok:
        return resp

    target = Usuario.query.get_or_404(user_id)
    new_username = request.form.get('username', '').strip().lower()
    new_password = request.form.get('password', '').strip()

    if not new_username:
        flash("❌ El nombre de usuario no puede estar vacío", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    if target.username.lower() == 'admin' and new_username != 'admin':
        flash("❌ El usuario admin no puede cambiar de nombre", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    exists = Usuario.query.filter(
        func.lower(Usuario.username) == new_username,
        Usuario.id != target.id
    ).first()
    if exists:
        flash(f"❌ Ya existe otro usuario con nombre '{new_username}'", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    try:
        target.username = new_username
        if new_password:
            target.password = new_password
        db.session.commit()
        flash(f"✅ Usuario '{new_username}' actualizado", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar usuario: {e}", "danger")

    return redirect(url_for('main.index', _anchor='pane-users'))


@main_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_users_delete(user_id):
    ok, resp = _require_admin_session()
    if not ok:
        return resp

    target = Usuario.query.get_or_404(user_id)
    current_user = session.get('user_mode', '').lower().strip()

    if target.username.lower() == 'admin':
        flash("❌ El usuario admin no se puede eliminar", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    if target.username.lower() == current_user:
        flash("❌ No puedes eliminar tu propio usuario en sesión", "danger")
        return redirect(url_for('main.index', _anchor='pane-users'))

    try:
        db.session.delete(target)
        db.session.commit()
        flash("✅ Usuario eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar usuario: {e}", "danger")

    return redirect(url_for('main.index', _anchor='pane-users'))

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
            return redirect(url_for('main.cargando'))
        flash("❌ Usuario o contraseña incorrectos", "danger")
    return render_template('login.html')


#-- RUTA DE CARGA CON PROGRESO POST-LOGIN --
@main_bp.route('/cargando')
def cargando():
    """Pantalla de transición simple antes de renderizar index()."""
    if not session.get('logged_in'):
        return redirect(url_for('main.login'))
    user_mode = session.get('user_mode', '')
    delay_ms = 1200 if user_mode == 'admin' else 500
    return render_template('cargando_simple.html', user_mode=user_mode, delay_ms=delay_ms)


#-- RUTA DE LOGOUT --
@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))