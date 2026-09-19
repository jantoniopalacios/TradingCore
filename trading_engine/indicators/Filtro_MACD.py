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
# --- Utilidades de señal ---
# ----------------------------------------------------------------------
def _logic_value(strategy_self, attr_name: str) -> str:
    """Devuelve la opción de lógica MACD normalizada."""
    value = getattr(strategy_self, attr_name, 'None')
    if value is None:
        return 'none'
    return str(value).strip().lower()


def _histogram_crosses_up(macd_hist) -> bool:
    """True cuando el histograma cruza de cero/negativo a positivo."""
    try:
        previous = float(macd_hist[-2])
        current = float(macd_hist[-1])
    except Exception:
        try:
            previous = float(macd_hist.iloc[-2])
            current = float(macd_hist.iloc[-1])
        except Exception:
            return False
    return previous <= 0 < current


def _histogram_crosses_down(macd_hist) -> bool:
    """True cuando el histograma cruza de cero/positivo a negativo."""
    try:
        previous = float(macd_hist[-2])
        current = float(macd_hist[-1])
    except Exception:
        try:
            previous = float(macd_hist.iloc[-2])
            current = float(macd_hist.iloc[-1])
        except Exception:
            return False
    return previous >= 0 > current


# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_macd_buy_signal(strategy_self, condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """Evalúa la señal de compra MACD seleccionada en ``macd_buy_logic``.

    Opciones admitidas:
    - ``macd_cruce_up``: MACD Line cruza al alza Signal Line.
    - ``macd_histogram_buy``: el histograma cruza de cero/negativo a positivo.
    - ``None``: MACD no genera señal de compra.
    """
    if not getattr(strategy_self, 'macd', False):
        return condicion_base_tecnica, None

    logic = _logic_value(strategy_self, 'macd_buy_logic')
    signal = False
    reason = None

    if logic == 'macd_cruce_up':
        macd_line = getattr(strategy_self, 'macd_line', None)
        signal_line = getattr(strategy_self, 'macd_signal_line', None)
        if macd_line is not None and signal_line is not None:
            signal = bool(crossover(macd_line, signal_line))
            if signal:
                reason = 'MACD Cruce Up'

    elif logic == 'macd_histogram_buy':
        macd_hist = getattr(strategy_self, 'macd_hist', None)
        if macd_hist is not None:
            signal = _histogram_crosses_up(macd_hist)
            if signal:
                reason = 'MACD Histograma Buy'

    # ``None`` o cualquier valor no reconocido se trata de forma segura como sin señal.
    return condicion_base_tecnica or signal, reason


# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_macd_sell_signal(strategy_self) -> Tuple[bool, Optional[str]]:
    """Evalúa la señal de venta MACD seleccionada en ``macd_sell_logic``.

    Opciones admitidas:
    - ``macd_cruce_down``: MACD Line cruza a la baja Signal Line.
    - ``macd_histogram_sell``: el histograma cruza de cero/positivo a negativo.
    - ``None``: MACD no genera señal de venta.
    """
    if not getattr(strategy_self, 'macd', False):
        return False, None

    logic = _logic_value(strategy_self, 'macd_sell_logic')

    if logic == 'macd_cruce_down':
        macd_line = getattr(strategy_self, 'macd_line', None)
        signal_line = getattr(strategy_self, 'macd_signal_line', None)
        if macd_line is not None and signal_line is not None and crossover(signal_line, macd_line):
            return True, 'MACD Cruce Down'

    elif logic == 'macd_histogram_sell':
        macd_hist = getattr(strategy_self, 'macd_hist', None)
        if macd_hist is not None and _histogram_crosses_down(macd_hist):
            return True, 'MACD Histograma Sell'

    return False, None
