from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
from bokeh.models import RadioButtonGroup

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
    full_ratio_path = backtesting_path / "Run_Results" / "Global" / "FullRatio"
    fundamentals_path.mkdir()
    full_ratio_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dashboard_module, "DATA_FILES_BASE_PATH", tmp_path)
    monkeypatch.setattr(dashboard_module, "BACKTESTING_BASE_DIR", backtesting_path)
    return fundamentals_path, full_ratio_path


def _add_eps_periods(store, symbol="AAPL", count=8, reported_date=date(2025, 8, 1)):
    store.merge_records(
        symbol,
        [
            _record(
                symbol,
                date(2020 + index // 4, 3 + (index % 4) * 3, 1),
                reported_date,
                1.0 + index / 10,
            )
            for index in range(count)
        ],
    )


def _write_valuation(full_ratio_path, rows):
    full_ratio_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        full_ratio_path / "FR_diario.csv",
        sep=";",
        index=False,
    )

def _valuation_row(symbol="AAPL", date_value="2025-08-15", **overrides):
    row = {
        "Date": date_value,
        "Symbol": symbol,
        "Close": 150.0,
        "PER": 18.5,
        "LTM EPS": 8.1,
        "LTM EPS %": 12.5,
        "PER M5Y": 24.0,
        "% PER vs PER M5Y": -22.9,
        "Margen de seguridad": 35.4,
        "Full Ratio": 1.91,
    }
    row.update(overrides)
    return row


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
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert b"AAPL" in response.data
    assert "No evaluable" in body
    assert "Actualizar y evaluar" in body
    assert "—" in body
    assert 'aria-current="page"' in body
    assert "FUNDAMENTALES" in body
    assert "Volver" not in body
    detail = client.get("/fundamentals/AAPL").get_data(as_text=True)
    assert "Sin datos" in detail
    assert 'aria-current="page"' in detail
    assert "FUNDAMENTALES" in detail


def test_saved_configuration_syncs_added_and_removed_fundamental_symbols(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    _configure_dashboard_paths(monkeypatch, tmp_path)
    import scenarios.BacktestWeb.routes.main_bp as main_module

    monkeypatch.setattr(
        main_module,
        "CONFIG_SNAPSHOT_BASE_DIR",
        tmp_path / "config-snapshots",
    )
    _login(client, "dashboard-user")

    added = client.post(
        "/save_config_file",
        data={"symbols_content": "AAPL, MSFT", "config_file_name": "symbols.json"},
    )
    first_dashboard = client.get("/fundamentals").get_data(as_text=True)

    assert added.status_code == 200
    assert added.get_json()["status"] == "success"
    assert "AAPL" in first_dashboard
    assert "MSFT" in first_dashboard

    removed = client.post(
        "/save_config_file",
        data={"symbols_content": "MSFT, NVDA", "config_file_name": "symbols.json"},
    )
    second_dashboard = client.get("/fundamentals").get_data(as_text=True)

    assert removed.status_code == 200
    assert removed.get_json()["status"] == "success"
    assert "AAPL" not in second_dashboard
    assert "MSFT" in second_dashboard
    assert "NVDA" in second_dashboard


def test_dashboard_handles_saved_valuation_without_minimum_columns(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=8)
    pd.DataFrame({"Close": [150.0]}).to_csv(
        full_ratio_path / "FR_diario.csv",
        sep=";",
        index=False,
    )
    _login(client, "dashboard-user")

    response = client.get("/fundamentals")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'aria-current="page"' in body
    assert "FUNDAMENTALES" in body
    assert "Eval." in body
    assert "Valoración" in body
    assert "AAPL" in body
    assert "Internal Server Error" not in body
    assert "Traceback (most recent call last)" not in body
    assert "Parcial" in body
    assert "No evaluable" in body


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
    detail = client.get("/fundamentals/AAPL")
    body = detail.get_data(as_text=True)

    assert response.status_code == 200
    assert detail.status_code == 200
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
    detail = client.get("/fundamentals/AAPL")
    body = detail.get_data(as_text=True)

    assert response.status_code == 200
    assert detail.status_code == 200
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


def test_evaluation_status_distinguishes_no_partial_and_complete():
    eps_records = pd.DataFrame({"metric": ["diluted_eps"]})
    complete_valuation = {
        "PER": 18.5,
        "LTM EPS %": 12.5,
        "PER M5Y": 24.0,
        "Margen de seguridad": 35.4,
        "Full Ratio": 1.91,
    }

    assert dashboard_module._evaluation_status(
        eps_records, 3, "2025-08-01", complete_valuation, "2025-08-15"
    )[0] == "No"
    assert dashboard_module._evaluation_status(
        eps_records, 4, "2025-08-01", None, "2025-08-15"
    )[0] == "Parcial"
    assert "20 PER" in dashboard_module._evaluation_status(
        eps_records, 8, "2025-08-01", None, "2025-08-15"
    )[1]
    assert dashboard_module._evaluation_status(
        eps_records, 4, "2025-08-01", complete_valuation, "2025-08-15"
    )[0] == "Sí"
    assert "reportedDate" in dashboard_module._evaluation_status(
        eps_records, 4, None, complete_valuation, "2025-08-15"
    )[1]


def test_dashboard_uses_compact_investment_columns_and_saved_values(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path))
    _write_valuation(full_ratio_path, [_valuation_row()])
    _login(client, "dashboard-user")

    response = client.get("/fundamentals")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for heading in (
        "Ticker",
        "Último informe",
        "Eval.",
        "PER",
        "LTM EPS %",
        "Margen seg.",
        "Full Ratio",
        "Valoración",
    ):
        assert f"<th>{heading}" in body
    for removed_heading in (
        "<th>Registros</th>",
        "<th>Periodos EPS</th>",
        "<th>Primer fiscal</th>",
        "<th>Último fiscal</th>",
        "<th>Proveedores",
        "<th>Cobertura",
        "<th>Bootstrap",
        "<th>LTM EPS <",
        "<th>PER M5Y",
    ):
        assert removed_heading not in body
    assert "2025-08-01" in body
    assert "Sí" in body
    assert "18.50" in body
    assert "12.50%" in body
    assert "35.40" in body
    assert "1.91" in body
    assert "Mantener" in body
    assert 'id="select-all-symbols"' in body
    assert 'class="form-check-input symbol-select"' in body
    assert "0 seleccionados" in body
    assert "Actualizar fundamentales" in body
    assert "Evaluar seleccionados" in body


def test_action_endpoints_require_selection_and_reject_unconfigured_symbols(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    _configure_dashboard_paths(monkeypatch, tmp_path)

    unauthenticated = client.post("/fundamentals/update", json={"symbols": ["AAPL"]})
    _login(client, "dashboard-user")

    empty = client.post("/fundamentals/update", json={"symbols": []})
    unconfigured = client.post("/fundamentals/evaluate", json={"symbols": ["NVDA"]})

    assert unauthenticated.status_code == 401
    assert empty.status_code == 400
    assert "No hay activos seleccionados" in empty.get_json()["message"]
    assert unconfigured.status_code == 403


def test_update_action_only_updates_selected_symbols_without_running_full_ratio(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols(symbols=("AAPL", "MSFT"))
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    _login(client, "dashboard-user")
    update_calls = []

    def fake_update(symbols, path):
        update_calls.append((symbols, path))
        return [
            SimpleNamespace(
                yahoo_status="updated",
                bootstrap_status="not_requested",
            )
        ]

    from trading_engine.utils import Calculos_Financieros, Data_download

    monkeypatch.delenv("ALPHA_VANTAGE_KEY", raising=False)
    monkeypatch.setattr(Data_download, "update_normalized_fundamentals", fake_update)
    monkeypatch.setattr(
        Calculos_Financieros,
        "calcular_fullratio_OHLCV",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Actualizar no debe calcular Full Ratio")
        ),
    )

    response = client.post("/fundamentals/update", json={"symbols": ["MSFT"]})

    assert response.status_code == 200
    assert update_calls == [(["MSFT"], fundamentals_path)]
    assert response.get_json()["status"] == "success"
    assert response.get_json()["message"] == "Fundamentales actualizados para 1 activos."


def test_evaluate_action_uses_selected_normalized_data_and_preserves_other_symbols(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols(symbols=("AAPL", "MSFT"))
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _login(client, "dashboard-user")
    _write_valuation(
        full_ratio_path,
        [
            _valuation_row("AAPL", "2025-08-14", **{"Full Ratio": 0.2}),
            _valuation_row("MSFT", "2025-08-15", **{"Full Ratio": 0.7}),
            _valuation_row("MSFT", "2025-08-15", **{"Full Ratio": 0.8}),
        ],
    )
    adapter_calls = []
    ohlcv_calls = []
    calculation_calls = []

    def fake_adapter(symbols, path):
        adapter_calls.append((symbols, path))
        return pd.DataFrame(
            {
                "Symbol": ["AAPL"] * 4,
                "fiscalDateEnding": pd.to_datetime(
                    ["2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31"]
                ),
                "reportedDate": pd.to_datetime(
                    ["2024-05-01", "2024-08-01", "2024-11-01", "2025-02-01"]
                ),
                "Diluted EPS": [1.0, 1.1, 1.2, 1.3],
            }
        )

    def fake_ohlcv(symbols, intervalo, data_files_path):
        ohlcv_calls.append((symbols, intervalo, data_files_path))
        return pd.DataFrame(
            {
                "Symbol": ["AAPL"],
                "Close": [150.0],
                "Open": [149.0],
                "High": [151.0],
                "Low": [148.0],
                "Volume": [1000],
            },
            index=pd.DatetimeIndex(["2025-08-15"], name="Date"),
        )

    recalculated = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "PER": [17.0],
            "LTM EPS %": [10.0],
            "PER M5Y": [22.0],
            "% PER vs PER M5Y": [-22.7],
            "Margen de seguridad": [32.7],
            "Full Ratio": [1.92],
        },
        index=pd.DatetimeIndex(["2025-08-15"], name="Date"),
    )

    def fake_calculation(ohlcv, financial):
        calculation_calls.append((ohlcv, financial))
        return recalculated

    def fake_selection(data, logger):
        return pd.DataFrame(
            {"Recomendación": ["Mantener (Atractivo)"]},
            index=pd.Index(["AAPL"], name="Symbol"),
        )

    from trading_engine.utils import Calculos_Financieros, Data_download

    monkeypatch.setattr(dashboard_module, "build_legacy_eps_dataframe", fake_adapter)
    monkeypatch.setattr(Data_download, "load_or_download_full_ohlcv", fake_ohlcv)
    monkeypatch.setattr(Data_download, "update_normalized_fundamentals", lambda *a, **k: pytest.fail("No debe actualizar"))
    monkeypatch.setattr(Data_download, "manage_fundamental_data", lambda *a, **k: pytest.fail("No debe usar fallback"))
    monkeypatch.setattr(Calculos_Financieros, "calcular_fullratio_OHLCV", fake_calculation)
    monkeypatch.setattr(Calculos_Financieros, "generar_seleccion_activos", fake_selection)

    response = client.post("/fundamentals/evaluate", json={"symbols": ["AAPL"]})

    saved = pd.read_csv(full_ratio_path / "FR_diario.csv", sep=";")
    assert response.status_code == 200
    assert adapter_calls == [(["AAPL"], fundamentals_path)]
    assert ohlcv_calls == [(["AAPL"], "1d", tmp_path)]
    assert len(calculation_calls) == 1
    assert response.get_json()["evaluated"] == 1
    assert set(saved["Symbol"]) == {"AAPL", "MSFT"}
    assert len(saved[saved["Symbol"] == "AAPL"]) == 1
    assert saved.loc[saved["Symbol"] == "AAPL", "Full Ratio"].iloc[0] == 1.92
    assert len(saved[saved["Symbol"] == "MSFT"]) == 1
    assert not saved.duplicated(["Symbol", "Date"]).any()

    _create_user_and_symbols(username="user-b", symbols=("AAPL",))
    _login(client, "user-b")
    user_b_dashboard = client.get("/fundamentals").get_data(as_text=True)
    assert "17.00" in user_b_dashboard
    assert "AAPL" in user_b_dashboard
    assert "MSFT" not in user_b_dashboard


def test_legacy_user_valuation_files_migrate_deterministically_once(
    monkeypatch,
    tmp_path,
):
    _, global_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    run_results = tmp_path / "Backtesting" / "Run_Results"
    alice_path = run_results / "alice" / "FullRatio"
    bob_path = run_results / "bob" / "FullRatio"
    _write_valuation(
        alice_path,
        [
            _valuation_row("AAPL", "2025-08-14", **{"Full Ratio": 0.5}),
            _valuation_row("AAPL", "2025-08-15", **{"Full Ratio": 1.0}),
            _valuation_row("MSFT", "2025-08-15", **{"Full Ratio": 2.0}),
        ],
    )
    _write_valuation(
        bob_path,
        [_valuation_row("AAPL", "2025-08-15", **{"Full Ratio": 3.0})],
    )

    dashboard_module._dashboard_paths("new-user")

    migrated = pd.read_csv(global_path / "FR_diario.csv", sep=";")
    assert not migrated.duplicated(["Symbol", "Date"]).any()
    aapl_rows = migrated[migrated["Symbol"] == "AAPL"].set_index("Date")
    assert len(aapl_rows) == 2
    assert aapl_rows.loc["2025-08-14", "Full Ratio"] == 0.5
    assert aapl_rows.loc["2025-08-15", "Full Ratio"] == 3.0
    assert migrated.set_index("Symbol").loc["MSFT", "Full Ratio"] == 2.0
    assert (alice_path / "FR_diario.csv").exists()
    assert (bob_path / "FR_diario.csv").exists()

    (global_path / "FR_diario.csv").write_text(
        "Date;Symbol;Full Ratio\n2025-08-16;NVDA;4.0\n",
        encoding="utf-8",
    )
    dashboard_module._dashboard_paths("another-user")
    existing_global = pd.read_csv(global_path / "FR_diario.csv", sep=";")
    assert existing_global["Symbol"].tolist() == ["NVDA"]


def test_invalid_global_valuation_file_is_not_overwritten(monkeypatch, tmp_path):
    _, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    invalid_path = full_ratio_path / "FR_diario.csv"
    invalid_path.write_text("Close\n150.0\n", encoding="utf-8")
    original_contents = invalid_path.read_bytes()

    with pytest.raises(ValueError, match="Date y Symbol"):
        dashboard_module._persist_selected_valuation(
            full_ratio_path,
            pd.DataFrame(
                [{"Date": "2025-08-15", "Symbol": "AAPL", "PER": 18.5}]
            ),
            ["AAPL"],
        )

    assert invalid_path.read_bytes() == original_contents


def test_update_and_evaluate_updates_then_evaluates_normalized_eps(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _login(client, "dashboard-user")
    calls = []

    def fake_update(symbols, path):
        calls.append("update")
        _add_eps_periods(FundamentalStore(path), symbol="AAPL", count=8)
        return [
            SimpleNamespace(
                symbol="AAPL",
                yahoo_status="updated",
                bootstrap_status="not_requested",
            )
        ]

    def fake_ohlcv(symbols, intervalo, data_files_path):
        calls.append("ohlcv")
        assert symbols == ["AAPL"]
        return pd.DataFrame(
            {"Symbol": ["AAPL"], "Close": [150.0]},
            index=pd.DatetimeIndex(["2025-08-15"], name="Date"),
        )

    def fake_calculation(ohlcv, financial):
        calls.append("calculate")
        assert len(financial) == 8
        return pd.DataFrame(
            {
                "Date": ["2025-08-15"],
                "Symbol": ["AAPL"],
                "LTM EPS": [8.1],
                "LTM EPS %": [12.5],
                "PER": [18.5],
                "PER M5Y": [24.0],
                "% PER vs PER M5Y": [-22.9],
                "Margen de seguridad": [35.4],
                "Full Ratio": [1.91],
            }
        )

    def fake_selection(data, logger):
        calls.append("selection")
        return pd.DataFrame(
            {"Recomendación": ["Mantener (Atractivo)"]},
            index=pd.Index(["AAPL"], name="Symbol"),
        )

    from trading_engine.utils import Calculos_Financieros, Data_download

    monkeypatch.setattr(dashboard_module, "_update_normalized_fundamentals", fake_update)
    monkeypatch.setattr(
        dashboard_module,
        "build_legacy_eps_dataframe",
        lambda *args, **kwargs: pytest.fail("La acción combinada no debe usar legacy"),
    )
    monkeypatch.setattr(Data_download, "load_or_download_full_ohlcv", fake_ohlcv)
    monkeypatch.setattr(Calculos_Financieros, "calcular_fullratio_OHLCV", fake_calculation)
    monkeypatch.setattr(Calculos_Financieros, "generar_seleccion_activos", fake_selection)

    response = client.post("/fundamentals/update-and-evaluate", json={"symbols": ["AAPL"]})
    saved = pd.read_csv(full_ratio_path / "FR_diario.csv", sep=";")

    assert response.status_code == 200
    assert calls == ["update", "ohlcv", "calculate", "selection"]
    assert response.get_json()["status"] == "success"
    assert response.get_json()["updated_count"] == 1
    assert response.get_json()["evaluated_count"] == 1
    assert saved.loc[saved["Symbol"] == "AAPL", "PER"].iloc[0] == 18.5
    assert saved.loc[saved["Symbol"] == "AAPL", "Full Ratio"].iloc[0] == 1.91
    dashboard_body = client.get("/fundamentals").get_data(as_text=True)
    assert "18.50" in dashboard_body
    assert "Mantener" in dashboard_body


def test_update_and_evaluate_continues_with_cache_when_alpha_vantage_quota_blocked(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols(symbols=("AAPL", "MSFT"))
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    store = FundamentalStore(fundamentals_path)
    _add_eps_periods(store, symbol="AAPL", count=8)
    _add_eps_periods(store, symbol="MSFT", count=3)
    _write_valuation(full_ratio_path, [_valuation_row("MSFT", "2025-08-15", **{"Full Ratio": 0.77})])
    _login(client, "dashboard-user")

    def fake_update(symbols, path):
        return [
            SimpleNamespace(
                symbol="AAPL",
                yahoo_status="no_new_data",
                bootstrap_status="completed",
            ),
            SimpleNamespace(
                symbol="MSFT",
                yahoo_status="no_new_data",
                bootstrap_status="quota_blocked",
            ),
        ]

    def fake_ohlcv(symbols, intervalo, data_files_path):
        assert symbols == ["AAPL"]
        return pd.DataFrame(
            {"Symbol": ["AAPL"], "Close": [150.0]},
            index=pd.DatetimeIndex(["2025-08-15"], name="Date"),
        )

    from trading_engine.utils import Calculos_Financieros, Data_download

    monkeypatch.setattr(dashboard_module, "_update_normalized_fundamentals", fake_update)
    monkeypatch.setattr(
        dashboard_module,
        "build_legacy_eps_dataframe",
        lambda *args, **kwargs: pytest.fail("La acción combinada no debe usar legacy"),
    )
    monkeypatch.setattr(Data_download, "load_or_download_full_ohlcv", fake_ohlcv)
    monkeypatch.setattr(
        Calculos_Financieros,
        "calcular_fullratio_OHLCV",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "Date": ["2025-08-15"],
                "Symbol": ["AAPL"],
                "LTM EPS": [8.1],
                "LTM EPS %": [12.5],
                "PER": [18.5],
                "PER M5Y": [24.0],
                "% PER vs PER M5Y": [-22.9],
                "Margen de seguridad": [35.4],
                "Full Ratio": [1.91],
            }
        ),
    )
    monkeypatch.setattr(
        Calculos_Financieros,
        "generar_seleccion_activos",
        lambda *args, **kwargs: pd.DataFrame(
            {"Recomendación": ["Mantener (Atractivo)"]},
            index=pd.Index(["AAPL"], name="Symbol"),
        ),
    )

    response = client.post(
        "/fundamentals/update-and-evaluate",
        json={"symbols": ["AAPL", "MSFT"]},
    )
    result = response.get_json()
    saved = pd.read_csv(full_ratio_path / "FR_diario.csv", sep=";")

    assert response.status_code == 200
    assert result["status"] == "partial"
    assert result["evaluated_count"] == 1
    assert result["insufficient_count"] == 1
    assert result["quota_blocked_count"] == 1
    assert "Alpha Vantage" in result["message"]
    assert "cuota diaria" in result["message"]
    assert saved.loc[saved["Symbol"] == "MSFT", "Full Ratio"].iloc[0] == 0.77
    assert saved.loc[saved["Symbol"] == "AAPL", "Full Ratio"].iloc[0] == 1.91


def test_update_and_evaluate_without_alpha_vantage_key_uses_cache_neutrally(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=3)
    _login(client, "dashboard-user")
    monkeypatch.delenv("ALPHA_VANTAGE_KEY", raising=False)

    from trading_engine.utils import Data_download

    monkeypatch.setattr(
        dashboard_module,
        "_update_normalized_fundamentals",
        lambda symbols, path: [
            SimpleNamespace(
                symbol="AAPL",
                yahoo_status="no_new_data",
                bootstrap_status="not_requested",
            )
        ],
    )
    monkeypatch.setattr(
        dashboard_module,
        "build_legacy_eps_dataframe",
        lambda *args, **kwargs: pytest.fail("La acción combinada no debe usar legacy"),
    )
    monkeypatch.setattr(
        Data_download,
        "load_or_download_full_ohlcv",
        lambda *args, **kwargs: pytest.fail("No hay EPS suficiente para cargar OHLCV"),
    )

    response = client.post("/fundamentals/update-and-evaluate", json={"symbols": ["AAPL"]})
    result = response.get_json()

    assert response.status_code == 200
    assert result["status"] == "partial"
    assert result["quota_blocked_count"] == 0
    assert "histórico suficiente" in result["message"]
    assert "error" not in result["message"].lower()


def test_evaluate_without_four_normalized_eps_periods_does_not_download_or_fallback(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=3)
    _login(client, "dashboard-user")

    from trading_engine.utils import Data_download

    monkeypatch.setattr(
        Data_download,
        "load_or_download_full_ohlcv",
        lambda *args, **kwargs: pytest.fail("No debe descargar OHLCV sin EPS suficiente"),
    )
    monkeypatch.setattr(
        Data_download,
        "manage_fundamental_data",
        lambda *args, **kwargs: pytest.fail("No debe usar fallback legacy"),
    )

    response = client.post("/fundamentals/evaluate", json={"symbols": ["AAPL"]})
    saved = pd.read_csv(full_ratio_path / "FR_diario.csv", sep=";")

    assert response.status_code == 200
    assert response.get_json()["status"] == "partial"
    assert response.get_json()["insufficient"] == 1
    assert "Actualiza fundamentales" in response.get_json()["message"]
    assert "Symbol" in saved.columns
    assert saved.empty


def test_evaluation_and_valuation_use_the_same_global_market_date(monkeypatch, tmp_path):
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), "AAPL")
    _add_eps_periods(FundamentalStore(fundamentals_path), "MSFT")
    _write_valuation(
        full_ratio_path,
        [
            _valuation_row("AAPL", "2025-08-14"),
            _valuation_row("MSFT", "2025-08-15", **{"Full Ratio": -0.5}),
        ],
    )
    rows, _ = dashboard_module._load_dashboard_data(
        ["AAPL", "MSFT"], fundamentals_path, full_ratio_path
    )
    rows_by_symbol = {row["symbol"]: row for row in rows}

    assert rows_by_symbol["AAPL"]["evaluation_status"] == "Parcial"
    assert rows_by_symbol["AAPL"]["valuation_label"] == "No evaluable"
    assert rows_by_symbol["AAPL"]["valuation_as_of"] == "2025-08-15"
    assert rows_by_symbol["MSFT"]["evaluation_status"] == "Sí"
    assert rows_by_symbol["MSFT"]["valuation_label"] == "Desestimar"


def test_dashboard_uses_lightweight_rows_and_preserves_valuation_semantics(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols(symbols=("AAPL", "MSFT"))
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=8)
    _add_eps_periods(FundamentalStore(fundamentals_path), symbol="MSFT", count=8)
    _write_valuation(
        full_ratio_path,
        [
            _valuation_row("AAPL", "2025-08-14"),
            _valuation_row("MSFT", "2025-08-15"),
        ],
    )
    _login(client, "dashboard-user")

    from trading_engine.utils import Calculos_Financieros

    monkeypatch.setattr(
        Calculos_Financieros,
        "generar_seleccion_activos",
        lambda data, logger: pd.DataFrame(
            {"Recomendación": ["Mantener (Atractivo)", "Desestimar"]},
            index=pd.Index(["AAPL", "MSFT"], name="Symbol"),
        ),
    )

    read_csv = pd.read_csv
    valuation_reads = []

    def track_csv_read(path, *args, **kwargs):
        if str(path).endswith("FR_diario.csv"):
            valuation_reads.append(path)
        return read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", track_csv_read)
    store_load = FundamentalStore.load
    store_loads = []

    def track_store_load(store, symbol):
        store_loads.append(symbol)
        return store_load(store, symbol)

    monkeypatch.setattr(FundamentalStore, "load", track_store_load)
    monkeypatch.setattr(
        dashboard_module,
        "_load_saved_valuation",
        lambda *args, **kwargs: pytest.fail("No debe releer la valoración por símbolo"),
    )
    monkeypatch.setattr(
        dashboard_module,
        "_build_metric_charts",
        lambda *args, **kwargs: pytest.fail("El dashboard principal no debe construir gráficos"),
    )
    monkeypatch.setattr(
        dashboard_module,
        "build_legacy_eps_dataframe",
        lambda *args, **kwargs: pytest.fail("No debe usar el adaptador legacy"),
    )
    monkeypatch.setattr(
        FundamentalStore,
        "coverage_summary",
        lambda *args, **kwargs: pytest.fail("No debe volver a leer cobertura"),
    )
    monkeypatch.setattr(
        dashboard_module,
        "_load_dashboard_data",
        lambda *args, **kwargs: pytest.fail("La ruta principal no debe usar la carga pesada"),
    )
    rendered = {}

    def capture_render(template, **context):
        rendered.update(context)
        return "ok"

    monkeypatch.setattr(dashboard_module, "render_template", capture_render)

    response = client.get("/fundamentals")

    assert response.status_code == 200
    assert len(valuation_reads) == 1
    assert store_loads == ["AAPL", "MSFT"]
    rows = {row["symbol"]: row for row in rendered["symbols"]}
    aapl = rows["AAPL"]
    msft = rows["MSFT"]
    assert aapl["evaluation_status"] == "Parcial"
    assert aapl["valuation_as_of"] == "2025-08-15"
    assert aapl["valuation_label"] == "Mantener"
    assert aapl["metrics"] == {column: None for column in dashboard_module.VALUATION_COLUMNS}
    assert aapl["per_m5y_depth"] == "Insuficiente (<20 PER válidos)"
    assert msft["evaluation_status"] == "Sí"
    assert msft["latest_reported_date"] == "2025-08-01"
    assert msft["valuation_as_of"] == "2025-08-15"
    assert msft["valuation_label"] == "Desestimar"
    assert msft["metrics"] == {
        "LTM EPS": 8.1,
        "LTM EPS %": 12.5,
        "PER": 18.5,
        "PER M5Y": 24.0,
        "% PER vs PER M5Y": -22.9,
        "Margen de seguridad": 35.4,
        "Full Ratio": 1.91,
    }
    assert msft["ltm_depth"] == "Suficiente (4 trimestres)"
    assert msft["per_m5y_depth"] == "Suficiente (20 PER válidos)"
    assert msft["full_ratio_status"] == "Disponibles"


def test_dashboard_keeps_data_rows_when_another_symbol_has_empty_untyped_data(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols(symbols=("AAPL", "MSFT"))
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=8)
    _write_valuation(full_ratio_path, [_valuation_row("AAPL", "2025-08-15")])
    _login(client, "dashboard-user")

    from trading_engine.utils import Calculos_Financieros

    monkeypatch.setattr(
        Calculos_Financieros,
        "generar_seleccion_activos",
        lambda data, logger: pd.DataFrame(
            {"Recomendación": ["Mantener (Atractivo)"]},
            index=pd.Index(["AAPL"], name="Symbol"),
        ),
    )
    store_load = FundamentalStore.load

    def load_with_empty_msft(store, symbol):
        if symbol == "MSFT":
            return pd.DataFrame()
        return store_load(store, symbol)

    monkeypatch.setattr(FundamentalStore, "load", load_with_empty_msft)
    rendered = {}
    monkeypatch.setattr(
        dashboard_module,
        "render_template",
        lambda template, **context: rendered.update(context) or "ok",
    )

    response = client.get("/fundamentals")

    assert response.status_code == 200
    rows = {row["symbol"]: row for row in rendered["symbols"]}
    assert rows["AAPL"]["evaluation_status"] == "Sí"
    assert rows["AAPL"]["valuation_label"] == "Mantener"
    assert rows["AAPL"]["metrics"]["PER"] == 18.5
    assert rows["AAPL"]["metrics"]["Full Ratio"] == 1.91
    assert rows["MSFT"]["evaluation_status"] == "No"
    assert rows["MSFT"]["valuation_label"] == "No evaluable"
    assert rows["MSFT"]["metrics"] == {
        column: None for column in dashboard_module.VALUATION_COLUMNS
    }


def test_detail_exposes_four_configurable_chart_groups_and_read_only_data(
    client,
    monkeypatch,
    tmp_path,
):
    _create_user_and_symbols()
    fundamentals_path, full_ratio_path = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path))
    _write_valuation(full_ratio_path, [_valuation_row()])
    _login(client, "dashboard-user")
    monkeypatch.setattr(
        FundamentalStore,
        "merge_records",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("El dashboard de detalle no debe escribir en la caché")
        ),
    )

    response = client.get("/fundamentals/AAPL")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    group_specs = dashboard_module._metric_chart_group_specs()
    assert [spec["group_id"] for spec in group_specs] == [
        "chart_group_a_benefit",
        "chart_group_b_per_valuation",
        "chart_group_c_growth_comparison",
        "chart_group_d_full_ratio",
    ]
    assert [spec["metrics"] for spec in group_specs] == [
        ("Diluted EPS", "LTM EPS"),
        ("PER", "PER M5Y"),
        ("LTM EPS %", "% PER vs PER M5Y", "Margen de seguridad"),
        ("Full Ratio",),
    ]
    assert [spec["default_metrics"] for spec in group_specs] == [
        ("Diluted EPS",),
        ("PER", "PER M5Y"),
        ("LTM EPS %", "Margen de seguridad"),
        ("Full Ratio",),
    ]
    chart_group = dashboard_module._build_chart_group(
        title="Grupo con datos",
        metrics=("PER",),
        series_by_metric={
            "PER": [
                {
                    "date": pd.Timestamp("2025-08-15"),
                    "reported_date": "No disponible",
                    "value": 18.5,
                }
            ]
        },
        default_metrics=("PER",),
        x_axis_label="Fecha de mercado",
        group_id="test_chart_group",
    )
    chart_type_models = [
        model
        for model in chart_group.references()
        if isinstance(model, RadioButtonGroup)
    ]
    assert len(chart_type_models) == 1
    assert chart_type_models[0].labels == ["Línea", "Puntos", "Línea + puntos"]
    for metric in (
        "Diluted EPS",
        "LTM EPS",
        "LTM EPS %",
        "PER M5Y",
        "% PER vs PER M5Y",
        "Margen de seguridad",
        "Full Ratio",
    ):
        assert metric in body
    assert "fiscal_date" in body
    assert "reportedDate" in body
    assert "No hay" not in body
    assert "update_normalized_fundamentals" not in body


def test_detail_renders_when_valuation_series_are_missing(client, monkeypatch, tmp_path):
    _create_user_and_symbols()
    fundamentals_path, _ = _configure_dashboard_paths(monkeypatch, tmp_path)
    _add_eps_periods(FundamentalStore(fundamentals_path), count=1)
    _login(client, "dashboard-user")

    response = client.get("/fundamentals/AAPL")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Sin datos disponibles" in body
    assert "—" in body
    assert "NaN" not in body
    assert "Traceback (most recent call last)" not in body
    assert "Internal Server Error" not in body


def test_chart_group_without_series_has_no_controls_or_empty_plot():
    group = dashboard_module._build_chart_group(
        title="Grupo vacío",
        metrics=("PER", "PER M5Y"),
        series_by_metric={},
        default_metrics=("PER", "PER M5Y"),
        x_axis_label="Fecha de mercado",
        group_id="empty_chart_group",
    )

    assert group.name == "empty_chart_group"
    assert len(group.children) == 2
    assert all(child.__class__.__name__ == "Div" for child in group.children)
    assert group.children[1].text == "Sin datos disponibles para este grupo"


def test_chart_group_with_some_missing_metrics_keeps_data_and_lists_missing():
    group = dashboard_module._build_chart_group(
        title="Grupo parcial",
        metrics=("Diluted EPS", "LTM EPS"),
        series_by_metric={
            "Diluted EPS": [
                {
                    "date": pd.Timestamp("2025-03-31"),
                    "reported_date": "2025-05-01",
                    "value": 1.25,
                }
            ],
            "LTM EPS": [],
        },
        default_metrics=("Diluted EPS",),
        x_axis_label="Fecha fiscal",
        group_id="partial_chart_group",
    )

    assert len(group.children) == 4
    assert group.children[2].text == "Sin datos disponibles: LTM EPS"
    assert group.children[3].renderers


def test_eps_chart_series_excludes_records_without_reported_date(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record("AAPL", date(2025, 3, 31), date(2025, 5, 1), 1.25),
            _record("AAPL", date(2025, 6, 30), None, 1.50),
        ],
    )

    series = dashboard_module._build_eps_chart_series(store.load("AAPL"))

    assert len(series) == 1
    assert series[0]["date"] == pd.Timestamp("2025-03-31")
    assert series[0]["reported_date"] == "2025-05-01"
    assert series[0]["value"] == 1.25