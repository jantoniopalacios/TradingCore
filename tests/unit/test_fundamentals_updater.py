from datetime import date, datetime, timezone

from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.store import FundamentalStore
from trading_engine.fundamentals.updater import FundamentalUpdater


def _record(symbol, fiscal_date, reported_date, value):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=reported_date,
        metric="diluted_eps",
        value=value,
        provider="yahoo",
        source_type="test",
        updated_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
    )


class FakeYahooProvider:
    def __init__(self, records_by_symbol=None, errors_by_symbol=None):
        self.records_by_symbol = records_by_symbol or {}
        self.errors_by_symbol = errors_by_symbol or {}
        self.calls = []

    def fetch_records(self, symbol):
        self.calls.append(symbol)

        if symbol in self.errors_by_symbol:
            raise self.errors_by_symbol[symbol]

        return list(self.records_by_symbol.get(symbol, []))


def test_normalize_symbols_removes_blanks_duplicates_and_normalizes_case():
    assert FundamentalUpdater.normalize_symbols(
        ["aapl", " MSFT ", "", "AAPL", "zts"]
    ) == ["AAPL", "MSFT", "ZTS"]


def test_update_symbols_uses_exact_received_universe(tmp_path):
    provider = FakeYahooProvider()
    updater = FundamentalUpdater(
        store=FundamentalStore(tmp_path),
        yahoo_provider=provider,
    )

    updater.update_symbols(["AAPL", "MSFT", "AAPL"])

    assert provider.calls == ["AAPL", "MSFT"]


def test_update_symbol_merges_yahoo_records_into_store(tmp_path):
    record = _record(
        "AAPL",
        date(2025, 6, 30),
        date(2025, 8, 1),
        1.60,
    )
    provider = FakeYahooProvider(
        records_by_symbol={"AAPL": [record]}
    )
    store = FundamentalStore(tmp_path)
    updater = FundamentalUpdater(store, provider)

    result = updater.update_symbol("AAPL")

    assert result.status == "updated"
    assert result.fetched_records == 1
    assert result.stored_records == 1
    assert result.unique_fiscal_periods == 1

    stored = store.load("AAPL")
    assert len(stored) == 1
    assert stored.iloc[0]["value"] == 1.60


def test_update_symbol_with_existing_data_and_no_new_yahoo_data(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record(
                "AAPL",
                date(2025, 3, 31),
                date(2025, 5, 1),
                1.50,
            )
        ],
    )

    provider = FakeYahooProvider(records_by_symbol={"AAPL": []})
    updater = FundamentalUpdater(store, provider)

    result = updater.update_symbol("AAPL")

    assert result.status == "no_new_data"
    assert result.fetched_records == 0
    assert result.stored_records == 1


def test_update_symbol_reports_no_data_when_store_and_yahoo_are_empty(tmp_path):
    provider = FakeYahooProvider(records_by_symbol={"SAN.MC": []})
    updater = FundamentalUpdater(
        FundamentalStore(tmp_path),
        provider,
    )

    result = updater.update_symbol("SAN.MC")

    assert result.status == "no_data"
    assert result.stored_records == 0
    assert result.unique_fiscal_periods == 0
    assert result.message is not None


def test_update_symbol_preserves_existing_data_when_provider_errors(tmp_path):
    store = FundamentalStore(tmp_path)
    store.merge_records(
        "AAPL",
        [
            _record(
                "AAPL",
                date(2025, 3, 31),
                date(2025, 5, 1),
                1.50,
            )
        ],
    )

    provider = FakeYahooProvider(
        errors_by_symbol={"AAPL": RuntimeError("Yahoo temporalmente no disponible")}
    )
    updater = FundamentalUpdater(store, provider)

    result = updater.update_symbol("AAPL")

    assert result.status == "error"
    assert result.stored_records == 1
    assert "Yahoo temporalmente no disponible" in result.message

    stored = store.load("AAPL")
    assert len(stored) == 1


def test_update_symbols_continues_after_error_in_one_symbol(tmp_path):
    provider = FakeYahooProvider(
        records_by_symbol={
            "MSFT": [
                _record(
                    "MSFT",
                    date(2025, 6, 30),
                    date(2025, 7, 30),
                    3.65,
                )
            ]
        },
        errors_by_symbol={
            "AAPL": RuntimeError("fallo controlado")
        },
    )

    updater = FundamentalUpdater(
        FundamentalStore(tmp_path),
        provider,
    )

    results = updater.update_symbols(["AAPL", "MSFT"])

    assert [result.symbol for result in results] == ["AAPL", "MSFT"]
    assert results[0].status == "error"
    assert results[1].status == "updated"
    assert provider.calls == ["AAPL", "MSFT"]
