"""
Módulo para la lógica del Índice de Fuerza Relativa (RSI).

Contiene funciones delegadas para la actualización del estado dinámico (ascendente/descendente/mínimo/máximo) 
del RSI y la generación de señales de compra/venta basadas en giros y niveles de fuerza.
"""

from backtesting.lib import crossover
from typing import TYPE_CHECKING, Callable, Tuple, Optional
import pandas as pd

# Helper para obtener el último valor compatible con backtesting._Indicator y pd.Series
def _last_value(series):
    try:
        return float(series.iloc[-1])
    except Exception:
        try:
            return float(series[-1])
        except Exception:
            return None

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
    try:
        if strategy_self.rsi and strategy_self.rsi_ind is not None:
            estado_rsi = verificar_estado_indicador_func(strategy_self.rsi_ind)
            strategy_self.rsi_minimo_STATE = estado_rsi['minimo']
            strategy_self.rsi_maximo_STATE = estado_rsi['maximo']
            strategy_self.rsi_ascendente_STATE = estado_rsi['ascendente']
            strategy_self.rsi_descendente_STATE = estado_rsi['descendente']
        else:
            # Si RSI no está activo o no hay datos, initializar estados en False
            strategy_self.rsi_minimo_STATE = False
            strategy_self.rsi_maximo_STATE = False
            strategy_self.rsi_ascendente_STATE = False
            strategy_self.rsi_descendente_STATE = False
    except Exception as e:
        # Error en actualización de estado: inicializar en False para no bloquear
        strategy_self.rsi_minimo_STATE = False
        strategy_self.rsi_maximo_STATE = False
        strategy_self.rsi_ascendente_STATE = False
        strategy_self.rsi_descendente_STATE = False
        # Log silencioso del error (no rompe la estrategia)

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ─────────────────────────────────────────────────────────────────────────────
def check_rsi_buy_signal(strategy_self: 'StrategySelf', condicion_base_tecnica: bool) -> Tuple[bool, Optional[str]]:
    """
    Revisa las señales de compra (lógica OR) generadas por el RSI.
    
    Dos tipos de señales:
    1. GIRO DESDE SOBREVENTA: RSI estaba bajo y cruza su nivel mínimo al alza
    2. RSI ASCENDENTE: RSI está subiendo (momentum alcista)
    
    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia con RSI y configuraciones.
    condicion_base_tecnica : bool
        Condición técnica global actual.

    Returns
    -------
    tuple
        - bool: Nueva `condicion_base_tecnica` (True si se activó una señal OR).
        - Optional[str]: Razón del log de la señal activada, o None.
    """
    log_reason = None
    
    if strategy_self.rsi and strategy_self.rsi_ind is not None:
        
        # Obtener valor actual del RSI (compatible con backtesting._Indicator y pd.Series)
        rsi_actual = _last_value(strategy_self.rsi_ind)
        
        # ════════════════════════════════════════════════════════════════════════════
        # OPCIÓN 1: COMPRA POR GIRO DESDE SOBREVENTA (Cruce al alza del bajo_level)
        # ════════════════════════════════════════════════════════════════════════════
        if getattr(strategy_self, 'rsi_minimo', False):
            # Si el usuario activó que quiere comprar en mínimos (sobreventa)
            # Verificar si el RSI está en estado de mínimo Y si cruza hacia arriba
            
            if hasattr(strategy_self, 'rsi_minimo_STATE') and strategy_self.rsi_minimo_STATE:
                # RSI está en mínimo local
                if hasattr(strategy_self, 'rsi_threshold_ind') and strategy_self.rsi_threshold_ind is not None:
                    # Hay threshold definido, verificar cruce
                    cond_crossover = crossover(strategy_self.rsi_ind, strategy_self.rsi_threshold_ind)
                    if cond_crossover and (rsi_actual is not None and rsi_actual > float(strategy_self.rsi_low_level)):
                        log_reason = "RSI Giro desde Sobreventa"
                        condicion_base_tecnica = True
                else:
                    # Sin threshold, solo detección de mínimo
                    if (rsi_actual is not None and rsi_actual > float(strategy_self.rsi_low_level)):  # RSI saliendo de sobreventa
                        log_reason = "RSI Giro desde Sobreventa"
                        condicion_base_tecnica = True
        
        # ════════════════════════════════════════════════════════════════════════════
        # OPCIÓN 2: COMPRA POR RSI ASCENDENTE
        # ════════════════════════════════════════════════════════════════════════════
        if getattr(strategy_self, 'rsi_ascendente', False):
            # Si el usuario activó que quiere comprar cuando RSI está ascendente
            if hasattr(strategy_self, 'rsi_ascendente_STATE') and strategy_self.rsi_ascendente_STATE:
                if log_reason is None:  # No sobrescribir si ya hay razón anterior
                    log_reason = "RSI Ascendente"
                condicion_base_tecnica = True
    
    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_rsi_sell_signal(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Revisa la señal de venta de cierre técnico basada en el estado del RSI.

    La señal de venta se activa si:
    - RSI alcanza máximo local (sobrecompra) y el usuario lo activó
    - RSI está descendiendo y el usuario lo activó
    
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
    
    # Verificar si alguno de los deniegos está activo
    if strategy_self.rsi:
        # Inicializar estados si no existen (defensivo)
        maximo_state = getattr(strategy_self, 'rsi_maximo_STATE', False)
        descendente_state = getattr(strategy_self, 'rsi_descendente_STATE', False)
        
        # Cierre si RSI alcanza máximo (sobrecompra)
        if getattr(strategy_self, 'rsi_maximo', False) and maximo_state:
            return True, "VENTA RSI Máximo (Sobrecompra)"
        
        # Cierre si RSI desciende
        if getattr(strategy_self, 'rsi_descendente', False) and descendente_state:
            return True, "VENTA RSI Descendente"
    
    return False, None

# ----------------------------------------------------------------------
# --- Filtro Global de Fuerza (Bloqueo) ---
# ----------------------------------------------------------------------
def apply_rsi_global_filter(strategy_self: 'StrategySelf') -> bool:
    """
    Filtro global de RSI: FUERZA PURA.
    
    Bloquea TODAS las compras si RSI está por debajo del umbral de fuerza.
    Similar al veto hardcoded de EMA descendente, pero basado en nivel absoluto.
    
    Este filtro está SIEMPRE ACTIVO cuando RSI está activado (no requiere switch).
    EXCEPCIÓN: Si Umbral = 0 o no configurado, el filtro se desactiva completamente.
    
    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la estrategia con RSI.

    Returns
    -------
    bool
        False si RSI < threshold (BLOQUEA compras)
        True en caso contrario (permite compras)
    """
    # Si RSI no está activado, no bloquear
    if not strategy_self.rsi:
        return True
        
    if strategy_self.rsi_ind is not None:
        # Verificar si el umbral está configurado
        if hasattr(strategy_self, 'rsi_strength_threshold'):
            umbral_raw = strategy_self.rsi_strength_threshold
            
            # Si el umbral es None o vacío, desactivar el filtro
            if umbral_raw is None or umbral_raw == '':
                return True
            
            try:
                umbral = float(umbral_raw)
                
                # Si umbral es 0 o negativo, desactivar el filtro COMPLETAMENTE
                if umbral <= 0:
                    return True  # Permite todas las compras
                
                # Aplicar filtro de Fuerza Pura solo si umbral > 0
                rsi_actual = _last_value(strategy_self.rsi_ind)
                if rsi_actual is not None and rsi_actual < umbral:
                    # RSI por debajo del umbral de fuerza → BLOQUEO
                    return False
            except (ValueError, TypeError):
                # Si hay error de conversión, no bloquear
                return True
    
    return True  # Permite la operación