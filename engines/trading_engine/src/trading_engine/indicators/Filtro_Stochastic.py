# indicadores_tecnicos/Filtro_Stochastic.py
"""
Módulo Genérico para la lógica de Osciladores de Cruce (como Estocásticos Fast/Mid/Slow).
Contiene funciones reutilizables que son llamadas múltiples veces en el coordinador (Logica_Trading.py), 
una vez por cada versión de Estocástico (Rápido, Medio, Lento).
"""

from backtesting.lib import crossover

import ta.momentum # ¡Necesaria para el cálculo!
import pandas as pd

# ======================================================================
# --- INDICADOR AUXILIAR (HELPER) PARA SOLUCIONAR EL UNPACKING ---
# ======================================================================
class StochHelper: 
    
    # Asegúrate de que los parámetros se aceptan aquí
    def calculate(self, data, window, smooth_window): 
        
# Esto asegura que la librería 'ta' pueda usar el método .rolling()

        high_series = pd.Series(data.High)
        low_series = pd.Series(data.Low)
        close_series = pd.Series(data.Close)

        # 1. Realizar el cálculo con los parámetros dinámicos
        stoch_k_series = ta.momentum.stoch(
            high=high_series,     # Usar la serie convertida
            low=low_series,       # Usar la serie convertida
            close=close_series,   # Usar la serie convertida
            window=window, 
            smooth_window=smooth_window 
        )

# 2. Calcular la LÍNEA %D (Promedio móvil de 3 periodos de la línea %K)
        # La línea D (señal) se calcula como el promedio móvil de la línea K, 
        # usando el periodo estándar de 3.
        signal_period = 3 
        
        # 🟢 Corregido: Calculamos la línea D manualmente con un rolling mean.
        stoch_d_series = stoch_k_series.rolling(window=signal_period, min_periods=1).mean()
        
        # 3. Devolver las dos Series (K y D)
        return stoch_k_series, stoch_d_series
    
# ======================================================================
# ----------------------------------------------------------------------
# --- Actualización de Estado Genérica ---
# ----------------------------------------------------------------------
def update_oscillator_state(strategy_self, prefix, k_series, verificar_estado_indicador_func):
    """
    Actualiza el estado dinámico (STATE) de una serie de oscilador (%K).
    
    :param strategy_self: Instancia de la estrategia.
    :param prefix: Prefijo del indicador (e.g., 'stoch_fast', 'stoch_mid').
    :param k_series: Serie de datos del %K (o línea principal) del oscilador.
    :param verificar_estado_indicador_func: Función para calcular el estado dinámico.
    """
    if k_series is not None:
        estado_osc = verificar_estado_indicador_func(k_series)
        
        # Asignación dinámica al objeto strategy_self
        setattr(strategy_self, f"{prefix}_minimo_STATE", estado_osc['minimo'])
        setattr(strategy_self, f"{prefix}_maximo_STATE", estado_osc['maximo'])
        setattr(strategy_self, f"{prefix}_ascendente_STATE", estado_osc['ascendente'])
        setattr(strategy_self, f"{prefix}_descendente_STATE", estado_osc['descendente'])

# ----------------------------------------------------------------------
# --- Lógica de Compra Genérica (Señales OR) ---
# ----------------------------------------------------------------------
def check_oscillator_buy_signal(strategy_self, prefix, k_series, d_series, low_level):
    """
    Revisa la señal de compra para un Oscilador (Cruce de K sobre D, filtrado por sobreventa).
    [... parámetros omitidos por brevedad ...]
    """
    if k_series is None or d_series is None:
        return False, None
    
    # 🟢 1. RECUPERAR SETTINGS DEL USUARIO (si activó el filtro)
    ascendente_setting = getattr(strategy_self, f"{prefix}_ascendente", False)
    minimo_setting = getattr(strategy_self, f"{prefix}_minimo", False)
    
    # 2. CONDICIÓN BASE: Cruce
    buy_signal = crossover(k_series, d_series)
    
    # 3. FILTRO DE SOBREVENTA (Condición AND)
    if low_level is not None:
        buy_signal &= (k_series[-1] < low_level)
    
    # ----------------------------------------------------------
    # 🟢 4. FILTROS DE ESTADO (Condiciones AND)
    # ----------------------------------------------------------
    log_parts = []
    
    # A. Filtro Ascendente
    if ascendente_setting:
        # Recuperar el estado calculado (e.g., stoch_fast_ascendente_STATE)
        ascendente_state = getattr(strategy_self, f"{prefix}_ascendente_STATE", False)
        
        # Aplicar el filtro: solo comprar si la señal es True Y el estado es ascendente
        buy_signal |= ascendente_state
        if ascendente_state:
            log_parts.append("Ascendente")

    # B. Filtro Mínimo (Local)
    if minimo_setting:
        # Recuperar el estado calculado (e.g., stoch_fast_minimo_STATE)
        minimo_state = getattr(strategy_self, f"{prefix}_minimo_STATE", False)
        
        # Aplicar el filtro: solo comprar si la señal es True Y el estado es mínimo
        buy_signal |= minimo_state
        if minimo_state:
            log_parts.append("Mínimo")


    # 5. RETORNO FINAL
    if buy_signal:
        # Formato del log: Stoch Fast Cruce & Ascendente & Mínimo
        log_name = prefix.replace('_', ' ').title().replace('Stoch', 'Stoch') 
        
        # Añadir los filtros activados a la razón del log
        if log_parts:
            reason = f"{log_name} Cruce & {' & '.join(log_parts)}"
        else:
            reason = f"{log_name} Cruce"

        return True, reason
    
    return False, None
# ----------------------------------------------------------------------
# --- Lógica de Venta Genérica (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_oscillator_sell_signal(strategy_self, prefix):
    """
    Revisa la señal de venta de un Oscilador (Máximo o Descendente).
    
    :param strategy_self: Instancia de la estrategia.
    :param prefix: Prefijo del indicador (e.g., 'stoch_fast').
    :return: Tupla: (Booleano (señal de venta activa), Descripción del cierre (str o None)).
    """
    # Accede a los estados y settings de forma dinámica
    maximo_state = getattr(strategy_self, f"{prefix}_maximo_STATE", False)
    descendente_state = getattr(strategy_self, f"{prefix}_descendente_STATE", False)
    maximo_setting = getattr(strategy_self, f"{prefix}_maximo", False)
    descendente_setting = getattr(strategy_self, f"{prefix}_descendente", False)
    
    if (maximo_setting and maximo_state) or \
       (descendente_setting and descendente_state):
        
        log_name = prefix.replace('_', ' ').title().replace('Stoch', 'Stoch')
        return True, f"VENTA {log_name} Máximo/Descendente"
    
    return False, None