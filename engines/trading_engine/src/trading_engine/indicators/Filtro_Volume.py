import pandas as pd
import numpy as np
import ta.trend 
from typing import Callable, Tuple, Optional, Any

# ----------------------------------------------------------------------
# --- CÁLCULO DE MEDIA MÓVIL (Utilizado en System.init()) ---
# ----------------------------------------------------------------------
def calculate_volume_ma(volume_series: pd.Series, period: int) -> pd.Series:
    """
    Calcula la Media Móvil Simple (SMA) para la serie de volumen.

    Esta función es utilizada durante la inicialización de la estrategia para
    crear la serie base de Volumen de Media Móvil (V-MA).

    Parameters
    ----------
    volume_series : pd.Series
        Serie de datos de volumen histórico (Volume).
    period : int
        Período (ventana) de la Media Móvil a calcular (ej. 20).

    Returns
    -------
    pd.Series
        Serie de la Media Móvil de Volumen (V-MA).
    """
    return ta.trend.sma_indicator(volume_series, window=period)

# ----------------------------------------------------------------------
# --- Actualización de Estado (CORREGIDO) ---
# ----------------------------------------------------------------------
def update_volume_state(strategy_self: Any, verificar_estado_indicador_func: Callable):
    """
    Actualiza el estado dinámico (STATE) del Volumen.

    Esta función establece estados de mínimo/máximo en la ventana configurada y, 
    de forma personalizada, define el estado **ascendente** basado en el **Umbral de Overshoot**.
    
    El estado ``volume_ascendente_STATE`` se convierte en un indicador de "fuerza"
    basado en la cantidad de veces que el volumen real ha superado a la V-MA en la ventana de período.

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia (clase Logica_Trading).
    verificar_estado_indicador_func : Callable
        Función auxiliar para calcular el estado dinámico (usada aquí solo para tendencia básica).

    Returns
    -------
    None
    """
    # Verificamos que el indicador exista y tenga datos suficientes
    if (strategy_self.volume_active and 
        hasattr(strategy_self, 'volume_series') and 
        strategy_self.volume_series is not None and 
        len(strategy_self.volume_series) > strategy_self.volume_period):
            
        # 1. Llamada Genérica (Solo para Ascendente/Descendente básico, ignorando Min/Max)
        estado_volume = verificar_estado_indicador_func(strategy_self.volume_series)
        
        # Asignamos estados de tendencia básicos (pendiente de la VMA)
        strategy_self.volume_descendente_STATE = estado_volume['descendente']
        # 'ascendente' se sobrescribe con la lógica del Umbral/Overshoot (Punto 3)

        # ------------------------------------------------------------
        # 2. CÁLCULO PRECISO DE MÍNIMO / MÁXIMO
        # ------------------------------------------------------------
        periodo = strategy_self.volume_period
        # La lógica de Min/Max usa la VMA, no el volumen crudo, como indicador de tendencia.
        vma_window = strategy_self.volume_series[-periodo:]
        vma_actual = strategy_self.volume_series[-1]
        
        strategy_self.volume_minimo_STATE = (vma_actual == vma_window.min())
        strategy_self.volume_maximo_STATE = (vma_actual == vma_window.max())

        # ------------------------------------------------------------
        # 3. Lógica Personalizada: UMBRAL DE VOLUMEN (Overshoot)
        # ------------------------------------------------------------
        # Contar cuántas veces el volumen real ha superado la V-MA en la ventana.
        vol_window = pd.Series(strategy_self.data.Volume[-periodo:])
        vma_window_series = pd.Series(strategy_self.volume_series[-periodo:])
        
        overshoots = vol_window > vma_window_series
        count = overshoots.sum()
        strategy_self.volume_overshoot_count = count
        
        threshold = getattr(strategy_self, 'volume_overshoot_threshold', 0)
        cumple_umbral = count >= threshold
        
        # 🌟 Estado Ascendente = Cumple Umbral de "Fuerza" 🌟
        strategy_self.volume_ascendente_STATE = cumple_umbral
        
        # ------------------------------------------------------------
        # 4. Actualizar la serie de ploteo (Puntos Verdes)
        # ------------------------------------------------------------
        current_volume = strategy_self.data.Volume[-1]
        current_ma = strategy_self.volume_series[-1]
        umbral_nivel = current_ma * strategy_self.volume_avg_multiplier
        cond_nivel_valida = current_volume > umbral_nivel
        
        # Condición para Ploteo: el volumen actual debe superar el multiplicador promedio.
        condicion_final_ploteo = cond_nivel_valida
        
        if condicion_final_ploteo:
            # Ploteamos en el nivel del multiplicador para visualizar el evento.
            strategy_self.volume_umbral_s[-1] = strategy_self.volume_avg_multiplier
        else:
            # Usamos np.nan para que el punto no se dibuje
            strategy_self.volume_umbral_s[-1] = np.nan

# ----------------------------------------------------------------------
# --- Filtro de Volumen (Condición AND) ---
# ----------------------------------------------------------------------
def apply_volume_filter(strategy_self: Any) -> Tuple[bool, Optional[str]]:
    """
    Aplica el filtro de Volumen como una condición AND para la entrada.

    El filtro de volumen consta de dos sub-condiciones que deben cumplirse:

    1.  **Umbral de Nivel:** El volumen de la vela actual debe superar un nivel base,
        definido por la V-MA multiplicada por ``strategy_self.volume_avg_multiplier``.
    2.  **Filtro de Estado (Opcional):** Si el usuario activa filtros de estado (Min, Max, Asc, Desc), 
        al menos uno de ellos debe cumplirse en la vela actual.

    Parameters
    ----------
    strategy_self : strategy_system.System
        Instancia de la estrategia.

    Returns
    -------
    tuple[bool, str | None]
        - bool: `True` si el filtro es válido (o inactivo), `False` si lo invalida.
        - str | None: Razón del log.
    """
    if strategy_self.volume_active:
        
        if strategy_self.volume_series is None or len(strategy_self.data.Volume) < 1:
            return False, "Volume Faltan Datos"
        
        current_volume = strategy_self.data.Volume[-1]
        current_ma = strategy_self.volume_series[-1]
        
        # 1. Condición de Umbral de Nivel (Volumen Actual > V-MA * Multiplicador)
        umbral_nivel = current_ma * strategy_self.volume_avg_multiplier
        cond_nivel_valida = current_volume > umbral_nivel
        
        if not cond_nivel_valida:
            # Falla el filtro AND si el volumen actual es bajo.
            return False, f"Volumen Bajo ({int(current_volume)} < {int(umbral_nivel)})"

        # 2. Condición de Estado
        filtros_estado_activos = (strategy_self.volume_minimo or strategy_self.volume_maximo or 
                                  strategy_self.volume_ascendente or strategy_self.volume_descendente)

        if filtros_estado_activos:
            cond_estado_cumplida = (
                (strategy_self.volume_minimo and strategy_self.volume_minimo_STATE) or 
                (strategy_self.volume_maximo and strategy_self.volume_maximo_STATE) or 
                (strategy_self.volume_ascendente and strategy_self.volume_ascendente_STATE) or 
                (strategy_self.volume_descendente and strategy_self.volume_descendente_STATE)
            )
            
            if not cond_estado_cumplida:
                # Falla el filtro AND si el nivel es ok pero el estado requerido no se cumple.
                return False, "Volumen No Cumple Estado"
            
            # Si se activaron filtros de estado Y se cumplen
            return True, f"Volumen Ok (x{round(current_volume/current_ma, 1)})"
        
        # Si NO se activaron filtros de estado, solo necesitamos el Umbral de Nivel (que ya pasó)
        return True, f"Volumen Ok (x{round(current_volume/current_ma, 1)})"

    # El filtro no está activo, por lo que la condición es TRUE por defecto.
    return True, None