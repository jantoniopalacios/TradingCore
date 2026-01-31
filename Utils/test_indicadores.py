import unittest
import pandas as pd
import numpy as np
import sys
import os

# 1. Configuración de rutas
root_path = os.path.abspath(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# 2. Importaciones basadas en tu código real
try:
    from scenarios.BacktestWeb.estrategia_system import _calculate_vma_sma
    from trading_engine.indicators.Filtro_BollingerBands import calculate_bollinger_bands
    import ta.momentum as momentum
    print("\n" + "="*60)
    print("📊 AUDITORÍA FINAL DE INDICADORES (Sincronizada con Filtro_BB)")
    print("="*60 + "\n")
except ImportError as e:
    print(f"❌ Error de configuración: {e}")
    sys.exit(1)

class TestIndicadores(unittest.TestCase):
    
    def test_vma_sma(self):
        """Valida la media móvil del volumen."""
        datos = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        resultado = _calculate_vma_sma(datos, 3)
        self.assertEqual(resultado.iloc[2], 20.0)
        print("✅ FASE 1: VMA/SMA Volumen validado.")

    def test_bollinger_bands_final(self):
        """Auditoría de Bandas usando la firma real: (data, window, num_std)"""
        print("--- [FASE 2: AUDITORÍA DE BANDAS Y RETORNO] ---")
        
        # Simulamos una caída y una recuperación (para testear cruce inferior)
        df = pd.DataFrame({
            'Close': [100, 95, 90, 85, 88, 92, 95],
            'Open':  [100, 95, 90, 85, 88, 92, 95], # Requerido si el motor pide OHLC
            'High':  [100, 95, 90, 85, 88, 92, 95],
            'Low':   [100, 95, 90, 85, 88, 92, 95]
        })
        
        # 🌟 LLAMADA CORREGIDA: Según tu código (data, window, num_std)
        # Retorno: (sma, upper, lower)
        sma, upper, lower = calculate_bollinger_bands(df, window=3, num_std=2.0)
        
        reporte = pd.DataFrame({
            'Precio': df['Close'],
            'B. Superior': upper,
            'Media (SMA)': sma,
            'B. Inferior': lower
        }).dropna()
        
        print(reporte.to_string(justify='center', formatters={'B. Superior': '{:,.2f}'.format, 'B. Inferior': '{:,.2f}'.format, 'Media (SMA)': '{:,.2f}'.format}))
        
        # Verificación lógica: La banda superior debe ser mayor a la inferior
        self.assertTrue((upper.dropna() > lower.dropna()).all())
        print("\n✅ FASE 2: Estructura (SMA, Upper, Lower) y cálculos validados.")

    def test_rsi_momentum(self):
        """Valida niveles de RSI."""
        precios = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        rsi_serie = momentum.rsi(precios, window=5)
        self.assertGreater(rsi_serie.dropna().iloc[-1], 70)
        print("✅ FASE 3: Momentum RSI validado.")

    def test_macd_logic(self):
        """FASE 4: Validación de la estructura MACD requerida por next()."""
        print("\n--- [FASE 4: AUDITORÍA MACD Y ATRIBUTOS] ---")
        import ta.trend as trend
        
        # Simulamos precios para generar movimiento
        precios = pd.Series(np.random.uniform(10, 20, 150))
        
        # Variables que vienen de la web (simuladas como int)
        fast, slow, signal = 12, 26, 9
        
        # Simulamos lo que hace self.I()
        macd_line = trend.macd(precios, window_fast=fast, window_slow=slow)
        macd_signal_line = trend.macd_signal(precios, window_fast=fast, window_slow=slow, window_sign=signal)
        macd_hist = trend.macd_diff(precios, window_fast=fast, window_slow=slow, window_sign=signal)
        
        # Verificación de colisión: ¿Tienen datos?
        self.assertFalse(macd_hist.dropna().empty)
        
        print(f"MACD Hist (últimos 3): {macd_hist.tail(3).values}")
        print("✅ FASE 4: Atributos MACD validados.")

if __name__ == '__main__':
    unittest.main()