# indicadores_tecnicos/Filtro_EMA.py
"""
Módulo para la lógica de la Media Móvil Exponencial (EMA).
Contiene funciones para la actualización del estado (ascendente/descendente/mínimo/máximo) 
y la generación de señales de compra/venta basadas en cruces y tendencia.
"""

from backtesting.lib import crossover
# Se asume que 'verificar_estado_indicador' está disponible a través de una importación 
# en el script principal (Logica_Trading) o en un módulo auxiliar (e.g., Calculos_Tecnicos).
# Por ahora, la referencia se mantiene, asumiendo que el script principal maneja la importación.
# from Calculos_Tecnicos import verificar_estado_indicador 

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_ema_state(strategy_self, verificar_estado_indicador_func):
    """
    Actualiza el estado dinámico (STATE) de la EMA Lenta (ma_slow).
    
    :param strategy_self: Instancia de la estrategia (accede a self.ema_slow_series).
    :param verificar_estado_indicador_func: Función para calcular el estado dinámico.
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
def check_ema_buy_signal(strategy_self, condicion_base_tecnica):
    """
    Revisa las señales de compra OR de EMA (Cruce, Mínimo o Ascendente).
    
    :param strategy_self: Instancia de la estrategia.
    :param condicion_base_tecnica: Condición técnica global actual (booleano).
    :return: Tupla: (Nueva condicion_base_tecnica (booleano), razón del log (str o None)).
    """
    log_reason = None
    
    # (A) Lógica de Cruce (Señal de Compra base OR)
    if strategy_self.ema_cruce_signal and strategy_self.ema_fast_series is not None and strategy_self.ema_slow_series is not None:
        cond_tendencia_cruce = crossover(strategy_self.ema_fast_series, strategy_self.ema_slow_series)
        if cond_tendencia_cruce:
            log_reason = "EMA Cruce"
            condicion_base_tecnica |= cond_tendencia_cruce

    # (B) Lógica de Estado (Señal de Compra OR basada en EMA Lenta)
    # 1. Señal OR: Si el usuario requiere MÍNIMO (ema_slow_minimo = True) Y el estado real es MÍNIMO.
    if strategy_self.ema_slow_minimo and strategy_self.ema_slow_minimo_STATE:
        log_reason = "EMA Lenta Minimo"
        condicion_base_tecnica = True

    # 2. Señal OR: Si el usuario requiere ASCENDENTE (ema_slow_ascendente = True) Y el estado real es ASCENDENTE.
    if strategy_self.ema_slow_ascendente and strategy_self.ema_slow_ascendente_STATE:
        log_reason = "EMA Lenta Ascendente"
        condicion_base_tecnica = True    
        
    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Filtro Global de Compra (Condición AND) ---
# ----------------------------------------------------------------------
def apply_ema_global_filter(strategy_self, condicion_base_tecnica):
    """
    Aplica los filtros globales de DENEGAR/REQUERIR de la EMA Lenta (Condición AND).
    
    :param strategy_self: Instancia de la estrategia.
    :param condicion_base_tecnica: Condición técnica global actual (booleano).
    :return: Condicion_base_tecnica modificada (booleano).
    """
    if strategy_self.ema_slow_activo:
        
        # ⚠️ Lógica de DENIEGO (Máximo o Descendente)
        if (strategy_self.ema_slow_maximo and strategy_self.ema_slow_maximo_STATE) or \
           (strategy_self.ema_slow_descendente and strategy_self.ema_slow_descendente_STATE):
            return False # DENIEGO TOTAL (AND)
            
        # ✅ Lógica de REQUERIMIENTO (Mínimo o Ascendente)
        if (strategy_self.ema_slow_minimo and not strategy_self.ema_slow_minimo_STATE) or \
           (strategy_self.ema_slow_ascendente and not strategy_self.ema_slow_ascendente_STATE):
            return False # DENIEGO por requerimiento no cumplido (AND)

    return condicion_base_tecnica

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_ema_sell_signal(strategy_self):
    """
    Revisa la señal de venta de la EMA Lenta (Descendente).
    
    :param strategy_self: Instancia de la estrategia.
    :return: Tupla: (Booleano (señal de venta activa), Descripción del cierre (str o None)).
    """
    # Cierre si el usuario activó la intención de descendente Y el estado dinámico se cumple.
    if strategy_self.ema_slow_descendente and strategy_self.ema_slow_descendente_STATE: 
        return True, "VENTA EMA Lenta Descendente (Filtro)"
    
    return False, None