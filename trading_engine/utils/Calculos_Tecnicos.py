# Calculos_Tecnicos.py

"""
Módulo dedicado al análisis técnico auxiliar de series de tiempo.
Contiene funciones para detectar mínimos/máximos locales y la dirección 
(tendencia local) de un indicador o precio.
"""

import numpy as np
import pandas as pd
from typing import Union, List

# Definición de tipos para las funciones
SeriesOrList = Union[pd.Series, np.ndarray, List[float]]

# ----------------------------------------------------------------------
# --- FUNCIONES DE ANÁLISIS DE ESTADO (Tendencia) ---
# ----------------------------------------------------------------------

def es_ascendente(serie: SeriesOrList, periodo: int = 3) -> bool:
    """
    Determina si la serie es ascendente comparando el valor actual 
    con el valor del inicio del periodo (más robusto ante mesetas).
    """
    if len(serie) < periodo:
        return False
    
    # Compara el último punto con el primero del bloque
    return serie[-1] > serie[-periodo]


def es_descendente(serie: SeriesOrList, periodo: int = 3) -> bool:
    """
    Determina si la serie es descendente comparando el valor actual 
    con el valor del inicio del periodo.
    """
    if len(serie) < periodo:
        return False
        
    # Compara el último punto con el primero del bloque
    # Esto detectará la caída en MSFT aunque haya velas planas entre medias
    return serie[-1] < serie[-periodo]

# ----------------------------------------------------------------------
# --- FUNCIONES DE ANÁLISIS DE ESTADO (Mínimos y Máximos Locales) ---
# ----------------------------------------------------------------------

def es_minimo_local(serie: SeriesOrList) -> bool:
    """
    Detecta si el punto anterior es un mínimo local (giro de U).
    
    Requiere al menos 3 puntos: [anterior_anterior, anterior, actual].
    Se cumple si: (anterior < anterior_anterior) Y (actual > anterior)

    :param serie: Serie de tiempo (indicador, precio, etc.).
    :return: True si se detecta un mínimo local en el punto anterior.
    """
    if len(serie) < 3:
        return False
    
    # Puntos: [-3] anterior_anterior, [-2] anterior, [-1] actual
    anterior_anterior = serie[-3]
    anterior = serie[-2]
    actual = serie[-1]
    
    # Condición de mínimo: la vela anterior fue más baja que la ante-anterior
    # y la vela actual es más alta que la anterior.
    return (anterior < anterior_anterior) and (actual > anterior)


def es_maximo_local(serie: SeriesOrList) -> bool:
    """
    Detecta si el punto anterior es un máximo local (giro de V invertida).
    
    Requiere al menos 3 puntos: [anterior_anterior, anterior, actual].
    Se cumple si: (anterior > anterior_anterior) Y (actual < anterior)

    :param serie: Serie de tiempo (indicador, precio, etc.).
    :return: True si se detecta un máximo local en el punto anterior.
    """
    if len(serie) < 3:
        return False
    
    # Puntos: [-3] anterior_anterior, [-2] anterior, [-1] actual
    anterior_anterior = serie[-3]
    anterior = serie[-2]
    actual = serie[-1]

    # Condición de máximo: la vela anterior fue más alta que la ante-anterior
    # y la vela actual es más baja que la anterior.
    return (anterior > anterior_anterior) and (actual < anterior)

# ----------------------------------------------------------------------
# --- FUNCIÓN DE VERIFICACIÓN DE ESTADO ---
# ----------------------------------------------------------------------

def verificar_estado_indicador(indicador_serie: SeriesOrList) -> dict: # <-- Usamos el tipo SeriesOrList definido
    """
    Función auxiliar para resumir el estado técnico de un indicador.
    
    :param indicador_serie: La serie del indicador (backtesting._Indicator o pd.Series).
    :return: Diccionario con los estados booleanos.
    """
    # Verificación de datos insuficientes
    if indicador_serie is None or len(indicador_serie) < 3:
        return {
            "minimo": False, "maximo": False, 
            "ascendente": False, "descendente": False
        }
        
    # NOTA DE CORRECCIÓN: No usamos .values, ya que indicador_serie (un backtesting._Indicator) 
    # se comporta como un array de NumPy y puede ser indexado o pasado directamente.
    
    # Calculamos estados, pasando el objeto indicador directamente
    estado = {
        # Se ha producido un mínimo/máximo justo en la vela anterior (giro)
        "minimo": es_minimo_local(indicador_serie), # <-- Pasamos el objeto directamente
        "maximo": es_maximo_local(indicador_serie), # <-- Pasamos el objeto directamente
        # El valor del indicador crece/decrece en las últimas 3 velas
        "ascendente": es_ascendente(indicador_serie, periodo=3), # <-- Pasamos el objeto directamente
        "descendente": es_descendente(indicador_serie, periodo=3) # <-- Pasamos el objeto directamente
    }
    
    return estado