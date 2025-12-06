# indicadores_tecnicos/Filtro_RSI.py
"""
Módulo para la lógica del Índice de Fuerza Relativa (RSI).
Contiene funciones para la actualización del estado dinámico (ascendente/descendente/mínimo/máximo) 
y la generación de señales de compra/venta.
"""

from backtesting.lib import crossover
# Se asume que 'verificar_estado_indicador' será importado o pasado como argumento.

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_rsi_state(strategy_self, verificar_estado_indicador_func):
    """
    Actualiza el estado dinámico (STATE) del RSI.
    
    :param strategy_self: Instancia de la estrategia.
    :param verificar_estado_indicador_func: Función para calcular el estado dinámico.
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
def check_rsi_buy_signal(strategy_self, condicion_base_tecnica):
    """
    Revisa las señales de compra OR de RSI (Giro, Fuerza Pura).
    
    :param strategy_self: Instancia de la estrategia.
    :param condicion_base_tecnica: Condición técnica global actual (booleano).
    :return: Tupla: (Nueva condicion_base_tecnica (booleano), razón del log (str o None)).
    """
    log_reason = None
    
    if strategy_self.rsi and strategy_self.rsi_ind is not None:
        
        # Condición de Giro (Señal más fuerte: Mínimo Local + Cruce de Impulso/Threshold)
        if hasattr(strategy_self, 'rsi_threshold_ind') and strategy_self.rsi_threshold_ind is not None:
            
            # Se asume que 'rsi_minimo' es una propiedad de la estrategia que indica que se detectó un mínimo.
            cond_min_detect = strategy_self.rsi_minimo if hasattr(strategy_self, 'rsi_minimo') and strategy_self.rsi_minimo is not None else False
            cond_crossover_confirm = crossover(strategy_self.rsi_ind, strategy_self.rsi_threshold_ind)
            
            cond_rsi_giro = cond_min_detect and cond_crossover_confirm
            
            if cond_rsi_giro:
                log_reason = "RSI Giro"
            
            # Lógica de Fuerza Pura RSI (Anulación OR, se activa si hay fuerza por encima de un umbral)
            cond_rsi_pure_force = False
            if hasattr(strategy_self, 'rsi_strength_threshold') and strategy_self.rsi_strength_threshold is not None:
                # Compara el último valor del RSI con el umbral de fuerza (ej. 50 o 70)
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
def check_rsi_sell_signal(strategy_self):
    """
    Revisa la señal de venta de RSI (Máximo o Descendente).
    
    :param strategy_self: Instancia de la estrategia.
    :return: Tupla: (Booleano (señal de venta activa), Descripción del cierre (str o None)).
    """
    # Cierre si el usuario activó rsi_maximo O rsi_descendente como intención, 
    # Y el estado dinámico correspondiente se cumple.
    if (strategy_self.rsi_maximo and strategy_self.rsi_maximo_STATE) or \
       (strategy_self.rsi_descendente and strategy_self.rsi_descendente_STATE): 
        
        return True, "VENTA RSI Máximo/Descendente"
    
    return False, None