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
    # RSI Flags (Señales OR y Deniegos AND)
    rsi_minimo = False
    rsi_maximo = False
    rsi_ascendente = False
    rsi_descendente = False

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
        # 🟢 Inicialización de Indicadores (I) - BLOQUE COMPLETO 🟢
        # -------------------------------------------------------------
        
        # --- 1. MEDIAS MÓVILES (EMA) ---
        # Forzamos la creación de la serie siempre que los periodos estén definidos,
        # independientemente de los interruptores de señal.
        if self.ema_slow_period:
            self.ema_slow_series = self.I(
                ta.trend.ema_indicator, self.data.Close.s, 
                int(self.ema_slow_period), name='EMA_Lenta'
            )
            # Inicializamos las series de estados para el plot
            self.ema_slow_minimo_s = self.ema_slow_series.copy() * 0
            self.ema_slow_maximo_s = self.ema_slow_series.copy() * 0
            self.ema_slow_ascendente_s = self.ema_slow_series.copy() * 0
            self.ema_slow_descendente_s = self.ema_slow_series.copy() * 0

        if self.ema_cruce_signal and self.ema_fast_period:
            self.ema_fast_series = self.I(
                ta.trend.ema_indicator, self.data.Close.s, 
                int(self.ema_fast_period), name='EMA_Rapida'
            )

        # --- 2. RSI ---
        if self.rsi and self.rsi_period:
            self.rsi_ind = self.I(ta.momentum.rsi, self.data.Close.s, int(self.rsi_period), name='RSI')
            self.rsi_threshold_ind = self.I(
                lambda x: pd.Series([float(self.rsi_low_level)] * len(x), index=x.index), 
                self.data.Close.s, name='RSI_Threshold'
            )
            
        # --- 3. STOCHASTICS (FAST, MID, SLOW) ---
        stoch_calculator = StochHelper()
        for prefix in ['fast', 'mid', 'slow']:
            active = getattr(self, f'stoch_{prefix}')
            period = getattr(self, f'stoch_{prefix}_period')
            smooth = getattr(self, f'stoch_{prefix}_smooth')
            
            if active and period:
                k_ser, d_ser = stoch_calculator.calculate(
                    data=self.data, window=int(period), smooth_window=int(smooth)
                )
                setattr(self, f'stoch_k_{prefix}', self.I(lambda: k_ser, name=f'STOCH_{prefix.upper()}_K'))
                setattr(self, f'stoch_d_{prefix}', self.I(lambda: d_ser, name=f'STOCH_{prefix.upper()}_D'))

        # --- 4. MACD ---
        self.macd = str(getattr(self, 'macd', 'False')).lower() == 'true'
        if self.macd:
            try:
                self.macd_line = self.I(ta.trend.macd, self.data.Close.s, int(self.macd_fast), int(self.macd_slow), name='MACD_Line')
                self.macd_signal_line = self.I(ta.trend.macd_signal, self.data.Close.s, int(self.macd_fast), int(self.macd_slow), int(self.macd_signal), name='MACD_Signal')
                self.macd_hist = self.I(ta.trend.macd_diff, self.data.Close.s, int(self.macd_fast), int(self.macd_slow), int(self.macd_signal), name='MACD_Hist')
            except Exception as e:
                print(f"⚠️ MACD Error: {e}")
                self.macd = False

        # --- 5. BANDAS DE BOLLINGER (BB) ---
        if self.bb_active:
            bb_sma_s, bb_upper_s, bb_lower_s = calculate_bollinger_bands(
                self.data.df, window=int(self.bb_window), num_std=float(self.bb_num_std)
            )
            self.bb_sma_series = self.I(lambda: bb_sma_s, name='BB_SMA', overlay=True, color='blue')
            self.bb_upper_band_series = self.I(lambda: bb_upper_s, name='BB_Upper', overlay=True, color='red')
            self.bb_lower_band_series = self.I(lambda: bb_lower_s, name='BB_Lower', overlay=True, color='red')

        # --- 6. MARGEN DE SEGURIDAD (MoS) ---
        if self.margen_seguridad_active and 'Margen de seguridad' in self.data.df.columns:
            self.margen_seguridad_ind = self.I(lambda x: x, self.data.df['Margen de seguridad'], name='MoS')

        # --- 7. VOLUMEN Y RVOL ---
        if self.volume_active and self.volume_period:
            self.data.VMA_SMA = self.I(_calculate_vma_sma, self.data.Volume, int(self.volume_period), name='VMA_SMA', plot=False)
            self.volume_series = self.data.VMA_SMA
            
            # Panel de Volumen Relativo (RVOL)
            self.rvol = self.I(lambda v, ma: v / ma, self.data.Volume, self.data.VMA_SMA, name='Vol_Relativo', overlay=False)
            self.rvol_threshold = self.I(
                lambda x: pd.Series([float(self.volume_avg_multiplier)]*len(x), index=x.index),
                self.data.Close.s, name='Umbral_Nivel', color='red', overlay=True
            )
            # Puntos de estado sobre el panel de volumen
            self.volume_umbral_s = self.I(
                lambda x: pd.Series([np.nan] * len(x), index=x.index),
                self.data.Close.s, name='Estado_Asc', color='green', overlay=True, scatter=True
            )
    # ------------------------------------------------------------------
    # --- MÉTODO NEXT (Limpio - Llama a los Wrappers) ---
    # ------------------------------------------------------------------

    def next(self):
        """
        Orquesta el ciclo de vida de cada vela:
        1. Si hay posición abierta: gestiona salida.
        2. Si no hay posición: busca entrada.
        """
        # Delegamos la lógica pesada a los wrappers que conectan con Logica_Trading.py
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