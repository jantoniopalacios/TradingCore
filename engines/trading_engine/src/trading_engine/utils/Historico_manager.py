# Utilidades_trading/Historico_manager.py

import pandas as pd
import os
import logging

logger = logging.getLogger("Historico_Manager")

# Lista de columnas que DEBEN ser coherentes con las columnas creadas en backtest.py
# Se asume que esta lista es importada desde backtest.py o un archivo centralizado (mejor opción).

def guardar_historico(resultados_df, fichero_historico, COLUMNAS_HISTORICO):
    """
    Gestiona la escritura (append) de los resultados detallados en el archivo histórico.

    :param resultados_df: DataFrame que contiene los resultados del backtest Y todos los parámetros.
    :param fichero_historico: Ruta completa al archivo CSV del histórico.
    :param COLUMNAS_HISTORICO: Lista de columnas en el orden deseado.
    """
    logger.info(f"Iniciando actualización del histórico detallado: {fichero_historico}")
    
    try:
        # 1. Crear el DataFrame final para el histórico, SELECCIONANDO y ORDENANDO las columnas
        # Se asegura de que el DataFrame solo tiene las columnas definidas y en el orden correcto.
        df_historico_final = resultados_df[COLUMNAS_HISTORICO]
        
        # 2. Verificamos si el archivo ya existe para decidir si incluimos el encabezado.
        es_nuevo_archivo = not os.path.exists(fichero_historico)
        
        # 3. Aseguramos la creación del directorio si no existe
        historico_dir = os.path.dirname(fichero_historico)
        if historico_dir and not os.path.exists(historico_dir):
            os.makedirs(historico_dir, exist_ok=True)
            
        # 4. Guardamos/Adjuntamos
        df_historico_final.to_csv(
            fichero_historico, 
            index=False, 
            mode='a',             # Usamos 'a' para adjuntar (append)
            header=es_nuevo_archivo, # Incluimos encabezado solo si es la primera vez
            encoding='utf-8'
        )
        logger.info(f"Nuevos registros detallados añadidos al histórico: {fichero_historico}")
        
    except KeyError as e:
        logger.error(f"Error (KeyError): Una o más columnas de COLUMNAS_HISTORICO no se encuentran en resultados_df. {e}")
        logger.error("Asegúrate de que todos los parámetros de la estrategia se añadieron correctamente en el Paso 1.")
    except Exception as e:
        logger.error(f"Error al actualizar el fichero histórico detallado {fichero_historico}: {e}")