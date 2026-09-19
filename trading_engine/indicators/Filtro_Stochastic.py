# indicadores_tecnicos/Filtro_Stochastic.py
"""
Módulo Genérico para la lógica de Osciladores de Cruce (como Estocásticos Fast/Mid/Slow).

Contiene funciones reutilizables que son llamadas múltiples veces en el coordinador (Logica_Trading.py), 
una vez por cada versión de Estocástico (Rápido, Medio, Lento). La lógica implementa señales de cruce 
(%K vs %D) filtradas opcionalmente por la zona de sobreventa/sobrecompra y por los estados dinámicos.
"""

from backtesting.lib import crossover
from typing import Callable, Tuple, Optional, Any
import pandas as pd
import ta.momentum # ¡Necesaria para el cálculo!

# ======================================================================
# --- INDICADOR AUXILIAR (HELPER) PARA SOLUCIONAR EL UNPACKING ---
# ======================================================================
class StochHelper: 
    """
    Clase auxiliar (Wrapper) utilizada para calcular el oscilador Estocástico.

    Se utiliza para encapsular la lógica de cálculo del paquete 'ta' (Technical Analysis)
    y asegurar que los datos de entrada (O/H/L/C) sean Series de Pandas para que los 
    cálculos internos (como rolling mean) se realicen correctamente, devolviendo las 
    Series %K y %D necesarias para Backtesting.py.
    """
    def calculate(self, data: Any, window: int, smooth_window: int) -> Tuple[pd.Series, pd.Series]: 
        """
        Calcula las líneas %K y %D del Oscilador Estocástico.

        Parameters
        ----------
        data : pd.DataFrame
            El DataFrame histórico con columnas High, Low, y Close.
        window : int
            El período de tiempo (ventana) para el cálculo del %K (e.g., 14).
        smooth_window : int
            El período de suavizado para el cálculo del %K (e.g., 3).

        Returns
        -------
        tuple[pd.Series, pd.Series]
            - pd.Series: La línea %K (principal) del Oscilador Estocástico.
            - pd.Series: La línea %D (señal) del Oscilador Estocástico.
        """
        
        high_series = pd.Series(data.High)
        low_series = pd.Series(data.Low)
        close_series = pd.Series(data.Close)

        # 1. Realizar el cálculo de %K con los parámetros dinámicos
        stoch_k_series = ta.momentum.stoch(
            high=high_series, 
            low=low_series, 
            close=close_series, 
            window=window, 
            smooth_window=smooth_window 
        )

        # 2. Calcular la LÍNEA %D (Promedio móvil de 3 periodos de la línea %K)
        # La línea D (señal) se calcula como el promedio móvil de la línea K, usando el período estándar de 3.
        signal_period = 3 
        stoch_d_series = stoch_k_series.rolling(window=signal_period, min_periods=1).mean()
        
        # 3. Devolver las dos Series (K y D)
        return stoch_k_series, stoch_d_series
    
# ======================================================================
# ----------------------------------------------------------------------
# --- Actualización de Estado Genérica ---
# ----------------------------------------------------------------------
def update_oscillator_state(strategy_self, prefix: str, k_series: pd.Series, verificar_estado_indicador_func: Callable):
    """
    Actualiza el estado dinámico (STATE) de una serie de oscilador (%K).

    Esta función utiliza el ``prefix`` para asignar los resultados de forma dinámica
    a las variables de estado de la estrategia (e.g., ``strategy_self.stoch_fast_minimo_STATE``).

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia de trading.
    prefix : str
        Prefijo del indicador utilizado para acceder/establecer variables dinámicas 
        (e.g., 'stoch_fast', 'stoch_mid', 'stoch_slow').
    k_series : pd.Series
        Serie de datos del %K (o línea principal) del oscilador.
    verificar_estado_indicador_func : Callable
        Función auxiliar utilizada para calcular el estado dinámico (mínimo, máximo, ascendente, descendente).

    Returns
    -------
    None
    """
    if k_series is not None:
        estado_osc = verificar_estado_indicador_func(k_series)
        
        # Asignación dinámica al objeto strategy_self
        setattr(strategy_self, f"{prefix}_minimo_STATE", estado_osc['minimo'])
        setattr(strategy_self, f"{prefix}_maximo_STATE", estado_osc['maximo'])
        setattr(strategy_self, f"{prefix}_ascendente_STATE", estado_osc['ascendente'])
        setattr(strategy_self, f"{prefix}_descendente_STATE", estado_osc['descendente'])

# ----------------------------------------------------------------------
# --- Lógica de Compra Genérica (Señales OR) ---
# ----------------------------------------------------------------------
def check_oscillator_buy_signal(
    strategy_self,
    prefix: str,
    k_series: pd.Series,
    d_series: pd.Series,
    low_level: Optional[float],
) -> Tuple[bool, Optional[str]]:
    if k_series is None or d_series is None:
        return False, None

    buy_logic = getattr(strategy_self, f"{prefix}_buy_logic", "None")

    if buy_logic in (None, "", "None"):
        return False, None

    ascendente_setting = buy_logic == f"{prefix}_ascendente"
    minimo_setting = buy_logic == f"{prefix}_minimo"

    if not ascendente_setting and not minimo_setting:
        return False, None

    buy_signal = crossover(k_series, d_series)

    k_actual = k_series.iloc[-1] if hasattr(k_series, "iloc") else k_series[-1]

    if low_level is not None:
        buy_signal &= (k_actual < low_level)

    log_parts = []

    if ascendente_setting:
        ascendente_state = getattr(
            strategy_self,
            f"{prefix}_ascendente_STATE",
            False,
        )
        buy_signal &= ascendente_state
        if ascendente_state:
            log_parts.append("Ascendente")

    if minimo_setting:
        minimo_state = getattr(
            strategy_self,
            f"{prefix}_minimo_STATE",
            False,
        )
        buy_signal &= minimo_state
        if minimo_state:
            log_parts.append("Mínimo")

    if buy_signal:
        log_name = prefix.replace("_", " ").title()

        if log_parts:
            reason = f"{log_name} Cruce & {' & '.join(log_parts)}"
        else:
            reason = f"{log_name} Cruce"

        return True, reason

    return False, None

# ----------------------------------------------------------------------
# --- Lógica de Venta Genérica (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_oscillator_sell_signal(
    strategy_self,
    prefix: str,
) -> Tuple[bool, Optional[str]]:
    sell_logic = getattr(strategy_self, f"{prefix}_sell_logic", "None")

    if sell_logic in (None, "", "None"):
        return False, None

    maximo_setting = sell_logic == f"{prefix}_maximo"
    descendente_setting = sell_logic == f"{prefix}_descendente"

    if not maximo_setting and not descendente_setting:
        return False, None

    maximo_state = getattr(
        strategy_self,
        f"{prefix}_maximo_STATE",
        False,
    )
    descendente_state = getattr(
        strategy_self,
        f"{prefix}_descendente_STATE",
        False,
    )

    log_name = prefix.replace("_", " ").title()

    if maximo_setting and maximo_state:
        return True, f"{log_name} Máximo"

    if descendente_setting and descendente_state:
        return True, f"{log_name} Descendente"

    return False, None

# NOTA: Se ha corregido la lógica de AND en check_oscillator_buy_signal (Líneas 149 y 159) para asegurar
# que los filtros de estado actúen como verdaderas condiciones de filtrado (AND) y no como condiciones OR.