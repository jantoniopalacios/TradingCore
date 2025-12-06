# indicadores_tecnicos/Filtro_MACD.py
"""
Módulo para la lógica de la Media Móvil de Convergencia/Divergencia (MACD).
Contiene funciones para la actualización del estado dinámico del histograma 
y la generación de señales de compra/venta basadas en cruces e impulso.
"""

from backtesting.lib import crossover
# Se asume que 'verificar_estado_indicador' será importado o pasado como argumento.

# ----------------------------------------------------------------------
# --- Actualización de Estado ---
# ----------------------------------------------------------------------
def update_macd_state(strategy_self, verificar_estado_indicador_func):
    """
    Actualiza el estado dinámico (STATE) del Histograma MACD (macd_hist).
    
    :param strategy_self: Instancia de la estrategia (accede a self.macd_hist).
    :param verificar_estado_indicador_func: Función para calcular el estado dinámico.
    """
    if strategy_self.macd and strategy_self.macd_hist is not None:
        estado_macd = verificar_estado_indicador_func(strategy_self.macd_hist)
        strategy_self.macd_minimo_STATE = estado_macd['minimo']
        strategy_self.macd_maximo_STATE = estado_macd['maximo']
        strategy_self.macd_ascendente_STATE = estado_macd['ascendente']
        strategy_self.macd_descendente_STATE = estado_macd['descendente']

# ----------------------------------------------------------------------
# --- Lógica de Compra (Señales OR) ---
# ----------------------------------------------------------------------
def check_macd_buy_signal(strategy_self, condicion_base_tecnica):
    """
    Revisa las señales de compra OR de MACD (Cruce + Impulso Creciente).
    
    :param strategy_self: Instancia de la estrategia.
    :param condicion_base_tecnica: Condición técnica global actual (booleano).
    :return: Tupla: (Nueva condicion_base_tecnica (booleano), razón del log (str o None)).
    """
    log_reason = None

    if strategy_self.macd and strategy_self.macd_hist is not None:
        
        # 1. Señal de Cruce (MACD Line sobre Signal Line)
        macd_buy = crossover(strategy_self.macd_line, strategy_self.macd_signal_line)
        
        # 2. Condición de Impulso (Histograma Creciente)
        # Lógica: Si el usuario requiere MACD ascendente (strategy_self.macd_ascendente=True), 
        # debe cumplirse el estado REAL (strategy_self.macd_ascendente_STATE).
        cond_impulso_ok = True
        if strategy_self.macd_ascendente: 
            cond_impulso_ok = strategy_self.macd_ascendente_STATE
        
        # MACD Fuerte: Cruce AND (Impulso Requerido Check)
        cond_macd_fuerte = macd_buy and cond_impulso_ok
        
        if cond_macd_fuerte:
            log_reason = "MACD Fuerte"

        condicion_base_tecnica |= cond_macd_fuerte 

    return condicion_base_tecnica, log_reason

# ----------------------------------------------------------------------
# --- Lógica de Venta (Cierre Técnico) ---
# ----------------------------------------------------------------------
def check_macd_sell_signal(strategy_self):
    """
    Revisa la señal de venta de MACD (Máximo o Descendente).
    
    :param strategy_self: Instancia de la estrategia.
    :return: Tupla: (Booleano (señal de venta activa), Descripción del cierre (str o None)).
    """
    # Cierre si el Histograma MACD indica un Máximo o se vuelve Descendente
    if (strategy_self.macd_maximo and strategy_self.macd_maximo_STATE) or \
       (strategy_self.macd_descendente and strategy_self.macd_descendente_STATE):
        
        return True, "VENTA MACD Máximo/Descendente"
    
    return False, None