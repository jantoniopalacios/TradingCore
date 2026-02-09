"""
El fichero Logica_Trading.py contiene las funciones centrales que definen el comportamiento y las reglas de decisión de la 
estrategia de backtesting System.

ACTUALIZACIÓN: Este módulo ahora actúa como COORDINADOR, delegando la lógica específica de cada indicador 
a los módulos de la carpeta 'indicators' para mejorar la modularidad y el mantenimiento.
"""

from backtesting.lib import crossover
import pandas as pd
import numpy as np

# Importación del módulo auxiliar para los estados
from trading_engine.utils.Calculos_Tecnicos import verificar_estado_indicador 

# --- NUEVAS IMPORTACIONES DE MÓDULOS (Lógica Delegada) ---
from trading_engine.indicators.Filtro_EMA import update_ema_state, check_ema_buy_signal, apply_ema_global_filter, check_ema_sell_signal
from trading_engine.indicators.Filtro_RSI import update_rsi_state, check_rsi_buy_signal, apply_rsi_global_filter, check_rsi_sell_signal
from trading_engine.indicators.Filtro_MACD import update_macd_state, check_macd_buy_signal, check_macd_sell_signal
from trading_engine.indicators.Filtro_Stochastic import update_oscillator_state, check_oscillator_buy_signal, check_oscillator_sell_signal
from trading_engine.indicators.Filtro_MoS import update_mos_state, apply_mos_filter
from trading_engine.indicators.Filtro_Volume import update_volume_state, apply_volume_filter

# 🟢 NUEVA IMPORTACIÓN: Bandas de Bollinger
from trading_engine.indicators.Filtro_BollingerBands import update_bb_state, check_bb_buy_signal, check_bb_sell_signal

# Importación para tipado (asumiendo que System es la clase que se usa como self)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from estrategia_system import System as StrategySelf 

# ----------------------------------------------------------------------
# --- FUNCIONES AUXILIARES PARA LOGS ---
# ----------------------------------------------------------------------
import logging
logger = logging.getLogger('Logica_Trading')

def _log_trade_action_sl_update(strategy_self: 'StrategySelf', old_sl: float, new_sl: float) -> None:
    """
    Función auxiliar para registrar la actualización del Stop Loss dinámico (Trailing Stop) 
    en la lista de operaciones de la estrategia (`strategy_self.trades_list`).

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy) del backtest.
    old_sl : float
        Valor anterior del Stop Loss antes de la actualización.
    new_sl : float
        Nuevo valor (mayor) del Stop Loss después de la actualización.
        
    Returns
    -------
    None
    """
    strategy_self.trades_list.append({
        "Symbol": strategy_self.ticker, 
        "Tipo": "ACT_SL", 
        "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
        # --- Datos de Trade CERRADO (Log de SL) ---
        "Precio_Entrada": "N/A", 
        "Stop_Loss_Inicial": round(old_sl, 2) if old_sl is not None else "N/A", # El SL anterior
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

def _actualizar_estados_indicadores(strategy_self: 'StrategySelf') -> None:
    """
    Función crucial que se ejecuta en cada ciclo de next(). Delega el cálculo y 
    actualización de los estados dinámicos (`_STATE`) a los módulos de indicadores.

    Este proceso centralizado asegura que todos los estados se calculen antes de 
    la toma de decisiones de compra o venta en el mismo ciclo (barra de precio).

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy).
        
    Returns
    -------
    None
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
        update_volume_state(strategy_self, verificar_estado_indicador)
        
    # 🟢 7. BOLLINGER BANDS (BB)
    if strategy_self.bb_active:
        update_bb_state(strategy_self, verificar_estado_indicador)


# ----------------------------------------------------------------------
# --- LÓGICA DE APERTURA (COMPRA) ---
# ----------------------------------------------------------------------

def check_buy_signal(strategy_self: 'StrategySelf') -> None:
    """
    Revisa las condiciones de COMPRA combinando todos los filtros activos (AND y OR).

    Esta es la función principal de entrada que orquesta la lógica:
    1. Calcula/actualiza los estados de todos los indicadores.
    2. Evalúa las señales de entrada (lógica OR entre indicadores).
    3. Aplica los filtros globales excluyentes (lógica AND).
    4. Ejecuta la compra y establece el Stop Loss inicial si la señal es válida.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy).

    Returns
    -------
    None
        La función ejecuta la orden de compra si las condiciones se cumplen 
        (a través de `strategy_self.buy()`).
    """
    if strategy_self.position:
        # Ya hay una posición abierta, no hay señal de compra.
        return 

    # 1. CALCULAR Y ACTUALIZAR ESTADOS
    _actualizar_estados_indicadores(strategy_self)

    # DEBUG: Log de estados de indicadores (útil para diagnosticar por qué no hay trades)
    try:
        # Protector para obtener último valor compatible con backtesting._Indicator
        rsi_val = None
        try:
            rsi_val = getattr(strategy_self, 'rsi_ind', None)
            if rsi_val is not None:
                try:
                    rsi_val = rsi_val.iloc[-1]
                except Exception:
                    rsi_val = rsi_val[-1]
        except Exception:
            rsi_val = None
        logger.debug(f"DEBUG STATES | Ticker={getattr(strategy_self,'ticker', 'UNK')} | RSI_active={getattr(strategy_self,'rsi', False)} | RSI_minimo_FLAG={getattr(strategy_self,'rsi_minimo', False)} | RSI_minimo_STATE={getattr(strategy_self,'rsi_minimo_STATE', False)} | RSI_actual={rsi_val}")
    except Exception:
        logger.debug("DEBUG STATES | could not print RSI values")

    # Condición principal de compra: se activa con OR entre señales fuertes
    condicion_base_tecnica = False
    technical_reasons = {} 
        
    # ----------------------------------------------------------------------
    # --- 1. FILTROS DE SEÑAL (Lógica OR) ---
    # ----------------------------------------------------------------------

    # Delegación de chequeos de compra (OR Lógica)
    condicion_base_tecnica, log_reason_ema = check_ema_buy_signal(strategy_self, condicion_base_tecnica)
    if log_reason_ema: technical_reasons['EMA'] = log_reason_ema

    if strategy_self.rsi:
        condicion_base_tecnica, log_reason_rsi = check_rsi_buy_signal(strategy_self, condicion_base_tecnica)
        if log_reason_rsi: technical_reasons['RSI'] = log_reason_rsi

    if strategy_self.macd:
        condicion_base_tecnica, log_reason_macd = check_macd_buy_signal(strategy_self, condicion_base_tecnica)
        if log_reason_macd: technical_reasons['MACD'] = log_reason_macd

    # STOCHASTIC (Manejo de Fast/Mid/Slow con OR prioritario)
    log_reason_stoch = None
    # Prioridad: Fast > Mid > Slow
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
            
    if log_reason_stoch: technical_reasons['Stoch'] = log_reason_stoch

    # 🟢 BOLLINGER BANDS (BB) - Lógica Flexible (Cruce o Toque)
    if getattr(strategy_self, 'bb_active', False):
        # CASO 1: Si bb_buy_crossover es False, compramos por simple "Toque" (Precio < Banda)
        if not getattr(strategy_self, 'bb_buy_crossover', True):
            precio_actual = strategy_self.data.Close[-1]
            banda_inf = strategy_self.bb_lower_band_series[-1]
            
            if precio_actual < banda_inf:
                condicion_base_tecnica = True
                # Usamos el formato detallado para que el log sea útil
                technical_reasons['BB'] = f"Sobreventa (Precio {precio_actual:.2f} < {banda_inf:.2f})"
        
        # CASO 2: Si bb_buy_crossover es True, usamos la lógica de cruce (original)
        else:
            condicion_base_tecnica, log_reason_bb = check_bb_buy_signal(strategy_self, condicion_base_tecnica)
            if log_reason_bb:
                technical_reasons['BB'] = log_reason_bb


    # ----------------------------------------------------------------------
    # --- 2. FILTRO GLOBAL EMA LENTA (Condición AND) ---
    # ----------------------------------------------------------------------
    
    # Este filtro puede anular una señal de compra si la tendencia es muy desfavorable.
    condicion_base_tecnica = apply_ema_global_filter(strategy_self, condicion_base_tecnica)

    # ----------------------------------------------------------------------
    # --- 3. FILTRO GLOBAL RSI FUERZA PURA (Condición AND) ---
    # ----------------------------------------------------------------------
    
    # Bloquea compras si RSI está por debajo del umbral de fuerza (calidad insuficiente).
    # Solo aplica si RSI tiene datos válidos Y hay switches activos
    try:
        if strategy_self.rsi and hasattr(strategy_self, 'rsi_ind') and strategy_self.rsi_ind is not None:
            if not apply_rsi_global_filter(strategy_self):
                condicion_base_tecnica = False
    except Exception:
        # Error en filtro RSI: ignorar y continuar sin filtro
        pass

    # ----------------------------------------------------------------------
    # --- 4. VERIFICACIÓN DE MODO BUY & HOLD (Compra sin filtros técnicos) ---
    # ----------------------------------------------------------------------
    # Verificar si RSI tiene switches de SEÑAL activos (solo estos cuentan como indicador "activo")
    # Los switches de VENTA (máximo, descendente) NO bloquean B&H, solo cierran posiciones
    rsi_tiene_switches_compra = (
        getattr(strategy_self, 'rsi_minimo', False) or
        getattr(strategy_self, 'rsi_ascendente', False)
    )
    
    indicadores_tecnicos_activos = (
        strategy_self.ema_cruce_signal or
        rsi_tiene_switches_compra or  # RSI solo cuenta si tiene switches de COMPRA
        strategy_self.macd or 
        strategy_self.stoch_fast or 
        strategy_self.stoch_mid or 
        strategy_self.stoch_slow or
        strategy_self.bb_active # 🟢 Añadido BB
    )
    if not condicion_base_tecnica:
        # Lógica Buy & Hold: Compra si no hay señales activas PERO la tendencia de la EMA Lenta es favorable.
        if not indicadores_tecnicos_activos:
            condicion_base_tecnica = strategy_self.ema_slow_minimo_STATE or strategy_self.ema_slow_ascendente_STATE
            if condicion_base_tecnica:
                technical_reasons['B&H'] = "B&H Mínimo"

    # ----------------------------------------------------------------------
    # --- 4. FILTRO DE VOLUMEN (Condición AND Excluyente) ---
    # ----------------------------------------------------------------------
    volume_condition_met, volume_log_reason = apply_volume_filter(strategy_self)
    
    if not volume_condition_met:
        # Falla el filtro de volumen, abortamos la señal de compra
        return
    
    if volume_log_reason: technical_reasons['Volume'] = volume_log_reason 

    # ----------------------------------------------------------------------
    # --- 5. FILTRO FUNDAMENTAL (Margen de Seguridad - Condición AND) ---
    # ----------------------------------------------------------------------
    cond_mos_valida, mos_log_reason = apply_mos_filter(strategy_self)

    # Si MoS está activo y no es válido, salimos de la función de compra
    if strategy_self.margen_seguridad_active and not cond_mos_valida:
        return
    
    # ----------------------------------------------------------------------
    # --- 6. DECISIÓN FINAL DE COMPRA ---
    # ----------------------------------------------------------------------
    
    # Compra si: (Señal Técnica Fuerte) AND (Condición Fundamental Válida)
    if condicion_base_tecnica and cond_mos_valida:
        
        strategy_self.buy()

        # Inicializa el precio máximo para el Trailing Stop Loss
        strategy_self.max_price = strategy_self.data.Close[-1]
        
        # Calcula el Stop Loss inicial
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
        
        # Registro en trades_list
        strategy_self.trades_list.append({
            "Symbol": strategy_self.ticker, 
            "Tipo": "COMPRA", 
            "Descripcion": descripcion_compra,
            "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            "Precio_Entrada": round(strategy_self.data.Close[-1], 2), 
            "Stop_Loss_Inicial": round(strategy_self.my_stop_loss, 2), 
            "Precio_Salida": "N/A", 
            "PnL_Absoluto": "N/A", 
            "Retorno_Pct": "N/A", 
            "Comision_Total": "N/A",
        })

# ----------------------------------------------------------------------
# --- LÓGICA DE CIERRE (VENTA) ---
# ----------------------------------------------------------------------

def manage_existing_position(strategy_self: 'StrategySelf') -> None:
    """
    Gestiona el cierre de la posición (cierre técnico o stop-loss dinámico/Trailing Stop).

    Esta es la función principal de salida que orquesta la lógica:
    1. Calcula/actualiza los estados de los indicadores.
    2. Evalúa las señales de cierre técnico (lógica OR entre indicadores).
    3. Si no hay cierre técnico, gestiona el Stop Loss dinámico (Trailing SL).
    4. Ejecuta el cierre por Stop Loss si el precio cae por debajo del límite.

    Parameters
    ----------
    strategy_self : StrategySelf
        Instancia de la clase System (Strategy) con la posición abierta.

    Returns
    -------
    None
        La función ejecuta la orden de venta (cierre) a través de `strategy_self.position.close()` 
        si se cumplen las condiciones de salida o Stop Loss.
    """
    if not strategy_self.position:
        return 
        
    # 1. CALCULAR Y ACTUALIZAR ESTADOS
    _actualizar_estados_indicadores(strategy_self)

    final_stop_loss = strategy_self.my_stop_loss

    close_position = False
    descripcion_cierre = "N/A"
    
    # Lógica de Control: Solo ejecuta cierre técnico si hay indicadores activos.
    indicadores_tecnicos_activos = (
        strategy_self.ema_cruce_signal or
        (getattr(strategy_self, 'ema_slow_minimo', False) or getattr(strategy_self, 'ema_slow_maximo', False) or getattr(strategy_self, 'ema_slow_ascendente', False) or getattr(strategy_self, 'ema_slow_descendente', False)) or
        strategy_self.rsi or
        strategy_self.macd or
        strategy_self.stoch_fast or
        strategy_self.stoch_mid or
        strategy_self.stoch_slow or
        strategy_self.bb_active # 🟢 Añadido BB
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

        # 2. RSI (Solo si no hay señal anterior)
        if not close_position:
            close_position_rsi, desc_rsi = check_rsi_sell_signal(strategy_self)
            if close_position_rsi:
                close_position = True
                descripcion_cierre = desc_rsi

        # 3. MACD (Solo si no hay señal anterior)
        if not close_position:
            close_position_macd, desc_macd = check_macd_sell_signal(strategy_self)
            if close_position_macd:
                close_position = True
                descripcion_cierre = desc_macd

        # 4. ESTOCÁSTICOS (Solo si no hay señal anterior - Prioridad: Fast > Mid > Slow)
        if not close_position:
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
            
        # 🟢 5. BOLLINGER BANDS (BB) (Solo si no hay señal anterior)
        if not close_position:
            close_position_bb, desc_bb = check_bb_sell_signal(strategy_self)
            if close_position_bb:
                close_position = True
                descripcion_cierre = desc_bb
            
        # ----------------------------------------------------------------------
        # --- CIERRE Y REGISTRO TÉCNICO ---
        # ----------------------------------------------------------------------
        
        if close_position:
            strategy_self.position.close()
            
            # Obtener el objeto trade para el log
            trade_obj = strategy_self.trades[-1] if strategy_self.trades else None
            
            # Reseteo de variables de la estrategia
            strategy_self.max_price = 0
            strategy_self.my_stop_loss = None
            
            # 🌟 REGISTRO DE VENTA TÉCNICA 🌟
            strategy_self.trades_list.append({
                "Symbol": strategy_self.ticker, 
                "Tipo": "VENTA",
                "Descripcion": descripcion_cierre, 
                "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                "Precio_Entrada": round(trade_obj.entry_price, 4) if trade_obj and trade_obj.entry_price is not None else "N/A",
                "Stop_Loss_Inicial": round(final_stop_loss, 2) if final_stop_loss else "N/A", 
                "Precio_Salida": round(trade_obj.exit_price, 4) if trade_obj and trade_obj.exit_price is not None else round(strategy_self.data.Close[-1], 4),
                "PnL_Absoluto": round(trade_obj.pl, 2) if trade_obj and trade_obj.pl is not None else "N/A", 
                "Retorno_Pct": round(trade_obj.pl_pct * 100, 2) if trade_obj and trade_obj.pl_pct is not None else "N/A", 
                "Comision_Total": round(trade_obj._commissions, 2) if trade_obj and trade_obj._commissions is not None else "N/A",
            })
            
            return 
            
    # ----------------------------------------------------------------------
    # --- GESTIÓN DE STOP LOSS DINÁMICO (Trailing Stop) ---
    # ----------------------------------------------------------------------
    
    # 1. Actualiza el precio máximo alcanzado
    current_high = strategy_self.data.High[-1]
    strategy_self.max_price = max(strategy_self.max_price, current_high)
    
    # 2. Calcular el nuevo SL basado en el máximo
    new_stop_loss = strategy_self.max_price * (1 - strategy_self.stoploss_percentage_below_close)

    # 3. Actualiza el SL solo si ha subido (Trailing)
    if strategy_self.my_stop_loss is None or new_stop_loss > strategy_self.my_stop_loss:
        old_stop_loss = strategy_self.my_stop_loss
        strategy_self.my_stop_loss = new_stop_loss
        
        # Registrar la actualización del SL (comentada para evitar logs excesivos)
        # _log_trade_action_sl_update(strategy_self, old_stop_loss, new_stop_loss)

    # 4. Cierre por Stop Loss
    if strategy_self.my_stop_loss is not None and strategy_self.data.Close[-1] < strategy_self.my_stop_loss:
        
        strategy_self.position.close()
        

        trade_obj = strategy_self.trades[-1] if strategy_self.trades else None
        
        # Reseteo de variables de la estrategia
        strategy_self.max_price = 0
        strategy_self.my_stop_loss = None
        
        # 🌟 REGISTRO DE VENTA POR STOP LOSS 🌟
        strategy_self.trades_list.append({
            "Symbol": strategy_self.ticker, 
            "Tipo": "VENTA",
            "Descripcion": "StopLoss", 
            "Fecha": strategy_self.data.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            "Precio_Entrada": round(trade_obj.entry_price, 4) if trade_obj and trade_obj.entry_price is not None else "N/A",
            "Stop_Loss_Inicial": round(final_stop_loss, 2) if final_stop_loss else "N/A", 
            "Precio_Salida": round(trade_obj.exit_price, 4) if trade_obj and trade_obj.exit_price is not None else round(strategy_self.data.Close[-1], 4),
            "PnL_Absoluto": round(trade_obj.pl, 2) if trade_obj and trade_obj.pl is not None else "N/A", 
            "Retorno_Pct": round(trade_obj.pl_pct * 100, 2) if trade_obj and trade_obj.pl_pct is not None else "N/A", 
            "Comision_Total": round(trade_obj._commissions, 2) if trade_obj and trade_obj._commissions is not None else "N/A",
        })
    else:
        # Registro por qué no se compró (debug) — protegido contra variables no definidas
        try:
            cbt = locals().get('condicion_base_tecnica', None)
            cmv = locals().get('cond_mos_valida', None)
            tre = locals().get('technical_reasons', None)
            logger.debug(f"NO BUY | Ticker={getattr(strategy_self,'ticker','UNK')} | condicion_base_tecnica={cbt} | cond_mos_valida={cmv} | technical_reasons={tre}")
        except Exception:
            logger.debug("NO BUY | Ticker=%s | debug values unavailable", getattr(strategy_self,'ticker','UNK'))