import pandas as pd
import yfinance as yf
import logging
from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System 

# 1. Configurar Logs para ver qué pasa dentro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BacktestReal")

def lanzar_prueba():
    symbol = "NVDA"
    print(f"\n🚀 Lanzando motor profesional para: {symbol}")
    
    # 2. Descargar datos limpios
    data = yf.download(symbol, start="2022-01-01", interval="1d")
    
    if data.empty:
        print("❌ No se pudieron descargar datos.")
        return
    
    # --- FIX PARA MULTIINDEX DE YFINANCE ---
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0) # Se queda solo con 'Close', 'Open', etc.
    
    # Aseguramos que los nombres de las columnas sean exactamente los que espera el motor
    data.index.name = 'Date' 
    # ---------------------------------------

    # 3. EJECUCIÓN DEL MOTOR PURO (Sin Flask, sin errores de contexto)
    try:
        stats, trades, bt = run_backtest_for_symbol(
            data_clean=data,
            strategy_class=System,
            symbol=symbol,
            cash=1000000,
            commission=0.001,
            stoploss_percentage=0.05,
            logger=logger
        )
        
        print("\n" + "—"*40)
        print(f"📊 RESULTADOS FINALES ({symbol})")
        print("—"*40)
        print(f"💰 Retorno: {stats['Return [%]']:.2f}%")
        print(f"📈 Win Rate: {stats['Win Rate [%]']:.2f}%")
        print(f"🔄 Total Trades: {stats['# Trades']}")
        print("—"*40)
        
    except Exception as e:
        print(f"❌ Error en el motor: {e}")

if __name__ == "__main__":
    lanzar_prueba()