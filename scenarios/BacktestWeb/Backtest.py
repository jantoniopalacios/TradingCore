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
    Orquesta la descarga de datos (usando start_date/end_date), el backtesting y el guardado de resultados.
    """
    start_time = time.time()
    
    # 🎯 PASO 1: RE-CONFIGURACIÓN FORZADA DE LOGGING
    from .configuracion import PROJECT_ROOT
    log_path = PROJECT_ROOT / "trading_app.log"
    
    # Obtenemos el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Evitamos duplicar handlers si ya existen
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log de prueba inicial
    logging.info(f"--- NUEVO BACKTEST INICIADO POR USUARIO: {config_dict.get('user_mode')} ---")

    # 🎯 PASO 2: Cargar la configuración REAL del usuario desde el disco
    user_mode = config_dict.get('user_mode', 'invitado')
    
    # Importamos la función de carga que ya creamos en configuracion.py
    from .configuracion import cargar_y_asignar_configuracion
    
    # Esto lee el .env de juan, lo aplica a System y nos da el diccionario con TODO (fechas incluidas)
    parametros_generales_y_rutas = cargar_y_asignar_configuracion(user_mode)

    # Extraemos la nueva ruta del mail que viene de configuracion.py
    fichero_mail_setup = parametros_generales_y_rutas.get('fichero_mail')

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
    # 🎯 PASO 8: Guardado de Gráficos usando Pathlib (Más robusto)
    graph_dir = Path(parametros_generales_y_rutas.get('graph_dir'))
    for symbol, bt_obj in backtest_objects.items():
        graph_file = graph_dir / f"{symbol}_backtest.html"
        try:
            if bt_obj:
                # Convertimos Path a string porque algunas librerías de plotting no aceptan objetos Path
                bt_obj.plot(filename=str(graph_file), open_browser=False) 
                logger.info(f"✅ Gráfico guardado para {symbol} en {user_mode}")
        except Exception as e:
            logger.error(f"❌ Error gráfico {symbol}: {e}")

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

            # ... (Dentro de ejecutar_backtest, después de guardar_historico)

            if not resultados_df.empty:
                try:
                    from .database import db, ResultadoBacktest, Trade, Usuario
                    from flask import current_app
                    from datetime import datetime

                    with current_app.app_context():
                        user_obj = Usuario.query.filter_by(username=user_mode).first()
                        if not user_obj:
                            logger.error(f"❌ DB: Usuario {user_mode} no encontrado.")
                            return None

                        for _, row in resultados_df.iterrows():
                            # Mapeo exacto según tu CSV de ejemplo
                            nuevo_bt = ResultadoBacktest(
                                usuario_id=user_obj.id,
                                symbol=str(row.get('Symbol', 'N/A')),
                                sharpe_ratio=float(row.get('Sharpe Ratio', 0) or 0),
                                max_drawdown=float(row.get('Max Drawdown [%]', 0) or 0),
                                profit_factor=float(row.get('Profit Factor', 0) or 0),
                                return_pct=float(row.get('Return [%]', 0) or 0),
                                total_trades=int(row.get('Total Trades', 0) or 0),
                                win_rate=float(row.get('Win Rate [%]', 0) or 0),
                                
                                # Datos temporales
                                fecha_ejecucion=datetime.now(),
                                fecha_inicio_datos=str(start_date),
                                fecha_fin_datos=str(end_date),
                                intervalo=str(intervalo)
                            )
                            db.session.add(nuevo_bt)
                            db.session.flush() 

                            # Guardar Trades si existen
                            if not trades_df.empty:
                                # Filtramos trades por el símbolo actual (ej: NVDA)
                                trades_simbolo = trades_df[trades_df['Symbol'] == row.get('Symbol')]
                                for _, t_row in trades_simbolo.iterrows():
                                    nuevo_trade = Trade(
                                        backtest_id=nuevo_bt.id,
                                        tipo=str(t_row.get('Type', 'N/A')),
                                        fecha=str(t_row.get('Entry_Date', t_row.get('Date', ''))),
                                        precio_entrada=float(t_row.get('Entry_Price', 0) or 0),
                                        precio_salida=float(t_row.get('Exit_Price', 0) or 0),
                                        pnl_absoluto=float(t_row.get('PnL', 0) or 0),
                                        retorno_pct=float(t_row.get('Return [%]', 0) or 0)
                                    )
                                    db.session.add(nuevo_trade)

                        db.session.commit()
                        logger.info(f"✅ SQL: Guardado exitoso en base de datos para {user_mode}")

                except Exception as e:
                    db.session.rollback()
                    logger.error(f"❌ Error SQL Crítico: {e}")
            
        except Exception as e:
            logger.error(f"Error al guardar ficheros: {e}")
            
        # ----------------------------------------------------------------------
        # 🎯 PUNTO 10: ENVÍO DE EMAIL AUTOMÁTICO
        # ----------------------------------------------------------------------

        # 1. Verificamos si el usuario ha activado el switch en la web
        if getattr(System, 'enviar_mail', False):
            asunto = f"📊 Resultados Backtest: {user_mode} - {datetime.now().strftime('%Y-%m-%d')}"
            cuerpo = (
                f"Hola {user_mode},\n\n"
                f"La ejecución de la estrategia ha finalizado correctamente.\n"
                f"Se adjunta el fichero de resultados con el detalle de las operaciones."
            )
            
            destinatario = System.destinatario_email
            adjunto = str(parametros_generales_y_rutas.get('fichero_resultados')) 

            logger.info(f"📬 Intentando enviar reporte a: {destinatario}")

            try:
                # 💡 PASO CLAVE: Inyectamos 'config_path'
                send_email(
                    subject=asunto,
                    body=cuerpo,
                    to_email=destinatario,
                    attachment_path=adjunto,
                    config_path=fichero_mail_setup  # <--- Usamos la ruta calculada por el orquestador
                )
                logger.info(f"✅ Email enviado correctamente a {destinatario}")
            except Exception as e:
                logger.error(f"❌ Error crítico en el envío de correo: {e}")
        else:
            logger.info("ℹ️ Envío de email saltado (desactivado por el usuario).")
    
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