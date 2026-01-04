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

# 1. Detección dinámica de la raíz buscando un marcador (como la carpeta .venv o Backtesting)
def find_project_root(current_path):
    for parent in current_path.parents:
        # Usamos .lower() para evitar errores de Windows vs Linux
        child_names = [child.name.lower() for child in parent.iterdir() if child.is_dir()]
        if "backtesting" in child_names and "data_files" in child_names:
            return parent
        if parent.name == "TradingCore":
            return parent
    return current_path.parents[1]

# ----------------------------------------------------------------------
# --- RUTAS MAESTRAS Y RAÍZ (ESTRUCTURA CORREGIDA) ---
# ----------------------------------------------------------------------
WEB_STRATEGY_DIR = Path(__file__).parent 
PROJECT_ROOT = find_project_root(WEB_STRATEGY_DIR)

# 🎯 CONFIGURACIÓN GLOBAL DE CORREO (Centralizada para todos los usuarios)
# Ubicación: TradingCore/trading_engine/utils/Config/setup_mail.env
MAIL_CONFIG_GLOBAL = PROJECT_ROOT / "trading_engine" / "utils" / "Config" / "setup_mail.env"

# Ahora Backtesting está en la raíz: TradingCore/Backtesting
BACKTESTING_BASE_DIR = PROJECT_ROOT / "Backtesting"

# 3. 🎯 NUEVA CARPETA DE DATOS (Sustituye a OneDrive)
# Se crea en TradingCore/Data_Files
DATA_FILES_BASE_PATH = PROJECT_ROOT / "Data_Files"

# Moldes ahora en: TradingCore/Backtesting/Config/
CONFIG_MAESTRA_DIR = BACKTESTING_BASE_DIR / "Config" / "templates"
PLANTILLA_ENV = CONFIG_MAESTRA_DIR / "variables_setup.env"
PLANTILLA_CSV = CONFIG_MAESTRA_DIR / "symbols.csv"

# Para el archivo de usuarios en Backtesting/users.csv
RUTA_USERS_CSV = BACKTESTING_BASE_DIR / "users.csv"

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
    # 1. Carpeta de CONFIGURACIÓN personal (Donde viven su .env y sus símbolos)
    user_config_dir = BACKTESTING_BASE_DIR / "Config" / user_mode
    user_config_dir.mkdir(parents=True, exist_ok=True)

    # 2. Carpeta de RESULTADOS (Donde van los CSVs generados)
    user_results_dir = BACKTESTING_BASE_DIR / "Run_Results" / user_mode
    user_results_dir.mkdir(parents=True, exist_ok=True)

    # 3. Carpeta de GRÁFICOS
    user_graph_dir = BACKTESTING_BASE_DIR / "Graphics" / user_mode
    user_graph_dir.mkdir(parents=True, exist_ok=True)

    # Definimos dónde deben estar sus ficheros de configuración
    f_var = user_config_dir / "variables_setup.env"
    f_sym = user_config_dir / "symbols.csv"

    print(f"\n--- 🛠️  INICIALIZANDO ENTORNO: {user_mode} ---")

    # Clonación de .env (desde Config_templates a Config/usuario/)
    if not f_var.exists() or f_var.stat().st_size == 0:
        if PLANTILLA_ENV.exists():
            shutil.copy(PLANTILLA_ENV, f_var)
            print(f"✅ Molde .env clonado con éxito para {user_mode}.")
        else:
            print(f"⚠️ AVISO: No se encontró molde .env en {PLANTILLA_ENV}.")
            f_var.touch()

    # Clonación de symbols.csv
    if not f_sym.exists() or f_sym.stat().st_size == 0:
        if PLANTILLA_CSV.exists():
            shutil.copy(PLANTILLA_CSV, f_sym)
            print(f"✅ Molde symbols.csv clonado con éxito para {user_mode}.")
        else:
            print(f"⚠️ AVISO: No se encontró molde .csv en {PLANTILLA_CSV}.")
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
    
    # 1. Leemos los valores actuales para identificar cuáles son booleanos
    config_actual = dotenv_values(env_path)
    
    # 2. Primero, actualizamos con TODO lo que sí viene en el formulario
    # (Esto cubre strings como el Email, números y switches en ON)
    for key, valor_nuevo in parametros.items():
        set_key(str(env_path), key, str(valor_nuevo))
    
    # 3. Lógica General para Switches Apagados (OFF):
    # Recorremos el .env actual. Si una llave era booleana pero NO ha venido 
    # en el POST, significa que el usuario ha movido el switch a OFF.
    for key, val_prev in config_actual.items():
        if key not in parametros:
            # Comprobamos si el valor previo era un booleano
            # (Limpiamos comillas por si acaso)
            val_clean = str(val_prev).lower().strip().replace("'", "").replace('"', "")
            
            if val_clean in ['true', 'false', 'on', 'off']:
                # Si era un booleano y no ha llegado en el POST, es que está en OFF
                set_key(str(env_path), key, "False")

# ----------------------------------------------------------------------
# --- CARGA Y ASIGNACIÓN ---
# ----------------------------------------------------------------------

def cargar_y_asignar_configuracion(user_mode="invitado"):
    rutas = inicializar_configuracion_usuario(user_mode)
    
    # Asegurarnos de que el archivo existe y tiene tamaño > 0 antes de leer
    f_var = rutas['fichero_variables']
    if f_var.exists() and f_var.stat().st_size > 0:
        # override=True es vital para que no use valores antiguos de memoria
        load_dotenv(f_var, override=True)
        config_data = dotenv_values(f_var)
    else:
        config_data = {}
        logger.warning(f"Archivo de variables vacío o no listo en: {f_var}")

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

    # --- Opciones de Ejecución y Correo ---
    System.usar_filtro_fundamental = get_param('usar_filtro_fundamental', False, bool)
    System.enviar_mail = get_param('enviar_mail', False, bool)
    System.destinatario_email = get_param('destinatario_email', 'juantxu@yahoo.com', str)

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
        'full_ratio_path': full_ratio_path,
        'fichero_mail': MAIL_CONFIG_GLOBAL  # <--- Inyectamos la ruta global aquí
    })

    return resultado