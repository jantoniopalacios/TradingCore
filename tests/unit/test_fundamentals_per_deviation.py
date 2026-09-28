import numpy as np
import pandas as pd
import pytest

from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV


def _calculate_for_per(current_per, historical_per=20.0):
    fiscal_dates = pd.date_range(
        "2020-03-31",
        periods=23,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    fundamentals = pd.DataFrame(
        {
            "Symbol": "AAPL",
            "fiscalDateEnding": fiscal_dates,
            "reportedDate": reported_dates,
            "Diluted EPS": 1.0,
        }
    )
    market_dates = pd.date_range(fiscal_dates[0], reported_dates[-1], freq="D")
    prices = pd.DataFrame(
        {"Symbol": "AAPL", "Close": historical_per * 4.0},
        index=pd.Index(market_dates, name="Date"),
    )
    latest_report = reported_dates[-1]
    prices.loc[latest_report, "Close"] = current_per * 4.0

    result = calcular_fullratio_OHLCV(prices, fundamentals)
    return result.loc[latest_report]


@pytest.mark.parametrize(
    ("current_per", "expected_deviation"),
    [(10.0, -50.0), (30.0, 50.0), (20.0, 0.0)],
)
def test_per_deviation_uses_historical_mean_as_denominator(
    current_per,
    expected_deviation,
):
    result = _calculate_for_per(current_per)

    assert result["PER M5Y"] == 20.0
    assert result["% PER vs PER M5Y"] == expected_deviation


@pytest.mark.parametrize(
    "historical_per",
    [np.nan, 0.0, -20.0],
)
def test_nonpositive_or_missing_historical_mean_produces_nan(historical_per):
    result = _calculate_for_per(10.0, historical_per=historical_per)

    assert pd.isna(result["% PER vs PER M5Y"])
    assert not np.isinf(result["% PER vs PER M5Y"])


def test_safety_margin_uses_corrected_deviation_without_formula_change():
    result = _calculate_for_per(10.0)

    assert result["LTM EPS %"] == 0.0
    assert result["% PER vs PER M5Y"] == -50.0
    assert result["Margen de seguridad"] == 50.0