import logging

import numpy as np
import pandas as pd

from trading_engine.utils.Calculos_Financieros import (
    calcular_fullratio_OHLCV,
    generar_seleccion_activos,
)


ATTRACTIVE = "Mantener (Atractivo)"
REJECTED = "Desestimar (No cumple criterios)"
NOT_EVALUABLE = "No evaluable (Datos insuficientes)"


def _symbol_data(symbol, period_count, market_end=None):
    fiscal_dates = pd.date_range(
        "2020-03-31",
        periods=period_count,
        freq=pd.offsets.QuarterEnd(),
    )
    reported_dates = fiscal_dates + pd.Timedelta(days=30)
    eps = np.ones(period_count, dtype=float)
    if period_count >= 4:
        eps[-1] = 1.8

    fundamentals = pd.DataFrame(
        {
            "Symbol": symbol,
            "fiscalDateEnding": fiscal_dates,
            "reportedDate": reported_dates,
            "Diluted EPS": eps,
        }
    )
    ltm_eps = pd.Series(eps).rolling(window=4, min_periods=4).sum()
    price_end = max(
        pd.Timestamp(market_end) if market_end is not None else reported_dates[-1],
        reported_dates[-1],
    )
    market_dates = pd.date_range(fiscal_dates[0], price_end, freq="D")
    prices = pd.DataFrame(
        {"Symbol": symbol, "Close": 80.0},
        index=pd.Index(market_dates, name="Date"),
    )
    for quarter_index in range(3, period_count):
        prices.loc[fiscal_dates[quarter_index], "Close"] = (
            20.0 * ltm_eps.iloc[quarter_index]
        )

    if period_count >= 23:
        prices.loc[reported_dates[-1], "Close"] = 15.0 * ltm_eps.iloc[-1]

    return fundamentals, prices


def _calculate_and_select(fundamentals, prices):
    stocks_data = calcular_fullratio_OHLCV(prices, fundamentals)
    selection = generar_seleccion_activos(
        stocks_data,
        logging.getLogger("test.fundamentals_insufficient_history"),
    )
    return stocks_data, selection


def test_fewer_than_four_quarters_has_no_ltm_and_is_not_evaluable():
    fundamentals, prices = _symbol_data("AAPL", 3)

    stocks_data, selection = _calculate_and_select(fundamentals, prices)

    assert stocks_data["LTM EPS"].isna().all()
    assert selection.loc["AAPL", "Recomendación"] == NOT_EVALUABLE


def test_ltm_exists_but_under_twenty_valid_pers_is_not_evaluable():
    fundamentals, prices = _symbol_data("AAPL", 22)

    stocks_data, selection = _calculate_and_select(fundamentals, prices)
    latest = stocks_data.iloc[-1]

    assert pd.notna(latest["LTM EPS"])
    assert pd.isna(latest["PER M5Y"])
    assert pd.isna(latest["Margen de seguridad"])
    assert pd.isna(latest["Full Ratio"])
    assert selection.loc["AAPL", "Recomendación"] == NOT_EVALUABLE


def test_sufficient_history_is_evaluated_normally():
    fundamentals, prices = _symbol_data("AAPL", 23)

    stocks_data, selection = _calculate_and_select(fundamentals, prices)

    assert stocks_data.iloc[-1]["LTM EPS"] == 4.8
    assert stocks_data.iloc[-1]["PER M5Y"] == 20.0
    assert selection.loc["AAPL", "Recomendación"] == ATTRACTIVE


def test_sufficient_and_insufficient_symbols_appear_as_currently_defined():
    enough_fundamentals, enough_prices = _symbol_data("AAPL", 23)
    latest_report = enough_fundamentals["reportedDate"].iloc[-1]
    short_fundamentals, short_prices = _symbol_data("MSFT", 10, market_end=latest_report)
    fundamentals = pd.concat([enough_fundamentals, short_fundamentals], ignore_index=True)
    prices = pd.concat([enough_prices, short_prices]).sort_index()

    stocks_data, selection = _calculate_and_select(fundamentals, prices)
    latest_rows = stocks_data.loc[latest_report]

    assert latest_rows.set_index("Symbol").loc["AAPL", "Full Ratio"] > 0
    assert pd.isna(latest_rows.set_index("Symbol").loc["MSFT", "Full Ratio"])
    assert selection.loc["AAPL", "Recomendación"] == ATTRACTIVE
    assert selection.loc["MSFT", "Recomendación"] == NOT_EVALUABLE


def test_nan_required_metrics_follow_current_classification_behavior():
    latest_date = pd.Timestamp("2025-09-29")
    stocks_data = pd.DataFrame(
        {
            "Symbol": ["NAN_GROWTH", "NAN_MARGIN", "NAN_RATIO"],
            "Close": [100.0, 100.0, 100.0],
            "LTM EPS %": [np.nan, 10.0, 10.0],
            "PER": [10.0, 10.0, 10.0],
            "PER M5Y": [15.0, 15.0, 15.0],
            "Margen de seguridad": [5.0, np.nan, 5.0],
            "Full Ratio": [1.0, 1.0, np.nan],
        },
        index=pd.DatetimeIndex([latest_date] * 3, name="Date"),
    )

    selection = generar_seleccion_activos(
        stocks_data,
        logging.getLogger("test.fundamentals_insufficient_history"),
    )

    assert selection.loc["NAN_GROWTH", "Recomendación"] == NOT_EVALUABLE
    assert selection.loc["NAN_MARGIN", "Recomendación"] == NOT_EVALUABLE
    assert selection.loc["NAN_RATIO", "Recomendación"] == NOT_EVALUABLE


def test_insufficient_history_uses_explicit_not_evaluable_recommendation():
    fundamentals, prices = _symbol_data("MSFT", 22)
    _, selection = _calculate_and_select(fundamentals, prices)

    assert selection.loc["MSFT", "Recomendación"] == NOT_EVALUABLE
