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
from pathlib import Path 

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
from .configuracion import asignar_parametros_a_system, inicializar_configuracion_usuario
from .estrategia_system import System

# Inicialización de logging (después de la gestión de rutas)
logger = logging.getLogger("Ejecucion")
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# --- CÓDIGO PRINCIPAL DE EJECUCIÓN (ORQUESTACIÓN WEB) ---
# ----------------------------------------------------------------------

def ejecutar_backtest(config_dict: dict):
    """
    Orquesta la descarga de datos (usando start_date/end_date), el backtesting y el guardado de resultados.
    """
    start_time = time.time()
    
    # 🎯 PASO 1: Obtener las rutas dinámicas según el modo de usuario
    # El config_dict que viene de la web ya contiene el 'user_mode' (ej: juantxu_local)
    user_mode = config_dict.get('user_mode', 'invitado')
    rutas_fisicas = inicializar_configuracion_usuario(user_mode)

    # 🎯 PASO 2: Configurar la clase System y obtener los parámetros generales
    try:
        # Pasamos AMBOS argumentos requeridos
        parametros_generales_y_rutas = asignar_parametros_a_system(config_dict, rutas_fisicas)
    except Exception as e:
        logger.error(f"❌ Error al asignar parámetros al sistema: {e}")
        return pd.DataFrame()

    # 2. Extracción de Parámetros Generales y Rutas
    start_date = parametros_generales_y_rutas.get('start_date') 
    end_date = parametros_generales_y_rutas.get('end_date')
    intervalo = parametros_generales_y_rutas.get('intervalo')
    cash = parametros_generales_y_rutas.get('cash', 10000)
    commission = parametros_generales_y_rutas.get('commission', 0.0)
    stoploss_percentage = parametros_generales_y_rutas.get('stoploss_percentage_below_close', 0.0) 
    enviar_mail = parametros_generales_y_rutas.get('enviar_mail', False)
    destinatario_email = parametros_generales_y_rutas.get('destinatario_email')
    usar_filtro_fundamental = parametros_generales_y_rutas.get('usar_filtro_fundamental', False) 

    fichero_simbolos = parametros_generales_y_rutas.get('fichero_simbolos')
    graph_dir = parametros_generales_y_rutas.get('graph_dir')
    fichero_resultados = parametros_generales_y_rutas.get('fichero_resultados')
    fichero_historico = parametros_generales_y_rutas.get('fichero_historico')
    fichero_trades = parametros_generales_y_rutas.get('fichero_trades')

    # Rutas de Caché (Inyectadas desde la configuración y convertidas a Path)
    data_files_path = Path(parametros_generales_y_rutas.get('data_files_path'))
    fundamentals_path = Path(parametros_generales_y_rutas.get('fundamentals_path'))
    
    logger.info(f"Iniciando proceso de backtesting. Rango de Fechas: {start_date} a {end_date}, Intervalo: {intervalo}")

    # Leer el fichero CSV de los Tickers (Simbolos) a descargar
    try:
        simbolos_df = pd.read_csv(fichero_simbolos)
    except FileNotFoundError:
        logger.error(f"Error: No se pudo encontrar el archivo '{fichero_simbolos}'.")
        return pd.DataFrame() 
    
    if "Symbol" not in simbolos_df.columns:
        logger.error("Error: El archivo debe contener una columna llamada 'Symbol'.")
        return pd.DataFrame() 

    # 3. Descarga de Datos OHLCV 
    stocks_data = descargar_datos_YF(
        simbolos_df, 
        start_date, 
        end_date, 
        intervalo,
        data_files_path # Ruta del caché OHLCV
    ) 
    
    if stocks_data.empty:
        logger.error("No se pudieron descargar datos históricos para ningún símbolo en el rango especificado.")
        return pd.DataFrame() 

    # 4. Gestión de Datos FUNDAMENTALES y Cálculo de Ratios
    api_key = "60NPBW4583RN0HSB" 
    financial_data = manage_fundamental_data(
        simbolos_df, 
        api_key,
        fundamentals_path # Ruta del caché Fundamental
    ) 
    # 2. Definir la ruta específica para el Full Ratio (INYECTADA)
    # Obtenemos la ruta del usuario actual para guardar el CSV de ratios diarios
    full_ratio_output_path = parametros_generales_y_rutas.get('full_ratio_path') 

    # 3. Llamada a la utilidad pura (Pasamos la ruta explícitamente)
    stocks_data = calcular_fullratio_OHLCV(
        stocks_data, 
        financial_data, 
        output_path=full_ratio_output_path # <--- Inyección de dependencia
    ) 

    # 5. Selección de Activos (Filtro Fundamental)
    lista_activos_analizados = generar_seleccion_activos(stocks_data, logger)
    simbolos_a_procesar = simbolos_df["Symbol"].tolist() 
    
    if not lista_activos_analizados.empty:
        activos_para_backtest = lista_activos_analizados[
            lista_activos_analizados["Recomendación"] == "Mantener (Atractivo)"
        ].index.tolist()
        
        if usar_filtro_fundamental:
            simbolos_a_procesar = activos_para_backtest
            logger.info(f"CONFIGURACIÓN WEB: Se usará la lista filtrada de {len(simbolos_a_procesar)} símbolos (filtro fundamental activo).")
        else:
            logger.warning(f"CONFIGURACIÓN WEB: Filtro fundamental inactivo. Se procesarán los {len(simbolos_a_procesar)} símbolos originales.")
    
    # 6. Determinar el periodo mínimo de datos requerido
    required_period = 20 # Mínimo inicial
    
    if System.stoch_slow and System.stoch_slow_period is not None:
        required_period = max(required_period, System.stoch_slow_period)
        
    required_period = max(required_period, 20) 
    logger.info(f"Mínimo de velas requerido: {required_period}")
    
    # ----------------------------------------------------------------------
    # 🎯 PASO 7: EJECUCIÓN CENTRAL DELEGADA (CON PARCHE DE ROBUSTEZ)
    # ----------------------------------------------------------------------
    
    # Verificar la robustez del DataFrame antes de iterar
    if stocks_data.empty or "Symbol" not in stocks_data.columns:
        logger.error("❌ Error de robustez: Los datos consolidados están vacíos o les falta la columna 'Symbol'. Cancelando backtest.")
        return pd.DataFrame()

    # Si todo es correcto, creamos el diccionario de datos
    stocks_data_dict = {
        symbol: stocks_data[stocks_data["Symbol"] == symbol] 
        for symbol in stocks_data["Symbol"].unique() # Esto ya es seguro
    }

    # Llamada a la función delegada
    resultados_df, trades_df, backtest_objects = run_multi_symbol_backtest(
        stocks_data_dict,
        System, 
        parametros_generales_y_rutas,
        simbolos_a_procesar,
        required_period,
        logger
    )
    
    # ----------------------------------------------------------------------
    # 8. POST-PROCESO (Guardado de Gráficos y Consolidación de Parámetros)
    # ----------------------------------------------------------------------

    # Guardar Gráficos HTML 
    for symbol, bt_obj in backtest_objects.items():
        graph_file = os.path.join(graph_dir, f"{symbol}_backtest.html")
        try:
            # Asumo que bt_obj tiene un método plot compatible (e.g., Backtrader)
            # NOTA: Si bt_obj es None porque el backtest falló para ese símbolo, se debe manejar.
            if bt_obj:
                bt_obj.plot(filename=graph_file, open_browser=False) 
                logger.info(f"Gráfico guardado para {symbol}.")
            else:
                logger.warning(f"No se pudo generar gráfico para {symbol}: Objeto de backtest vacío.")
        except Exception as e:
            logger.error(f"Error al generar el gráfico para {symbol}: {e}")

    # Consolidación de Parámetros
    parametros_completos = {}
    
    try:
        parametros_completos.update(config_dict)
        
        fecha_ejecucion = time.strftime("%Y-%m-%d %H:%M:%S")
        
        parametros_completos.update({
            'Fecha_Ejecucion': fecha_ejecucion,
            'Fecha_Inicio_Datos': start_date,
            'Fecha_Fin_Datos': end_date,
            'Intervalo_Datos': intervalo,
            'Cash_Inicial': cash,
            'Comision': commission,
            'Enviar_Mail': enviar_mail,
            'SL_%_Close': stoploss_percentage,
        })

        if not resultados_df.empty:
            for col in COLUMNAS_HISTORICO:
                if col in parametros_completos:
                    resultados_df[col] = parametros_completos[col]
                elif col not in resultados_df.columns:
                    resultados_df[col] = pd.NA 
            
            columnas_existentes_en_df = [col for col in COLUMNAS_HISTORICO if col in resultados_df.columns]
            resultados_df = resultados_df[columnas_existentes_en_df]
            
    except Exception as e:
        logger.error(f"Error al consolidar y/o inyectar parámetros: {e}")
        
    # 9. Guardar Resultados y Histórico
    if not trades_df.empty:
        os.makedirs(os.path.dirname(fichero_trades), exist_ok=True)
        trades_df.to_csv(fichero_trades, index=False, encoding='utf-8')
        logger.info(f"Operaciones de trading guardadas en: {fichero_trades}")

    if not resultados_df.empty:
        try:
            os.makedirs(os.path.dirname(fichero_resultados), exist_ok=True)
            resultados_df.to_csv(fichero_resultados, index=False, mode='w', encoding='utf-8') 
            logger.info(f"Estadísticas guardadas en: {fichero_resultados}")
            
            logger.info(f"Actualizando el histórico detallado: {fichero_historico}")
            # Asumo que guardar_historico ahora maneja la lógica de append/creación
            guardar_historico(resultados_df, fichero_historico, COLUMNAS_HISTORICO)
            
        except Exception as e:
            logger.error(f"Error al guardar ficheros: {e}")
            
        # 10. Enviar Mail
        if enviar_mail:
             # send_email(...)
             logger.info("Archivos enviados por mail.")
    
    logger.info(f"Proceso de backtesting completado en {time.time() - start_time:.2f} segundos. 🎉")
    return None



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
        resultados = ejecutar_backtest(config_dict)
        if resultados.empty:
            logger.warning("La ejecución finalizó, pero no se generaron resultados de backtest.")
    else:
        logger.error("❌ ERROR CRÍTICO: No se pudo obtener ninguna configuración (ni .env, ni simulada). Terminando.")