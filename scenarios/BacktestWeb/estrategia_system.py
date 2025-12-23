# estrategia_system.py (Adaptado a la estructura central)

import pandas as pd
import numpy as np
import ta.trend
import ta.momentum
from backtesting import Strategy
# Importamos crossover para posible uso en MACD o medias móviles
from backtesting.lib import crossover 

# =========================================================================
# === IMPORTACIONES DEL MOTOR CENTRAL (TRADING_ENGINE) ===
# =========================================================================

# 🎯 IMPORTACIÓN DE LÓGICA CORE: Asume que Logica_Trading está en trading_engine.core
# NOTA: Para este escenario de "scenarios/BacktestWeb", usar una importación absoluta es mejor.
# Si el escenario se ejecuta desde la raíz o si trading_engine está instalado, funciona:
from trading_engine.core.Logica_Trading import check_buy_signal, manage_existing_position 

# 🎯 IMPORTACIÓN DE INDICADORES: El StochHelper se traslada a la carpeta 'indicators'
from trading_engine.indicators.Filtro_Stochastic import StochHelper 
from trading_engine.indicators.Filtro_BollingerBands import calculate_bollinger_bands

# =========================================================================
# =========================================================================


# --- FUNCIÓN DE CÁLCULO DE VMA (Media Móvil Simple basada en Pandas) ---
# 💡 ¡CORRECCIÓN CLAVE! Aceptamos **kwargs para ignorar los argumentos de ploteo de backtesting.py
def _calculate_vma_sma( data, period, **kwargs): 
    """Calcula la Media Móvil Simple (SMA) del volumen usando Pandas, ignorando argumentos de ploteo."""
    # Pandas rolling() es el método más robusto aquí.
    return pd.Series(data).rolling(period).mean() 

# ----------------------------------------------------------------------
# --- CLASE DE LA ESTRATEGIA: System ---
# ----------------------------------------------------------------------

class System(Strategy):

    # ------------------------------------------------------------------
    # --- ATRIBUTOS DE CLASE (INICIALIZACIÓN Y GESTIÓN) ---
    # ... (El resto de atributos de clase queda sin cambios) ...
    # ------------------------------------------------------------------

    from_date = None
    to_date = None

    # RSI
    rsi = None; rsi_period = None; rsi_low_level = None; rsi_high_level = None
    rsi_strength_threshold = None
    rsi_minimo = False # Placeholder
    rsi_maximo = False # Placeholder
    rsi_ascendente = False # Placeholder
    rsi_descendente = False # Placeholder

    # ESTOCÁSTICOS
    stoch_fast = None; stoch_fast_period = None; stoch_fast_smooth = None; stoch_fast_low_level = None
    stoch_fast_high_level = None; stoch_fast_oversold = None
    # Estados STOCH FAST
    stoch_fast_minimo = False
    stoch_fast_maximo = False
    stoch_fast_ascendente = False
    stoch_fast_descendente = False
    
    stoch_mid = None; stoch_mid_period = None; stoch_mid_smooth = None; stoch_mid_low_level = None
    stoch_mid_high_level = None; stoch_mid_oversold = None
    # Estados STOCH MID
    stoch_mid_minimo = False
    stoch_mid_maximo = False
    stoch_mid_ascendente = False
    stoch_mid_descendente = False

    stoch_slow = None; stoch_slow_period = None; stoch_slow_smooth = None; stoch_slow_low_level = None
    stoch_slow_high_level = None; stoch_slow_oversold = None
    # Estados STOCH SLOW
    stoch_slow_minimo = False
    stoch_slow_maximo = False
    stoch_slow_ascendente = False
    stoch_slow_descendente = False

    # MEDIAS MÓVILES (EMA)
    # MODIFICACIÓN: 'ema_cruce_signal' añadido para coincidir con .env
    ema_cruce_signal = False
    ema_slow_activo = False
    ema_fast_period = None
    ema_slow_period = None
    # Series de indicadores (Para evitar conflicto con la variable de activación)
    ema_fast_series = None
    ema_slow_series = None
    # Estados EMA LENTA
    ema_slow_minimo = False # Cambiado de 'ema_minimo'
    ema_slow_maximo = False # Cambiado de 'ema_maximo'
    ema_slow_ascendente = False # Cambiado de 'ema_ascendente'
    ema_slow_descendente = False # Cambiado de 'ema_descendente'

    # MACD
    macd = None; macd_fast = None; macd_slow = None; macd_signal = None
    # Estados MACD
    macd_minimo = False # Placeholder
    macd_maximo = False # Placeholder
    macd_ascendente = False # Placeholder
    macd_descendente = False # Placeholder

    # ------------------------------------------------------------------
    # 🌟 BANDAS DE BOLLINGER (BB) - NUEVOS ATRIBUTOS DE CLASE 🌟
    # ------------------------------------------------------------------
    bb_active = False           # ¿El indicador está activo?
    bb_window = 20              # Período de la SMA central
    bb_num_std = 2.0            # Desviaciones estándar para las bandas
    bb_buy_crossover = False    # Lógica de compra: cruce de banda inferior
    bb_sell_crossover = False   # Lógica de venta: cruce de banda superior
    
    # Series de indicadores
    bb_sma_series = None        # Media Móvil Simple (línea central)
    bb_upper_band_series = None # Banda Superior
    bb_lower_band_series = None # Banda Inferior
    
    # Estados BB (Para lógicas de volatilidad/ancho de banda)
    bb_minimo = False
    bb_maximo = False
    bb_ascendente = False
    bb_descendente = False
    # ------------------------------------------------------------------

    # RIESGO Y GESTIÓN DE CAPITAL
    riesgo_max_trade = 0.0 # Porcentaje máximo a perder por trade
    riesgo_max_drawdown = 0.0 # Porcentaje máximo de drawdown global

    # LÓGICAS DE CRUCE
    ema_buy_logic_crossover = False
    ema_sell_logic_crossover = False
    macd_buy_logic_crossover = False
    macd_sell_logic_crossover = False

    # VOLUMEN (Nuevas variables de control)
    volumen_min_entrada = 0.0 # Volumen mínimo para la entrada
    volumen_max_entrada = 0.0 # Volumen máximo para la entrada

    # MARGEN DE SEGURIDAD (FUNDAMENTAL)
    margen_seguridad_active = None
    margen_seguridad_threshold = None
    # Estados MoS
    margen_seguridad_minimo = False # Placeholder
    margen_seguridad_maximo = False # Placeholder
    margen_seguridad_ascendente = False # Placeholder
    margen_seguridad_descendente = False # Placeholder

    # --- VOLUMEN ---
    volume_active = False 
    volume_period = 20 
    volume_avg_multiplier = 1.0 
    volume_overshoot_threshold = 3 # 🌟 NUEVO: Parámetro para el Umbral de veces (asumido del .env)
    volume_overshoot_count = 0 # 🌟 NUEVO: Contador para el estado actual
    # Estados de Volumen (Exclusivos)
    volume_minimo = False
    volume_maximo = False
    volume_ascendente = False
    volume_descendente = False
    # Serie del indicador (para almacenar el V-SMA/V-EMA)
    volume_series = None
    

    # Stop Loss Dinámico (Global)
    stoploss_percentage_below_close = None
    
    # Atributos estáticos para gestión de rutas (inicializados en configuracion.py)
    DATA_FILES_PATH = None
    FULLRATIO_PATH = None

    
    # ------------------------------------------------------------------
    # --- ATRIBUTOS DE INSTANCIA (SETUP Y LÓGICA) ---
    # ------------------------------------------------------------------
    def init(self):
        
        # --- Variables de Gestión de Posición ---
        self.my_stop_loss = None  # Stop loss dinámico
        self.max_price = 0        # Precio máximo alcanzado desde la entrada
        
        # --- Variables de Logging y Ticker ---
        self.trades_list = []

        # 2. INICIALIZACIÓN DE VARIABLES DE ESTADO
        # Es necesario definir estas variables aquí para que existan cuando 
        # Logica_Trading intente leerlas o escribirlas.

        # Estados para (EMA LENTA) 🌟
        self.ema_slow_ascendente_STATE = False
        self.ema_slow_descendente_STATE = False
        self.ema_slow_maximo_STATE = False
        self.ema_slow_minimo_STATE = False # ¡La variable que faltaba!        
        
        # Estados para RSI
        self.rsi_ascendente_STATE = False
        self.rsi_descendente_STATE = False
        self.rsi_minimo_STATE = False
        self.rsi_maximo_STATE = False

        # Estados para Estocásticos (Fast, Mid, Slow)
        self.stoch_fast_ascendente_STATE = False
        self.stoch_fast_descendente_STATE = False
        self.stoch_mid_ascendente_STATE = False
        self.stoch_mid_descendente_STATE = False
        self.stoch_slow_ascendente_STATE = False
        self.stoch_slow_descendente_STATE = False
        
        # Estados para MACD
        self.macd_ascendente_STATE = False
        self.macd_descendente_STATE = False
        
        # Estados para Volumen
        self.volume_ascendente_STATE = False
        self.volume_descendente_STATE = False
        
        # Estados para Margen de Seguridad
        self.margen_seguridad_ascendente_STATE = False
        self.margen_seguridad_descendente_STATE = False

        # -------------------------------------------------------------
        # 🌟 NUEVOS ESTADOS BB
        # -------------------------------------------------------------
        self.bb_ascendente_STATE = False
        self.bb_descendente_STATE = False
        self.bb_maximo_STATE = False
        self.bb_minimo_STATE = False
        # -------------------------------------------------------------
        
        # Otros estados auxiliares que puedan ser necesarios
        self.compra_detectada = False
        self.venta_detectada = False
        
        # -------------------------------------------------------------
        # 🟢 Inicialización de Indicadores (I) - CORRECCIÓN DE DATOS 🟢
        # -------------------------------------------------------------
        
        # MEDIAS MÓVILES EXPONENCIALES (EMA)

        # 1. 💡 REGLA DE ACTIVACIÓN: ema_slow_activo
        # Si alguno de los filtros de estado está activo en la configuración,
        # forzamos ema_slow_activo a True (si no lo estaba ya).
        if self.ema_slow_minimo or self.ema_slow_maximo or \
           self.ema_slow_ascendente or self.ema_slow_descendente:
            self.ema_slow_activo = True
            
        # 2. CÁLCULO DE INDICADORES
        
        # EMA Lenta: Siempre se calcula si hay CRUCE O si hay filtro activo.
        if self.ema_cruce_signal or self.ema_slow_activo:
            self.ema_slow_series = self.I(
                ta.trend.ema_indicator, self.data.Close.s, 
                self.ema_slow_period, name='EMA_Lenta'
            )
            # Inicialización de series de estado (solo si se usan filtros)
            if self.ema_slow_activo:
                self.ema_slow_minimo_s = self.ema_slow_series.copy() * 0
                self.ema_slow_maximo_s = self.ema_slow_series.copy() * 0
                self.ema_slow_ascendente_s = self.ema_slow_series.copy() * 0
                self.ema_slow_descendente_s = self.ema_slow_series.copy() * 0
            
        else:
            self.ema_slow_series = None

        # EMA Rápida: Solo se calcula si hay CRUCE.
        if self.ema_cruce_signal:
            self.ema_fast_series = self.I(
                ta.trend.ema_indicator, self.data.Close.s, 
                self.ema_fast_period, name='EMA_Rapida'
            )
        else:
            self.ema_fast_series = None

        # 2. RSI
        if self.rsi and self.rsi_period:
            # FIX: Usamos .s para asegurar que 'ta' reciba un objeto Series válido (soluciona el AttributeError)
            self.rsi_ind = self.I(ta.momentum.rsi, self.data.Close.s, self.rsi_period, name='RSI')
            
            # Indicador auxiliar para la línea de umbral del RSI
            self.rsi_threshold_ind = self.I(lambda x: pd.Series([self.rsi_low_level] * len(x), index=x.index), self.data.Close.s, name='RSI_Threshold')
            
        # 3. STOCHASTICS (FAST, MID, SLOW)
        # Creamos una instancia única del calculador (puede ser dentro o fuera del init si es más limpio)
        stoch_calculator = StochHelper()
        data = self.data

        # --- STOCH FAST ---
        if self.stoch_fast and self.stoch_fast_period:
            # 1. Calcular las series K y D usando el método 'calculate'
            stoch_k_fast_series, stoch_d_fast_series = stoch_calculator.calculate(
                data=data,
                window=self.stoch_fast_period, 
                smooth_window=self.stoch_fast_smooth
            )
            # 2. Asignar las Series a las variables de la estrategia usando self.I(lambda: ...)
            self.stoch_k_fast = self.I(lambda: stoch_k_fast_series, name='STOCH_FAST_K')
            self.stoch_d_fast = self.I(lambda: stoch_d_fast_series, name='STOCH_FAST_D')

        # --- STOCH MID ---
        if self.stoch_mid and self.stoch_mid_period:
            stoch_k_mid_series, stoch_d_mid_series = stoch_calculator.calculate(
                data=data,
                window=self.stoch_mid_period, 
                smooth_window=self.stoch_mid_smooth
            )
            self.stoch_k_mid = self.I(lambda: stoch_k_mid_series, name='STOCH_MID_K')
            self.stoch_d_mid = self.I(lambda: stoch_d_mid_series, name='STOCH_MID_D')

        # --- STOCH SLOW ---
        if self.stoch_slow and self.stoch_slow_period:
            stoch_k_slow_series, stoch_d_slow_series = stoch_calculator.calculate(
                data=data,
                window=self.stoch_slow_period, 
                smooth_window=self.stoch_slow_smooth
            )
            self.stoch_k_slow = self.I(lambda: stoch_k_slow_series, name='STOCH_SLOW_K')
            self.stoch_d_slow = self.I(lambda: stoch_d_slow_series, name='STOCH_SLOW_D')
        # ----------------------------------------------------------------------
            
        # 4. MACD
        # El MACD de ta.trend.macd generalmente no necesita .s
        if self.macd and self.macd_fast and self.macd_slow and self.macd_signal:
            self.macd_line = self.I(ta.trend.macd, self.data.Close.s, self.macd_fast, self.macd_slow, name='MACD_Line')
            self.macd_signal_line = self.I(ta.trend.macd_signal, self.data.Close.s, self.macd_fast, self.macd_slow, self.macd_signal, name='MACD_Signal')
            self.macd_hist = self.I(ta.trend.macd_diff, self.data.Close.s, self.macd_fast, self.macd_slow, self.macd_signal, name='MACD_Hist')

       
        # 5. BANDAS DE BOLLINGER (BB) 🌟 INTEGRACIÓN FINAL
        if self.bb_active: # Verificar si el indicador está habilitado en los parámetros
            # backtesting.py requiere que las series sean envueltas en self.I() si van a ser ploteadas,
            # pero dado que calculate_bollinger_bands devuelve Series de Pandas ya calculadas,
            # las asignamos directamente (aunque no se plotean automáticamente a menos que las envuelvas)
            # o si las pasas como lambdas a self.I()
            
            # Opción 1 (La mejor, usando I() con lambda para ploteo si es necesario)
            bb_sma_s, bb_upper_s, bb_lower_s = calculate_bollinger_bands(
                self.data.df, 
                window=self.bb_window, 
                num_std=self.bb_num_std
            )
            
            self.bb_sma_series = self.I(lambda: bb_sma_s, name='BB_SMA', overlay=True, color='blue')
            self.bb_upper_band_series = self.I(lambda: bb_upper_s, name='BB_Upper', overlay=True, color='red')
            self.bb_lower_band_series = self.I(lambda: bb_lower_s, name='BB_Lower', overlay=True, color='red')

        # 6. MARGEN DE SEGURIDAD (FUNDAMENTAL)
        if self.margen_seguridad_active:
             # Corrección: Se utiliza 'Margen de seguridad' in self.data para comprobar la existencia de la columna
             # self.data.df es la forma correcta de acceder al DataFrame completo en init()
             if 'Margen de seguridad' in self.data.df.columns:
                 self.margen_seguridad_ind = self.I(lambda x: x, self.data.df['Margen de seguridad'], name='MoS')
             else:
                 self.margen_seguridad_active = False

            
        # 7. VOLUMEN Y VMA 
        if self.volume_active and self.volume_period:
            
            # 1. Calcular VMA (CÁLCULO INTERNO: plot=False)
            self.data.VMA_SMA = self.I(
                _calculate_vma_sma,               # <--- NUEVA FUNCIÓN CORREGIDA
                self.data.Volume,         
                self.volume_period,       
                name='VMA_SMA',
                plot=False,  # <--- ESENCIAL: No ensuciar el gráfico
            )
            self.volume_series = self.data.VMA_SMA
            
            # 2. 📊 RVOL (CREA el panel de escala relativa)
            self.rvol = self.I(
                lambda v, ma: v / ma, 
                self.data.Volume, 
                self.data.VMA_SMA,
                name='Vol_Relativo',
                plot=True,
                color='black',
                overlay=False,  # <--- CREA EL NUEVO EJE (panel)
                scatter=False
            )
            
            # 3. Línea de Referencia (Se DIBUJA sobre el panel creado en #2)
            self.rvol_threshold = self.I(
                lambda x: pd.Series([self.volume_avg_multiplier]*len(x), index=x.index),
                self.data.Close.s, 
                name='Umbral_Nivel',
                plot=True,
                color='red',
                overlay=True,  # <--- SUPERPONE sobre RVOL (mismo panel)
                scatter=False
            )

            # 4. Puntos de Estado (Se DIBUJA sobre el panel RVOL)
            self.volume_umbral_s = self.I(
                # 💡 CORRECCIÓN: La lambda acepta 'x' (que será self.data.Close.s) para obtener len e index.
                lambda x, *args, **kwargs: pd.Series([np.nan] * len(x), index=x.index),
                self.data.Close.s,  # <--- Pasamos self.data.Close.s como serie de referencia
                name='Estado_Asc',
                # Parámetros de Ploteo
                plot=True,
                color='green', 
                overlay=True,  
                scatter=True, 
                size=5 
            )
    # ------------------------------------------------------------------
    # --- MÉTODO NEXT (Limpio - Llama a los Wrappers) ---
    # ------------------------------------------------------------------

    def next(self):

        # 1. DEBUG DE SUPERVIVENCIA: Si esto no sale, el problema es el DATASET
        # print(f"DEBUG: Procesando fecha {self.data.index[-1]}") 

        # 2. COMPROBACIÓN DE INDICADORES
        if self.bb_active and self.bb_upper_band_series is not None:
            # En backtesting.py, [-1] es la vela que se está procesando AHORA
            precio_actual = self.data.Close[-1]
            banda_inf = self.bb_lower_band_series[-1]
            
            # Si quieres ver por qué no compra, imprime la comparativa:
            # print(f"Precio: {precio_actual:.2f} | Banda Inf: {banda_inf:.2f} | ¿Debajo?: {precio_actual < banda_inf}")

        """
        Genera señales de trading, delegando la lógica a métodos wrapper internos.
        """
        
        if self.position:
            self._manage_existing_position_wrapper()
        else:
            self._check_buy_signal_wrapper()
            
            
    # ------------------------------------------------------------------
    # --- WRAPPERS (Métodos internos que satisfacen al framework) ---
    # ------------------------------------------------------------------

    def _check_buy_signal_wrapper(self):
        """Wrapper que llama a la función externa check_buy_signal."""
        check_buy_signal(self)

    def _manage_existing_position_wrapper(self):
        """Wrapper que llama a la función externa manage_existing_position."""
        manage_existing_position(self)