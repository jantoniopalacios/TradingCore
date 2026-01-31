"""Script principal para ejecutar el backtesting de la estrategia System.
Adaptado para ser el orquestador del ESCENARIO WEB, utilizando el motor central (Backtest_Runner) 
y las nuevas utilidades de descarga basadas en un rango de fechas fijo.
"""

# ----------------------------------------------------------------------
# --- IMPORTACIONES CORE Y UTILS (Absolutas) ---
# ----------------------------------------------------------------------
import pandas as pd
import numpy as np
import logging
import sys
import os
import time
from datetime import datetime
from pathlib import Path 

from bokeh.embed import file_html
from bokeh.resources import CDN

import json
from .DBStore import save_backtest_run

# ----------------------------------------------------------------------
# --- SOLUCIÓN DE RUTA SIMPLIFICADA (Para trading_engine a nivel de raíz) ---
# ----------------------------------------------------------------------

# Obtiene la ruta del script actual: /TradingCore/scenarios/BacktestWeb
script_dir = os.path.dirname(os.path.abspath(__file__)) 

# Sube DOS niveles (a /TradingCore/, la raíz del proyecto)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) 

if project_root not in sys.path:
    # Inyectamos la raíz del proyecto para que Python encuentre 'trading_engine'
    sys.path.insert(0, project_root) 
    # Usamos logging más abajo, aquí solo print si es necesario, pero lo quitamos para no generar ruido.

# ----------------------------------------------------------------------
# --- IMPORTACIONES DEL MOTOR trading_engine (Simplificadas) ---
# ----------------------------------------------------------------------
# NOTA: Estas importaciones asumen la nueva estructura: trading_engine/core, trading_engine/utils
try:
    from trading_engine.core.Backtest_Runner import run_multi_symbol_backtest 
    from trading_engine.utils.Data_download import descargar_datos_YF, manage_fundamental_data
    from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV, generar_seleccion_activos
    from trading_engine.utils.utils_mail import send_email
    from trading_engine.utils.Historico_manager import guardar_historico
    from trading_engine.core.constants import COLUMNAS_HISTORICO 
except ImportError as e:
    # Esto atrapará errores si la estructura no fue movida correctamente
    print(f"ERROR CRÍTICO DE IMPORTACIÓN: No se pudo encontrar el módulo del motor 'trading_engine'. Verifique que la carpeta 'trading_engine' se encuentre en la raíz del proyecto y contenga __init__.py. Error: {e}", file=sys.stderr)
    sys.exit(1)


# ----------------------------------------------------------------------
# --- IMPORTACIONES LOCALES DEL ESCENARIO ---
# ----------------------------------------------------------------------
try:
    # Intento de importación relativa (cuando se lanza desde app.py / Flask)
    from .configuracion import asignar_parametros_a_system, inicializar_configuracion_usuario
except (ImportError, ValueError):
    # Intento de importación absoluta (cuando se lanza el script directamente)
    from configuracion import asignar_parametros_a_system, inicializar_configuracion_usuario
from .estrategia_system import System

# Inicialización de logging (después de la gestión de rutas)
logger = logging.getLogger("Ejecucion")
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# --- CÓDIGO PRINCIPAL DE EJECUCIÓN (ORQUESTACIÓN WEB) ---
# ----------------------------------------------------------------------

def ejecutar_backtest(config_dict: dict):
    """
    Orquesta la descarga de datos, el backtesting y el guardado de resultados.
    Versión LIMPIA: Se eliminan normalizadores manuales y prints de debug excesivos.
    """
    start_time = time.time()
    
    # 1. Identificar al usuario y cargar rutas base del disco
    user_mode = config_dict.get('user_mode') or 'invitado'
    from .configuracion import cargar_y_asignar_configuracion, asignar_parametros_a_system
    
    # Cargamos rutas y configuración base (.env)
    datos_base = cargar_y_asignar_configuracion(user_mode)

    # 2. MESTIZAJE ÚNICO: La WEB (config_dict) manda sobre el DISCO (datos_base)
    config_final = {**datos_base, **config_dict}

    # 3. Sincronizar la clase System (prioridad absoluta a los datos mezclados)
    asignar_parametros_a_system(config_final, config_final)

    # 4. Extracción limpia de variables necesarias
    start_date = config_final.get('start_date') 
    end_date = config_final.get('end_date')
    intervalo = config_final.get('intervalo')
    cash = float(config_final.get('cash', 10000))
    filtro_fundamental = config_final.get('filtro_fundamental', False) 
    
    # Rutas convertidas a Path
    data_files_path = Path(config_final.get('data_files_path'))
    fundamentals_path = Path(config_final.get('fundamentals_path'))
    
    logger.info(f"🚀 Iniciando Backtest Web | Usuario: {user_mode} | Rango: {start_date} a {end_date}")

    # 5. Obtener Símbolos desde la DB
    from .database import Simbolo, Usuario
    u_actual = Usuario.query.filter_by(username=user_mode).first()
    if not u_actual:
        logger.error(f"Usuario '{user_mode}' no encontrado.")
        return None, None, {}

    simbolos_usuario = Simbolo.query.filter_by(usuario_id=u_actual.id).all()
    simbolos_df = pd.DataFrame([{"Symbol": s.symbol, "Name": s.name} for s in simbolos_usuario])
    
    # 6. Descarga y Cálculos (OHLCV + Fundamentales)
    stocks_data = descargar_datos_YF(simbolos_df, start_date, end_date, intervalo, data_files_path) 
    
    if stocks_data.empty:
        logger.error("No hay datos históricos disponibles.")
        return None, None, {} 

    financial_data = manage_fundamental_data(simbolos_df, "60NPBW4583RN0HSB", fundamentals_path) 
    stocks_data = calcular_fullratio_OHLCV(stocks_data, financial_data, output_path=config_final.get('full_ratio_path')) 

    # 7. Selección de Activos con Filtro Fundamental Simplificado
    simbolos_a_procesar = simbolos_df["Symbol"].tolist() 
    if filtro_fundamental:
        lista_activos = generar_seleccion_activos(stocks_data, logger)
        if not lista_activos.empty:
            simbolos_a_procesar = lista_activos[lista_activos["Recomendación"] == "Mantener (Atractivo)"].index.tolist()
            logger.info(f"Filtro Fundamental Activo: Procesando {len(simbolos_a_procesar)} activos filtrados.")
    else:
        logger.info(f"Filtro Fundamental Inactivo: Procesando todos los activos ({len(simbolos_a_procesar)}).")

    # 8. Ejecución del Motor (Backtest_Runner)
    stocks_data_dict = {s: stocks_data[stocks_data["Symbol"] == s] for s in stocks_data["Symbol"].unique()}
    
    resultados_df, trades_df, backtest_objects = run_multi_symbol_backtest(
        stocks_data_dict, System, config_final, simbolos_a_procesar, 20, logger
    )

    # 9. Guardado de Gráficos y Resultados en DB
    diccionario_graficos_html = {} 
    graph_dir = Path(config_final.get('graph_dir'))

    for symbol, bt_results in backtest_objects.items():
        if bt_results:
            graph_file = graph_dir / f"{symbol}_backtest.html"
            bt_results.plot(filename=str(graph_file), open_browser=False)
            if graph_file.exists():
                with open(graph_file, 'r', encoding='utf-8') as f:
                    diccionario_graficos_html[symbol] = f.read()

    # 10. Persistencia en base de datos delegada a DBStore
    if not resultados_df.empty:
        try:
            current_user_id = config_dict.get('user_id', 1)
            for _, row in resultados_df.iterrows():
                ticker = row['Symbol']
                save_backtest_run(
                    user_id=current_user_id,
                    stats=row.to_dict(),
                    config_dict=config_final,
                    trades_df=trades_df[trades_df['Symbol'] == ticker] if not trades_df.empty else None,
                    grafico_html=diccionario_graficos_html.get(ticker)
                )
            logger.info("✅ Resultados guardados en base de datos.")
        except Exception as e:
            logger.error(f"Error en persistencia DB: {e}")

    logger.info(f"✨ Backtest completado en {time.time() - start_time:.2f}s.")
    return resultados_df, trades_df, diccionario_graficos_html


# ======================================================================
# Bloque de ejecución principal (Necesario si se ejecuta directamente)
# ======================================================================

if __name__ == '__main__':
    
    # 1. Configuración de Logging (Asegurar que ves los mensajes)
    # Si no tienes un archivo de configuración de logging, añade esto temporalmente:
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger("Ejecucion") # Asegurar que el logger 'Ejecucion' está configurado
    
    logger.info("Ejecución de Backtest.py iniciada directamente.")
    
    try:
        # Importación LOCAL para evitar problemas de rutas en el inicio
        from configuracion import read_config_with_metadata 
    except ImportError:
        logger.error("❌ ERROR: No se puede importar 'read_config_with_metadata' de configuracion.py. Verifica la ruta.")
        sys.exit(1)

    # 2. Cargar Configuración
    
    # La función read_config_with_metadata debería leer el .env (configuración base)
    config_dict, _ = read_config_with_metadata(None) 
    
    if not config_dict:
        logger.warning("⚠️ ADVERTENCIA: No se pudo cargar la configuración completa desde el .env. Usando valores simulados.")
        # Usar los valores simulados si no se encuentra el .env
        simulated_config = {
            # Asegúrate de que estas fechas sean válidas y exista el símbolo en el fichero CSV
            'start_date': '2022-01-01', 
            'end_date': '2024-01-01',
            'intervalo': '1d',
            'cash': 10000,
            # Asegúrate de añadir AQUÍ todos los parámetros necesarios que el orquestador espera
            # como los parámetros de la estrategia y la ruta al fichero_simbolos si no está en el .env
        }
        config_dict = simulated_config 

    # 3. Ejecutar la función principal
    if config_dict:
        res_df, trades_df, graphs = ejecutar_backtest(config_dict)
        if res_df is None or res_df.empty:
            logger.warning("La ejecución finalizó, pero no se generaron resultados de backtest.")
    else:
        logger.error("❌ ERROR CRÍTICO: No se pudo obtener ninguna configuración (ni .env, ni simulada). Terminando.")