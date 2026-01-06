import logging
import shutil
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values 
from datetime import datetime, timedelta

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
        logger = logging.getLogger("Configuracion")
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

CONFIG_MAESTRA_DIR = BACKTESTING_BASE_DIR / "Config" / "templates"
PLANTILLA_ENV = CONFIG_MAESTRA_DIR / "variables_setup.env"
PLANTILLA_CSV = CONFIG_MAESTRA_DIR / "symbols.csv"
RUTA_USERS_CSV = BACKTESTING_BASE_DIR / "users.csv"

# ----------------------------------------------------------------------
# --- LOGGING ---
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Configuracion")

# ----------------------------------------------------------------------
# --- GESTIÓN DINÁMICA DE USUARIOS ---
# ----------------------------------------------------------------------

def inicializar_configuracion_usuario(user_mode="invitado"):
    user_config_dir = BACKTESTING_BASE_DIR / "Config" / user_mode
    user_results_dir = BACKTESTING_BASE_DIR / "Run_Results" / user_mode
    user_graph_dir = BACKTESTING_BASE_DIR / "Graphics" / user_mode
    
    for p in [user_config_dir, user_results_dir, user_graph_dir]:
        p.mkdir(parents=True, exist_ok=True)

    f_var = user_config_dir / "variables_setup.env"
    f_sym = user_config_dir / "symbols.csv"

    # Clonación de moldes
    if not f_var.exists() or f_var.stat().st_size == 0:
        if PLANTILLA_ENV.exists():
            shutil.copy(PLANTILLA_ENV, f_var)
        else:
            f_var.touch()

    if not f_sym.exists() or f_sym.stat().st_size == 0:
        if PLANTILLA_CSV.exists():
            shutil.copy(PLANTILLA_CSV, f_sym)
        else:
            f_sym.touch()

    return {
        "user_mode": user_mode,
        "results_dir": user_results_dir,
        "graph_dir": user_graph_dir,
        "fichero_variables": f_var,
        "fichero_simbolos": f_sym,
        "fichero_resultados": user_results_dir / "resultados_estrategia.csv",
        "fichero_historico": user_graph_dir / "resultados_historico.csv",
        "fichero_trades": user_results_dir / "trades_log.csv"
    }

# ----------------------------------------------------------------------
# --- PERSISTENCIA Y LECTURA ---
# ----------------------------------------------------------------------

def read_config_with_metadata(fichero_variables_path):
    config_data = dotenv_values(fichero_variables_path)
    return dict(config_data), {}

def guardar_parametros_a_env(parametros: dict, user_mode):
    rutas = inicializar_configuracion_usuario(user_mode)
    env_path = rutas['fichero_variables']
    config_actual = dotenv_values(env_path)
    
    for key, valor_nuevo in parametros.items():
        set_key(str(env_path), key, str(valor_nuevo))
    
    for key, val_prev in config_actual.items():
        if key not in parametros:
            val_clean = str(val_prev).lower().strip().replace("'", "").replace('"', "")
            if val_clean in ['true', 'false', 'on', 'off']:
                set_key(str(env_path), key, "False")

# ----------------------------------------------------------------------
# --- CARGA Y ASIGNACIÓN ---
# ----------------------------------------------------------------------

def cargar_y_asignar_configuracion(user_mode="invitado"):
    rutas = inicializar_configuracion_usuario(user_mode)
    f_var = rutas['fichero_variables']
    if f_var.exists() and f_var.stat().st_size > 0:
        load_dotenv(f_var, override=True)
        config_data = dotenv_values(f_var)
    else:
        config_data = {}
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
    System.usar_filtro_fundamental = get_param('usar_filtro_fundamental', False, bool)
    System.enviar_mail = get_param('enviar_mail', False, bool)
    System.destinatario_email = get_param('destinatario_email', '', str)

    # --- 2. EMA ---
    System.ema_active = get_param('ema_active', False, bool)
    System.ema_cruce_signal = get_param('ema_cruce_signal', False, bool)
    System.ema_fast_period = get_param('ema_fast_period', 5, int)
    System.ema_slow_period = get_param('ema_slow_period', 30, int)
    System.ema_buy_logic = get_param('ema_buy_logic', 'None')
    System.ema_sell_logic = get_param('ema_sell_logic', 'None')

    # --- 3. RSI ---
    System.rsi = get_param('rsi', False, bool)
    System.rsi_period = get_param('rsi_period', 14, int)
    System.rsi_low_level = get_param('rsi_low_level', 30, int)
    System.rsi_high_level = get_param('rsi_high_level', 70, int)
    System.rsi_strength_threshold = get_param('rsi_strength_threshold', 50, int)
    System.rsi_buy_logic = get_param('rsi_buy_logic', 'None')
    System.rsi_sell_logic = get_param('rsi_sell_logic', 'None')

    # --- 4. MACD ---
    System.macd = get_param('macd', False, bool)
    System.macd_fast_period = get_param('macd_fast_period', 12, int)
    System.macd_slow_period = get_param('macd_slow_period', 26, int)
    System.macd_signal_period = get_param('macd_signal_period', 9, int)
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