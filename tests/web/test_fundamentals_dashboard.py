from datetime import date, datetime, timezone

import pandas as pd
import pytest

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.database import Simbolo, Usuario, db
from scenarios.BacktestWeb.routes import fundamentals_dashboard as dashboard_module
from trading_engine.fundamentals.bootstrap import BootstrapStateStore, BootstrapSymbolState
from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.store import FundamentalStore


def test_coverage_category_uses_normalized_eps_period_count():
    assert dashboard_module._coverage_label(0) == "Sin datos"
    assert dashboard_module._coverage_label(3) == "Cobertura insuficiente"
    assert dashboard_module._coverage_label(4) == "Cobertura parcial"
    assert dashboard_module._coverage_label(19) == "Cobertura parcial"
    assert dashboard_module._coverage_label(20) == "Cobertura suficiente"


@pytest.fixture
def client(monkeypatch):
    import scenarios.BacktestWeb.app as app_module

    monkeypatch.setattr(app_module, "DB_URI", "sqlite:///:memory:")
    monkeypatch.setattr(app_module, "ENGINE_OPTIONS", {})
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        with app.app_context():
            yield test_client


def _record(symbol, fiscal_date, reported_date, value, provider="yahoo"):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=reported_date,
        metric="diluted_eps",
        value=value,
        provider=provider,
        source_type="test",
        updated_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )


def _configure_dashboard_paths(monkeypatch, tmp_path):
    fundamentals_path = tmp_path / "Fundamentals"
    backtesting_path = tmp_path / "Backtesting"
    full_ratio_path = backtesting_path / "Run_Results" / "dashboard-user" / "FullRatio"
    fundamentals_path.mkdir()
    full_ratio_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dashboard_module, "DATA_FILES_BASE_PATH", tmp_path)
    monkeypatch.setattr(dashboard_module, "BACKTESTING_BASE_DIR", backtesting_path)
    return fundamentals_path, full_ratio_path


def _create_user_and_symbols(username="dashboard-user", symbols=("AAPL",)):
    user = Usuario(username=username, password="offline")
    db.session.add(user)
    db.session.flush()
    for symbol in symbols:
        db.session.add(Simbolo(symbol=symbol, name=symbol, usuario_id=user.id))
    db.session.commit()


def _login(client, username):
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["user_mode"] = username


def test_fundamental_dashboard_requires_login(client):
    response = client.get("/fundamentals")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_shows_configured_symbol_without_normalized_data(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    _configure_dashboard_paths(monkeypatch, tmp_path)
    _login(client, "dashboard-user")

    response = client.get("/fundamentals")

    assert response.status_code == 200
    assert b"AAPL" in response.data
    assert "Sin datos" in response.get_data(as_text=True)


def test_dashboard_coverage_summary_uses_store_and_existing_bootstrap_state(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    store = FundamentalStore(fundamentals_path)
    store.merge_records(
        "AAPL",
        [
            _record("AAPL", date(2025, 3, 31), date(2025, 5, 1), 1.0),
            _record("AAPL", date(2025, 6, 30), date(2025, 8, 1), 1.2),
        ],
    )
    BootstrapStateStore(fundamentals_path / "bootstrap_state.json").save(
        {"AAPL": BootstrapSymbolState(status="partial")}
    )
    _login(client, "dashboard-user")

    response = client.get("/fundamentals")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "2" in body
    assert "Cobertura insuficiente" in body
    assert "partial" in body


def test_dashboard_coverage_is_sufficient_without_saved_valuation(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    FundamentalStore(fundamentals_path).merge_records(
        "AAPL",
        [
            _record(
                "AAPL",
                date(2020 + index // 4, 3 + (index % 4) * 3, 1),
                date(2025, 8, 1),
                1.0,
            )
            for index in range(20)
        ],
    )
    _login(client, "dashboard-user")

    response = client.get("/fundamentals")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Cobertura suficiente" in body
    assert "Suficiente (4 trimestres)" in body
    assert "No calculado" in body
    assert "No disponibles" in body


def test_symbol_detail_is_limited_to_configured_symbols(client, monkeypatch, tmp_path):
    _create_user_and_symbols()
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    FundamentalStore(fundamentals_path).merge_records(
        "AAPL",
        [_record("AAPL", date(2025, 3, 31), date(2025, 5, 1), 1.0)],
    )
    _login(client, "dashboard-user")

    detail = client.get("/fundamentals/AAPL")
    outsider = client.get("/fundamentals/MSFT")

    assert detail.status_code == 200
    assert b"reported_date" in detail.data
    assert outsider.status_code == 404