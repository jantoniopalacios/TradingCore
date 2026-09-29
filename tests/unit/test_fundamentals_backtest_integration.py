from trading_engine.fundamentals.providers import alpha_vantage, yahoo
from trading_engine.fundamentals import service as service_module
from trading_engine.utils import Data_download


class FakeYahooProvider:
    def __init__(self):
        self.calls = []

    def fetch_records(self, symbol):
        self.calls.append(symbol)
        return []


class FakeAlphaVantageProvider:
    def __init__(self):
        self.calls = []

    def fetch_records(self, symbol):
        self.calls.append(symbol)
        return []


def test_disabled_filter_does_not_construct_or_call_service(tmp_path, monkeypatch):
    def fail_if_constructed(*args, **kwargs):
        raise AssertionError("El servicio no debe construirse con el filtro desactivado")

    monkeypatch.setattr(service_module, "FundamentalService", fail_if_constructed)

    result = Data_download.update_normalized_fundamentals_if_enabled(
        False,
        ["AAPL"],
        tmp_path,
    )

    assert result == []


def test_enabled_filter_uses_exact_symbols_without_mutating_input(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "test-key")
    yahoo_provider = FakeYahooProvider()
    alpha_provider = FakeAlphaVantageProvider()
    monkeypatch.setattr(yahoo, "YahooFundamentalProvider", lambda: yahoo_provider)
    monkeypatch.setattr(
        alpha_vantage,
        "AlphaVantageFundamentalProvider",
        lambda: alpha_provider,
    )
    symbols = ["AAPL", "SAN.MC", "MSFT"]
    original_symbols = symbols.copy()

    results = Data_download.update_normalized_fundamentals_if_enabled(
        True,
        symbols,
        tmp_path,
    )

    assert [result.symbol for result in results] == original_symbols
    assert yahoo_provider.calls == original_symbols
    assert alpha_provider.calls == original_symbols
    assert symbols == original_symbols


def test_missing_alpha_vantage_key_does_not_block_yahoo(tmp_path, monkeypatch):
    yahoo_provider = FakeYahooProvider()
    monkeypatch.setattr(yahoo, "YahooFundamentalProvider", lambda: yahoo_provider)
    monkeypatch.delenv("ALPHA_VANTAGE_KEY", raising=False)

    results = Data_download.update_normalized_fundamentals_if_enabled(
        True,
        ["AAPL"],
        tmp_path,
    )

    assert yahoo_provider.calls == ["AAPL"]
    assert results[0].yahoo_status == "no_data"
    assert results[0].bootstrap_status == "not_requested"
    assert "Yahoo no devolvió fundamentales utilizables" in results[0].message


def test_normalized_update_error_does_not_raise_to_legacy_flow(tmp_path, monkeypatch):
    def fail_update(*args, **kwargs):
        raise RuntimeError("fallo de actualización")

    monkeypatch.setattr(service_module, "FundamentalService", fail_update)

    results = Data_download.update_normalized_fundamentals_if_enabled(
        True,
        ["AAPL"],
        tmp_path,
    )

    assert results == []


def test_bootstrap_state_file_is_inside_fundamentals_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "test-key")
    monkeypatch.setattr(yahoo, "YahooFundamentalProvider", FakeYahooProvider)
    monkeypatch.setattr(
        alpha_vantage,
        "AlphaVantageFundamentalProvider",
        FakeAlphaVantageProvider,
    )
    fundamentals_path = tmp_path / "fundamentals"

    Data_download.update_normalized_fundamentals_if_enabled(
        True,
        ["AAPL"],
        fundamentals_path,
    )

    assert (fundamentals_path / "bootstrap_state.json").exists()