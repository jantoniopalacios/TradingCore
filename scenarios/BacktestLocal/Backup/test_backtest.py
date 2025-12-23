import pandas as pd
from backtesting import Backtest
import yfinance as yf
import ta

# 1. Importar la estrategia desde el mismo directorio
from estrategia_system import System

# 2. Descargar datos de ejemplo
def load_data(ticker="MSFT", period="1y", interval="1d"):
    """Descarga datos de ejemplo usando yfinance."""
    print(f"Descargando datos para {ticker}...")
    
    # 1. Descargar datos
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if data.empty:
        raise ValueError(f"No se pudieron descargar datos para {ticker}")
        
    # 2. APLANAR COLUMNAS (CORRECCIÓN CLAVE)
    # yfinance a veces devuelve un MultiIndex, lo eliminamos.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
        
    # 3. RENOMBRAR Y LIMPIAR
    data = data.rename(columns={
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume'
    })
    
    # Asegurar que no hay NaNs al principio que causen problemas
    return data.dropna()

# 3. Función principal para el backtest
def run_backtest():
# --- A. Cargar datos ---
    SYMBOL = "AAPL" # Definimos el símbolo aquí
    df_data = load_data(ticker=SYMBOL, period="2y", interval="1d")
    
    # --- B. Configurar Parámetros de la Estrategia (Ejemplos) ---
    # Nota: Estos parámetros DEBEN coincidir con los atributos definidos en System

    # 🎯 ATRIBUTO FALTANTE AÑADIDO:
    System.ticker = SYMBOL
    
    # 🎯 Ejemplo de Activación de EMA Lenta y RSI
    params = {
        'ema_slow_period': 50,
        'ema_slow_activo': True,
        'rsi': True,
        'rsi_period': 14,
        'rsi_low_level': 30,
        'rsi_high_level': 70,
        'stoploss_percentage_below_close': 0.05, # 5% SL
        'ema_slow_ascendente': True, # Filtro de estado
        # Añadir más parámetros que su Logica_Trading necesite...
    }

    # Asignar parámetros a la Estrategia (IMPORTANTE)
    System.ema_slow_period = params['ema_slow_period']
    System.ema_slow_activo = params['ema_slow_activo']
    System.rsi = params['rsi']
    System.rsi_period = params['rsi_period']
    System.rsi_low_level = params['rsi_low_level']
    System.stoploss_percentage_below_close = params['stoploss_percentage_below_close']
    System.ema_slow_ascendente = params['ema_slow_ascendente']


    # --- C. Ejecutar Backtest ---
    bt = Backtest(df_data, System, 
                  cash=10000, 
                  commission=.002, 
                  exclusive_orders=True)

    print("\n--- INICIANDO BACKTEST ---")
    
    # Ejecutar y optimizar (si es necesario)
    stats = bt.run()

    print("\n--- RESULTADOS DEL BACKTEST ---")
    print(stats)
    
    # Mostrar el gráfico de resultados
    bt.plot() 

if __name__ == '__main__':
    # Asegúrate de que las dependencias estén inicializadas si usas librerías complejas.
    run_backtest()