# ----------------------------------------------------------------------
# --- configuración.py ---
# ----------------------------------------------------------------------
# Descripción       : Gestión de configuración y parámetros de usuario  
# Fecha de modificación : 2026-02-01
# ----------------------------------------------------------------------


import json
import logging
from pathlib import Path
import shutil

# Importamos db
from trading_engine.core.database_pg import db



# ----------------------------------------------------------------------
# --- IMPORTACIÓN DE LA CLASE SYSTEM ---
# ----------------------------------------------------------------------
try:
    import estrategia_system as es
    System = es.System
except ImportError:
    try:
        from .estrategia_system import System
    except ImportError:
        logger.warning("No se pudo importar la clase 'System'. Usando placeholder.")
        class System: pass

# 1. Detección dinámica de la raíz
def find_project_root(current_path):
    for parent in current_path.parents:
        try:
            child_names = [child.name.lower() for child in parent.iterdir() if child.is_dir()]
            if "backtesting" in child_names and "data_files" in child_names:
                return parent
            if parent.name == "TradingCore":
                return parent
        except: continue
    return current_path.parents[1]

# ----------------------------------------------------------------------
# --- RUTAS MAESTRAS Y RAÍZ ---
# ----------------------------------------------------------------------
WEB_STRATEGY_DIR = Path(__file__).parent 
PROJECT_ROOT = find_project_root(WEB_STRATEGY_DIR)

MAIL_CONFIG_GLOBAL = PROJECT_ROOT / "trading_engine" / "utils" / "Config" / "setup_mail.env"
BACKTESTING_BASE_DIR = PROJECT_ROOT / "Backtesting"
DATA_FILES_BASE_PATH = PROJECT_ROOT / "Data_Files"

# Restaurada la variable DB_URI que solicitaste
DB_URI = "postgresql+pg8000://postgres:admin@localhost:5433/trading_db"

# ----------------------------------------------------------------------
# --- LOGGING CONFIGURATION ---
# ----------------------------------------------------------------------
LOG_FILE_PATH = PROJECT_ROOT / "Backtesting" / "logs" / "trading_app.log"
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# En lugar de basicConfig, solo haz esto:
logger = logging.getLogger("Configuracion")
# El handler se heredará del que configuramos en app.py

# ----------------------------------------------------------------------
# --- GESTIÓN DINÁMICA DE USUARIOS ---
# ----------------------------------------------------------------------

# Mantengo el nombre original: inicializar_configuracion_usuario
def inicializar_configuracion_usuario(user_mode="invitado"):
    """
    Crea las carpetas de resultados y gráficos. 
    Se han eliminado las referencias a symbols.csv y variables.env
    """
    user_results_dir = BACKTESTING_BASE_DIR / "Run_Results" / user_mode
    user_graph_dir = BACKTESTING_BASE_DIR / "Graphics" / user_mode
    user_log_dir = BACKTESTING_BASE_DIR / "logs"

    for p in [user_results_dir, user_graph_dir]:
        p.mkdir(parents=True, exist_ok=True)

    return {
        "user_mode": user_mode,
        "results_dir": user_results_dir,
        "graph_dir": user_graph_dir,
        "log_file": user_log_dir / "trading_app.log", # Ruta que leerá el admin
        "fichero_resultados": user_results_dir / "resultados_estrategia.csv",
        "fichero_historico": user_graph_dir / "resultados_historico.csv",
        "fichero_trades": user_results_dir / "trades_log.csv"
    }

# ----------------------------------------------------------------------
# --- PERSISTENCIA Y LECTURA ---
# ----------------------------------------------------------------------

def guardar_parametros_a_db(parametros: dict, user_mode):
    from .database import Usuario 

    try:
        usuario = Usuario.query.filter_by(username=user_mode).first()
        if usuario:
            config_dict = {}
            if usuario.config_actual:
                config_dict = json.loads(usuario.config_actual) if isinstance(usuario.config_actual, str) else usuario.config_actual
            
            config_dict.update(parametros)
            usuario.config_actual = json.dumps(config_dict)
            db.session.commit()
            logger.info(f"💾 DB actualizada con éxito para {user_mode}")
            return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error guardando en DB: {e}")
        return False

# ----------------------------------------------------------------------
# --- CARGA Y ASIGNACIÓN ---
# ----------------------------------------------------------------------

def cargar_y_asignar_configuracion(user_mode="admin"):
    from .database import Usuario 

    rutas = inicializar_configuracion_usuario(user_mode)
    config_data = {}
    
    try:
        usuario = Usuario.query.filter_by(username=user_mode).first()
        if usuario and usuario.config_actual:
            if isinstance(usuario.config_actual, str):
                config_data = json.loads(usuario.config_actual)
            else:
                config_data = usuario.config_actual
            logger.info(f"✅ Configuración recuperada de DB para: {user_mode}")
        else:
            logger.warning(f"⚠️ Sin config en DB para {user_mode}. Usando valores por defecto.")
    
    except Exception as e:
        logger.error(f"❌ Error de DB en configuracion.py: {e}")

    return asignar_parametros_a_system(config_data, rutas)

def asignar_parametros_a_system(config_data: dict, rutas: dict):
    def get_param(key, default, type_func=str):
        value = config_data.get(key)
        if value is None or value == '': return default
        try:
            val_clean = str(value).strip().strip('"').strip("'")
            if type_func is bool: return val_clean.lower() in ['true', 'on', '1', 'yes']
            if type_func is int: return int(float(val_clean))
            if type_func is float: return float(val_clean)
            return type_func(val_clean)
        except: return default

    # --- 1. GENERALES ---
    System.start_date = get_param('start_date', None)
    System.end_date = get_param('end_date', None)
    System.intervalo = get_param('intervalo', '1d')
    System.cash = get_param('cash', 10000, int)
    System.commission = get_param('commission', 0.0, float)
    System.stoploss_percentage_below_close = get_param('stoploss_percentage_below_close', 0.0, float)
    
    # Stop Loss por Swing
    System.stoploss_swing_enabled = get_param('stoploss_swing_enabled', False, bool)
    System.stoploss_swing_lookback = get_param('stoploss_swing_lookback', 10, int)
    System.stoploss_swing_buffer = get_param('stoploss_swing_buffer', 1.0, float)
    
    System.filtro_fundamental = get_param('filtro_fundamental', False, bool)
    System.enviar_mail = get_param('enviar_mail', False, bool)
    System.destinatario_email = get_param('destinatario_email', '', str)

    # --- 2. EMA ---
    System.ema_cruce_signal = get_param('ema_cruce_signal', False, bool)
    System.ema_fast_period = get_param('ema_fast_period', 5, int)
    System.ema_slow_period = get_param('ema_slow_period', 30, int)
    System.ema_slow_minimo = get_param('ema_slow_minimo', False, bool)
    System.ema_slow_ascendente = get_param('ema_slow_ascendente', False, bool)
    System.ema_slow_descendente = get_param('ema_slow_descendente', False, bool)
    System.ema_slow_maximo = get_param('ema_slow_maximo', False, bool)
    System.ema_buy_logic = get_param('ema_buy_logic', 'None')
    System.ema_sell_logic = get_param('ema_sell_logic', 'None')

    # --- 3. RSI ---
    System.rsi = get_param('rsi', False, bool)
    System.rsi_period = get_param('rsi_period', 14, int)
    System.rsi_low_level = get_param('rsi_low_level', 30, int)
    System.rsi_high_level = get_param('rsi_high_level', 70, int)
    System.rsi_strength_threshold = get_param('rsi_strength_threshold', 50, int)
    # RSI Flags (Señales OR y Deniegos AND)
    System.rsi_minimo = get_param('rsi_minimo', False, bool)
    System.rsi_maximo = get_param('rsi_maximo', False, bool)
    System.rsi_ascendente = get_param('rsi_ascendente', False, bool)
    System.rsi_descendente = get_param('rsi_descendente', False, bool)
    System.rsi_buy_logic = get_param('rsi_buy_logic', 'None')
    System.rsi_sell_logic = get_param('rsi_sell_logic', 'None')

    # --- 4. MACD ---
    System.macd = get_param('macd', False, bool)
    System.macd_fast = get_param('macd_fast', 12, int)
    System.macd_slow = get_param('macd_slow', 26, int)
    System.macd_signal = get_param('macd_signal', 9, int)
    System.macd_buy_logic = get_param('macd_buy_logic', 'None')
    System.macd_sell_logic = get_param('macd_sell_logic', 'None')

    # --- 5. ESTOCÁSTICOS ---
    for s in ['fast', 'mid', 'slow']:
        setattr(System, f'stoch_{s}', get_param(f'stoch_{s}', False, bool))
        setattr(System, f'stoch_{s}_period', get_param(f'stoch_{s}_period', 14, int))
        setattr(System, f'stoch_{s}_smooth', get_param(f'stoch_{s}_smooth', 3, int))
        setattr(System, f'stoch_{s}_low_level', get_param(f'stoch_{s}_low_level', 20, int))
        setattr(System, f'stoch_{s}_high_level', get_param(f'stoch_{s}_high_level', 80, int))
        setattr(System, f'stoch_{s}_buy_logic', get_param(f'stoch_{s}_buy_logic', 'None'))
        setattr(System, f'stoch_{s}_sell_logic', get_param(f'stoch_{s}_sell_logic', 'None'))

    # --- 6. BOLLINGER BANDS ---
    System.bb_active = get_param('bb_active', False, bool)
    System.bb_window = get_param('bb_window', 20, int)
    System.bb_num_std = get_param('bb_num_std', 2.0, float)
    System.bb_buy_crossover = get_param('bb_buy_crossover', False, bool)
    System.bb_sell_crossover = get_param('bb_sell_crossover', False, bool)
    System.bb_window_state = get_param('bb_window_state', 20, int)

    # --- 7. RIESGO Y CONTEXTO ---
    System.margen_seguridad_active = get_param('margen_seguridad_active', False, bool)
    System.margen_seguridad_threshold = get_param('margen_seguridad_threshold', 50.0, float)
    System.margen_seguridad_minimo = get_param('margen_seguridad_minimo', False, bool)
    System.margen_seguridad_ascendente = get_param('margen_seguridad_ascendente', False, bool)
    
    System.volume_active = get_param('volume_active', False, bool)
    System.volume_period = get_param('volume_period', 20, int)
    System.volume_avg_multiplier = get_param('volume_avg_multiplier', 1.0, float)
    System.volume_minimo = get_param('volume_minimo', False, bool)
    System.volume_ascendente = get_param('volume_ascendente', False, bool)

    # ----------------------------------------------------------------------
    # --- GESTIÓN DE RUTAS Y RETORNO ---
    # ----------------------------------------------------------------------
    user_mode = rutas.get('user_mode', 'invitado')
    data_files_path = DATA_FILES_BASE_PATH
    fundamentals_path = data_files_path / "Fundamentals"
    full_ratio_path = rutas['results_dir'] / "FullRatio"

    for p in [data_files_path, fundamentals_path, full_ratio_path, rutas['graph_dir']]:
        p.mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ Configuración cargada y TIPADA para usuario: {user_mode}")

    all_params = {k: getattr(System, k) for k in dir(System) if not k.startswith('_') and not callable(getattr(System, k))}
    resultado = {**all_params, **rutas}
    resultado.update({
        'data_files_path': data_files_path,
        'fundamentals_path': fundamentals_path,
        'full_ratio_path': full_ratio_path,
        'fichero_mail': MAIL_CONFIG_GLOBAL
    })

    return resultado