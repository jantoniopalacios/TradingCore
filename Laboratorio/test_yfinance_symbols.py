import yfinance as yf

symbols = ["ZTS", "SAN.MC"]
for symbol in symbols:
    print(f"Descargando datos para: {symbol}")
    df = yf.download(symbol, period="1y", interval="1d")
    print(df.head())
    print(f"Filas descargadas: {len(df)}\n")
