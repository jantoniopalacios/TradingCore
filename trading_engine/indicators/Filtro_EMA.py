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
    
    IMPORTANTE: Las señales de EMA SOLO se activan si están EXPLÍCITAMENTE habilitadas en la configuración.
    No se activan automáticamente incluso si los estados técnicos son favorables.

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
    # SOLO se activa si ema_cruce_signal está explícitamente habilitado
    if strategy_self.ema_cruce_signal and strategy_self.ema_fast_series is not None and strategy_self.ema_slow_series is not None:
        # La función 'crossover' verifica si la primera serie cruza sobre la segunda en el tick actual.
        cond_tendencia_cruce = crossover(strategy_self.ema_fast_series, strategy_self.ema_slow_series)
        if cond_tendencia_cruce:
            log_reason = "EMA Cruce Rápida/Lenta"
            # Usa el operador |= (OR a nivel de bit) para mantener el estado True si ya lo estaba.
            condicion_base_tecnica |= cond_tendencia_cruce

    # (B) Lógica de Estado (Señal OR basada en el estado dinámico de la EMA Lenta)
    # SOLO se activan si están explícitamente habilitadas en la configuración
    
    # 1. Señal OR por MÍNIMO: SOLO si el usuario explícitamente activó ema_slow_minimo=True
    if getattr(strategy_self, 'ema_slow_minimo', False) and strategy_self.ema_slow_minimo_STATE:
        log_reason = "EMA Lenta Minimo"
        condicion_base_tecnica = True

    # 2. Señal OR por ASCENDENTE: SOLO si el usuario explícitamente activó ema_slow_ascendente=True
    if getattr(strategy_self, 'ema_slow_ascendente', False) and strategy_self.ema_slow_ascendente_STATE:    
        log_reason = "EMA Lenta Ascendente"
        condicion_base_tecnica = True     
        
    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Filtro Global de Compra (Condición AND) ---
# ----------------------------------------------------------------------
def apply_ema_global_filter(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> bool:
    """
    Aplica el filtro global excluyente (Condición AND) de la EMA Lenta.

    IMPORTANTE: Este filtro implementa una **regla de veto permanente**:
    - Si EMA Lenta está en DESCENSO → BLOQUEA CUALQUIER COMPRA (sin excepciones)
    - Esto es un filtro de protección hardcodeado que no depende de configuración
    
    Además, aplica requerimientos configurables si están habilitados.

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

    # ======================================================================
    # --- FILTRO GLOBAL DE VETO (HARDCODEADO): EMA Descendente BLOQUEA TODO ---
    # ======================================================================
    # Este es un filtro de PROTECCIÓN PERMANENTE que no depende de parámetros configurables.
    # Si la EMA Lenta está en descenso → NO se ejecuta NINGUNA compra, independientemente de
    # cualquier otra señal técnica positiva.
    if hasattr(strategy_self, 'ema_slow_descendente_STATE') and strategy_self.ema_slow_descendente_STATE:
        return False  # VETO ABSOLUTO: Bloquea cualquier compra si EMA está descendiendo
    
    # ======================================================================
    # --- FILTROS CONFIGURABLES (si estan habilitados) ---
    # ======================================================================
    
    # Determinar si el filtro EMA Lenta está habilitado según los flags disponibles
    ema_filter_enabled = any([
        getattr(strategy_self, 'ema_slow_minimo', False),
        getattr(strategy_self, 'ema_slow_maximo', False),
        getattr(strategy_self, 'ema_slow_ascendente', False),
        getattr(strategy_self, 'ema_cruce_signal', False),
    ])

    # Si ningún flag relacionado con EMA Lenta está activado, devolvemos la condición original
    # (pero el filtro de veto ya se aplicó arriba)
    if not ema_filter_enabled:
        return condicion_base_tecnica

    # ⚠️ Lógica de DENIEGO (Si se intenta comprar en tendencia MAXIMO)
    if getattr(strategy_self, 'ema_slow_maximo', False) and strategy_self.ema_slow_maximo_STATE:
        return False # DENIEGO: Máximo local detectado

    # ✅ Lógica de REQUERIMIENTO (Asegura que se cumpla el estado deseado)
    # Si el usuario REQUIERE MÍNIMO pero el estado NO es MÍNIMO, se deniega.
    if getattr(strategy_self, 'ema_slow_minimo', False) and not strategy_self.ema_slow_minimo_STATE:
        return False # DENIEGO: Requerimiento de mínimo no cumplido
    
    # Si el usuario REQUIERE ASCENDENTE pero el estado NO es ASCENDENTE, se deniega.
    if getattr(strategy_self, 'ema_slow_ascendente', False) and not strategy_self.ema_slow_ascendente_STATE:
        return False # DENIEGO: Requerimiento de ascendente no cumplido

    return condicion_base_tecnica

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_ema_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta de cierre técnico basada en el estado de la EMA Lenta.

    La señal de venta se activa si:
    1. El usuario activó la opción "Descendente" (ema_slow_descendente=True) Y la EMA está descendiendo
    2. El usuario activó la opción "Máximo" (ema_slow_maximo=True) Y la EMA detecta un máximo local

    ** IMPORTANTE: Esta lógica AHORA lee directamente los flags de configuración (ema_slow_descendente y 
    ema_slow_maximo), no depende de un parámetro externo ema_sell_logic que no pasa desde el formulario.

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
    
    # ======================================================================
    # OPCIÓN 1: Usuario seleccionó "Decreciente" → Cierra si EMA desciende
    # ======================================================================
    # Si el usuario tiene el switch 'Descendente' activado en la UI para VENTA
    if getattr(strategy_self, 'ema_slow_descendente', False) and strategy_self.ema_slow_descendente_STATE:
        return True, "VENTA: EMA Lenta Descendente"
    
    # ======================================================================
    # OPCIÓN 2: Usuario seleccionó "Máximo" → Cierra si EMA toca máximo local
    # ======================================================================
    # Si el usuario tiene el switch 'Máximo' activado en la UI para VENTA
    if getattr(strategy_self, 'ema_slow_maximo', False) and strategy_self.ema_slow_maximo_STATE:
        return True, "VENTA: Máximo en EMA Lenta"

    return False, None