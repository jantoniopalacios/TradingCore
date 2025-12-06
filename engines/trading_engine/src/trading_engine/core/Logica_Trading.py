# Logica_Trading.py

"""
El fichero Logica_Trading.py contiene las funciones centrales que definen el comportamiento y las reglas de decisión de la 
estrategia de backtesting System.

ACTUALIZACIÓN: Este módulo ahora actúa como COORDINADOR, delegando la lógica específica de cada indicador 
a los módulos de la carpeta 'indicadores_tecnicos' para mejorar la modularidad y el mantenimiento.
"""

from backtesting.lib import crossover
import pandas as pd
import numpy as np
# Importación del módulo auxiliar para los estados
from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador 

# --- NUEVAS IMPORTACIONES DE MÓDULOS ---
# Importamos la lógica de cada indicador
from trading_engine.indicators.Filtro_EMA import update_ema_state, check_ema_buy_signal, apply_ema_global_filter, check_ema_sell_signal
from trading_engine.indicators.Filtro_RSI import update_rsi_state, check_rsi_buy_signal, check_rsi_sell_signal
from trading_engine.indicators.Filtro_MACD import update_macd_state, check_macd_buy_signal, check_macd_sell_signal
from trading_engine.indicators.Filtro_Stochastic import update_oscillator_state, check_oscillator_buy_signal, check_oscillator_sell_signal
from trading_engine.indicators.Filtro_MoS import update_mos_state, apply_mos_filter
from trading_engine.indicators.Filtro_Volume import update_volume_state, apply_volume_filter

# ----------------------------------------------------------------------
# --- FUNCIONES AUXILIARES PARA LOGS ---
# ----------------------------------------------------------------------

def _log_trade_action_sl_update(strategy_self, old_sl, new_sl):
    # (El contenido de esta función no cambia y se mantiene igual que en la versión anterior)
    
    """
    Descripción: Función auxiliar para registrar específicamente la actualización del Stop Loss dinámico (Trailing Stop) dentro 
    del log de operaciones (strategy_self.trades_list).
    ...
    """
    strategy_self.trades_list.append({
        "Symbol": strategy_self.ticker, 
        "Tipo": "ACT_SL", 
        "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
        # --- Datos de Trade CERRADO (Log de SL) ---
        "Precio_Entrada": "N/A", 
        "Stop_Loss_Inicial": round(old_sl, 2), # El SL anterior
        "Precio_Salida": "N/A",
        "Resultado": "N/A",
        # --- Métricas Financieras (N/A) ---
        "PnL_Absoluto": "N/A",
        "Retorno_Pct": "N/A",
        "Comision_Total": "N/A",
        # --- Datos de Log Personalizado (N/A) ---
        "Descripcion": "N/A", 
        "Fecha de operacion": "N/A",
        "Precio": "N/A", 
        "Stop_loss": "N/A", 
        # --- Datos de ACT_SL ---
        "Nuevo_SL": round(new_sl, 2), # El nuevo SL
    })


# ----------------------------------------------------------------------
# --- CÁLCULO DE ESTADOS DE INDICADORES (FUNCIÓN CENTRALIZADA Y DELEGADA) ---
# ----------------------------------------------------------------------

def _actualizar_estados_indicadores(strategy_self):
    """
    Función crucial que se ejecuta en cada ciclo de next().
    DELEGA el cálculo y actualización de los estados dinámicos a los módulos de indicadores.

    Rol: Coordinación del Análisis Técnico.
    """
    
    # 1. EMA
    update_ema_state(strategy_self, verificar_estado_indicador)
    
    # 2. RSI
    if strategy_self.rsi:
        update_rsi_state(strategy_self, verificar_estado_indicador)

    # 3. MACD
    if strategy_self.macd:
        update_macd_state(strategy_self, verificar_estado_indicador)

    # 4. Margen de Seguridad (MoS)
    if strategy_self.margen_seguridad_active:
        update_mos_state(strategy_self, verificar_estado_indicador)

    # 5. Stochastic (Fast, Mid, Slow) - Usando la función genérica
    if strategy_self.stoch_fast:
        update_oscillator_state(strategy_self, 'stoch_fast', strategy_self.stoch_k_fast, verificar_estado_indicador)
        
    if strategy_self.stoch_mid:
        update_oscillator_state(strategy_self, 'stoch_mid', strategy_self.stoch_k_mid, verificar_estado_indicador)

    if strategy_self.stoch_slow:
        update_oscillator_state(strategy_self, 'stoch_slow', strategy_self.stoch_k_slow, verificar_estado_indicador)

    # 6. VOLUMEN
    if strategy_self.volume_active:
        # Llama a la función que calcula los estados dinámicos (Min/Max/Asc/Desc) de la V-MA
        update_volume_state(strategy_self, verificar_estado_indicador)


# ----------------------------------------------------------------------
# --- LÓGICA DE APERTURA (COMPRA) ---
# ----------------------------------------------------------------------

def check_buy_signal(strategy_self):
    """
    Revisa las condiciones de COMPRA combinando todos los filtros activos.

    Rol: Decisión de Compra (Coordinación de Señales OR y Filtros AND).
    """
    if strategy_self.position:
            return 

    # 1. CALCULAR Y ACTUALIZAR ESTADOS
    _actualizar_estados_indicadores(strategy_self)

    # Condición principal de compra: se activa con OR entre señales fuertes
    condicion_base_tecnica = False
    technical_reasons = {} 
        
    # ----------------------------------------------------------------------
    # --- 1. FILTROS DE SEÑAL (Lógica OR) ---
    # ----------------------------------------------------------------------

    # A. EMA
    condicion_base_tecnica, log_reason_ema = check_ema_buy_signal(strategy_self, condicion_base_tecnica)
    if log_reason_ema:
        technical_reasons['EMA'] = log_reason_ema

    # B. RSI
    if strategy_self.rsi:
        condicion_base_tecnica, log_reason_rsi = check_rsi_buy_signal(strategy_self, condicion_base_tecnica)
        if log_reason_rsi:
            technical_reasons['RSI'] = log_reason_rsi

    # C. MACD
    if strategy_self.macd:
        condicion_base_tecnica, log_reason_macd = check_macd_buy_signal(strategy_self, condicion_base_tecnica)
        if log_reason_macd:
            technical_reasons['MACD'] = log_reason_macd

    # D. STOCHASTIC (Usando la función genérica)
    log_reason_stoch = None
    if strategy_self.stoch_fast:
        stoch_buy, reason = check_oscillator_buy_signal(strategy_self, 'stoch_fast', strategy_self.stoch_k_fast, strategy_self.stoch_d_fast, strategy_self.stoch_fast_low_level)
        if stoch_buy:
            condicion_base_tecnica = True
            log_reason_stoch = reason
    
    if strategy_self.stoch_mid and log_reason_stoch is None:
        stoch_buy, reason = check_oscillator_buy_signal(strategy_self, 'stoch_mid', strategy_self.stoch_k_mid, strategy_self.stoch_d_mid, strategy_self.stoch_mid_low_level)
        if stoch_buy:
            condicion_base_tecnica = True
            log_reason_stoch = reason

    if strategy_self.stoch_slow and log_reason_stoch is None:
        stoch_buy, reason = check_oscillator_buy_signal(strategy_self, 'stoch_slow', strategy_self.stoch_k_slow, strategy_self.stoch_d_slow, strategy_self.stoch_slow_low_level)
        if stoch_buy:
            condicion_base_tecnica = True
            log_reason_stoch = reason
            
    if log_reason_stoch:
        technical_reasons['Stoch'] = log_reason_stoch


    # ----------------------------------------------------------------------
    # --- 2. FILTRO GLOBAL EMA LENTA (Condición AND) ---
    # ----------------------------------------------------------------------
    
    condicion_base_tecnica = apply_ema_global_filter(strategy_self, condicion_base_tecnica)

    # ----------------------------------------------------------------------
    # --- 3. VERIFICACIÓN DE MODO BUY & HOLD (COMPRA SIN FILTROS) ---
    # ----------------------------------------------------------------------
    indicadores_tecnicos_activos = (
        strategy_self.ema_cruce_signal or
        strategy_self.rsi or 
        strategy_self.macd or 
        strategy_self.stoch_fast or 
        strategy_self.stoch_mid or 
        strategy_self.stoch_slow
    )
    if not condicion_base_tecnica:
        # Si NO hay indicadores activos y la condición base es False (es decir, el usuario quiere Buy & Hold con filtro mínimo)
        if not indicadores_tecnicos_activos:
            # La compra se activa solo si la EMA Lenta está en un estado favorable (mínimo o ascendente).
            condicion_base_tecnica = strategy_self.ema_slow_minimo_STATE or strategy_self.ema_slow_ascendente_STATE
            if condicion_base_tecnica:
                technical_reasons['B&H'] = "B&H Mínimo"

    # ----------------------------------------------------------------------
    # --- 4. FILTRO DE VOLUMEN (Condición AND Excluyente) 
    # ----------------------------------------------------------------------
    # El filtro de Volumen es una condición AND: DEBE cumplirse para continuar.
    volume_condition_met, volume_log_reason = apply_volume_filter(strategy_self)
    
    if not volume_condition_met:
        # Si el volumen es un filtro activo y falla, abortamos la señal de compra
        # (Opcional: puedes registrar el 'volume_log_reason' aquí antes de salir)
        return
    
    # Si pasa el filtro de volumen, añadimos la razón de log a la lista de registros
    if volume_log_reason:
        technical_reasons['Volume'] = volume_log_reason # Usamos technical_reasons o creamos una sección de Filtros

    # ----------------------------------------------------------------------
    # --- 5. FILTRO FUNDAMENTAL (Margen de Seguridad - Condición AND) ---
    # ----------------------------------------------------------------------
    
    cond_mos_valida, mos_log_reason = apply_mos_filter(strategy_self)

    # Si MoS está activo y no es válido, salimos de la función de compra
    if strategy_self.margen_seguridad_active and not cond_mos_valida:
        # Aquí puedes registrar el fallo del filtro fundamental
        return
    
    # ----------------------------------------------------------------------
    # --- 6. DECISIÓN FINAL DE COMPRA ---
    # ----------------------------------------------------------------------
    
    # Compra si: (Señal Técnica Fuerte) AND (Condición Fundamental Válida)
    if condicion_base_tecnica and cond_mos_valida:
        
        strategy_self.buy()
        # 1. El precio máximo inicial debe ser el precio de entrada (Close[-1]).
        strategy_self.max_price = strategy_self.data.Close[-1]
        
        # 2. El Stop Loss inicial DEBE calcularse usando el parámetro del usuario.
        strategy_self.my_stop_loss = strategy_self.max_price * (1 - strategy_self.stoploss_percentage_below_close)

        # 🌟 REGISTRO DE COMPRA DETALLADO 🌟
        log_parts = []

        # --- 1. Razones Técnicas ---
        if technical_reasons:
            clean_reasons = [v for k, v in technical_reasons.items() if v]
            log_parts.append("Tecnica: " + " & ".join(clean_reasons))

        # --- 2. Razón Fundamental (MOS) ---
        if mos_log_reason:
            log_parts.append(mos_log_reason)

        # Compilar la descripción final
        descripcion_adicional = " (" + " | ".join(log_parts) + ")" if log_parts else ""
        descripcion_compra = "COMPRA" + descripcion_adicional
        
        strategy_self.trades_list.append({
            "Symbol": strategy_self.ticker, 
            "Tipo": "COMPRA",
            "Fecha": "N/A", 
            "Precio_Entrada": "N/A", 
            "Stop_Loss_Inicial": "N/A", 
            "Precio_Salida": "N/A", 
            "Resultado": "N/A",
            "PnL_Absoluto": "N/A", 
            "Retorno_Pct": "N/A", 
            "Comision_Total": "N/A", 
            "Descripcion": descripcion_compra, 
            "Fecha de operacion": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            "Precio": round(strategy_self.data.Close[-1], 2), 
            "Stop_loss": round(strategy_self.my_stop_loss, 2), 
            "Nuevo_SL": "N/A",
        })

# ----------------------------------------------------------------------
# --- LÓGICA DE CIERRE (VENTA) ---
# ----------------------------------------------------------------------

def manage_existing_position(strategy_self):
    """
    Gestiona el cierre de la posición (cierre técnico o stop-loss dinámico).

    Rol: Decisión de Venta (Coordinación de Cierres Técnicos OR).
    """
    if not strategy_self.position:
        return 
        
    # 1. CALCULAR Y ACTUALIZAR ESTADOS
    _actualizar_estados_indicadores(strategy_self)

    close_position = False
    descripcion_cierre = "N/A"
    
    # ----------------------------------------------------------------------
    # --- LÓGICA DE CONTROL (VERIFICA SI HAY FILTROS ACTIVOS) ---
    # ----------------------------------------------------------------------
    indicadores_tecnicos_activos = (
        strategy_self.ema_cruce_signal or
        (strategy_self.ema_slow_activo) or
        strategy_self.rsi or
        strategy_self.macd or
        strategy_self.stoch_fast or
        strategy_self.stoch_mid or
        strategy_self.stoch_slow
    )

    if indicadores_tecnicos_activos:
        # ----------------------------------------------------------------------
        # --- LÓGICA DE CIERRE TÉCNICO (OR entre señales de VENTA) ---
        # ----------------------------------------------------------------------
        
        # 1. Filtro de Tendencia (EMA Lenta)
        close_position_ema, desc_ema = check_ema_sell_signal(strategy_self)
        if close_position_ema:
            close_position = True
            descripcion_cierre = desc_ema

        # 2. RSI
        if not close_position:
            close_position_rsi, desc_rsi = check_rsi_sell_signal(strategy_self)
            if close_position_rsi:
                close_position = True
                descripcion_cierre = desc_rsi

        # 3. MACD
        if not close_position:
            close_position_macd, desc_macd = check_macd_sell_signal(strategy_self)
            if close_position_macd:
                close_position = True
                descripcion_cierre = desc_macd

        # 4. ESTOCÁSTICOS (Usa la función genérica y comprueba los tres)
        if not close_position:
            # Aunque la función genérica comprueba los tres internamente, es más limpio 
            # delegar la verificación y priorizar la señal más sensible (Fast, Mid, Slow)
            
            # Fast
            close_position_stoch_fast, desc_stoch_fast = check_oscillator_sell_signal(strategy_self, 'stoch_fast')
            if close_position_stoch_fast:
                close_position = True
                descripcion_cierre = desc_stoch_fast

            # Mid
            elif strategy_self.stoch_mid:
                close_position_stoch_mid, desc_stoch_mid = check_oscillator_sell_signal(strategy_self, 'stoch_mid')
                if close_position_stoch_mid:
                    close_position = True
                    descripcion_cierre = desc_stoch_mid
            
            # Slow
            elif strategy_self.stoch_slow:
                close_position_stoch_slow, desc_stoch_slow = check_oscillator_sell_signal(strategy_self, 'stoch_slow')
                if close_position_stoch_slow:
                    close_position = True
                    descripcion_cierre = desc_stoch_slow
            
            
    # ----------------------------------------------------------------------
    # --- CIERRE Y REGISTRO TÉCNICO ---
    # ----------------------------------------------------------------------
    
    if close_position:
        # Si se cumple alguna condición de cierre técnico, cerramos la posición aquí
        strategy_self.position.close()
        
        # ... (El resto del log y reseteo de variables se mantiene igual)
        trade_obj = strategy_self.trades[-1] if strategy_self.trades else None
        
        # Reseteo de variables de la estrategia
        strategy_self.max_price = 0
        strategy_self.my_stop_loss = None
        
        # 🌟 REGISTRO DE VENTA TÉCNICA 🌟
        strategy_self.trades_list.append({
            "Symbol": strategy_self.ticker, 
            "Tipo": descripcion_cierre, # Usamos la descripción del motivo
            "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            "Precio_Entrada": round(trade_obj.entry_price, 4) if trade_obj and trade_obj.entry_price is not None else "N/A",
            "Stop_Loss_Inicial": "N/A", 
            "Precio_Salida": round(trade_obj.exit_price, 4) if trade_obj and trade_obj.exit_price is not None else round(strategy_self.data.Close[-1], 4),
            "Resultado": "Cerrada",
            "PnL_Absoluto": round(trade_obj.pl, 2) if trade_obj and trade_obj.pl is not None else "N/A", 
            "Retorno_Pct": round(trade_obj.pl_pct * 100, 2) if trade_obj and trade_obj.pl_pct is not None else "N/A", 
            "Comision_Total": round(trade_obj._commissions, 2) if trade_obj and trade_obj._commissions is not None else "N/A",
            "Descripcion": "Cierre tecnico", # Indicamos que fue un cierre técnico
            "Fecha de operacion": "N/A", 
            "Precio": "N/A", 
            "Stop_loss": "N/A", 
            "Nuevo_SL": "N/A",
        })
        
        return 
        
    # ----------------------------------------------------------------------
    # --- GESTIÓN DE STOP LOSS DINÁMICO (Trailing Stop) ---
    # ----------------------------------------------------------------------
    current_high = strategy_self.data.High[-1]
    strategy_self.max_price = max(strategy_self.max_price, current_high)
    
    # Calcular el nuevo SL
    new_stop_loss = strategy_self.max_price * (1 - strategy_self.stoploss_percentage_below_close)

    # Actualiza el SL solo si ha subido (trailing)
    if strategy_self.my_stop_loss is None or new_stop_loss > strategy_self.my_stop_loss:
        old_stop_loss = strategy_self.my_stop_loss
        strategy_self.my_stop_loss = new_stop_loss
        
        # Registrar la actualización del SL
        _log_trade_action_sl_update(strategy_self, old_stop_loss, new_stop_loss)


    # Cierre por Stop Loss
    if strategy_self.my_stop_loss is not None and strategy_self.data.Close[-1] < strategy_self.my_stop_loss:
        # ... (El resto del log por Stop Loss se mantiene igual)
        strategy_self.position.close()
        
        final_stop_loss = strategy_self.my_stop_loss
        trade_obj = strategy_self.trades[-1] if strategy_self.trades else None
        
        # Reseteo de variables de la estrategia
        strategy_self.max_price = 0
        strategy_self.my_stop_loss = None
        
        # 🌟 REGISTRO DE VENTA POR STOP LOSS 🌟
        strategy_self.trades_list.append({
            "Symbol": strategy_self.ticker, 
            "Tipo": "VENTA StopLoss", 
            "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            "Precio_Entrada": round(trade_obj.entry_price, 4) if trade_obj and trade_obj.entry_price is not None else "N/A",
            "Stop_Loss_Inicial": round(final_stop_loss, 2) if final_stop_loss else "N/A", 
            "Precio_Salida": round(trade_obj.exit_price, 4) if trade_obj and trade_obj.exit_price is not None else round(strategy_self.data.Close[-1], 4),
            "Resultado": "Cerrada",
            "PnL_Absoluto": round(trade_obj.pl, 2) if trade_obj and trade_obj.pl is not None else "N/A", 
            "Retorno_Pct": round(trade_obj.pl_pct * 100, 2) if trade_obj and trade_obj.pl_pct is not None else "N/A", 
            "Comision_Total": round(trade_obj._commissions, 2) if trade_obj and trade_obj._commissions is not None else "N/A",
            "Descripcion": "N/A", 
            "Fecha de operacion": "N/A", 
            "Precio": "N/A", 
            "Stop_loss": "N/A", 
            "Nuevo_SL": "N/A",
        })