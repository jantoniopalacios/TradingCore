"""
Módulo para la lógica de las Bandas de Bollinger (BB).

Contiene funciones delegadas para la actualización del estado dinámico y la generación de señales 
de compra/venta basadas en el cruce de bandas y la volatilidad.
"""

from backtesting.lib import crossover
from typing import Callable, Tuple, Optional, Any, TYPE_CHECKING
import pandas as pd
from ta.volatility import BollingerBands

# --- EQUIVALENTE A CROSSUNDER ---
def crossunder(series1, series2):
    """Retorna True si series1 cruza por debajo de series2."""
    return crossover(series2, series1)

if TYPE_CHECKING:
    from estrategia_system import System as StrategySelf 
    CheckStateFunc = Callable[[pd.Series], dict]

# ======================================================================
# --- CÁLCULO DE BANDAS (HELPER) ---
# ======================================================================
def calculate_bollinger_bands(data: Any, window: int, num_std: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calcula la Media Móvil Simple (SMA) y las Bandas Superior e Inferior usando la librería TA.
    """
    close_series = pd.Series(data.Close)
    
    bb_indicator = BollingerBands(
        close=close_series, 
        window=window, 
        window_dev=num_std,
        fillna=False 
    )

    return bb_indicator.bollinger_mavg(), bb_indicator.bollinger_hband(), bb_indicator.bollinger_lband()

# ----------------------------------------------------------------------
# --- ACTUALIZACIÓN DE ESTADO DINÁMICO ---
# ----------------------------------------------------------------------
def update_bb_state(strategy_self: 'StrategySelf', verificar_estado_indicador_func: 'CheckStateFunc') -> None:
    """
    Actualiza los atributos de estado (_STATE) en la estrategia.
    """
    if not strategy_self.bb_active or strategy_self.bb_sma_series is None:
        return

    precio_actual = strategy_self.data.Close[-1]
    
    # 1. Estados de posición (Precio vs Extremos)
    strategy_self.bb_minimo_STATE = precio_actual < strategy_self.bb_lower_band_series[-1]
    strategy_self.bb_maximo_STATE = precio_actual > strategy_self.bb_upper_band_series[-1]

    # 2. Estados de tendencia de la SMA central
    estados_sma = verificar_estado_indicador_func(strategy_self.bb_sma_series)
    strategy_self.bb_ascendente_STATE = estados_sma["ascendente"]
    strategy_self.bb_descendente_STATE = estados_sma["descendente"]

# ----------------------------------------------------------------------
# --- LÓGICA DE COMPRA ---
# ----------------------------------------------------------------------
def check_bb_buy_signal(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Señal: Precio cruza por ENCIMA de la Banda Inferior (saliendo de sobreventa).
    """
    log_reason = None
    
    if strategy_self.bb_active and strategy_self.bb_buy_crossover:
        # Señal de reversión alcista
        if crossover(strategy_self.data.Close, strategy_self.bb_lower_band_series):
            log_reason = "BB Reversión desde Banda Inferior"
            condicion_base_tecnica = True

    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- LÓGICA DE VENTA ---
# ----------------------------------------------------------------------
def check_bb_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Señal: Precio cruza por DEBAJO de la Banda Superior o de la SMA central.
    """
    if strategy_self.bb_active and strategy_self.bb_sell_crossover:
        close_price = strategy_self.data.Close
        
        # 1. Salida de sobrecompra (Banda Superior)
        cond_sell_band = crossunder(close_price, strategy_self.bb_upper_band_series)
        
        # 2. Pérdida de momentum (SMA Central)
        cond_sell_sma = crossunder(close_price, strategy_self.bb_sma_series) 
        
        if cond_sell_band or cond_sell_sma:
            return True, "VENTA BB Extremo/Fin Tendencia"
    
    return False, None