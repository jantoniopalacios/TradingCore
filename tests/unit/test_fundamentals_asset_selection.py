import logging

import numpy as np
import pandas as pd
import pytest

from trading_engine.utils.Calculos_Financieros import generar_seleccion_activos


COLUMNS = [
    "Symbol",
    "Close",
    "LTM EPS %",
    "PER",
    "PER M5Y",
    "Margen de seguridad",
    "Full Ratio",
]
ATTRACTIVE = "Mantener (Atractivo)"
REJECTED = "Desestimar (No cumple criterios)"
NOT_EVALUABLE = "No evaluable (Datos insuficientes)"


def _row(
    symbol,
    *,
    growth=10.0,
    margin=5.0,
    full_ratio=1.0,
    close=100.0,
    per=10.0,
    per_mean=15.0,
):
    return {
        "Symbol": symbol,
        "Close": close,
        "LTM EPS %": growth,
        "PER": per,
        "PER M5Y": per_mean,
        "Margen de seguridad": margin,
        "Full Ratio": full_ratio,
    }


def _select(rows):
    frame = pd.DataFrame(
        [(timestamp, row) for timestamp, row in rows],
        columns=["Date", "Values"],
    )
    data = pd.DataFrame(frame.pop("Values").tolist(), index=pd.DatetimeIndex(frame["Date"], name="Date"))
    return generar_seleccion_activos(data, logging.getLogger("test.asset_selection"))


def _recommendation(selection, symbol):
    return selection.loc[symbol, "Recomendación"]


def test_all_three_positive_conditions_are_attractive():
    selection = _select(
        [("2025-09-29", _row("AAPL", growth=1.0, margin=1.0, full_ratio=1.0))]
    )

    assert _recommendation(selection, "AAPL") == ATTRACTIVE


@pytest.mark.parametrize(
    "failing_values",
    [
        {"growth": 0.0, "margin": 1.0, "full_ratio": 1.0},
        {"growth": -1.0, "margin": 1.0, "full_ratio": 1.0},
        {"growth": 1.0, "margin": 0.0, "full_ratio": 1.0},
        {"growth": 1.0, "margin": -1.0, "full_ratio": 1.0},
        {"growth": 1.0, "margin": 1.0, "full_ratio": 0.0},
        {"growth": 1.0, "margin": 1.0, "full_ratio": -1.0},
    ],
)
def test_each_nonpositive_condition_rejects_even_when_others_are_positive(
    failing_values,
):
    selection = _select(
        [("2025-09-29", _row("AAPL", **failing_values))]
    )

    assert _recommendation(selection, "AAPL") == REJECTED


def test_nan_growth_or_margin_is_classified_as_not_evaluable():
    selection = _select(
        [
            ("2025-09-29", _row("GROWTH", growth=np.nan)),
            ("2025-09-29", _row("MARGIN", margin=np.nan)),
        ]
    )

    assert _recommendation(selection, "GROWTH") == NOT_EVALUABLE
    assert _recommendation(selection, "MARGIN") == NOT_EVALUABLE


def test_nan_full_ratio_is_classified_as_not_evaluable():
    selection = _select(
        [("2025-09-29", _row("AAPL", full_ratio=np.nan))]
    )

    assert _recommendation(selection, "AAPL") == NOT_EVALUABLE


def test_missing_required_metric_column_is_classified_as_not_evaluable():
    stocks_data = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "Close": [100.0],
            "LTM EPS %": [10.0],
            "Full Ratio": [1.0],
        },
        index=pd.DatetimeIndex(["2025-09-29"], name="Date"),
    )

    selection = generar_seleccion_activos(
        stocks_data,
        logging.getLogger("test.asset_selection"),
    )

    assert _recommendation(selection, "AAPL") == NOT_EVALUABLE


def test_only_latest_market_date_is_used_for_a_symbol():
    selection = _select(
        [
            ("2025-09-28", _row("AAPL", growth=10.0, margin=10.0, full_ratio=10.0)),
            ("2025-09-29", _row("AAPL", growth=0.0, margin=10.0, full_ratio=10.0)),
        ]
    )

    assert _recommendation(selection, "AAPL") == REJECTED


def test_only_symbols_on_global_latest_date_are_selected():
    selection = _select(
        [
            ("2025-09-28", _row("AAPL", growth=10.0, margin=10.0, full_ratio=10.0)),
            ("2025-09-29", _row("MSFT", growth=10.0, margin=10.0, full_ratio=10.0)),
        ]
    )

    assert _recommendation(selection, "MSFT") == ATTRACTIVE
    assert "AAPL" not in selection.index
    assert set(selection.index) == {"MSFT"}


def test_symbols_on_latest_date_are_evaluated_independently():
    selection = _select(
        [
            ("2025-09-29", _row("AAPL", growth=5.0, margin=5.0, full_ratio=2.0)),
            ("2025-09-29", _row("MSFT", growth=5.0, margin=0.0, full_ratio=2.0)),
        ]
    )

    assert _recommendation(selection, "AAPL") == ATTRACTIVE
    assert _recommendation(selection, "MSFT") == REJECTED
    assert set(selection.index) == {"AAPL", "MSFT"}


def test_and_logic_requires_every_condition_to_be_positive():
    selection = _select(
        [
            ("2025-09-29", _row("A", growth=1.0, margin=0.0, full_ratio=1.0)),
            ("2025-09-29", _row("B", growth=0.0, margin=1.0, full_ratio=1.0)),
            ("2025-09-29", _row("C", growth=1.0, margin=1.0, full_ratio=0.0)),
            ("2025-09-29", _row("D", growth=1.0, margin=1.0, full_ratio=1.0)),
        ]
    )

    assert _recommendation(selection, "A") == REJECTED
    assert _recommendation(selection, "B") == REJECTED
    assert _recommendation(selection, "C") == REJECTED
    assert _recommendation(selection, "D") == ATTRACTIVE


def test_missing_metrics_receive_distinct_classification_from_rejection():
    selection = _select(
        [
            ("2025-09-29", _row("ATTRACTIVE", growth=1.0, margin=1.0, full_ratio=1.0)),
            ("2025-09-29", _row("REJECTED", growth=0.0, margin=1.0, full_ratio=1.0)),
            ("2025-09-29", _row("UNKNOWN", full_ratio=np.nan)),
        ]
    )

    assert _recommendation(selection, "ATTRACTIVE") == ATTRACTIVE
    assert _recommendation(selection, "REJECTED") == REJECTED
    assert _recommendation(selection, "UNKNOWN") == NOT_EVALUABLE
