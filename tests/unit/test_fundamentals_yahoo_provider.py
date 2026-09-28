from datetime import date

import pandas as pd

from trading_engine.fundamentals.providers.yahoo import (
    YahooFundamentalProvider,
)


class FakeTicker:
    def __init__(self, income_stmt, earnings_dates):
        self._income_stmt = income_stmt
        self._earnings_dates = earnings_dates

    def get_income_stmt(self, freq="yearly", pretty=False):
        assert freq == "quarterly"
        assert pretty is True
        return self._income_stmt

    def get_earnings_dates(self, limit=12):
        assert limit == 100
        return self._earnings_dates


def _provider(income_stmt, earnings_dates, max_report_lag_days=120):
    ticker = FakeTicker(income_stmt, earnings_dates)
    return YahooFundamentalProvider(
        ticker_factory=lambda symbol: ticker,
        max_report_lag_days=max_report_lag_days,
    )


def test_fetch_records_matches_fiscal_period_to_next_report_date():
    income = pd.DataFrame(
        {
            pd.Timestamp("2025-03-31"): [1.50],
            pd.Timestamp("2025-06-30"): [1.60],
        },
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {
            "Reported EPS": [1.52, 1.61],
        },
        index=[
            pd.Timestamp("2025-05-01"),
            pd.Timestamp("2025-08-01"),
        ],
    )

    records = _provider(income, earnings).fetch_records("aapl")

    assert len(records) == 2
    assert records[0].symbol == "AAPL"
    assert records[0].fiscal_date == date(2025, 3, 31)
    assert records[0].reported_date == date(2025, 5, 1)
    assert records[0].value == 1.50
    assert records[0].provider == "yahoo"
    assert records[0].metric == "diluted_eps"


def test_fetch_records_uses_statement_eps_not_reported_eps_value():
    income = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [1.50]},
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {"Reported EPS": [1.75]},
        index=[pd.Timestamp("2025-05-01")],
    )

    records = _provider(income, earnings).fetch_records("ZTS")

    assert len(records) == 1
    assert records[0].value == 1.50
    assert "income_stmt_diluted_eps" in records[0].source_type


def test_fetch_records_does_not_invent_reported_date_when_missing():
    income = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [1.50]},
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {"Reported EPS": []},
        index=pd.DatetimeIndex([]),
    )

    records = _provider(income, earnings).fetch_records("AAPL")

    assert records == []


def test_fetch_records_rejects_report_date_outside_maximum_lag():
    income = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [1.50]},
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {"Reported EPS": [1.50]},
        index=[pd.Timestamp("2025-09-15")],
    )

    records = _provider(
        income,
        earnings,
        max_report_lag_days=120,
    ).fetch_records("AAPL")

    assert records == []


def test_fetch_fiscal_eps_ignores_null_values_and_orders_dates():
    income = pd.DataFrame(
        {
            pd.Timestamp("2025-06-30"): [1.60],
            pd.Timestamp("2025-03-31"): [1.50],
            pd.Timestamp("2024-12-31"): [None],
        },
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {"Reported EPS": []},
        index=pd.DatetimeIndex([]),
    )

    rows = _provider(income, earnings).fetch_fiscal_eps("AAPL")

    assert [row.fiscal_date for row in rows] == [
        date(2025, 3, 31),
        date(2025, 6, 30),
    ]


def test_fetch_reported_eps_ignores_null_values_and_orders_dates():
    income = pd.DataFrame()
    earnings = pd.DataFrame(
        {
            "Reported EPS": [1.60, None, 1.50],
        },
        index=[
            pd.Timestamp("2025-08-01"),
            pd.Timestamp("2025-06-01"),
            pd.Timestamp("2025-05-01"),
        ],
    )

    rows = _provider(income, earnings).fetch_reported_eps("AAPL")

    assert [row.reported_date for row in rows] == [
        date(2025, 5, 1),
        date(2025, 8, 1),
    ]


def test_fetch_records_does_not_match_report_before_fiscal_date():
    income = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [1.50]},
        index=["Diluted EPS"],
    )
    earnings = pd.DataFrame(
        {"Reported EPS": [1.50]},
        index=[pd.Timestamp("2025-02-01")],
    )

    records = _provider(income, earnings).fetch_records("AAPL")

    assert records == []


def test_provider_handles_alternate_diluted_eps_row_name():
    income = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [1.50]},
        index=["DilutedEPS"],
    )
    earnings = pd.DataFrame(
        {"ReportedEPS": [1.50]},
        index=[pd.Timestamp("2025-05-01")],
    )

    records = _provider(income, earnings).fetch_records("AAPL")

    assert len(records) == 1
    assert records[0].value == 1.50
