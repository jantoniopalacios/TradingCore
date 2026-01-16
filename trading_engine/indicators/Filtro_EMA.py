"""
Módulo para la lógica de la Media Móvil Exponencial (EMA).

Contiene funciones delegadas para la actualización del estado dinámico (ascendente/descendente/mínimo/máximo) 
de la EMA Lenta, y la generación de señales de compra/venta basadas en cruces y tendencia.


"""

from backtesting.lib import crossover
from typing import TYPE_CHECKING, Callable, Tuple, Optional

if TYPE_CHECKING:
    # Usamos StrategySelf para tipado sin crear una dependencia circular de importación
    from estrategia_system import System as StrategySelf 
    
    # Definición de tipo para la función de verificación de estado
    CheckStateFunc = Callable[[pd.Series], dict]

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_ema_state(strategy_self: 'StrategySelf', verificar_estado_indicador_func: 'CheckStateFunc') -> None:
    """
    Actualiza el estado dinámico (STATE) de la EMA Lenta (ma_slow) basado en sus últimos valores.

    Este estado se almacena como variables booleanas de instancia (ej. `ema_slow_minimo_STATE`) 
    para ser utilizado posteriormente por las funciones de señal y filtrado.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy), que accede a `self.ema_slow_series`.
    verificar_estado_indicador_func : CheckStateFunc
        Función auxiliar que calcula el estado dinámico (minimo, maximo, ascendente, descendente) 
        de una serie de pandas.

    Returns
    -------
    None
        Actualiza los atributos de estado de la instancia `strategy_self` directamente.
    """
    if strategy_self.ema_slow_series is not None:
        estado_ema = verificar_estado_indicador_func(strategy_self.ema_slow_series)
        strategy_self.ema_slow_minimo_STATE = estado_ema['minimo']
        strategy_self.ema_slow_maximo_STATE = estado_ema['maximo']
        strategy_self.ema_slow_ascendente_STATE = estado_ema['ascendente']
        strategy_self.ema_slow_descendente_STATE = estado_ema['descendente']

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_ema_buy_signal(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Revisa las señales de compra (lógica OR) generadas por la EMA (Cruce, Mínimo o Ascendente).

    Cualquiera de estas señales puede establecer la `condicion_base_tecnica` como True.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia, que contiene las series EMA y las configuraciones del usuario.
    condicion_base_tecnica : bool
        Condición técnica global actual (el resultado de las señales OR anteriores).

    Returns
    -------
    tuple
        - bool: Nueva `condicion_base_tecnica` (True si se activó una señal OR).
        - Optional[str]: Razón del log de la señal activada, o None si no hay señal de EMA.
    """
    log_reason = None
    
    # (A) Lógica de Cruce (EMA Rápida cruza encima de la EMA Lenta)
    if strategy_self.ema_cruce_signal and strategy_self.ema_fast_series is not None and strategy_self.ema_slow_series is not None:
        # La función 'crossover' verifica si la primera serie cruza sobre la segunda en el tick actual.
        cond_tendencia_cruce = crossover(strategy_self.ema_fast_series, strategy_self.ema_slow_series)
        if cond_tendencia_cruce:
            log_reason = "EMA Cruce Rápida/Lenta"
            # Usa el operador |= (OR a nivel de bit) para mantener el estado True si ya lo estaba.
            condicion_base_tecnica |= cond_tendencia_cruce

    # (B) Lógica de Estado (Señal OR basada en el estado dinámico de la EMA Lenta)
    
    # 1. Señal OR por MÍNIMO: Si el usuario requiere MÍNIMO Y el estado actual es MÍNIMO.
    if strategy_self.ema_slow_minimo and strategy_self.ema_slow_minimo_STATE:
        log_reason = "EMA Lenta Minimo"
        condicion_base_tecnica = True

    # 2. Señal OR por ASCENDENTE: Si el usuario requiere ASCENDENTE Y el estado actual es ASCENDENTE.
    if strategy_self.ema_slow_ascendente and strategy_self.ema_slow_ascendente_STATE:
        log_reason = "EMA Lenta Ascendente"
        condicion_base_tecnica = True 
        
    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Filtro Global de Compra (Condición AND) ---
# ----------------------------------------------------------------------
def apply_ema_global_filter(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> bool:
    """
    Aplica el filtro global excluyente (Condición AND) de la EMA Lenta.

    Este filtro puede anular cualquier señal de compra generada por la lógica OR si 
    las condiciones de tendencia de la EMA Lenta son desfavorables o si no se cumplen 
    los requerimientos mínimos.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia con los parámetros de filtrado activados.
    condicion_base_tecnica : bool
        Condición técnica global actual.

    Returns
    -------
    bool
        La `condicion_base_tecnica` modificada (False si falla el filtro, True en caso contrario).
    """

    # Si el filtro de EMA no está activo, devolvemos la condición tal cual viene
    if not strategy_self.ema_cruce_signal: 
        return condicion_base_tecnica

    if strategy_self.ema_slow_activo:
        
        # ⚠️ Lógica de DENIEGO (Si se intenta comprar en tendencia MAXIMO o DESCENDENTE)
        if (strategy_self.ema_slow_maximo and strategy_self.ema_slow_maximo_STATE) or \
           (strategy_self.ema_slow_descendente and strategy_self.ema_slow_descendente_STATE):
            return False # DENIEGO TOTAL (Anula cualquier señal OR)
            
        # ✅ Lógica de REQUERIMIENTO (Asegura que se cumpla el estado deseado)
        # Si el usuario REQUIERE MÍNIMO pero el estado NO es MÍNIMO, se deniega.
        if (strategy_self.ema_slow_minimo and not strategy_self.ema_slow_minimo_STATE) or \
           (strategy_self.ema_slow_ascendente and not strategy_self.ema_slow_ascendente_STATE):
            return False # DENIEGO por requerimiento no cumplido (Anula cualquier señal OR)

    return condicion_base_tecnica

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_ema_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta de cierre técnico basada en el estado de la EMA Lenta.

    La señal de venta se activa si la EMA Lenta pasa a un estado de tendencia descendente o mñaximo,
    sirviendo como filtro de salida de tendencia.

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
 
    """Verifica si el botón 'Decreciente' de la web debe cerrar la posición."""
    
    # 1. Comprobar si el usuario seleccionó 'Decreciente' (valor: ema_slow_descendente)
    if strategy_self.ema_sell_logic == 'ema_slow_descendente':
        # 2. Si el cálculo técnico (de los extremos) confirma que baja
        if strategy_self.ema_slow_descendente_STATE:
            return True, "VENTA: EMA Lenta Descendente"
            
    # Si eligió 'Máximo'
    if strategy_self.ema_sell_logic == 'ema_slow_maximo':
        if strategy_self.ema_slow_maximo_STATE:
            return True, "VENTA: Máximo en EMA Lenta"

    return False, None