#!/usr/bin/env python3
"""
Audit trailing stop behavior for ZTS without changing application code.

What this script does:
- Runs backtests for one symbol and multiple stop percentages.
- Uses the existing strategy/motor classes as-is.
- Audits each closed trade under TrailingBase with deterministic checks:
  1) stop is monotonic non-decreasing during the trade
  2) exit bar is the first bar where Close < trailing_stop
  3) recorded exit date matches expected date from OHLC replay

Default scenario mirrors your baseline:
- EMA slow period enabled for B&H context (200)
- No technical indicators active (RSI/MACD/Stoch/BB/EMA cross all off)
- No BreakEven, no Swing stop, no RSI trailing logic
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_engine.core.Backtest_Runner import run_backtest_for_symbol
from scenarios.BacktestWeb.estrategia_system import System


@dataclass
class AuditFinding:
    stop_value: float
    trade_number: int
    severity: str
    message: str


def _parse_decimal(value: str) -> float:
    """Accept both decimal formats: 0.05 and 0,05."""
    cleaned = value.strip().replace("%", "").replace(",", ".")
    return float(cleaned)


def _load_ohlcv(symbol: str, interval: str, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    csv_path = PROJECT_ROOT / "Data_files" / f"{symbol}_{interval}_MAX.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    date_col = next((c for c in ["Date", "date", "Fecha", "fecha", "Datetime", "datetime"] if c in df.columns), None)
    if not date_col:
        raise ValueError("No datetime column found in CSV")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing OHLCV columns: {missing}")

    out = df[required].copy()
    if start:
        out = out[out.index >= pd.to_datetime(start)]
    if end:
        out = out[out.index <= pd.to_datetime(end)]
    return out.dropna()


def _configure_base_strategy(ema_slow_period: int) -> None:
    # Baseline B&H-style setup: no technical buy/sell indicators active.
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


def _pair_trades(trades_df: pd.DataFrame) -> List[tuple[pd.Series, pd.Series]]:
    buys = []
    pairs = []
    for _, row in trades_df.iterrows():
        tipo = str(row.get("Tipo", "")).strip().upper()
        if tipo == "COMPRA":
            buys.append(row)
        elif tipo == "VENTA" and buys:
            pairs.append((buys.pop(0), row))
    return pairs


def _audit_trade(
    data: pd.DataFrame,
    buy_row: pd.Series,
    sell_row: pd.Series,
    trailing_pct: float,
    trade_number: int,
    stop_value: float,
) -> List[AuditFinding]:
    findings: List[AuditFinding] = []

    buy_ts = pd.to_datetime(buy_row["Fecha"], errors="coerce")
    sell_ts = pd.to_datetime(sell_row["Fecha"], errors="coerce")
    if pd.isna(buy_ts) or pd.isna(sell_ts):
        findings.append(AuditFinding(stop_value, trade_number, "error", "invalid trade dates"))
        return findings

    if buy_ts not in data.index or sell_ts not in data.index:
        findings.append(AuditFinding(stop_value, trade_number, "error", "trade date not present in OHLCV index"))
        return findings

    window = data.loc[(data.index >= buy_ts) & (data.index <= sell_ts)].copy()
    if window.empty:
        findings.append(AuditFinding(stop_value, trade_number, "error", "empty OHLCV window for trade"))
        return findings

    # Mirror production logic exactly for TrailingBase (Close/Close mode):
    # - At BUY: max_price starts at buy close; initial stop uses that close.
    # - During open position: max_price updates with each bar close.
    # - Stop only ratchets up, never down.
    # - Exit condition is close < my_stop_loss.
    buy_close = float(window.iloc[0]["Close"])
    max_price = buy_close
    my_stop_loss = max_price * (1 - trailing_pct)
    prev_stop = my_stop_loss
    expected_exit = None

    for ts, row in window.iloc[1:].iterrows():
        close = float(row["Close"])
        max_price = max(max_price, close)
        new_stop_loss = max_price * (1 - trailing_pct)

        if new_stop_loss > my_stop_loss:
            my_stop_loss = new_stop_loss

        if my_stop_loss + 1e-12 < prev_stop:
            findings.append(
                AuditFinding(
                    stop_value,
                    trade_number,
                    "error",
                    f"non-monotonic stop at {ts}: {my_stop_loss:.6f} < {prev_stop:.6f}",
                )
            )
            break
        prev_stop = my_stop_loss

        if close < my_stop_loss:
            expected_exit = ts
            break

    if expected_exit is None:
        findings.append(AuditFinding(stop_value, trade_number, "error", "no stop trigger found but trade was closed by stop"))
        return findings

    if expected_exit != sell_ts:
        findings.append(
            AuditFinding(
                stop_value,
                trade_number,
                "error",
                f"exit mismatch: expected {expected_exit.date()} but got {sell_ts.date()}",
            )
        )

    return findings


def run_audit(symbol: str, interval: str, start: str, end: str, ema_slow_period: int, stops: List[float]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("audit_stops")

    data = _load_ohlcv(symbol, interval, start, end)
    _configure_base_strategy(ema_slow_period)

    findings: List[AuditFinding] = []

    print("\n=== STOP AUDIT ===")
    print(f"Symbol={symbol} interval={interval} range={start}..{end} ema_slow={ema_slow_period}")

    for stop_value in stops:
        stats, trades_log, _ = run_backtest_for_symbol(
            data_clean=data,
            strategy_class=System,
            symbol=symbol,
            cash=10000,
            commission=0.0,
            stoploss_percentage=stop_value,
            logger=logger,
        )

        trades_df = pd.DataFrame(trades_log)
        if trades_df.empty:
            print(f"stop={stop_value:.2f} -> no trades")
            continue

        stop_sales = trades_df[
            (trades_df.get("Tipo", "").astype(str).str.upper() == "VENTA")
            & (trades_df.get("Descripcion", "").astype(str).str.contains("StopLoss", case=False, na=False))
        ]

        pairs = _pair_trades(trades_df)
        print(
            f"stop={stop_value:.2f} -> trades={len(trades_df)} pairs={len(pairs)} stop_sales={len(stop_sales)} return={float(stats.get('Return [%]', 0.0)):.2f}%"
        )

        for idx, (buy_row, sell_row) in enumerate(pairs, start=1):
            desc = str(sell_row.get("Descripcion", ""))
            if "StopLoss" not in desc:
                continue
            findings.extend(_audit_trade(data, buy_row, sell_row, stop_value, idx, stop_value))

    if not findings:
        print("\nNo stop logic issues detected in audited scenario.")
        return 0

    print("\nFindings:")
    for f in findings:
        print(f"- [{f.severity}] stop={f.stop_value:.2f} trade={f.trade_number}: {f.message}")

    errors = sum(1 for f in findings if f.severity == "error")
    return 1 if errors > 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit TrailingBase stop behavior for ZTS or another symbol.")
    parser.add_argument("--symbol", default="ZTS")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-03-16")
    parser.add_argument("--ema-slow", type=int, default=200)
    parser.add_argument("--stops", nargs="+", default=["0.05", "0.10", "0.15"], help="List like 0.05 0.10 0.15 or with comma")
    args = parser.parse_args()

    stops = [_parse_decimal(str(x)) for x in args.stops]
    return run_audit(args.symbol, args.interval, args.start, args.end, args.ema_slow, stops)


if __name__ == "__main__":
    raise SystemExit(main())
