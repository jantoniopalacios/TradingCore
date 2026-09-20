import numpy as np
import pandas as pd
import ta.trend
from typing import Any, Callable, Optional, Tuple


def calculate_volume_ma(volume_series: pd.Series, period: int) -> pd.Series:
    """Calcula la media móvil simple (SMA) del volumen."""
    return ta.trend.sma_indicator(volume_series, window=period)


def _last_value(values):
    """Devuelve el último valor de forma compatible con pandas, numpy y backtesting."""
    if values is None:
        return None
    try:
        return values.iloc[-1]
    except AttributeError:
        return values[-1]


def update_volume_state(strategy_self: Any, verificar_estado_indicador_func: Callable):
    """
    Actualiza los estados dinámicos de la SMA de volumen.

    Los estados ascendente/descendente representan la tendencia real de la
    V-SMA. Mínimo/máximo se calculan sobre la ventana ``volume_period``.
    """
    if not getattr(strategy_self, "volume_active", False):
        return

    volume_series = getattr(strategy_self, "volume_series", None)
    period = int(getattr(strategy_self, "volume_period", 0) or 0)
    if volume_series is None or period <= 0 or len(volume_series) <= period:
        return

    estado_volume = verificar_estado_indicador_func(volume_series)
    strategy_self.volume_ascendente_STATE = bool(estado_volume.get("ascendente", False))
    strategy_self.volume_descendente_STATE = bool(estado_volume.get("descendente", False))

    vma_window = np.asarray(volume_series[-period:], dtype=float)
    vma_actual = float(vma_window[-1])
    strategy_self.volume_minimo_STATE = bool(vma_actual == np.nanmin(vma_window))
    strategy_self.volume_maximo_STATE = bool(vma_actual == np.nanmax(vma_window))

    current_volume = _last_value(strategy_self.data.Volume)
    current_ma = _last_value(volume_series)
    if current_volume is None or current_ma is None:
        return

    umbral_nivel = float(current_ma) * float(strategy_self.volume_avg_multiplier)
    cond_nivel_valida = float(current_volume) > umbral_nivel

    volume_umbral_s = getattr(strategy_self, "volume_umbral_s", None)
    if volume_umbral_s is not None:
        volume_umbral_s[-1] = (
            float(strategy_self.volume_avg_multiplier)
            if cond_nivel_valida
            else np.nan
        )


def apply_volume_filter(strategy_self: Any) -> Tuple[bool, Optional[str]]:
    """
    Aplica el filtro de volumen como condición AND para la entrada.

    El volumen actual debe superar la V-SMA por el multiplicador configurado.
    Si hay filtros de estado seleccionados, basta con que se cumpla al menos
    uno de ellos.
    """
    if not getattr(strategy_self, "volume_active", False):
        return True, None

    volume_series = getattr(strategy_self, "volume_series", None)
    data = getattr(strategy_self, "data", None)
    volume_data = getattr(data, "Volume", None)
    if volume_series is None or volume_data is None or len(volume_data) < 1:
        return False, "Volume Faltan Datos"

    current_volume = _last_value(volume_data)
    current_ma = _last_value(volume_series)
    if current_volume is None or current_ma is None:
        return False, "Volume Faltan Datos"

    current_volume = float(current_volume)
    current_ma = float(current_ma)
    multiplier = float(getattr(strategy_self, "volume_avg_multiplier", 1.0))
    umbral_nivel = current_ma * multiplier

    if current_volume <= umbral_nivel:
        return False, f"Volumen Bajo ({int(current_volume)} < {int(umbral_nivel)})"

    state_settings = (
        ("volume_minimo", "volume_minimo_STATE"),
        ("volume_maximo", "volume_maximo_STATE"),
        ("volume_ascendente", "volume_ascendente_STATE"),
        ("volume_descendente", "volume_descendente_STATE"),
    )
    active_state_filters = [
        state_attr
        for setting_attr, state_attr in state_settings
        if bool(getattr(strategy_self, setting_attr, False))
    ]

    if active_state_filters and not any(
        bool(getattr(strategy_self, state_attr, False))
        for state_attr in active_state_filters
    ):
        return False, "Volumen No Cumple Estado"

    return True, f"Volumen Ok (x{round(current_volume / current_ma, 1)})"
