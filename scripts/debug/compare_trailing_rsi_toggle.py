#!/usr/bin/env python3
"""A/B check: same config, only toggling RSI ON/OFF to see trailing stop source changes."""

from __future__ import annotations

import sys
from pathlib import Path
from collections import Counter

import pandas as pd
from backtesting import Backtest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion, System


def load_ohlcv(symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
    p = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    df = pd.read_csv(p)
    dc = next((c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None)
    if not dc:
        raise ValueError(f"No date column in {p}")
    df[dc] = pd.to_datetime(df[dc], errors="coerce")
    df = df.dropna(subset=[dc]).set_index(dc).sort_index()
    out = df[["Open", "High", "Low", "Close", "Volume"]]
    return out[(out.index >= pd.Timestamp(start)) & (out.index <= pd.Timestamp(end))].dropna()


def run_case(symbol: str, interval: str, start: str, end: str, rsi_enabled: bool):
    data = load_ohlcv(symbol, interval, start, end)

    # Isolate RSI impact on trailing source: disable RSI buy/sell switches and force no gate.
    System.rsi = rsi_enabled
    System.rsi_minimo = False
    System.rsi_ascendente = False
    System.rsi_maximo = False
    System.rsi_descendente = False
    System.rsi_strength_threshold = 0
    System.ticker = symbol

    bt = Backtest(
        data,
        System,
        cash=float(getattr(System, "cash", 10000) or 10000),
        commission=float(getattr(System, "commission", 0.0) or 0.0),
        trade_on_close=True,
        finalize_trades=True,
    )
    stats = bt.run()

    trades_list = list(getattr(stats._strategy, "trades_list", []) or [])
    stop_sources = Counter()
    for row in trades_list:
        if str(row.get("Tipo")) == "VENTA":
            desc = str(row.get("Descripcion", ""))
            if desc.startswith("StopLoss (") and desc.endswith(")"):
                stop_sources[desc] += 1

    return {
        "trades": int(stats.get("# Trades", 0) or 0),
        "ret": float(stats.get("Return [%]", 0.0) or 0.0),
        "stop_sources": dict(stop_sources),
    }


def main() -> int:
    symbol = "SAN.MC"
    interval = "1d"
    start = "2023-01-01"
    end = "2026-03-16"

    app = create_app("admin")
    with app.app_context():
        cargar_y_asignar_configuracion("admin")

        print("=== ADMIN CONFIG (relevant to trailing) ===")
        print(
            {
                "rsi": System.rsi,
                "rsi_trailing_limit": System.rsi_trailing_limit,
                "trailing_pct_below": System.trailing_pct_below,
                "trailing_pct_above": System.trailing_pct_above,
                "stoploss_percentage_below_close": System.stoploss_percentage_below_close,
                "breakeven_enabled": System.breakeven_enabled,
                "breakeven_trigger_pct": System.breakeven_trigger_pct,
                "stoploss_swing_enabled": System.stoploss_swing_enabled,
            }
        )

        off_case = run_case(symbol, interval, start, end, rsi_enabled=False)
        on_case = run_case(symbol, interval, start, end, rsi_enabled=True)

        print("\n=== CASE A: RSI OFF ===")
        print(off_case)
        print("\n=== CASE B: RSI ON (same config) ===")
        print(on_case)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
