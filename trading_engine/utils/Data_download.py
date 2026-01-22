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

# Importar motor de base de datos para posibles usos futuros
from trading_engine.core.database_pg import engine_pg

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
    Función : manage_fundamental_data (Versión Optimizada)

    Orquesta la gestión de fundamentales con lógica de "Último Disponible":
    1. Busca cualquier archivo Q?_SYMBOL.csv existente.
    2. Si el archivo del trimestre actual no existe, intenta descargar/actualizar.
    3. Si la descarga falla (sin crédito), mantiene y usa el archivo del trimestre anterior.
    4. Progresivamente actualiza la caché conforme hay éxito en las descargas.
    """
    
    logger.info("======================================================")
    logger.info("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES INICIADA  ===")
    logger.info("=======================================================")

    if not isinstance(simbolos_df, pd.DataFrame) or "Symbol" not in simbolos_df.columns:
        logger.error("Error: El DataFrame de símbolos es inválido.")
        return pd.DataFrame()
        
    symbols = simbolos_df["Symbol"].tolist()
    folder_path = Path(fundamentals_path)
    folder_path.mkdir(parents=True, exist_ok=True) 

    # Determinamos el trimestre "ideal" para hoy
    current_quarter = (datetime.now().month - 1) // 3 + 1
    
    # --- FASE 1: DETERMINAR NECESIDAD DE ACTUALIZACIÓN ---
    # Revisamos si todos los símbolos tienen ya el archivo del trimestre actual
    symbols_to_update = []
    for symbol in symbols:
        # Buscamos específicamente el archivo del trimestre actual
        target_file = folder_path / f"Q{current_quarter}_{symbol}.csv"
        
        if not target_file.exists():
            symbols_to_update.append(symbol)
    
    needs_download = len(symbols_to_update) > 0
    df_consolidated = pd.DataFrame()
    av_failed = False

    # --- FASE 2: EJECUTAR ACTUALIZACIÓN (Si falta algún Q actual) ---
    if needs_download:
        logger.info(f"-> Se detectaron {len(symbols_to_update)} símbolos que podrían actualizarse a Q{current_quarter}.")
        # Llamamos a la descarga (la función de descarga ya gestionará el fallback internamente)
        df_consolidated = download_fundamentals_AlphaV(api_key_av, simbolos_df, folder_path)
        
        if df_consolidated.empty and not simbolos_df.empty:
            av_failed = True
            logger.warning("-> La descarga de AV no devolvió datos nuevos. Activando Fallback sobre caché existente.")

    # --- FASE 3: CONSOLIDACIÓN FINAL (Carga de lo que haya en disco) ---
    # Si no hubo descarga o la descarga falló, recolectamos lo mejor que tengamos en disco
    if not needs_download or av_failed:
        logger.info("-> Consolidando datos desde la mejor caché disponible (Q actual o anteriores).")
        all_data_list = []
        
        for symbol in symbols:
            # Buscamos todos los archivos QX_SYMBOL.csv (Q1, Q2, Q3, Q4 y el especial Q0)
            existing_files = list(folder_path.glob(f"Q?_{symbol}.csv"))
            
            if not existing_files:
                logger.warning(f"No se encontró NINGUNA caché (ni antigua ni nueva) para {symbol}.")
                continue
                
            # Seleccionamos el mejor archivo disponible (el nombre más alto: Q4 > Q1, etc.)
            # Nota: Al ser cambio de año, Q4 de 2025 es "alfabéticamente" mayor que Q1 de 2026.
            best_file_path = max(existing_files) 
            
            # Evitamos cargar marcadores de fallo Q0 si hay otras opciones
            if 'Q0' in best_file_path.name and len(existing_files) > 1:
                existing_files = [f for f in existing_files if 'Q0' not in f.name]
                best_file_path = max(existing_files)

            try:
                data = pd.read_csv(best_file_path, sep=";")
                data['fiscalDateEnding'] = pd.to_datetime(data['fiscalDateEnding'], errors='coerce')
                data.set_index('fiscalDateEnding', inplace=True)
                all_data_list.append(data)
                logger.info(f"Cargado para backtest: {best_file_path.name} (Último disponible)")
            except Exception as e:
                logger.error(f"Error al cargar {best_file_path.name}: {e}")
                
        if all_data_list:
            df_consolidated = pd.concat(all_data_list, axis=0)
            df_consolidated = df_consolidated.loc[:, ~df_consolidated.columns.duplicated()] 
            df_consolidated = df_consolidated.sort_index()

    logger.info("========================================================")
    logger.info("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES FINALIZADA  ===")
    logger.info("========================================================")
    
    return df_consolidated

def download_fundamentals_AlphaV(
    api_key: str, 
    simbolos_df: pd.DataFrame, 
    fundamentals_path: Path
):
    """
    Descarga datos de Alpha Vantage gestionando la caché de forma inteligente.
    Mantiene un solo archivo 'Q' por símbolo y usa el anterior si la API falla.
    """
    import time
    from datetime import datetime

    current_month = datetime.now().month
    current_quarter = (current_month - 1) // 3 + 1
    folder_path = Path(fundamentals_path)
    folder_path.mkdir(parents=True, exist_ok=True)
    
    all_data_list = [] 
    symbols = simbolos_df["Symbol"].tolist()

    try:
        # Inicialización de la API
        from alpha_vantage.fundamentaldata import FundamentalData
        fd = FundamentalData(key=api_key, output_format="pandas")
    except Exception as e:
        logger.error(f"Error al inicializar Alpha Vantage: {e}")
        return pd.DataFrame() 

    for symbol in symbols:
        # --- PASO 1: BÚSQUEDA ELÁSTICA EN CACHÉ ---
        # Buscamos cualquier archivo que empiece por Q (Q1, Q2, Q3, Q4 o Q0)
        archivos_encontrados = list(folder_path.glob(f"Q?_{symbol}.csv"))
        
        # Seleccionamos el que tenga el nombre "mayor" (ej: Q4 > Q1 alfabéticamente)
        file_path_latest = max(archivos_encontrados) if archivos_encontrados else None
        
        data = pd.DataFrame()
        needs_download = True

        # --- PASO 2: CARGA DEL PLAN B (Fallback) ---
        if file_path_latest:
            try:
                data = pd.read_csv(file_path_latest, sep=";", parse_dates=['fiscalDateEnding'])
                logger.info(f"Cargada caché previa para {symbol}: {file_path_latest.name}")
                
                # Si el archivo ya es del trimestre actual, no hace falta descargar
                if f"Q{current_quarter}" in file_path_latest.name:
                    logger.info(f"Caché de {symbol} al día (Q{current_quarter}). Saltando descarga.")
                    needs_download = False
            except Exception as e:
                logger.error(f"Error leyendo caché {file_path_latest.name}: {e}")
                data = pd.DataFrame() # Si falla, intentaremos descargar de cero

        # --- PASO 3: INTENTO DE DESCARGA ---
        if needs_download:
            logger.info(f"Intentando actualizar {symbol} al Q{current_quarter} via API...")
            try:
                # Descargas (mantenemos las 4 peticiones originales por ahora)
                balance_sheet, _ = fd.get_balance_sheet_quarterly(symbol)
                time.sleep(0.5) 
                income_statement, _ = fd.get_income_statement_quarterly(symbol)
                time.sleep(0.5)
                cash_flow, _ = fd.get_cash_flow_quarterly(symbol)
                time.sleep(0.5)
                earnings, _ = fd.get_earnings_quarterly(symbol)

                # Unión de datos
                new_data = pd.merge(balance_sheet, income_statement, on="fiscalDateEnding", how="outer")
                new_data = pd.merge(new_data, cash_flow, on="fiscalDateEnding", how="outer")
                new_data = pd.merge(new_data, earnings, on="fiscalDateEnding", how="outer")
                new_data["Symbol"] = symbol
                
                # Selección de columnas (tus columnas actuales)
                columnas_necesarias = [
                    "fiscalDateEnding", "Symbol", "totalRevenue", "ebit", "operatingCashflow",
                    "capitalExpenditures", "netIncome_x", "totalShareholderEquity", 
                    "totalLiabilities", "goodwill", "netIncome_y", "reportedEPS"
                ]
                new_data = new_data[new_data.columns.intersection(columnas_necesarias)]
                new_data = new_data.rename(columns={"netIncome_y": "Net Income", "reportedEPS": "Diluted EPS"})
                
                # --- PASO 4: GUARDADO NUEVO Y LIMPIEZA DEL VIEJO ---
                new_file_name = f"Q{current_quarter}_{symbol}.csv"
                new_file_path = folder_path / new_file_name
                
                new_data.to_csv(new_file_path, index=False, sep=";")
                logger.info(f"Archivo {new_file_name} guardado correctamente.")
                
                # Si la descarga funcionó, el "plan B" ya no hace falta
                # Borramos cualquier archivo Q antiguo que no sea el que acabamos de crear
                for old_file in archivos_encontrados:
                    if old_file != new_file_path and old_file.exists():
                        old_file.unlink() # Borra el archivo
                        logger.info(f"Eliminada caché antigua: {old_file.name}")
                
                # Actualizamos la variable data con los nuevos datos frescos
                data = new_data

            except Exception as e:
                # SI FALLA LA API: No borramos nada.
                if not data.empty:
                    logger.warning(f"API Falló para {symbol}. Usando caché {file_path_latest.name}. Motivo: {e}")
                else:
                    # Si no había ni caché ni API, creamos marcador Q0
                    logger.error(f"Sin caché ni API para {symbol}. Creando marcador Q0.")
                    q0_path = folder_path / f"Q0_{symbol}.csv"
                    pd.DataFrame({"fiscalDateEnding": [pd.NaT], "Symbol": [symbol]}).to_csv(q0_path, index=False, sep=";")

            # Delay para respetar el Rate Limit (ajusta según tu plan de AV)
            time.sleep(12) 

        # Añadir al listado final (venga de caché o de API)
        if not data.empty:
            all_data_list.append(data)

    # Consolidación final del DataFrame para el programa
    if all_data_list:
        df_final = pd.concat(all_data_list, axis=0)
        df_final['fiscalDateEnding'] = pd.to_datetime(df_final['fiscalDateEnding'], errors='coerce')
        df_final.dropna(subset=['fiscalDateEnding'], inplace=True)
        return df_final
    
    return pd.DataFrame()

def guardar_en_postgres(df, tabla_nombre):
    """
    Toma cualquier DataFrame (OHLCV o Fundamentales) y lo guarda 
    en PostgreSQL usando una política de 'Append' o 'Replace'.
    """
    if df is None or df.empty:
        logger.warning(f"No hay datos para guardar en la tabla {tabla_nombre}.")
        return

    # Limpieza de nombres de columnas para Postgres (minúsculas y sin espacios)
    df_copy = df.copy()
    if isinstance(df_copy.index, pd.DatetimeIndex):
        df_copy.reset_index(inplace=True)
        
    df_copy.columns = [c.replace(' ', '_').lower() for c in df_copy.columns]

    try:
        # Usamos method='multi' para que la inserción sea mucho más rápida
        df_copy.to_sql(tabla_nombre, con=engine_pg, if_exists='append', index=False, method='multi')
        logger.info(f"✅ Se han guardado {len(df_copy)} registros en la tabla '{tabla_nombre}' de PostgreSQL.")
    except Exception as e:
        logger.error(f"❌ Error al inyectar datos en Postgres: {e}")