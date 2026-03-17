#!/usr/bin/env python3
"""
Compara los dos modelos de trailing stop sin tocar el código de producción:

  - close/close (actual, desde commit a4203c6): max_price se actualiza con Close[-1]
  - high/close  (original, pre-commit):         max_price se actualiza con High[-1]

Uso básico:
    python scripts/compare_trailing_model.py \\
        --symbols ZTS SAN.MC \\
        --interval 1d \\
        --start 2023-01-01 \\
        --end 2026-03-16 \\
        --ema-slow 200 \\
        --stops 0.05 0.10 0.15

Salida: tabla por fila (símbolo × stop × modelo) con:
    Return [%], Trades, Stop-Sales, Win Rate, Max Drawdown, Sharpe
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importar el módulo ANTES de la estrategia para poder parchear el flag
import trading_engine.core.Logica_Trading as lt_module
from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_decimal(value: str) -> float:
    return float(value.strip().replace("%", "").replace(",", "."))


def _load_ohlcv(symbol: str, interval: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    date_col = next(
        (c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None
    )
    if not date_col:
        raise ValueError("Columna de fecha no encontrada en el CSV")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV sin columnas OHLCV: {missing}")

    out = df[required].copy()
    if start:
        out = out[out.index >= pd.to_datetime(start)]
    if end:
        out = out[out.index <= pd.to_datetime(end)]
    return out.dropna()


def _configure_base_strategy(ema_slow_period: int) -> None:
    System.ema_cruce_signal = False
    System.ema_fast_period = 5
    System.ema_slow_period = int(ema_slow_period)
    System.ema_slow_minimo = False
    System.ema_slow_ascendente = False
    System.ema_slow_maximo = False
    System.ema_slow_descendente = False

    System.rsi = False
    System.rsi_minimo = False
    System.rsi_ascendente = False
    System.rsi_maximo = False
    System.rsi_descendente = False
    System.rsi_trailing_limit = None
    System.trailing_pct_below = None
    System.trailing_pct_above = None

    System.macd = False
    System.stoch_fast = False
    System.stoch_mid = False
    System.stoch_slow = False
    System.bb_active = False

    System.stoploss_swing_enabled = False
    System.breakeven_enabled = False


def _count_stop_sales(trades_log: list) -> int:
    return sum(
        1
        for t in trades_log
        if str(t.get("Tipo", "")).upper() == "VENTA"
        and "StopLoss" in str(t.get("Descripcion", ""))
    )


def _extract_stats(stats: dict) -> dict:
    def _f(key: str, decimals: int = 2):
        val = stats.get(key, None)
        try:
            return round(float(val), decimals)
        except Exception:
            return None

    return {
        "Return [%]":    _f("Return [%]"),
        "Win Rate [%]":  _f("Win Rate [%]"),
        "Max DD [%]":    _f("Max. Drawdown [%]"),
        "Sharpe":        _f("Sharpe Ratio", 3),
    }


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def run_comparison(
    symbols: list[str],
    interval: str,
    start: str,
    end: str,
    ema_slow_period: int,
    stops: list[float],
) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("compare_trailing")

    _configure_base_strategy(ema_slow_period)

    models = [
        ("close", "Close/Close (actual)"),
        ("high",  "High/Close  (original)"),
    ]

    rows = []

    for symbol in symbols:
        print(f"\nCargando datos: {symbol} {interval} {start} -> {end}")
        data = _load_ohlcv(symbol, interval, start, end)

        for stop in stops:
            row_pair: dict[str, dict] = {}

            for model_key, model_label in models:
                # -- Fijar flag en el módulo de producción --
                lt_module._trailing_ref = model_key

                stats, trades_log, _ = run_backtest_for_symbol(
                    data_clean=data,
                    strategy_class=System,
                    symbol=symbol,
                    cash=10000,
                    commission=0.0,
                    stoploss_percentage=stop,
                    logger=logger,
                )

                trades_df = pd.DataFrame(trades_log)
                n_trades = len(trades_df[trades_df.get("Tipo", pd.Series(dtype=str)).astype(str).str.upper() == "COMPRA"]) if not trades_df.empty else 0
                n_stop   = _count_stop_sales(trades_log)
                kpi      = _extract_stats(stats)

                row_pair[model_key] = {
                    "Symbol":    symbol,
                    "Stop":      f"{stop:.0%}",
                    "Model":     model_label,
                    "Trades":    n_trades,
                    "StopSales": n_stop,
                    **kpi,
                }

            rows.append(row_pair["close"])
            rows.append(row_pair["high"])

    # -- Restaurar a modo de producción (close) --
    lt_module._trailing_ref = "close"

    # ---------------------------------------------------------------------------
    # Presentación de resultados
    # ---------------------------------------------------------------------------
    df = pd.DataFrame(rows)

    # Tabla plana
    print("\n" + "=" * 90)
    print(f"COMPARATIVA  Close/Close  vs  High/Close   --  {interval}  {start} -> {end}")
    print("=" * 90)

    col_w = {
        "Symbol": 8, "Stop": 5, "Model": 22,
        "Trades": 7, "StopSales": 9,
        "Return [%]": 11, "Win Rate [%]": 12, "Max DD [%]": 10, "Sharpe": 8,
    }
    header = "  ".join(k.ljust(v) for k, v in col_w.items())
    print(header)
    print("-" * len(header))

    prev_key = None
    for _, r in df.iterrows():
        key = (r["Symbol"], r["Stop"])
        if prev_key and key != prev_key:
            print()
        prev_key = key

        line = "  ".join(
            str(r.get(k, "")).ljust(v)
            for k, v in col_w.items()
        )
        print(line)

    # Resumen delta: high - close
    print("\n" + "=" * 90)
    print("DELTA  (High/Close minus Close/Close)  -- columnas numericas")
    print("=" * 90)

    close_df = df[df["Model"].str.startswith("Close")].set_index(["Symbol", "Stop"]).copy()
    high_df  = df[df["Model"].str.startswith("High")].set_index(["Symbol", "Stop"]).copy()

    num_cols = ["Return [%]", "Win Rate [%]", "Max DD [%]", "Sharpe", "Trades", "StopSales"]
    delta_df = (high_df[num_cols] - close_df[num_cols]).round(3)
    delta_df.columns = [f"D_{c.replace(' ', '_').replace('[', '').replace(']', '').replace('%', 'pct')}" for c in delta_df.columns]
    delta_df = delta_df.reset_index()

    # Simple delta table
    dcols = list(delta_df.columns)
    dwidths = [10, 6] + [13] * (len(dcols) - 2)
    dheader = "  ".join(c.ljust(w) for c, w in zip(dcols, dwidths))
    print(dheader)
    print("-" * len(dheader))
    for _, r in delta_df.iterrows():
        def _fmt(col, w):
            v = r[col]
            if isinstance(v, str):
                return str(v).ljust(w)
            if pd.isna(v):
                return "N/A".ljust(w)
            if isinstance(v, float):
                s = f"{v:+.2f}"
            else:
                s = f"{int(v):+d}"
            return s.ljust(w)
        print("  ".join(_fmt(c, w) for c, w in zip(dcols, dwidths)))

    print()
    print("Nota: D_* positivo = High/Close produce un valor mayor en esa metrica.")
    print("  _trailing_ref restaurado a 'close' (modo produccion).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Compara modelos Close/Close vs High/Close de trailing stop.")
    parser.add_argument("--symbols",   nargs="+", default=["ZTS", "SAN.MC"], help="Símbolos a comparar")
    parser.add_argument("--interval",  default="1d")
    parser.add_argument("--start",     default="2023-01-01")
    parser.add_argument("--end",       default="2026-03-16")
    parser.add_argument("--ema-slow",  type=int, default=200)
    parser.add_argument("--stops",     nargs="+", default=["0.05", "0.10", "0.15"])
    args = parser.parse_args()

    stops = [_parse_decimal(str(x)) for x in args.stops]
    run_comparison(args.symbols, args.interval, args.start, args.end, args.ema_slow, stops)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
