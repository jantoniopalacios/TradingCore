import os
import pandas as pd
import time
from sqlalchemy import create_engine, inspect, text, Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# --- CONFIGURACIÓN ---
# Puedes leer esto de un .env independiente más adelante
DB_URL = "postgresql://usuario:password@localhost:5433/tu_base_datos"
CSV_FUNDAMENTALS_PATH = "./Data_files/Fundamentals" # Ruta donde están tus CSV actuales

Base = declarative_base()

# --- MODELO INDEPENDIENTE ---
class FundamentalData(Base):
    __tablename__ = 'fundamental_data'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True, nullable=False)
    fecha_reporte = Column(Date, nullable=False)
    metrica = Column(String(50), nullable=False) # 'EPS', 'Revenue', etc.
    valor = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('symbol', 'fecha_reporte', 'metrica', name='_sym_date_met_uc'),)

def inicializar_y_sincronizar():
    # 1. Comprobar Conexión
    try:
        engine = create_engine(DB_URL)
        # Intentamos una conexión simple
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Conexión con SQL Server exitosa.")
    except Exception as e:
        print(f"❌ Error: No se puede conectar a la DB. ¿Está el servidor activo? {e}")
        return

    # 2. Verificar/Generar Tabla
    inspector = inspect(engine)
    if not inspector.has_table("fundamental_data"):
        print("⚠️ Tabla 'fundamental_data' no encontrada. Creándola...")
        Base.metadata.create_all(engine)
        print("✅ Tabla creada correctamente.")
    else:
        print("✅ Tabla 'fundamental_data' ya existe.")

    # 3. SESIÓN DE TRABAJO
    Session = sessionmaker(bind=engine)
    session = Session()

    # 4. APROVECHAR CSV EXISTENTES (Sincronización inicial)
    print("🔍 Buscando ficheros CSV para migrar a la DB...")
    if os.path.exists(CSV_FUNDAMENTALS_PATH):
        for f in os.listdir(CSV_FUNDAMENTALS_PATH):
            if f.endswith(".csv"):
                ticker = f.replace(".csv", "")
                print(f"--- Sincronizando {ticker} ---")
                
                # Leemos el CSV (asumiendo que tiene 'Date' y 'EPS' o similar)
                df = pd.read_csv(os.path.join(CSV_FUNDAMENTALS_PATH, f))
                
                # Transformamos y guardamos en DB
                for _, row in df.iterrows():
                    # Ejemplo: Migrando EPS
                    dato = FundamentalData(
                        symbol=ticker,
                        fecha_reporte=row['Date'],
                        metrica='EPS',
                        valor=row['EPS']
                    )
                    # Usamos merge para evitar errores si ya existía el dato
                    session.merge(dato)
                
                session.commit()
                print(f"✅ {ticker} migrado correctamente.")

    print("🚀 Proceso de inicialización finalizado.")

if __name__ == "__main__":
    inicializar_y_sincronizar()