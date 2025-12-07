"""
Módulo para la lógica del Índice de Fuerza Relativa (RSI).

Contiene funciones delegadas para la actualización del estado dinámico (ascendente/descendente/mínimo/máximo) 
del RSI y la generación de señales de compra/venta basadas en giros y niveles de fuerza.
"""

from backtesting.lib import crossover
from typing import TYPE_CHECKING, Callable, Tuple, Optional
import pandas as pd

if TYPE_CHECKING:
    # Usamos StrategySelf para tipado sin crear una dependencia circular de importación
    from estrategia_system import System as StrategySelf 
    
    # Definición de tipo para la función de verificación de estado
    CheckStateFunc = Callable[[pd.Series], dict]

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_rsi_state(strategy_self: 'StrategySelf', verificar_estado_indicador_func: 'CheckStateFunc') -> None:
    """
    Actualiza el estado dinámico (STATE) del indicador RSI.

    Calcula y almacena el estado dinámico (mínimo, máximo, ascendente, descendente) 
    en las variables de instancia `strategy_self` si el RSI está activo.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy), que accede a `self.rsi_ind`.
    verificar_estado_indicador_func : CheckStateFunc
        Función auxiliar que calcula el estado dinámico de una serie de pandas.

    Returns
    -------
    None
        Actualiza los atributos de estado de la instancia `strategy_self` directamente.
    """
    if strategy_self.rsi and strategy_self.rsi_ind is not None:
        estado_rsi = verificar_estado_indicador_func(strategy_self.rsi_ind)
        strategy_self.rsi_minimo_STATE = estado_rsi['minimo']
        strategy_self.rsi_maximo_STATE = estado_rsi['maximo']
        strategy_self.rsi_ascendente_STATE = estado_rsi['ascendente']
        strategy_self.rsi_descendente_STATE = estado_rsi['descendente']

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_rsi_buy_signal(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Revisa las señales de compra (lógica OR) generadas por el RSI (Giro de Mínimo o Fuerza Pura).

    La señal de compra se activa por un giro desde un extremo (sobreventa) o por una fuerza 
    continua por encima de un umbral predefinido.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia, que contiene las series RSI y las configuraciones del usuario.
    condicion_base_tecnica : bool
        Condición técnica global actual (el resultado de las señales OR anteriores).

    Returns
    -------
    tuple
        - bool: Nueva `condicion_base_tecnica` (True si se activó una señal OR).
        - Optional[str]: Razón del log de la señal activada, o None si no hay señal de RSI.
    """
    log_reason = None
    
    if strategy_self.rsi and strategy_self.rsi_ind is not None:
        
        # Condición de Giro (Señal más fuerte: Mínimo Local + Cruce de Impulso/Threshold)
        if hasattr(strategy_self, 'rsi_threshold_ind') and strategy_self.rsi_threshold_ind is not None:
            
            # Se asume que 'rsi_minimo' es una propiedad de la estrategia que indica que se detectó un mínimo (e.g., sobreventa).
            cond_min_detect = strategy_self.rsi_minimo if hasattr(strategy_self, 'rsi_minimo') and strategy_self.rsi_minimo is not None else False
            
            # Cruce del RSI por encima de una línea de impulso (ej. 30 o 50).
            cond_crossover_confirm = crossover(strategy_self.rsi_ind, strategy_self.rsi_threshold_ind)
            
            cond_rsi_giro = cond_min_detect and cond_crossover_confirm
            
            if cond_rsi_giro:
                log_reason = "RSI Giro desde Sobreventa"
            
            # Lógica de Fuerza Pura RSI (Anulación OR, se activa si hay fuerza por encima de un umbral)
            cond_rsi_pure_force = False
            if hasattr(strategy_self, 'rsi_strength_threshold') and strategy_self.rsi_strength_threshold is not None:
                # Compara el último valor del RSI con el umbral de fuerza (ej. 50 o un nivel de sobrecompra).
                cond_rsi_pure_force = (strategy_self.rsi_ind[-1] > strategy_self.rsi_strength_threshold)

            # Si hay fuerza pura y aún no se ha detectado una razón (para no sobrescribir el Giro)
            if cond_rsi_pure_force and log_reason is None:
                    log_reason = "RSI Fuerza Pura"

            # Combinar ambas señales con OR
            condicion_base_tecnica |= cond_rsi_giro 
            condicion_base_tecnica |= cond_rsi_pure_force
            
    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_rsi_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta de cierre técnico basada en el estado de sobrecompra o tendencia descendente del RSI.

    La señal de venta se activa si la estrategia está configurada para reaccionar a 
    niveles máximos o a un cambio de tendencia descendente en el RSI.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia.

    Returns
    -------
    tuple
        - bool: True si la señal de venta está activa.
        - Optional[str]: Descripción del cierre para el log, o None.
    """
    # Cierre si el usuario activó rsi_maximo O rsi_descendente como intención, 
    # Y el estado dinámico correspondiente se cumple.
    if (strategy_self.rsi_maximo and strategy_self.rsi_maximo_STATE) or \
       (strategy_self.rsi_descendente and strategy_self.rsi_descendente_STATE): 
        
        return True, "VENTA RSI Máximo/Descendente"
    
    return False, None