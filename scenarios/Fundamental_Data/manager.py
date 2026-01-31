import os
import requests
import time
from datetime import datetime
from sqlalchemy import func
from database import engine, SessionLocal, FundamentalData, Simbolo

# Tu API Key de Alpha Vantage
API_KEY = "60NPBW4583RN0HSB"

def limpiar_ticker(nombre_archivo):
    # Quita .csv y prefijos como Q0_, Q1_, etc.
    nombre = nombre_archivo.replace(".csv", "")
    return re.sub(r'^Q\d+_', '', nombre)

def ejecutar_migración():
    # 1. Limpieza inicial de la tabla para borrar datos con prefijos sucios
    with engine.connect() as conn:
        print("🧹 Limpiando tabla fundamental_data para migración limpia...")
        conn.execute(text("TRUNCATE TABLE fundamental_data"))
        conn.commit()

    # 2. Localizar archivos CSV
    # Ruta relativa: sube dos niveles desde scenarios/Fundamental_Data hasta TradingCore
    CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Data_files", "Fundamentals"))
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ No se encontró la carpeta: {CSV_PATH}")
        return

    session = SessionLocal()
    files = [f for f in os.listdir(CSV_PATH) if f.endswith(".csv")]
    print(f"📈 Procesando {len(files)} archivos...")

    for file in files:
        ticker_limpio = limpiar_ticker(file)
        print(f"🚀 Migrando: {ticker_limpio} (desde {file})")
        
        try:
            df = pd.read_csv(os.path.join(CSV_PATH, file), sep=';', na_values=['None', ''])
            
            # Métricas que queremos capturar
            metrics = [
                'goodwill', 'totalLiabilities', 'totalShareholderEquity', 
                'totalRevenue', 'ebit', 'netIncome_x', 'operatingCashflow', 
                'capitalExpenditures', 'Net Income', 'Diluted EPS'
            ]
            
            cols_presentes = [m for m in metrics if m in df.columns]

            for _, row in df.iterrows():
                if pd.isnull(row['fiscalDateEnding']): continue
                
                fecha = pd.to_datetime(row['fiscalDateEnding']).date()
                
                for m in cols_presentes:
                    if pd.notnull(row[m]):
                        dato = FundamentalData(
                            symbol=ticker_limpio,
                            fecha_reporte=fecha,
                            metrica=m,
                            valor=float(row[m])
                        )
                        session.merge(dato) # Evita duplicados si el archivo tiene filas repetidas
            
            session.commit()
            print(f"✅ {ticker_limpio} completado.")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error en {file}: {e}")

    session.close()
    print("\n✨ Migración finalizada con éxito.")

def mostrar_estado_fundamentales():
    session = SessionLocal()
    try:
        # Obtenemos la lista de tickers únicos de todos los usuarios
        tickers_unicos = session.query(Simbolo.symbol).distinct().all()
        
        print(f"\n{'TICKER':<12} | {'ÚLTIMA FECHA EN DB':<20} | {'ESTADO'}")
        print("-" * 50)
        
        for (ticker_name,) in tickers_unicos:
            # Buscamos la fecha máxima para este ticker en la tabla de fundamentales
            max_fecha = session.query(func.max(FundamentalData.fecha_reporte))\
                .filter(FundamentalData.symbol == ticker_name).scalar()
            
            if max_fecha:
                dias_antiguedad = (date.today() - max_fecha).days
                estado = "✅ OK" if dias_antiguedad < 100 else "⚠️ DESACTUALIZADO"
                fecha_str = max_fecha.strftime('%Y-%m-%d')
            else:
                fecha_str = "SIN DATOS"
                estado = "❌ PENDIENTE"
            
            print(f"{ticker_name:<12} | {fecha_str:<20} | {estado}")
            
    finally:
        session.close()

def limpiar_simbolos_sin_datos():
    session = SessionLocal()
    try:
        print("\n🔍 Iniciando limpieza de símbolos duplicados o sin datos...")
        
        # 1. Identificar tickers que tienen datos fundamentales
        tickers_con_datos = session.query(FundamentalData.symbol).distinct().all()
        lista_validos = [t[0] for t in tickers_con_datos]
        
        # 2. Buscar en la tabla Simbolo aquellos que NO están en la lista anterior
        # (Esto capturará a "GOOGLE", "NVIDIA", "NIKE", etc.)
        simbolos_a_borrar = session.query(Simbolo).filter(~Simbolo.symbol.in_(lista_validos)).all()
        
        if not simbolos_a_borrar:
            print("✨ No se encontraron símbolos huérfanos para borrar.")
            return

        print(f"⚠️ Se van a eliminar {len(simbolos_a_borrar)} símbolos sin datos.")
        
        for s in simbolos_a_borrar:
            ticker = s.symbol
            print(f"🗑️ Eliminando {ticker}...")
            
            # --- OPCIONAL: Borrado manual en otras tablas si no hay CASCADE ---
            # Ejemplo: session.query(OtrasTablas).filter_by(symbol=ticker).delete()
            
            # Borrado de la tabla principal de símbolos
            session.delete(s)
        
        session.commit()
        print("✅ Limpieza completada con éxito.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error durante la limpieza: {e}")
    finally:
        session.close()
def test_escritura_local():
    """Prueba de inserción sin gastar tokens de Alpha Vantage"""
    session = SessionLocal()
    ticker_test = "TEST"
    fecha_test = datetime.strptime("2025-12-31", "%Y-%m-%d").date()
    
    try:
        print(f"🧪 Iniciando test de escritura para {ticker_test}...")
        
        # Simulamos una métrica
        dato = FundamentalData(
            symbol=ticker_test,
            fecha_reporte=fecha_test,
            metrica="test_metric",
            valor=999.99
        )
        
        session.merge(dato)
        session.commit()
        print("✅ Escritura exitosa. La base de datos y pg8000 responden correctamente.")
        
        # Limpiamos el rastro del test
        # session.delete(dato)
        # session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error en el test de escritura: {e}")
    finally:
        session.close()

def obtener_cola_prioritaria():
    session = SessionLocal()
    # Tickers únicos que los usuarios tienen en la web
    tickers_web = [s[0] for s in session.query(Simbolo.symbol).distinct().all()]
    
    # Tickers que ya tienen ALGÚN dato
    con_datos = [f[0] for f in session.query(FundamentalData.symbol).distinct().all()]
    
    # La diferencia son los que faltan por completo
    pendientes = [t for t in tickers_web if t not in con_datos and len(t) <= 10]
    
    print(f"📊 Tickers en Web: {len(tickers_web)} | Con datos: {len(con_datos)}")
    print(f"🎯 Cola de descarga prioritaria: {pendientes}")
    return pendientes

def descargar_ticker(ticker, session):
    """Descarga datos de Alpha Vantage para un ticker específico."""
    url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={API_KEY}'
    
    try:
        print(f"📡 Solicitando datos para {ticker}...")
        r = requests.get(url)
        data = r.json()

        if "quarterlyReports" not in data:
            print(f"⚠️ No hay reportes para {ticker}. (Límite de API o ticker inválido)")
            return False

        for report in data["quarterlyReports"]:
            fecha = datetime.strptime(report['fiscalDateEnding'], '%Y-%m-%d').date()
            
            # Métricas clave para tu análisis
            mapping = {
                'totalRevenue': report.get('totalRevenue'),
                'netIncome': report.get('netIncome'),
                'ebit': report.get('ebit'),
                'operatingIncome': report.get('operatingIncome')
            }

            for metrica, valor in mapping.items():
                if valor and valor != 'None':
                    obj = FundamentalData(
                        symbol=ticker,
                        fecha_reporte=fecha,
                        metrica=metrica,
                        valor=float(valor)
                    )
                    session.merge(obj)
        
        session.commit()
        print(f"✅ {ticker} actualizado con éxito.")
        return True
        
    except Exception as e:
        print(f"❌ Error descargando {ticker}: {e}")
        session.rollback()
        return False

def ejecutar_flujo_inteligente():
    session = SessionLocal()
    try:
        # 1. Obtener tickers de la web que no tienen datos fundamentales
        # Usamos un set para no repetir tickers que pertenecen a varios usuarios
        tickers_en_web = {s.symbol for s in session.query(Simbolo).all()}
        tickers_con_datos = {f.symbol for f in session.query(FundamentalData.symbol).distinct().all()}
        
        cola_descarga = list(tickers_en_web - tickers_con_datos)
        
        # Filtramos tickers que sean nombres largos (basura)
        cola_descarga = [t for t in cola_descarga if len(t) <= 5]

        if not cola_descarga:
            print("✨ Todos los tickers están al día. No se requiere descarga.")
            return

        print(f"🚀 Se han encontrado {len(cola_descarga)} tickers pendientes.")
        
        for i, ticker in enumerate(cola_descarga):
            exito = descargar_ticker(ticker, session)
            
            # Pausa para no exceder 5 peticiones por minuto (API Free)
            if i < len(cola_descarga) - 1 and exito:
                print("⏳ Esperando 15 segundos para la siguiente petición...")
                time.sleep(15)

    finally:
        session.close()

if __name__ == "__main__":
    # ejecutar_migracion() # Si tienes nuevos CSVs, descomenta esto
    ejecutar_flujo_inteligente()