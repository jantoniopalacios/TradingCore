import pandas as pd
import numpy as np
import ta.trend 

# ----------------------------------------------------------------------
# --- CÁLCULO DE MEDIA MÓVIL (Utilizado en System.init()) ---
# ----------------------------------------------------------------------
def calculate_volume_ma(volume_series: pd.Series, period: int) -> pd.Series:
    return ta.trend.sma_indicator(volume_series, window=period)

# ----------------------------------------------------------------------
# --- Actualización de Estado (CORREGIDO) ---
# ----------------------------------------------------------------------
def update_volume_state(strategy_self, verificar_estado_indicador_func):
    """
    Actualiza el estado dinámico (STATE) del Volumen.
    Incluye lógica personalizada para Overshoot, Mínimos y Máximos usando el periodo correcto.
    """
    # Verificamos que el indicador exista y tenga datos suficientes
    if (strategy_self.volume_active and 
        hasattr(strategy_self, 'volume_series') and 
        strategy_self.volume_series is not None and 
        len(strategy_self.volume_series) > strategy_self.volume_period):
            
        # 1. Llamada Genérica (Solo para Ascendente/Descendente básico)
        # 🛑 CORRECCIÓN: Pasamos SOLO la serie, eliminando el segundo argumento que causaba el error.
        estado_volume = verificar_estado_indicador_func(strategy_self.volume_series)
        
        # Asignamos estados de tendencia básicos (pendiente de la VMA)
        strategy_self.volume_descendente_STATE = estado_volume['descendente']
        # Nota: 'ascendente' lo sobrescribiremos abajo con la lógica del Umbral/Overshoot

        # ------------------------------------------------------------
        # 2. CÁLCULO PRECISO DE MÍNIMO / MÁXIMO (Usando volume_period)
        # ------------------------------------------------------------
        # Como verificar_estado_indicador no acepta periodo, lo calculamos aquí
        # para asegurarnos de que el Min/Max corresponde a la ventana configurada.
        
        periodo = strategy_self.volume_period
        # Tomamos la ventana de la VMA (Media Móvil)
        vma_window = strategy_self.volume_series[-periodo:]
        vma_actual = strategy_self.volume_series[-1]
        
        # Es Mínimo si el valor actual es el menor de la ventana
        strategy_self.volume_minimo_STATE = (vma_actual == vma_window.min())
        
        # Es Máximo si el valor actual es el mayor de la ventana
        strategy_self.volume_maximo_STATE = (vma_actual == vma_window.max())

        # ------------------------------------------------------------
        # 3. Lógica Personalizada: UMBRAL DE VOLUMEN (Overshoot)
        # ------------------------------------------------------------
        
        # Tomamos la ventana de VOLUMEN real
        vol_window = pd.Series(strategy_self.data.Volume[-periodo:])
        # Tomamos la ventana de VMA correspondiente
        # (Convertimos a pandas Series para asegurar operaciones vectorizadas correctas)
        vma_window_series = pd.Series(strategy_self.volume_series[-periodo:])
        
        # Comparamos: ¿Volumen > VMA?
        overshoots = vol_window > vma_window_series
        
        # Contamos las veces que fue True
        count = overshoots.sum()
        strategy_self.volume_overshoot_count = count
        
        # Verificamos si supera el umbral configurado
        threshold = getattr(strategy_self, 'volume_overshoot_threshold', 0)
        cumple_umbral = count >= threshold
        
        # 🌟 Estado Ascendente = Cumple Umbral de "Fuerza" 🌟
        strategy_self.volume_ascendente_STATE = cumple_umbral
        
        # ------------------------------------------------------------
        # 4. Actualizar la serie de ploteo (Puntos Verdes)
        # ------------------------------------------------------------
        
        # 4a. Condición de NIVEL Instantáneo: ¿El volumen actual supera el multiplicador?
        current_volume = strategy_self.data.Volume[-1]
        current_ma = strategy_self.volume_series[-1]
        umbral_nivel = current_ma * strategy_self.volume_avg_multiplier
        cond_nivel_valida = current_volume > umbral_nivel
        
        # CONDICIÓN DE PLOTEO: 
        # El punto verde solo se dibuja si:
        # 1. Cumple el CONTEO de explosiones (cumple_umbral)
        # 2. El volumen de la vela actual está por encima del UMBRAL de Nivel (cond_nivel_valida)
        condicion_final_ploteo = cond_nivel_valida
        
        if condicion_final_ploteo:
             # Ploteamos exactamente en la línea roja del umbral (volume_avg_multiplier)
             strategy_self.volume_umbral_s[-1] = strategy_self.volume_avg_multiplier
        else:
             # Usamos np.nan para que el punto no se dibuje
             strategy_self.volume_umbral_s[-1] = np.nan
# ----------------------------------------------------------------------
# --- Filtro de Volumen (Condición AND) ---
# ----------------------------------------------------------------------
def apply_volume_filter(strategy_self):
    """
    Aplica el filtro de Volumen.
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
                return False, "Volumen No Cumple Estado"
            
            return True, f"Volumen Ok (x{round(current_volume/current_ma, 1)})"
        
        return True, f"Volumen Ok (x{round(current_volume/current_ma, 1)})"

    return True, None