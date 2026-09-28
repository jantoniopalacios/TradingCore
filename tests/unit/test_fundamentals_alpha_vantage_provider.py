from trading_engine.fundamentals.providers.alpha_vantage import (
    AlphaVantageFundamentalProvider,
    AlphaVantageNoData,
    AlphaVantageQuotaExhausted,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _http_get_for(payload, calls):
    def fake_get(url, params=None, timeout=None):
        calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        return FakeResponse(payload)
    return fake_get


def test_alpha_vantage_parses_quarterly_earnings_without_network():
    calls = []
    payload = {
        "symbol": "AAPL",
        "quarterlyEarnings": [
            {
                "fiscalDateEnding": "2025-06-30",
                "reportedDate": "2025-07-31",
                "reportedEPS": "1.57",
            },
            {
                "fiscalDateEnding": "2025-03-31",
                "reportedDate": "2025-05-01",
                "reportedEPS": "1.50",
            },
        ],
    }

    provider = AlphaVantageFundamentalProvider(
        api_key="test-key",
        http_get=_http_get_for(payload, calls),
    )

    records = provider.fetch_records("aapl")

    assert len(records) == 2
    assert records[0].symbol == "AAPL"
    assert records[0].value == 1.50
    assert records[1].value == 1.57
    assert records[1].provider == "alpha_vantage"
    assert calls[0]["params"]["function"] == "EARNINGS"


def test_alpha_vantage_detects_quota_note():
    calls = []
    provider = AlphaVantageFundamentalProvider(
        api_key="test-key",
        http_get=_http_get_for(
            {
                "Note": (
                    "Thank you for using Alpha Vantage! "
                    "Our standard API call frequency is limited."
                )
            },
            calls,
        ),
    )

    try:
        provider.fetch_records("AAPL")
    except AlphaVantageQuotaExhausted:
        pass
    else:
        raise AssertionError("Se esperaba AlphaVantageQuotaExhausted")


def test_alpha_vantage_detects_quota_information():
    calls = []
    provider = AlphaVantageFundamentalProvider(
        api_key="test-key",
        http_get=_http_get_for(
            {
                "Information": (
                    "You have reached the daily API call limit."
                )
            },
            calls,
        ),
    )

    try:
        provider.fetch_records("AAPL")
    except AlphaVantageQuotaExhausted:
        pass
    else:
        raise AssertionError("Se esperaba AlphaVantageQuotaExhausted")


def test_alpha_vantage_no_quarterly_earnings_is_no_data():
    calls = []
    provider = AlphaVantageFundamentalProvider(
        api_key="test-key",
        http_get=_http_get_for({"symbol": "SAN.MC"}, calls),
    )

    try:
        provider.fetch_records("SAN.MC")
    except AlphaVantageNoData:
        pass
    else:
        raise AssertionError("Se esperaba AlphaVantageNoData")


def test_alpha_vantage_skips_invalid_rows():
    calls = []
    provider = AlphaVantageFundamentalProvider(
        api_key="test-key",
        http_get=_http_get_for(
            {
                "quarterlyEarnings": [
                    {
                        "fiscalDateEnding": "2025-06-30",
                        "reportedDate": "2025-07-31",
                        "reportedEPS": "1.57",
                    },
                    {
                        "fiscalDateEnding": "2025-03-31",
                        "reportedDate": "bad-date",
                        "reportedEPS": "1.50",
                    },
                    {
                        "fiscalDateEnding": "2024-12-31",
                        "reportedDate": "2025-01-30",
                        "reportedEPS": "None",
                    },
                ]
            },
            calls,
        ),
    )

    records = provider.fetch_records("AAPL")

    assert len(records) == 1
    assert records[0].value == 1.57
