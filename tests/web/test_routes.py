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


def test_render_native_backtest_html_returns_html_and_cleans_temp_file():
    from pathlib import Path
    from scenarios.BacktestWeb.routes.graph_render import _render_native_backtest_html

    class FakeBacktestResult:
        filename = None

        def plot(self, filename, open_browser=False):
            self.filename = filename
            Path(filename).write_text('<html><body>NATIVE_GRAPH</body></html>', encoding='utf-8')

    fake_bt_result = FakeBacktestResult()

    html = _render_native_backtest_html(fake_bt_result, 123)

    assert html == '<html><body>NATIVE_GRAPH</body></html>'
    assert not Path(fake_bt_result.filename).exists()


def test_render_native_backtest_html_cleans_temp_file_when_plot_fails():
    from pathlib import Path
    from scenarios.BacktestWeb.routes.graph_render import _render_native_backtest_html

    class FailingBacktestResult:
        filename = None

        def plot(self, filename, open_browser=False):
            self.filename = filename
            raise RuntimeError('plot failed')

    fake_bt_result = FailingBacktestResult()

    with pytest.raises(RuntimeError, match='plot failed'):
        _render_native_backtest_html(fake_bt_result, 123)

    assert not Path(fake_bt_result.filename).exists()


def test_effective_graph_config_params_override_base_config():
    from types import SimpleNamespace
    from scenarios.BacktestWeb.routes.config_helpers import _build_effective_graph_config

    resultado = SimpleNamespace(
        params_tecnicos='{"start_date": "2024-02-01", "end_date": "2024-02-29", "intervalo": "1wk"}',
        fecha_inicio_datos=None,
        fecha_fin_datos=None,
        intervalo=None,
    )
    base_config = {
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'intervalo': '1d',
    }

    config_final, start_date, end_date, intervalo = _build_effective_graph_config(resultado, base_config)

    assert (start_date, end_date, intervalo) == ('2024-02-01', '2024-02-29', '1wk')
    assert config_final['start_date'] == config_final['START_DATE'] == start_date
    assert config_final['end_date'] == config_final['END_DATE'] == end_date
    assert config_final['intervalo'] == config_final['INTERVAL'] == intervalo


def test_effective_graph_config_result_dates_have_priority():
    from types import SimpleNamespace
    from scenarios.BacktestWeb.routes.config_helpers import _build_effective_graph_config

    resultado = SimpleNamespace(
        params_tecnicos='{"start_date": "2024-02-01", "end_date": "2024-02-29", "intervalo": "1wk"}',
        fecha_inicio_datos='2024-03-01',
        fecha_fin_datos='2024-03-31',
        intervalo='1h',
    )
    base_config = {
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'intervalo': '1d',
    }

    config_final, start_date, end_date, intervalo = _build_effective_graph_config(resultado, base_config)

    assert (start_date, end_date, intervalo) == ('2024-03-01', '2024-03-31', '1h')
    assert config_final['start_date'] == config_final['START_DATE'] == start_date
    assert config_final['end_date'] == config_final['END_DATE'] == end_date
    assert config_final['intervalo'] == config_final['INTERVAL'] == intervalo


def test_effective_graph_config_invalid_params_json_uses_base_config():
    from types import SimpleNamespace
    from scenarios.BacktestWeb.routes.config_helpers import _build_effective_graph_config

    resultado = SimpleNamespace(
        params_tecnicos='{invalid json',
        fecha_inicio_datos=None,
        fecha_fin_datos=None,
        intervalo=None,
    )
    base_config = {
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'intervalo': '1d',
    }

    config_final, start_date, end_date, intervalo = _build_effective_graph_config(resultado, base_config)

    assert (start_date, end_date, intervalo) == ('2024-01-01', '2024-01-31', '1d')
    assert config_final['start_date'] == config_final['START_DATE'] == start_date
    assert config_final['end_date'] == config_final['END_DATE'] == end_date
    assert config_final['intervalo'] == config_final['INTERVAL'] == intervalo


def test_effective_graph_config_missing_date_returns_none():
    from types import SimpleNamespace
    from scenarios.BacktestWeb.routes.config_helpers import _build_effective_graph_config

    resultado = SimpleNamespace(
        params_tecnicos=None,
        fecha_inicio_datos=None,
        fecha_fin_datos='2024-01-31',
        intervalo=None,
    )

    assert _build_effective_graph_config(resultado, {'start_date': None}) is None


def test_load_graph_market_data_returns_filtered_symbol():
    import pandas as pd
    from scenarios.BacktestWeb.routes.graph_data import _load_graph_market_data

    market_data = pd.DataFrame([
        {'Symbol': 'AAPL', 'Close': 100},
        {'Symbol': 'MSFT', 'Close': 200},
    ])

    def descargar_datos_func(*args):
        return market_data

    result = _load_graph_market_data(
        'AAPL', '2024-01-01', '2024-01-31', '1d',
        Path('Data_files'), descargar_datos_func, pd.DataFrame,
    )

    assert set(result) == {'AAPL'}
    assert result['AAPL']['Symbol'].tolist() == ['AAPL']


def test_load_graph_market_data_returns_none_when_download_empty():
    import pandas as pd
    from scenarios.BacktestWeb.routes.graph_data import _load_graph_market_data

    def descargar_datos_func(*args):
        return pd.DataFrame()

    result = _load_graph_market_data(
        'AAPL', '2024-01-01', '2024-01-31', '1d',
        Path('Data_files'), descargar_datos_func, pd.DataFrame,
    )

    assert result is None


def test_load_graph_market_data_returns_none_when_symbol_missing():
    import pandas as pd
    from scenarios.BacktestWeb.routes.graph_data import _load_graph_market_data

    market_data = pd.DataFrame([
        {'Symbol': 'MSFT', 'Close': 200},
    ])

    def descargar_datos_func(*args):
        return market_data

    result = _load_graph_market_data(
        'AAPL', '2024-01-01', '2024-01-31', '1d',
        Path('Data_files'), descargar_datos_func, pd.DataFrame,
    )

    assert result is None


def test_run_graph_backtest_returns_symbol_result():
    from scenarios.BacktestWeb.routes.graph_data import _run_graph_backtest

    calls = []
    objeto_resultado = {'stats': 'ok'}

    def fake_run_backtest(stocks_data_dict, system_cls, config_final, symbols, bar_count, logger):
        calls.append((stocks_data_dict, system_cls, config_final, symbols, bar_count, logger))
        return None, None, {'AAPL': objeto_resultado}

    stocks_dict = {'AAPL': 'df'}
    sys_cls = object()
    cfg = {'param': 1}
    logger_obj = object()

    result = _run_graph_backtest(
        stocks_dict, sys_cls, cfg, 'AAPL', fake_run_backtest, logger_obj
    )

    assert result is objeto_resultado
    assert len(calls) == 1
    assert calls[0] == (stocks_dict, sys_cls, cfg, ['AAPL'], 20, logger_obj)


def test_run_graph_backtest_returns_none_when_symbol_missing():
    from scenarios.BacktestWeb.routes.graph_data import _run_graph_backtest

    def fake_run_backtest_empty(*args):
        return None, None, {}

    result_empty = _run_graph_backtest(
        {}, None, {}, 'AAPL', fake_run_backtest_empty, None
    )
    assert result_empty is None

    def fake_run_backtest_none(*args):
        return None, None, None

    result_none = _run_graph_backtest(
        {}, None, {}, 'AAPL', fake_run_backtest_none, None
    )
    assert result_none is None