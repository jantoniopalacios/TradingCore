import numpy as np
import pandas as pd
import pytest

from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV


def _result_at_latest_report(
    eps_growth_percent=20.0,
    per_deviation_percent=-25.0,
    period_count=23,
    current_per=None,
):
    fiscal_dates = pd.date_range(
        "2020-03-31",
        periods=period_count,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    eps_values = np.ones(period_count, dtype=float)
    eps_values[-1] = 1.0 + 4.0 * eps_growth_percent / 100.0
    fundamentals = pd.DataFrame(
        {
            "Symbol": "AAPL",
            "fiscalDateEnding": fiscal_dates,
            "reportedDate": reported_dates,
            "Diluted EPS": eps_values,
        }
    )

    ltm_eps = pd.Series(eps_values).rolling(
        window=4,
        min_periods=4,
    ).sum()
    market_dates = pd.date_range(fiscal_dates[0], reported_dates[-1], freq="D")
    prices = pd.DataFrame(
        {
            "Symbol": "AAPL",
            "Close": 80.0,
        },
        index=pd.Index(market_dates, name="Date"),
    )
    for quarter_index in range(3, len(fiscal_dates)):
        prices.loc[fiscal_dates[quarter_index], "Close"] = (
            20.0 * ltm_eps.iloc[quarter_index]
        )

    latest_ltm_eps = ltm_eps.iloc[-1]
    target_per = (
        current_per
        if current_per is not None
        else 20.0 * (1.0 + per_deviation_percent / 100.0)
    )
    latest_report = reported_dates[-1]
    prices.loc[latest_report, "Close"] = target_per * latest_ltm_eps

    result = calcular_fullratio_OHLCV(prices, fundamentals)
    return result.loc[latest_report]


@pytest.mark.parametrize(
    ("eps_growth", "per_deviation", "expected_margin", "expected_per"),
    [
        (20.0, -25.0, 45.0, 15.0),
        (20.0, 25.0, -5.0, 25.0),
        (-10.0, -25.0, 15.0, 15.0),
        (-10.0, 25.0, -35.0, 25.0),
    ],
)
def test_margin_of_safety_is_eps_growth_minus_per_deviation(
    eps_growth,
    per_deviation,
    expected_margin,
    expected_per,
):
    result = _result_at_latest_report(eps_growth, per_deviation)

    assert result["LTM EPS %"] == eps_growth
    assert result["% PER vs PER M5Y"] == per_deviation
    assert result["Margen de seguridad"] == expected_margin
    assert result["PER"] == expected_per
    assert result["Full Ratio"] == round(expected_margin / expected_per, 2)


def test_nan_ltm_eps_growth_propagates_to_margin_and_full_ratio():
    fiscal_dates = pd.date_range(
        "2025-03-31",
        periods=4,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    fundamentals = pd.DataFrame(
        {
            "Symbol": "AAPL",
            "fiscalDateEnding": fiscal_dates,
            "reportedDate": reported_dates,
            "Diluted EPS": [1.0, 1.0, 1.0, 1.0],
        }
    )
    market_dates = pd.date_range(fiscal_dates[0], reported_dates[-1], freq="D")
    prices = pd.DataFrame(
        {"Symbol": "AAPL", "Close": 40.0},
        index=pd.Index(market_dates, name="Date"),
    )
    latest_report = reported_dates[-1]

    result = calcular_fullratio_OHLCV(prices, fundamentals).loc[latest_report]

    assert pd.isna(result["LTM EPS %"])
    assert pd.isna(result["Margen de seguridad"])
    assert pd.isna(result["Full Ratio"])


def test_nan_per_deviation_propagates_to_margin_and_full_ratio():
    result = _result_at_latest_report(period_count=22)

    assert pd.isna(result["% PER vs PER M5Y"])
    assert pd.isna(result["Margen de seguridad"])
    assert pd.isna(result["Full Ratio"])


def test_full_ratio_keeps_current_zero_per_division_behavior():
    result = _result_at_latest_report(current_per=0.0)

    assert result["PER"] == 0.0
    assert result["% PER vs PER M5Y"] == -100.0
    assert np.isinf(result["Full Ratio"])


def test_full_ratio_is_nan_when_per_is_nan():
    result = _result_at_latest_report(current_per=np.nan)

    assert pd.isna(result["PER"])
    assert pd.isna(result["% PER vs PER M5Y"])
    assert pd.isna(result["Full Ratio"])
