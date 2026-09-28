import numpy as np
import pandas as pd

from trading_engine.utils.Calculos_Financieros import calcular_fullratio_OHLCV


def _quarterly_data(period_count):
    fiscal_dates = pd.date_range(
        "2020-03-31",
        periods=period_count,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    fundamentals = pd.DataFrame(
        {
            "Symbol": "AAPL",
            "fiscalDateEnding": fiscal_dates,
            "reportedDate": reported_dates,
            "Diluted EPS": np.arange(1, period_count + 1, dtype=float),
        }
    )
    market_dates = pd.date_range(
        fiscal_dates[0],
        reported_dates[-1],
        freq="D",
    )
    prices = pd.DataFrame(
        {"Symbol": "AAPL", "Close": 100.0},
        index=pd.Index(market_dates, name="Date"),
    )
    return fundamentals, prices


def _calculate(period_count):
    fundamentals, prices = _quarterly_data(period_count)
    return calcular_fullratio_OHLCV(prices, fundamentals)


def test_three_quarters_do_not_produce_ltm_eps():
    result = _calculate(3)

    assert result["LTM EPS"].isna().all()


def test_four_quarters_produce_ltm_eps_sum():
    fundamentals, _ = _quarterly_data(4)
    result = _calculate(4)
    report_date = fundamentals.iloc[-1]["reportedDate"]

    assert result.loc[report_date, "LTM EPS"] == 10.0


def test_nineteen_valid_quarterly_pers_do_not_produce_five_year_mean():
    result = _calculate(22)

    assert result["PER M5Y"].isna().all()


def test_twenty_valid_quarterly_pers_produce_five_year_mean():
    fundamentals, _ = _quarterly_data(23)
    result = _calculate(23)
    final_report_date = fundamentals.iloc[-1]["reportedDate"]
    ltm_eps = fundamentals["Diluted EPS"].rolling(
        window=4,
        min_periods=4,
    ).sum()
    expected_per_mean = (100.0 / ltm_eps).rolling(
        window=20,
        min_periods=20,
    ).mean().round(2).iloc[-1]

    assert result.loc[final_report_date, "PER M5Y"] == expected_per_mean


def test_reported_date_alignment_remains_inclusive_with_four_quarters():
    fundamentals, prices = _quarterly_data(4)
    final_report_date = fundamentals.iloc[-1]["reportedDate"]

    result = calcular_fullratio_OHLCV(prices, fundamentals)

    assert pd.isna(result.loc[final_report_date - pd.Timedelta(days=1), "LTM EPS"])
    assert result.loc[final_report_date, "LTM EPS"] == 10.0


def test_full_ratio_formula_is_unchanged_with_sufficient_history():
    fundamentals, prices = _quarterly_data(23)
    result = calcular_fullratio_OHLCV(prices, fundamentals)
    final_report_date = fundamentals.iloc[-1]["reportedDate"]

    eps = fundamentals["Diluted EPS"]
    ltm_eps = eps.rolling(window=4, min_periods=4).sum().round(2)
    ltm_eps_pct = (ltm_eps.pct_change() * 100).round(2)
    quarterly_per = (100.0 / ltm_eps).round(2)
    quarterly_per[ltm_eps <= 0] = np.nan
    per_mean = quarterly_per.rolling(window=20, min_periods=20).mean().round(2)
    final_per = quarterly_per.iloc[-1]
    per_vs_mean = round(100 * (final_per - per_mean.iloc[-1]) / per_mean.iloc[-1], 2)
    safety_margin = round(ltm_eps_pct.iloc[-1] - per_vs_mean, 2)
    expected_full_ratio = round(safety_margin / final_per, 2)

    assert result.loc[final_report_date, "Full Ratio"] == expected_full_ratio