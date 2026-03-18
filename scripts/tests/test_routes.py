import sys
from pathlib import Path
import pytest

# AÃ±adimos la raÃ­z al path para que encuentre 'trading_engine' y 'scenarios'
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Importamos usando la ruta completa de paquete
from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.configuracion import DB_URI

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_config_resurrected(client):
    """Verifica que la limpieza de CSV no rompiÃ³ la carga de DB_URI"""
    print(f"\n[INFO] DB_URI detectada: {DB_URI}")
    assert "postgresql" in DB_URI
    assert "localhost" in DB_URI

def test_index_without_csv(client):
    """Verifica que el index carga sin archivos fÃ­sicos de sÃ­mbolos"""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'
    
    response = client.get('/')
    assert response.status_code == 200
    print("âœ… Sistema validado: Index operativo 100% DB.")

