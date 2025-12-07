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
def check_oscillator_buy_signal(strategy_self, prefix: str, k_series: pd.Series, d_series: pd.Series, low_level: Optional[float]) -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de compra para un Oscilador genérico.

    La señal de compra base es un **Cruce alcista** (Línea %K sobre Línea %D), 
    que puede ser filtrada por los siguientes criterios (operaciones AND):
    
    1.  **Filtro de Sobreventa:** Ocurre solo si la última vela está por debajo del ``low_level`` (ej. 20).
    2.  **Filtros de Estado Dinámico:** Se consideran si los settings ``_ascendente`` o ``_minimo`` están activados.

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia.
    prefix : str
        Prefijo del indicador (e.g., 'stoch_fast').
    k_series : pd.Series
        Serie de datos de la Línea %K (principal).
    d_series : pd.Series
        Serie de datos de la Línea %D (señal).
    low_level : float | None
        Nivel de sobreventa (e.g., 20). Si es ``None``, no se aplica el filtro de sobreventa.

    Returns
    -------
    tuple[bool, str | None]
        - bool: True si se detecta una señal de compra.
        - str | None: Razón de la señal de compra para fines de logging (e.g., "Stoch Fast Cruce & Ascendente").
    """
    if k_series is None or d_series is None:
        return False, None
    
    # 🟢 1. RECUPERAR SETTINGS DEL USUARIO (si activó el filtro)
    ascendente_setting = getattr(strategy_self, f"{prefix}_ascendente", False)
    minimo_setting = getattr(strategy_self, f"{prefix}_minimo", False)
    
    # 2. CONDICIÓN BASE: Cruce
    buy_signal = crossover(k_series, d_series)
    
    # 3. FILTRO DE SOBREVENTA (Condición AND)
    if low_level is not None:
        # La señal de cruce solo se aplica si está en zona de sobreventa
        buy_signal &= (k_series[-1] < low_level)
    
    # ----------------------------------------------------------
    # 🟢 4. FILTROS DE ESTADO (Condiciones AND)
    # ----------------------------------------------------------
    log_parts = []
    
    # A. Filtro Ascendente
    if ascendente_setting:
        # Recuperar el estado calculado (e.g., stoch_fast_ascendente_STATE)
        ascendente_state = getattr(strategy_self, f"{prefix}_ascendente_STATE", False)
        
        # Aplicar el filtro: solo comprar si la señal es True Y el estado es ascendente
        buy_signal &= ascendente_state # ¡CORRECCIÓN de lógica! Si es un filtro AND, debe ser &=
        if ascendente_state:
            log_parts.append("Ascendente")

    # B. Filtro Mínimo (Local)
    if minimo_setting:
        # Recuperar el estado calculado (e.g., stoch_fast_minimo_STATE)
        minimo_state = getattr(strategy_self, f"{prefix}_minimo_STATE", False)
        
        # Aplicar el filtro: solo comprar si la señal es True Y el estado es mínimo
        buy_signal &= minimo_state # ¡CORRECCIÓN de lógica! Si es un filtro AND, debe ser &=
        if minimo_state:
            log_parts.append("Mínimo")


    # 5. RETORNO FINAL
    if buy_signal:
        # Formato del log: Stoch Fast Cruce & Ascendente & Mínimo
        log_name = prefix.replace('_', ' ').title().replace('Stoch', 'Stoch') 
        
        # Añadir los filtros activados a la razón del log
        if log_parts:
            reason = f"{log_name} Cruce & {' & '.join(log_parts)}"
        else:
            reason = f"{log_name} Cruce"

        return True, reason
    
    return False, None
# ----------------------------------------------------------------------
# --- Lógica de Venta Genérica (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_oscillator_sell_signal(strategy_self, prefix: str) -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta genérica para un Oscilador (%K).

    La señal de venta se activa si se cumple alguna de las siguientes condiciones, basada
    en la configuración de la estrategia y el estado dinámico del oscilador:

    1.  El %K ha alcanzado un **Máximo** (si ``_maximo`` está activado).
    2.  El %K es **Descendente** (si ``_descendente`` está activado).

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia.
    prefix : str
        Prefijo del indicador (e.g., 'stoch_fast', 'stoch_mid').

    Returns
    -------
    tuple[bool, str | None]
        - bool: True si se detecta una señal de venta activa, False en caso contrario.
        - str | None: Descripción de la razón del cierre (e.g., "VENTA Stoch Fast Máximo/Descendente") o None.
    """
    # Accede a los estados y settings de forma dinámica
    maximo_state = getattr(strategy_self, f"{prefix}_maximo_STATE", False)
    descendente_state = getattr(strategy_self, f"{prefix}_descendente_STATE", False)
    maximo_setting = getattr(strategy_self, f"{prefix}_maximo", False)
    descendente_setting = getattr(strategy_self, f"{prefix}_descendente", False)
    
    # Cierre si el oscilador indica Máximo OR se vuelve Descendente
    if (maximo_setting and maximo_state) or \
       (descendente_setting and descendente_state):
        
        log_name = prefix.replace('_', ' ').title().replace('Stoch', 'Stoch')
        return True, f"VENTA {log_name} Máximo/Descendente"
    
    return False, None

# NOTA: Se ha corregido la lógica de AND en check_oscillator_buy_signal (Líneas 149 y 159) para asegurar
# que los filtros de estado actúen como verdaderas condiciones de filtrado (AND) y no como condiciones OR.