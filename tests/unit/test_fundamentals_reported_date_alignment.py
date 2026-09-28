from datetime import date

import numpy as np
import pandas as pd

from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV


def _prices(start, end):
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "Symbol": "AAPL",
            "Close": np.full(len(dates), 100.0),
        },
        index=pd.Index(dates, name="Date"),
    )


def _fundamentals(rows):
    return pd.DataFrame(
        rows,
        columns=["Symbol", "fiscalDateEnding", "reportedDate", "Diluted EPS"],
    )


def _calculate(prices, fundamentals):
    return calcular_fullratio_OHLCV(prices, fundamentals)


def test_fundamental_is_available_from_reported_date_inclusive():
    prices = _prices("2025-04-29", "2025-05-03")
    fundamentals = _fundamentals(
        [
            ("AAPL", "2024-06-30", "2024-08-01", 1.0),
            ("AAPL", "2024-09-30", "2024-11-01", 1.0),
            ("AAPL", "2024-12-31", "2025-02-01", 1.0),
            ("AAPL", "2025-03-31", "2025-05-01", 1.0),
        ]
    )

    result = _calculate(prices, fundamentals)

    assert result.loc["2025-04-30", "LTM EPS"] is np.nan or pd.isna(
        result.loc["2025-04-30", "LTM EPS"]
    )
    assert result.loc["2025-05-01", "LTM EPS"] == 4.0
    assert result.loc["2025-05-02", "LTM EPS"] == 4.0
    assert result.loc["2025-05-01", "reportedDate"] == pd.Timestamp("2025-05-01")


def test_previous_quarter_remains_until_next_reported_date():
    prices = _prices("2025-04-30", "2025-08-02")
    fundamentals = _fundamentals(
        [
            ("AAPL", "2024-06-30", "2024-08-01", 1.0),
            ("AAPL", "2024-09-30", "2024-11-01", 1.0),
            ("AAPL", "2024-12-31", "2025-02-01", 1.0),
            ("AAPL", "2025-03-31", "2025-05-01", 1.0),
            ("AAPL", "2025-06-30", "2025-08-01", 2.0),
        ]
    )

    result = _calculate(prices, fundamentals)

    assert pd.isna(result.loc["2025-04-30", "LTM EPS"])
    assert result.loc["2025-05-01", "LTM EPS"] == 4.0
    assert result.loc["2025-07-31", "LTM EPS"] == 4.0
    assert result.loc["2025-08-01", "LTM EPS"] == 5.0
    assert result.loc["2025-07-31", "reportedDate"] == pd.Timestamp("2025-05-01")
    assert result.loc["2025-08-01", "reportedDate"] == pd.Timestamp("2025-08-01")


def test_null_reported_date_is_not_propagated():
    prices = _prices("2025-04-01", "2025-05-05")
    fundamentals = _fundamentals(
        [("AAPL", "2025-03-31", None, 2.0)]
    )

    result = _calculate(prices, fundamentals)

    assert result["LTM EPS"].isna().all()
    assert result["reportedDate"].isna().all()


def test_fiscal_to_report_interval_does_not_use_unreported_quarter():
    prices = _prices("2025-03-31", "2025-05-02")
    fundamentals = _fundamentals(
        [
            ("AAPL", "2024-06-30", "2024-08-01", 1.0),
            ("AAPL", "2024-09-30", "2024-11-01", 1.0),
            ("AAPL", "2024-12-31", "2025-02-01", 1.0),
            ("AAPL", "2025-03-31", "2025-05-01", 1.0),
        ]
    )

    result = _calculate(prices, fundamentals)

    assert result.loc["2025-03-31":"2025-04-30", "LTM EPS"].isna().all()
    assert result.loc["2025-05-01", "LTM EPS"] == 4.0


def test_daily_merge_does_not_duplicate_market_dates():
    prices = _prices("2025-04-29", "2025-05-03")
    fundamentals = _fundamentals(
        [
            ("AAPL", "2025-03-31", "2025-05-01", 2.0),
            ("AAPL", "2025-03-31", "2025-05-01", 2.5),
        ]
    )

    result = _calculate(prices, fundamentals)

    assert len(result) == len(prices)
    assert result.index.is_unique


def test_quarterly_calculations_are_unchanged_and_only_availability_shifts():
    prices = _prices("2025-03-31", "2025-08-02")
    fundamentals = _fundamentals(
        [
            ("AAPL", "2024-06-30", "2024-08-01", 1.0),
            ("AAPL", "2024-09-30", "2024-11-01", 2.0),
            ("AAPL", "2024-12-31", "2025-02-01", 3.0),
            ("AAPL", "2025-03-31", "2025-05-01", 2.0),
            ("AAPL", "2025-06-30", "2025-08-01", 3.0),
        ]
    )

    result = _calculate(prices, fundamentals)

    # At publication, the existing quarterly rolling sums and price-based PER remain intact.
    first_per = round(100.0 / 8.0, 2)
    second_ltm_eps = round(2.0 + 3.0 + 2.0 + 3.0, 2)
    second_per = round(100.0 / second_ltm_eps, 2)
    assert result.loc["2025-05-01", "LTM EPS"] == 8.0
    assert result.loc["2025-05-01", "PER"] == first_per
    assert result.loc["2025-08-01", "LTM EPS"] == second_ltm_eps
    assert result.loc["2025-08-01", "PER"] == second_per