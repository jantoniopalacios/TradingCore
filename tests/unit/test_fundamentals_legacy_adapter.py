from datetime import date, datetime, timezone

import pandas as pd

from trading_engine.fundamentals.legacy_adapter import build_legacy_eps_dataframe
from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.store import FundamentalStore
from trading_engine.utils import Data_download


def _record(symbol, fiscal_date, provider, value, reported_date=date(2025, 5, 1)):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=reported_date,
        metric="diluted_eps",
        value=value,
        provider=provider,
        source_type="test",
        updated_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


def test_builds_legacy_eps_columns_and_preserves_reported_date(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [_record("AAPL", date(2025, 3, 31), "yahoo", 1.25)],
    )

    result = build_legacy_eps_dataframe(["AAPL"], tmp_path)

    assert list(result.columns) == [
        "Symbol",
        "fiscalDateEnding",
        "reportedDate",
        "Diluted EPS",
    ]
    assert result.iloc[0]["Symbol"] == "AAPL"
    assert result.iloc[0]["reportedDate"] == pd.Timestamp("2025-05-01")
    assert result.iloc[0]["Diluted EPS"] == 1.25


def test_yahoo_has_priority_for_same_fiscal_period(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record("AAPL", date(2025, 3, 31), "alpha_vantage", 1.10),
            _record("AAPL", date(2025, 3, 31), "yahoo", 1.25),
        ],
    )

    result = build_legacy_eps_dataframe(["AAPL"], tmp_path)

    assert len(result) == 1
    assert result.iloc[0]["Diluted EPS"] == 1.25


def test_alpha_vantage_is_used_when_yahoo_is_absent(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "MSFT",
        [_record("MSFT", date(2025, 3, 31), "alpha_vantage", 3.50)],
    )

    result = build_legacy_eps_dataframe(["MSFT"], tmp_path)

    assert len(result) == 1
    assert result.iloc[0]["Diluted EPS"] == 3.50


def test_excludes_rows_without_reported_date(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [_record("AAPL", date(2025, 3, 31), "yahoo", 1.25, reported_date=None)],
    )

    result = build_legacy_eps_dataframe(["AAPL"], tmp_path)

    assert result.empty


def test_returns_one_row_per_symbol_and_fiscal_period(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record("AAPL", date(2025, 3, 31), "yahoo", 1.25),
            _record("AAPL", date(2025, 3, 31), "alpha_vantage", 1.10),
            _record("AAPL", date(2025, 6, 30), "alpha_vantage", 1.40),
        ],
    )

    result = build_legacy_eps_dataframe(["AAPL"], tmp_path)

    assert len(result) == 2
    assert not result.duplicated(["Symbol", "fiscalDateEnding"]).any()


def test_sorts_periods_chronologically_per_symbol(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record("AAPL", date(2025, 6, 30), "yahoo", 1.40),
            _record("AAPL", date(2024, 12, 31), "yahoo", 1.10),
        ],
    )

    result = build_legacy_eps_dataframe(["AAPL"], tmp_path)

    assert result["fiscalDateEnding"].tolist() == [
        pd.Timestamp("2024-12-31"),
        pd.Timestamp("2025-06-30"),
    ]


def test_normalized_cache_is_used_without_calling_legacy_download(tmp_path, monkeypatch):
    FundamentalStore(tmp_path).merge_records(
        "AAPL",
        [_record("AAPL", date(2025, 3, 31), "yahoo", 1.25)],
    )
    monkeypatch.setattr(
        Data_download,
        "update_normalized_fundamentals_if_enabled",
        lambda *args: [],
    )

    def fail_legacy(*args):
        raise AssertionError("No debe ejecutarse el fallback con caché normalizada válida")

    monkeypatch.setattr(Data_download, "manage_fundamental_data", fail_legacy)
    symbols = pd.DataFrame({"Symbol": ["AAPL"]})

    result = Data_download.load_fundamental_data_with_fallback(
        symbols,
        "unused",
        tmp_path,
    )

    assert result.iloc[0]["Diluted EPS"] == 1.25


def test_empty_normalized_cache_falls_back_to_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Data_download,
        "update_normalized_fundamentals_if_enabled",
        lambda *args: [],
    )
    legacy_data = pd.DataFrame({"Symbol": ["AAPL"], "Diluted EPS": [1.0]})
    legacy_calls = []

    def fake_legacy(symbols_df, api_key, fundamentals_path):
        legacy_calls.append(symbols_df["Symbol"].tolist())
        return legacy_data

    monkeypatch.setattr(Data_download, "manage_fundamental_data", fake_legacy)
    symbols = pd.DataFrame({"Symbol": ["AAPL", "MSFT"]})

    result = Data_download.load_fundamental_data_with_fallback(
        symbols,
        "unused",
        tmp_path,
    )

    assert result is legacy_data
    assert legacy_calls == [["AAPL", "MSFT"]]
    assert symbols["Symbol"].tolist() == ["AAPL", "MSFT"]


def test_adapter_error_falls_back_to_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Data_download,
        "update_normalized_fundamentals_if_enabled",
        lambda *args: (_ for _ in ()).throw(RuntimeError("adapter error")),
    )
    legacy_data = pd.DataFrame({"Symbol": ["AAPL"]})
    monkeypatch.setattr(
        Data_download,
        "manage_fundamental_data",
        lambda *args: legacy_data,
    )

    result = Data_download.load_fundamental_data_with_fallback(
        pd.DataFrame({"Symbol": ["AAPL"]}),
        "unused",
        tmp_path,
    )

    assert result is legacy_data

def test_partial_normalized_cache_falls_back_to_legacy(tmp_path, monkeypatch):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [_record("AAPL", date(2025, 3, 31), "yahoo", 1.25)],
    )

    monkeypatch.setattr(
        Data_download,
        "update_normalized_fundamentals_if_enabled",
        lambda *args: [],
    )

    legacy_data = pd.DataFrame(
        {
            "Symbol": ["AAPL", "MSFT"],
            "Diluted EPS": [1.25, 3.50],
        }
    )

    monkeypatch.setattr(
        Data_download,
        "manage_fundamental_data",
        lambda *args: legacy_data,
    )

    symbols = pd.DataFrame({"Symbol": ["AAPL", "MSFT"]})

    result = Data_download.load_fundamental_data_with_fallback(
        symbols,
        "unused",
        tmp_path,
    )

    assert result is legacy_data