from datetime import date, datetime, timezone

from trading_engine.fundamentals.bootstrap import BootstrapResult
from trading_engine.fundamentals.models import FundamentalRecord
from trading_engine.fundamentals.service import FundamentalService
from trading_engine.fundamentals.store import FundamentalStore
from trading_engine.fundamentals.updater import FundamentalUpdater


def _record(symbol, fiscal_date, provider, value):
    return FundamentalRecord(
        symbol=symbol,
        fiscal_date=fiscal_date,
        reported_date=date(2025, 8, 1),
        metric="diluted_eps",
        value=value,
        provider=provider,
        source_type="test",
        updated_at=datetime(2025, 8, 2, tzinfo=timezone.utc),
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


class FakeBootstrapper:
    def __init__(self, results_by_symbol=None, records_by_symbol=None):
        self.results_by_symbol = results_by_symbol or {}
        self.records_by_symbol = records_by_symbol or {}
        self.calls = []

    def run(self, symbols):
        results = []
        for symbol in symbols:
            self.calls.append(symbol)
            records = self.records_by_symbol.get(symbol, [])
            if records:
                self.store.merge_records(symbol, records)
            result = self.results_by_symbol.get(
                symbol,
                BootstrapResult(symbol, "completed", len(records)),
            )
            results.append(result)
            if result.status == "quota_blocked":
                break
        return results


def _service(tmp_path, yahoo_provider=None, bootstrapper=None):
    store = FundamentalStore(tmp_path)
    updater = FundamentalUpdater(store, yahoo_provider or FakeYahooProvider())
    bootstrapper = bootstrapper or FakeBootstrapper()
    bootstrapper.store = store
    return FundamentalService(store, updater, bootstrapper), store, yahoo_provider, bootstrapper


def test_normalizes_symbols_and_preserves_order(tmp_path):
    service, _, _, _ = _service(tmp_path)

    results = service.update_for_symbols([" aapl ", "MSFT", "", "AAPL", "zts"])

    assert [result.symbol for result in results] == ["AAPL", "MSFT", "ZTS"]


def test_yahoo_update_and_bootstrap_completion(tmp_path):
    yahoo = FakeYahooProvider(
        records_by_symbol={"AAPL": [_record("AAPL", date(2025, 6, 30), "yahoo", 1.2)]}
    )
    bootstrapper = FakeBootstrapper(
        records_by_symbol={
            "AAPL": [_record("AAPL", date(2024, 12, 31), "alpha_vantage", 4.8)]
        }
    )
    service, _, _, _ = _service(tmp_path, yahoo, bootstrapper)

    result = service.update_for_symbols(["AAPL"])[0]

    assert result.yahoo_status == "updated"
    assert result.bootstrap_status == "completed"
    assert result.providers == ["alpha_vantage", "yahoo"]


def test_completed_bootstrap_state_is_used_without_rebootstrapping(tmp_path):
    bootstrapper = FakeBootstrapper(
        results_by_symbol={
            "MSFT": BootstrapResult("MSFT", "skipped_completed", 0)
        }
    )
    service, _, _, _ = _service(tmp_path, bootstrapper=bootstrapper)

    result = service.update_for_symbols(["MSFT"])[0]

    assert result.bootstrap_status == "skipped_completed"
    assert bootstrapper.calls == ["MSFT"]


def test_quota_exhaustion_stops_remaining_symbols_after_yahoo(tmp_path):
    yahoo = FakeYahooProvider()
    bootstrapper = FakeBootstrapper(
        results_by_symbol={
            "MSFT": BootstrapResult("MSFT", "quota_blocked", 0, "Cuota agotada")
        }
    )
    service, _, _, _ = _service(tmp_path, yahoo, bootstrapper)

    results = service.update_for_symbols(["AAPL", "MSFT", "ZTS", "SAN.MC"])

    assert yahoo.calls == ["AAPL", "MSFT", "ZTS", "SAN.MC"]
    assert bootstrapper.calls == ["AAPL", "MSFT"]
    
    by_symbol = {result.symbol: result for result in results}

    assert by_symbol["AAPL"].bootstrap_status in {"completed", "skipped_completed"}
    assert by_symbol["MSFT"].bootstrap_status == "quota_blocked"
    assert by_symbol["ZTS"].bootstrap_status == "not_run"
    assert by_symbol["SAN.MC"].bootstrap_status == "not_run"


def test_no_data_status_is_preserved_from_bootstrapper(tmp_path):
    bootstrapper = FakeBootstrapper(
        results_by_symbol={"SAN.MC": BootstrapResult("SAN.MC", "no_data", 0)}
    )
    service, _, _, _ = _service(tmp_path, bootstrapper=bootstrapper)

    result = service.update_for_symbols(["SAN.MC"])[0]

    assert result.bootstrap_status == "no_data"


def test_yahoo_error_preserves_existing_history_and_bootstraps(tmp_path):
    yahoo = FakeYahooProvider(errors_by_symbol={"AAPL": RuntimeError("Yahoo offline")})
    bootstrapper = FakeBootstrapper(
        records_by_symbol={
            "AAPL": [_record("AAPL", date(2024, 12, 31), "alpha_vantage", 4.8)]
        }
    )
    service, store, _, _ = _service(tmp_path, yahoo, bootstrapper)
    existing = _record("AAPL", date(2024, 9, 30), "yahoo", 1.1)
    store.merge_records("AAPL", [existing])

    result = service.update_for_symbols(["AAPL"])[0]

    assert result.yahoo_status == "error"
    assert result.bootstrap_status == "completed"
    assert result.stored_records == 2
    assert "Yahoo offline" in result.message


def test_yahoo_error_does_not_prevent_other_symbols(tmp_path):
    yahoo = FakeYahooProvider(
        errors_by_symbol={"AAPL": RuntimeError("fallo controlado")},
        records_by_symbol={
            "MSFT": [_record("MSFT", date(2025, 6, 30), "yahoo", 3.2)]
        },
    )
    service, _, _, bootstrapper = _service(tmp_path, yahoo)

    results = service.update_for_symbols(["AAPL", "MSFT"])

    assert [result.yahoo_status for result in results] == ["error", "updated"]
    assert [result.bootstrap_status for result in results] == ["completed", "completed"]
    assert bootstrapper.calls == ["AAPL", "MSFT"]


def test_bootstrap_can_be_disabled(tmp_path):
    bootstrapper = FakeBootstrapper()
    service, _, _, _ = _service(tmp_path, bootstrapper=bootstrapper)

    results = service.update_for_symbols(["AAPL", "MSFT"], bootstrap_missing=False)

    assert [result.bootstrap_status for result in results] == [
        "not_requested",
        "not_requested",
    ]
    assert bootstrapper.calls == []


def test_final_coverage_is_read_from_store(tmp_path):
    yahoo = FakeYahooProvider(
        records_by_symbol={"AAPL": [_record("AAPL", date(2025, 6, 30), "yahoo", 1.2)]}
    )
    service, _, _, _ = _service(tmp_path, yahoo)

    result = service.update_for_symbols(["AAPL"])[0]

    assert result.stored_records == 1
    assert result.unique_fiscal_periods == 1
    assert result.first_fiscal_date == "2025-06-30"
    assert result.last_fiscal_date == "2025-06-30"
    assert result.providers == ["yahoo"]


def test_providers_preserves_multiple_data_sources(tmp_path):
    yahoo = FakeYahooProvider(
        records_by_symbol={"AAPL": [_record("AAPL", date(2025, 6, 30), "yahoo", 1.2)]}
    )
    bootstrapper = FakeBootstrapper(
        records_by_symbol={
            "AAPL": [_record("AAPL", date(2025, 6, 30), "alpha_vantage", 1.1)]
        }
    )
    service, _, _, _ = _service(tmp_path, yahoo, bootstrapper)

    result = service.update_for_symbols(["AAPL"])[0]

    assert result.stored_records == 2
    assert result.unique_fiscal_periods == 1
    assert result.providers == ["alpha_vantage", "yahoo"]