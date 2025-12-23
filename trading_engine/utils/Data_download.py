# trading_engine/utils/Data_download.py

"""
Descripción : Contiene funciones generales diseñadas para la descarga y gestión de datos 
históricos (OHLCV) y datos fundamentales.

Esta versión utiliza un rango de fechas fijo (start_date, end_date) y una gestión de caché 
simplificada para los datos OHLCV, guardando la totalidad de la historia solicitada.
"""

import os
import re
import pandas as pd
from datetime import datetime
import time 
from pathlib import Path 
import logging

import yfinance as yf
import numpy as np

# Se asume que las librerías de AlphaVantage están instaladas
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData

# Se necesita la constante para las columnas del histórico para la carga
try:
    from trading_engine.core.constants import COLUMNAS_OHLCV 
except ImportError:
    # Definición de fallback si la constante no existe
    COLUMNAS_OHLCV = ["Open", "High", "Low", "Close", "Volume", "Adj Close"] 

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------
# --- DESCARGA DE DATOS OHLCV (YAHOO FINANCE) - MODIFICADA ---
# --------------------------------------------------------------------------------

def descargar_datos_YF(
    simbolos_df: pd.DataFrame, 
    start_date: str,
    end_date: str,
    intervalo: str, 
    data_files_path: Path
) -> pd.DataFrame:
    
    """
    Función : descargar_datos_YF

    Descripción : Descarga los datos históricos de cotización (OHLCV) obteniendo
    siempre el historial completo ('period=max') si la caché no está actualizada
    (no es del día de hoy). Luego recorta el rango de datos solicitado.

    Resumen de la Nueva Lógica
        La función ahora busca un archivo llamado ZTS_1d_MAX.csv.

        Si lo encuentra, comprueba su fecha de última modificación. Si la modificación no es la de hoy, se considera obsoleto
     y se fuerza una nueva descarga.

        Si se fuerza la descarga, se usa period='max' para obtener todo el historial disponible.

        El historial completo se guarda sobrescribiendo el archivo MAX.

        Finalmente, se carga o se usa el DataFrame completo (data_to_use) y se filtra con .loc[start_dt:end_dt] para devolver 
    al backtester solo el rango solicitado.

    Parámetros:
    - simbolos_df: DataFrame, con la columna 'Symbol'.
    - start_date: str, fecha de inicio del backtest (ej. '2020-01-01').
    - end_date: str, fecha de fin del backtest (ej. '2023-12-31').
    - intervalo: str, intervalo de los datos (ej. '1d').
    - data_files_path: Path, la ruta al directorio de caché para los datos OHLCV.

    Salida: Devuelve un dataframe consolidado con los datos de todos los valores.
    """
    data_dir = Path(data_files_path)
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Usando directorio de caché OHLCV: {data_dir}")

    all_data = pd.DataFrame()
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 🎯 FECHA CLAVE: Hoy, sin tiempo, para comparación de frescura.
    today_date_str = datetime.now().strftime("%Y-%m-%d")

    for index, row in simbolos_df.iterrows():
        symbol = row["Symbol"]
        
        # 🎯 CAMBIO CLAVE 1: Nombre de archivo MAX
        csv_file_name_max = f"{symbol}_{intervalo}_MAX.csv"
        csv_file_path_max = data_dir / csv_file_name_max

        logger.info(f"--- Verificando caché para {symbol} ---")

        data_to_use = pd.DataFrame()
        needs_download = True
        
        # 1. Verificar si el archivo MAX existe y si está fresco (fecha de modificación = hoy)
        if csv_file_path_max.exists():
            mod_timestamp = os.path.getmtime(csv_file_path_max)
            mod_date_str = datetime.fromtimestamp(mod_timestamp).strftime("%Y-%m-%d")
            
            if mod_date_str == today_date_str:
                logger.info(f"1. Caché MAX encontrada y está **fresca** (Modificación: {mod_date_str}).")
                needs_download = False
                
                try:
                    data_to_use = pd.read_csv(csv_file_path_max, index_col='Date', parse_dates=True)
                    data_to_use.index = pd.to_datetime(data_to_use.index)
                    if data_to_use.empty:
                        logger.warning(f"La caché MAX de {symbol} está vacía. Forzando descarga.")
                        needs_download = True
                except Exception as e:
                    logger.error(f"Error al leer la caché MAX ({csv_file_name_max}): {e}. Forzando descarga.")
                    needs_download = True
            else:
                # El archivo existe pero no es de hoy
                logger.info(f"1. Caché MAX encontrada, pero está **obsoleta** (Modificación: {mod_date_str}).")
                needs_download = True
        else:
            logger.info(f"1. Archivo de caché MAX no encontrado: {csv_file_name_max}.")
            needs_download = True

        # 2. Si se necesita descargar (Caché no existe o está obsoleta)
        if needs_download:
            # --- Limpieza de archivos obsoletos (Opcional, solo si el formato viejo persistiera) ---
            # Si se usaba el formato [HOY]_1d_SYMBOL.csv, esta limpieza no es estrictamente
            # necesaria si usamos el formato MAX, pero la mantengo para borrar el formato antiguo
            # y solo si falló la carga. Si solo usamos MAX, esta sección se simplifica mucho.
            # La voy a quitar para forzar el flujo MAX y simplificar.
            
            # --- Descarga y Sobrescritura ---
            # 🎯 CAMBIO CLAVE 2: Usar period='max' para obtener el historial completo
            logger.info(f"2. Descargando historial COMPLETO (period='max') para {symbol}...")
            try:
                data = yf.download(
                    symbol,
                    period='max',  # <--- DESCARGA EL HISTORIAL COMPLETO
                    interval=intervalo,
                    multi_level_index=False,
                    rounding=4,
                )

                if data.empty:
                    logger.warning(f"Advertencia: No se encontraron datos para {symbol}.")
                    continue

                data.index.name = 'Date'
                data["Symbol"] = symbol
                
                # Guardar datos en un CSV (Sobrescribe o crea el archivo MAX)
                data.to_csv(csv_file_path_max)
                logger.info(f"3. Descarga COMPLETA guardada/actualizada en {csv_file_path_max}")
                data_to_use = data

            except Exception as e:
                logger.error(f"Error al descargar datos para {symbol}: {e}")
                continue
        
        # 4. Recorte Final y Consolidación (Esto es ahora el FILTRADO sobre el Caché MAX)
        if not data_to_use.empty:
            # Seleccionar solo el rango solicitado (start_dt inclusive, end_dt inclusive)
            final_data = data_to_use.loc[start_dt:end_dt].copy()
            
            if final_data.empty:
                logger.warning(f"Advertencia: No hay datos en el rango [{start_date} - {end_date}] después del recorte. Saltando {symbol}.")
                continue
            
            # Asegurar que solo se incluyan las columnas estándar antes de consolidar
            try:
                final_data = final_data[final_data.columns.intersection(COLUMNAS_OHLCV + ["Symbol"])]
            except Exception as e:
                 logger.warning(f"Fallo al filtrar columnas estándar para {symbol}: {e}")

            all_data = pd.concat([all_data, final_data], axis=0)

    logger.info("Descarga y gestión de caché OHLCV completada.")
    return all_data

# --------------------------------------------------------------------------------
# --- ORQUESTACIÓN FUNDAMENTAL (SOLO ALPHAVANTAGE) ---
# --------------------------------------------------------------------------------

def manage_fundamental_data(
    simbolos_df: pd.DataFrame, 
    api_key_av: str,
    fundamentals_path: Path
) -> pd.DataFrame:
    """
    Función : manage_fundamental_data

    Orquesta la gestión completa de los datos fundamentales. Ahora solo utiliza
    Alpha Vantage para la construcción del histórico trimestral completo.

    Implementa una lógica de FALLBACK: si la descarga de AV falla por límite de
    tasa, carga el último archivo trimestral existente en caché.
    """
    
    logger.info("======================================================")
    logger.info("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES INICIADA  ===")
    logger.info("=======================================================")

    if not isinstance(simbolos_df, pd.DataFrame) or "Symbol" not in simbolos_df.columns:
        logger.error("Error: El primer argumento debe ser un DataFrame de pandas con la columna 'Symbol'. Terminando la gestión.")
        return pd.DataFrame()
        
    symbols = simbolos_df["Symbol"].tolist()

    folder_path = Path(fundamentals_path)
    folder_path.mkdir(parents=True, exist_ok=True) 

    # --- FASE 1: CONSTRUCCIÓN Y MANTENIMIENTO (AlphaV) ---
    logger.info("[FASE 1: CONSTRUCCIÓN Y MANTENIMIENTO (AlphaV)]")
    
    current_quarter = (datetime.now().month - 1) // 3 + 1
    
    # --- 1. Determinar si se necesita descarga ---
    needs_download = False
    for symbol in symbols:
        required_file = fundamentals_path / f"Q{current_quarter}_{symbol}.csv"
        # Si el archivo del trimestre actual NO existe, necesitamos descargar.
        if not required_file.exists():
            needs_download = True
            logger.info(f"-> Símbolo {symbol} requiere DESCARGA: Falta el reporte Q{current_quarter}.")
            break 
    
    df_consolidated = pd.DataFrame()
    av_failed = False # Flag para rastrear el fallo de AV

    # --- 2. Ejecutar Descarga si es Necesario ---
    if needs_download:
        logger.info(f"-> Ejecutando download_fundamentals_AlphaV para construir/actualizar el histórico...")
        # Llama a la función que intentará descargar el historial completo de AV
        df_consolidated = download_fundamentals_AlphaV(api_key_av, simbolos_df, folder_path)
        
        # Comprobar si AV falló completamente (devuelve DataFrame vacío)
        if df_consolidated.empty and not simbolos_df.empty: # Si la lista de símbolos no estaba vacía, pero el resultado sí
            av_failed = True
            logger.warning("¡ADVERTENCIA! La descarga de Alpha Vantage falló (posiblemente por límite de tasa) y devolvió un DataFrame vacío.")
    
    # --- 3. Lógica de Carga/Fallback ---
    # Se ejecuta si: a) No se necesitaba descargar (needs_download=False), O
    #               b) Se necesitaba descargar pero falló (av_failed=True).
    if not needs_download or av_failed:
        
        if not needs_download:
            logger.info("-> Cargando archivos del trimestre actual (Caché Fresca).")
        else: # av_failed es True
            logger.warning("-> Activando lógica de FALLBACK: Buscando el último reporte trimestral existente en caché.")
            
        all_data_list = []
        for symbol in symbols:
            
            # Buscamos todos los archivos QX_SYMBOL.csv y Q0_SYMBOL.csv (fallo)
            existing_files = list(fundamentals_path.glob(f"Q?_{symbol}.csv"))
            
            if not existing_files:
                logger.warning(f"No se encontró ninguna caché para {symbol}. Se saltará este símbolo.")
                continue
                
            # Seleccionamos el archivo con el número de trimestre más alto (Q4 > Q3, pero Q0 es el menor)
            # max() ordenará alfabéticamente/numéricamente.
            best_file_path = max(existing_files) 
            
            # Si estamos en modo fallo y el mejor archivo es solo el marcador Q0, lo saltamos.
            if av_failed and 'Q0' in best_file_path.name:
                logger.warning(f"Solo se encontró el marcador de fallo '{best_file_path.name}'. Saltando {symbol}.")
                continue

            logger.info(f"Cargando {best_file_path.name} para {symbol}.")
            try:
                 data = pd.read_csv(best_file_path, sep=";")
                 data['fiscalDateEnding'] = pd.to_datetime(data['fiscalDateEnding'], errors='coerce')
                 data.set_index('fiscalDateEnding', inplace=True)
                 all_data_list.append(data)
            except Exception as e:
                logger.error(f"Error al cargar caché {best_file_path.name} para {symbol}: {e}")
                
        if all_data_list:
            df_consolidated = pd.concat(all_data_list, axis=0)
            df_consolidated = df_consolidated.loc[:, ~df_consolidated.columns.duplicated()] 
            df_consolidated = df_consolidated.sort_index()
        # Si all_data_list está vacío, df_consolidated sigue siendo el DataFrame vacío inicial o se sobrescribe aquí.
        
    # --- 4. Finalización ---
   
    logger.info("========================================================")
    logger.info("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES FINALIZADA  ===")
    logger.info("========================================================")
    
    return df_consolidated

def download_fundamentals_AlphaV(
    api_key: str, 
    simbolos_df: pd.DataFrame, 
    fundamentals_path: Path # Se recibe por parámetro
):
    """
    Realiza la descarga de los datos fundamentales trimestrales (Alpha Vantage).
    Incluye un retardo de 3 segundos para cumplir con el límite de 1 request per second
    del plan gratuito y lógica de limpieza trimestral de caché.
    """
    
    # fd = FundamentalData(key=api_key, output_format="pandas") # Se moverá dentro del loop
    current_month = datetime.now().month
    current_quarter = (current_month - 1) // 3 + 1
    folder_path = Path(fundamentals_path)
    folder_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Directorio de caché fundamental: '{folder_path}'") 
    all_data_list = [] 
    symbols = simbolos_df["Symbol"].tolist()

    # Inicializar la clase FundamentalData una vez
    try:
        fd = FundamentalData(key=api_key, output_format="pandas")
    except Exception as e:
        logger.error(f"Error al inicializar Alpha Vantage FundamentalData: {e}")
        return pd.DataFrame() 

    for symbol in symbols:
        file_name = f"Q{current_quarter}_{symbol}.csv"
        file_path = folder_path / file_name 
        data = pd.DataFrame()

        # 1. Búsqueda y Manejo de la caché existente para el trimestre actual
        if file_path.is_file(): 
            logger.info(f"Datos Q{current_quarter} ya guardados en {file_path}. Cargando datos locales...")
            try:
                data = pd.read_csv(file_path, sep=";", parse_dates=['fiscalDateEnding'])
            except Exception as e:
                logger.error(f"Error al cargar el archivo local {file_path}: {e}. Intentando descargar de nuevo.")

        # 2. Descarga si la caché falla o no existe
        if data.empty:
            logger.info(f"Descargando datos de {symbol} de Alpha Vantage...")
            try:
                # Descarga de los 4 tipos de datos fundamentales
                # NOTA: Cada una de estas es una petición, por lo que se consumen 4 peticiones por símbolo.
                balance_sheet, _ = fd.get_balance_sheet_quarterly(symbol)
                income_statement, _ = fd.get_income_statement_quarterly(symbol)
                cash_flow, _ = fd.get_cash_flow_quarterly(symbol)
                earnings, _ = fd.get_earnings_quarterly(symbol)

                # Procesamiento y Merge de DataFrames
                data = pd.merge(balance_sheet, income_statement, on="fiscalDateEnding", how="outer")
                data = pd.merge(data, cash_flow, on="fiscalDateEnding", how="outer")
                data = pd.merge(data, earnings, on="fiscalDateEnding", how="outer")
                data["Symbol"] = symbol
                
                # Filtrado de columnas y renombrado
                columnas_necesarias = [
                    "fiscalDateEnding", "Symbol", "totalRevenue", "ebit", "operatingCashflow",
                    "capitalExpenditures", "netIncome_x", "totalShareholderEquity", 
                    "totalLiabilities", "goodwill", "netIncome_y", "reportedEPS"
                ]
                data = data[data.columns.intersection(columnas_necesarias)]
                
                nuevos_nombres = {"netIncome_y": "Net Income", "reportedEPS": "Diluted EPS"}
                data = data.rename(columns=nuevos_nombres)
                data['fiscalDateEnding'] = pd.to_datetime(data['fiscalDateEnding'])

                # 3. Guardado y Limpieza de Versiones Antiguas
                data.to_csv(file_path, index=False, sep=";")
                logger.info(f"Datos Q{current_quarter} guardados en {file_path}. **Buscando y borrando versiones anteriores.**")
                
                # Limpieza de cachés de trimestres anteriores (Qx-1)
                pattern = f"Q?_{symbol}.csv"
                for file_path_obj in folder_path.glob(pattern):
                    if file_path_obj.name != file_name:
                        try:
                            os.remove(file_path_obj)
                            logger.info(f"Archivo de caché obsoleto fundamental eliminado: {file_path_obj.name}")
                        except Exception as e:
                            logger.warning(f"No se pudo eliminar el archivo obsoleto {file_path_obj.name}: {e}")
                
            except Exception as e:
                logger.error(f"Error al descargar datos de AV para {symbol}: {e}.")
                # Manejo de fallo de descarga
                fail_file_name = f"Q0_{symbol}.csv" 
                fail_file_path = folder_path / fail_file_name 
                
                empty_data = pd.DataFrame({"fiscalDateEnding": [pd.NaT], "Symbol": [symbol], "totalRevenue": [np.nan]})
                empty_data.to_csv(fail_file_path, index=False, sep=";")
                logger.warning(f"Marcador de fallo '{fail_file_name}' creado para {symbol}.")

                # 🎯 CAMBIO CLAVE: Aumentar el retardo para cumplir con 1 request per second
                time.sleep(3) 
                continue 

        if not data.empty:
            all_data_list.append(data)
            
        # 🎯 CAMBIO CLAVE: Aumentar el retardo para cumplir con 1 request per second
        time.sleep(3) 

    if all_data_list:
        all_data = pd.concat(all_data_list, axis=0)
        all_data['fiscalDateEnding'] = pd.to_datetime(all_data['fiscalDateEnding'], errors='coerce')
        all_data.dropna(subset=['fiscalDateEnding'], inplace=True)
        all_data.set_index("fiscalDateEnding", inplace=True)
        # Aseguramos que solo exista un reporte por fecha/símbolo, tomando el primero (más probable de AV)
        all_data = all_data.drop_duplicates(subset=all_data.columns.drop(['Symbol']), keep='first')
        return all_data
    else:
        return pd.DataFrame()