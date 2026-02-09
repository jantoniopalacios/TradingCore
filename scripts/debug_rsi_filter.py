"""
Script de debug para verificar el filtro RSI
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
from trading_engine.indicators.Filtro_EMA import update_ema_state, check_ema_buy_signal, apply_ema_global_filter
from trading_engine.indicators.Filtro_RSI import update_rsi_state, apply_rsi_global_filter
from backtesting.test import GOOG

class TestStrategy(Strategy):
    # EMA
    ema_cruce_signal = True
    ema_fast_period = 5
    ema_slow_period = 50
    
    # RSI
    rsi = True
    rsi_period = 14
    rsi_strength_threshold = 0  # CLAVE: Umbral en 0
    rsi_minimo = False
    rsi_ascendente = False
    rsi_maximo = False
    rsi_descendente = False
    
    def init(self):
        from backtesting.lib import crossover
        import pandas_ta as ta
        
        # EMA
        close_series = pd.Series(self.data.Close, index=self.data.index)
        self.ema_fast = self.I(ta.ema, close_series, length=self.ema_fast_period)
        self.ema_slow = self.I(ta.ema, close_series, length=self.ema_slow_period)
        
        # RSI
        self.rsi_ind = self.I(ta.rsi, close_series, length=self.rsi_period)
        
    def next(self):
        # Actualizar estados
        update_ema_state(self)
        if self.rsi:
            update_rsi_state(self)
        
        # Verificar señal EMA
        if crossover(self.ema_fast, self.ema_slow):
            condicion_base = True
            
            # Aplicar filtro EMA
            condicion_base = apply_ema_global_filter(self, condicion_base)
            
            # Aplicar filtro RSI
            rsi_filter_result = apply_rsi_global_filter(self)
            
            print(f"\n=== SEÑAL EMA DETECTADA ===")
            print(f"Fecha: {self.data.index[-1]}")
            print(f"RSI actual: {self.rsi_ind[-1]:.2f}")
            print(f"Umbral configurado: {self.rsi_strength_threshold}")
            print(f"Tipo umbral: {type(self.rsi_strength_threshold)}")
            print(f"Filtro RSI resultado: {rsi_filter_result}")
            print(f"Condición base después de EMA: {condicion_base}")
            
            if not rsi_filter_result:
                condicion_base = False
                print("❌ COMPRA BLOQUEADA por filtro RSI")
            
            if condicion_base and not self.position:
                print("✅ COMPRA EJECUTADA")
                self.buy()
        
        # Venta simple por cruce inverso
        elif crossover(self.ema_slow, self.ema_fast) and self.position:
            self.position.close()

# Ejecutar test
print("="*80)
print("TEST: RSI con umbral = 0 (debe permitir todas las compras de EMA)")
print("="*80)

bt = Backtest(GOOG, TestStrategy, cash=10000, commission=.002)
stats = bt.run()

print("\n" + "="*80)
print("RESULTADO")
print("="*80)
print(f"Total trades: {stats['# Trades']}")
print(f"Return: {stats['Return [%]']:.2f}%")

if stats['# Trades'] == 0:
    print("\n⚠️ PROBLEMA: No se ejecutaron trades. El filtro RSI está bloqueando.")
else:
    print("\n✅ OK: Se ejecutaron trades. El filtro RSI funciona correctamente.")
