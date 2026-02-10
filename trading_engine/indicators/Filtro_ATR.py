"""
Módulo para el filtro de volatilidad basado en ATR (Average True Range).

Contiene funciones para calcular el ATR y aplicar un filtro de rango 
de volatilidad permitida [atr_min, atr_max].
"""

from typing import TYPE_CHECKING, Optional, Tuple
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('Filtro_ATR')

if TYPE_CHECKING:
    from estrategia_system import System as StrategySelf

# Helper para obtener el último valor compatible con backtesting._Indicator y pd.Series
def _last_value(series):
    try:
        return float(series.iloc[-1])
    except Exception:
        try:
            return float(series[-1])
        except Exception:
            return None

# -----------------------------------------------------------------------
# --- Cálculo de ATR ---
# -----------------------------------------------------------------------

def calculate_atr(data_df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calcula el Average True Range (ATR) basado en el período especificado.
    
    ATR es el promedio móvil exponencial (EMA) del True Range, donde:
    True Range = max(High - Low, |High - Close_anterior|, |Low - Close_anterior|)
    
    Parameters
    ----------
    data_df : pd.DataFrame
        DataFrame con columnas 'High', 'Low', 'Close'.
    period : int
        Período para la EMA del True Range (por defecto 14).
        
    Returns
    -------
    pd.Series
        Series con los valores de ATR calculados.
    """
    try:
        if period < 1:
            period = 1
            
        high = data_df['High']
        low = data_df['Low']
        close = data_df['Close']
        
        # Calcular True Range
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calcular EMA del True Range (ATR)
        atr = tr.ewm(span=period, adjust=False).mean()
        
        return atr
    except Exception as e:
        logger.error(f"Error calculando ATR: {e}")
        return pd.Series([np.nan] * len(data_df), index=data_df.index)

# -----------------------------------------------------------------------
# --- Filtro de Rango ATR ---
# -----------------------------------------------------------------------

def apply_atr_range_filter(strategy_self: 'StrategySelf') -> Tuple[bool, Optional[str]]:
    """
    Aplica un filtro de rango de volatilidad (ATR) a la entrada.
    
    Compra SOLO si el ATR actual está dentro del rango [atr_min, atr_max].
    Si ATR < atr_min: mercado sin suficiente volatilidad (poco movimiento).
    Si ATR > atr_max: mercado con volatilidad excesiva (ruido/caos).
    
    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy).
        
    Returns
    -------
    Tuple[bool, Optional[str]]
        - bool: True si el ATR está dentro del rango permitido (compra permitida).
        - str: Descripción del resultado (para logging).
    """
    try:
        # Verificar si ATR está habilitado
        if not getattr(strategy_self, 'atr_enabled', False):
            return True, None  # Filtro deshabilitado, permitir compra
        
        # Obtener parámetros
        atr_period = int(getattr(strategy_self, 'atr_period', 14))
        atr_min = float(getattr(strategy_self, 'atr_min', 2.0))
        atr_max = float(getattr(strategy_self, 'atr_max', 5.0))
        
        # Validación de parámetros
        if atr_period < 1:
            atr_period = 1
        if atr_min < 0:
            atr_min = 0
        if atr_max < atr_min:
            atr_max = atr_min + 1.0
        
        # Calcular ATR
        atr_series = calculate_atr(strategy_self.data.df, period=atr_period)
        atr_actual = _last_value(atr_series)
        
        if atr_actual is None or np.isnan(atr_actual):
            # Sin datos de ATR aún, permitir compra
            return True, None
        
        # Validaciones de rango
        permit = atr_min <= atr_actual <= atr_max
        
        # Debug logging
        fecha = strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S') if hasattr(strategy_self.data, 'index') else 'N/A'
        log_msg = f"[ATR FILTER] {fecha} | ATR={atr_actual:.2f}, Min={atr_min:.2f}, Max={atr_max:.2f}, Permite={'✓' if permit else '✗'}"
        print(log_msg)
        logger.info(log_msg)
        
        reason = None
        if permit:
            reason = f"ATR en rango [{atr_min:.2f}-{atr_max:.2f}]"
        else:
            if atr_actual < atr_min:
                reason = f"ATR {atr_actual:.2f} < Mínimo {atr_min:.2f} (poca volatilidad)"
            else:
                reason = f"ATR {atr_actual:.2f} > Máximo {atr_max:.2f} (exceso volatilidad)"
        
        return permit, reason
        
    except Exception as e:
        logger.error(f"Error en apply_atr_range_filter: {e}")
        # Error en el filtro: permitir compra para no bloquear toda la estrategia
        return True, None
