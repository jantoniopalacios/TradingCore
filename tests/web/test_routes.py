import sys
from pathlib import Path
import pytest
from trading_engine.core.database_pg import ENGINE_OPTIONS

# AÃ±adimos la raÃ­z al path para que encuentre 'trading_engine' y 'scenarios'
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Importamos usando la ruta completa de paquete
from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.configuracion import DB_URI

@pytest.fixture
def client(monkeypatch):
    import scenarios.BacktestWeb.app as app_module

    monkeypatch.setattr(app_module, "DB_URI", "sqlite:///:memory:")
    monkeypatch.setattr(app_module, "ENGINE_OPTIONS", {})

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        with app.app_context():
            yield client

def test_config_resurrected(client):
    """Verifica que la limpieza de CSV no rompiÃ³ la carga de DB_URI"""
    print(f"\n[INFO] DB_URI detectada: {DB_URI}")
    assert "postgresql" in DB_URI
    assert "localhost" in DB_URI
    assert ENGINE_OPTIONS['pool_pre_ping'] is True

def test_index_without_csv(client):
    """Verifica que el index carga sin archivos fÃ­sicos de sÃ­mbolos"""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'
    
    response = client.get('/')
    assert response.status_code == 200
    print("âœ… Sistema validado: Index operativo 100% DB.")

def test_scheduler_script_path_exists():
    """Verifica que la ruta configurada para el scheduler apunta a un script existente."""
    from scenarios.BacktestWeb.routes.main_bp import SCHEDULER_SCRIPT_PATH

    assert SCHEDULER_SCRIPT_PATH.exists()
    assert SCHEDULER_SCRIPT_PATH.name == "backtest_scheduler.py"


def test_database_url_uses_default_connection_values():
    import os
    import pytest
    from trading_engine.core.database_pg import DATABASE_URL

    env_vars = [
        "TRADINGCORE_DB_USER",
        "TRADINGCORE_DB_PASS",
        "TRADINGCORE_DB_HOST",
        "TRADINGCORE_DB_PORT",
        "TRADINGCORE_DB_NAME",
    ]

    if any(os.getenv(name) is not None for name in env_vars):
        pytest.skip("La conexión de BD está sobrescrita mediante variables de entorno")

    assert DATABASE_URL == "postgresql+pg8000://postgres:admin@localhost:5433/trading_db"

def test_scheduler_reuses_core_database_url():
    from scripts.scheduler.backtest_scheduler import DATABASE_URL as scheduler_database_url
    from trading_engine.core.database_pg import DATABASE_URL

    assert scheduler_database_url == DATABASE_URL

def test_scheduler_truthy_helper():
    from scripts.scheduler.backtest_scheduler import _es_verdadero

    assert _es_verdadero(True) is True
    assert _es_verdadero(False) is False
    assert _es_verdadero("true") is True
    assert _es_verdadero("1") is True
    assert _es_verdadero("yes") is True
    assert _es_verdadero("false") is False
    assert _es_verdadero("0") is False
    assert _es_verdadero("no") is False


def test_scheduler_utc_now_iso_format():
    from datetime import datetime, timezone
    from scripts.scheduler.backtest_scheduler import _utc_now_iso

    value = _utc_now_iso()

    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    assert parsed.tzinfo == timezone.utc

def test_scheduler_paths_match_web_paths():
    from scripts.scheduler.backtest_scheduler import (
        STATUS_FILE_PATH,
        PID_FILE_PATH,
    )
    from scenarios.BacktestWeb.routes.main_bp import (
        SCHEDULER_STATUS_PATH,
        SCHEDULER_PID_PATH,
    )

    assert STATUS_FILE_PATH == SCHEDULER_STATUS_PATH
    assert PID_FILE_PATH == SCHEDULER_PID_PATH


def test_backtest_status_idle(client):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'

    response = client.get('/backtest_status')

    assert response.status_code == 200
    assert response.get_json()['status'] == 'idle'


def test_scheduler_status_requires_admin(client):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'user'

    response = client.get('/scheduler/status')

    assert response.status_code == 403
    assert response.get_json()['status'] == 'error'


def test_graph_cache_helpers_without_snapshot():
    from types import SimpleNamespace
    from scenarios.BacktestWeb.routes.graph_cache import (
        _graph_cache_file_for_result,
        _graph_snapshot_file_for_result,
        _read_graph_snapshot_payload,
    )

    resultado = SimpleNamespace(id=123, usuario_id=7, symbol="AAPL")

    assert str(_graph_cache_file_for_result(resultado)).endswith("bt_123_AAPL.html")
    assert str(_graph_snapshot_file_for_result(resultado)).endswith("bt_123_AAPL_snapshot.json.gz")
    assert _read_graph_snapshot_payload(resultado) is None


def test_view_graph_requires_login(client):
    response = client.get('/backtest/ver_grafico/999999')

    assert response.status_code == 302
    assert response.headers['Location'] == '/login'


def test_view_graph_missing_result_returns_404(client):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'

    response = client.get('/backtest/ver_grafico/999999')

    assert response.status_code == 404


def test_view_graph_uses_legacy_html_fallback(client, monkeypatch):
    from scenarios.BacktestWeb.database import db, ResultadoBacktest, Usuario
    import scenarios.BacktestWeb.routes.main_bp as main_bp

    user = Usuario(username='legacy_graph_user', password='123')
    db.session.add(user)
    db.session.flush()
    resultado = ResultadoBacktest(
        usuario_id=user.id,
        id_estrategia=1,
        symbol='AAPL',
        grafico_html='<html><body><div>LEGACY_GRAPH</div></body></html>',
    )
    db.session.add(resultado)
    db.session.commit()

    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'

    monkeypatch.setattr(main_bp, '_regenerate_graph_html_on_demand', lambda resultado, user_mode: None)

    response = client.get(f'/backtest/ver_grafico/{resultado.id}')

    assert response.status_code == 200
    assert 'LEGACY_GRAPH' in response.get_data(as_text=True)


def test_view_graph_returns_unavailable_message_when_no_graph(client, monkeypatch):
    from scenarios.BacktestWeb.database import db, ResultadoBacktest, Usuario
    import scenarios.BacktestWeb.routes.main_bp as main_bp

    user = Usuario(username='empty_graph_user', password='123')
    db.session.add(user)
    db.session.flush()
    resultado = ResultadoBacktest(
        usuario_id=user.id,
        id_estrategia=1,
        symbol='AAPL',
        grafico_html=None,
    )
    db.session.add(resultado)
    db.session.commit()

    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['user_mode'] = 'admin'

    monkeypatch.setattr(main_bp, '_regenerate_graph_html_on_demand', lambda resultado, user_mode: None)

    response = client.get(f'/backtest/ver_grafico/{resultado.id}')

    assert response.status_code == 200
    assert 'Grafico no disponible para este backtest' in response.get_data(as_text=True)