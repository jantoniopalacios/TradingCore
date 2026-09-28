import numpy as np
import pandas as pd
import pytest

from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV


def _latest_full_ratio(margin, per, eps_growth=None):
    fiscal_dates = pd.date_range(
        "2020-03-31",
        periods=23,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    if eps_growth is None:
        per_deviation = 100.0 * (per - 20.0) / 20.0
        eps_growth = margin + per_deviation
    eps_values = np.ones(23, dtype=float)
    eps_values[-1] = 1.0 + 4.0 * eps_growth / 100.0
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
        {"Symbol": "AAPL", "Close": 80.0},
        index=pd.Index(market_dates, name="Date"),
    )
    for quarter_index in range(3, len(fiscal_dates)):
        prices.loc[fiscal_dates[quarter_index], "Close"] = (
            20.0 * ltm_eps.iloc[quarter_index]
        )
    latest_report = reported_dates[-1]
    prices.loc[latest_report, "Close"] = per * ltm_eps.iloc[-1]

    result = calcular_fullratio_OHLCV(prices, fundamentals)
    return result.loc[latest_report]


@pytest.mark.parametrize(
    ("margin", "per", "expected_full_ratio"),
    [
        (40.0, 10.0, 4.0),
        (40.0, 20.0, 2.0),
        (-20.0, 10.0, -2.0),
        (0.0, 20.0, 0.0),
    ],
)
def test_full_ratio_is_margin_divided_by_per(margin, per, expected_full_ratio):
    result = _latest_full_ratio(margin, per)

    assert result["Margen de seguridad"] == margin
    assert result["PER"] == per
    assert result["Full Ratio"] == expected_full_ratio


def test_nan_per_produces_nan_full_ratio():
    result = _latest_full_ratio(40.0, np.nan, eps_growth=20.0)

    assert pd.isna(result["PER"])
    assert pd.isna(result["Full Ratio"])


def test_zero_per_preserves_current_division_behavior():
    result = _latest_full_ratio(40.0, 0.0)

    assert result["PER"] == 0.0
    assert np.isposinf(result["Full Ratio"])


def test_negative_per_preserves_current_signed_quotient():
    result = _latest_full_ratio(40.0, -10.0, eps_growth=20.0)

    assert result["PER"] == -10.0
    assert result["Margen de seguridad"] == 170.0
    assert result["Full Ratio"] == -17.0


def test_lower_per_increases_full_ratio_for_fixed_margin():
    lower_per = _latest_full_ratio(40.0, 10.0)
    higher_per = _latest_full_ratio(40.0, 20.0)

    assert lower_per["Full Ratio"] > higher_per["Full Ratio"]


def test_higher_margin_increases_full_ratio_for_fixed_per():
    lower_margin = _latest_full_ratio(0.0, 20.0)
    higher_margin = _latest_full_ratio(40.0, 20.0)

    assert higher_margin["Full Ratio"] > lower_margin["Full Ratio"]
