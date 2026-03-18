# web_strategy/constants.py

# ======================================================================
# --- 1. CONSTANTES PARA EL PROCESAMIENTO DE FORMS (BLUEPRINT) ---
# ======================================================================

# Prefijos para identificar los grupos de indicadores que usan lógica exclusiva (radio buttons)
LOGIC_PREFIXES = [
    'rsi', 
    'stoch_fast', 
    'stoch_mid', 
    'stoch_slow'
]

# Sufijos para identificar las condiciones específicas de compra/venta en esos grupos
LOGIC_SUFFIXES = [
    '_minimo', 
    '_ascendente', 
    '_maximo', 
    '_descendente'
]

# ----------------------------------------------------------------------
# --- COMENTARIOS DE VARIABLES (TOOLTIPS) ---
# ----------------------------------------------------------------------

VARIABLE_COMMENTS = {
    # ------------------------------------------------------------------
    # A. PARÁMETROS GLOBALES (Ya proporcionados + Fecha/Datos)
    # ------------------------------------------------------------------
    "periodo": "Define el período total de datos a descargar (ej: 1y para un año, max para todos los datos disponibles).",
    "intervalo": "Define la frecuencia de los datos (ej: 1d para datos diarios, 1h para datos por hora).",
    "cash": "Monto inicial de capital con el que comienza el backtest.",
    "commission": "Comisión de trading aplicada a cada operación (ej: 0.002 = 0.2%).",
    "stoploss_percentage_below_close": "Porcentaje de pérdida máxima por posición antes de vender automáticamente (Stop Loss).",
    "breakeven_enabled": "Activa protección de capital inicial basada en el precio de entrada.",
    "breakeven_trigger_pct": "Porcentaje máximo de pérdida permitido desde la entrada (ej: 0.03 = 3% o 3 = 3%).",
    "enviar_mail": "Si está activo, se enviará un correo con el resumen de los resultados al finalizar la ejecución.",
    "destinatario_email": "Dirección(es) de correo electrónico a la que se enviarán los resultados.",
    
    # ------------------------------------------------------------------
    # B. PARÁMETROS DE MARGEN Y VOLUMEN (web_strategy/_tab_risk_volume.html)
    # ------------------------------------------------------------------
    "Margen_Seguridad_Active": "Activa el filtro fundamental (Margen de Seguridad de Benjamin Graham). Solo permite compras si el precio actual está por debajo del umbral.",
    "Margen_Seguridad_Threshold": "Valor mínimo del Margen de Seguridad (en porcentaje) que debe cumplir la acción para ser considerada para la compra.",
    
    # ------------------------------------------------------------------
    # C. PARÁMETROS RSI (web_strategy/_tab_rsi.html)
    # ------------------------------------------------------------------
    "rsi": "Activa el Relative Strength Index (RSI) como indicador de señal.",
    "rsi_period": "Período de cálculo para el RSI (ej: 14).",
    "rsi_high_level": "Nivel superior de sobrecompra (ej: 70). Si el RSI está por encima de este nivel, puede generar una señal de venta.",
    "rsi_strength_threshold": "Umbral de fuerza mínima que debe tener la tendencia de una señal para ser considerada válida.",
    "rsi_low_level": "Nivel inferior de sobreventa (ej: 30). Si el RSI está por debajo de este nivel, puede generar una señal de compra.",
    "rsi_minimo": "Lógica de Compra: Activa la señal cuando el RSI alcanza un MÍNIMO de sobreventa.",
    "rsi_ascendente": "Lógica de Compra: Activa la señal cuando el RSI cruza al alza el umbral de sobreventa (ej: cruza 30).",
    "rsi_maximo": "Lógica de Venta: Activa la señal cuando el RSI marca un máximo local en zona de sobrecompra (por encima de rsi_high_level).",
    "rsi_descendente": "Lógica de Venta: Activa la señal cuando el RSI cruza a la baja el umbral de sobrecompra (rsi_high_level).",
    
    # ------------------------------------------------------------------
    # D. PARÁMETROS STOCHASTICS (web_strategy/_tab_stoch.html)
    # ------------------------------------------------------------------
    # General
    "stoch_fast": "Activa el Oscilador Estocástico Rápido como indicador de señal.",
    "stoch_mid": "Activa el Oscilador Estocástico Medio como indicador de señal.",
    "stoch_slow": "Activa el Oscilador Estocástico Lento como indicador de señal.",
    "stoch_fast_period": "Período principal (%K) para el cálculo del Estocástico Rápido.",
    "stoch_mid_period": "Período principal (%K) para el cálculo del Estocástico Medio.",
    "stoch_slow_period": "Período principal (%K) para el cálculo del Estocástico Lento.",
    "stoch_fast_smooth": "Período de suavizado (%D) para el Estocástico Rápido.",
    "stoch_mid_smooth": "Período de suavizado (%D) para el Estocástico Medio.",
    "stoch_slow_smooth": "Período de suavizado (%D) para el Estocástico Lento.",
    "stoch_fast_low_level": "Nivel de sobreventa para el Estocástico Rápido (ej: 20).",
    "stoch_mid_low_level": "Nivel de sobreventa para el Estocástico Medio (ej: 20).",
    "stoch_slow_low_level": "Nivel de sobreventa para el Estocástico Lento (ej: 20).",
    "stoch_fast_high_level": "Nivel de sobrecompra para el Estocástico Rápido (ej: 80).",
    "stoch_mid_high_level": "Nivel de sobrecompra para el Estocástico Medio (ej: 80).",
    "stoch_slow_high_level": "Nivel de sobrecompra para el Estocástico Lento (ej: 80).",
    # Lógicas (Aplicable a Fast, Mid, Slow)
    "stoch_fast_minimo": "Lógica de Compra: Activa la señal cuando el Estocástico Rápido alcanza un MÍNIMO de sobreventa.",
    "stoch_fast_ascendente": "Lógica de Compra: Activa la señal cuando el Estocástico Rápido cruza al alza el nivel de sobreventa.",
    "stoch_fast_maximo": "Lógica de Venta: Activa la señal cuando el Estocástico Rápido alcanza un MÁXIMO de sobrecompra.",
    "stoch_fast_descendente": "Lógica de Venta: Activa la señal cuando el Estocástico Rápido cruza a la baja el nivel de sobrecompra.",
    # Se repiten las lógicas para MID y SLOW con la misma lógica descriptiva
    "stoch_mid_minimo": "Lógica de Compra: Activa la señal cuando el Estocástico Medio alcanza un MÍNIMO de sobreventa.",
    "stoch_mid_ascendente": "Lógica de Compra: Activa la señal cuando el Estocástico Medio cruza al alza el nivel de sobreventa.",
    "stoch_mid_maximo": "Lógica de Venta: Activa la señal cuando el Estocástico Medio alcanza un MÁXIMO de sobrecompra.",
    "stoch_mid_descendente": "Lógica de Venta: Activa la señal cuando el Estocástico Medio cruza a la baja el nivel de sobrecompra.",
    "stoch_slow_minimo": "Lógica de Compra: Activa la señal cuando el Estocástico Lento alcanza un MÍNIMO de sobreventa.",
    "stoch_slow_ascendente": "Lógica de Compra: Activa la señal cuando el Estocástico Lento cruza al alza el nivel de sobreventa.",
    "stoch_slow_maximo": "Lógica de Venta: Activa la señal cuando el Estocástico Lento alcanza un MÁXIMO de sobrecompra.",
    "stoch_slow_descendente": "Lógica de Venta: Activa la señal cuando el Estocástico Lento cruza a la baja el nivel de sobrecompra.",
    
    # ------------------------------------------------------------------
    # E. PARÁMETROS EMA (web_strategy/_tab_ema.html)
    # ------------------------------------------------------------------
    "ema_cruce_signal": "Activa la señal de trading basada en el cruce de las Medias Móviles Exponenciales (EMA).",
    "ema_fast_period": "Período para el cálculo de la EMA Rápida (ej: 12).",
    "ema_slow_period": "Período para el cálculo de la EMA Lenta (ej: 26).",
    "ema_buy_logic_crossover": "Activa la señal de COMPRA cuando la EMA Rápida cruza por encima de la EMA Lenta.",
    "ema_sell_logic_crossover": "Activa la señal de VENTA cuando la EMA Rápida cruza por debajo de la EMA Lenta.",
    "ema_slow_activo": "Activa la EMA Lenta como filtro de tendencia. Solo permite compras si el precio está por encima de la EMA Lenta.",

    # ------------------------------------------------------------------
    # F. PARÁMETROS MACD (web_strategy/_tab_macd.html)
    # ------------------------------------------------------------------
    "macd": "Activa el Moving Average Convergence Divergence (MACD) como indicador de señal.",
    "macd_fast": "Período para el cálculo de la EMA rápida del MACD (ej: 12).",
    "macd_slow": "Período para el cálculo de la EMA lenta del MACD (ej: 26).",
    "macd_signal": "Período para el cálculo de la línea de señal del MACD (ej: 9).",
    "macd_buy_logic_crossover": "Activa la señal de COMPRA cuando el MACD cruza por encima de la línea de Señal.",
    "macd_sell_logic_crossover": "Activa la señal de VENTA cuando el MACD cruza por debajo de la línea de Señal.",

    # ------------------------------------------------------------------
    # H. PARÁMETROS BOLLINGER BANDS (web_strategy/_tab_bb.html) <--- 🟢 ADICIÓN BB
    # ------------------------------------------------------------------
    'bb_active': 'Activar Bandas de Bollinger (BB) en la estrategia.',
    'bb_window': 'Período (ventana) de la Media Móvil central (típico: 20).',
    'bb_num_std': 'Número de Desviaciones Estándar para las bandas (típico: 2.0).',
    'bb_buy_crossover': 'Señal OR: Cruce alcista por encima de la Banda Inferior (giro de sobreventa).',
    'bb_sell_crossover': 'Señal OR (Cierre): Cruce bajista por debajo de la Banda Superior/Media (cierre técnico).',
    'bb_window_state': 'Período para el cálculo de estado dinámico (mínimo/máximo) del ancho de banda (volatilidad).',
}


# 1. Columnas Requeridas para la Ejecución del Backtest (Limpieza de Datos)
# Estas columnas son las mínimas que deben estar presentes en el DataFrame 
# antes de pasarlo al motor Backtrader, incluyendo datos OHLCV y ratios fundamentales.
REQUIRED_COLS = [
    "Open", 
    "High", 
    "Low", 
    "Close", 
    "Volume", 
    "Margen de seguridad",  # Requerida si se usa filtro fundamental
    "LTM EPS"               # Requerida si se usa filtro fundamental
]

# ======================================================================
# --- 2. DEFINICIÓN DE COLUMNAS PARA EL HISTÓRICO DE RESULTADOS (CSV) ---
# ======================================================================

# Esta lista debe contener el nombre exacto de las columnas del CSV de resultados 
# para asegurar la consistencia al guardar y leer el histórico de backtests.
COLUMNAS_HISTORICO = [
    
    # ------------------------------------------------------------------
    # A. MÉTRICAS DE RENDIMIENTO (Resultado del Backtest)
    # ------------------------------------------------------------------
    'Symbol',
    'Sharpe Ratio',
    'Max Drawdown [%]',
    'Profit Factor',
    'Return [%]',
    'Total Trades',
    'Win Rate [%]',
    
    # ------------------------------------------------------------------
    # B. PARÁMETROS GLOBALES (web_strategy/_tab_global.html)
    # ------------------------------------------------------------------
    'Fecha_Ejecucion',
    'Fecha_Inicio_Datos',
    'Fecha_Fin_Datos',
    'Intervalo_Datos',
    'Cash_Inicial', 
    'Comision',
    'Enviar_Mail',
    
    # ------------------------------------------------------------------
    # C. PARÁMETROS DE MARGEN Y VOLUMEN (web_strategy/_tab_risk_volume.html)
    # ------------------------------------------------------------------
    'Margen_Seguridad_Active', 
    'Margen_Seguridad_Threshold',
    # 'Riesgo_Max_Trade',
    # 'Riesgo_Max_Drawdown',
    # 'Volumen_Min_Entrada',
    # 'Volumen_Max_Entrada',

    # ------------------------------------------------------------------
    # D. PARÁMETROS RSI (web_strategy/_tab_rsi.html)
    # ------------------------------------------------------------------
    'rsi', # Activación
    'rsi_period',
    'rsi_high_level',
    'rsi_strength_threshold',
    'rsi_low_level',
    'rsi_minimo', # Lógica de Compra
    'rsi_ascendente',
    'rsi_maximo', # Lógica de Venta
    'rsi_descendente',

    # ------------------------------------------------------------------
    # E. PARÁMETROS STOCH (web_strategy/_tab_stoch.html)
    # ------------------------------------------------------------------
    # FAST
    'stoch_fast',
    'stoch_fast_period',
    'stoch_fast_smooth',
    'stoch_fast_low_level',
    'stoch_fast_high_level',
    'stoch_fast_minimo', 
    'stoch_fast_ascendente',
    'stoch_fast_maximo', 
    'stoch_fast_descendente',
    # MID
    'stoch_mid',
    'stoch_mid_period',
    'stoch_mid_smooth',
    'stoch_mid_low_level',
    'stoch_mid_high_level',
    'stoch_mid_minimo', 
    'stoch_mid_ascendente',
    'stoch_mid_maximo', 
    'stoch_mid_descendente',
    # SLOW
    'stoch_slow',
    'stoch_slow_period',
    'stoch_slow_smooth',
    'stoch_slow_low_level',
    'stoch_slow_high_level',
    'stoch_slow_minimo', 
    'stoch_slow_ascendente',
    'stoch_slow_maximo', 
    'stoch_slow_descendente',

    # ------------------------------------------------------------------
    # F. PARÁMETROS EMA (web_strategy/_tab_ema.html)
    # --- ¡NOMBRES CORREGIDOS PARA COINCIDIR CON ESTRATEGIA_SYSTEM.PY! ---
    # ------------------------------------------------------------------
    'ema_cruce_signal',        # Antes: 'ema_active'
    'ema_fast_period',         # Antes: 'ema_short_period'
    'ema_slow_period',         # Antes: 'ema_long_period'
    'ema_buy_logic_crossover',
    'ema_sell_logic_crossover',
    'ema_slow_activo',         # Antes: 'ema_filter_active'

    # ------------------------------------------------------------------
    # G. PARÁMETROS MACD (web_strategy/_tab_macd.html)
    # --- ¡NOMBRES CORREGIDOS PARA COINCIDIR CON ESTRATEGIA_SYSTEM.PY! ---
    # ------------------------------------------------------------------
    'macd',                    # Antes: 'macd_active'
    'macd_fast',               # Antes: 'macd_fast_period'
    'macd_slow',               # Antes: 'macd_slow_period'
    'macd_signal',             # Antes: 'macd_signal_period'
    'macd_buy_logic_crossover',
    'macd_sell_logic_crossover',

    # ------------------------------------------------------------------
    # H. PARÁMETROS BOLLINGER BANDS (web_strategy/_tab_bb.html) <--- 🟢 ADICIÓN BB
    # ------------------------------------------------------------------
    # Parámetros de configuración
    'bb_active',
    'bb_window',
    'bb_num_std',
    'bb_buy_crossover',
    'bb_sell_crossover',
    'bb_window_state',
    # Líneas del indicador (para trazar o registrar el estado)
    'BB_SMA',
    'BB_Upper',
    'BB_Lower',

]