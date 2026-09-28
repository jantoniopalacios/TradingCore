from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import pandas as pd

from .store import FundamentalStore


LEGACY_EPS_COLUMNS = [
    "Symbol",
    "fiscalDateEnding",
    "reportedDate",
    "Diluted EPS",
]


def build_legacy_eps_dataframe(
    symbols: Iterable[str],
    fundamentals_path: Path | str,
) -> pd.DataFrame:
    """Convierte EPS almacenado a las columnas que consume el Full Ratio actual."""
    store = FundamentalStore(fundamentals_path)
    frames = []
    seen_symbols = set()

    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        if not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)

        records = store.load(symbol)
        if records.empty:
            continue

        records = records[
            (records["metric"] == "diluted_eps")
            & records["provider"].isin(["yahoo", "alpha_vantage"])
        ].copy()
        if records.empty:
            continue

        records["reported_date"] = pd.to_datetime(
            records["reported_date"], errors="coerce"
        )
        records["fiscal_date"] = pd.to_datetime(
            records["fiscal_date"], errors="coerce"
        )
        records["value"] = pd.to_numeric(records["value"], errors="coerce")
        records = records.dropna(
            subset=["reported_date", "fiscal_date", "value"]
        )
        records = records[records["value"].map(math.isfinite)]
        if records.empty:
            continue

        records["_provider_priority"] = records["provider"].map(
            {"yahoo": 0, "alpha_vantage": 1}
        )
        records = records.sort_values(
            ["fiscal_date", "_provider_priority", "updated_at"],
            na_position="first",
        ).drop_duplicates(subset=["fiscal_date"], keep="first")
        records["Symbol"] = symbol
        records["fiscalDateEnding"] = records["fiscal_date"]
        records["reportedDate"] = records["reported_date"]
        records["Diluted EPS"] = records["value"]
        frames.append(records[LEGACY_EPS_COLUMNS])

    if not frames:
        return pd.DataFrame(columns=LEGACY_EPS_COLUMNS)

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["Symbol", "fiscalDateEnding"])
        .reset_index(drop=True)
    )