# Test rápido del filtro RSI
import sys
sys.path.insert(0, '.')

# Simulación de strategy con umbral = 0
class DummyStrategy:
    rsi = True
    rsi_strength_threshold = 0
    rsi_ind = [10, 20, 30, 40, 50]  # Serie de RSI ficticia
    
    def __getattr__(self, name):
        return None

from trading_engine.indicators.Filtro_RSI import apply_rsi_global_filter

strategy = DummyStrategy()

print(f"RSI activado: {strategy.rsi}")
print(f"Umbral configurado: {strategy.rsi_strength_threshold}")
print(f"Tipo de umbral: {type(strategy.rsi_strength_threshold)}")

resultado = apply_rsi_global_filter(strategy)

print(f"\nResultado del filtro: {resultado}")
if resultado:
    print("✅ Filtro permitiría compras")
else:
    print("❌ Filtro bloquearía compras")
