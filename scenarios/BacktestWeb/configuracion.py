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

# ----------------------------------------------------------------------
# --- RUTAS MAESTRAS Y RAÍZ (ESTRUCTURA CORREGIDA) ---
# ----------------------------------------------------------------------
WEB_STRATEGY_DIR = Path(__file__).parent 

# Buscar el nombre de la carpeta por si acaso
PROJECT_ROOT = next(p for p in WEB_STRATEGY_DIR.parents if p.name == "TradingCore")

# Ahora Backtesting está en la raíz: TradingCore/Backtesting
BACKTESTING_BASE_DIR = PROJECT_ROOT / "Backtesting"

# 3. 🎯 NUEVA CARPETA DE DATOS (Sustituye a OneDrive)
# Se crea en TradingCore/Data_Files
DATA_FILES_BASE_PATH = PROJECT_ROOT / "Data_Files"

# Moldes ahora en: TradingCore/Backtesting/Config/
CONFIG_MAESTRA_DIR = BACKTESTING_BASE_DIR / "Config"
PLANTILLA_ENV = CONFIG_MAESTRA_DIR / "variables_setup.env"
PLANTILLA_CSV = CONFIG_MAESTRA_DIR / "symbols.csv"

# Para verificar en la consola si la ruta es correcta al arrancar
print(f"DEBUG: Raíz detectada: {PROJECT_ROOT.absolute()}")
print(f"DEBUG: Buscando Backtesting en: {BACKTESTING_BASE_DIR.absolute()}")



# ----------------------------------------------------------------------
# --- LOGGING ---
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Configuracion")

# ----------------------------------------------------------------------
# --- GESTIÓN DINÁMICA DE USUARIOS ---
# ----------------------------------------------------------------------

def inicializar_configuracion_usuario(user_mode="invitado"):
    user_results_dir = BACKTESTING_BASE_DIR / "Run_Results" / user_mode
    user_results_dir.mkdir(parents=True, exist_ok=True)

    user_graph_dir = BACKTESTING_BASE_DIR / "Graphics" / user_mode
    user_graph_dir.mkdir(parents=True, exist_ok=True)

    f_var = user_results_dir / "variables_setup.env"
    f_sym = user_results_dir / "symbols.csv"

    print(f"\n--- 🛠️  INICIALIZANDO ENTORNO: {user_mode} ---")

    # Clonación de .env
    if not f_var.exists():
        if PLANTILLA_ENV.exists():
            shutil.copy(PLANTILLA_ENV, f_var)
            print(f"✅ Molde .env clonado con éxito.")
        else:
            print(f"⚠️ AVISO: No se encontró molde .env en {PLANTILLA_ENV}. Se creará uno vacío.")
            f_var.touch() # Crea el archivo vacío para evitar errores de lectura

    # Clonación de symbols.csv
    if not f_sym.exists():
        if PLANTILLA_CSV.exists():
            shutil.copy(PLANTILLA_CSV, f_sym)
            print(f"✅ Molde symbols.csv clonado con éxito.")
        else:
            print(f"⚠️ AVISO: No se encontró molde .csv en {PLANTILLA_CSV}. Se creará uno vacío.")
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
    
    for key in config_actual.keys():
        if key in parametros:
            valor_nuevo = str(parametros[key])
            set_key(str(env_path), key, valor_nuevo)
        else:
            val_prev = config_actual[key].lower().replace("'", "").replace('"', "")
            if val_prev in ['true', 'false', 'on', 'off']:
                set_key(str(env_path), key, "False")

# ----------------------------------------------------------------------
# --- CARGA Y ASIGNACIÓN ---
# ----------------------------------------------------------------------

def cargar_y_asignar_configuracion(user_mode="invitado"):
    rutas = inicializar_configuracion_usuario(user_mode)
    load_dotenv(rutas['fichero_variables'], override=True)
    config_data = dotenv_values(rutas['fichero_variables'])
    return asignar_parametros_a_system(config_data, rutas)

def asignar_parametros_a_system(config_data: dict, rutas: dict):
    # 1. Función auxiliar para limpiar y tipar datos (Mantenemos tu lógica robusta)
    def get_param(key, default, type_func=str):
        value = config_data.get(key)
        if value is None or value == '': return default
        try:
            val_clean = str(value).strip().strip('"').strip("'")
            if type_func is bool: 
                return val_clean.lower() in ['true', 'on', '1', 'yes']
            if type_func is int: return int(float(val_clean))
            if type_func is float: return float(val_clean)
            return type_func(val_clean)
        except: return default

    # ----------------------------------------------------------------------
    # 🎯 2. ASIGNACIÓN MASIVA A LA CLASE SYSTEM (El Motor de la Estrategia)
    # ----------------------------------------------------------------------
    
    # --- Parámetros Generales de Backtest ---
    System.start_date = get_param('start_date', None)
    System.end_date = get_param('end_date', None)
    System.intervalo = get_param('intervalo', '1d')
    System.cash = get_param('cash', 10000, int)
    System.commission = get_param('commission', 0.0, float)
    System.stoploss_percentage_below_close = get_param('stoploss_percentage_below_close', 0.0, float)

    # --- INDICADORES: EMA (Clave para que se vean las curvas) ---
    System.ema_active = get_param('ema_active', False, bool)
    System.ema_cruce_signal = get_param('ema_cruce_signal', False, bool)
    System.ema_fast_period = get_param('ema_fast_period', 5, int)
    System.ema_slow_period = get_param('ema_slow_period', 30, int)
    System.ema_buy_logic = get_param('ema_buy_logic', 'None')
    System.ema_sell_logic = get_param('ema_sell_logic', 'None')

    # --- INDICADORES: RSI ---
    System.rsi = get_param('rsi', False, bool)
    System.rsi_period = get_param('rsi_period', 14, int)
    System.rsi_low_level = get_param('rsi_low_level', 30, int)
    System.rsi_high_level = get_param('rsi_high_level', 70, int)
    System.rsi_strength_threshold = get_param('rsi_strength_threshold', 50, int)
    System.rsi_buy_logic = get_param('rsi_buy_logic', 'None')

    # --- INDICADORES: MACD ---
    System.macd = get_param('macd', False, bool)
    System.macd_fast_period = get_param('macd_fast_period', 12, int)
    System.macd_slow_period = get_param('macd_slow_period', 26, int)
    System.macd_signal_period = get_param('macd_signal_period', 9, int)
    System.macd_buy_logic = get_param('macd_buy_logic', 'None')

    # --- INDICADORES: ESTOCÁSTICOS (Fast, Mid, Slow) ---
    for suffix in ['fast', 'mid', 'slow']:
        setattr(System, f'stoch_{suffix}', get_param(f'stoch_{suffix}', False, bool))
        setattr(System, f'stoch_{suffix}_period', get_param(f'stoch_{suffix}_period', 14, int))
        setattr(System, f'stoch_{suffix}_low_level', get_param(f'stoch_{suffix}_low_level', 20, int))
        setattr(System, f'stoch_{suffix}_buy_logic', get_param(f'stoch_{suffix}_buy_logic', 'None'))

    # --- INDICADORES: BOLLINGER BANDS ---
    System.bb_active = get_param('bb_active', False, bool)
    System.bb_window = get_param('bb_window', 20, int)
    System.bb_num_std = get_param('bb_num_std', 2.0, float)
    System.bb_buy_crossover = get_param('bb_buy_crossover', False, bool)

    # --- FILTROS DE VOLUMEN Y MARGEN DE SEGURIDAD ---
    System.volume_active = get_param('volume_active', False, bool)
    System.volume_period = get_param('volume_period', 20, int)
    System.volume_avg_multiplier = get_param('volume_avg_multiplier', 1.0, float)
    
    System.margen_seguridad_active = get_param('margen_seguridad_active', False, bool)
    System.margen_seguridad_threshold = get_param('margen_seguridad_threshold', 50.0, float)

    # ----------------------------------------------------------------------
    # 🎯 3. GESTIÓN DE RUTAS Y RETORNO
    # ----------------------------------------------------------------------
    user_mode = rutas.get('user_mode', 'invitado')
    data_files_path = DATA_FILES_BASE_PATH
    fundamentals_path = data_files_path / "Fundamentals"
    full_ratio_path = rutas['results_dir'] / "FullRatio"

    for p in [data_files_path, fundamentals_path, full_ratio_path, rutas['graph_dir']]:
        p.mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ Configuración cargada y TIPADA para usuario: {user_mode}")

    # Construcción del diccionario de retorno para el orquestador
    all_params = {k: getattr(System, k) for k in dir(System) if not k.startswith('_') and not callable(getattr(System, k))}
    resultado = {**all_params, **rutas}
    resultado.update({
        'data_files_path': data_files_path,
        'fundamentals_path': fundamentals_path,
        'full_ratio_path': full_ratio_path
    })
    
    return resultado