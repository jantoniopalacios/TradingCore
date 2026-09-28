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


def test_nan_growth_or_margin_is_classified_as_rejected():
    selection = _select(
        [
            ("2025-09-29", _row("GROWTH", growth=np.nan)),
            ("2025-09-29", _row("MARGIN", margin=np.nan)),
        ]
    )

    assert _recommendation(selection, "GROWTH") == REJECTED
    assert _recommendation(selection, "MARGIN") == REJECTED


def test_nan_full_ratio_is_dropped_from_selection():
    selection = _select(
        [("2025-09-29", _row("AAPL", full_ratio=np.nan))]
    )

    assert "AAPL" not in selection.index
    assert selection.empty


def test_only_latest_market_date_is_used_for_a_symbol():
    selection = _select(
        [
            ("2025-09-28", _row("AAPL", growth=10.0, margin=10.0, full_ratio=10.0)),
            ("2025-09-29", _row("AAPL", growth=0.0, margin=10.0, full_ratio=10.0)),
        ]
    )

    assert _recommendation(selection, "AAPL") == REJECTED


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
