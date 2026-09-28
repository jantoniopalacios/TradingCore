from datetime import date, datetime, timezone

import pandas as pd

from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.store import FundamentalStore


def _record(
    symbol="AAPL",
    fiscal_date=date(2025, 3, 31),
    reported_date=date(2025, 5, 1),
    value=1.50,
    provider="yahoo",
    source_type="reported_eps",
    updated_at=None,
):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=reported_date,
        metric="diluted_eps",
        value=value,
        provider=provider,
        source_type=source_type,
        updated_at=updated_at or datetime(2025, 5, 1, tzinfo=timezone.utc),
    )


def test_store_creates_one_accumulative_file_per_symbol(tmp_path):
    store = FundamentalStore(tmp_path)

    store.merge_records("AAPL", [_record()])

    assert (tmp_path / "AAPL.csv").exists()
    assert not list(tmp_path.glob("Q?_AAPL.csv"))


def test_store_preserves_different_providers_for_same_period(tmp_path):
    store = FundamentalStore(tmp_path)

    store.merge_records(
        "AAPL",
        [
            _record(value=1.50, provider="yahoo"),
            _record(value=1.47, provider="alpha_vantage"),
        ],
    )

    df = store.load("AAPL")

    assert len(df) == 2
    assert set(df["provider"]) == {"yahoo", "alpha_vantage"}
    assert set(df["value"]) == {1.50, 1.47}


def test_same_provider_same_period_keeps_latest_observation(tmp_path):
    store = FundamentalStore(tmp_path)

    older = _record(
        value=1.40,
        updated_at=datetime(2025, 5, 1, tzinfo=timezone.utc),
    )
    newer = _record(
        value=1.50,
        updated_at=datetime(2025, 5, 2, tzinfo=timezone.utc),
    )

    store.merge_records("AAPL", [older, newer])

    df = store.load("AAPL")

    assert len(df) == 1
    assert df.iloc[0]["value"] == 1.50


def test_available_as_of_uses_reported_date_not_fiscal_date(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record(
                fiscal_date=date(2025, 3, 31),
                reported_date=date(2025, 5, 1),
                value=1.50,
            )
        ],
    )

    before_report = store.available_as_of(
        "AAPL",
        date(2025, 4, 15),
        metric="diluted_eps",
    )
    after_report = store.available_as_of(
        "AAPL",
        date(2025, 5, 1),
        metric="diluted_eps",
    )

    assert before_report.empty
    assert len(after_report) == 1
    assert after_report.iloc[0]["value"] == 1.50


def test_available_as_of_excludes_records_without_reported_date(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record(
                reported_date=None,
                value=1.50,
            )
        ],
    )

    result = store.available_as_of(
        "AAPL",
        date(2030, 1, 1),
        metric="diluted_eps",
    )

    assert result.empty


def test_coverage_summary_counts_unique_fiscal_periods(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record(
                fiscal_date=date(2025, 3, 31),
                reported_date=date(2025, 5, 1),
                value=1.50,
                provider="yahoo",
            ),
            _record(
                fiscal_date=date(2025, 3, 31),
                reported_date=date(2025, 5, 1),
                value=1.47,
                provider="alpha_vantage",
            ),
            _record(
                fiscal_date=date(2025, 6, 30),
                reported_date=date(2025, 8, 1),
                value=1.60,
                provider="yahoo",
            ),
        ],
    )

    summary = store.coverage_summary("AAPL")

    assert summary["records"] == 3
    assert summary["unique_fiscal_periods"] == 2
    assert summary["first_fiscal_date"] == "2025-03-31"
    assert summary["last_fiscal_date"] == "2025-06-30"
    assert summary["providers"] == ["alpha_vantage", "yahoo"]


def test_store_rejects_record_for_other_symbol(tmp_path):
    store = FundamentalStore(tmp_path)

    try:
        store.merge_records("AAPL", [_record(symbol="MSFT")])
    except ValueError as exc:
        assert "MSFT" in str(exc)
    else:
        raise AssertionError("Se esperaba ValueError")
