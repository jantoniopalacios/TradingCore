"""
Fichero : Data_download.py

Descripción : El fichero Data_download.py contiene funciones generales diseñadas para la descarga y gestión de datos históricos 
de cotizaciones (OHLCV) y datos fundamentales. Utiliza las librerías yfinance y AlphaVantage.

Todos los datos descargados se almacenan en directorios de caché definidos estáticamente a través de System.DATA_FILES_PATH 
y System.FUNDAMENTALS_PATH (rutas de caché).


"""

import os
import glob # Se mantiene, aunque se prefiere Pathlib.glob
import re
import pandas as pd
from datetime import datetime
import time  # Para manejar límites de tasa
from pathlib import Path  # 🎯 IMPORTACIÓN CLAVE: Para manejo de rutas
import logging

import yfinance as yf

import numpy as np

from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData

# Acceder a la configuración de rutas estáticas
try:
    from estrategia_system import System
except ImportError:
    class System:
        DATA_FILES_PATH = Path("./Data files")
        FUNDAMENTALS_PATH = Path("./Data files/Fundamentals")
    logging.warning("No se pudo importar 'System'. Usando rutas de fallback.")


def descargar_datos_YF(simbolos_df, periodo, intervalo):
    """
    Función : descargar_datos_YF

    Descripción : Descarga los datos históricos de cotización (OHLCV) para una lista de símbolos. Implementa una lógica 
    de caché que verifica si los datos ya están actualizados para el día actual y elimina archivos antiguos para mantener 
    la carpeta limpia.

    Parámetros:
    - simbolos_df: DataFrame, con la columna 'Symbol'.
    - periodo : periodo de datos a descargar.
    - intervalo: str, intervalo de los datos.

    Salida: Devuelve un dataframe con los datos de todos los valores con los campos OHLCV
    y un campo Symbol

    """

    # Usar la ruta estática configurada
    data_dir = System.DATA_FILES_PATH
    
    # Asegurar que el directorio de caché exista
    # Los argumentos parents=True y exist_ok=True evitan errores si ya existe o si necesita crear carpetas intermedias.
    data_dir.mkdir(parents=True, exist_ok=True)

    # Crear un DataFrame para almacenar todos los datos
    all_data = pd.DataFrame()

    # Lógica para limitar el periodo a 5 años (Mantenida)
    if periodo.endswith(('y', 'Y')):
        years = int(periodo.removesuffix('y').removesuffix('Y'))
        if years > 5:
            print(f"Advertencia: El periodo de {years} años es demasiado largo. Limitando a 5 años.")
            periodo = '5y'
    elif periodo.endswith(('mo', 'MO')):
        months = int(periodo.removesuffix('mo').removesuffix('MO'))
        if months > 60:
            print(f"Advertencia: El periodo de {months} meses es demasiado largo. Limitando a 60 meses (5 años).")
            periodo = '5y'

    # Descargar datos para cada símbolo
    for index, row in simbolos_df.iterrows():
        symbol = row["Symbol"]

        print(f"Verificando datos OHLCV existentes para {symbol}...")

        # Verificar si existe un archivo con datos del símbolo y la fecha de hoy
        today = datetime.now().strftime("%Y-%m-%d")
        scope = periodo + intervalo

        # 🎯 USO DE PATHLIB: Construcción de la ruta del archivo
        csv_file_path = data_dir / f"{today}_{scope}_{symbol}.csv"

        # Verificar si el archivo existe
        file_exists = csv_file_path.exists()

        if file_exists:
            print(
                f"Los datos para {symbol} ya están actualizados para hoy en el archivo {csv_file_path}. No se descargarán nuevamente."
            )

            existing_data = pd.read_csv(csv_file_path, index_col='Date', parse_dates=True)

            # Concatenar los datos existentes al DataFrame global
            all_data = pd.concat([all_data, existing_data], axis=0)

            continue
        else:
            print(f"No se encontró un archivo {csv_file_path}.")

            # Recorrer todos los archivos CSV en la carpeta para eliminar datos antiguos
            # 🎯 USO DE PATHLIB.GLOB: Reemplaza glob.glob(os.path.join(data_dir, "*.csv"))
            for file_path_obj in data_dir.glob("*.csv"):
                # Intentar extraer la fecha del nombre del archivo (formato YYYY-MM-DD)
                match = re.search(r"\d{4}-\d{2}-\d{2}", file_path_obj.name)

                if match:
                    file_date = match.group()

                    # Si la fecha del archivo NO es la de hoy, eliminar el archivo
                    if file_date != today:
                        os.remove(file_path_obj)
                        print(f"Archivo eliminado: {file_path_obj.name}")
                else:
                    print(
                        f"Advertencia: No se encontró fecha en el nombre del archivo {file_path_obj.name}. No se elimina."
                    )

        print(f"Descargando datos para {symbol} desde Yahoo Finance...")

        try:
            # Descargar datos con yfinance
            data = yf.download(
                symbol,
                period=periodo,
                interval=intervalo,
                multi_level_index=False,
                rounding=4,
            )

            if data.empty:
                print(f"Advertencia: No se encontraron datos para {symbol}.")
                continue

            # Estandarizar el índice a 'Date'
            data.index.name = 'Date'

            data["Symbol"] = symbol

            # Guardar datos en un CSV
            data.to_csv(csv_file_path) # Funciona con Path
            print(f"Datos guardados en {csv_file_path}")

            # Concatenar al DataFrame global
            all_data = pd.concat([all_data, data], axis=0)

        except Exception as e:
            print(f"Error al descargar datos para {symbol}: {e}")

    return all_data

# --------------------------------------------------------------------------------
# --- ORQUESTACIÓN Y MANTENIMIENTO FUNDAMENTAL ---
# --------------------------------------------------------------------------------

def manage_fundamental_data(simbolos_df: pd.DataFrame, api_key_av: str) -> pd.DataFrame: # ❌ Sin parámetro de ruta
    """
    Función : manage_fundamental_data

    Orquesta la gestión completa de los datos fundamentales. Consta de dos fases principales: Construcción Inicial (AlphaV) 
    para obtener el histórico profundo si falta y Mantenimiento Inteligente (yfinance) para la actualización.
    
    Utiliza System.FUNDAMENTALS_PATH para la cache.
    """
    
    print("\n=======================================================")
    print("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES INICIADA  ===")
    print("=======================================================")

    # 1. Validación de la Entrada (Mantenida)
    if not isinstance(simbolos_df, pd.DataFrame) or "Symbol" not in simbolos_df.columns:
        print("Error: El primer argumento debe ser un DataFrame de pandas con la columna 'Symbol'. Terminando la gestión.")
        return pd.DataFrame()
        
    symbols = simbolos_df["Symbol"].tolist()

    # Usar la ruta estática para Fundamentales
    folder_path = System.FUNDAMENTALS_PATH
    folder_path.mkdir(parents=True, exist_ok=True) # Crear si no existe (aunque ya lo hace configuracion.py)

    # --- 3. Fase de CONSTRUCCIÓN (AlphaV): Crea el histórico PROFUNDO si falta ---
    print("\n[FASE 1: CONSTRUCCIÓN INICIAL (AlphaV)]")
    
    needs_initial_download = False
    
    for symbol in symbols:
        # Busca CUALQUIER archivo Q{X}_{symbol}.csv existente
        # 🎯 USO DE PATHLIB.GLOB: Reemplaza os.listdir y filtros
        existing_files = [f for f in folder_path.glob(f"Q*_{symbol}.csv")]
        
        if not existing_files:
            needs_initial_download = True
            print(f"-> Símbolo {symbol} requiere DESCARGA INICIAL. No se encontró ningún archivo de histórico.")
            break # Si falta uno, asumimos que debemos ejecutar AV para todos

    if needs_initial_download:
        # LLAMADA SIN ARGUMENTO DE RUTA
        print(f"-> Ejecutando download_fundamentals_AlphaV para construir el histórico...")
        # Nota: La función download_fundamentals_AlphaV se encargará de guardar los archivos.
        download_fundamentals_AlphaV(api_key_av, simbolos_df) 
    else:
        print("-> Todos los símbolos tienen archivos base. Saltando la descarga inicial de AlphaV.")

    # --- 4. Fase de MANTENIMIENTO (yfinance): Actualización inteligente ---
    print("\n[FASE 2: MANTENIMIENTO INTELIGENTE (yfinance)]")
    
    # LLAMADA SIN ARGUMENTO DE RUTA
    # Nota: Esta función lee y actualiza los archivos, y retorna el consolidado final.
    df_consolidated = update_fundamentals_YF_overwrite(simbolos_df) 
    
    print("\n=======================================================")
    print("===  ORQUESTACIÓN DE DATOS FUNDAMENTALES FINALIZADA  ===")
    print("=======================================================")
    
    return df_consolidated


def download_fundamentals_AlphaV(api_key, simbolos_df: pd.DataFrame): # ❌ Sin parámetro de ruta

    """
    Función : download_fundamentals_AlphaV

    Realiza la descarga inicial de los datos fundamentales trimestrales (hoja de balance, estado de resultados, flujo de caja,
      y ganancias). Fusiona los informes y guarda el resultado en un archivo de caché que lleva el prefijo del trimestre actual 
      (Qx). Si la descarga falla, crea un archivo marcador Q0 para que la fase de mantenimiento lo maneje.

    Utiliza System.FUNDAMENTALS_PATH para la cache.
    """
    # Inicializar el cliente de Alpha Vantage 
    fd = FundamentalData(key=api_key, output_format="pandas")

    # Calcular el cuatrimestre actual para nombrar el archivo de caché
    current_month = datetime.now().month
    current_quarter = (current_month - 1) // 3 + 1

    # Usar la ruta estática para Fundamentales y asegurar que existe
    folder_path = System.FUNDAMENTALS_PATH
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"Directorio '{folder_path}' ya existe.") 

    all_data_list = [] 
    symbols = simbolos_df["Symbol"].tolist()

    for symbol in symbols:
        
        file_name = f"Q{current_quarter}_{symbol}.csv"
        file_path = folder_path / file_name # 🎯 USO DE PATHLIB

        data = pd.DataFrame()

        # Verificar si el fichero ya existe
        if file_path.is_file(): # 🎯 USO DE PATHLIB

            print(f"Datos ya guardados en {file_path}. Cargando datos locales...")
            try:
                # Importante: usar el mismo separador (sep=';') que en el guardado
                data = pd.read_csv(file_path, sep=";", parse_dates=['fiscalDateEnding'])
            except Exception as e:
                print(f"Error al cargar el archivo local {file_path}: {e}. Intentando descargar de nuevo.")

        # Descargar si no existe o la caché falló
        if data.empty:
            print(f"Descargando datos de {symbol} de Alpha Vantage...")
            try:
                # ... (Lógica de descarga y fusión de Alpha Vantage) ...
                balance_sheet, _ = fd.get_balance_sheet_quarterly(symbol)
                income_statement, _ = fd.get_income_statement_quarterly(symbol)
                cash_flow, _ = fd.get_cash_flow_quarterly(symbol)
                earnings, _ = fd.get_earnings_quarterly(symbol)

                data = pd.merge(balance_sheet, income_statement, on="fiscalDateEnding", how="outer")
                data = pd.merge(data, cash_flow, on="fiscalDateEnding", how="outer")
                data = pd.merge(data, earnings, on="fiscalDateEnding", how="outer")

                data["Symbol"] = symbol
                
                # ... (Lógica de selección y renombrado de columnas) ...
                columnas_necesarias = [
                    "fiscalDateEnding", "Symbol", "totalRevenue", "ebit", "operatingCashflow",
                    "capitalExpenditures", "netIncome_x", "totalShareholderEquity", 
                    "totalLiabilities", "goodwill", "netIncome_y", "reportedEPS"
                ]
                data = data[data.columns.intersection(columnas_necesarias)]
                
                nuevos_nombres = {"netIncome_y": "Net Income", "reportedEPS": "Diluted EPS"}
                data = data.rename(columns=nuevos_nombres)

                data['fiscalDateEnding'] = pd.to_datetime(data['fiscalDateEnding'])

                # Guardar los datos en un fichero CSV (usando Path y separador ;)
                data.to_csv(file_path, index=False, sep=";")
                print(f"Datos guardados en {file_path}.")

            except Exception as e:
                # ----------------------------------------------------
                # --- CREAR ARCHIVO  VACIO (Q0) ---
                # ----------------------------------------------------
                print(f"Error al descargar datos de AV para {symbol}: {e}.")
                # Q0_{symbol}.csv es el marcador que le dice a la función de YF: "No tengo histórico, haz lo que puedas."
                fail_file_name = f"Q0_{symbol}.csv" 
                fail_file_path = folder_path / fail_file_name # 🎯 USO DE PATHLIB
                
                # Crear un DataFrame vacío con las columnas esenciales (para evitar fallos al cargar)
                empty_data = pd.DataFrame({"fiscalDateEnding": [pd.NaT], "Symbol": [symbol], "totalRevenue": [np.nan]})
                # Sobrescribir el posible Qx (si se creó con éxito) con Q0 (si la descarga falló)
                empty_data.to_csv(fail_file_path, index=False, sep=";")
                print(f"Marcador de fallo '{fail_file_name}' creado para {symbol}. Se intentará actualizar con yfinance.")

                # Pausar para evitar exceder el límite de tasa de AlphaV
                time.sleep(1) 
                
                continue # Pasar al siguiente símbolo

        if not data.empty:
            all_data_list.append(data)
            
        # Pausar para evitar exceder el límite de tasa de AlphaV
        time.sleep(1) 

    # 4. Consolidar el resultado final
    if all_data_list:
        all_data = pd.concat(all_data_list, axis=0)
        all_data['fiscalDateEnding'] = pd.to_datetime(all_data['fiscalDateEnding'], errors='coerce')
        all_data.dropna(subset=['fiscalDateEnding'], inplace=True)
        all_data.set_index("fiscalDateEnding", inplace=True)
        # Eliminar posibles duplicados introducidos por los merges de AlphaV (mantener la primera entrada de la fecha fiscal)
        all_data = all_data.drop_duplicates(subset=all_data.columns.drop(['Symbol']), keep='first')
    else:
        all_data = pd.DataFrame() 

    return all_data


# Mapeo de columnas de yfinance a los nombres estándar (Mantenido)
COLUMN_MAPPING_YF = {
    'TotalRevenue': 'totalRevenue',
    'EBIT': 'ebit',
    'OperatingCashFlow': 'operatingCashflow',
    'CapitalExpenditures': 'capitalExpenditures',
    'NetIncome_is': 'Net Income', 
    'StockholdersEquity': 'totalShareholderEquity',
    'TotalLiabilitiesNetMinorityInterest': 'totalLiabilities',
    'Goodwill': 'goodwill',
}

def update_fundamentals_YF_overwrite(simbolos_df: pd.DataFrame) -> pd.DataFrame: # Se añade type hint de retorno para claridad
    """
    Función : update_fundamentals_YF_overwrite
    
    Ejecuta el mantenimiento híbrido inteligente. Carga el histórico en caché y descarga los últimos reportes trimestrales 
    disponibles de yfinance. Filtra los reportes que son posteriores a la última fecha en caché, los fusiona con los datos 
    históricos, sobrescribe/renombra el archivo de caché al trimestre actual (Q_actual) y elimina la versión antigua u obsoleta.
    Utiliza System.FUNDAMENTALS_PATH para la cache.
    
    Salida: DataFrame consolidado de TODOS los datos fundamentales de la caché.
    """
    
    current_quarter = (datetime.now().month - 1) // 3 + 1
    
    # 🎯 MODIFICACIÓN CLAVE: Usar la ruta estática configurada
    folder_path = System.FUNDAMENTALS_PATH
    folder_path.mkdir(parents=True, exist_ok=True)
   
    all_combined_data = []

    symbols = simbolos_df["Symbol"].tolist()

    for symbol in symbols:
        print(f"\n--- Procesando actualización para {symbol} (Q Actual: {current_quarter}) ---")

        # 1. IDENTIFICAR y CARGAR el archivo existente (el de Q más alto)
        # 🎯 USO DE PATHLIB.GLOB
        # max() selecciona el archivo con el prefijo Q más alto (p. ej., Q4 sobre Q3 o Q0)
        existing_files = [f for f in folder_path.glob(f"Q*_{symbol}.csv")]
        
        file_name = None
        file_path = None
        current_file_quarter = 0

        if existing_files:
            file_path = max(existing_files) # Pathlib soporta max
            file_name = file_path.name
            
            match = re.match(r'Q(\d+)_', file_name)
            if match:
                current_file_quarter = int(match.group(1))

            if current_file_quarter == current_quarter:
                # Caso A: Ya actualizado (el archivo tiene el prefijo del trimestre actual).
                print(f"1. Archivo {file_name} ya tiene el prefijo Q{current_quarter}. Se asume actualizado. Verificando por informes más nuevos.")
            else:
                # Caso B: Obsoleto (Qx < Q_actual) o Fallo (Q0).
                print(f"1. Archivo {file_name} tiene el prefijo Q{current_file_quarter}. Se requiere actualizar a Q{current_quarter}.")

        
        if not file_path or not file_path.exists(): # Si no se encontró ningún archivo histórico.
            print(f"1. Error: El archivo histórico no existe. Ejecuta primero 'download_fundamentals_AlphaV'.")
            continue
            
        # Cargar Histórico Existente para la fusión
        try:
            historical_data = pd.read_csv(file_path, sep=";")
            historical_data['fiscalDateEnding'] = pd.to_datetime(historical_data['fiscalDateEnding'], errors='coerce')
            max_date_in_cache = historical_data['fiscalDateEnding'].max()
            # Si el archivo es un Q0 vacío (max() devuelve NaT/NaN), forzar una fecha antigua.
            if pd.isna(max_date_in_cache): max_date_in_cache = datetime(1900, 1, 1)
        except Exception as e:
            print(f"Error al cargar el histórico de {symbol}: {e}. Archivo corrupto. Saltando este símbolo.")
            continue


        # 2. DESCARGAR y FILTRAR datos de YF
        print(f"2. Último reporte en caché: {max_date_in_cache.strftime('%Y-%m-%d')}. Descargando datos recientes de yfinance...")
        new_reports = pd.DataFrame()
        
        try:
            ticker = yf.Ticker(symbol)
            balance_sheet = ticker.quarterly_balance_sheet.T.reset_index().rename(columns={'index': 'fiscalDateEnding'})
            income_statement = ticker.quarterly_income_stmt.T.reset_index().rename(columns={'index': 'fiscalDateEnding'})
            cash_flow = ticker.quarterly_cash_flow.T.reset_index().rename(columns={'index': 'fiscalDateEnding'})
            
            # Renombrar 'DilutedEPS' antes de la fusión para mantener la coherencia
            if 'DilutedEPS' in income_statement.columns: income_statement.rename(columns={'DilutedEPS': 'Diluted EPS'}, inplace=True)

            for df in [balance_sheet, income_statement, cash_flow]:
                df['fiscalDateEnding'] = pd.to_datetime(df['fiscalDateEnding'], errors='coerce')

            latest_yf_data = pd.merge(balance_sheet, income_statement, on="fiscalDateEnding", how="outer", suffixes=('_bs', '_is'))
            latest_yf_data = pd.merge(latest_yf_data, cash_flow, on="fiscalDateEnding", how="outer")
            latest_yf_data.dropna(subset=['fiscalDateEnding'], inplace=True)
            latest_yf_data["Symbol"] = symbol
            
            # Aplicar mapeo de columnas
            latest_yf_data.rename(columns=COLUMN_MAPPING_YF, inplace=True)
            
            # Filtrar columnas al formato estandarizado
            cols_to_keep = ['fiscalDateEnding', 'Symbol', 'Diluted EPS'] + list(COLUMN_MAPPING_YF.values())
            latest_yf_data = latest_yf_data[latest_yf_data.columns.intersection(cols_to_keep)]
            
            # Filtro CLAVE: Obtener solo reportes posteriores al último en caché
            new_reports = latest_yf_data[latest_yf_data['fiscalDateEnding'] > max_date_in_cache].copy()
            
            if new_reports.empty:
                print("2. YF no tiene informes más nuevos que el caché.")
            else:
                print(f"2. Encontrados {len(new_reports)} informes nuevos para agregar/sobrescribir.")

        except Exception as e:
            print(f"2. Error al descargar o procesar datos recientes de YF para {symbol}: {e}. Usando histórico antiguo.")
            # Si falla la descarga de YF, usamos el histórico que cargamos y pasamos al siguiente símbolo.
            historical_data['fiscalDateEnding'] = pd.to_datetime(historical_data['fiscalDateEnding'], errors='coerce')
            historical_data.set_index('fiscalDateEnding', inplace=True)
            all_combined_data.append(historical_data) 
            time.sleep(0.5) 
            continue
            
        # 3. FUSIÓN y Limpieza
        # Proceder a fusionar si hay nuevos reportes O si el archivo es obsoleto (para renombrar)
        if not new_reports.empty or current_file_quarter < current_quarter:
            
            # Asegurar que las columnas del histórico y los nuevos reportes son compatibles antes de concatenar
            combined_data = pd.concat([historical_data, new_reports], ignore_index=True)
            combined_data.sort_values(by='fiscalDateEnding', inplace=True)
            # Sobrescribir: mantener la última entrada para cada fecha fiscal (la de YF)
            combined_data.drop_duplicates(subset=['fiscalDateEnding', 'Symbol'], keep='last', inplace=True)
            
            if not new_reports.empty: print(f"3. Histórico consolidado: {len(combined_data)} filas.")
            
            # 4. GUARDAR Histórico Consolidado y RENOMBRAR al Q actual
            
            new_file_name = f"Q{current_quarter}_{symbol}.csv"
            new_file_path = folder_path / new_file_name 
            
            combined_data.to_csv(new_file_path, index=False, sep=";")
            
            # Eliminar el archivo antiguo si el nombre ha cambiado (p. ej., Q0 a Q4)
            if new_file_path != file_path and file_path.exists(): 
                os.remove(file_path) # Usamos os.remove, aunque path.unlink() también funciona
                print(f"4. ¡Archivo de cache obsoleto eliminado: {file_name}!")
            
            print(f"4. ¡Archivo actualizado y renombrado a: {new_file_name}! 🎉")
            
        else:
            # Si no hay nuevos reportes y el archivo ya está en el Q actual
            combined_data = historical_data 
            print("3. La caché es la más reciente. No se requiere sobrescribir/renombrar.")

        
        # Aseguramos que el índice sea el correcto antes de añadirlo a la lista final
        combined_data['fiscalDateEnding'] = pd.to_datetime(combined_data['fiscalDateEnding'], errors='coerce')
        combined_data.set_index('fiscalDateEnding', inplace=True)
        all_combined_data.append(combined_data)
        
        time.sleep(0.5) 

    # 5. Concatenar y finalizar
    if all_combined_data:
        final_df = pd.concat(all_combined_data, axis=0)
        # Limpiar columnas duplicadas que puedan haber surgido del proceso de merge
        final_df = final_df.loc[:, ~final_df.columns.duplicated()] 
        return final_df.sort_index()
    else:
        return pd.DataFrame()