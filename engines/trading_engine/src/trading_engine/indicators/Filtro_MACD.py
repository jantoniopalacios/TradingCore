# indicadores_tecnicos/Filtro_MACD.py
"""
Módulo para la lógica de la Media Móvil de Convergencia/Divergencia (MACD).
Contiene funciones para la actualización del estado dinámico del histograma 
y la generación de señales de compra/venta basadas en cruces e impulso.
"""

from backtesting.lib import crossover
from typing import Callable, Tuple, Optional

# Se asume que 'verificar_estado_indicador' será importado o pasado como argumento.

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_macd_state(strategy_self, verificar_estado_indicador_func: Callable):
    """
    Actualiza el estado dinámico (STATE) del Histograma MACD (macd_hist) en la instancia de la estrategia.

    Este proceso calcula si el histograma ha alcanzado un mínimo/máximo o si su tendencia es ascendente/descendente
    en la vela actual, utilizando una función auxiliar. Los resultados se almacenan en las variables de estado internas 
    (e.g., :py:attr:`strategy_self.macd_minimo_STATE`).

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia de trading que contiene el histórico de precios
        y las variables de estado.
    verificar_estado_indicador_func : Callable
        Función auxiliar utilizada para calcular el estado dinámico del histograma
        (mínimo, máximo, ascendente, descendente) a partir de los datos históricos.

    Returns
    -------
    None
    """
    if strategy_self.macd and strategy_self.macd_hist is not None:
        estado_macd = verificar_estado_indicador_func(strategy_self.macd_hist)
        strategy_self.macd_minimo_STATE = estado_macd['minimo']
        strategy_self.macd_maximo_STATE = estado_macd['maximo']
        strategy_self.macd_ascendente_STATE = estado_macd['ascendente']
        strategy_self.macd_descendente_STATE = estado_macd['descendente']

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_macd_buy_signal(strategy_self, condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Evalúa las señales de compra generadas por el indicador MACD.

    Esta función combina el cruce alcista (MACD Line cruza por encima de Signal Line) con una 
    condición opcional de **Impulso Creciente** (Histograma Ascendente) si esta es requerida 
    por la configuración de la estrategia (strategy_self.macd_ascendente=True). 
    La condición de compra resultante se agrega mediante una operación OR a la condición base técnica.

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia que contiene los datos del indicador 
        (self.macd_line, self.macd_signal_line) y la configuración de impulso.
    condicion_base_tecnica : bool
        El estado actual de la condición de entrada de compra técnica global.

    Returns
    -------
    tuple[bool, str | None]
        - bool: La nueva condición base técnica después de aplicar la lógica OR del MACD.
        - str | None: Razón de la señal de compra para fines de logging (e.g., "MACD Fuerte") o None si no hay señal.
    """
    log_reason = None

    if strategy_self.macd and strategy_self.macd_hist is not None:
        
        # 1. Señal de Cruce (MACD Line sobre Signal Line)
        macd_buy = crossover(strategy_self.macd_line, strategy_self.macd_signal_line)
        
        # 2. Condición de Impulso (Histograma Creciente)
        # Lógica: Si el usuario requiere MACD ascendente (strategy_self.macd_ascendente=True), 
        # debe cumplirse el estado REAL (strategy_self.macd_ascendente_STATE).
        cond_impulso_ok = True
        if strategy_self.macd_ascendente: 
            cond_impulso_ok = strategy_self.macd_ascendente_STATE
        
        # MACD Fuerte: Cruce AND (Impulso Requerido Check)
        cond_macd_fuerte = macd_buy and cond_impulso_ok
        
        if cond_macd_fuerte:
            log_reason = "MACD Fuerte"

        condicion_base_tecnica |= cond_macd_fuerte 

    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_macd_sell_signal(strategy_self) -> Tuple[bool, Optional[str]]:
    """
    Evalúa las señales de salida o cierre de posición generadas por el indicador MACD.

    La señal de venta se activa si se cumple alguna de las siguientes condiciones, basada
    en el estado dinámico del Histograma MACD:

    1.  El Histograma ha alcanzado un **Máximo** (si strategy_self.macd_maximo es True).
    2.  El Histograma es **Descendente** (si strategy_self.macd_descendente es True).

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia que contiene las variables de configuración y estado del MACD
        (e.g., self.macd_maximo, self.macd_maximo_STATE).

    Returns
    -------
    tuple[bool, str | None]
        - bool: True si se detecta una señal de venta activa, False en caso contrario.
        - str | None: Descripción de la razón del cierre (e.g., "VENTA MACD Máximo/Descendente") o None.
    """
    # Cierre si el Histograma MACD indica un Máximo o se vuelve Descendente
    if (strategy_self.macd_maximo and strategy_self.macd_maximo_STATE) or \
       (strategy_self.macd_descendente and strategy_self.macd_descendente_STATE):
        
        return True, "VENTA MACD Máximo/Descendente"
    
    return False, None