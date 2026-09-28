from datetime import date, datetime, timezone

from trading_engine.fundamentals.bootstrap import (
    AlphaVantageBootstrapper,
    BootstrapStateStore,
)
from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.providers.alpha_vantage import (
    AlphaVantageNoData,
    AlphaVantageQuotaExhausted,
)
from trading_engine.fundamentals.store import FundamentalStore


def _record(symbol, fiscal_date=date(2025, 6, 30), provider="alpha_vantage"):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=date(2025, 7, 31),
        metric="diluted_eps",
        value=1.50,
        provider=provider,
        source_type="test",
        updated_at=datetime(2025, 7, 31, tzinfo=timezone.utc),
    )


def _records(symbol, count, provider="alpha_vantage"):
    return [
        _record(symbol, date(2000 + index, 12, 31), provider)
        for index in range(count)
    ]


class FakeAlphaProvider:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    def fetch_records(self, symbol):
        self.calls.append(symbol)
        result = self.behavior[symbol]
        if isinstance(result, Exception):
            raise result
        return result


def _bootstrapper(tmp_path, provider):
    store = FundamentalStore(tmp_path / "fundamentals")
    state_store = BootstrapStateStore(
        tmp_path / "fundamentals" / "bootstrap_state.json"
    )
    return AlphaVantageBootstrapper(
        store=store,
        provider=provider,
        state_store=state_store,
    ), store, state_store


def test_bootstrap_completes_symbol_and_persists_state(tmp_path):
    provider = FakeAlphaProvider({"AAPL": _records("AAPL", 20)})
    bootstrapper, store, state_store = _bootstrapper(tmp_path, provider)

    result = bootstrapper.run(["AAPL"])

    assert result[0].status == "completed"
    assert result[0].fetched_records == 20
    assert len(store.load("AAPL")) == 20

    state = state_store.load()
    assert state["AAPL"].status == "completed"
    assert state["AAPL"].completed_at is not None


def test_completed_symbol_is_not_downloaded_again(tmp_path):
    provider = FakeAlphaProvider({"AAPL": _records("AAPL", 20)})
    bootstrapper, _, _ = _bootstrapper(tmp_path, provider)

    bootstrapper.run(["AAPL"])
    second = bootstrapper.run(["AAPL"])

    assert second[0].status == "skipped_completed"
    assert provider.calls == ["AAPL"]


def test_nineteen_unique_periods_are_partial_without_completed_at(tmp_path):
    provider = FakeAlphaProvider({"AAPL": _records("AAPL", 19)})
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    result = bootstrapper.run(["AAPL"])

    assert result[0].status == "partial"
    state = state_store.load()["AAPL"]
    assert state.status == "partial"
    assert state.completed_at is None


def test_partial_symbol_is_retried_on_next_run(tmp_path):
    provider = FakeAlphaProvider({"AAPL": _records("AAPL", 19)})
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    first = bootstrapper.run(["AAPL"])
    provider.behavior["AAPL"] = _records("AAPL", 20)
    second = bootstrapper.run(["AAPL"])

    assert first[0].status == "partial"
    assert second[0].status == "completed"
    assert provider.calls == ["AAPL", "AAPL"]
    assert state_store.load()["AAPL"].completed_at is not None


def test_coverage_from_store_determines_completion(tmp_path):
    provider = FakeAlphaProvider({"AAPL": [_record("AAPL", date(2025, 12, 31))]})
    bootstrapper, store, state_store = _bootstrapper(tmp_path, provider)
    store.merge_records("AAPL", _records("AAPL", 19, provider="yahoo"))

    result = bootstrapper.run(["AAPL"])

    assert result[0].status == "completed"
    assert store.coverage_summary("AAPL")["unique_fiscal_periods"] == 20
    assert state_store.load()["AAPL"].completed_at is not None


def test_completed_at_is_only_set_for_completed_state(tmp_path):
    provider = FakeAlphaProvider({
        "AAPL": _records("AAPL", 20),
        "MSFT": _records("MSFT", 19),
    })
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    results = bootstrapper.run(["AAPL", "MSFT"])

    assert [result.status for result in results] == ["completed", "partial"]
    state = state_store.load()
    assert state["AAPL"].completed_at is not None
    assert state["MSFT"].completed_at is None


def test_quota_exhaustion_stops_remaining_symbols(tmp_path):
    provider = FakeAlphaProvider(
        {
            "AAPL": _records("AAPL", 20),
            "MSFT": AlphaVantageQuotaExhausted("daily limit"),
            "ZTS": [_record("ZTS")],
        }
    )
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    results = bootstrapper.run(["AAPL", "MSFT", "ZTS"])

    assert [item.status for item in results] == [
        "completed",
        "quota_blocked",
    ]
    assert provider.calls == ["AAPL", "MSFT"]

    state = state_store.load()
    assert state["AAPL"].status == "completed"
    assert state["MSFT"].status == "quota_blocked"
    assert "ZTS" not in state


def test_quota_blocked_symbol_is_retried_next_run(tmp_path):
    provider = FakeAlphaProvider({"MSFT": AlphaVantageQuotaExhausted("daily limit")})
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    bootstrapper.run(["MSFT"])

    provider.behavior["MSFT"] = _records("MSFT", 20)
    second = bootstrapper.run(["MSFT"])

    assert second[0].status == "completed"
    assert provider.calls == ["MSFT", "MSFT"]
    assert state_store.load()["MSFT"].status == "completed"


def test_no_data_is_terminal_until_manual_reset(tmp_path):
    provider = FakeAlphaProvider(
        {"SAN.MC": AlphaVantageNoData("sin datos")}
    )
    bootstrapper, _, state_store = _bootstrapper(tmp_path, provider)

    first = bootstrapper.run(["SAN.MC"])
    second = bootstrapper.run(["SAN.MC"])

    assert first[0].status == "no_data"
    assert second[0].status == "skipped_no_data"
    assert provider.calls == ["SAN.MC"]

    bootstrapper.reset_symbol("SAN.MC")
    assert state_store.load()["SAN.MC"].status == "pending"


def test_regular_error_does_not_stop_next_symbol(tmp_path):
    provider = FakeAlphaProvider(
        {
            "AAPL": RuntimeError("network"),
            "MSFT": _records("MSFT", 20),
        }
    )
    bootstrapper, store, _ = _bootstrapper(tmp_path, provider)

    results = bootstrapper.run(["AAPL", "MSFT"])

    assert [item.status for item in results] == ["error", "completed"]
    assert provider.calls == ["AAPL", "MSFT"]
    assert len(store.load("MSFT")) == 20
