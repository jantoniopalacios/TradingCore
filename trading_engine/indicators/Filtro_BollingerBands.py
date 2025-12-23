# trading_engine/indicators/Filtro_BollingerBands.py
"""
Módulo para la lógica de las Bandas de Bollinger (BB).

Contiene funciones delegadas para la actualización del estado dinámico y la generación de señales 
de compra/venta basadas en el cruce de bandas y la volatilidad (ensanchamiento/estrechamiento).
"""

from backtesting.lib import crossover
from typing import Callable, Tuple, Optional, Any, TYPE_CHECKING
import pandas as pd
import ta.volatility # Se asume que usas TA para el cálculo
from ta.volatility import BollingerBands

# 🟢 NUEVA DEFINICIÓN: Equivalente a crossunder, usando crossover(serie2, serie1)
def crossunder(series1, series2):
    """Retorna True si series1 cruza por debajo de series2 en la última barra."""
    return crossover(series2, series1)

if TYPE_CHECKING:
    from estrategia_system import System as StrategySelf 
    CheckStateFunc = Callable[[pd.Series], dict]

# ======================================================================
# --- CÁLCULO DE BANDAS (HELPER) ---
# ======================================================================
def calculate_bollinger_bands(data: Any, window: int, num_std: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calcula la Media Móvil Simple (SMA) y las Bandas Superior e Inferior.

    Parameters
    ----------
    data : Any
        DataFrame con datos 'Close', 'High', 'Low' (se espera self.data.df).
    window : int
        Período (ventana) para el cálculo de la SMA.
    num_std : float
        Número de desviaciones estándar.

    Returns
    -------
    tuple[pd.Series, pd.Series, pd.Series]
        (SMA, Upper Band, Lower Band)
    """
    # Se extrae la serie de cierre, asumiendo que 'data' es un DataFrame o tiene atributo 'Close'
    close_series = pd.Series(data.Close)
    
    # 🌟 CORRECCIÓN DEL ERROR: Instanciar la clase BollingerBands
    # En lugar de llamar a una función 'bollinger_bands' que no existe
    bb_indicator = BollingerBands(
        close=close_series, 
        window=window, 
        window_dev=num_std,
        fillna=False 
    )

    sma = bb_indicator.bollinger_mavg()
    upper = bb_indicator.bollinger_hband()
    lower = bb_indicator.bollinger_lband()
    
    return sma, upper, lower

# ----------------------------------------------------------------------
# --- Actualización de Estado Dinámico (Volatilidad / Extremos) ---
# ----------------------------------------------------------------------
def update_bb_state(strategy_self: 'StrategySelf', verificar_estado_indicador_func: 'CheckStateFunc') -> None:
    """
    CORRECCIÓN: Se captura el diccionario retornado por la función auxiliar
    y se asignan los valores a los atributos de la estrategia.
    """
    if not strategy_self.bb_active or strategy_self.bb_sma_series is None:
        return

    precio_actual = strategy_self.data.Close[-1]
    
    # 1. Estados de posición (Precio vs Bandas)
    strategy_self.bb_minimo_STATE = precio_actual < strategy_self.bb_lower_band_series[-1]
    strategy_self.bb_maximo_STATE = precio_actual > strategy_self.bb_upper_band_series[-1]

    # 2. Estados de tendencia (SMA central)
    # LLAMADA CORRECTA: Solo pasamos la serie
    estados_sma = verificar_estado_indicador_func(strategy_self.bb_sma_series)
    
    # Asignamos los resultados del diccionario a la estrategia
    strategy_self.bb_ascendente_STATE = estados_sma["ascendente"]
    strategy_self.bb_descendente_STATE = estados_sma["descendente"]
    # Nota: También podrías usar estados_sma["minimo"] si quieres detectar giros en la SMA

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_bb_buy_signal(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de compra (lógica OR): Precio cruza por encima de la Banda Inferior (reversión).

    Parameters
    ----------
    strategy_self: Instancia de la estrategia.
    condicion_base_tecnica: Condición técnica global actual.

    Returns
    -------
    tuple: (Nueva condición base técnica, Razón del log)
    """
    # Añade este print temporal para ver qué está pasando "por dentro"
    # print(f"DEBUG: {strategy_self.data.index[0].date()} - BB_Min_State: {strategy_self.bb_minimo_STATE}")

    log_reason = None
    
    # 🌟 ADAPTACIÓN: Verificamos si la lógica de compra específica está activa.
    if strategy_self.bb_active and strategy_self.bb_buy_crossover:
        close_price = strategy_self.data.Close
        # Usamos el último valor de la serie de la banda inferior
        lower_band = strategy_self.bb_lower_band_series 
        
        # 🟢 Señal: Precio cruza por ENCIMA de la Banda Inferior (saliendo de sobreventa)
        cond_buy_band = crossover(close_price, lower_band)

        if cond_buy_band:
            log_reason = "BB Reversión desde Banda Inferior"
            condicion_base_tecnica = True

    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_bb_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta de cierre técnico: Precio cruza por debajo de la Banda Superior 
    o Cruce a la baja de la SMA (fin de tendencia).

    Returns
    -------
    tuple: (True si la señal de venta está activa, Descripción del cierre)
    """
    # 🌟 ADAPTACIÓN: Verificamos si la lógica de venta específica está activa.
    if strategy_self.bb_active and strategy_self.bb_sell_crossover:
        close_price = strategy_self.data.Close
        upper_band = strategy_self.bb_upper_band_series
        sma_band = strategy_self.bb_sma_series
        
        # 🔴 Señal 1: Precio cruza por DEBAJO de la Banda Superior (saliendo de sobrecompra)
        cond_sell_band = crossunder(close_price, upper_band)
        
        # 🔴 Señal 2: Precio cruza por DEBAJO de la SMA (fin de tendencia)
        # Esto es un buen filtro de salida para cerrar la posición al perder el momentum central.
        cond_sell_sma = crossunder(close_price, sma_band) 
        
        # Se activa si CUALQUIERA de las condiciones de venta está activa (lógica OR en la venta)
        if cond_sell_band or cond_sell_sma:
            return True, "VENTA BB Extremo/Fin Tendencia"
    
    return False, None