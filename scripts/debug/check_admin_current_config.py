#!/usr/bin/env python3
"""Run a quick control backtest using the current persisted config for admin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from backtesting import Backtest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion, System


def _load_ohlcv(symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    date_col = next((c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None)
    if not date_col:
        raise ValueError(f"No date column in {csv_path.name}")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()

    out = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    out = out[(out.index >= pd.to_datetime(start)) & (out.index <= pd.to_datetime(end))]
    return out.dropna()


def main() -> int:
    parser = argparse.ArgumentParser(description="Control backtest using current admin persisted config")
    parser.add_argument("--symbols", nargs="+", default=["ZTS", "SAN.MC"])
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-03-16")
    args = parser.parse_args()

    app = create_app("admin")
    with app.app_context():
        cargar_y_asignar_configuracion("admin")

        print("=" * 96)
        print("CONTROL BACKTEST - CURRENT ADMIN PERSISTED CONFIG")
        print(f"Range: {args.start} -> {args.end} | Interval: {args.interval}")
        print(
            "Active core flags: "
            f"rsi={System.rsi}, rsi_minimo={System.rsi_minimo}, rsi_low_level={System.rsi_low_level}, "
            f"rsi_strength_threshold={System.rsi_strength_threshold}, "
            f"ema_slow_ascendente={System.ema_slow_ascendente}, ema_slow_period={System.ema_slow_period}"
        )
        print("=" * 96)

        for symbol in args.symbols:
            data = _load_ohlcv(symbol, args.interval, args.start, args.end)
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

            print(
                f"{symbol:<8} trades={int(stats.get('# Trades', 0)):>3} "
                f"return={float(stats.get('Return [%]', 0.0)):>8.2f}% "
                f"winrate={float(stats.get('Win Rate [%]', 0.0)):>7.2f}% "
                f"maxdd={float(stats.get('Max. Drawdown [%]', 0.0)):>8.2f}%"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
