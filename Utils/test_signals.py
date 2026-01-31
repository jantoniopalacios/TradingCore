import unittest
import pandas as pd
import sys
import os

# 1. Configuración de rutas
root_path = os.path.abspath(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# 2. Importaciones
try:
    from trading_engine.indicators.Filtro_BollingerBands import (
        check_bb_buy_signal, 
        check_bb_sell_signal
    )
    print("✅ Funciones de señales cargadas correctamente.")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    sys.exit(1)

# Clase Mock mejorada: Inicializa series vacías en lugar de None
class MockStrategy:
    def __init__(self, df, upper=None, sma=None, lower=None):
        self.data = type('Data', (), {'Close': df['Close'], 'index': df.index})
        self.bb_active = True
        self.bb_buy_crossover = True
        self.bb_sell_crossover = True
        
        # Si no se pasan bandas, creamos series neutras para evitar el error NoneType
        self.bb_upper_band_series = upper if upper is not None else pd.Series([999.0] * len(df))
        self.bb_sma_series = sma if sma is not None else pd.Series([0.0] * len(df))
        self.bb_lower_band_series = lower if lower is not None else pd.Series([0.0] * len(df))
        
        self.bb_minimo_STATE = False
        self.position = True

class TestSenales(unittest.TestCase):

    def test_cruce_banda_inferior_compra(self):
        """Test: El precio cruza hacia arriba la banda inferior."""
        print("\n--- [EJECUTANDO: COMPRA BANDA INFERIOR] ---")
        df = pd.DataFrame({'Close': [100.0, 90.0, 80.0, 85.0]})
        banda_inf = pd.Series([82.0, 82.0, 82.0, 82.0])
        
        strategy = MockStrategy(df, lower=banda_inf)
        compra_activa, razon = check_bb_buy_signal(strategy, False)
        
        print(f"Resultado: {compra_activa} | Motivo: {razon}")
        self.assertTrue(compra_activa)

    def test_cruce_banda_superior_venta(self):
        """Test: El precio cruza hacia abajo la banda superior."""
        print("\n--- [EJECUTANDO: VENTA BANDA SUPERIOR] ---")
        # El precio cae de 120 a 105. La banda está en 110.
        df = pd.DataFrame({'Close': [100.0, 115.0, 120.0, 105.0]})
        banda_sup = pd.Series([110.0, 110.0, 110.0, 110.0])
        
        # IMPORTANTE: Pasamos una SMA neutra (p.ej. 50) para que no sea None
        sma_neutra = pd.Series([50.0, 50.0, 50.0, 50.0])
        
        strategy = MockStrategy(df, upper=banda_sup, sma=sma_neutra)
        venta_activa, razon = check_bb_sell_signal(strategy)
        
        print(f"Resultado: {venta_activa} | Motivo: {razon}")
        self.assertTrue(venta_activa)

if __name__ == '__main__':
    unittest.main()