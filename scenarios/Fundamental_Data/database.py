from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# --- ESTRUCTURA BASE ---
Base = declarative_base()

class FundamentalData(Base):
    """Tabla para almacenar las métricas financieras (EPS, Revenue, etc.)"""
    __tablename__ = 'fundamental_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), index=True, nullable=False)
    fecha_reporte = Column(Date, nullable=False)
    metrica = Column(String(50), nullable=False) # Ej: 'Diluted EPS', 'totalRevenue'
    valor = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Restricción: No puede haber dos valores para la misma métrica, símbolo y fecha
    __table_args__ = (
        UniqueConstraint('symbol', 'fecha_reporte', 'metrica', name='_sym_date_met_uc'),
    )

class Simbolo(Base):
    """
    Espejo de la tabla 'simbolos' que usa la App Web. 
    Solo declaramos lo mínimo para poder leer la lista de tickers.
    """
    __tablename__ = 'simbolos' 
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)

# --- CONFIGURACIÓN DE CONEXIÓN (Copiada de tu sistema pg8000) ---
DB_USER = "postgres"
DB_PASS = "admin"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "trading_db"

DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Motor y Sesión
engine = create_engine(DATABASE_URL, client_encoding='utf8')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea las tablas si no existen"""
    Base.metadata.create_all(bind=engine)