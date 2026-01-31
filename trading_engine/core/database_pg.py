from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

# --- CONFIGURACIÓN ---
DB_USER = "postgres"
DB_PASS = "admin"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "trading_db"

DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 1. Creamos el objeto 'db' que Flask-SQLAlchemy necesita
db = SQLAlchemy()

# 2. Mantenemos el engine para compatibilidad con tus otros scripts
engine_pg = create_engine(
    DATABASE_URL,
    client_encoding='utf8',
    connect_args={
        'user': DB_USER,
        'password': DB_PASS
    }
)

def init_db(app):
    """Función para inicializar la db desde app.py"""
    db.init_app(app)
    with app.app_context():
        db.create_all()